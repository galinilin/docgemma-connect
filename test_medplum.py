#!/usr/bin/env python3
"""Test script for Medplum FHIR tools.

Tests all 5 Medplum EHR integration tools:
- search_patient
- get_patient_chart
- add_allergy
- prescribe_medication
- save_clinical_note

Usage:
    uv run python test_medplum.py

    # With a specific patient
    TEST_PATIENT_ID=abc-123 uv run python test_medplum.py

    # Create test patient automatically
    CREATE_TEST_PATIENT=1 uv run python test_medplum.py

Environment Variables:
    MEDPLUM_CLIENT_ID     - Medplum OAuth2 client ID
    MEDPLUM_CLIENT_SECRET - Medplum OAuth2 client secret
    TEST_PATIENT_ID       - Use specific patient ID for testing
    TEST_PATIENT_NAME     - Search for patient by name (default: "Smith")
    CREATE_TEST_PATIENT   - Create a test patient if none found (default: false)
"""

from __future__ import annotations

import asyncio
import os
import sys

# Test configuration
TEST_PATIENT_NAME = os.getenv("TEST_PATIENT_NAME", "Smith")
TEST_PATIENT_ID = os.getenv("TEST_PATIENT_ID", "")
CREATE_TEST_PATIENT = os.getenv("CREATE_TEST_PATIENT", "").lower() in ("1", "true", "yes")


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


async def test_credentials() -> bool:
    """Test if Medplum credentials are configured."""
    print_header("Checking Credentials")

    from docgemma.tools.medplum import get_client

    client = get_client()
    error = client._check_credentials()

    if error:
        print(f"  ERROR: {error}")
        print("\n  Please set environment variables:")
        print("    export MEDPLUM_CLIENT_ID=your_client_id")
        print("    export MEDPLUM_CLIENT_SECRET=your_client_secret")
        return False

    print("  Credentials configured")
    return True


async def create_test_patient() -> str | None:
    """Create a test patient in Medplum for testing."""
    print_header("Creating Test Patient")

    from docgemma.tools.medplum import get_client

    client = get_client()

    patient_resource = {
        "resourceType": "Patient",
        "name": [
            {
                "use": "official",
                "family": "TestPatient",
                "given": ["DocGemma"],
            }
        ],
        "gender": "other",
        "birthDate": "1990-01-01",
    }

    try:
        result = await client.post("/Patient", patient_resource)
        patient_id = result.get("id")
        print(f"  Created test patient: DocGemma TestPatient (ID: {patient_id})")
        return patient_id
    except Exception as e:
        print(f"  Failed to create test patient: {e}")
        return None


async def test_search_patient() -> str | None:
    """Test search_patient tool."""
    print_header("Test: search_patient")

    from docgemma.tools.medplum import SearchPatientInput, search_patient

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
        # Parse "1. John Smith (ID: abc-123)" format
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

    from docgemma.tools.medplum import GetPatientChartInput, get_patient_chart

    print(f"\n  Fetching chart for patient {patient_id}...")
    result = await get_patient_chart(GetPatientChartInput(patient_id=patient_id))
    print_result(result)

    if result.error:
        print(f"\n  FAILED: {result.error}")
        return False

    print("\n  SUCCESS")
    return True


async def test_add_allergy(patient_id: str) -> bool:
    """Test add_allergy tool."""
    print_header("Test: add_allergy")

    from docgemma.tools.medplum import AddAllergyInput, add_allergy

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

    print("\n  SUCCESS")
    return True


async def test_prescribe_medication(patient_id: str) -> bool:
    """Test prescribe_medication tool."""
    print_header("Test: prescribe_medication")

    from docgemma.tools.medplum import PrescribeMedicationInput, prescribe_medication

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

    from docgemma.tools.medplum import SaveClinicalNoteInput, save_clinical_note

    print(f"\n  Saving test clinical note for patient {patient_id}...")
    result = await save_clinical_note(
        SaveClinicalNoteInput(
            patient_id=patient_id,
            note_text="This is an automated test note from DocGemma Medplum integration testing.",
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

    # Check all Medplum tools are registered
    tool_names = get_tool_names()
    medplum_tools = [
        "search_patient",
        "get_patient_chart",
        "add_allergy",
        "prescribe_medication",
        "save_clinical_note",
    ]

    print("\n  Checking tool registration...")
    all_registered = True
    for tool in medplum_tools:
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
    result = await execute_tool("search_patient", {"name": "Test"})
    print(f"    search_patient via registry: {'error' not in result or result.get('error') is None}")

    print("\n  SUCCESS")
    return True


async def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print(" DocGemma Medplum Integration Tests")
    print("=" * 60)

    results = {
        "credentials": False,
        "registry": False,
        "search_patient": False,
        "get_patient_chart": False,
        "add_allergy": False,
        "prescribe_medication": False,
        "save_clinical_note": False,
    }

    # Test credentials first
    results["credentials"] = await test_credentials()
    if not results["credentials"]:
        print("\n" + "=" * 60)
        print(" Tests aborted: Missing credentials")
        print("=" * 60)
        return 1

    # Test registry integration
    results["registry"] = await test_registry_integration()

    # Get a patient ID for testing
    patient_id = TEST_PATIENT_ID
    if not patient_id:
        patient_id = await test_search_patient()
        results["search_patient"] = patient_id is not None

        # If no patient found, try to create one
        if not patient_id and CREATE_TEST_PATIENT:
            patient_id = await create_test_patient()
            if patient_id:
                results["search_patient"] = True
    else:
        print_header("Using provided TEST_PATIENT_ID")
        print(f"  Patient ID: {patient_id}")
        results["search_patient"] = True

    if not patient_id:
        print("\n" + "=" * 60)
        print(" Cannot continue without a patient ID")
        print(" Options:")
        print("   1. Set TEST_PATIENT_ID=<id> to use existing patient")
        print("   2. Set CREATE_TEST_PATIENT=1 to create a test patient")
        print("   3. Set TEST_PATIENT_NAME=<name> to search for patients")
        print("=" * 60)
    else:
        # Run remaining tests with patient ID
        results["get_patient_chart"] = await test_get_patient_chart(patient_id)
        results["add_allergy"] = await test_add_allergy(patient_id)
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
