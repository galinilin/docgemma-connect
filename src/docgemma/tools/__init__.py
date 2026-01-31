"""DocGemma MCP Tools for medical AI agents.

This package provides MCP-compatible tools for medical information retrieval
and patient record management. All tools are async and include robust error
handling for use in agentic systems.

Available Tools:
    - check_drug_safety: FDA boxed warnings lookup (OpenFDA)
    - search_medical_literature: PubMed article search
    - check_drug_interactions: Drug interaction checker (OpenFDA)
    - find_clinical_trials: Search recruiting trials (ClinicalTrials.gov)

Usage:
    # Run as MCP server
    python -m docgemma.tools.server

    # Or use tools directly
    from docgemma.tools import check_drug_safety, DrugSafetyInput

    result = await check_drug_safety(DrugSafetyInput(brand_name="Lipitor"))
"""

from .clinical_trials import find_clinical_trials
from .drug_interactions import check_drug_interactions
from .drug_safety import check_drug_safety
from .medical_literature import search_medical_literature
from .schemas import (
    ArticleSummary,
    ClinicalTrial,
    ClinicalTrialsInput,
    ClinicalTrialsOutput,
    DrugInteraction,
    DrugInteractionsInput,
    DrugInteractionsOutput,
    DrugSafetyInput,
    DrugSafetyOutput,
    MedicalLiteratureInput,
    MedicalLiteratureOutput,
    PatientRecord,
    PatientRecordsInput,
    PatientRecordsOutput,
)

__all__ = [
    # Tools
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    # Input schemas
    "DrugSafetyInput",
    "MedicalLiteratureInput",
    "DrugInteractionsInput",
    "PatientRecordsInput",
    "ClinicalTrialsInput",
    # Output schemas
    "DrugSafetyOutput",
    "MedicalLiteratureOutput",
    "DrugInteractionsOutput",
    "PatientRecordsOutput",
    "ClinicalTrialsOutput",
    # Supporting schemas
    "ArticleSummary",
    "DrugInteraction",
    "PatientRecord",
    "ClinicalTrial",
]
