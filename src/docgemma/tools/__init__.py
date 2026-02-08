"""DocGemma MCP Tools for medical AI agents.

This package provides MCP-compatible tools for medical information retrieval
and patient record management. All tools are async and include robust error
handling for use in agentic systems.

Available Tools:
    - check_drug_safety: FDA boxed warnings lookup (OpenFDA)
    - search_medical_literature: PubMed article search
    - check_drug_interactions: Drug interaction checker (OpenFDA)
    - find_clinical_trials: Search recruiting trials (ClinicalTrials.gov)
    - analyze_medical_image: Medical image analysis (MedGemma Vision)

FHIR Store EHR Tools:
    - search_patient: Search patients by name/DOB
    - get_patient_chart: Retrieve patient clinical summary
    - add_allergy: Document allergies
    - prescribe_medication: Create medication orders
    - save_clinical_note: Save clinical notes

Usage:
    # Run as MCP server
    python -m docgemma.tools.server

    # Or use tools directly
    from docgemma.tools import check_drug_safety, DrugSafetyInput

    result = await check_drug_safety(DrugSafetyInput(brand_name="Lipitor"))

    # FHIR store tools
    from docgemma.tools import search_patient, SearchPatientInput

    result = await search_patient(SearchPatientInput(name="Smith"))
"""

from .clinical_trials import find_clinical_trials
from .drug_interactions import check_drug_interactions
from .drug_safety import check_drug_safety
from .image_analysis import analyze_medical_image
from .medical_literature import search_medical_literature
from .registry import (
    TOOL_REGISTRY,
    execute_tool,
    get_tool_names,
    get_tools_for_prompt,
)
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
    ImageAnalysisInput,
    ImageAnalysisOutput,
    MedicalLiteratureInput,
    MedicalLiteratureOutput,
    PatientRecord,
    PatientRecordsInput,
    PatientRecordsOutput,
)

# Local FHIR JSON store tools
from .fhir_store import (
    FhirJsonStore,
    get_client,
    search_patient,
    get_patient_chart,
    add_allergy,
    prescribe_medication,
    save_clinical_note,
    SearchPatientInput,
    SearchPatientOutput,
    GetPatientChartInput,
    GetPatientChartOutput,
    AddAllergyInput,
    AddAllergyOutput,
    PrescribeMedicationInput,
    PrescribeMedicationOutput,
    SaveClinicalNoteInput,
    SaveClinicalNoteOutput,
)

__all__ = [
    # Registry
    "TOOL_REGISTRY",
    "execute_tool",
    "get_tool_names",
    "get_tools_for_prompt",
    # Tools
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "analyze_medical_image",
    # Input schemas
    "DrugSafetyInput",
    "MedicalLiteratureInput",
    "DrugInteractionsInput",
    "PatientRecordsInput",
    "ClinicalTrialsInput",
    "ImageAnalysisInput",
    # Output schemas
    "DrugSafetyOutput",
    "MedicalLiteratureOutput",
    "DrugInteractionsOutput",
    "PatientRecordsOutput",
    "ClinicalTrialsOutput",
    "ImageAnalysisOutput",
    # Supporting schemas
    "ArticleSummary",
    "DrugInteraction",
    "PatientRecord",
    "ClinicalTrial",
    # FHIR store client
    "FhirJsonStore",
    "get_client",
    # FHIR store tools
    "search_patient",
    "get_patient_chart",
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
    # FHIR store input schemas
    "SearchPatientInput",
    "GetPatientChartInput",
    "AddAllergyInput",
    "PrescribeMedicationInput",
    "SaveClinicalNoteInput",
    # FHIR store output schemas
    "SearchPatientOutput",
    "GetPatientChartOutput",
    "AddAllergyOutput",
    "PrescribeMedicationOutput",
    "SaveClinicalNoteOutput",
]
