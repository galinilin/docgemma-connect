"""AgentState for DocGemma v3 agent graph.

7-node architecture with binary intent classification and reactive tool loop.
Empirically grounded in 856 experiments on MedGemma 4B.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class ExtractedEntities(TypedDict):
    """Pre-extracted entities from deterministic input assembly."""

    patient_ids: list[str]
    drug_mentions: list[str]
    action_verbs: list[str]
    has_image: bool


class ToolResult(TypedDict, total=False):
    """Single tool execution result."""

    tool_name: str
    tool_label: str  # Clinician-facing label (e.g. "Drug Safety Report")
    args: dict[str, Any]
    result: dict[str, Any]
    formatted_result: str  # Clinician-friendly formatted string
    error: Optional[str]
    error_type: Optional[str]  # Category for routing (timeout, not_found, etc.)
    success: bool  # Required by agent_runner.py


class AgentState(TypedDict, total=False):
    """LangGraph state for the v3 agent graph.

    ~20 fields (down from v2's 40+).  Flows through 7 nodes:
    INPUT_ASSEMBLY -> INTENT_CLASSIFY -> TOOL_SELECT -> TOOL_EXECUTE ->
    RESULT_CLASSIFY -> DETERMINISTIC_ROUTER -> SYNTHESIZE
    """

    # ── Input ──
    user_query: str
    conversation_history: list[dict[str, str]]
    image_data: Optional[bytes]
    extracted_entities: ExtractedEntities
    image_findings: Optional[str]
    previous_image_findings: Optional[str]  # Carried from prior turn for continuity

    # ── Intent Classification (Node 2) ──
    intent: str  # "DIRECT" | "TOOL_NEEDED"
    task_summary: str  # Clinical framing ~50 words
    suggested_tool: Optional[str]  # Non-binding hint for TOOL_SELECT

    # ── Tool Loop (Nodes 3-6) ──
    current_tool: Optional[str]
    current_args: Optional[dict[str, Any]]
    tool_results: Annotated[list[ToolResult], operator.add]  # Accumulates
    step_count: int  # Number of tool loop iterations completed

    # ── Result Classification (Node 5) ──
    last_result_classification: Optional[str]  # quality enum value
    last_result_summary: Optional[str]

    # ── Error Handling (Node 5a) ──
    error_messages: list[str]  # Pre-formatted clinician-safe strings
    clarification_request: Optional[str]  # If ask_user triggered

    # ── Internal (interrupt/approval contract with agent_runner.py) ──
    _planned_tool: Optional[str]
    _planned_args: Optional[dict[str, Any]]

    # ── Session context (from frontend) ──
    session_patient_id: Optional[str]       # From frontend patient selector
    tool_calling_enabled: Optional[bool]    # False = force DIRECT route
    patient_context: Optional[str]          # Pre-fetched chart summary for selected patient

    # ── Preliminary Thinking (optional pre-reasoning step) ──
    thinking_enabled: Optional[bool]        # From frontend toggle
    preliminary_thinking_text: Optional[str]  # Free-form reasoning output

    # ── Output (Node 7) ──
    final_response: Optional[str]
    model_thinking: Optional[str]  # Raw thinking text captured from <unused94>...<unused95>


# Backward compatibility alias
DocGemmaState = AgentState

# v2 compat stubs — not used in v3 but keeps old imports alive
Subtask = dict
ConversationMessage = dict
