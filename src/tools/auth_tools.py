from langchain_core.tools import tool
from src.database.csv_manager import csv_manager

@tool
def autenticar_cliente(cpf: str, data_nascimento: str) -> str:
    """Autentica o cliente e inicia o fluxo de atendimento autenticado do Madeiro Bank.
    Chame esta ferramenta assim que o cliente informar, na conversa ou pelo modal,
    o CPF e a data de nascimento. Ela valida os dados contra a base de clientes
    (clientes.csv) e retorna o status da autenticação com as informações cadastrais
    do cliente."""
    success, client, error_msg = csv_manager.validate_client(cpf, data_nascimento)
    if not success:
        return f"FALHA_AUTENTICACAO: {error_msg}"
    
    return (
        f"AUTENTICACAO_SUCESSO: Cliente {client.nome} autenticado com sucesso. "
        f"CPF: {client.cpf}, Limite Atual: R$ {client.limite_credito:.2f}, Score Atual: {client.score_credito}."
    )

@tool
def solicitar_dados_autenticacao() -> str:
    """Exibe na interface do cliente um formulário modal para coleta do CPF e da
    Data de Nascimento. Use esta ferramenta sempre que precisar coletar ou
    corrigir esses dados para autenticação: a interface exibe um botão no chat;
    o modal é aberto somente quando o cliente clicar nesse botão e os dados
    preenchidos chegam à conversa como uma mensagem do cliente."""
    return "SOLICITAR_DADOS_AUTENTICACAO: Exibir no chat o botão para preencher CPF e Data de Nascimento."
