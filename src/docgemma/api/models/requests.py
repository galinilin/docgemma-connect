"""API request schemas."""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    # No required fields - session is created empty
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a session."""

    content: str = Field(..., description="User message content")
    image_base64: str | None = Field(
        default=None,
        description="Optional base64-encoded image data",
    )


class ToolApprovalRequest(BaseModel):
    """Request to approve or reject a tool execution."""

    approved: bool = Field(..., description="Whether to approve the tool execution")
    reason: str | None = Field(
        default=None,
        description="Optional reason for rejection",
    )


# =============================================================================
# Patient/EHR Request Models
# =============================================================================


class AddAllergyRequest(BaseModel):
    """Request to add an allergy to a patient's chart."""

    substance: str = Field(
        ...,
        description="Substance the patient is allergic to",
        min_length=1,
    )
    reaction: str = Field(
        ...,
        description="Description of the allergic reaction",
        min_length=1,
    )
    severity: str = Field(
        default="moderate",
        description="Severity level: mild, moderate, or severe",
    )


class PrescribeMedicationRequest(BaseModel):
    """Request to prescribe a medication."""

    medication_name: str = Field(
        ...,
        description="Name of the medication",
        min_length=1,
    )
    dosage: str = Field(
        ...,
        description="Dosage (e.g., '500mg')",
        min_length=1,
    )
    frequency: str = Field(
        ...,
        description="Frequency (e.g., 'twice daily')",
        min_length=1,
    )


class SaveNoteRequest(BaseModel):
    """Request to save a clinical note."""

    note_text: str = Field(
        ...,
        description="The clinical note content",
        min_length=1,
    )
    note_type: str = Field(
        default="clinical-note",
        description="Type of note (clinical-note, progress-note, discharge-summary)",
    )


class CreatePatientRequest(BaseModel):
    """Request to create a new patient."""

    given_name: str = Field(
        ...,
        description="Patient's given/first name",
        min_length=1,
    )
    family_name: str = Field(
        ...,
        description="Patient's family/last name",
        min_length=1,
    )
    birth_date: str = Field(
        ...,
        description="Date of birth (YYYY-MM-DD)",
    )
    gender: str = Field(
        default="unknown",
        description="Patient gender: male, female, other, unknown",
    )
