"""Local FHIR JSON store tools for DocGemma.

Provides tools for interacting with a local file-based FHIR R4 store:
- search_patient: Search patients by name/DOB
- get_patient_chart: Retrieve patient clinical summary
- add_allergy: Document allergies
- prescribe_medication: Create medication orders
- save_clinical_note: Save clinical notes

Usage:
    from docgemma.tools.fhir_store import search_patient, SearchPatientInput

    result = await search_patient(SearchPatientInput(name="Smith"))
"""

from .allergies import add_allergy
from .chart import get_patient_chart
from .medications import prescribe_medication
from .notes import save_clinical_note
from .schemas import (
    AddAllergyInput,
    AddAllergyOutput,
    GetPatientChartInput,
    GetPatientChartOutput,
    PrescribeMedicationInput,
    PrescribeMedicationOutput,
    SaveClinicalNoteInput,
    SaveClinicalNoteOutput,
    SearchPatientInput,
    SearchPatientOutput,
)
from .search import search_patient
from .store import FhirJsonStore, ResourceNotFoundError, get_client

__all__ = [
    # Client
    "FhirJsonStore",
    "ResourceNotFoundError",
    "get_client",
    # Tool functions
    "search_patient",
    "get_patient_chart",
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
    # Input schemas
    "SearchPatientInput",
    "GetPatientChartInput",
    "AddAllergyInput",
    "PrescribeMedicationInput",
    "SaveClinicalNoteInput",
    # Output schemas
    "SearchPatientOutput",
    "GetPatientChartOutput",
    "AddAllergyOutput",
    "PrescribeMedicationOutput",
    "SaveClinicalNoteOutput",
]
