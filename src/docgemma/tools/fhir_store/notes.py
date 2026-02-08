"""Clinical note documentation tool for local FHIR JSON store.

Creates DocumentReference resources for clinical notes.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from .store import get_client
from .schemas import SaveClinicalNoteInput, SaveClinicalNoteOutput


async def save_clinical_note(input_data: SaveClinicalNoteInput) -> SaveClinicalNoteOutput:
    """Save a clinical note to the patient's chart.

    Creates a FHIR DocumentReference resource with the note content
    encoded as base64 in an attachment.

    Args:
        input_data: Note details including patient_id, note_text, note_type

    Returns:
        SaveClinicalNoteOutput with confirmation including document ID, or error
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

    except Exception as e:
        return SaveClinicalNoteOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
