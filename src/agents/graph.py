import ast
import json
import re
from typing import Any, Dict, List, Optional
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph

from src.agents.llm import get_llm
from src.agents.prompts import CREDIT_PROMPT, EXCHANGE_PROMPT, INTERVIEW_PROMPT, TRIAGE_PROMPT
from src.agents.state import AgentState, AgentType
from src.database.csv_manager import clean_cpf, csv_manager
from src.tools.auth_tools import autenticar_cliente, solicitar_dados_autenticacao
from src.tools.credit_tools import consultar_limite_credito, processar_solicitacao_aumento_limite
from src.tools.exchange_tools import consultar_cotacao_moeda
from src.tools.interview_tools import processar_entrevista_e_atualizar_score
from src.tools.session_tools import encerrar_sessao_atendimento, transferir_para_agente

TRIAGE_TOOLS = [solicitar_dados_autenticacao, autenticar_cliente, transferir_para_agente, encerrar_sessao_atendimento]
CREDIT_TOOLS = [consultar_limite_credito, processar_solicitacao_aumento_limite, transferir_para_agente, encerrar_sessao_atendimento]
INTERVIEW_TOOLS = [processar_entrevista_e_atualizar_score, transferir_para_agente, encerrar_sessao_atendimento]
EXCHANGE_TOOLS = [consultar_cotacao_moeda, transferir_para_agente, encerrar_sessao_atendimento]

ALL_TOOLS = {
    "autenticar_cliente": autenticar_cliente,
    "solicitar_dados_autenticacao": solicitar_dados_autenticacao,
    "consultar_limite_credito": consultar_limite_credito,
    "processar_solicitacao_aumento_limite": processar_solicitacao_aumento_limite,
    "processar_entrevista_e_atualizar_score": processar_entrevista_e_atualizar_score,
    "consultar_cotacao_moeda": consultar_cotacao_moeda,
    "encerrar_sessao_atendimento": encerrar_sessao_atendimento,
    "transferir_para_agente": transferir_para_agente,
}

def extract_clean_text(content: Any) -> str:
    """Extrai texto limpo e natural de qualquer estrutura retornada pelo LLM ou LangChain/Gemini.
    Elimina metadados, blocos de assinatura, listas de dicionários [{'type': 'text', ...}], etc.

    Garantia: nunca retorna a representação bruta (str) de listas/dicionários internos.
    """
    if content is None:
        return ""

    # 1) Strings (inclusive representações Python de list/dict vindas do LLM)
    if isinstance(content, str):
        return _extract_text_from_string(content)

    # 2) Listas de blocos de conteúdo
    if isinstance(content, (list, tuple)):
        parts: List[str] = []
        for item in content:
            extracted = _extract_text_from_block(item)
            if extracted:
                parts.append(extracted)
        return "\n".join(parts).strip()

    # 3) Dicionários isolados
    if isinstance(content, dict):
        extracted = _extract_text_from_dict(content)
        return extracted if extracted else ""

    # 4) Objetos tipados (.text / .content / .parts)
    extracted = _extract_text_from_block(content)
    if extracted:
        return extracted

    return str(content).strip()


def _extract_text_from_block(block: Any) -> str:
    """Extrai o texto de um bloco individual de conteúdo (dict, string ou objeto)."""
    if block is None:
        return ""
    if isinstance(block, str):
        return _extract_text_from_string(block)
    if isinstance(block, dict):
        return _extract_text_from_dict(block)
    if isinstance(block, (list, tuple)):
        return extract_clean_text(block)

    # Blocos tipados (ex.: ContentBlock do langchain/google-genai)
    block_type = str(getattr(block, "type", "") or "").lower()
    if block_type in ("thought", "thinking", "tool_call", "function_call", "function_call_signature", "image", "image_url"):
        return ""
    if hasattr(block, "text"):
        val = getattr(block, "text")
        if val is not None and val is not block:
            return _extract_text_from_string(str(val))
    if hasattr(block, "content"):
        val = getattr(block, "content")
        if val is not None and val is not block:
            return extract_clean_text(val)
    return ""


