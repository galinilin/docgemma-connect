"""Seed the local FHIR JSON store from Synthea bundles.

Parses Synthea FHIR Bundle JSON files and extracts individual resources
into ``data/fhir/{ResourceType}/{id}.json``.

Supports two input layouts:
1. Flat directory of bundles (legacy)
2. Category directory with manifest.json (new category-based pipeline)

Usage:
    # Legacy flat mode
    uv run python -m docgemma.tools.fhir_store.seed

    # Category mode (auto-detected via manifest.json)
    uv run python -m docgemma.tools.fhir_store.seed --bundle-dir ../docgemma-synthea/output/fhir_augmented

    # With clean
    uv run python -m docgemma.tools.fhir_store.seed --clean
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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
    "Encounter",
}

# Default paths (relative to docgemma-connect/)
_CONNECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_BUNDLE_DIR = _CONNECT_ROOT.parent / "docgemma-synthea" / "output" / "fhir_augmented"
_DEFAULT_DATA_DIR = _CONNECT_ROOT / "data" / "fhir"


def _find_bundle_files(bundle_dir: Path) -> tuple[list[Path], dict | None]:
    """Discover bundle files — supports both flat and category layouts.

    Returns:
        Tuple of (list of bundle file paths, manifest dict or None).
    """
    manifest_path = bundle_dir / "manifest.json"
    manifest = None

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"Found manifest.json with {len(manifest)} entries (category mode)")

    # Walk all **/*.json recursively to find bundles
    bundle_files = sorted(bundle_dir.rglob("*.json"))
    # Filter out manifest.json and non-bundle files
    bundle_files = [
        f for f in bundle_files
        if f.name != "manifest.json" and f.suffix == ".json"
    ]

    return bundle_files, manifest


def _build_manifest_index(manifest: list[dict] | None) -> dict[str, dict]:
    """Build a lookup from bundle filename -> manifest entry."""
    if not manifest:
        return {}
    index = {}
    for entry in manifest:
        # Use just the filename as key (basename)
        path = Path(entry.get("path", ""))
        index[path.name] = entry
    return index


def _score_patient_richness(bundle: dict) -> int:
    """Score a patient bundle by clinical data richness.

    Counts conditions + observations + document references.
    """
    score = 0
    for entry in bundle.get("entry", []):
        rtype = entry.get("resource", {}).get("resourceType", "")
        if rtype in ("Condition", "Observation", "DocumentReference", "MedicationRequest"):
            score += 1
    return score


def seed(
    bundle_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
    clean: bool = False,
) -> None:
    """Extract FHIR resources from Synthea bundles into the local store.

    Args:
        bundle_dir: Directory containing Synthea ``*.json`` bundles.
        data_dir:   Target directory for individual resource files.
        clean:      If True, remove all existing data before seeding.
    """
    bundle_dir = Path(bundle_dir or os.getenv("SYNTHEA_BUNDLE_DIR", str(_DEFAULT_BUNDLE_DIR)))
    data_dir = Path(data_dir or os.getenv("FHIR_DATA_DIR", str(_DEFAULT_DATA_DIR)))

    if not bundle_dir.is_dir():
        print(f"ERROR: Bundle directory not found: {bundle_dir}")
        return

    # Clean mode: remove existing data
    if clean and data_dir.is_dir():
        print(f"Cleaning existing data at {data_dir}")
        shutil.rmtree(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    bundle_files, manifest = _find_bundle_files(bundle_dir)
    manifest_index = _build_manifest_index(manifest)

    if not bundle_files:
        print(f"ERROR: No JSON files found in {bundle_dir}")
        return

    print(f"Seeding from {len(bundle_files)} bundles in {bundle_dir}")
    print(f"Target: {data_dir}")

    # If manifest exists, group bundles by specialty for patient selection
    specialty_bundles: dict[str, list[tuple[Path, dict, int]]] = {}

    stats: Counter[str] = Counter()

    for bundle_file in bundle_files:
        bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
        manifest_entry = manifest_index.get(bundle_file.name)

        if manifest_entry:
            specialty = manifest_entry.get("specialty", "unknown")
            pick = manifest_entry.get("pick", 999)
            richness = _score_patient_richness(bundle)
            specialty_bundles.setdefault(specialty, []).append(
                (bundle_file, bundle, richness)
            )
        else:
            # No manifest entry — process directly (legacy mode)
            _process_bundle(bundle, bundle_file, data_dir, stats, specialty_tag=None)

    # Process manifest-tracked bundles with patient selection
    if specialty_bundles:
        for specialty, bundles_with_scores in specialty_bundles.items():
            # Sort by richness (descending) and pick top N
            manifest_sample = manifest_index.get(bundles_with_scores[0][0].name, {})
            pick = manifest_sample.get("pick", len(bundles_with_scores))

            bundles_with_scores.sort(key=lambda x: x[2], reverse=True)
            selected = bundles_with_scores[:pick]
            skipped = len(bundles_with_scores) - len(selected)

            display_name = manifest_sample.get("display_name", specialty)
            if skipped > 0:
                print(f"  {display_name}: selected {len(selected)}/{len(bundles_with_scores)} patients (by richness)")

            for bundle_file, bundle, _ in selected:
                me = manifest_index.get(bundle_file.name, {})
                tag_info = {
                    "system": "http://docgemma.dev/specialty",
                    "code": me.get("specialty", ""),
                    "display": me.get("display_name", ""),
                }
                _process_bundle(bundle, bundle_file, data_dir, stats, specialty_tag=tag_info)

    # Synthea bundles typically don't include AllergyIntolerance resources.
    # Seed a few sample allergies so the UI has data to display.
    _seed_sample_allergies(data_dir, stats)

    print("\nSeeded resources:")
    for rtype in sorted(stats):
        print(f"  {rtype}: {stats[rtype]}")
    print(f"  TOTAL: {sum(stats.values())}")


# Per-patient caps to keep EHR UI realistic (max ~6-7 per category)
_RESOURCE_CAPS: dict[str, int] = {
    "Condition": 6,
    "MedicationRequest": 6,
    "Observation": 7,       # labs + vitals combined
    "DocumentReference": 7,  # notes
    "Encounter": 7,
    # Patient and AllergyIntolerance are uncapped (1 patient, few allergies)
}


def _sort_key_for_recency(resource: dict) -> str:
    """Extract a date string for sorting resources most-recent-first."""
    # Try various date fields
    for field in ("effectiveDateTime", "date", "authoredOn", "onsetDateTime"):
        val = resource.get(field, "")
        if val:
            return val
    # Encounter period
    period_start = resource.get("period", {}).get("start", "")
    if period_start:
        return period_start
    return ""


def _process_bundle(
    bundle: dict,
    bundle_file: Path,
    data_dir: Path,
    stats: Counter,
    specialty_tag: dict | None = None,
) -> None:
    """Extract resources from a single bundle into the data directory."""
    entries = bundle.get("entry", [])

    # Find patient ID
    patient_id: str | None = None
    for entry in entries:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            patient_id = resource.get("id")
            break

    if not patient_id:
        print(f"  SKIP {bundle_file.name}: no Patient resource found")
        return

    # Group resources by type, then apply caps (keep most recent)
    by_type: dict[str, list[dict]] = {}
    patient_resource: dict | None = None

    for entry in entries:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        if resource_type not in SUPPORTED_TYPES:
            continue
        if not resource.get("id"):
            continue

        if resource_type == "Patient":
            patient_resource = resource
            continue

        by_type.setdefault(resource_type, []).append(resource)

    # Write Patient first (always kept)
    if patient_resource:
        _clean_patient_name(patient_resource)
        _rewrite_references(patient_resource, patient_id)
        if specialty_tag and specialty_tag.get("code"):
            meta = patient_resource.setdefault("meta", {})
            tags = meta.setdefault("tag", [])
            existing_codes = {t.get("code") for t in tags}
            if specialty_tag["code"] not in existing_codes:
                tags.append(specialty_tag)
        dest_dir = data_dir / "Patient"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{patient_resource['id']}.json"
        dest.write_text(json.dumps(patient_resource, indent=2), encoding="utf-8")
        stats["Patient"] += 1

    # Write other resources with caps
    for resource_type, resources in by_type.items():
        cap = _RESOURCE_CAPS.get(resource_type)

        if cap and len(resources) > cap:
            # Sort by date descending (most recent first), keep top N
            resources.sort(key=_sort_key_for_recency, reverse=True)
            resources = resources[:cap]

        dest_dir = data_dir / resource_type
        dest_dir.mkdir(parents=True, exist_ok=True)

        for resource in resources:
            _rewrite_references(resource, patient_id)
            dest = dest_dir / f"{resource['id']}.json"
            dest.write_text(json.dumps(resource, indent=2), encoding="utf-8")
            stats[resource_type] += 1


_TRAILING_DIGITS_RE = re.compile(r"\d+$")


def _clean_patient_name(patient: dict) -> None:
    """Strip Synthea-appended numbers from patient name parts.

    E.g. ``"Ladawn167"`` → ``"Ladawn"``, ``"Spinka232"`` → ``"Spinka"``.
    """
    for name_entry in patient.get("name", []):
        if "family" in name_entry:
            name_entry["family"] = _TRAILING_DIGITS_RE.sub("", name_entry["family"])
        if "given" in name_entry:
            name_entry["given"] = [
                _TRAILING_DIGITS_RE.sub("", g) for g in name_entry["given"]
            ]
        if "text" in name_entry:
            name_entry["text"] = " ".join(
                _TRAILING_DIGITS_RE.sub("", part)
                for part in name_entry["text"].split()
            )
        if "prefix" in name_entry:
            name_entry["prefix"] = [
                _TRAILING_DIGITS_RE.sub("", p) for p in name_entry["prefix"]
            ]


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
    parser = argparse.ArgumentParser(
        description="Seed the local FHIR JSON store from Synthea bundles",
    )
    parser.add_argument(
        "--bundle-dir", type=str, default=None,
        help="Directory containing Synthea bundles (default: auto-detect)",
    )
    parser.add_argument(
        "--data-dir", type=str, default=None,
        help="Target directory for FHIR resource files",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Remove all existing data before seeding",
    )
    args = parser.parse_args()

    seed(
        bundle_dir=args.bundle_dir,
        data_dir=args.data_dir,
        clean=args.clean,
    )
