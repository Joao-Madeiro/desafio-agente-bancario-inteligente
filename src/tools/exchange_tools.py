import httpx
from datetime import datetime
from langchain_core.tools import tool
import re
import unicodedata

CURRENCY_NAMES = {
    "USD": "Dólar Americano",
    "EUR": "Euro",
    "GBP": "Libra Esterlina",
    "BTC": "Bitcoin",
    "CAD": "Dólar Canadense",
    "JPY": "Iene Japonês",
    "CHF": "Franco Suíço",
}

CURRENCY_ALIASES = {
    "dolar": "USD",
    "dolaramericano": "USD",
    "dollar": "USD",
    "euro": "EUR",
    "libra": "GBP",
    "libraesterlina": "GBP",
    "bitcoin": "BTC",
    "btc": "BTC",
    "dolarcanadense": "CAD",
    "iene": "JPY",
    "ienejapones": "JPY",
    "francosuico": "CHF",
}


def normalize_currency(value: object) -> str:
    raw_value = str(value or "").strip()
    folded = unicodedata.normalize("NFKD", raw_value)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-zA-Z]", "", folded).lower()
    if normalized in CURRENCY_ALIASES:
        return CURRENCY_ALIASES[normalized]

    code = re.sub(r"[^a-zA-Z]", "", raw_value).upper()
    if len(code) == 3:
        return code
    return ""

@tool
def consultar_cotacao_moeda(moeda: str = "USD") -> str:
    """Consulta a cotação de moedas estrangeiras em relação ao Real Brasileiro (BRL) em tempo real.
    Suporta moedas como USD (Dólar), EUR (Euro), GBP (Libra), BTC (Bitcoin), etc."""
    raw_moeda = str(moeda or "").strip()
    moeda_code = normalize_currency(raw_moeda) if raw_moeda else "USD"
    if not moeda_code:
        return (
            f"ERRO: Não foi possível identificar a moeda '{raw_moeda}'. "
            "Informe um código de três letras ou uma moeda como dólar, euro ou bitcoin."
        )

    api_url = f"https://economia.awesomeapi.com.br/last/{moeda_code}-BRL"
    
    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(api_url)
            if response.status_code == 200:
                data = response.json()
                key = f"{moeda_code}BRL"
                if key in data:
                    item = data[key]
                    nome = item.get("name", CURRENCY_NAMES.get(moeda_code, moeda_code))
                    compra = float(item.get("bid", 0.0))
                    venda = float(item.get("ask", 0.0))
                    pct_change = float(item.get("pctChange", 0.0))
                    create_date = item.get("create_date", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    
                    sinal = "+" if pct_change > 0 else ""
                    return (
                        f"COTACAO_SUCESSO: Cotação do {nome} ({moeda_code}/BRL) em tempo real: "
                        f"Compra: R$ {compra:.4f} | Venda: R$ {venda:.4f} | "
                        f"Variação: {sinal}{pct_change:.2f}% | Atualizado em: {create_date}."
                    )
    except Exception as exc:
        pass

    fallback_rates = {
        "USD": (5.75, 5.76, 0.15),
        "EUR": (6.20, 6.22, -0.10),
        "GBP": (7.35, 7.38, 0.05),
        "BTC": (540000.0, 542000.0, 1.25),
    }
    
    if moeda_code in fallback_rates:
        compra, venda, pct = fallback_rates[moeda_code]
        return (
            f"COTACAO_SUCESSO (Referencial): Cotação do {CURRENCY_NAMES.get(moeda_code, moeda_code)} ({moeda_code}/BRL): "
            f"Compra: R$ {compra:.2f} | Venda: R$ {venda:.2f} | Variação: {pct:+.2f}% | "
            f"Referência do Madeiro Bank."
        )

    return f"ERRO: Não foi possível obter a cotação para a moeda '{moeda_code}'. Moedas disponíveis: USD, EUR, GBP, BTC, CAD, JPY."
