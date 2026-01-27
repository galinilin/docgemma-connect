"""Test script for DocGemma MCP tools.

Run with: uv run python test_tools.py
"""

import asyncio

# Import directly from tools subpackage to avoid loading torch/model
from docgemma.tools.clinical_trials import find_clinical_trials
from docgemma.tools.drug_interactions import check_drug_interactions
from docgemma.tools.drug_safety import check_drug_safety
from docgemma.tools.medical_literature import search_medical_literature
from docgemma.tools.schemas import (
    ClinicalTrialsInput,
    DrugInteractionsInput,
    DrugSafetyInput,
    MedicalLiteratureInput,
    PatientRecordsInput,
)


async def test_drug_safety():
    """Test the drug safety tool with OpenFDA."""
    print("\n" + "=" * 60)
    print("Testing: check_drug_safety")
    print("=" * 60)

    # Test with a drug known to have boxed warnings
    result = await check_drug_safety(DrugSafetyInput(brand_name="Prozac"))
    print(f"\nDrug: {result.brand_name}")
    print(f"Has Warning: {result.has_warning}")
    if result.boxed_warning:
        print(f"Warning (truncated): {result.boxed_warning}...")
    if result.error:
        print(f"Error: {result.error}")


async def test_medical_literature():
    """Test the PubMed search tool."""
    print("\n" + "=" * 60)
    print("Testing: search_medical_literature")
    print("=" * 60)

    result = await search_medical_literature(
        MedicalLiteratureInput(query="diabetes treatment guidelines", max_results=2)
    )
    print(f"\nQuery: {result.query}")
    print(f"Total Found: {result.total_found}")
    print(f"Articles returned: {len(result.articles)}")

    for article in result.articles:
        print(f"\n  - PMID: {article.pmid}")
        print(f"    Title: {article.title}...")
        print(f"    Authors: {article.authors}")
        print(f"    Journal: {article.journal}")

    if result.error:
        print(f"Error: {result.error}")


async def test_drug_interactions():
    """Test the drug interactions tool with RxNav."""
    print("\n" + "=" * 60)
    print("Testing: check_drug_interactions")
    print("=" * 60)

    # Test with drugs known to interact
    result = await check_drug_interactions(
        DrugInteractionsInput(drugs=["warfarin", "aspirin", "ibuprofen"])
    )
    print(f"\nDrugs checked: {result.drugs_checked}")
    print(f"Resolved RxCUIs: {result.resolved_rxcuis}")
    print(f"Interactions found: {len(result.interactions)}")

    for interaction in result.interactions[:3]:  # Show first 3
        print(f"\n  - Pair: {interaction.drug_pair}")
        print(f"    Severity: {interaction.severity}")
        print(f"    Description: {interaction.description}...")

    if result.error:
        print(f"Error: {result.error}")


async def test_clinical_trials():
    """Test the clinical trials search tool."""
    print("\n" + "=" * 60)
    print("Testing: find_clinical_trials")
    print("=" * 60)

    # Test with a common condition
    result = await find_clinical_trials(
        ClinicalTrialsInput(condition="lung cancer", location="California")
    )
    print(f"\nCondition: {result.condition}")
    print(f"Location: {result.location}")
    print(f"Total recruiting trials found: {result.total_found}")
    print(f"Trials returned: {len(result.trials)}")

    for trial in result.trials:
        print(f"\n  - NCT ID: {trial.nct_id}")
        print(f"    Title: {trial.title[:80]}...")
        print(f"    Status: {trial.status}")
        print(f"    Conditions: {', '.join(trial.conditions[:2])}")
        if trial.locations:
            print(f"    Locations: {', '.join(trial.locations[:2])}")
        if trial.contact_email:
            print(f"    Contact: {trial.contact_email}")

    if result.error:
        print(f"Error: {result.error}")


async def main():
    """Run all tool tests."""
    print("\nDocGemma MCP Tools Test Suite")
    print("=" * 60)

    await test_drug_safety()
    await test_medical_literature()
    await test_drug_interactions()
    await test_clinical_trials()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
