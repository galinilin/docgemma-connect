"""Local JSON-based FHIR R4 store.

Replaces MedplumClient with a local filesystem-backed store that reads
and writes FHIR R4 resources as JSON files under data/fhir/{ResourceType}/{id}.json.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


class ResourceNotFoundError(Exception):
    """Raised when a requested FHIR resource does not exist on disk."""


class FhirJsonStore:
    """Local FHIR store backed by JSON files on disk.

    Drop-in replacement for MedplumClient — same get()/post() interface,
    but reads/writes from ``data/fhir/{ResourceType}/{id}.json``.
    """

    def __init__(self, data_dir: str | Path | None = None):
        if data_dir is None:
            data_dir = os.getenv(
                "FHIR_DATA_DIR",
                str(Path(__file__).resolve().parents[4] / "data" / "fhir"),
            )
        self._data_dir = Path(data_dir)

    # ------------------------------------------------------------------
    # Compatibility shim (same name the consumer code calls)
    # ------------------------------------------------------------------

    def _check_credentials(self) -> str | None:
        """Always returns None — no auth required for local store."""
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, path: str, params: dict | None = None) -> dict:
        """Read resources from disk.

        Supports two forms:
          - ``/Patient/123``  → single resource read
          - ``/Patient``      → search (returns FHIR Bundle)

        Recognised search parameters:
          name, birthdate, subject, patient, status, category, _count, _sort
        """
        parts = path.strip("/").split("/")
        resource_type = parts[0]

        if len(parts) == 2:
            # Direct read: /ResourceType/id
            return self._read_resource(resource_type, parts[1])

        # Search: /ResourceType?params
        return self._search(resource_type, params or {})

    async def delete(self, path: str) -> bool:
        """Delete a FHIR resource from disk.

        Accepts ``/ResourceType/id``.
        Returns True if deleted, raises ResourceNotFoundError if missing.
        """
        parts = path.strip("/").split("/")
        if len(parts) != 2:
            raise ValueError(f"Delete requires /ResourceType/id, got: {path}")
        resource_type, resource_id = parts
        file_path = self._data_dir / resource_type / f"{resource_id}.json"
        if not file_path.exists():
            raise ResourceNotFoundError(f"{resource_type}/{resource_id} not found")
        file_path.unlink()
        return True

    async def post(self, path: str, data: dict) -> dict:
        """Write a new FHIR resource to disk.

        Assigns a UUID ``id`` and writes to
        ``data/fhir/{ResourceType}/{id}.json``.
        Returns the resource dict (with ``id`` populated).
        """
        resource_type = path.strip("/").split("/")[0]
        resource_id = str(uuid.uuid4())
        data["id"] = resource_id

        resource_dir = self._data_dir / resource_type
        resource_dir.mkdir(parents=True, exist_ok=True)

        dest = resource_dir / f"{resource_id}.json"
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_resource(self, resource_type: str, resource_id: str) -> dict:
        """Read a single resource file. Raises ResourceNotFoundError if missing."""
        file_path = self._data_dir / resource_type / f"{resource_id}.json"
        if not file_path.exists():
            raise ResourceNotFoundError(
                f"{resource_type}/{resource_id} not found"
            )
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _search(self, resource_type: str, params: dict) -> dict:
        """Search resources on disk and return a FHIR Bundle.

        Applies basic filters then wraps matching resources in a Bundle.
        """
        resource_dir = self._data_dir / resource_type
        if not resource_dir.is_dir():
            return {"resourceType": "Bundle", "type": "searchset", "entry": []}

        resources: list[dict] = []
        for file_path in resource_dir.iterdir():
            if not file_path.suffix == ".json":
                continue
            resource = json.loads(file_path.read_text(encoding="utf-8"))
            if self._matches(resource, params):
                resources.append(resource)

        # Sorting
        sort_key = params.get("_sort", "")
        descending = sort_key.startswith("-")
        if sort_key:
            sort_field = sort_key.lstrip("-")
            field_map = {"_lastUpdated": "meta.lastUpdated"}
            sort_field = field_map.get(sort_field, sort_field)
            if sort_field == "date":
                # Try multiple date fields: effectiveDateTime (Observation), date (DocumentReference)
                resources.sort(
                    key=lambda r: self._get_nested(r, "effectiveDateTime") or self._get_nested(r, "date") or self._get_nested(r, "createdDateTime") or "",
                    reverse=descending,
                )
                sort_field = None  # already sorted
            if sort_field:
                resources.sort(
                    key=lambda r: self._get_nested(r, sort_field) or "",
                    reverse=descending,
                )

        # Count limit
        count = params.get("_count")
        if count is not None:
            resources = resources[: int(count)]

        entries = [
            {"resource": r, "fullUrl": f"{resource_type}/{r.get('id', '')}"}
            for r in resources
        ]

        return {"resourceType": "Bundle", "type": "searchset", "entry": entries}

    def _matches(self, resource: dict, params: dict) -> bool:
        """Check whether *resource* matches all non-meta search params."""
        for key, value in params.items():
            if key.startswith("_"):
                continue  # Skip _count, _sort, etc.

            if key == "name":
                if not self._match_name(resource, value):
                    return False

            elif key == "birthdate":
                if resource.get("birthDate", "") != value:
                    return False

            elif key in ("subject", "patient"):
                ref = self._extract_reference(resource, key)
                # Accept "Patient/123" or bare "123"
                if ref != value and ref != f"Patient/{value}":
                    return False

            elif key == "status":
                if resource.get("status", "") != value:
                    return False

            elif key == "category":
                if not self._match_category(resource, value):
                    return False

            elif key == "type":
                if not self._match_type(resource, value):
                    return False

        return True

    # -- match helpers --------------------------------------------------

    @staticmethod
    def _match_name(resource: dict, query: str) -> bool:
        """Case-insensitive partial match on Patient name fields."""
        query_lower = query.lower()
        for name_obj in resource.get("name", []):
            family = (name_obj.get("family") or "").lower()
            givens = " ".join(name_obj.get("given", [])).lower()
            if query_lower in family or query_lower in givens:
                return True
        return False

    @staticmethod
    def _match_category(resource: dict, value: str) -> bool:
        """Match Observation.category coding code."""
        for cat in resource.get("category", []):
            for coding in cat.get("coding", []):
                if coding.get("code") == value:
                    return True
        return False

    @staticmethod
    def _match_type(resource: dict, value: str) -> bool:
        """Match resource.type.coding[].code (e.g. DocumentReference.type)."""
        type_obj = resource.get("type", {})
        if isinstance(type_obj, dict):
            for coding in type_obj.get("coding", []):
                if coding.get("code") == value:
                    return True
        return False

    @staticmethod
    def _extract_reference(resource: dict, param_name: str) -> str:
        """Pull the reference string for 'subject' or 'patient' fields."""
        # 'subject' and 'patient' are the two FHIR search param names.
        # The actual resource field may be either key.
        for field in ("subject", "patient"):
            ref_obj = resource.get(field)
            if isinstance(ref_obj, dict):
                return ref_obj.get("reference", "")
        return ""

    @staticmethod
    def _get_nested(d: dict, dotted_key: str) -> str | None:
        """Retrieve a (possibly dotted) key from a dict."""
        parts = dotted_key.split(".")
        current: dict | str | None = d
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current if isinstance(current, str) else None


# --------------------------------------------------------------------------
# Global singleton (mirrors medplum.client.get_client)
# --------------------------------------------------------------------------

_client: FhirJsonStore | None = None


def get_client() -> FhirJsonStore:
    """Get or create the global FhirJsonStore instance."""
    global _client
    if _client is None:
        _client = FhirJsonStore()
    return _client
