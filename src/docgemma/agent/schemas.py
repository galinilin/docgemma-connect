"""Pydantic schemas for agent LLM nodes (Outlines constrained generation).

V2: 4-way triage, 10 tools, up to 5 subtasks, validation/fix-args support.

Optimized for SLMs (Small Language Models):
- Flat structures only (no nested lists/dicts)
- Explicit fields instead of open dicts
- Short max_length constraints
- Literal types for constrained choices
"""

from typing import Literal

from pydantic import BaseModel, Field


# All 10 tools + none sentinel
ToolName = Literal[
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "search_patient",
    "get_patient_chart",
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
    "analyze_medical_image",
    "none",
]


class TriageDecision(BaseModel):
    """4-way triage: direct / lookup / reasoning / multi_step."""

    route: Literal["direct", "lookup", "reasoning", "multi_step"]
    tool: ToolName | None = None  # Only for "lookup"
    query: str | None = Field(default=None, max_length=128)  # Only for "lookup"


class ThinkingOutput(BaseModel):
    """Chain-of-thought reasoning before decomposition or tool selection."""

    reasoning: str = Field(max_length=512)


class ExtractedToolNeeds(BaseModel):
    """From reasoning chain, identify if a tool call would help."""

    needs_tool: bool = False
    tool: ToolName | None = None
    query: str | None = Field(default=None, max_length=128)


class DecomposedIntentV2(BaseModel):
    """Flat decomposition into 1-5 subtasks. No nested objects."""

    subtask_1: str = Field(max_length=100)
    tool_1: ToolName
    subtask_2: str | None = Field(default=None, max_length=100)
    tool_2: ToolName | None = None
    subtask_3: str | None = Field(default=None, max_length=100)
    tool_3: ToolName | None = None
    subtask_4: str | None = Field(default=None, max_length=100)
    tool_4: ToolName | None = None
    subtask_5: str | None = Field(default=None, max_length=100)
    tool_5: ToolName | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None


class ToolCallV2(BaseModel):
    """Tool selection with explicit argument fields for all 10 tools.

    Field order matters for SLM generation: patient_id is early so the model
    fills it before falling into a null pattern for irrelevant fields.
    """

    tool_name: ToolName
    # Patient/EHR (early — REQUIRED for EHR tools, model must decide early)
    patient_id: str | None = Field(default=None, max_length=64)
    # Universal
    query: str | None = Field(default=None, max_length=128)
    # Drug-specific
    drug_name: str | None = Field(default=None, max_length=64)
    drug_list: str | None = Field(default=None, max_length=128)
    # Patient identifiers
    name: str | None = Field(default=None, max_length=64)
    dob: str | None = Field(default=None, max_length=10)
    # Allergy
    substance: str | None = Field(default=None, max_length=64)
    reaction: str | None = Field(default=None, max_length=64)
    severity: str | None = Field(default=None, max_length=16)
    # Prescription
    medication_name: str | None = Field(default=None, max_length=64)
    dosage: str | None = Field(default=None, max_length=32)
    frequency: str | None = Field(default=None, max_length=32)
    # Clinical note
    note_text: str | None = Field(default=None, max_length=512)
    note_type: str | None = Field(default=None, max_length=32)


class FixedArgs(BaseModel):
    """Corrected arguments after validation failure.

    Field order matches ToolCallV2 (patient_id early).
    """

    patient_id: str | None = Field(default=None, max_length=64)
    query: str | None = Field(default=None, max_length=128)
    drug_name: str | None = Field(default=None, max_length=64)
    drug_list: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, max_length=64)
    dob: str | None = Field(default=None, max_length=10)
    substance: str | None = Field(default=None, max_length=64)
    reaction: str | None = Field(default=None, max_length=64)
    severity: str | None = Field(default=None, max_length=16)
    medication_name: str | None = Field(default=None, max_length=64)
    dosage: str | None = Field(default=None, max_length=32)
    frequency: str | None = Field(default=None, max_length=32)
    note_text: str | None = Field(default=None, max_length=512)
    note_type: str | None = Field(default=None, max_length=32)
