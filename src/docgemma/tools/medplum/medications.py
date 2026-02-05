"""Medication prescribing tool for Medplum FHIR API.

Creates MedicationRequest resources for prescribing medications.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .client import get_client
from .schemas import PrescribeMedicationInput, PrescribeMedicationOutput


async def prescribe_medication(
    input_data: PrescribeMedicationInput,
) -> PrescribeMedicationOutput:
    """Prescribe a medication for a patient.

    Creates a FHIR MedicationRequest resource with the specified
    medication, dosage, and frequency.

    Args:
        input_data: Prescription details including patient_id, medication_name, dosage, frequency

    Returns:
        PrescribeMedicationOutput with confirmation including order ID, or error

    Example:
        >>> result = await prescribe_medication(PrescribeMedicationInput(
        ...     patient_id="abc-123",
        ...     medication_name="Metformin",
        ...     dosage="500mg",
        ...     frequency="twice daily"
        ... ))
        >>> print(result.result)
        Prescribed: Metformin 500mg twice daily for Patient abc-123 (Order ID: xyz-789)
    """
    client = get_client()
    patient_id = input_data.patient_id.strip()
    medication_name = input_data.medication_name.strip()
    dosage = input_data.dosage.strip()
    frequency = input_data.frequency.strip()

    # Check credentials
    cred_error = client._check_credentials()
    if cred_error:
        return PrescribeMedicationOutput(result="", error=cred_error)

    # Build FHIR MedicationRequest resource
    medication_request = {
        "resourceType": "MedicationRequest",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "text": medication_name,
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
        },
        "authoredOn": datetime.now(timezone.utc).isoformat(),
        "dosageInstruction": [
            {
                "text": f"{dosage} {frequency}",
                "timing": {
                    "code": {
                        "text": frequency,
                    }
                },
                "doseAndRate": [
                    {
                        "doseQuantity": {
                            "value": _extract_dose_value(dosage),
                            "unit": _extract_dose_unit(dosage),
                        }
                    }
                ],
            }
        ],
    }

    try:
        result = await client.post("/MedicationRequest", medication_request)
        order_id = result.get("id", "unknown")

        return PrescribeMedicationOutput(
            result=f"Prescribed: {medication_name} {dosage} {frequency} for Patient {patient_id} (Order ID: {order_id})",
            error=None,
        )

    except httpx.TimeoutException:
        return PrescribeMedicationOutput(
            result="",
            error="Request timed out while prescribing medication",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return PrescribeMedicationOutput(
                result="",
                error=f"Patient not found: {patient_id}",
            )
        if e.response.status_code == 401:
            return PrescribeMedicationOutput(
                result="",
                error="Authentication failed - check Medplum credentials",
            )
        if e.response.status_code == 422:
            return PrescribeMedicationOutput(
                result="",
                error=f"Invalid prescription data: {e.response.text[:200]}",
            )
        return PrescribeMedicationOutput(
            result="",
            error=f"EHR error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return PrescribeMedicationOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


def _extract_dose_value(dosage: str) -> float:
    """Extract numeric value from dosage string like '500mg' -> 500."""
    import re

    match = re.search(r"(\d+(?:\.\d+)?)", dosage)
    if match:
        return float(match.group(1))
    return 0


def _extract_dose_unit(dosage: str) -> str:
    """Extract unit from dosage string like '500mg' -> 'mg'."""
    import re

    match = re.search(r"\d+(?:\.\d+)?\s*(\w+)", dosage)
    if match:
        return match.group(1)
    return "unit"
