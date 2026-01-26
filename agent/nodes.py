import re
from .state import AgentState


def emergency_check(state: AgentState):
    """
    Checks for emergency keywords in the user input.
    """
    emergency_keywords = [
        "suicide",
        "kill myself",
        "chest pain",
        "bleeding",
        "heart attack",
    ]
    for keyword in emergency_keywords:
        if re.search(keyword, state["input"], re.IGNORECASE):
            state["is_emergency"] = True
            state[
                "final_response"
            ] = "If you are experiencing a medical emergency, please call your local emergency number immediately."
            return state
    state["is_emergency"] = False
    return state


def persona_router(state: AgentState):
    """
    Sets the persona for the agent based on user input.
    """
    # Simple keyword-based routing for now.
    if "doctor" in state["input"].lower() or "expert" in state["input"].lower():
        state["persona"] = "expert"
    else:
        state["persona"] = "patient"
    return state


def complexity_router(state: AgentState):
    """
    Determises if the user input requires reasoning or a direct response.
    """
    # Simple keyword-based routing for now.
    complex_keywords = ["compare", "diagnose", "what is", "explain"]
    for keyword in complex_keywords:
        if keyword in state["input"].lower():
            state["is_complex"] = True
            return state
    state["is_complex"] = False
    return state


def tool_node(state: AgentState):
    """
    Executes the appropriate tool based on the agent's state.
    """
    # This is a placeholder for now.
    # In the future, this will call the appropriate tool based on the persona and input.
    state["final_response"] = "This is a placeholder for the tool node."
    return state


def synthesis_node(state: AgentState):
    """
    Generates the final response to the user.
    """
    # If the emergency check already set a final response, we'll use that.
    if state.get("final_response"):
        return state

    # This is a placeholder for now.
    # In the future, this will synthesize a response based on the tool output.
    state["final_response"] = "This is a placeholder for the synthesis node."
    return state
