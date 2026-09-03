import os
import base64
import hashlib
import hmac
import json
import uuid
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.graph import AgentOrchestrator, extract_clean_text
from src.agents.state import AgentState
from src.config import CLIENTS_CSV_PATH, REQUESTS_CSV_PATH, SCORE_LIMIT_CSV_PATH
from src.database.csv_manager import csv_manager
from src.models.schemas import ChatRequest, ChatResponse, ResetRequest
from src.tools.exchange_tools import consultar_cotacao_moeda

app = FastAPI(
    title="Madeiro Bank - Agente Bancário Inteligente",
    description="Sistema multiespecialista de atendimento bancário com LangChain, LangGraph e Google Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: Dict[str, AgentState] = {}
orchestrators: Dict[str, AgentOrchestrator] = {}
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24
SESSION_COOKIE_PREFIX = "madeiro-session-"
SESSION_SECRET = (
    os.getenv("SESSION_SECRET")
    or os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or "madeiro-bank-development-session-secret"
)


def _new_session_state() -> AgentState:
    return {
        "messages": [],
        "active_agent": "triage",
        "authenticated": False,
        "client_cpf": None,
        "client_name": None,
        "auth_attempts": 0,
        "interview_data": {},
        "interview_completed": False,
        "request_auth_modal": False,
        "is_finished": False,
    }


def _session_cookie_name(session_id: str) -> str:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]
    return f"{SESSION_COOKIE_PREFIX}{digest}"


def _session_snapshot(state: AgentState) -> Dict[str, Any]:
    """Keep the serverless handoff small and free of tool-call metadata."""
    history = []
    for message in state.get("messages", [])[-4:]:
        if isinstance(message, HumanMessage):
            role = "human"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue
        content = extract_clean_text(message.content)
        if content:
            history.append({"role": role, "content": content[:350]})

    return {
        "active_agent": state.get("active_agent", "triage"),
        "authenticated": bool(state.get("authenticated", False)),
        "client_cpf": state.get("client_cpf"),
        "client_name": state.get("client_name"),
        "auth_attempts": int(state.get("auth_attempts", 0)),
        "interview_data": state.get("interview_data", {}),
        "interview_completed": bool(state.get("interview_completed", False)),
        "request_auth_modal": bool(state.get("request_auth_modal", False)),
        "is_finished": bool(state.get("is_finished", False)),
        "messages": history,
    }


def _encode_session_cookie(state: AgentState) -> str:
    payload = json.dumps(
        _session_snapshot(state), ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _decode_session_cookie(value: Optional[str]) -> Optional[AgentState]:
    if not value or "." not in value:
        return None
    encoded, signature = value.rsplit(".", 1)
    expected = hmac.new(
        SESSION_SECRET.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        snapshot = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
        state = _new_session_state()
        for key in (
            "active_agent",
            "authenticated",
            "client_cpf",
            "client_name",
            "auth_attempts",
            "interview_data",
            "interview_completed",
            "request_auth_modal",
            "is_finished",
        ):
            if key in snapshot:
                state[key] = snapshot[key]
        for item in snapshot.get("messages", []):
            if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                continue
            if item.get("role") == "human":
                state["messages"].append(HumanMessage(content=item["content"]))
            elif item.get("role") == "assistant":
                state["messages"].append(AIMessage(content=item["content"]))
        return state
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _set_session_cookie(response: Response, session_id: str, state: AgentState) -> None:
    response.set_cookie(
        key=_session_cookie_name(session_id),
        value=_encode_session_cookie(state),
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=bool(os.getenv("VERCEL")),
        samesite="lax",
        path="/",
    )


def get_session_state(session_id: str, cookie_value: Optional[str] = None) -> AgentState:
    if session_id not in sessions:
        sessions[session_id] = _decode_session_cookie(cookie_value) or _new_session_state()
    return sessions[session_id]

def get_orchestrator() -> AgentOrchestrator:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    if key not in orchestrators:
        orchestrators[key] = AgentOrchestrator()
    return orchestrators[key]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Madeiro Bank AI Agent"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, request: Request, response: Response):
    cookie_name = _session_cookie_name(payload.session_id)
    state = get_session_state(payload.session_id, request.cookies.get(cookie_name))

    if state.get("is_finished", False):
        _set_session_cookie(response, payload.session_id, state)
        return ChatResponse(
            session_id=payload.session_id,
            response="Este atendimento foi encerrado. Para iniciar um novo contato com o **Madeiro Bank**, reinicie a sessão.",
            active_agent="ended",
            authenticated=state.get("authenticated", False),
            client_info=csv_manager.find_client_by_cpf(state["client_cpf"]) if state.get("client_cpf") else None,
            is_finished=True,
        )

    previous_agent = state.get("active_agent", "triage")
    user_msg = HumanMessage(content=payload.message)
    state["messages"].append(user_msg)

    try:
        orchestrator = get_orchestrator()
        updated_state = orchestrator.process_message(state)
        
        for k, v in updated_state.items():
            if k == "messages":
                state["messages"] = v
            else:
                state[k] = v

        new_active_agent = state.get("active_agent", "triage")
        transition_occurred = bool(previous_agent != new_active_agent)

        last_ai_message = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
            "Desculpe, não consegui processar a resposta no momento. Por favor, tente novamente.",
        )
        cleaned_response = extract_clean_text(last_ai_message)

        client_info = None
        if state.get("authenticated") and state.get("client_cpf"):
            client_info = csv_manager.find_client_by_cpf(state["client_cpf"])

        _set_session_cookie(response, payload.session_id, state)
        return ChatResponse(
            session_id=payload.session_id,
            response=cleaned_response,
            active_agent=new_active_agent,
            previous_agent=previous_agent,
            transition_occurred=transition_occurred,
            authenticated=state.get("authenticated", False),
            client_info=client_info,
            request_auth_modal=state.get("request_auth_modal", False),
            is_finished=state.get("is_finished", False),
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no processamento do agente: {str(exc)}")

@app.post("/api/reset")
def reset_session(
    response: Response,
    payload: Optional[ResetRequest] = None,
    session_id: Optional[str] = None,
):
    target_id = session_id or (payload.session_id if payload else None) or str(uuid.uuid4())
    sessions[target_id] = _new_session_state()
    _set_session_cookie(response, target_id, sessions[target_id])
    return {"session_id": target_id, "message": "Sessão reiniciada com sucesso."}

@app.get("/api/clients")
def list_clients():
    return {"clients": csv_manager.get_all_clients()}

@app.get("/api/requests")
def list_requests():
    return {"requests": csv_manager.get_all_requests()}

@app.get("/api/score-rules")
def list_score_rules():
    return {"rules": csv_manager.get_all_score_rules()}

@app.get("/api/exchange-rates")
def get_exchange_rates():
    quotes = {}
    for code in ["USD", "EUR", "GBP", "BTC"]:
        try:
            res = consultar_cotacao_moeda.invoke({"moeda": code})
            quotes[code] = res
        except Exception:
            quotes[code] = f"Cotação {code} indisponível temporariamente."
    return {"quotes": quotes}

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))
