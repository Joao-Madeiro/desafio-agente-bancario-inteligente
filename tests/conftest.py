import pytest
import pandas as pd
from pathlib import Path
from src.config import CLIENTS_CSV_PATH, REQUESTS_CSV_PATH, SCORE_LIMIT_CSV_PATH
from src.database.csv_manager import CSVManager, csv_manager

INITIAL_CLIENTS = [
    {
        "cpf": "12345678900",
        "nome": "Ana Silva",
        "data_nascimento": "1990-05-15",
        "limite_credito": 2500.00,
        "score_credito": 450,
        "email": "ana.silva@email.com",
        "telefone": "(11) 98765-4321",
    },
    {
        "cpf": "98765432111",
        "nome": "Carlos Souza",
        "data_nascimento": "1985-10-22",
        "limite_credito": 12000.00,
        "score_credito": 820,
        "email": "carlos.souza@email.com",
        "telefone": "(21) 99876-5432",
    },
    {
        "cpf": "11122233344",
        "nome": "Mariana Oliveira",
        "data_nascimento": "1998-01-03",
        "limite_credito": 800.00,
        "score_credito": 210,
        "email": "mariana.oliveira@email.com",
        "telefone": "(31) 97654-3210",
    },
    {
        "cpf": "55566677788",
        "nome": "Roberto Santos",
        "data_nascimento": "1978-12-19",
        "limite_credito": 4000.00,
        "score_credito": 580,
        "email": "roberto.santos@email.com",
        "telefone": "(41) 98888-7777",
    },
]

@pytest.fixture(autouse=True)
def reset_test_csv_state():
    df_clients = pd.DataFrame(INITIAL_CLIENTS)
    df_clients.to_csv(CLIENTS_CSV_PATH, index=False)

    df_reqs = pd.DataFrame(
        columns=[
            "cpf_cliente",
            "data_hora_solicitacao",
            "limite_atual",
            "novo_limite_solicitado",
            "status_pedido",
        ]
    )
    df_reqs.to_csv(REQUESTS_CSV_PATH, index=False)
    yield
    df_clients.to_csv(CLIENTS_CSV_PATH, index=False)
