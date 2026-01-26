from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    Represents the state of our agent.
    """
    input: str
    persona: str
    is_emergency: bool
    is_complex: bool
    allowed_tools: List[str]
    tool_invocations: List
    messages: Annotated[list, operator.add]
    final_response: str
