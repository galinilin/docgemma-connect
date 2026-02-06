"""Patient search tool for local FHIR JSON store.

Searches patients by name and/or date of birth using FHIR Patient resource.
"""

from __future__ import annotations

from .store import get_client
from .schemas import SearchPatientInput, SearchPatientOutput


async def search_patient(input_data: SearchPatientInput) -> SearchPatientOutput:
    """Search for patients by name and/or date of birth.

    Args:
        input_data: Search parameters (name and/or dob)

    Returns:
        SearchPatientOutput with formatted results or error
    """
    client = get_client()

    # Check credentials (always None for local store)
    cred_error = client._check_credentials()
    if cred_error:
        return SearchPatientOutput(result="", error=cred_error)

    # Build query params
    params = {}
    if input_data.name:
        params["name"] = input_data.name.strip()
    if input_data.dob:
        params["birthdate"] = input_data.dob.strip()

    if not params:
        return SearchPatientOutput(
            result="",
            error="At least one search parameter (name or dob) is required",
        )

    try:
        data = await client.get("/Patient", params=params)
        entries = data.get("entry", [])

        if not entries:
            return SearchPatientOutput(
                result="No patients found matching search criteria",
                error=None,
            )

        # Format results
        lines = [f"Found {len(entries)} patient(s):"]
        for i, entry in enumerate(entries, 1):
            resource = entry.get("resource", {})
            patient_id = resource.get("id", "unknown")

            # Extract name
            names = resource.get("name", [])
            if names:
                name_obj = names[0]
                given = " ".join(name_obj.get("given", []))
                family = name_obj.get("family", "")
                full_name = f"{given} {family}".strip() or "Unknown"
            else:
                full_name = "Unknown"

            # Extract DOB
            dob = resource.get("birthDate", "Unknown")

            lines.append(f"{i}. {full_name} (ID: {patient_id}) DOB: {dob}")

        return SearchPatientOutput(result="\n".join(lines), error=None)

    except Exception as e:
        return SearchPatientOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
