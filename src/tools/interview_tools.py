import re
from langchain_core.tools import tool
from src.database.csv_manager import csv_manager

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
        "autonomo": 200,
        "desempregado": 0,
    }
    cleaned_emprego = str(tipo_emprego).strip().lower()
    peso_emprego_val = emprego_map.get(cleaned_emprego, 100)

    try:
        dep_count = int(num_dependentes)
    except (ValueError, TypeError):
        dep_count = 0

    if dep_count == 0:
        peso_dep_val = 100
    elif dep_count == 1:
        peso_dep_val = 80
    elif dep_count == 2:
        peso_dep_val = 60
    else:
        peso_dep_val = 30

    cleaned_dividas = str(tem_dividas).strip().lower()
    if cleaned_dividas in ["sim", "s", "true", "possui", "tenho"]:
        peso_dividas_val = -100
    else:
        peso_dividas_val = 100

    renda = max(0.0, float(renda_mensal))
    desp = max(0.0, float(despesas))

    razao_renda_despesa = renda / (desp + 1.0)
    score_bruto = (razao_renda_despesa * peso_renda) + peso_emprego_val + peso_dep_val + peso_dividas_val
    score_final = max(0, min(1000, round(score_bruto)))

    return int(score_final)

@tool
def processar_entrevista_e_atualizar_score(
    cpf: str,
    renda_mensal: float,
    tipo_emprego: str,
    despesas: float,
    num_dependentes: int,
    tem_dividas: str,
) -> str:
    """Calcula o novo score de crédito ponderado a partir das respostas da entrevista financeira
    e atualiza a base de dados de clientes do Banco Ágil."""
    client = csv_manager.find_client_by_cpf(cpf)
    if not client:
        return "ERRO: Cliente não encontrado na base de dados para atualização de score."

    score_antigo = client.score_credito
    novo_score = calculate_score(
        renda_mensal=renda_mensal,
        tipo_emprego=tipo_emprego,
        despesas=despesas,
        num_dependentes=num_dependentes,
        tem_dividas=tem_dividas,
    )

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
