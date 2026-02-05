"""Medplum FHIR API tools for DocGemma.

Provides MCP tools for interacting with Medplum EHR:
- search_patient: Search patients by name/DOB
- get_patient_chart: Retrieve patient clinical summary
- add_allergy: Document allergies
- prescribe_medication: Create medication orders
- save_clinical_note: Save clinical notes

Usage:
    from docgemma.tools.medplum import search_patient, SearchPatientInput

    result = await search_patient(SearchPatientInput(name="Smith"))
"""

from .allergies import add_allergy
from .chart import get_patient_chart
from .client import MedplumClient, get_client
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

__all__ = [
    # Client
    "MedplumClient",
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
