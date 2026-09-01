import pytest
from pathlib import Path
from src.database.csv_manager import CSVManager, clean_cpf, parse_date

def test_clean_cpf():
    assert clean_cpf("123.456.789-00") == "12345678900"
    assert clean_cpf("12345678900") == "12345678900"
    assert clean_cpf("123 456 789 00") == "12345678900"

def test_parse_date():
    assert parse_date("15/05/1990") == "1990-05-15"
    assert parse_date("1990-05-15") == "1990-05-15"
    assert parse_date("15-05-1990") == "1990-05-15"
    assert parse_date("invalid-date") is None

def test_csv_manager_auth_and_crud(tmp_path: Path):
    clients_file = tmp_path / "clientes.csv"
    requests_file = tmp_path / "solicitacoes.csv"
    score_file = tmp_path / "score.csv"

    manager = CSVManager(
        clients_path=clients_file,
        requests_path=requests_file,
        score_path=score_file,
    )

    initial_clients = manager.get_all_clients()
    assert len(initial_clients) == 0

    import pandas as pd
    df = pd.DataFrame([{
        "cpf": "12345678900",
        "nome": "Ana Teste",
        "data_nascimento": "1990-05-15",
        "limite_credito": 2000.0,
        "score_credito": 500,
        "email": "ana@teste.com",
        "telefone": "11999999999",
    }])
    df.to_csv(clients_file, index=False)

    success, client, err = manager.validate_client("123.456.789-00", "15/05/1990")
    assert success is True
    assert client is not None
    assert client.nome == "Ana Teste"
    assert err is None

    success_fail_dob, _, err_dob = manager.validate_client("12345678900", "01/01/1990")
    assert success_fail_dob is False
    assert "não confere" in err_dob

    success_fail_cpf, _, err_cpf = manager.validate_client("99999999999", "15/05/1990")
    assert success_fail_cpf is False
    assert "não localizado" in err_cpf

    assert manager.update_client_score("12345678900", 750) is True
    updated_client = manager.find_client_by_cpf("12345678900")
    assert updated_client.score_credito == 750

    assert manager.update_client_limit("12345678900", 8000.0) is True
    updated_client2 = manager.find_client_by_cpf("12345678900")
    assert updated_client2.limite_credito == 8000.0

    req = manager.record_limit_request("12345678900", 8000.0, 12000.0, "aprovado")
    assert req.status_pedido == "aprovado"
    assert len(manager.get_all_requests()) == 1
