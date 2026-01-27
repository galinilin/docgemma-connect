"""Clinical trials search tool using ClinicalTrials.gov API v2.

Searches for actively recruiting clinical trials to help patients find
experimental treatments when standard care options are exhausted.
"""

from __future__ import annotations

import httpx

from .schemas import ClinicalTrial, ClinicalTrialsInput, ClinicalTrialsOutput

# ClinicalTrials.gov API v2 endpoint
CLINICALTRIALS_API_URL = "https://clinicaltrials.gov/api/v2/studies"

# Request timeout in seconds
REQUEST_TIMEOUT = 30.0

# Maximum results to return (to save context tokens)
MAX_RESULTS = 3


async def find_clinical_trials(
    input_data: ClinicalTrialsInput,
) -> ClinicalTrialsOutput:
    """Search for actively recruiting clinical trials on ClinicalTrials.gov.

    This tool searches ONLY for trials with status "RECRUITING", meaning they
    are actively enrolling patients. Use this to help patients find experimental
    treatments when standard care has failed or is unavailable.

    Args:
        input_data: The condition to search for and optional location filter.

    Returns:
        ClinicalTrialsOutput containing up to 3 relevant recruiting trials
        with contact information and study locations.

    Example:
        >>> result = await find_clinical_trials(
        ...     ClinicalTrialsInput(condition="lung cancer", location="California")
        ... )
        >>> for trial in result.trials:
        ...     print(f"{trial.nct_id}: {trial.title}")
    """
    condition = input_data.condition.strip()
    location = input_data.location.strip() if input_data.location else None

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Build query parameters for API v2
            params = {
                "query.cond": condition,
                "filter.overallStatus": "RECRUITING",
                "pageSize": MAX_RESULTS,
                "format": "json",
                # Request specific fields to reduce response size
                "fields": (
                    "NCTId,BriefTitle,OfficialTitle,OverallStatus,"
                    "Condition,LocationCity,LocationState,LocationCountry,"
                    "CentralContactName,CentralContactPhone,CentralContactEMail,"
                    "LocationContactName,LocationContactPhone,LocationContactEMail"
                ),
            }

            # Add location filter if provided
            if location:
                params["query.locn"] = location

            response = await client.get(CLINICALTRIALS_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse response
            studies = data.get("studies", [])
            total_count = data.get("totalCount", 0)

            trials = []
            for study in studies:
                trial = _parse_study(study)
                if trial:
                    trials.append(trial)

            return ClinicalTrialsOutput(
                condition=condition,
                location=location,
                total_found=total_count,
                trials=trials,
                error=None,
            )

    except httpx.TimeoutException:
        return ClinicalTrialsOutput(
            condition=condition,
            location=location,
            total_found=0,
            trials=[],
            error=f"Request timed out after {REQUEST_TIMEOUT} seconds",
        )
    except httpx.HTTPStatusError as e:
        return ClinicalTrialsOutput(
            condition=condition,
            location=location,
            total_found=0,
            trials=[],
            error=f"HTTP error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return ClinicalTrialsOutput(
            condition=condition,
            location=location,
            total_found=0,
            trials=[],
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


def _parse_study(study: dict) -> ClinicalTrial | None:
    """Parse a study object from the API response.

    Args:
        study: Raw study dict from API response.

    Returns:
        Parsed ClinicalTrial or None if parsing fails.
    """
    try:
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        contacts_module = protocol.get("contactsLocationsModule", {})

        # Extract NCT ID
        nct_id = id_module.get("nctId", "Unknown")

        # Extract title (prefer official, fall back to brief)
        title = id_module.get("officialTitle") or id_module.get("briefTitle", "No title")

        # Extract status
        status = status_module.get("overallStatus", "Unknown")

        # Extract conditions
        conditions = conditions_module.get("conditions", [])

        # Extract central contact info
        central_contacts = contacts_module.get("centralContacts", [])
        contact_name = None
        contact_phone = None
        contact_email = None

        if central_contacts:
            primary_contact = central_contacts[0]
            contact_name = primary_contact.get("name")
            contact_phone = primary_contact.get("phone")
            contact_email = primary_contact.get("email")

        # Extract locations
        locations_list = contacts_module.get("locations", [])
        locations = []

        for loc in locations_list[:5]:  # Limit to 5 locations
            city = loc.get("city", "")
            state = loc.get("state", "")
            country = loc.get("country", "")

            parts = [p for p in [city, state, country] if p]
            if parts:
                locations.append(", ".join(parts))

            # If no central contact, try to get from first location
            if not contact_name and loc.get("contacts"):
                loc_contact = loc["contacts"][0]
                contact_name = contact_name or loc_contact.get("name")
                contact_phone = contact_phone or loc_contact.get("phone")
                contact_email = contact_email or loc_contact.get("email")

        return ClinicalTrial(
            nct_id=nct_id,
            title=title,
            status=status,
            conditions=conditions,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            locations=locations,
        )

    except Exception:
        return None
