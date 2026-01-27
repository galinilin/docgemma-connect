"""Drug interactions tool using OpenFDA drug labeling API.

Checks for drug interaction warnings by querying FDA drug labels.
Since the NIH RxNav drug interaction API was discontinued in January 2024,
this tool extracts interaction information from FDA-approved drug labels.
"""

from __future__ import annotations

import httpx

from .schemas import DrugInteraction, DrugInteractionsInput, DrugInteractionsOutput

# OpenFDA Drug Label API endpoint
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

# Request timeout in seconds
REQUEST_TIMEOUT = 30.0


async def check_drug_interactions(
    input_data: DrugInteractionsInput,
) -> DrugInteractionsOutput:
    """Check for drug interactions using FDA drug labeling data.

    Queries the OpenFDA drug label API to extract "drug_interactions" sections
    from approved drug labels. This provides official FDA-reviewed interaction
    information.

    Note: The NIH RxNav drug-drug interaction API was discontinued in Jan 2024.
    This tool uses OpenFDA labels as an alternative source.

    Args:
        input_data: List of drug names to check for interactions.

    Returns:
        DrugInteractionsOutput containing interaction warnings found in labels.

    Example:
        >>> result = await check_drug_interactions(
        ...     DrugInteractionsInput(drugs=["warfarin", "aspirin"])
        ... )
        >>> for interaction in result.interactions:
        ...     print(f"{interaction.drug_pair}: {interaction.description}")
    """
    drugs = [d.strip().lower() for d in input_data.drugs]

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            interactions: list[DrugInteraction] = []
            resolved_rxcuis: dict[str, str | None] = {}

            # For each drug, fetch its label and look for interactions with other drugs
            for drug in drugs:
                label_data = await _fetch_drug_label(client, drug)

                if label_data is None:
                    resolved_rxcuis[drug] = None
                    continue

                # Mark as found (using brand name from label as "ID")
                brand_name = _extract_brand_name(label_data)
                resolved_rxcuis[drug] = brand_name or drug

                # Extract interaction warnings
                drug_interactions_text = label_data.get("drug_interactions", [])

                if drug_interactions_text:
                    # Check if any of the other drugs are mentioned
                    interaction_text = " ".join(drug_interactions_text).lower()

                    for other_drug in drugs:
                        if other_drug != drug and other_drug in interaction_text:
                            # Found a potential interaction
                            interactions.append(
                                DrugInteraction(
                                    drug_pair=(drug, other_drug),
                                    severity="See label",
                                    description=_extract_relevant_text(
                                        drug_interactions_text, other_drug
                                    ),
                                )
                            )

            # Deduplicate interactions (A-B and B-A are the same)
            unique_interactions = _deduplicate_interactions(interactions)

            if not resolved_rxcuis or all(v is None for v in resolved_rxcuis.values()):
                return DrugInteractionsOutput(
                    drugs_checked=drugs,
                    resolved_rxcuis=resolved_rxcuis,
                    interactions=[],
                    error="Could not find FDA label data for any of the provided drugs.",
                )

            return DrugInteractionsOutput(
                drugs_checked=drugs,
                resolved_rxcuis=resolved_rxcuis,
                interactions=unique_interactions,
                error=None,
            )

    except httpx.TimeoutException:
        return DrugInteractionsOutput(
            drugs_checked=drugs,
            resolved_rxcuis={},
            interactions=[],
            error=f"Request timed out after {REQUEST_TIMEOUT} seconds",
        )
    except Exception as e:
        return DrugInteractionsOutput(
            drugs_checked=drugs,
            resolved_rxcuis={},
            interactions=[],
            error=f"Unexpected error: {type(e).__name__}: {e}",
        )


async def _fetch_drug_label(
    client: httpx.AsyncClient, drug_name: str
) -> dict | None:
    """Fetch drug label from OpenFDA.

    Args:
        client: HTTP client instance.
        drug_name: The drug name to look up.

    Returns:
        The label data dict if found, None otherwise.
    """
    try:
        # Search by brand name or generic name
        params = {
            "search": f'(openfda.brand_name:"{drug_name}") OR (openfda.generic_name:"{drug_name}")',
            "limit": 1,
        }

        response = await client.get(OPENFDA_LABEL_URL, params=params)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if results:
            return results[0]

        return None
    except Exception:
        return None


def _extract_brand_name(label_data: dict) -> str | None:
    """Extract brand name from label data."""
    openfda = label_data.get("openfda", {})
    brand_names = openfda.get("brand_name", [])
    if brand_names:
        return brand_names[0]
    return None


def _extract_relevant_text(interaction_texts: list[str], drug_name: str) -> str:
    """Extract the most relevant interaction text mentioning the drug.

    Args:
        interaction_texts: List of interaction text sections.
        drug_name: The drug to find mentions of.

    Returns:
        The most relevant text snippet (truncated if long).
    """
    full_text = " ".join(interaction_texts)
    drug_lower = drug_name.lower()

    # Find sentences mentioning the drug
    sentences = full_text.replace("\n", " ").split(".")
    relevant = []

    for sentence in sentences:
        if drug_lower in sentence.lower():
            cleaned = sentence.strip()
            if cleaned:
                relevant.append(cleaned + ".")

    if relevant:
        # Return first 2 relevant sentences, max 500 chars
        result = " ".join(relevant[:2])
        if len(result) > 500:
            return result[:497] + "..."
        return result

    # Fallback: return truncated full text
    if len(full_text) > 300:
        return full_text[:297] + "..."
    return full_text


def _deduplicate_interactions(
    interactions: list[DrugInteraction],
) -> list[DrugInteraction]:
    """Remove duplicate interactions (A-B same as B-A).

    Args:
        interactions: List of interactions to deduplicate.

    Returns:
        Deduplicated list of interactions.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[DrugInteraction] = []

    for interaction in interactions:
        # Create normalized key (alphabetically sorted pair)
        pair = tuple(sorted(interaction.drug_pair))
        if pair not in seen:
            seen.add(pair)
            unique.append(interaction)

    return unique
