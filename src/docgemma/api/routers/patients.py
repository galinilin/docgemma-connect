"""Patient/EHR API endpoints.

Provides REST endpoints for browsing and managing patient data
via the local FHIR JSON store.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query

from ..models.requests import (
    AddAllergyRequest,
    CreatePatientRequest,
    PrescribeMedicationRequest,
    SaveNoteRequest,
)
from ..models.responses import (
    AllergyInfo,
    AllergyResponse,
    ConditionInfo,
    LabResult,
    MedicationInfo,
    MedicationResponse,
    NoteResponse,
    PatientChartResponse,
    PatientListResponse,
    PatientSummary,
)
from ...tools.fhir_store import (
    AddAllergyInput,
    GetPatientChartInput,
    PrescribeMedicationInput,
    SaveClinicalNoteInput,
    SearchPatientInput,
    add_allergy,
    get_client,
    get_patient_chart,
    prescribe_medication,
    save_clinical_note,
    search_patient,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=PatientListResponse)
async def list_patients(
    name: str | None = Query(None, description="Search by patient name"),
    dob: str | None = Query(None, description="Search by date of birth (YYYY-MM-DD)"),
) -> PatientListResponse:
    """Search for patients by name and/or date of birth.

    Returns a list of matching patients. At least one search parameter
    is required.
    """
    # If no search params, return empty list (or could list all)
    if not name and not dob:
        # Try to list recent patients
        client = get_client()
        cred_error = client._check_credentials()
        if cred_error:
            return PatientListResponse(patients=[], total=0, error=cred_error)

        try:
            data = await client.get("/Patient", params={"_count": "50", "_sort": "-_lastUpdated"})
            patients = _parse_patient_bundle(data)
            return PatientListResponse(patients=patients, total=len(patients))
        except Exception as e:
            return PatientListResponse(patients=[], total=0, error=str(e))

    # Use search_patient tool
    result = await search_patient(SearchPatientInput(name=name, dob=dob))

    if result.error:
        return PatientListResponse(patients=[], total=0, error=result.error)

    # Parse the result text into structured data
    patients = _parse_search_result(result.result)
    return PatientListResponse(patients=patients, total=len(patients))


@router.post("", response_model=PatientSummary, status_code=201)
async def create_patient(request: CreatePatientRequest) -> PatientSummary:
    """Create a new patient record."""
    client = get_client()

    cred_error = client._check_credentials()
    if cred_error:
        raise HTTPException(status_code=503, detail=cred_error)

    patient_resource = {
        "resourceType": "Patient",
        "name": [
            {
                "use": "official",
                "family": request.family_name,
                "given": [request.given_name],
            }
        ],
        "gender": request.gender,
        "birthDate": request.birth_date,
    }

    try:
        result = await client.post("/Patient", patient_resource)
        return PatientSummary(
            patient_id=result.get("id", "unknown"),
            name=f"{request.given_name} {request.family_name}",
            dob=request.birth_date,
            gender=request.gender,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {e}")


@router.get("/{patient_id}", response_model=PatientChartResponse)
async def get_patient(patient_id: str) -> PatientChartResponse:
    """Get a patient's full chart including demographics, conditions,
    medications, allergies, and recent labs.
    """
    client = get_client()

    cred_error = client._check_credentials()
    if cred_error:
        raise HTTPException(status_code=503, detail=cred_error)

    try:
        # Fetch patient demographics
        patient_data = await client.get(f"/Patient/{patient_id}")

        # Extract basic info
        name = _extract_patient_name(patient_data)
        dob = patient_data.get("birthDate", "unknown")
        gender = patient_data.get("gender")

        # Fetch related resources
        conditions = await _fetch_conditions(client, patient_id)
        medications = await _fetch_medications(client, patient_id)
        allergies = await _fetch_allergies(client, patient_id)
        labs = await _fetch_labs(client, patient_id)
        notes = await _fetch_notes(client, patient_id)

        return PatientChartResponse(
            patient_id=patient_id,
            name=name,
            dob=dob,
            gender=gender,
            conditions=conditions,
            medications=medications,
            allergies=allergies,
            labs=labs,
            notes=notes,
        )

    except Exception as e:
        error_str = str(e)
        if "404" in error_str:
            raise HTTPException(status_code=404, detail=f"Patient not found: {patient_id}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch patient: {e}")


@router.post("/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
async def add_patient_allergy(
    patient_id: str,
    request: AddAllergyRequest,
) -> AllergyResponse:
    """Add an allergy to the patient's chart."""
    result = await add_allergy(
        AddAllergyInput(
            patient_id=patient_id,
            substance=request.substance,
            reaction=request.reaction,
            severity=request.severity,
        )
    )

    if result.error:
        return AllergyResponse(
            success=False,
            allergy_id=None,
            message="",
            error=result.error,
        )

    # Extract allergy ID from result message
    allergy_id = _extract_id_from_message(result.result, "Allergy ID")

    return AllergyResponse(
        success=True,
        allergy_id=allergy_id,
        message=result.result,
    )


