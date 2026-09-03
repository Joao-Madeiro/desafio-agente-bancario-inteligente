from langchain_core.messages import AIMessage
from fastapi.testclient import TestClient

import src.api.main as main


def test_session_cookie_round_trip_preserves_authenticated_state():
    state = main._new_session_state()
    state.update(
        {
            "authenticated": True,
            "client_cpf": "12345678900",
            "client_name": "Juliana Silva",
            "active_agent": "credit",
        }
    )

    restored = main._decode_session_cookie(main._encode_session_cookie(state))

    assert restored is not None
    assert restored["authenticated"] is True
    assert restored["client_cpf"] == "12345678900"
    assert restored["active_agent"] == "credit"


def test_api_restores_session_after_in_memory_store_is_lost(monkeypatch):
    seen_states = []

    class FakeOrchestrator:
        def process_message(self, state):
            seen_states.append(state["authenticated"])
            return {
                "messages": [AIMessage(content="Resposta")],
                "active_agent": "credit",
                "authenticated": True,
                "client_cpf": "12345678900",
                "client_name": "Juliana Silva",
                "request_auth_modal": False,
            }

    monkeypatch.setattr(main, "get_orchestrator", lambda: FakeOrchestrator())
    main.sessions.clear()
    client = TestClient(main.app)
    session_id = "stateless-vercel-test"

    first = client.post(
        "/api/chat", json={"session_id": session_id, "message": "autenticar"}
    )
    assert first.status_code == 200
    assert first.json()["authenticated"] is True

    # A new Vercel instance starts with an empty in-memory dictionary.
    main.sessions.clear()
    second = client.post(
        "/api/chat", json={"session_id": session_id, "message": "qual meu limite?"}
    )

    assert second.status_code == 200
    assert second.json()["authenticated"] is True
    assert seen_states == [False, True]


def test_reset_accepts_session_id_from_json_and_resets_cookie():
    client = TestClient(main.app)
    session_id = "reset-vercel-test"
    main.sessions[session_id] = main._new_session_state()
    main.sessions[session_id]["authenticated"] = True

    result = client.post("/api/reset", json={"session_id": session_id})

    assert result.status_code == 200
    assert result.json()["session_id"] == session_id
    cookie_name = main._session_cookie_name(session_id)
    restored = main._decode_session_cookie(client.cookies.get(cookie_name))
    assert restored is not None
    assert restored["authenticated"] is False
