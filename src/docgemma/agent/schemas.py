"""Pydantic schemas for Outlines constrained generation (v3).

CRITICAL RULE: In every schema, decision-critical fields come FIRST.
Optional/nullable fields come LAST.  This is load-bearing — reversing
field order drops arg accuracy from 88% to 21% (Part II, Section 20).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Node 2 — Intent Classification
# ─────────────────────────────────────────────────────────────────────────────

class IntentClassification(BaseModel):
    """Binary intent classification.  Decision field FIRST."""

    intent: Literal["DIRECT", "TOOL_NEEDED"]
    task_summary: str = Field(
        description="Brief clinical summary of the user's request (~50 words max)",
    )
    suggested_tool: Optional[str] = Field(
        default=None,
        description="If TOOL_NEEDED, which tool is most likely relevant",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Node 3 Stage 1 — Tool Selection (single field, no nullable distractors)
# ─────────────────────────────────────────────────────────────────────────────

class ToolSelection(BaseModel):
    """Select the appropriate tool.  Single field — no null cascade risk."""

    tool_name: Literal[
        "check_drug_safety",
        "check_drug_interactions",
        "search_medical_literature",
        "find_clinical_trials",
        "search_patient",
        "get_patient_chart",
        "prescribe_medication",
        "add_allergy",
        "save_clinical_note",
        "analyze_medical_image",
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Node 3 Stage 2 — Per-tool argument schemas
#   Required fields first, optional fields last.
# ─────────────────────────────────────────────────────────────────────────────

class DrugSafetyArgs(BaseModel):
    drug_name: str


class DrugInteractionArgs(BaseModel):
    drug_names: list[str] = Field(min_length=2, description="Two or more drug names")


class LiteratureSearchArgs(BaseModel):
    query: str = Field(description="Search query for medical literature")


class ClinicalTrialsArgs(BaseModel):
    condition: str
    status: Optional[str] = None


class PatientSearchArgs(BaseModel):
    name: str


class PatientChartArgs(BaseModel):
    patient_id: str


class PrescribeMedicationArgs(BaseModel):
    patient_id: str
    medication_name: str
    dosage: str
    frequency: str
    notes: Optional[str] = None


class AddAllergyArgs(BaseModel):
    patient_id: str
    substance: str
    reaction: str
    severity: Optional[str] = None


class ClinicalNoteArgs(BaseModel):
    patient_id: str
    note_type: str
    note_text: str


class ImageAnalysisArgs(BaseModel):
    query: str = Field(description="What to look for in the image")


# Mapping: tool_name -> arg schema class
TOOL_ARG_SCHEMAS: dict[str, type[BaseModel]] = {
    "check_drug_safety": DrugSafetyArgs,
    "check_drug_interactions": DrugInteractionArgs,
    "search_medical_literature": LiteratureSearchArgs,
    "find_clinical_trials": ClinicalTrialsArgs,
    "search_patient": PatientSearchArgs,
    "get_patient_chart": PatientChartArgs,
    "prescribe_medication": PrescribeMedicationArgs,
    "add_allergy": AddAllergyArgs,
    "save_clinical_note": ClinicalNoteArgs,
    "analyze_medical_image": ImageAnalysisArgs,
}


# ─────────────────────────────────────────────────────────────────────────────
# Node 5 — Result Classification (94% accuracy — Part III, Section 29)
# ─────────────────────────────────────────────────────────────────────────────

class ResultAssessment(BaseModel):
    """Classify tool result quality.  Classification field FIRST."""

    quality: Literal[
        "success_rich",
        "success_partial",
        "no_results",
        "error_retryable",
        "error_fatal",
    ]
    brief_summary: str = Field(
        description="1-2 sentence summary of what the tool returned",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Node 5a — Retry Strategy (LLM-assisted, 92% accuracy — Part III, Section 35)
# ─────────────────────────────────────────────────────────────────────────────

class RetryStrategy(BaseModel):
    """Choose retry approach.  Strategy field FIRST."""

    strategy: Literal["retry_same", "retry_different_args"]
    reasoning: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Brief explanation of retry rationale",
    )
