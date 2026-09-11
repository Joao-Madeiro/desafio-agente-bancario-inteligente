import re

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.graph import AgentOrchestrator, extract_clean_text
from src.database.csv_manager import csv_manager
from src.tools.exchange_tools import consultar_cotacao_moeda


def format_auth_date(value: str) -> str:
    """Converte uma data compacta do modal para o formato aceito pela API."""
    trimmed = str(value or "").strip()
    iso_match = re.match(r"^(\d{4})[-/](\d{2})[-/](\d{2})$", trimmed)
    if iso_match:
        return f"{iso_match.group(3)}/{iso_match.group(2)}/{iso_match.group(1)}"
    digits = re.sub(r"\D", "", trimmed)
    digits = digits[:8]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}/{digits[2:]}"
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"


def format_auth_cpf(value: str) -> str:
    """Aplica a máscara visual de CPF no valor preenchido no modal."""
    digits = re.sub(r"\D", "", str(value or ""))[:11]
    if len(digits) <= 3:
        return digits
    if len(digits) <= 6:
        return f"{digits[:3]}.{digits[3:]}"
    if len(digits) <= 9:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

st.set_page_config(
    page_title="Madeiro Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main { background-color: #0b0f19; }
    .agent-badge {
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 6px;
    }
    .badge-triage { background-color: #083344; color: #67e8f9; border: 1px solid #06b6d4; }
    .badge-credit { background-color: #022c22; color: #6ee7b7; border: 1px solid #10b981; }
    .badge-interview { background-color: #2e1065; color: #d8b4fe; border: 1px solid #8b5cf6; }
    .badge-exchange { background-color: #451a03; color: #fcd34d; border: 1px solid #f59e0b; }
    .badge-ended { background-color: #1e293b; color: #94a3b8; border: 1px solid #475569; }
</style>
""", unsafe_allow_html=True)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

if "auth_modal_open" not in st.session_state:
    st.session_state.auth_modal_open = False

if "state" not in st.session_state:
    st.session_state.state = {
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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "type": "message",
            "role": "assistant",
            "agent": "triage",
            "content": "Olá! Bem-vindo ao **Madeiro Bank**. Sou seu assistente virtual. Envie uma mensagem para iniciarmos seu atendimento.",
        }
    ]

with st.sidebar:
    st.title("🏦 Madeiro Bank")

    if not st.session_state.orchestrator:
        st.session_state.orchestrator = AgentOrchestrator()

    st.divider()

    st.subheader("👤 Perfil do Cliente")
    if st.session_state.state.get("authenticated") and st.session_state.state.get("client_cpf"):
        client = csv_manager.find_client_by_cpf(st.session_state.state["client_cpf"])
        if client:
            st.success(f"**{client.nome}** (Autenticado)")
            st.write(f"**CPF:** `{client.cpf}`")
            st.metric("Limite de Crédito", f"R$ {client.limite_credito:,.2f}")
            st.metric("Score de Crédito", f"{client.score_credito} pts")
    else:
        st.info("Nenhum cliente autenticado no momento.")

    st.divider()

    if st.button("🔄 Novo Atendimento (Reset)"):
        st.session_state.state = {
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
        st.session_state.auth_modal_open = False
        st.session_state.chat_history = [
            {
                "type": "message",
                "role": "assistant",
                "agent": "triage",
                "content": "Olá! Bem-vindo ao **Madeiro Bank**. Envie uma mensagem para iniciarmos seu atendimento.",
            }
        ]
        st.rerun()

    st.subheader("📊 Base de Dados (CSV)")
    csv_tab = st.selectbox("Visualizar Tabela:", ["Clientes", "Solicitações de Aumento", "Regras de Score"])
    if csv_tab == "Clientes":
        st.dataframe(csv_manager.get_clients_df(), use_container_width=True)
    elif csv_tab == "Solicitações de Aumento":
        st.dataframe(csv_manager.get_requests_df(), use_container_width=True)
    else:
        st.dataframe(csv_manager.get_score_rules_df(), use_container_width=True)

st.header("💬 Madeiro Bank")

agent_labels = {
    "triage": ("Agente de Triagem", "badge-triage"),
    "credit": ("Agente de Crédito", "badge-credit"),
    "interview": ("Agente de Entrevista de Crédito", "badge-interview"),
    "exchange": ("Agente de Câmbio", "badge-exchange"),
    "ended": ("Atendimento Encerrado", "badge-ended"),
}

for item in st.session_state.chat_history:
    if item.get("type") == "transition":
        continue
    msg = item
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            agent_key = msg.get("agent", "triage")
            name, badge_cls = agent_labels.get(agent_key, ("Agente", "badge-triage"))
            st.markdown(f'<span class="agent-badge {badge_cls}">🤖 {name}</span>', unsafe_allow_html=True)
        st.markdown(msg["content"])

user_input = st.chat_input("Digite sua mensagem...", disabled=st.session_state.state.get("is_finished", False))

if (
    st.session_state.state.get("request_auth_modal")
    and not st.session_state.state.get("authenticated")
    and not st.session_state.state.get("is_finished")
):
    with st.chat_message("assistant"):
        st.markdown(
            "Para continuar com segurança, informe seus dados cadastrais "
            "usando o botão abaixo."
        )
        if st.button("🔐 Preencher dados de autenticação", key="open_auth_modal"):
            st.session_state.auth_modal_open = True

if (
    st.session_state.get("auth_modal_open")
    and st.session_state.state.get("request_auth_modal")
    and not st.session_state.state.get("authenticated")
    and not st.session_state.state.get("is_finished")
):
    @st.dialog("🔐 Autenticação do Cliente", width="small")
    def _auth_dialog():
        st.markdown(
            "**Madeiro Bank** · Para iniciar o atendimento com segurança, "
            "informe seus dados cadastrais. Use um CPF cadastrado na base de teste."
        )
        with st.form("auth_modal_form"):
            cpf_val = st.text_input("CPF (somente números)", placeholder="000.000.000-00")
            dn_val = st.text_input("Data de Nascimento", placeholder="DD/MM/AAAA")
            submitted = st.form_submit_button(
                "🔐 Autenticar", type="primary", use_container_width=True
            )
        if submitted:
            if cpf_val and dn_val:
                cpf_clean = re.sub(r"\D", "", cpf_val)
                st.session_state.auth_modal_payload = (
                    f"Meu CPF é {format_auth_cpf(cpf_clean)} e minha data de nascimento é "
                    f"{format_auth_date(dn_val)}"
                )
                st.session_state.auth_modal_open = False
                st.rerun()
            else:
                st.warning("Preencha o CPF e a Data de Nascimento.")

    _auth_dialog()

auth_modal_payload = st.session_state.pop("auth_modal_payload", None)
if user_input is None and auth_modal_payload:
    user_input = auth_modal_payload

if user_input:
    st.session_state.chat_history.append({"type": "message", "role": "user", "content": user_input})
    st.session_state.state["messages"].append(HumanMessage(content=user_input))
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Processando solicitação..."):
            updated_state = st.session_state.orchestrator.process_message(st.session_state.state)
            
            for k, v in updated_state.items():
                if k == "messages":
                    st.session_state.state["messages"] = v
                else:
                    st.session_state.state[k] = v

            if st.session_state.state.get("authenticated") or st.session_state.state.get("is_finished"):
                st.session_state.auth_modal_open = False

            new_agent = st.session_state.state.get("active_agent", "triage")
            
            last_ai = next(
                (m.content for m in reversed(st.session_state.state["messages"]) if isinstance(m, AIMessage)),
                "Atendimento processado.",
            )
            cleaned_ai = extract_clean_text(last_ai)

            name, badge_cls = agent_labels.get(new_agent, ("Agente", "badge-triage"))
            st.markdown(f'<span class="agent-badge {badge_cls}">🤖 {name}</span>', unsafe_allow_html=True)
            st.markdown(cleaned_ai)

            st.session_state.chat_history.append({
                "type": "message",
                "role": "assistant",
                "agent": new_agent,
                "content": cleaned_ai,
            })
            st.rerun()
