"""Seed the local FHIR JSON store from Synthea bundles.

Parses Synthea FHIR Bundle JSON files and extracts individual resources
into ``data/fhir/{ResourceType}/{id}.json``.

Usage:
    uv run python -m docgemma.tools.fhir_store.seed
"""

from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from pathlib import Path

# Resource types we care about for the EHR UI
SUPPORTED_TYPES = {
    "Patient",
    "Condition",
    "MedicationRequest",
    "AllergyIntolerance",
    "Observation",
    "DocumentReference",
}

# Default paths (relative to docgemma-connect/)
_CONNECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_BUNDLE_DIR = _CONNECT_ROOT.parent / "docgemma-synthea" / "output" / "fhir_augmented"
_DEFAULT_DATA_DIR = _CONNECT_ROOT / "data" / "fhir"


def seed(
    bundle_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> None:
    """Extract FHIR resources from Synthea bundles into the local store.

    Args:
        bundle_dir: Directory containing Synthea ``*.json`` bundles.
        data_dir:   Target directory for individual resource files.
    """
    bundle_dir = Path(bundle_dir or os.getenv("SYNTHEA_BUNDLE_DIR", str(_DEFAULT_BUNDLE_DIR)))
    data_dir = Path(data_dir or os.getenv("FHIR_DATA_DIR", str(_DEFAULT_DATA_DIR)))

    if not bundle_dir.is_dir():
        print(f"ERROR: Bundle directory not found: {bundle_dir}")
        return

    bundle_files = sorted(bundle_dir.glob("*.json"))
    if not bundle_files:
        print(f"ERROR: No JSON files found in {bundle_dir}")
        return

    print(f"Seeding from {len(bundle_files)} bundles in {bundle_dir}")
    print(f"Target: {data_dir}")

    stats: Counter[str] = Counter()

    for bundle_file in bundle_files:
        bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
        entries = bundle.get("entry", [])

        # First pass: build a map of urn:uuid -> Patient/{id} for reference rewriting
        patient_id: str | None = None
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Patient":
                patient_id = resource.get("id")
                break

        if not patient_id:
            print(f"  SKIP {bundle_file.name}: no Patient resource found")
            continue

        urn_prefix = f"urn:uuid:{patient_id}"

        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")

            if resource_type not in SUPPORTED_TYPES:
                continue

            resource_id = resource.get("id")
            if not resource_id:
                continue

            # Rewrite urn:uuid references to Patient/{id} format
            _rewrite_references(resource, patient_id)

            # Write to disk
            dest_dir = data_dir / resource_type
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{resource_id}.json"
            dest.write_text(json.dumps(resource, indent=2), encoding="utf-8")

            stats[resource_type] += 1

    # Synthea bundles typically don't include AllergyIntolerance resources.
    # Seed a few sample allergies so the UI has data to display.
    _seed_sample_allergies(data_dir, stats)

    print("\nSeeded resources:")
    for rtype in sorted(stats):
        print(f"  {rtype}: {stats[rtype]}")
    print(f"  TOTAL: {sum(stats.values())}")


def _rewrite_references(resource: dict, patient_id: str) -> None:
    """Recursively rewrite ``urn:uuid:{patient_id}`` → ``Patient/{patient_id}``."""
    urn = f"urn:uuid:{patient_id}"
    target = f"Patient/{patient_id}"

    def _walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "reference" and isinstance(value, str) and value == urn:
                    obj[key] = target
                else:
                    _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(resource)


def _seed_sample_allergies(data_dir: Path, stats: Counter) -> None:
    """Add sample AllergyIntolerance resources for demo patients.

    Only adds allergies if none exist yet for a patient.
    """
    patient_dir = data_dir / "Patient"
    allergy_dir = data_dir / "AllergyIntolerance"

    if not patient_dir.is_dir():
        return

    # Check which patients already have allergies
    existing_allergy_patients: set[str] = set()
    if allergy_dir.is_dir():
        for f in allergy_dir.iterdir():
            if f.suffix == ".json":
                allergy = json.loads(f.read_text(encoding="utf-8"))
                ref = allergy.get("patient", {}).get("reference", "")
                if ref.startswith("Patient/"):
                    existing_allergy_patients.add(ref.split("/", 1)[1])

    # Sample allergies to add (one per patient that lacks them)
    sample_allergies = [
        {"substance": "Penicillin", "reaction": "Hives", "severity": "moderate", "criticality": "low"},
        {"substance": "Sulfonamide", "reaction": "Rash", "severity": "mild", "criticality": "low"},
        {"substance": "Aspirin", "reaction": "Bronchospasm", "severity": "severe", "criticality": "high"},
        {"substance": "Latex", "reaction": "Contact dermatitis", "severity": "mild", "criticality": "low"},
        {"substance": "Iodine contrast", "reaction": "Anaphylaxis", "severity": "severe", "criticality": "high"},
        {"substance": "Codeine", "reaction": "Nausea", "severity": "mild", "criticality": "low"},
        {"substance": "Amoxicillin", "reaction": "Urticaria", "severity": "moderate", "criticality": "low"},
    ]

    patient_files = sorted(patient_dir.glob("*.json"))
    allergy_dir.mkdir(parents=True, exist_ok=True)

    for i, pf in enumerate(patient_files):
        patient = json.loads(pf.read_text(encoding="utf-8"))
        pid = patient.get("id")
        if not pid or pid in existing_allergy_patients:
            continue

        sample = sample_allergies[i % len(sample_allergies)]
        allergy_id = str(uuid.uuid4())

        allergy_resource = {
            "resourceType": "AllergyIntolerance",
            "id": allergy_id,
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active",
                        "display": "Active",
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": "confirmed",
                        "display": "Confirmed",
                    }
                ]
            },
            "criticality": sample["criticality"],
            "code": {"text": sample["substance"]},
            "patient": {"reference": f"Patient/{pid}"},
            "reaction": [
                {
                    "manifestation": [{"text": sample["reaction"]}],
                    "severity": sample["severity"],
                }
            ],
        }

        dest = allergy_dir / f"{allergy_id}.json"
        dest.write_text(json.dumps(allergy_resource, indent=2), encoding="utf-8")
        stats["AllergyIntolerance"] += 1


if __name__ == "__main__":
    seed()
