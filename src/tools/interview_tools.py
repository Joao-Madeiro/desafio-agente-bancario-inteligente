from typing import Any

from langchain_core.tools import tool
from src.database.csv_manager import csv_manager
from src.tools.credit_tools import parse_money


def _normalize_employment(value: object) -> str:
    normalized = str(value).strip().lower()
    aliases = {
        "autonomo": "autônomo",
        "autônoma": "autônomo",
        "autônomo": "autônomo",
        "formal": "formal",
        "desempregado": "desempregado",
        "desempregada": "desempregado",
    }
    if normalized not in aliases:
        raise ValueError("O tipo de emprego deve ser formal, autônomo ou desempregado.")
    return aliases[normalized]


def _normalize_dependents(value: object) -> int:
    normalized = str(value).strip().lower()
    if normalized in {"3+", "3 +", "3 ou mais", "mais de 3"}:
        return 3
    dependents = int(value)
    if dependents < 0:
        raise ValueError("O número de dependentes não pode ser negativo.")
    return dependents


def _normalize_debts(value: object) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"sim", "s", "true", "possui", "tenho"}:
        return "sim"
    if normalized in {"não", "nao", "n", "false", "não tenho", "nao tenho"}:
        return "não"
    raise ValueError("Informe se possui dívidas ativas com sim ou não.")

def calculate_score(
    renda_mensal: float,
    tipo_emprego: str,
    despesas: float,
    num_dependentes: int,
    tem_dividas: str,
) -> int:
    peso_renda = 30.0
    
    emprego_map = {
        "formal": 300,
        "autônomo": 200,
        "desempregado": 0,
    }
    cleaned_emprego = _normalize_employment(tipo_emprego)
    peso_emprego_val = emprego_map[cleaned_emprego]
    dep_count = _normalize_dependents(num_dependentes)

    if dep_count == 0:
        peso_dep_val = 100
    elif dep_count == 1:
        peso_dep_val = 80
    elif dep_count == 2:
        peso_dep_val = 60
    else:
        peso_dep_val = 30

    cleaned_dividas = _normalize_debts(tem_dividas)
    if cleaned_dividas == "sim":
        peso_dividas_val = -100
    else:
        peso_dividas_val = 100

    renda = parse_money(renda_mensal)
    desp = parse_money(despesas)
    if renda < 0 or desp < 0:
        raise ValueError("Renda e despesas não podem ser negativas.")

    razao_renda_despesa = renda / (desp + 1.0)
    score_bruto = (razao_renda_despesa * peso_renda) + peso_emprego_val + peso_dep_val + peso_dividas_val
    score_final = max(0, min(1000, round(score_bruto)))

    return int(score_final)

@tool
def processar_entrevista_e_atualizar_score(
    cpf: str,
    renda_mensal: Any,
    tipo_emprego: Any,
    despesas: Any,
    num_dependentes: Any,
    tem_dividas: Any,
) -> str:
    """Calcula o novo score de crédito ponderado a partir das respostas da entrevista financeira
    e atualiza a base de dados de clientes do Madeiro Bank."""
    client = csv_manager.find_client_by_cpf(cpf)
    if not client:
        return "ERRO: Cliente não encontrado na base de dados para atualização de score."

    try:
        novo_score = calculate_score(
            renda_mensal=renda_mensal,
            tipo_emprego=tipo_emprego,
            despesas=despesas,
            num_dependentes=num_dependentes,
            tem_dividas=tem_dividas,
        )
    except (TypeError, ValueError):
        return (
            "ERRO: Não foi possível calcular o score. Informe renda e despesas válidas, "
            "um tipo de emprego permitido, dependentes não negativos e dívidas como sim ou não."
        )

    score_antigo = client.score_credito

    success = csv_manager.update_client_score(client.cpf, novo_score)
    if not success:
        return "ERRO: Falha técnica ao salvar novo score no banco de dados."

    score_rule = csv_manager.get_score_rule_for_score(novo_score)
    limite_teto = score_rule.limite_maximo_permitido if score_rule else 0.0

    return (
        f"ENTREVISTA_CONCLUIDA: Entrevista financeira finalizada com sucesso. "
        f"Score anterior: {score_antigo} pontos -> Novo Score calculado: {novo_score} pontos "
        f"({score_rule.descricao_faixa if score_rule else ''}). "
        f"Limite máximo elegível com o novo score: R$ {limite_teto:.2f}."
    )
