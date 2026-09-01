from langchain_core.tools import tool

@tool
def encerrar_sessao_atendimento() -> str:
    """Encerra formalmente a sessão de atendimento bancário quando o cliente se despede
    ou solicita o encerramento do atendimento."""
    return "SESSAO_ENCERRADA: Atendimento finalizado com sucesso. O Banco Ágil agradece o seu contato!"

@tool
def transferir_para_agente(agente: str) -> str:
    """Transfere o atendimento para outro agente especializado do Banco Ágil, quando a
    solicitação do cliente estiver fora do seu escopo de atuação. Use esta ferramenta em
    vez de tentar atender o assunto diretamente.
    Parâmetro `agente`: 'credit' (crédito/limites), 'interview' (entrevista de crédito /
    reavaliação de score) ou 'exchange' (câmbio/cotações de moedas)."""
    destinos = {"credit", "interview", "exchange"}
    alvo = str(agente).strip().lower()
    if alvo not in destinos:
        return f"ERRO: destino de transferência inválido '{agente}'. Use: credit, interview ou exchange."
    return f"TRANSFERENCIA:{alvo}"
