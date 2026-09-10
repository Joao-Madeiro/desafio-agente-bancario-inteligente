from langchain_core.messages import AIMessage, HumanMessage

from src.agents.graph import AgentOrchestrator, TRIAGE_PROMPT
from src.api.main import _new_session_state
from src.database.csv_manager import CSVManager
from src.tools import credit_tools, exchange_tools, interview_tools


def make_manager(tmp_path):
    clients = tmp_path / "clientes.csv"
    clients.write_text(
        "cpf,nome,data_nascimento,limite_credito,score_credito,email,telefone\n"
        "12345678900,Cliente Teste,1990-05-15,2500.0,450,,\n",
        encoding="utf-8",
    )
    return CSVManager(
        clients_path=clients,
        requests_path=tmp_path / "solicitacoes.csv",
        score_path=tmp_path / "score.csv",
    )


def test_limit_request_is_persisted_with_final_status(monkeypatch, tmp_path):
    manager = make_manager(tmp_path)
    monkeypatch.setattr(credit_tools, "csv_manager", manager)

    result = credit_tools.processar_solicitacao_aumento_limite.invoke(
        {"cpf": "123.456.789-00", "novo_limite_solicitado": "R$ 5.000,00"}
    )

    assert "SOLICITACAO_APROVADA" in result
    request = manager.get_all_requests()[0]
    assert request.status_pedido == "aprovado"
    assert manager.find_client_by_cpf("12345678900").limite_credito == 5000.0


def test_interview_score_validates_inputs_and_clamps_range():
    assert interview_tools.calculate_score(3000, "formal", 1000, 0, "não") == 590

    try:
        interview_tools.calculate_score(3000, "informal", 1000, 0, "não")
    except ValueError as exc:
        assert "tipo de emprego" in str(exc)
    else:
        raise AssertionError("Entradas inválidas deveriam ser rejeitadas")


def test_exchange_accepts_currency_names():
    assert exchange_tools.normalize_currency("dólar") == "USD"
    assert exchange_tools.normalize_currency("Bitcoin") == "BTC"
    assert exchange_tools.normalize_currency("EUR") == "EUR"


def test_authentication_stops_at_third_failure_even_if_model_repeats_tool():
    class RepeatingAuthModel:
        def invoke(self, _conversation):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "autenticar_cliente",
                        "args": {"cpf": "00000000000", "data_nascimento": "01/01/2000"},
                        "id": "auth-failure",
                        "type": "tool_call",
                    }
                ],
            )

    state = _new_session_state()
    state["messages"] = [HumanMessage(content="Quero me autenticar")]
    state["auth_attempts"] = 2
    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)

    result = orchestrator._call_agent_with_tools(
        TRIAGE_PROMPT, RepeatingAuthModel(), state, "triage"
    )

    assert result["auth_attempts"] == 3
    assert result["is_finished"] is True
    assert result["active_agent"] == "ended"
