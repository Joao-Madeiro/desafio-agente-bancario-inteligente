import pytest
from src.tools.credit_tools import consultar_limite_credito, processar_solicitacao_aumento_limite
from src.database.csv_manager import csv_manager

def test_credit_consultation():
    # Ana Silva possui score 450 e limite 2500 inicial
    res = consultar_limite_credito.invoke({"cpf": "12345678900"})
    assert "Ana Silva" in res
    assert "R$ 2500.00" in res

def test_credit_increase_approved():
    # Score 820 (Carlos Souza) permite até R$ 50.000,00
    res = processar_solicitacao_aumento_limite.invoke({
        "cpf": "98765432111",
        "novo_limite_solicitado": 20000.0,
    })
    assert "SOLICITACAO_APROVADA" in res
    assert "R$ 20000.00" in res

def test_credit_increase_rejected_low_score():
    # Score 210 (Mariana Oliveira) permite até R$ 1.000,00. Solicitar R$ 5.000,00 deve ser rejeitado
    res = processar_solicitacao_aumento_limite.invoke({
        "cpf": "11122233344",
        "novo_limite_solicitado": 5000.0,
    })
    assert "SOLICITACAO_REJEITADA" in res
    assert "Entrevista de Crédito" in res

def test_credit_increase_lower_than_current():
    # Solicitar limite menor que o atual
    res = processar_solicitacao_aumento_limite.invoke({
        "cpf": "12345678900",
        "novo_limite_solicitado": 1000.0,
    })
    assert "SOLICITACAO_INVALIDA" in res