def _extract_text_from_dict(block: Dict[str, Any]) -> str:
    """Extrai o texto de um bloco representado como dict."""
    block_type = str(block.get("type", "") or "").lower()

    if "text" in block and block_type not in ("thought", "thinking"):
        return _extract_text_from_string(str(block["text"]))

    if "thinking" in block:
        return ""

    if "content" in block:
        return extract_clean_text(block["content"])

    if "parts" in block:
        return extract_clean_text(block["parts"])

    # dict com chaves textuais variadas (ex.: {"role": ..., "text": ...})
    for key in ("text", "message", "answer"):
        if key in block and isinstance(block[key], str):
            return _extract_text_from_string(block[key])

    return ""


def _extract_text_from_string(text: str) -> str:
    """Limpa uma string; se for a repr de uma lista/dict, extrai recursivamente."""
    content_stripped = text.strip()
    if not content_stripped:
        return ""

    looks_like_collection = (
        (content_stripped.startswith("[") and content_stripped.endswith("]"))
        or (content_stripped.startswith("{") and content_stripped.endswith("}"))
    )
    if looks_like_collection:
        try:
            parsed = json.loads(content_stripped)
            cleaned = extract_clean_text(parsed)
            if cleaned:
                return cleaned
        except Exception:
            pass

        try:
            parsed = ast.literal_eval(content_stripped)
            cleaned = extract_clean_text(parsed)
            if cleaned:
                return cleaned
        except Exception:
            pass

        # Último recurso: capturar apenas os campos 'text' (descarta assinaturas/metadados)
        matches = re.findall(
            r"['\"]text['\"]\s*:\s*['\"](.*?)['\"](?=(?:,\s*['\"]|\s*\}))",
            content_stripped,
            re.DOTALL,
        )
        if matches:
            joined = "".join(matches)
            return (
                joined.replace("\\n", "\n")
                .replace("\\'", "'")
                .replace('\\"', '"')
                .strip()
            )

    return content_stripped

def execute_tools(messages: List[BaseMessage]) -> List[ToolMessage]:
    last_message = messages[-1]
    tool_messages = []
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_fn = ALL_TOOLS.get(tool_name)
            if tool_fn:
                try:
                    result = tool_fn.invoke(tool_args)
                except Exception as exc:
                    result = f"ERRO na execução da ferramenta {tool_name}: {str(exc)}"
            else:
                result = f"ERRO: Ferramenta {tool_name} não encontrada."
            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                )
            )
    return tool_messages

def _sanitize_history(messages: List[BaseMessage]) -> List[BaseMessage]:
    """Remove tool calls e respostas de ferramentas do histórico persistido.

    O Gemini (modelos com thinking) exige `thought_signature` ao reenviar
    function calls e rejeita a requisição quando a assinatura não está
    disponível. Para evitar o erro 400, o histórico enviado contém apenas
    mensagens de texto (humanas e do assistente).
    """
    clean: List[BaseMessage] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            continue
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            text = extract_clean_text(m.content)
            if text:
                clean.append(AIMessage(content=text))
            continue
        clean.append(m)
    return clean

