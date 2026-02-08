"""Pydantic schemas for MCP tool inputs and outputs.

These schemas provide strict type validation and serve as documentation
for the LLM to understand how to call each tool correctly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Drug Safety (OpenFDA) Schemas
# =============================================================================


class DrugSafetyInput(BaseModel):
    """Input schema for checking drug safety warnings."""

    brand_name: str = Field(
        ...,
        description="The brand name of the medication to check (e.g., 'Lipitor', 'Advil')",
        min_length=1,
    )


class DrugSafetyOutput(BaseModel):
    """Output schema for drug safety check results."""

    brand_name: str = Field(..., description="The queried drug name")
    has_warning: bool = Field(..., description="Whether a boxed warning exists")
    boxed_warning: str | None = Field(
        None, description="The boxed warning text if present"
    )
    error: str | None = Field(None, description="Error message if the lookup failed")


# =============================================================================
# Medical Literature (PubMed) Schemas
# =============================================================================


class MedicalLiteratureInput(BaseModel):
    """Input schema for searching medical literature."""

    query: str = Field(
        ...,
        description="Search query for medical literature (e.g., 'diabetes treatment guidelines')",
        min_length=1,
    )
    max_results: int = Field(
        default=3,
        description="Maximum number of results to return (1-10)",
        ge=1,
        le=10,
    )


class ArticleSummary(BaseModel):
    """Summary of a single PubMed article."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Article title")
    authors: str = Field(..., description="Author list (abbreviated)")
    journal: str = Field(..., description="Journal name")
    pub_date: str = Field(..., description="Publication date")
    abstract: str | None = Field(None, description="Article abstract if available")


class MedicalLiteratureOutput(BaseModel):
    """Output schema for medical literature search results."""

    query: str = Field(..., description="The original search query")
    total_found: int = Field(..., description="Total number of results found")
    articles: list[ArticleSummary] = Field(
        default_factory=list, description="List of article summaries"
    )
    error: str | None = Field(None, description="Error message if the search failed")


# =============================================================================
# Drug Interactions (RxNav) Schemas
# =============================================================================


class DrugInteractionsInput(BaseModel):
    """Input schema for checking drug interactions."""

    drugs: list[str] = Field(
        ...,
        description="List of drug names to check for interactions (e.g., ['warfarin', 'aspirin'])",
        min_length=2,
    )


class DrugInteraction(BaseModel):
    """A single drug interaction."""

    drug_pair: tuple[str, str] = Field(..., description="The two drugs that interact")
    severity: str = Field(..., description="Interaction severity level")
    description: str = Field(..., description="Description of the interaction")


class DrugInteractionsOutput(BaseModel):
    """Output schema for drug interaction check results."""

    drugs_checked: list[str] = Field(..., description="The drugs that were checked")
    resolved_rxcuis: dict[str, str | None] = Field(
        ..., description="Mapping of drug names to RxCUI codes (None if not found)"
    )
    interactions: list[DrugInteraction] = Field(
        default_factory=list, description="List of found interactions"
    )
    error: str | None = Field(None, description="Error message if the check failed")


# =============================================================================
# Patient Records (Mock EHR) Schemas
# =============================================================================


class PatientRecordsInput(BaseModel):
    """Input schema for patient records operations."""

    action: Literal["read", "update"] = Field(
        ..., description="Action to perform: 'read' to get patient data, 'update' to add data"
    )
    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
    )
    # Fields for update action
    diagnosis: str | None = Field(
        None, description="New diagnosis to add (for 'update' action)"
    )
    medication: str | None = Field(
        None, description="New medication to add (for 'update' action)"
    )
    note: str | None = Field(
        None, description="Clinical note to add (for 'update' action)"
    )


class PatientRecord(BaseModel):
    """A patient's medical record."""

    patient_id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient's full name")
    date_of_birth: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    diagnoses: list[str] = Field(default_factory=list, description="List of diagnoses")
    medications: list[str] = Field(
        default_factory=list, description="Current medications"
    )
    notes: list[str] = Field(default_factory=list, description="Clinical notes")


class PatientRecordsOutput(BaseModel):
    """Output schema for patient records operations."""

    action: str = Field(..., description="The action that was performed")
    success: bool = Field(..., description="Whether the operation succeeded")
    patient: PatientRecord | None = Field(
        None, description="The patient record (for read/update)"
    )
    message: str | None = Field(None, description="Status message")
    error: str | None = Field(None, description="Error message if the operation failed")


# =============================================================================
# Clinical Trials (ClinicalTrials.gov) Schemas
# =============================================================================


class ClinicalTrialsInput(BaseModel):
    """Input schema for searching clinical trials."""

    condition: str = Field(
        ...,
        description="Medical condition to search for (e.g., 'lung cancer', 'diabetes')",
        min_length=1,
    )
    location: str | None = Field(
        None,
        description="Optional location filter (e.g., 'California', 'New York', 'United States')",
    )


class ClinicalTrial(BaseModel):
    """Summary of a single clinical trial."""

    nct_id: str = Field(..., description="ClinicalTrials.gov identifier (e.g., NCT12345678)")
    title: str = Field(..., description="Official title of the study")
    status: str = Field(..., description="Recruitment status")
    conditions: list[str] = Field(
        default_factory=list, description="Conditions being studied"
    )
    contact_name: str | None = Field(None, description="Primary contact name")
    contact_phone: str | None = Field(None, description="Primary contact phone")
    contact_email: str | None = Field(None, description="Primary contact email")
    locations: list[str] = Field(
        default_factory=list, description="Study locations (city, state/country)"
    )


class ClinicalTrialsOutput(BaseModel):
    """Output schema for clinical trials search results."""

    condition: str = Field(..., description="The searched condition")
    location: str | None = Field(None, description="The location filter applied")
    total_found: int = Field(..., description="Total number of recruiting trials found")
    trials: list[ClinicalTrial] = Field(
        default_factory=list, description="List of clinical trials"
    )
    error: str | None = Field(None, description="Error message if the search failed")


# =============================================================================
# Medical Image Analysis Schemas
# =============================================================================


class ImageAnalysisInput(BaseModel):
    """Input schema for analyzing a medical image."""

    image_data: bytes = Field(..., description="Raw image bytes")
    query: str = Field(
        default="Describe this medical image in detail. Identify the imaging modality, anatomical region, and any notable findings.",
        description="Analysis prompt / clinical question about the image",
    )


class ImageAnalysisOutput(BaseModel):
    """Output schema for medical image analysis results."""

    findings: str = Field(..., description="Clinical findings from the image")
    query: str = Field(..., description="The analysis query used")
    error: str | None = Field(None, description="Error message if analysis failed")
