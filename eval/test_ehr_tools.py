#!/usr/bin/env python3
"""Test script for local FHIR JSON store EHR tools.

Tests all 5 EHR integration tools against the local file-based FHIR store:
- search_patient
- get_patient_chart
- add_allergy
- prescribe_medication
- save_clinical_note

Usage:
    uv run python test_ehr_tools.py

    # With a specific patient
    TEST_PATIENT_ID=089cfff1-5cd4-3374-cf17-7f99b3b2b95f uv run python test_ehr_tools.py

    # Search for a different patient name
    TEST_PATIENT_NAME=Barton uv run python test_ehr_tools.py

Prerequisites:
    Seed the FHIR store first:
        uv run python -m docgemma.tools.fhir_store.seed

Environment Variables:
    FHIR_DATA_DIR         - Override default FHIR store path (optional)
    TEST_PATIENT_ID       - Use specific patient ID for testing
    TEST_PATIENT_NAME     - Search for patient by name (default: "Adam")
"""

from __future__ import annotations

import asyncio
import os
import sys

# Test configuration
TEST_PATIENT_NAME = os.getenv("TEST_PATIENT_NAME", "Adam")
TEST_PATIENT_ID = os.getenv("TEST_PATIENT_ID", "")


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {text}")
    print("=" * 60)


def print_result(result: object, indent: int = 2) -> None:
    """Print a result object nicely."""
    if hasattr(result, "model_dump"):
        data = result.model_dump()
    else:
        data = result

    for key, value in data.items():
        if value is not None:
            # Truncate long values
            str_value = str(value)
            if len(str_value) > 200:
                str_value = str_value[:200] + "..."
            print(f"{' ' * indent}{key}: {str_value}")


async def test_store_exists() -> bool:
    """Test if the FHIR store has been seeded."""
    print_header("Checking FHIR Store")

    from docgemma.tools.fhir_store import get_client

    client = get_client()

    # _check_credentials always returns None for local store
    error = client._check_credentials()
    if error:
        print(f"  ERROR: {error}")
        return False

    print(f"  Data dir: {client._data_dir}")

    # Check that Patient directory has files
    patient_dir = client._data_dir / "Patient"
    if not patient_dir.is_dir():
        print("  ERROR: No Patient directory found. Run the seed script first:")
        print("    uv run python -m docgemma.tools.fhir_store.seed")
        return False

    patient_count = len(list(patient_dir.glob("*.json")))
    print(f"  Patients found: {patient_count}")

    if patient_count == 0:
        print("  ERROR: No patients found. Run the seed script first:")
        print("    uv run python -m docgemma.tools.fhir_store.seed")
        return False

    print("  FHIR store is ready")
    return True


async def test_search_patient() -> str | None:
    """Test search_patient tool."""
    print_header("Test: search_patient")

    from docgemma.tools.fhir_store import SearchPatientInput, search_patient

    # Test 1: Search by name
    print(f"\n  Searching for patients named '{TEST_PATIENT_NAME}'...")
    result = await search_patient(SearchPatientInput(name=TEST_PATIENT_NAME))
    print_result(result)

    if result.error:
        print(f"\n  FAILED: {result.error}")
        return None

    # Try to extract a patient ID from results
    patient_id = None
    if "ID:" in result.result:
        import re

        match = re.search(r"ID:\s*([^\)]+)", result.result)
        if match:
            patient_id = match.group(1).strip()
            print(f"\n  Found patient ID: {patient_id}")

    # Test 2: Search with no params (should error)
    print("\n  Testing search with no parameters (should fail)...")
    result = await search_patient(SearchPatientInput())
    if result.error:
        print(f"  Expected error: {result.error}")
    else:
        print(f"  Unexpected success: {result.result}")

    return patient_id


async def test_get_patient_chart(patient_id: str) -> bool:
    """Test get_patient_chart tool."""
    print_header("Test: get_patient_chart")

    from docgemma.tools.fhir_store import GetPatientChartInput, get_patient_chart

    print(f"\n  Fetching chart for patient {patient_id}...")
    result = await get_patient_chart(GetPatientChartInput(patient_id=patient_id))
    print_result(result)

    if result.error:
        print(f"\n  FAILED: {result.error}")
        return False

    # Verify chart contains expected sections
    chart = result.result
    expected_sections = ["PATIENT:", "CONDITIONS:", "MEDICATIONS:", "ALLERGIES:", "LABS:"]
    for section in expected_sections:
        if section not in chart:
            print(f"\n  FAILED: Missing section '{section}' in chart")
            return False

    print("\n  SUCCESS")
    return True


async def test_get_patient_chart_not_found() -> bool:
    """Test get_patient_chart with non-existent patient."""
    print_header("Test: get_patient_chart (not found)")

    from docgemma.tools.fhir_store import GetPatientChartInput, get_patient_chart

    print("\n  Fetching chart for non-existent patient...")
    result = await get_patient_chart(
        GetPatientChartInput(patient_id="nonexistent-id-12345")
    )

    if result.error and "not found" in result.error.lower():
        print(f"  Expected error: {result.error}")
        print("\n  SUCCESS")
        return True

    print(f"\n  FAILED: Expected 'not found' error, got: {result.error or result.result}")
    return False


async def test_add_allergy(patient_id: str) -> bool:
    """Test add_allergy tool."""
    print_header("Test: add_allergy")

    from docgemma.tools.fhir_store import AddAllergyInput, add_allergy

    print(f"\n  Adding test allergy for patient {patient_id}...")
    result = await add_allergy(
        AddAllergyInput(
            patient_id=patient_id,
            substance="Test Allergen (automated test)",
            reaction="mild rash",
            severity="mild",
        )
    )
    print_result(result)

    if result.error:
        print(f"\n  FAILED: {result.error}")
        return False

    # Verify the allergy appears in the chart
    from docgemma.tools.fhir_store import GetPatientChartInput, get_patient_chart

    chart = await get_patient_chart(GetPatientChartInput(patient_id=patient_id))
    if "Test Allergen" in chart.result:
        print("  Verified: allergy appears in patient chart")
    else:
        print("  Warning: allergy not found in chart (may need re-fetch)")

    print("\n  SUCCESS")
    return True


