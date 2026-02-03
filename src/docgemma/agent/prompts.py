"""Prompt templates for DocGemma agent nodes.

Optimized for SLMs (Small Language Models):
- Direct imperatives, no politeness
- One-shot examples where helpful
- Minimal context, maximum clarity
- Structure over prose

Temperature Guide:
- 0.0-0.1: Structured output (JSON, classification)
- 0.3-0.4: Focused reasoning
- 0.5-0.6: Natural text generation
"""

from ..tools.registry import get_tools_for_prompt

# =============================================================================
# TEMPERATURE SETTINGS
# =============================================================================

TEMPERATURE = {
    "complexity_router": 0.0,   # Binary classification - deterministic
    "thinking_mode": 0.3,       # Reasoning - focused
    "decompose_intent": 0.1,    # Structured output - very deterministic
    "plan_tool": 0.0,           # Tool selection - deterministic
    "synthesize_response": 0.5, # Free-form text
    "clarification": 0.4,       # Free-form question
    "direct_response": 0.5,     # Free-form answer
}

# =============================================================================
# COMPLEXITY ROUTER (Binary classification)
# =============================================================================

COMPLEXITY_PROMPT = """Classify: DIRECT or COMPLEX?

DIRECT = answer from medical knowledge (definitions, facts, mechanisms)
COMPLEX = needs tools, data lookup, patient records, images

Query: {user_input}"""


# =============================================================================
# THINKING MODE (Chain-of-thought)
# =============================================================================

THINKING_PROMPT = """Analyze this clinical query. What information is needed? What tools might help?

Query: {user_input}"""


# =============================================================================
# INTENT DECOMPOSITION (Flat structure, 1-2 subtasks max)
# =============================================================================

def get_decompose_prompt(user_input: str, reasoning: str) -> str:
    """Generate decomposition prompt with dynamic tool list."""
    tools = get_tools_for_prompt()
    return f"""Decompose into 1-2 tool calls.

Tools:
{tools}

Query: {user_input}

Context: {reasoning}

Return subtask_1, tool_1, and optionally subtask_2, tool_2."""


# Keep static version for backwards compatibility
DECOMPOSE_PROMPT = """Decompose into 1-2 tool calls.

Tools:
{tools}

Query: {user_input}

Context: {reasoning}

Return subtask_1, tool_1, and optionally subtask_2, tool_2."""


# =============================================================================
# TOOL PLANNING (Explicit fields, no dict)
# =============================================================================

def get_plan_prompt(intent: str, suggested_tool: str) -> str:
    """Generate tool planning prompt with dynamic tool list."""
    tools = get_tools_for_prompt()
    return f"""Select tool and arguments.

Task: {intent}
Suggested: {suggested_tool}

Tools:
{tools}

Return tool_name and the appropriate argument field."""


# Keep static version for backwards compatibility
PLAN_PROMPT = """Select tool and arguments.

Task: {intent}
Suggested: {suggested_tool}

Tools:
{tools}

Return tool_name and the appropriate argument field."""


# =============================================================================
# RESPONSE SYNTHESIS
# =============================================================================

SYNTHESIS_PROMPT = """Clinical decision support response.

Query: {user_input}

Tool findings:
{tool_results}

Respond concisely. Use medical abbreviations. Cite sources if available."""


# =============================================================================
# CLARIFICATION REQUEST
# =============================================================================

CLARIFICATION_PROMPT = """Need more information.

Query: {user_input}
Missing: {missing_info}

Ask one specific question."""


# =============================================================================
# DIRECT RESPONSE
# =============================================================================

DIRECT_RESPONSE_PROMPT = """Answer concisely as a clinical decision support system.

{user_input}"""
