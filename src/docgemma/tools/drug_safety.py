"""Drug safety tool using OpenFDA API.

Fetches boxed warnings (black box warnings) for medications from the FDA's
drug labeling database. These are the most serious warnings issued by the FDA.
"""

from __future__ import annotations

import httpx

from .schemas import DrugSafetyInput, DrugSafetyOutput

# OpenFDA Drug Label API endpoint
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

# Request timeout in seconds
REQUEST_TIMEOUT = 30.0


async def check_drug_safety(input_data: DrugSafetyInput) -> DrugSafetyOutput:
    """Check for FDA boxed warnings on a medication.

    Queries the OpenFDA drug labeling API to retrieve any "black box" warnings
    associated with a medication. These warnings indicate serious or
    life-threatening risks.

    Args:
        input_data: The drug name to check.

    Returns:
        DrugSafetyOutput containing the warning text if found, or an indication
        that no warnings exist. Includes error details if the lookup fails.

    Example:
        >>> result = await check_drug_safety(DrugSafetyInput(brand_name="Lipitor"))
        >>> if result.has_warning:
        ...     print(result.boxed_warning)
    """
    brand_name = input_data.brand_name.strip()

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Search by brand name in OpenFDA
            params = {
                "search": f'openfda.brand_name:"{brand_name}"',
                "limit": 1,
            }

            response = await client.get(OPENFDA_LABEL_URL, params=params)

            # Handle 404 - no results found
            if response.status_code == 404:
                return DrugSafetyOutput(
                    brand_name=brand_name,
                    has_warning=False,
                    boxed_warning=None,
                    error=None,
                )

            response.raise_for_status()
            data = response.json()

            # Check if we have results
            results = data.get("results", [])
            if not results:
                return DrugSafetyOutput(
                    brand_name=brand_name,
                    has_warning=False,
                    boxed_warning=None,
                    error=None,
                )

            # Extract boxed warning if present
            label = results[0]
            boxed_warning = label.get("boxed_warning")

            # boxed_warning is typically a list of strings
            if boxed_warning:
                if isinstance(boxed_warning, list):
                    warning_text = "\n\n".join(boxed_warning)
                else:
                    warning_text = str(boxed_warning)

                return DrugSafetyOutput(
                    brand_name=brand_name,
                    has_warning=True,
                    boxed_warning=warning_text,
                    error=None,
                )

            return DrugSafetyOutput(
                brand_name=brand_name,
                has_warning=False,
                boxed_warning=None,
                error=None,
            )

    except httpx.TimeoutException:
        return DrugSafetyOutput(
            brand_name=brand_name,
            has_warning=False,
            boxed_warning=None,
            error=f"Request timed out after {REQUEST_TIMEOUT} seconds",
        )
    except httpx.HTTPStatusError as e:
        return DrugSafetyOutput(
            brand_name=brand_name,
            has_warning=False,
            boxed_warning=None,
            error=f"HTTP error {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return DrugSafetyOutput(
            brand_name=brand_name,
            has_warning=False,
            boxed_warning=None,
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )
