"""Pydantic schemas for Medplum FHIR tools.

Input and output schemas for patient search, chart retrieval,
allergy documentation, medication prescribing, and clinical notes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# =============================================================================
# Search Patient
# =============================================================================


class SearchPatientInput(BaseModel):
    """Input schema for searching patients."""

    name: str | None = Field(
        None,
        description="Patient name to search for (partial match supported)",
    )
    dob: str | None = Field(
        None,
        description="Date of birth in YYYY-MM-DD format",
    )


class SearchPatientOutput(BaseModel):
    """Output schema for patient search results."""

    result: str = Field(..., description="Formatted search results")
    error: str | None = Field(None, description="Error message if search failed")


# =============================================================================
# Get Patient Chart
# =============================================================================


class GetPatientChartInput(BaseModel):
    """Input schema for retrieving patient chart."""

    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
    )


class GetPatientChartOutput(BaseModel):
    """Output schema for patient chart retrieval."""

    result: str = Field(..., description="Formatted clinical summary")
    error: str | None = Field(None, description="Error message if retrieval failed")


# =============================================================================
# Add Allergy
# =============================================================================


class AddAllergyInput(BaseModel):
    """Input schema for documenting an allergy."""

    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
    )
    substance: str = Field(
        ...,
        description="Substance the patient is allergic to (e.g., 'Penicillin')",
        min_length=1,
    )
    reaction: str = Field(
        ...,
        description="Description of the allergic reaction (e.g., 'hives', 'anaphylaxis')",
        min_length=1,
    )
    severity: str = Field(
        default="moderate",
        description="Severity level: 'mild', 'moderate', or 'severe'",
    )


class AddAllergyOutput(BaseModel):
    """Output schema for allergy documentation."""

    result: str = Field(..., description="Confirmation message")
    error: str | None = Field(None, description="Error message if operation failed")


# =============================================================================
# Prescribe Medication
# =============================================================================


class PrescribeMedicationInput(BaseModel):
    """Input schema for prescribing medication."""

    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
    )
    medication_name: str = Field(
        ...,
        description="Name of the medication to prescribe",
        min_length=1,
    )
    dosage: str = Field(
        ...,
        description="Dosage (e.g., '10mg', '500mg')",
        min_length=1,
    )
    frequency: str = Field(
        ...,
        description="Frequency (e.g., 'once daily', 'twice daily', 'every 8 hours')",
        min_length=1,
    )


class PrescribeMedicationOutput(BaseModel):
    """Output schema for medication prescription."""

    result: str = Field(..., description="Confirmation message with order ID")
    error: str | None = Field(None, description="Error message if operation failed")


# =============================================================================
# Save Clinical Note
# =============================================================================


class SaveClinicalNoteInput(BaseModel):
    """Input schema for saving a clinical note."""

    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
    )
    note_text: str = Field(
        ...,
        description="The clinical note content",
        min_length=1,
    )
    note_type: str = Field(
        default="clinical-note",
        description="Type of note (e.g., 'clinical-note', 'progress-note', 'discharge-summary')",
    )


class SaveClinicalNoteOutput(BaseModel):
    """Output schema for clinical note save operation."""

    result: str = Field(..., description="Confirmation message with document ID")
    error: str | None = Field(None, description="Error message if operation failed")