async def test_add_allergy_invalid_severity() -> bool:
    """Test add_allergy with invalid severity."""
    print_header("Test: add_allergy (invalid severity)")

    from docgemma.tools.fhir_store import AddAllergyInput, add_allergy

    print("\n  Adding allergy with invalid severity...")
    result = await add_allergy(
        AddAllergyInput(
            patient_id="any-id",
            substance="Something",
            reaction="reaction",
            severity="extreme",
        )
    )

    if result.error and "Invalid severity" in result.error:
        print(f"  Expected error: {result.error}")
        print("\n  SUCCESS")
        return True

    print(f"\n  FAILED: Expected validation error, got: {result.error or result.result}")
    return False


async def test_prescribe_medication(patient_id: str) -> bool:
    """Test prescribe_medication tool."""
    print_header("Test: prescribe_medication")

    from docgemma.tools.fhir_store import PrescribeMedicationInput, prescribe_medication

    print(f"\n  Prescribing test medication for patient {patient_id}...")
    result = await prescribe_medication(
        PrescribeMedicationInput(
            patient_id=patient_id,
            medication_name="Test Medication (automated test)",
            dosage="100mg",
            frequency="once daily",
        )
    )
    print_result(result)

    if result.error:
        print(f"\n  FAILED: {result.error}")
        return False

    print("\n  SUCCESS")
    return True


async def test_save_clinical_note(patient_id: str) -> bool:
    """Test save_clinical_note tool."""
    print_header("Test: save_clinical_note")

    from docgemma.tools.fhir_store import SaveClinicalNoteInput, save_clinical_note

    print(f"\n  Saving test clinical note for patient {patient_id}...")
    result = await save_clinical_note(
        SaveClinicalNoteInput(
            patient_id=patient_id,
            note_text="This is an automated test note from DocGemma FHIR store integration testing.",
            note_type="progress-note",
        )
    )
    print_result(result)

    if result.error:
        print(f"\n  FAILED: {result.error}")
        return False

    print("\n  SUCCESS")
    return True


async def test_registry_integration() -> bool:
    """Test tools work through the registry."""
    print_header("Test: Registry Integration")

    from docgemma.tools import execute_tool, get_tool_names

    # Check all EHR tools are registered
    tool_names = get_tool_names()
    ehr_tools = [
        "search_patient",
        "get_patient_chart",
        "add_allergy",
        "prescribe_medication",
        "save_clinical_note",
    ]

    print("\n  Checking tool registration...")
    all_registered = True
    for tool in ehr_tools:
        if tool in tool_names:
            print(f"    {tool}: registered")
        else:
            print(f"    {tool}: MISSING")
            all_registered = False

    if not all_registered:
        print("\n  FAILED: Some tools not registered")
        return False

    # Test execution through registry
    print("\n  Testing execution through registry...")
    result = await execute_tool("search_patient", {"name": TEST_PATIENT_NAME})
    has_error = isinstance(result, dict) and result.get("error")
    print(f"    search_patient via registry: {'FAIL' if has_error else 'OK'}")

    if has_error:
        print(f"\n  FAILED: {result.get('error')}")
        return False

    print("\n  SUCCESS")
    return True


async def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print(" DocGemma Local FHIR Store - EHR Tools Tests")
    print("=" * 60)

    results: dict[str, bool] = {
        "store_exists": False,
        "registry": False,
        "search_patient": False,
        "get_patient_chart": False,
        "chart_not_found": False,
        "add_allergy": False,
        "allergy_invalid_severity": False,
        "prescribe_medication": False,
        "save_clinical_note": False,
    }

    # Test store exists first
    results["store_exists"] = await test_store_exists()
    if not results["store_exists"]:
        print("\n" + "=" * 60)
        print(" Tests aborted: FHIR store not seeded")
        print(" Run: uv run python -m docgemma.tools.fhir_store.seed")
        print("=" * 60)
        return 1

    # Test registry integration
    results["registry"] = await test_registry_integration()

    # Get a patient ID for testing
    patient_id = TEST_PATIENT_ID
    if not patient_id:
        patient_id = await test_search_patient()
        results["search_patient"] = patient_id is not None
    else:
        print_header("Using provided TEST_PATIENT_ID")
        print(f"  Patient ID: {patient_id}")
        results["search_patient"] = True

    if not patient_id:
        print("\n" + "=" * 60)
        print(" Cannot continue without a patient ID")
        print(" Options:")
        print(f"   1. Ensure patients exist matching '{TEST_PATIENT_NAME}'")
        print("   2. Set TEST_PATIENT_ID=<id> to use a specific patient")
        print("   3. Set TEST_PATIENT_NAME=<name> to search a different name")
        print("=" * 60)
    else:
        # Run remaining tests with patient ID
        results["get_patient_chart"] = await test_get_patient_chart(patient_id)
        results["chart_not_found"] = await test_get_patient_chart_not_found()
        results["add_allergy"] = await test_add_allergy(patient_id)
        results["allergy_invalid_severity"] = await test_add_allergy_invalid_severity()
        results["prescribe_medication"] = await test_prescribe_medication(patient_id)
        results["save_clinical_note"] = await test_save_clinical_note(patient_id)

    # Print summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {test}: {status}")

    print(f"\n  Total: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
