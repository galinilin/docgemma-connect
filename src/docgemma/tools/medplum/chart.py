"""Patient chart retrieval tool for Medplum FHIR API.

Retrieves comprehensive patient chart including demographics, conditions,
medications, allergies, and recent lab results.
"""

from __future__ import annotations

import httpx

from .client import get_client
from .schemas import GetPatientChartInput, GetPatientChartOutput


async def get_patient_chart(input_data: GetPatientChartInput) -> GetPatientChartOutput:
    """Retrieve a patient's clinical chart summary.

    Fetches patient demographics along with conditions, medications,
    allergies, and recent laboratory results in a single summary.

    Args:
        input_data: Patient ID to retrieve

    Returns:
        GetPatientChartOutput with formatted clinical summary or error

    Example:
        >>> result = await get_patient_chart(GetPatientChartInput(patient_id="abc-123"))
        >>> print(result.result)
        PATIENT: John Smith (M, DOB: 1978-03-15)
        CONDITIONS: Hypertension, Type 2 Diabetes
        MEDICATIONS: Metformin 500mg BID, Lisinopril 10mg daily
        ALLERGIES: Penicillin (severe - anaphylaxis)
        LABS: HbA1c 7.2% (2024-01-15), Creatinine 1.1 (2024-01-15)
    """
    client = get_client()
    patient_id = input_data.patient_id.strip()

    # Check credentials
    cred_error = client._check_credentials()
    if cred_error:
        return GetPatientChartOutput(result="", error=cred_error)

    try:
        # Fetch patient demographics
        patient_data = await client.get(f"/Patient/{patient_id}")

        # Parse patient demographics
        patient_name = _extract_patient_name(patient_data)
        patient_gender = patient_data.get("gender", "unknown")[0].upper()
        patient_dob = patient_data.get("birthDate", "unknown")

        # Initialize collections
        conditions = []
        medications = []
        allergies = []
        labs = []

        # Fetch conditions
        try:
            conditions_data = await client.get(
                "/Condition",
                params={"subject": patient_id, "_count": "50"},
            )
            for entry in conditions_data.get("entry", []):
                resource = entry.get("resource", {})
                _parse_resource(resource, conditions, medications, allergies)
        except Exception:
            pass  # Continue if conditions fetch fails

        # Fetch medications
        try:
            meds_data = await client.get(
                "/MedicationRequest",
                params={"subject": patient_id, "status": "active", "_count": "50"},
            )
            for entry in meds_data.get("entry", []):
                resource = entry.get("resource", {})
                _parse_resource(resource, conditions, medications, allergies)
        except Exception:
            pass  # Continue if medications fetch fails

        # Fetch allergies
        try:
            allergies_data = await client.get(
                "/AllergyIntolerance",
                params={"patient": patient_id, "_count": "50"},
            )
            for entry in allergies_data.get("entry", []):
                resource = entry.get("resource", {})
                _parse_resource(resource, conditions, medications, allergies)
        except Exception:
            pass  # Continue if allergies fetch fails

        # Fetch recent labs
        try:
            labs_data = await client.get(
                "/Observation",
                params={
                    "subject": patient_id,
                    "category": "laboratory",
                    "_count": "20",
                    "_sort": "-date",
                },
            )
            for entry in labs_data.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Observation":
                    lab = _format_lab(resource)
                    if lab:
                        labs.append(lab)
        except Exception:
            pass  # Continue if labs fetch fails

        # Format output
        lines = [f"PATIENT: {patient_name} ({patient_gender}, DOB: {patient_dob})"]
        lines.append(f"CONDITIONS: {', '.join(conditions) if conditions else 'None documented'}")
        lines.append(f"MEDICATIONS: {', '.join(medications) if medications else 'None active'}")
        lines.append(f"ALLERGIES: {', '.join(allergies) if allergies else 'NKDA'}")
        lines.append(f"LABS: {', '.join(labs[:5]) if labs else 'None recent'}")

        return GetPatientChartOutput(result="\n".join(lines), error=None)

    except httpx.TimeoutException:
        return GetPatientChartOutput(
            result="",
            error="Request timed out while fetching patient chart",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return GetPatientChartOutput(
                result="",
                error=f"Patient not found: {patient_id}",
            )
        if e.response.status_code == 401:
            return GetPatientChartOutput(
                result="",
                error="Authentication failed - check Medplum credentials",
            )
        return GetPatientChartOutput(
            result="",
            error=f"EHR error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return GetPatientChartOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


def _extract_patient_name(patient: dict) -> str:
    """Extract formatted patient name from FHIR Patient resource."""
    names = patient.get("name", [])
    if names:
        name_obj = names[0]
        given = " ".join(name_obj.get("given", []))
        family = name_obj.get("family", "")
        return f"{given} {family}".strip() or "Unknown"
    return "Unknown"


def _parse_resource(
    resource: dict,
    conditions: list[str],
    medications: list[str],
    allergies: list[str],
) -> None:
    """Parse a FHIR resource and add to appropriate collection."""
    resource_type = resource.get("resourceType")

    if resource_type == "Condition":
        code = resource.get("code", {})
        text = code.get("text") or _get_coding_display(code)
        if text:
            conditions.append(text)

    elif resource_type == "MedicationRequest":
        med = resource.get("medicationCodeableConcept", {})
        text = med.get("text") or _get_coding_display(med)
        # Add dosage if available
        dosage_list = resource.get("dosageInstruction", [])
        if dosage_list and text:
            dosage = dosage_list[0].get("text", "")
            if dosage:
                text = f"{text} {dosage}"
        if text:
            medications.append(text)

    elif resource_type == "AllergyIntolerance":
        code = resource.get("code", {})
        substance = code.get("text") or _get_coding_display(code)
        # Get severity and reaction
        severity = resource.get("criticality", "unknown")
        reactions = resource.get("reaction", [])
        reaction_text = ""
        if reactions:
            manifestations = reactions[0].get("manifestation", [])
            if manifestations:
                reaction_text = manifestations[0].get("text") or _get_coding_display(manifestations[0])
        if substance:
            if severity and reaction_text:
                allergies.append(f"{substance} ({severity} - {reaction_text})")
            elif severity:
                allergies.append(f"{substance} ({severity})")
            else:
                allergies.append(substance)


def _get_coding_display(codeable_concept: dict) -> str:
    """Extract display text from a CodeableConcept."""
    codings = codeable_concept.get("coding", [])
    if codings:
        return codings[0].get("display", "")
    return ""


def _format_lab(observation: dict) -> str | None:
    """Format an Observation resource as a lab result string."""
    code = observation.get("code", {})
    name = code.get("text") or _get_coding_display(code)
    if not name:
        return None

    # Get value
    value = ""
    if "valueQuantity" in observation:
        vq = observation["valueQuantity"]
        value = f"{vq.get('value', '')} {vq.get('unit', '')}".strip()
    elif "valueString" in observation:
        value = observation["valueString"]
    elif "valueCodeableConcept" in observation:
        value = observation["valueCodeableConcept"].get("text", "")

    # Get date
    date = observation.get("effectiveDateTime", "")[:10]  # YYYY-MM-DD

    if value:
        return f"{name} {value} ({date})" if date else f"{name} {value}"
    return None