@router.post("/{patient_id}/medications", response_model=MedicationResponse, status_code=201)
async def prescribe_patient_medication(
    patient_id: str,
    request: PrescribeMedicationRequest,
) -> MedicationResponse:
    """Prescribe a medication for the patient."""
    result = await prescribe_medication(
        PrescribeMedicationInput(
            patient_id=patient_id,
            medication_name=request.medication_name,
            dosage=request.dosage,
            frequency=request.frequency,
        )
    )

    if result.error:
        return MedicationResponse(
            success=False,
            order_id=None,
            message="",
            error=result.error,
        )

    # Extract order ID from result message
    order_id = _extract_id_from_message(result.result, "Order ID")

    return MedicationResponse(
        success=True,
        order_id=order_id,
        message=result.result,
    )


@router.post("/{patient_id}/notes", response_model=NoteResponse, status_code=201)
async def save_patient_note(
    patient_id: str,
    request: SaveNoteRequest,
) -> NoteResponse:
    """Save a clinical note to the patient's chart."""
    result = await save_clinical_note(
        SaveClinicalNoteInput(
            patient_id=patient_id,
            note_text=request.note_text,
            note_type=request.note_type,
        )
    )

    if result.error:
        return NoteResponse(
            success=False,
            note_id=None,
            message="",
            error=result.error,
        )

    # Extract note ID from result message
    note_id = _extract_id_from_message(result.result, "Doc ID")

    return NoteResponse(
        success=True,
        note_id=note_id,
        message=result.result,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_search_result(result_text: str) -> list[PatientSummary]:
    """Parse search_patient result text into PatientSummary objects."""
    patients = []

    if not result_text or "No patients found" in result_text:
        return patients

    # Parse lines like "1. John Smith (ID: abc-123) DOB: 1978-03-15"
    pattern = r"\d+\.\s+(.+?)\s+\(ID:\s*([^)]+)\)\s+DOB:\s*(\S+)"

    for match in re.finditer(pattern, result_text):
        name, patient_id, dob = match.groups()
        patients.append(
            PatientSummary(
                patient_id=patient_id.strip(),
                name=name.strip(),
                dob=dob.strip(),
                gender=None,
            )
        )

    return patients


def _parse_patient_bundle(data: dict) -> list[PatientSummary]:
    """Parse FHIR Bundle into PatientSummary list."""
    patients = []

    for entry in data.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Patient":
            continue

        patient_id = resource.get("id", "unknown")
        name = _extract_patient_name(resource)
        dob = resource.get("birthDate", "unknown")
        gender = resource.get("gender")

        patients.append(
            PatientSummary(
                patient_id=patient_id,
                name=name,
                dob=dob,
                gender=gender,
            )
        )

    return patients


def _extract_patient_name(patient: dict) -> str:
    """Extract formatted patient name from FHIR Patient resource."""
    names = patient.get("name", [])
    if names:
        name_obj = names[0]
        given = " ".join(name_obj.get("given", []))
        family = name_obj.get("family", "")
        return f"{given} {family}".strip() or "Unknown"
    return "Unknown"


def _extract_id_from_message(message: str, id_label: str) -> str | None:
    """Extract ID from message like 'something (Order ID: xyz-123)'."""
    pattern = rf"{id_label}:\s*([^)\s]+)"
    match = re.search(pattern, message)
    if match:
        return match.group(1)
    return None


async def _fetch_conditions(client, patient_id: str) -> list[ConditionInfo]:
    """Fetch patient conditions."""
    try:
        data = await client.get("/Condition", params={"subject": patient_id, "_count": "50"})
        conditions = []
        for entry in data.get("entry", []):
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            name = code.get("text") or _get_coding_display(code)
            if name:
                conditions.append(
                    ConditionInfo(
                        id=resource.get("id"),
                        name=name,
                        status=resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
                    )
                )
        return conditions
    except Exception:
        return []


async def _fetch_medications(client, patient_id: str) -> list[MedicationInfo]:
    """Fetch patient medications."""
    try:
        data = await client.get(
            "/MedicationRequest",
            params={"subject": patient_id, "_count": "50"},
        )
        medications = []
        for entry in data.get("entry", []):
            resource = entry.get("resource", {})
            med = resource.get("medicationCodeableConcept", {})
            name = med.get("text") or _get_coding_display(med)
            if name:
                # Extract dosage
                dosage_list = resource.get("dosageInstruction", [])
                dosage = dosage_list[0].get("text", "") if dosage_list else None

                medications.append(
                    MedicationInfo(
                        id=resource.get("id"),
                        name=name,
                        dosage=dosage,
                        frequency=None,
                        status=resource.get("status", "active"),
                    )
                )
        return medications
    except Exception:
        return []


async def _fetch_allergies(client, patient_id: str) -> list[AllergyInfo]:
    """Fetch patient allergies."""
    try:
        data = await client.get(
            "/AllergyIntolerance",
            params={"patient": patient_id, "_count": "50"},
        )
        allergies = []
        for entry in data.get("entry", []):
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            substance = code.get("text") or _get_coding_display(code)
            if substance:
                # Get reaction
                reactions = resource.get("reaction", [])
                reaction_text = None
                if reactions:
                    manifestations = reactions[0].get("manifestation", [])
                    if manifestations:
                        reaction_text = manifestations[0].get("text")

                allergies.append(
                    AllergyInfo(
                        id=resource.get("id"),
                        substance=substance,
                        reaction=reaction_text,
                        severity=resource.get("criticality"),
                        status=resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
                    )
                )
        return allergies
    except Exception:
        return []


async def _fetch_labs(client, patient_id: str) -> list[LabResult]:
    """Fetch patient lab results."""
    try:
        data = await client.get(
            "/Observation",
            params={
                "subject": patient_id,
                "category": "laboratory",
                "_count": "20",
                "_sort": "-date",
            },
        )
        labs = []
        for entry in data.get("entry", []):
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            name = code.get("text") or _get_coding_display(code)
            if not name:
                continue

            # Get value
            value = ""
            if "valueQuantity" in resource:
                vq = resource["valueQuantity"]
                value = f"{vq.get('value', '')} {vq.get('unit', '')}".strip()
            elif "valueString" in resource:
                value = resource["valueString"]
            elif "valueCodeableConcept" in resource:
                value = resource["valueCodeableConcept"].get("text", "")

            if value:
                labs.append(
                    LabResult(
                        id=resource.get("id"),
                        name=name,
                        value=value,
                        date=resource.get("effectiveDateTime", "")[:10] if resource.get("effectiveDateTime") else None,
                        status=resource.get("status"),
                    )
                )
        return labs
    except Exception:
        return []


async def _fetch_notes(client, patient_id: str) -> list:
    """Fetch patient clinical notes."""
    from ..models.responses import ClinicalNote

    try:
        data = await client.get(
            "/DocumentReference",
            params={"subject": patient_id, "_count": "20", "_sort": "-date"},
        )
        notes = []
        for entry in data.get("entry", []):
            resource = entry.get("resource", {})
            doc_type = resource.get("type", {})
            note_type = doc_type.get("text") or _get_coding_display(doc_type) or "Note"

            notes.append(
                ClinicalNote(
                    id=resource.get("id"),
                    note_type=note_type,
                    date=resource.get("date", "")[:10] if resource.get("date") else None,
                    preview=None,  # Could decode content if needed
                )
            )
        return notes
    except Exception:
        return []


def _get_coding_display(codeable_concept: dict) -> str:
    """Extract display text from a CodeableConcept."""
    codings = codeable_concept.get("coding", [])
    if codings:
        return codings[0].get("display", "")
    return ""
