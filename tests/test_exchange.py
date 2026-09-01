import pytest
from src.tools.exchange_tools import consultar_cotacao_moeda

def test_exchange_usd():
    res = consultar_cotacao_moeda.invoke({"moeda": "USD"})
    assert "COTACAO_SUCESSO" in res
    assert "USD/BRL" in res or "Dólar" in res

def test_exchange_eur():
    res = consultar_cotacao_moeda.invoke({"moeda": "EUR"})
    assert "COTACAO_SUCESSO" in res

def test_exchange_unknown_currency():
    res = consultar_cotacao_moeda.invoke({"moeda": "XYZ"})
    assert "ERRO" in res or "COTACAO_SUCESSO" in res
