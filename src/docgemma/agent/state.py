"""Agent state definition (v2: 4-way triage architecture)."""

from typing import TypedDict


class Subtask(TypedDict):
    """A decomposed subtask from the user query."""

    intent: str
    requires_tool: str | None
    context: str


class ToolResult(TypedDict):
    """Result from a tool execution."""

    tool_name: str
    arguments: dict
    result: dict
    success: bool


class ConversationMessage(TypedDict):
    """A message in the conversation history."""

    role: str  # "user" | "assistant"
    content: str


class DocGemmaState(TypedDict, total=False):
    """State object for the DocGemma v2 agent pipeline.

    Flows through: image_detection -> clinical_context_assembler -> triage_router
                   -> [direct|lookup|reasoning|multi_step] -> synthesize_response
    """

    # === Turn-level inputs ===
    user_input: str
    image_present: bool
    image_data: bytes | None

    # === Multi-turn context ===
    conversation_history: list[ConversationMessage]

    # === Clinical context (assembled before triage) ===
    clinical_context: dict | None

    # === Routing (4-way triage) ===
    triage_route: str | None  # "direct" | "lookup" | "reasoning" | "multi_step"
    triage_tool: str | None  # Tool name from triage (LOOKUP only)
    triage_query: str | None  # Query from triage (LOOKUP only)

    # === Reasoning path ===
    reasoning: str | None  # From thinking_mode
    reasoning_tool_needs: dict | None  # From extract_tool_needs: {tool, query} or None
    reasoning_continuation: str | None  # From reasoning_continuation node

    # === Agentic loop state (max 5 subtasks) ===
    subtasks: list[Subtask]
    current_subtask_index: int
    tool_results: list[ToolResult]
    loop_iterations: int
    tool_retries: int
    last_result_status: str  # "success"|"error"|"needs_more_action"|"needs_user_input"|"done"|"continue"

    # === Tool execution (internal) ===
    _planned_tool: str | None
    _planned_args: dict | None

    # === Validation ===
    validation_error: str | None

    # === Error handling ===
    error_strategy: str | None  # "retry_same" | "retry_reformulate" | "skip_subtask"

    # === Control flags ===
    needs_user_input: bool
    missing_info: str | None

    # === Output ===
    final_response: str | None
