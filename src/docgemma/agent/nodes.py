"""Agent node implementations."""

from __future__ import annotations

import functools
import logging
import time
from typing import TYPE_CHECKING, Callable, ParamSpec, TypeVar

from .prompts import (
    CLARIFICATION_PROMPT,
    COMPLEXITY_PROMPT,
    DECOMPOSE_PROMPT,
    DIRECT_RESPONSE_PROMPT,
    PLAN_PROMPT,
    SYNTHESIS_PROMPT,
    THINKING_PROMPT,
)
from .schemas import ComplexityClassification, DecomposedIntent, ThinkingOutput, ToolCall
from .state import DocGemmaState, Subtask, ToolResult

if TYPE_CHECKING:
    from ..protocols import DocGemmaProtocol

logger = logging.getLogger(__name__)

# =============================================================================
# Timing Decorator
# =============================================================================

P = ParamSpec("P")
T = TypeVar("T")


def timed_node(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to log elapsed time for node execution."""

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info(f"[NODE] {func.__name__} starting...")
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"[NODE] {func.__name__} completed in {elapsed_ms:.1f}ms")

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info(f"[NODE] {func.__name__} starting...")
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"[NODE] {func.__name__} completed in {elapsed_ms:.1f}ms")

    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    return sync_wrapper  # type: ignore

# =============================================================================
# Constants
# =============================================================================

MAX_ITERATIONS_PER_SUBTASK = 3
MAX_TOOL_RETRIES = 3
MAX_SUBTASKS = 5

SUPPORTED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/dicom",
    "application/dicom",
}

AVAILABLE_TOOLS = [
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "get_patient_record",
    "update_patient_record",
    "analyze_medical_image",
]


# =============================================================================
# Node 1: Image Detection (Pure Code)
# =============================================================================


@timed_node
def image_detection(state: DocGemmaState) -> DocGemmaState:
    """Detect if medical images are attached to the request.

    This is pure code - no LLM call. Image analysis happens later via tool.
    """
    # For now, just check if image_data was provided in the initial state
    # In production, this would inspect request attachments
    image_present = state.get("image_data") is not None

    return {
        **state,
        "image_present": image_present,
    }


# =============================================================================
# Node 2: Complexity Router (LLM + Outlines)
# =============================================================================


@timed_node
def complexity_router(state: DocGemmaState, model: DocGemmaProtocol) -> DocGemmaState:
    """Route query to direct answer or complex processing pipeline."""
    # Image attached = always complex
    if state.get("image_present"):
        return {**state, "complexity": "complex"}

    prompt = COMPLEXITY_PROMPT.format(
        user_input=state["user_input"],
        image_present=state.get("image_present", False),
    )

    result = model.generate_outlines(prompt, ComplexityClassification)
    return {**state, "complexity": result.complexity}


# =============================================================================
# Node 3: Thinking Mode (LLM + Outlines)
# =============================================================================


@timed_node
def thinking_mode(state: DocGemmaState, model: DocGemmaProtocol) -> DocGemmaState:
    """Generate reasoning for complex queries before decomposition."""
    prompt = THINKING_PROMPT.format(user_input=state["user_input"])
    result = model.generate_outlines(prompt, ThinkingOutput, max_new_tokens=512)
    return {**state, "reasoning": result.reasoning}


# =============================================================================
# Node 4: Decompose Intent (LLM + Outlines)
# =============================================================================


@timed_node
def decompose_intent(state: DocGemmaState, model: DocGemmaProtocol) -> DocGemmaState:
    """Decompose complex query into subtasks."""
    prompt = DECOMPOSE_PROMPT.format(
        user_input=state["user_input"],
        image_present=state.get("image_present", False),
        reasoning=state.get("reasoning", "No prior reasoning."),
        max_subtasks=MAX_SUBTASKS,
    )

    result = model.generate_outlines(prompt, DecomposedIntent, max_new_tokens=1024)

    # Handle clarification needed
    if result.requires_clarification:
        return {
            **state,
            "needs_user_input": True,
            "missing_info": result.clarification_question,
            "subtasks": [],
        }

    # Convert to state format
    subtasks: list[Subtask] = [
        {"intent": s.intent, "requires_tool": s.requires_tool, "context": s.context}
        for s in result.subtasks[:MAX_SUBTASKS]
    ]

    return {
        **state,
        "subtasks": subtasks,
        "current_subtask_index": 0,
        "tool_results": [],
        "loop_iterations": 0,
        "tool_retries": 0,
    }


# =============================================================================
# Node 5: Plan Tool (LLM + Outlines)
# =============================================================================


@timed_node
def plan_tool(state: DocGemmaState, model: DocGemmaProtocol) -> DocGemmaState:
    """Select tool for current subtask."""
    idx = state.get("current_subtask_index", 0)
    subtasks = state.get("subtasks", [])

    if not subtasks or idx >= len(subtasks):
        return {**state, "last_result_status": "success"}

    subtask = subtasks[idx]

    # Format previous results
    prev_results = state.get("tool_results", [])
    prev_str = "None" if not prev_results else "\n".join(
        f"- {r['tool_name']}: {r['success']}" for r in prev_results
    )

    prompt = PLAN_PROMPT.format(
        intent=subtask["intent"],
        context=subtask["context"],
        suggested_tool=subtask.get("requires_tool", "unknown"),
        previous_results=prev_str,
        tools=", ".join(AVAILABLE_TOOLS),
    )

    result = model.generate_outlines(prompt, ToolCall, max_new_tokens=256)

    # Store planned tool call in state for execute node
    return {
        **state,
        "_planned_tool": result.tool_name,
        "_planned_args": result.arguments,
    }


# =============================================================================
# Node 5: Execute Tool (Pure Code - MCP Call)
# =============================================================================


def _truncate_for_log(obj: dict, max_len: int = 200) -> str:
    """Truncate object representation for logging."""
    import json

    try:
        s = json.dumps(obj, default=str)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


@timed_node
async def execute_tool(state: DocGemmaState, tool_executor) -> DocGemmaState:
    """Execute the planned tool call.

    Args:
        state: Current agent state
        tool_executor: Async callable that executes tools by name
    """
    tool_name = state.get("_planned_tool")
    tool_args = state.get("_planned_args", {})

    if not tool_name or tool_name == "none":
        logger.info("[TOOL] No tool needed, skipping execution")
        return {
            **state,
            "last_result_status": "success",
            "_planned_tool": None,
            "_planned_args": None,
        }

    logger.info(f"[TOOL] Executing: {tool_name}")
    logger.info(f"[TOOL] Arguments: {_truncate_for_log(tool_args)}")

    start = time.perf_counter()
    try:
        result = await tool_executor(tool_name, tool_args)
        elapsed_ms = (time.perf_counter() - start) * 1000

        tool_result: ToolResult = {
            "tool_name": tool_name,
            "arguments": tool_args,
            "result": result,
            "success": not result.get("error"),
        }

        tool_results = state.get("tool_results", [])
        tool_results.append(tool_result)

        status = "success" if tool_result["success"] else "error"

        logger.info(f"[TOOL] {tool_name} completed in {elapsed_ms:.1f}ms - {status.upper()}")
        logger.info(f"[TOOL] Result: {_truncate_for_log(result)}")

        return {
            **state,
            "tool_results": tool_results,
            "last_result_status": status,
            "_planned_tool": None,
            "_planned_args": None,
        }

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000

        tool_result: ToolResult = {
            "tool_name": tool_name,
            "arguments": tool_args,
            "result": {"error": str(e)},
            "success": False,
        }
        tool_results = state.get("tool_results", [])
        tool_results.append(tool_result)

        logger.error(f"[TOOL] {tool_name} failed in {elapsed_ms:.1f}ms - ERROR: {e}")

        return {
            **state,
            "tool_results": tool_results,
            "last_result_status": "error",
            "_planned_tool": None,
            "_planned_args": None,
        }


# =============================================================================
# Node 6: Check Result (Pure Code)
# =============================================================================


@timed_node
def check_result(state: DocGemmaState) -> DocGemmaState:
    """Check tool result and update loop control state."""
    status = state.get("last_result_status", "success")
    iterations = state.get("loop_iterations", 0)
    retries = state.get("tool_retries", 0)
    idx = state.get("current_subtask_index", 0)
    subtasks = state.get("subtasks", [])

    if status == "error":
        if retries < MAX_TOOL_RETRIES:
            return {**state, "tool_retries": retries + 1}
        # Max retries exceeded, move on
        status = "success"

    if status == "success":
        # Check for more subtasks
        if idx < len(subtasks) - 1:
            return {
                **state,
                "current_subtask_index": idx + 1,
                "loop_iterations": 0,
                "tool_retries": 0,
                "last_result_status": "continue",
            }
        # All subtasks done
        return {**state, "last_result_status": "done"}

    if status == "needs_more_action":
        if iterations < MAX_ITERATIONS_PER_SUBTASK:
            return {
                **state,
                "loop_iterations": iterations + 1,
                "last_result_status": "continue",
            }
        # Max iterations, move on
        return {**state, "last_result_status": "done"}

    return {**state, "last_result_status": "done"}


# =============================================================================
# Node 7: Response Synthesis (LLM)
# =============================================================================


def _format_tool_results(results: list[ToolResult]) -> str:
    """Format tool results for synthesis prompt."""
    if not results:
        return "No tools were called."

    lines = []
    for r in results:
        status = "SUCCESS" if r["success"] else "FAILED"
        lines.append(f"[{r['tool_name']}] ({status})")
        if r["success"]:
            # Truncate large results
            result_str = str(r["result"])
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            lines.append(f"  {result_str}")
        else:
            lines.append(f"  Error: {r['result'].get('error', 'Unknown error')}")
    return "\n".join(lines)


@timed_node
def synthesize_response(state: DocGemmaState, model: DocGemmaProtocol) -> DocGemmaState:
    """Generate final response from accumulated context."""
    # Handle clarification request
    if state.get("needs_user_input"):
        prompt = CLARIFICATION_PROMPT.format(
            user_input=state["user_input"],
            missing_info=state.get("missing_info", "specific details"),
        )
        response = model.generate(prompt, max_new_tokens=256)
        return {**state, "final_response": response}

    # Normal synthesis
    tool_results = state.get("tool_results", [])
    prompt = SYNTHESIS_PROMPT.format(
        user_input=state["user_input"],
        tool_results=_format_tool_results(tool_results),
    )

    response = model.generate(prompt, max_new_tokens=512)
    return {**state, "final_response": response}


@timed_node
def direct_response(state: DocGemmaState, model: DocGemmaProtocol) -> DocGemmaState:
    """Generate direct response without tools (for simple queries)."""
    prompt = DIRECT_RESPONSE_PROMPT.format(user_input=state["user_input"])
    response = model.generate(prompt, max_new_tokens=256)
    return {**state, "final_response": response}
