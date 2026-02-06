"""API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .session import SessionStatus


class MessageResponse(BaseModel):
    """Response representation of a message."""

    role: str
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Response representation of a session."""

    session_id: str
    status: SessionStatus
    messages: list[MessageResponse]
    pending_approval: dict[str, Any] | None = None
    current_node: str | None = None
    completed_nodes: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionResponse]
    total: int


class GraphNode(BaseModel):
    """A node in the graph visualization."""

    id: str = Field(..., description="Node identifier")
    label: str = Field(..., description="Display label")
    status: str = Field(
        ...,
        description="Node status: pending, active, completed, skipped",
    )
    node_type: str = Field(
        default="default",
        description="Node type: decision, tool, llm, code",
    )


class GraphEdge(BaseModel):
    """An edge in the graph visualization."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str | None = Field(default=None, description="Edge label")
    active: bool = Field(default=False, description="Whether this edge is currently active")


class GraphStateResponse(BaseModel):
    """Response for graph state visualization."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    current_node: str | None = None
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    args: dict[str, str] = Field(..., description="Argument name -> description mapping")


class ToolListResponse(BaseModel):
    """Response for listing tools."""

    tools: list[ToolInfo]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    model_loaded: bool = False
    version: str = "0.1.0"


# =============================================================================
# Patient/EHR Response Models
# =============================================================================


class PatientSummary(BaseModel):
    """Summary of a patient for list views."""

    patient_id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient full name")
    dob: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    gender: str | None = Field(None, description="Patient gender")
    specialty: str | None = Field(None, description="Medical specialty category")


class PatientListResponse(BaseModel):
    """Response for listing patients."""

    patients: list[PatientSummary] = Field(default_factory=list)
    total: int = Field(..., description="Total number of patients found")
    error: str | None = Field(None, description="Error message if search failed")


class AllergyInfo(BaseModel):
    """Information about a patient allergy."""

    id: str | None = Field(None, description="Allergy record ID")
    substance: str = Field(..., description="Allergen substance")
    reaction: str | None = Field(None, description="Reaction description")
    severity: str | None = Field(None, description="Severity level")
    status: str = Field(default="active", description="Clinical status")


class MedicationInfo(BaseModel):
    """Information about a patient medication."""

    id: str | None = Field(None, description="Medication record ID")
    name: str = Field(..., description="Medication name")
    dosage: str | None = Field(None, description="Dosage instructions")
    frequency: str | None = Field(None, description="Frequency")
    status: str = Field(default="active", description="Medication status")


class ConditionInfo(BaseModel):
    """Information about a patient condition/diagnosis."""

    id: str | None = Field(None, description="Condition record ID")
    name: str = Field(..., description="Condition name")
    status: str = Field(default="active", description="Clinical status")


class LabResult(BaseModel):
    """Information about a lab result."""

    id: str | None = Field(None, description="Lab result ID")
    name: str = Field(..., description="Lab test name")
    value: str = Field(..., description="Result value with units")
    date: str | None = Field(None, description="Result date")
    status: str | None = Field(None, description="Result status (normal, abnormal, etc.)")


class ClinicalNote(BaseModel):
    """Information about a clinical note."""

    id: str | None = Field(None, description="Note ID")
    note_type: str = Field(..., description="Type of note")
    date: str | None = Field(None, description="Note date")
    preview: str | None = Field(None, description="Preview of note content")


class VitalSign(BaseModel):
    """Information about a vital sign reading."""

    id: str | None = Field(None, description="Vital sign ID")
    name: str = Field(..., description="Vital sign name (e.g. Heart rate)")
    value: float = Field(..., description="Numeric value")
    unit: str = Field(..., description="Unit (e.g. /min, mm[Hg])")
    date: str | None = Field(None, description="Reading date")


class ScreeningResult(BaseModel):
    """Information about a screening assessment result."""

    id: str | None = Field(None, description="Screening result ID")
    name: str = Field(..., description="Assessment name (e.g. GAD-7 total score)")
    score: str = Field(..., description="Score value")
    date: str | None = Field(None, description="Assessment date")


class VisitNote(BaseModel):
    """Information about a visit documentation note."""

    id: str | None = Field(None, description="Note ID")
    note_type: str = Field(..., description="HPI, Review of Systems, or Physical Exam")
    date: str | None = Field(None, description="Note date")
    author: str | None = Field(None, description="Note author")
    content: str = Field(..., description="Decoded note text")


class PatientChartResponse(BaseModel):
    """Full patient chart response."""

    patient_id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient full name")
    dob: str = Field(..., description="Date of birth")
    gender: str | None = Field(None, description="Patient gender")
    specialty: str | None = Field(None, description="Medical specialty category")
    conditions: list[ConditionInfo] = Field(default_factory=list)
    medications: list[MedicationInfo] = Field(default_factory=list)
    allergies: list[AllergyInfo] = Field(default_factory=list)
    labs: list[LabResult] = Field(default_factory=list)
    notes: list[ClinicalNote] = Field(default_factory=list)
    vitals: list[VitalSign] = Field(default_factory=list)
    screenings: list[ScreeningResult] = Field(default_factory=list)
    visit_notes: list[VisitNote] = Field(default_factory=list)
    error: str | None = Field(None, description="Error message if retrieval failed")


class AllergyResponse(BaseModel):
    """Response after adding an allergy."""

    success: bool = Field(..., description="Whether the operation succeeded")
    allergy_id: str | None = Field(None, description="Created allergy ID")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error message if failed")


class MedicationResponse(BaseModel):
    """Response after prescribing medication."""

    success: bool = Field(..., description="Whether the operation succeeded")
    order_id: str | None = Field(None, description="Created order ID")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error message if failed")


class NoteResponse(BaseModel):
    """Response after saving a clinical note."""

    success: bool = Field(..., description="Whether the operation succeeded")
    note_id: str | None = Field(None, description="Created note ID")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error message if failed")
