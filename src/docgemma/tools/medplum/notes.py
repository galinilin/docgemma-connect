"""Clinical note documentation tool for Medplum FHIR API.

Creates DocumentReference resources for clinical notes.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import httpx

from .client import get_client
from .schemas import SaveClinicalNoteInput, SaveClinicalNoteOutput


async def save_clinical_note(input_data: SaveClinicalNoteInput) -> SaveClinicalNoteOutput:
    """Save a clinical note to the patient's chart.

    Creates a FHIR DocumentReference resource with the note content
    encoded as base64 in an attachment.

    Args:
        input_data: Note details including patient_id, note_text, note_type

    Returns:
        SaveClinicalNoteOutput with confirmation including document ID, or error

    Example:
        >>> result = await save_clinical_note(SaveClinicalNoteInput(
        ...     patient_id="abc-123",
        ...     note_text="Patient presents with chest pain...",
        ...     note_type="progress-note"
        ... ))
        >>> print(result.result)
        Note saved to Patient abc-123's chart (Doc ID: doc-456)
    """
    client = get_client()
    patient_id = input_data.patient_id.strip()
    note_text = input_data.note_text.strip()
    note_type = input_data.note_type.strip()

    # Check credentials
    cred_error = client._check_credentials()
    if cred_error:
        return SaveClinicalNoteOutput(result="", error=cred_error)

    # Encode note content as base64
    note_base64 = base64.b64encode(note_text.encode("utf-8")).decode("utf-8")

    # Map common note types to LOINC codes
    note_type_codes = {
        "clinical-note": ("11506-3", "Progress note"),
        "progress-note": ("11506-3", "Progress note"),
        "discharge-summary": ("18842-5", "Discharge summary"),
        "history-and-physical": ("34117-2", "History and physical note"),
        "consultation": ("11488-4", "Consultation note"),
    }

    loinc_code, loinc_display = note_type_codes.get(
        note_type.lower(),
        ("11506-3", "Progress note"),  # Default to progress note
    )

    # Build FHIR DocumentReference resource
    document_reference = {
        "resourceType": "DocumentReference",
        "status": "current",
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": loinc_display,
                }
            ],
            "text": note_type,
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
        },
        "date": datetime.now(timezone.utc).isoformat(),
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain",
                    "data": note_base64,
                    "title": f"{note_type} - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                }
            }
        ],
    }

    try:
        result = await client.post("/DocumentReference", document_reference)
        doc_id = result.get("id", "unknown")

        return SaveClinicalNoteOutput(
            result=f"Note saved to Patient {patient_id}'s chart (Doc ID: {doc_id})",
            error=None,
        )

    except httpx.TimeoutException:
        return SaveClinicalNoteOutput(
            result="",
            error="Request timed out while saving clinical note",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return SaveClinicalNoteOutput(
                result="",
                error=f"Patient not found: {patient_id}",
            )
        if e.response.status_code == 401:
            return SaveClinicalNoteOutput(
                result="",
                error="Authentication failed - check Medplum credentials",
            )
        if e.response.status_code == 422:
            return SaveClinicalNoteOutput(
                result="",
                error=f"Invalid note data: {e.response.text[:200]}",
            )
        return SaveClinicalNoteOutput(
            result="",
            error=f"EHR error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return SaveClinicalNoteOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
