"""Medical imaging endpoints.

Provides upload and serving of imaging studies (JPEG/PNG) stored as
FHIR R4 Media resources with image files on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from ..models.responses import ImagingResponse
from ...tools.fhir_store import get_client

router = APIRouter(tags=["imaging"])

# Imaging files directory (sibling to data/fhir/)
_IMAGING_DIR = Path(__file__).resolve().parents[4] / "data" / "imaging"

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_CONTENT_TYPE_EXT = {"image/jpeg": "jpg", "image/png": "png"}

_MODALITY_DISPLAY = {
    "CT": "Computed Tomography",
    "DX": "Digital Radiography",
    "MR": "Magnetic Resonance",
    "SM": "Slide Microscopy",
    "PT": "Pathology",
    "OP": "Ophthalmic Photography",
    "XC": "External-camera Photography",
}


@router.post("/patients/{patient_id}/imaging", response_model=ImagingResponse, status_code=201)
async def upload_imaging(
    patient_id: str,
    file: UploadFile = File(...),
    modality: str = Form(...),
    body_site: str = Form(""),
    study_date: str = Form(""),
    description: str = Form(""),
    report: str = Form(""),
    report_author: str = Form(""),
) -> ImagingResponse:
    """Upload a medical image and create a FHIR Media resource."""
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        return ImagingResponse(
            success=False,
            message="",
            error=f"Invalid file type: {content_type}. Only JPEG and PNG are supported.",
        )

    # Read file and check size
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        return ImagingResponse(
            success=False,
            message="",
            error=f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). Maximum is 10 MB.",
        )

    # Create FHIR Media resource
    client = get_client()
    modality_display = _MODALITY_DISPLAY.get(modality, modality)
    ext = _CONTENT_TYPE_EXT.get(content_type, "jpg")

    media_resource = {
        "resourceType": "Media",
        "status": "completed",
        "type": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/media-type",
                    "code": "image",
                }
            ]
        },
        "modality": {
            "coding": [
                {
                    "system": "http://dicom.nema.org/resources/ontology/DCM",
                    "code": modality,
                    "display": modality_display,
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "createdDateTime": study_date or "",
        "content": {
            "contentType": content_type,
            "url": "",  # Patched after we know the ID
            "title": f"{modality_display} study",
        },
    }

    if body_site.strip():
        media_resource["bodySite"] = {"text": body_site.strip()}

    notes = []
    if description.strip():
        notes.append({"text": description.strip()})
    if report.strip():
        notes.append({
            "authorString": f"Report:{report_author.strip() or 'Unknown'}",
            "text": report.strip(),
        })
    if notes:
        media_resource["note"] = notes

    try:
        result = await client.post("/Media", media_resource)
        media_id = result["id"]

        # Save image file to disk
        _IMAGING_DIR.mkdir(parents=True, exist_ok=True)
        image_path = _IMAGING_DIR / f"{media_id}.{ext}"
        image_path.write_bytes(file_bytes)

        # Patch the FHIR resource with the correct URL
        result["content"]["url"] = f"/api/imaging/{media_id}"
        fhir_path = Path(client._data_dir) / "Media" / f"{media_id}.json"
        fhir_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        return ImagingResponse(
            success=True,
            media_id=media_id,
            message=f"Imaging study uploaded successfully (Media ID: {media_id})",
        )

    except Exception as e:
        return ImagingResponse(
            success=False,
            message="",
            error=f"Failed to upload imaging study: {e}",
        )


@router.delete("/imaging/{media_id}", response_model=ImagingResponse)
async def delete_imaging(media_id: str) -> ImagingResponse:
    """Delete an imaging study (FHIR Media resource + image file)."""
    client = get_client()

    # Delete FHIR resource
    try:
        await client.delete(f"/Media/{media_id}")
    except Exception as e:
        return ImagingResponse(
            success=False,
            message="",
            error=f"Failed to delete imaging resource: {e}",
        )

    # Delete image file from disk
    if _IMAGING_DIR.is_dir():
        for candidate in _IMAGING_DIR.iterdir():
            if candidate.stem == media_id:
                candidate.unlink()
                break

    return ImagingResponse(
        success=True,
        media_id=media_id,
        message="Imaging study deleted successfully",
    )


@router.get("/imaging/{media_id}")
async def get_imaging_file(media_id: str) -> FileResponse:
    """Serve an imaging file by media resource ID."""
    if not _IMAGING_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Imaging file not found")

    # Find the file with any extension
    for candidate in _IMAGING_DIR.iterdir():
        if candidate.stem == media_id:
            ext = candidate.suffix.lstrip(".")
            media_type = "image/png" if ext == "png" else "image/jpeg"
            return FileResponse(
                path=str(candidate),
                media_type=media_type,
                filename=candidate.name,
            )

    raise HTTPException(status_code=404, detail="Imaging file not found")
