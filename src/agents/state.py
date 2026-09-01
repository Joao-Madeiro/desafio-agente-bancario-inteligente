from typing import Annotated, Any, Dict, List, Literal, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

AgentType = Literal["triage", "credit", "interview", "exchange", "ended"]

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    active_agent: AgentType
    authenticated: bool
    client_cpf: Optional[str]
    client_name: Optional[str]
    auth_attempts: int
    interview_data: Dict[str, Any]
    is_finished: bool
