"""Agent state definition."""

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
    """State object for the DocGemma agent pipeline.

    Flows through: image_detection -> complexity_router -> decompose_intent
                   -> [plan -> execute -> check]* -> synthesize
    """

    # === Turn-level inputs ===
    user_input: str
    image_present: bool
    image_data: bytes | None

    # === Multi-turn context ===
    conversation_history: list[ConversationMessage]  # Previous messages for context

    # === Routing decisions ===
    complexity: str  # "direct" | "complex"
    reasoning: str | None  # from thinking_mode node

    # === Agentic loop state ===
    subtasks: list[Subtask]
    current_subtask_index: int
    tool_results: list[ToolResult]
    loop_iterations: int
    tool_retries: int
    last_result_status: str  # "success" | "error" | "needs_more_action" | "needs_user_input"

    # === Tool execution (internal) ===
    _planned_tool: str | None  # Tool name from plan_tool
    _planned_args: dict | None  # Tool arguments from plan_tool

    # === Control flags ===
    needs_user_input: bool
    missing_info: str | None

    # === Output ===
    final_response: str | None
