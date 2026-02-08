"""Allergy documentation tool for local FHIR JSON store.

Creates AllergyIntolerance resources in the patient's chart.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .store import get_client
from .schemas import AddAllergyInput, AddAllergyOutput


async def add_allergy(input_data: AddAllergyInput) -> AddAllergyOutput:
    """Document an allergy in the patient's chart.

    Creates a FHIR AllergyIntolerance resource with the specified
    substance, reaction, and severity.

    Args:
        input_data: Allergy details including patient_id, substance, reaction, severity

    Returns:
        AddAllergyOutput with confirmation or error
    """
    client = get_client()
    patient_id = input_data.patient_id.strip()
    substance = input_data.substance.strip()
    reaction = input_data.reaction.strip()
    severity = input_data.severity.strip().lower()

    # Check credentials
    cred_error = client._check_credentials()
    if cred_error:
        return AddAllergyOutput(result="", error=cred_error)

    # Validate severity
    valid_severities = {"mild", "moderate", "severe"}
    if severity not in valid_severities:
        return AddAllergyOutput(
            result="",
            error=f"Invalid severity '{severity}'. Must be: mild, moderate, or severe",
        )

    # Map severity to FHIR criticality
    criticality_map = {
        "mild": "low",
        "moderate": "low",
        "severe": "high",
    }

    # Build FHIR AllergyIntolerance resource
    allergy_resource = {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active",
                    "display": "Active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed",
                    "display": "Confirmed",
                }
            ]
        },
        "criticality": criticality_map[severity],
        "code": {
            "text": substance,
        },
        "patient": {
            "reference": f"Patient/{patient_id}",
        },
        "recordedDate": datetime.now(timezone.utc).isoformat(),
        "reaction": [
            {
                "manifestation": [
                    {
                        "text": reaction,
                    }
                ],
                "severity": severity,
            }
        ],
    }

    try:
        result = await client.post("/AllergyIntolerance", allergy_resource)
        allergy_id = result.get("id", "unknown")

        return AddAllergyOutput(
            result=f"Allergy documented: {substance} ({severity}) for Patient {patient_id} (Allergy ID: {allergy_id})",
            error=None,
        )

    except Exception as e:
        return AddAllergyOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