class AgentOrchestrator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.llm = get_llm(api_key=api_key)
        self.triage_llm = self.llm.bind_tools(TRIAGE_TOOLS)
        self.credit_llm = self.llm.bind_tools(CREDIT_TOOLS)
        self.interview_llm = self.llm.bind_tools(INTERVIEW_TOOLS)
        self.exchange_llm = self.llm.bind_tools(EXCHANGE_TOOLS)
        self.graph = self._build_graph()
        self._route_depth = 0

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("triage", self.triage_node)
        workflow.add_node("credit", self.credit_node)
        workflow.add_node("interview", self.interview_node)
        workflow.add_node("exchange", self.exchange_node)

        workflow.set_conditional_entry_point(
            self.route_entry,
            {
                "triage": "triage",
                "credit": "credit",
                "interview": "interview",
                "exchange": "exchange",
                "ended": END,
            },
        )

        workflow.add_edge("triage", END)
        workflow.add_edge("credit", END)
        workflow.add_edge("interview", END)
        workflow.add_edge("exchange", END)

        return workflow.compile()

    def route_entry(self, state: AgentState) -> str:
        if state.get("is_finished", False):
            return "ended"
        
        if not state.get("authenticated", False):
            return "triage"
        
        active = state.get("active_agent", "triage")
        return active if active in ["credit", "interview", "exchange"] else "triage"

    def _call_agent_with_tools(
        self,
        prompt: str,
        llm_with_tools: Any,
        state: AgentState,
        agent_name: AgentType,
    ) -> Dict[str, Any]:
        messages = _sanitize_history(state["messages"])
        client_context = ""
        if state.get("authenticated") and state.get("client_cpf"):
            client = csv_manager.find_client_by_cpf(state["client_cpf"])
            if client:
                client_context = (
                    f"\n\n[CONTEXTO DO CLIENTE ATUAL - MADEIRO BANK]\n"
                    f"Nome: {client.nome}\nCPF: {client.cpf}\n"
                    f"Limite Atual: R$ {client.limite_credito:.2f}\n"
                    f"Score Atual: {client.score_credito} pontos"
                )

        redirect_note = ""
        if agent_name == "credit" and state.get("interview_completed"):
            # Retomada pós-entrevista: o Agente de Crédito recebe contexto limpo
            # (sem o transcript da entrevista) para oferecer a nova análise sem
            # risco de redirecionamentos de ping-pong com o Agente de Entrevista.
            messages = [
                HumanMessage(
                    content="[RETOMADA PÓS-ENTREVISTA] O cliente acabou de concluir a "
                    "entrevista financeira. Continue o atendimento conforme o contexto "
                    "de redirecionamento do sistema."
                )
            ]
            redirect_note = (
                "\n\n[CONTEXTO DE REDIRECIONAMENTO]\n"
                "O cliente acabou de concluir a Entrevista Financeira de reavaliação de score. "
                "O score atualizado já está no contexto do cliente acima. Retome o atendimento "
                "oferecendo uma NOVA ANÁLISE de limite: apresente o novo score e pergunte se o "
                "cliente deseja solicitar um novo limite de crédito agora."
            )

        sys_msg = SystemMessage(content=prompt + client_context + redirect_note)
        conversation = [sys_msg] + messages

        updated_state: Dict[str, Any] = {
            "messages": [],
            "active_agent": agent_name,
            "request_auth_modal": False,
        }
        if agent_name == "credit" and state.get("interview_completed"):
            updated_state["interview_completed"] = False
        transfer_target: Optional[str] = None
        auth_attempts = state.get("auth_attempts", 0)

        # Loop agêntico: executa ferramentas até o modelo produzir uma resposta final
        # em texto, ou solicitar transferência para outro especialista.
        for _ in range(8):
            raw_response = llm_with_tools.invoke(conversation)

            tool_calls = getattr(raw_response, "tool_calls", None)
            if not tool_calls:
                conversation.append(raw_response)
                updated_state["messages"].append(raw_response)
                break

            tool_results = execute_tools([raw_response])

            # Bloqueio de escopo: a Triagem só transfere após autenticar o cliente.
            for tr in tool_results:
                if "TRANSFERENCIA:" in str(tr.content):
                    already_authed = state.get("authenticated", False) or updated_state.get("authenticated", False)
                    if agent_name == "triage" and not already_authed:
                        tr.content = (
                            "ERRO: Autenticação pendente. Chame `solicitar_dados_autenticacao` "
                            "para coletar os dados e `autenticar_cliente` antes de transferir "
                            "o atendimento para outro agente."
                        )

            # Os resultados das ferramentas são reapresentados ao modelo como
            # mensagem de texto (nunca como functionCall/response), evitando o
            # requisito de thought_signature do Gemini em requisições seguintes.
            results_lines = [f"- Ferramenta `{tr.name}`: {tr.content}" for tr in tool_results]
            summary = HumanMessage(
                content="[RESULTADOS DAS FERRAMENTAS - DADOS INTERNOS DO SISTEMA]\n"
                + "\n".join(results_lines)
                + "\n\nContinue o atendimento com base nos resultados acima."
            )
            conversation.append(summary)

            for tr in tool_results:
                tr_content = str(tr.content)
                if "AUTENTICACAO_SUCESSO" in tr_content:
                    updated_state["authenticated"] = True
                    updated_state["auth_attempts"] = 0
                    updated_state["request_auth_modal"] = False
                    auth_attempts = 0
                    match_cpf = re.search(r"CPF:\s*(\d+)", tr_content)
                    match_nome = re.search(r"Cliente\s+(.+?)\s+autenticado", tr_content)
                    if match_cpf:
                        updated_state["client_cpf"] = match_cpf.group(1)
                    if match_nome:
                        updated_state["client_name"] = match_nome.group(1)
                elif "FALHA_AUTENTICACAO" in tr_content:
                    auth_attempts += 1
                    updated_state["auth_attempts"] = auth_attempts
                    if auth_attempts >= 3:
                        updated_state["is_finished"] = True
                        updated_state["active_agent"] = "ended"
                elif "SESSAO_ENCERRADA" in tr_content:
                    updated_state["is_finished"] = True
                    updated_state["active_agent"] = "ended"
                elif "SOLICITAR_DADOS_AUTENTICACAO" in tr_content:
                    updated_state["request_auth_modal"] = True
                elif "ENTREVISTA_CONCLUIDA" in tr_content:
                    updated_state["interview_completed"] = True
                    updated_state["active_agent"] = "credit"
                    if agent_name == "interview":
                        transfer_target = "credit"
                elif "TRANSFERENCIA:" in tr_content:
                    target = tr_content.split("TRANSFERENCIA:", 1)[1].strip().lower()
                    if target in ("credit", "interview", "exchange") and target != agent_name:
                        transfer_target = target
                        updated_state["active_agent"] = target

            if transfer_target:
                break

        if not updated_state["messages"] and not transfer_target:
            if updated_state.get("is_finished"):
                fallback_text = "Atendimento encerrado. O Madeiro Bank agradece o seu contato!"
            elif updated_state.get("request_auth_modal"):
                fallback_text = (
                    "Para continuar com segurança, clique no botão de autenticação "
                    "e informe seu CPF e sua Data de Nascimento."
                )
            else:
                fallback_text = (
                    "Não consegui concluir esta solicitação agora. "
                    "Por favor, tente novamente."
                )
            updated_state["messages"].append(AIMessage(content=fallback_text))

        if (
            agent_name == "triage"
            and not transfer_target
            and not state.get("authenticated", False)
            and not updated_state.get("authenticated", False)
            and not updated_state.get("is_finished", False)
        ):
            # Garantia determinística: enquanto não houver autenticação, o botão
            # de CPF e Data de Nascimento permanece disponível para nova tentativa.
            updated_state["request_auth_modal"] = True

        if transfer_target:
            # A chamada de transferência é um controle interno: não deve entrar no
            # histórico da conversa (evita conflito de ordenação de function calls
            # no Gemini). O agente de destino gera a resposta a partir do contexto.
            updated_state["messages"] = []

        updated_state["_transfer_to"] = transfer_target
        return updated_state

    def _route_to(
        self,
        target: str,
        state: AgentState,
        fallback_prompt: str,
        fallback_llm: Any,
        fallback_name: AgentType,
    ) -> Dict[str, Any]:
        """Redireciona para outro nó de agente, com proteção contra loops infinitos."""
        self._route_depth += 1
        if self._route_depth > 6:
            self._route_depth -= 1
            return self._call_agent_with_tools(fallback_prompt, fallback_llm, state, fallback_name)
        try:
            return getattr(self, f"{target}_node")(state)
        finally:
            self._route_depth -= 1

    def _run_node(
        self,
        state: AgentState,
        agent_name: AgentType,
        prompt: str,
        llm_with_tools: Any,
    ) -> Dict[str, Any]:
        """Executa um agente e, se ele solicitar transferência, redireciona ao destino."""
        result = self._call_agent_with_tools(prompt, llm_with_tools, state, agent_name)
        transfer = result.pop("_transfer_to", None)
        if not transfer or transfer == agent_name:
            return result

        # Propaga as flags de estado (ex.: autenticação) para o agente de destino
        # e garante que sejam refletidas no estado final do grafo.
        flags = {k: v for k, v in result.items() if k != "messages"}
        for key, value in flags.items():
            state[key] = value

        target_result = self._route_to(transfer, state, prompt, llm_with_tools, agent_name)
        for key, value in flags.items():
            target_result.setdefault(key, value)
        return target_result

    def triage_node(self, state: AgentState) -> Dict[str, Any]:
        return self._run_node(state, "triage", TRIAGE_PROMPT, self.triage_llm)

    def credit_node(self, state: AgentState) -> Dict[str, Any]:
        return self._run_node(state, "credit", CREDIT_PROMPT, self.credit_llm)

    def interview_node(self, state: AgentState) -> Dict[str, Any]:
        return self._run_node(state, "interview", INTERVIEW_PROMPT, self.interview_llm)

    def exchange_node(self, state: AgentState) -> Dict[str, Any]:
        return self._run_node(state, "exchange", EXCHANGE_PROMPT, self.exchange_llm)

    def process_message(self, state: AgentState) -> AgentState:
        self._route_depth = 0
        return self.graph.invoke(state)

