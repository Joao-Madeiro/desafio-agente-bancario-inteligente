from langchain_core.tools import tool
from src.database.csv_manager import csv_manager

@tool
def autenticar_cliente(cpf: str, data_nascimento: str) -> str:
    """Autentica o cliente utilizando CPF e data de nascimento na base de dados do Banco Ágil.
    Retorna o status da autenticação e as informações cadastrais do cliente."""
    success, client, error_msg = csv_manager.validate_client(cpf, data_nascimento)
    if not success:
        return f"FALHA_AUTENTICACAO: {error_msg}"
    
    return (
        f"AUTENTICACAO_SUCESSO: Cliente {client.nome} autenticado com sucesso. "
        f"CPF: {client.cpf}, Limite Atual: R$ {client.limite_credito:.2f}, Score Atual: {client.score_credito}."
    )
