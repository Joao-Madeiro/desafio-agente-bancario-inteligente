from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone

class Cliente(BaseModel):
    cpf: str
    nome: str
    data_nascimento: str
    limite_credito: float
    score_credito: int
    email: Optional[str] = None
    telefone: Optional[str] = None

class SolicitacaoAumento(BaseModel):
    cpf_cliente: str
    data_hora_solicitacao: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    limite_atual: float
    novo_limite_solicitado: float
    status_pedido: Literal["pendente", "aprovado", "rejeitado"]

class ScoreLimiteRegra(BaseModel):
    score_min: int
    score_max: int
    limite_maximo_permitido: float
    descricao_faixa: str

class DadosEntrevista(BaseModel):
    renda_mensal: float
    tipo_emprego: Literal["formal", "autônomo", "desempregado"]
    despesas: float
    num_dependentes: int
    tem_dividas: Literal["sim", "não"]

class CotacaoMoeda(BaseModel):
    moeda_origem: str
    moeda_destino: str = "BRL"
    valor_compra: float
    valor_venda: float
    variacao_percentual: float
    data_hora: str

class MessagePayload(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    agent_name: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ResetRequest(BaseModel):
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    active_agent: str
    previous_agent: Optional[str] = None
    transition_occurred: bool = False
    authenticated: bool
    client_info: Optional[Cliente] = None
    request_auth_modal: bool = False
    is_finished: bool = False

