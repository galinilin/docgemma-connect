"""Pydantic schemas for agent LLM nodes (Outlines constrained generation)."""

from typing import Literal

from pydantic import BaseModel, Field


class ComplexityClassification(BaseModel):
    """Output schema for complexity routing."""

    complexity: Literal["direct", "complex"]
    reasoning: str = Field(description="Brief justification for the classification", max_length=128)


class ThinkingOutput(BaseModel):
    """Output schema for thinking mode."""

    reasoning: str = Field(
        ...,
        description="Reasoning and train of thoughts.",
        max_length=384,
    )


class SubtaskSchema(BaseModel):
    """A single subtask from intent decomposition."""

    intent: str = Field(description="Brief description of the subtask", max_length=128)
    requires_tool: str | None = Field(description="Suggested tool name or None")
    context: str = Field(description="Relevant extracted information", max_length=256)


class DecomposedIntent(BaseModel):
    """Output schema for intent decomposition."""

    subtasks: list[SubtaskSchema]
    requires_clarification: bool = False
    clarification_question: str | None = None


class ToolCall(BaseModel):
    """Output schema for tool selection."""

    tool_name: Literal[
        "check_drug_safety",
        "search_medical_literature",
        "check_drug_interactions",
        "find_clinical_trials",
        "get_patient_record",
        "update_patient_record",
        "analyze_medical_image",
        "none",
    ]
    arguments: dict = Field(default_factory=dict)
    reasoning: str = Field(description="Why this tool was selected", max_length=128)