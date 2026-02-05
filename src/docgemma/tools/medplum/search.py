"""Patient search tool for Medplum FHIR API.

Searches patients by name and/or date of birth using FHIR Patient resource.
"""

from __future__ import annotations

import httpx

from .client import get_client
from .schemas import SearchPatientInput, SearchPatientOutput


async def search_patient(input_data: SearchPatientInput) -> SearchPatientOutput:
    """Search for patients by name and/or date of birth.

    Args:
        input_data: Search parameters (name and/or dob)

    Returns:
        SearchPatientOutput with formatted results or error

    Example:
        >>> result = await search_patient(SearchPatientInput(name="Smith"))
        >>> print(result.result)
        Found 2 patients:
        1. John Smith (ID: abc-123) DOB: 1978-03-15
        2. Jane Smith (ID: def-456) DOB: 1985-07-22
    """
    client = get_client()

    # Check credentials
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

    except httpx.TimeoutException:
        return SearchPatientOutput(
            result="",
            error="Request timed out while searching patients",
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return SearchPatientOutput(
                result="",
                error="Authentication failed - check Medplum credentials",
            )
        return SearchPatientOutput(
            result="",
            error=f"EHR error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return SearchPatientOutput(
            result="",
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
