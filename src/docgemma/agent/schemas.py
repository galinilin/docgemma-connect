"""Pydantic schemas for agent LLM nodes (Outlines constrained generation).

Optimized for SLMs (Small Language Models):
- Flat structures only (no nested lists/dicts)
- Explicit fields instead of open dicts
- Short max_length constraints
- Literal types for constrained choices
"""

from typing import Literal

from pydantic import BaseModel, Field


# Available tools as a Literal type for strict validation
ToolName = Literal[
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "none",
]


class ComplexityClassification(BaseModel):
    """Classify query as direct (answer from knowledge) or complex (needs tools)."""

    complexity: Literal["direct", "complex"]


class ThinkingOutput(BaseModel):
    """Chain-of-thought reasoning before task decomposition."""

    reasoning: str = Field(max_length=256)


class DecomposedIntent(BaseModel):
    """Flat decomposition into 1-2 subtasks. No nested objects."""

    subtask_1: str = Field(description="First subtask description", max_length=100)
    tool_1: ToolName = Field(description="Tool for subtask 1")
    subtask_2: str | None = Field(default=None, description="Second subtask if needed", max_length=100)
    tool_2: ToolName | None = Field(default=None, description="Tool for subtask 2")
    needs_clarification: bool = False
    clarification_question: str | None = None


class ToolCall(BaseModel):
    """Tool selection with explicit argument fields (no dict)."""

    tool_name: ToolName
    # Explicit argument fields instead of dict
    drug_name: str | None = Field(default=None, max_length=64)
    drug_list: str | None = Field(default=None, description="Comma-separated drugs", max_length=128)
    query: str | None = Field(default=None, description="Search query", max_length=128)