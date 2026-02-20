"""Patient chart retrieval tool for local FHIR JSON store.

Retrieves comprehensive patient chart including demographics, conditions,
medications, allergies, vital signs, labs, imaging studies, encounters,
clinical notes, and screenings.
"""

from __future__ import annotations

import base64
from typing import Any

from .store import ResourceNotFoundError, get_client
from .schemas import GetPatientChartInput, GetPatientChartOutput


async def get_patient_chart(input_data: GetPatientChartInput) -> GetPatientChartOutput:
    """Retrieve a patient's full clinical chart.

    Fetches ALL available data for the patient across every FHIR resource
    type: demographics, conditions, medications, allergies, vital signs,
    laboratory results, imaging studies, encounters, clinical notes, and
    screening reports.

    Args:
        input_data: Patient ID to retrieve

    Returns:
        GetPatientChartOutput with formatted clinical summary or error
    """
    client = get_client()
    patient_id = input_data.patient_id.strip()

    cred_error = client._check_credentials()
    if cred_error:
        return GetPatientChartOutput(result="", error=cred_error)

    try:
        patient_data = await client.get(f"/Patient/{patient_id}")

        patient_name = _extract_patient_name(patient_data)
        patient_gender = patient_data.get("gender", "unknown")[0].upper()
        patient_dob = patient_data.get("birthDate", "unknown")

        # -- Collect every resource type --------------------------------

        conditions: list[str] = []
        medications: list[str] = []
        allergies: list[str] = []
        vitals: list[str] = []
        labs: list[str] = []
        imaging: list[str] = []
        encounters: list[str] = []
        notes: list[str] = []
        screenings: list[str] = []

        # Conditions (all)
        try:
            data = await client.get(
                "/Condition", params={"subject": patient_id}
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                text = _codeable_text(r.get("code", {}))
                if text:
                    clinical_status = _codeable_text(r.get("clinicalStatus", {}))
                    if clinical_status and clinical_status.lower() != "active":
                        text = f"{text} ({clinical_status})"
                    conditions.append(text)
        except Exception:
            pass

        # Medications (all active)
        try:
            data = await client.get(
                "/MedicationRequest",
                params={"subject": patient_id, "status": "active"},
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                med = r.get("medicationCodeableConcept", {})
                text = med.get("text") or _get_coding_display(med)
                dosage_list = r.get("dosageInstruction", [])
                if dosage_list and text:
                    dosage = dosage_list[0].get("text", "")
                    if dosage:
                        text = f"{text} {dosage}"
                if text:
                    medications.append(text)
        except Exception:
            pass

        # Allergies (all)
        try:
            data = await client.get(
                "/AllergyIntolerance", params={"patient": patient_id}
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                substance = _codeable_text(r.get("code", {}))
                if not substance:
                    continue
                severity = r.get("criticality", "")
                reactions = r.get("reaction", [])
                reaction_text = ""
                if reactions:
                    manifestations = reactions[0].get("manifestation", [])
                    if manifestations:
                        reaction_text = (
                            manifestations[0].get("text")
                            or _get_coding_display(manifestations[0])
                        )
                parts = [substance]
                detail = ", ".join(filter(None, [severity, reaction_text]))
                if detail:
                    parts.append(f"({detail})")
                allergies.append(" ".join(parts))
        except Exception:
            pass

        # Vital signs (all)
        try:
            data = await client.get(
                "/Observation",
                params={
                    "subject": patient_id,
                    "category": "vital-signs",
                    "_sort": "-date",
                },
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                if r.get("resourceType") == "Observation":
                    formatted = _format_observation(r)
                    if formatted:
                        vitals.append(formatted)
        except Exception:
            pass

        # Labs (all)
        try:
            data = await client.get(
                "/Observation",
                params={
                    "subject": patient_id,
                    "category": "laboratory",
                    "_sort": "-date",
                },
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                if r.get("resourceType") == "Observation":
                    formatted = _format_observation(r)
                    if formatted:
                        labs.append(formatted)
        except Exception:
            pass

        # Imaging studies — Media resources (text report only, no image)
        try:
            data = await client.get(
                "/Media", params={"subject": patient_id, "_sort": "-date"}
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                if r.get("resourceType") == "Media":
                    formatted = _format_imaging(r)
                    if formatted:
                        imaging.append(formatted)
        except Exception:
            pass

        # Encounters (all)
        try:
            data = await client.get(
                "/Encounter", params={"subject": patient_id, "_sort": "-date"}
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                if r.get("resourceType") == "Encounter":
                    formatted = _format_encounter(r)
                    if formatted:
                        encounters.append(formatted)
        except Exception:
            pass

        # Clinical notes — DocumentReference (all, base64-decoded)
        try:
            data = await client.get(
                "/DocumentReference",
                params={"subject": patient_id, "_sort": "-date"},
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                if r.get("resourceType") == "DocumentReference":
                    formatted = _format_document(r)
                    if formatted:
                        notes.append(formatted)
        except Exception:
            pass

        # Screenings — DiagnosticReport (all)
        try:
            data = await client.get(
                "/DiagnosticReport",
                params={"subject": patient_id, "_sort": "-date"},
            )
            for entry in data.get("entry", []):
                r = entry.get("resource", {})
                if r.get("resourceType") == "DiagnosticReport":
                    formatted = _format_screening(r)
                    if formatted:
                        screenings.append(formatted)
        except Exception:
            pass

        # -- Build output -----------------------------------------------

        lines = [f"PATIENT: {patient_name} ({patient_gender}, DOB: {patient_dob})"]

        lines.append(
            f"CONDITIONS: {', '.join(conditions) if conditions else 'None documented'}"
        )
        lines.append(
            f"MEDICATIONS: {', '.join(medications) if medications else 'None active'}"
        )
        lines.append(
            f"ALLERGIES: {', '.join(allergies) if allergies else 'NKDA'}"
        )

        if vitals:
            lines.append("VITAL SIGNS:")
            for v in vitals:
                lines.append(f"  {v}")
        else:
            lines.append("VITAL SIGNS: None recorded")

        if labs:
            lines.append("LABS:")
            for lab in labs:
                lines.append(f"  {lab}")
        else:
            lines.append("LABS: None recent")

        if imaging:
            lines.append("IMAGING:")
            for img in imaging:
                lines.append(f"  {img}")
        else:
            lines.append("IMAGING: None on file")

        if encounters:
            lines.append("ENCOUNTERS:")
            for enc in encounters:
                lines.append(f"  {enc}")
        else:
            lines.append("ENCOUNTERS: None documented")

        if screenings:
            lines.append("SCREENINGS:")
            for scr in screenings:
                lines.append(f"  {scr}")
        else:
            lines.append("SCREENINGS: None on file")

        if notes:
            lines.append("CLINICAL NOTES:")
            for note in notes:
                lines.append(f"  {note}")
        else:
            lines.append("CLINICAL NOTES: None on file")

        return GetPatientChartOutput(result="\n".join(lines), error=None)

    except ResourceNotFoundError:
        return GetPatientChartOutput(
            result="",
            error=f"Patient not found: {patient_id}",
        )
    except Exception as e:
        return GetPatientChartOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


# ======================================================================
# Helpers
# ======================================================================


def _extract_patient_name(patient: dict) -> str:
    """Extract formatted patient name from FHIR Patient resource."""
    names = patient.get("name", [])
    if names:
        name_obj = names[0]
        given = " ".join(name_obj.get("given", []))
        family = name_obj.get("family", "")
        return f"{given} {family}".strip() or "Unknown"
    return "Unknown"


def _get_coding_display(codeable_concept: dict) -> str:
    """Extract display text from a CodeableConcept."""
    codings = codeable_concept.get("coding", [])
    if codings:
        return codings[0].get("display", "")
    return ""


def _codeable_text(cc: dict) -> str:
    """Get human-readable text from a CodeableConcept (text first, then coding display)."""
    return cc.get("text") or _get_coding_display(cc)


def _interpretation_flag(observation: dict) -> str:
    """Extract interpretation code (e.g. H, L, HH, LL) from an Observation."""
    interps = observation.get("interpretation", [])
    if interps:
        codings = interps[0].get("coding", [])
        if codings:
            return codings[0].get("code", "")
    return ""


def _observation_value(obs: dict) -> str:
    """Extract the value string from an Observation (top-level or components)."""
    # Component-based observations (e.g. blood pressure panel)
    components = obs.get("component", [])
    if components:
        parts = []
        for comp in components:
            comp_name = _get_coding_display(comp.get("code", {}))
            comp_val = _quantity_str(comp)
            if comp_name and comp_val:
                parts.append(f"{comp_name} {comp_val}")
        if parts:
            return "; ".join(parts)

    # Simple value
    return _quantity_str(obs)


def _quantity_str(obs_or_component: dict) -> str:
    """Format valueQuantity / valueString / valueCodeableConcept."""
    if "valueQuantity" in obs_or_component:
        vq = obs_or_component["valueQuantity"]
        return f"{vq.get('value', '')} {vq.get('unit', '')}".strip()
    if "valueString" in obs_or_component:
        return obs_or_component["valueString"]
    if "valueCodeableConcept" in obs_or_component:
        return _codeable_text(obs_or_component["valueCodeableConcept"])
    return ""


def _format_observation(observation: dict) -> str | None:
    """Format an Observation as a single-line string with value, flag, and date."""
    code = observation.get("code", {})
    name = _codeable_text(code)
    if not name:
        return None

    value = _observation_value(observation)
    if not value:
        return None

    flag = _interpretation_flag(observation)
    date = observation.get("effectiveDateTime", "")[:10]

    parts = [name, value]
    if flag:
        parts.append(f"[{flag}]")
    if date:
        parts.append(f"({date})")

    result = " ".join(parts)

    # Append clinical note if present
    obs_notes = observation.get("note", [])
    if obs_notes:
        note_text = obs_notes[0].get("text", "")
        if note_text:
            result += f" — {note_text}"

    return result


def _format_imaging(media: dict) -> str | None:
    """Format a Media resource: modality, title, date, and text report (no image)."""
    modality = _get_coding_display(media.get("modality", {})) or "Unknown modality"
    title = media.get("content", {}).get("title", "")
    body_site = _get_coding_display(media.get("bodySite", {}))
    date = (media.get("createdDateTime") or "")[:10]

    # Text report from note[]
    report = ""
    media_notes = media.get("note", [])
    if media_notes:
        report = media_notes[0].get("text", "")

    if not title and not report:
        return None

    header_parts = [modality]
    if body_site:
        header_parts.append(body_site)
    if title:
        header_parts.append(f'"{title}"')
    if date:
        header_parts.append(f"({date})")
    header = " — ".join(filter(None, [" ".join(header_parts)]))

    if report:
        return f"{header}: {report}"
    return header


def _format_encounter(encounter: dict) -> str | None:
    """Format an Encounter: type, status, period, and reason."""
    enc_types = encounter.get("type", [])
    type_text = _get_coding_display(enc_types[0]) if enc_types else ""

    enc_class = encounter.get("class", {})
    class_text = enc_class.get("display", "")

    status = encounter.get("status", "")
    period = encounter.get("period", {})
    start = (period.get("start") or "")[:10]
    end = (period.get("end") or "")[:10]

    reason_parts = []
    for rc in encounter.get("reasonCode", []):
        reason_text = rc.get("text") or _get_coding_display(rc)
        if reason_text:
            reason_parts.append(reason_text)

    label = type_text or class_text or "Encounter"
    parts = [label]
    if status:
        parts.append(f"[{status}]")
    if start:
        date_range = start
        if end and end != start:
            date_range = f"{start} to {end}"
        parts.append(f"({date_range})")
    result = " ".join(parts)

    if reason_parts:
        result += f" — {'; '.join(reason_parts)}"

    return result


def _format_document(doc_ref: dict) -> str | None:
    """Format a DocumentReference: type, author, date, and decoded text content."""
    doc_type = _get_coding_display(doc_ref.get("type", {})) or "Document"
    date = (doc_ref.get("date") or "")[:10]

    authors = doc_ref.get("author", [])
    author = authors[0].get("display", "") if authors else ""

    # Decode base64 content
    content_text = ""
    contents = doc_ref.get("content", [])
    if contents:
        attachment = contents[0].get("attachment", {})
        b64_data = attachment.get("data", "")
        if b64_data:
            try:
                content_text = base64.b64decode(b64_data).decode("utf-8")
            except Exception:
                content_text = ""

    header_parts = [doc_type]
    if author:
        header_parts.append(author)
    if date:
        header_parts.append(date)
    header = " — ".join(header_parts)

    if content_text:
        return f"[{header}]\n    {content_text}"
    return f"[{header}]"


def _format_screening(report: dict) -> str | None:
    """Format a DiagnosticReport as a screening result."""
    code = report.get("code", {})
    name = _codeable_text(code)
    if not name:
        return None

    status = report.get("status", "")
    date = (report.get("effectiveDateTime") or report.get("issued") or "")[:10]
    conclusion = report.get("conclusion", "")

    parts = [name]
    if status:
        parts.append(f"[{status}]")
    if date:
        parts.append(f"({date})")
    result = " ".join(parts)

    if conclusion:
        result += f" — {conclusion}"

    # presentedForm text fallback
    if not conclusion:
        for form in report.get("presentedForm", []):
            b64 = form.get("data", "")
            if b64:
                try:
                    result += f" — {base64.b64decode(b64).decode('utf-8')}"
                except Exception:
                    pass
                break

    return result
