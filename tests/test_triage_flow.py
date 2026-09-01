import pytest
from src.database.csv_manager import csv_manager
from src.tools.auth_tools import autenticar_cliente
from src.tools.session_tools import encerrar_sessao_atendimento, transferir_para_agente

def test_triage_authentication_success():
    res = autenticar_cliente.invoke({"cpf": "12345678900", "data_nascimento": "15/05/1990"})
    assert "AUTENTICACAO_SUCESSO" in res
    assert "Ana Silva" in res

def test_triage_authentication_failure():
    res = autenticar_cliente.invoke({"cpf": "12345678900", "data_nascimento": "01/01/2000"})
    assert "FALHA_AUTENTICACAO" in res

def test_session_termination_tool():
    res = encerrar_sessao_atendimento.invoke({})
    assert "SESSAO_ENCERRADA" in res

def test_transfer_tool():
    assert "TRANSFERENCIA:credit" in transferir_para_agente.invoke({"agente": "credit"})
    assert "TRANSFERENCIA:interview" in transferir_para_agente.invoke({"agente": "interview"})
    assert "TRANSFERENCIA:exchange" in transferir_para_agente.invoke({"agente": "exchange"})
    assert "ERRO" in transferir_para_agente.invoke({"agente": "triage"})
