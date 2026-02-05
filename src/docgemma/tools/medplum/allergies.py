"""Allergy documentation tool for Medplum FHIR API.

Creates AllergyIntolerance resources in the patient's chart.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .client import get_client
from .schemas import AddAllergyInput, AddAllergyOutput


async def add_allergy(input_data: AddAllergyInput) -> AddAllergyOutput:
    """Document an allergy in the patient's chart.

    Creates a FHIR AllergyIntolerance resource with the specified
    substance, reaction, and severity.

    Args:
        input_data: Allergy details including patient_id, substance, reaction, severity

    Returns:
        AddAllergyOutput with confirmation or error

    Example:
        >>> result = await add_allergy(AddAllergyInput(
        ...     patient_id="abc-123",
        ...     substance="Penicillin",
        ...     reaction="anaphylaxis",
        ...     severity="severe"
        ... ))
        >>> print(result.result)
        Allergy documented: Penicillin (severe) for Patient abc-123
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

    except httpx.TimeoutException:
        return AddAllergyOutput(
            result="",
            error="Request timed out while documenting allergy",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return AddAllergyOutput(
                result="",
                error=f"Patient not found: {patient_id}",
            )
        if e.response.status_code == 401:
            return AddAllergyOutput(
                result="",
                error="Authentication failed - check Medplum credentials",
            )
        if e.response.status_code == 422:
            return AddAllergyOutput(
                result="",
                error=f"Invalid allergy data: {e.response.text[:200]}",
            )
        return AddAllergyOutput(
            result="",
            error=f"EHR error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return AddAllergyOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
