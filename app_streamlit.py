import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.graph import AgentOrchestrator, extract_clean_text
from src.database.csv_manager import csv_manager
from src.tools.exchange_tools import consultar_cotacao_moeda

st.set_page_config(
    page_title="Banco Ágil",
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
    .transition-pill {
        background-color: #0f172a;
        color: #94a3b8;
        border: 1px solid #6366f1;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.75rem;
        display: inline-block;
        margin: 10px auto;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

if "state" not in st.session_state:
    st.session_state.state = {
        "messages": [],
        "active_agent": "triage",
        "authenticated": False,
        "client_cpf": None,
        "client_name": None,
        "auth_attempts": 0,
        "interview_data": {},
        "is_finished": False,
    }

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "type": "message",
            "role": "assistant",
            "agent": "triage",
            "content": "Olá! Bem-vindo ao **Banco Ágil**. Sou seu assistente virtual. Para iniciarmos seu atendimento com segurança, por favor, me informe seu **CPF** e **Data de Nascimento**.",
        }
    ]

with st.sidebar:
    st.title("🏦 Banco Ágil")

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
            "is_finished": False,
        }
        st.session_state.chat_history = [
            {
                "type": "message",
                "role": "assistant",
                "agent": "triage",
                "content": "Olá! Bem-vindo ao **Banco Ágil**. Para iniciarmos seu atendimento com segurança, por favor, me informe seu **CPF** e **Data de Nascimento**.",
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

st.header("💬 Banco Ágil")

agent_labels = {
    "triage": ("Agente de Triagem", "badge-triage"),
    "credit": ("Agente de Crédito", "badge-credit"),
    "interview": ("Agente de Entrevista de Crédito", "badge-interview"),
    "exchange": ("Agente de Câmbio", "badge-exchange"),
    "ended": ("Atendimento Encerrado", "badge-ended"),
}

for item in st.session_state.chat_history:
    if item.get("type") == "transition":
        from_name = agent_labels.get(item["from"], (item["from"], ""))[0]
        to_name = agent_labels.get(item["to"], (item["to"], ""))[0]
        st.markdown(
            f'<div style="text-align: center;"><span class="transition-pill">🔄 Transferência em tempo real: {from_name} ➔ <b>{to_name}</b></span></div>',
            unsafe_allow_html=True,
        )
    else:
        msg = item
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                agent_key = msg.get("agent", "triage")
                name, badge_cls = agent_labels.get(agent_key, ("Agente", "badge-triage"))
                st.markdown(f'<span class="agent-badge {badge_cls}">🤖 {name}</span>', unsafe_allow_html=True)
            st.markdown(msg["content"])

user_input = st.chat_input("Digite sua mensagem...", disabled=st.session_state.state.get("is_finished", False))

if user_input:
    st.session_state.chat_history.append({"type": "message", "role": "user", "content": user_input})
    st.session_state.state["messages"].append(HumanMessage(content=user_input))
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Processando solicitação..."):
            prev_agent = st.session_state.state.get("active_agent", "triage")
            updated_state = st.session_state.orchestrator.process_message(st.session_state.state)
            
            for k, v in updated_state.items():
                if k == "messages":
                    st.session_state.state["messages"] = v
                else:
                    st.session_state.state[k] = v

            new_agent = st.session_state.state.get("active_agent", "triage")
            
            if prev_agent != new_agent:
                st.session_state.chat_history.append({
                    "type": "transition",
                    "from": prev_agent,
                    "to": new_agent,
                })

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
