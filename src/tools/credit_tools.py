from langchain_core.tools import tool
from src.database.csv_manager import csv_manager, clean_cpf

@tool
def consultar_limite_credito(cpf: str) -> str:
    """Consulta o limite de crédito disponível e o score atual do cliente autenticado."""
    client = csv_manager.find_client_by_cpf(cpf)
    if not client:
        return "ERRO: Cliente não localizado na base de dados."
    
    return (
        f"Nome: {client.nome} | Limite Atual: R$ {client.limite_credito:.2f} | "
        f"Score de Crédito: {client.score_credito} pontos."
    )

@tool
def processar_solicitacao_aumento_limite(cpf: str, novo_limite_solicitado: float) -> str:
    """Processa um pedido formal de aumento de limite de crédito para o cliente.
    Verifica a compatibilidade com a tabela de score x limite e registra a solicitação."""
    client = csv_manager.find_client_by_cpf(cpf)
    if not client:
        return "ERRO: Cliente não encontrado para processar a solicitação."

    try:
        novo_limite = float(novo_limite_solicitado)
    except (ValueError, TypeError):
        return "ERRO: O valor do novo limite deve ser um número válido."

    if novo_limite <= client.limite_credito:
        return (
            f"SOLICITACAO_INVALIDA: O novo limite solicitado (R$ {novo_limite:.2f}) "
            f"deve ser superior ao limite atual (R$ {client.limite_credito:.2f})."
        )

    score_rule = csv_manager.get_score_rule_for_score(client.score_credito)
    max_permitido = score_rule.limite_maximo_permitido if score_rule else 0.0

    if novo_limite <= max_permitido:
        status = "aprovado"
        csv_manager.update_client_limit(client.cpf, novo_limite)
        csv_manager.record_limit_request(
            cpf=client.cpf,
            limite_atual=client.limite_credito,
            novo_limite_solicitado=novo_limite,
            status_pedido=status,
        )
        return (
            f"SOLICITACAO_APROVADA: Parabéns! Seu pedido de aumento de limite para R$ {novo_limite:.2f} "
            f"foi APROVADO com base no seu score atual ({client.score_credito} pts - {score_rule.descricao_faixa if score_rule else ''}). "
            f"O novo limite já está disponível para uso imediato."
        )
    else:
        status = "rejeitado"
        csv_manager.record_limit_request(
            cpf=client.cpf,
            limite_atual=client.limite_credito,
            novo_limite_solicitado=novo_limite,
            status_pedido=status,
        )
        return (
            f"SOLICITACAO_REJEITADA: A solicitação de aumento para R$ {novo_limite:.2f} foi REJEITADA. "
            f"Com seu score atual de {client.score_credito} pontos ({score_rule.descricao_faixa if score_rule else ''}), "
            f"o limite máximo permitido pela política de crédito é de R$ {max_permitido:.2f}. "
            f"Você pode realizar uma Entrevista de Crédito para reavaliar e tentar elevar o seu score."
        )
