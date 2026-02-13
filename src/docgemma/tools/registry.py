"""Unified tool registry for DocGemma agent.

Add new tools by registering them with the @register_tool decorator.
The registry auto-generates prompt descriptions and handles dispatching.

Example:
    @register_tool(
        name="my_tool",
        description="What this tool does",
        args={"param1": "description of param1"}
    )
    async def my_tool_executor(param1: str) -> dict:
        return {"result": param1}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# Type alias for tool executor functions
ToolExecutor = Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class ToolDefinition:
    """Definition of a single tool."""

    name: str
    description: str
    args: dict[str, str]  # arg_name -> description
    executor: ToolExecutor | None = None
    # Which schema field maps to which arg (for LLM output parsing)
    arg_mapping: dict[str, str] = field(default_factory=dict)


class ToolRegistry:
    """Central registry for all agent tools."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        args: dict[str, str],
        arg_mapping: dict[str, str] | None = None,
    ) -> Callable[[ToolExecutor], ToolExecutor]:
        """Decorator to register a tool.

        Args:
            name: Tool name (used in LLM output)
            description: Short description for prompts
            args: Dict of {arg_name: description}
            arg_mapping: Optional mapping from schema fields to arg names
                         e.g. {"drug_name": "brand_name"} means schema's
                         drug_name field maps to executor's brand_name param
        """
        def decorator(func: ToolExecutor) -> ToolExecutor:
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                args=args,
                executor=func,
                arg_mapping=arg_mapping or {},
            )
            return func
        return decorator

    def register_tool(
        self,
        name: str,
        description: str,
        args: dict[str, str],
        executor: ToolExecutor,
        arg_mapping: dict[str, str] | None = None,
    ) -> None:
        """Register a tool directly (non-decorator form)."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            args=args,
            executor=executor,
            arg_mapping=arg_mapping or {},
        )

    def get(self, name: str) -> ToolDefinition | None:
        """Get tool definition by name."""
        return self._tools.get(name)

    @property
    def names(self) -> list[str]:
        """List of registered tool names."""
        return list(self._tools.keys())

    def generate_prompt_list(self) -> str:
        """Generate tool list for prompts.

        Returns formatted string like:
        - check_drug_safety: drug_name (FDA warnings lookup)
        - search_medical_literature: query (PubMed search)
        """
        lines = []
        for tool in self._tools.values():
            args_str = ", ".join(tool.args.keys())
            lines.append(f"- {tool.name}: {args_str} ({tool.description})")
        lines.append("- none: no tool needed")
        return "\n".join(lines)

    def generate_schema_fields(self) -> str:
        """Generate argument field descriptions for schema docstrings."""
        all_args = set()
        for tool in self._tools.values():
            all_args.update(tool.args.keys())
        return ", ".join(sorted(all_args))

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments dict (from LLM output)

        Returns:
            Tool result dict
        """
        print(f"[TOOL] Executing {tool_name} with args: {args}")
        
        if tool_name == "none" or not tool_name:
            print(f"[TOOL] Skipped: No tool needed")
            return {"skipped": True, "reason": "No tool needed"}

        tool = self._tools.get(tool_name)
        if not tool:
            error_msg = f"Unknown tool: {tool_name}"
            print(f"[TOOL] ERROR: {error_msg}")
            return {"error": error_msg}

        if not tool.executor:
            error_msg = f"Tool {tool_name} has no executor registered"
            print(f"[TOOL] ERROR: {error_msg}")
            return {"error": error_msg}

        # Map schema fields to executor params using arg_mapping
        mapped_args = {}
        for schema_field, value in args.items():
            if value is None:
                continue
            # Check if there's a mapping, otherwise use field name directly
            param_name = tool.arg_mapping.get(schema_field, schema_field)
            mapped_args[param_name] = value

        try:
            result = await tool.executor(**mapped_args)
            # Log success with truncated result
            result_preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
            print(f"[TOOL] SUCCESS {tool_name}: {result_preview}")
            return result
        except TypeError as e:
            # Handle missing/extra arguments gracefully
            error_msg = f"Argument error for {tool_name}: {e}"
            print(f"[TOOL] ERROR: {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Tool {tool_name} failed: {e}"
            print(f"[TOOL] ERROR: {error_msg}")
            return {"error": error_msg}


# Global registry instance
TOOL_REGISTRY = ToolRegistry()


# =============================================================================
# TOOL REGISTRATIONS
# =============================================================================
# Add new tools here! Each registration is self-contained.

from ..tools.drug_safety import check_drug_safety
from ..tools.drug_interactions import check_drug_interactions
from ..tools.medical_literature import search_medical_literature
from ..tools.clinical_trials import find_clinical_trials
from ..tools.schemas import (
    DrugSafetyInput,
    DrugInteractionsInput,
    MedicalLiteratureInput,
    ClinicalTrialsInput,
)

# FHIR store tools
from ..tools.fhir_store import (
    search_patient,
    get_patient_chart,
    add_allergy,
    prescribe_medication,
    save_clinical_note,
    SearchPatientInput,
    GetPatientChartInput,
    AddAllergyInput,
    PrescribeMedicationInput,
    SaveClinicalNoteInput,
)


# --- Drug Safety ---
async def _check_drug_safety(drug_name: str = "", query: str = "") -> dict:
    """Execute drug safety check."""
    brand_name = drug_name or query or "unknown"
    result = await check_drug_safety(DrugSafetyInput(brand_name=brand_name))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="check_drug_safety",
    description="FDA boxed warnings lookup",
    args={"drug_name": "single drug name"},
    executor=_check_drug_safety,
    arg_mapping={"drug_name": "drug_name", "query": "query"},
)


# --- Medical Literature ---
async def _search_medical_literature(query: str = "", max_results: int = 3) -> dict:
    """Execute PubMed search."""
    result = await search_medical_literature(
        MedicalLiteratureInput(query=query, max_results=max_results)
    )
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="search_medical_literature",
    description="PubMed article search",
    args={"query": "search terms"},
    executor=_search_medical_literature,
)


# --- Drug Interactions ---
async def _check_drug_interactions(drug_list: str = "", drugs: list[str] | None = None) -> dict:
    """Execute drug interaction check."""
    if drugs is None:
        drugs = []
    # Handle comma-separated string
    if drug_list and not drugs:
        drugs = [d.strip() for d in drug_list.split(",") if d.strip()]
    if len(drugs) < 2:
        return {"error": "Need at least 2 drugs to check interactions", "drugs_checked": drugs}
    result = await check_drug_interactions(DrugInteractionsInput(drugs=drugs))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="check_drug_interactions",
    description="Drug-drug interaction check",
    args={"drug_list": "comma-separated drug names"},
    executor=_check_drug_interactions,
)


# --- Clinical Trials ---
async def _find_clinical_trials(query: str = "", condition: str = "", location: str | None = None) -> dict:
    """Execute clinical trials search."""
    search_term = condition or query
    result = await find_clinical_trials(
        ClinicalTrialsInput(condition=search_term, location=location)
    )
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="find_clinical_trials",
    description="Search recruiting clinical trials",
    args={"query": "condition or drug to search"},
    executor=_find_clinical_trials,
    arg_mapping={"query": "query", "condition": "condition"},
)


# =============================================================================
# FHIR STORE TOOLS
# =============================================================================


# --- Search Patient ---
async def _search_patient(name: str = "", dob: str = "") -> dict:
    """Execute patient search."""
    result = await search_patient(SearchPatientInput(
        name=name if name else None,
        dob=dob if dob else None,
    ))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="search_patient",
    description="Search patients by name or DOB in EHR",
    args={"name": "patient name", "dob": "date of birth (YYYY-MM-DD)"},
    executor=_search_patient,
)


# --- Get Patient Chart ---
async def _get_patient_chart(patient_id: str = "") -> dict:
    """Execute patient chart retrieval."""
    if not patient_id:
        return {"result": "", "error": "patient_id is required"}
    result = await get_patient_chart(GetPatientChartInput(patient_id=patient_id))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="get_patient_chart",
    description="Get patient clinical summary from EHR",
    args={"patient_id": "patient ID"},
    executor=_get_patient_chart,
)


# --- Add Allergy ---
async def _add_allergy(
    patient_id: str = "",
    substance: str = "",
    reaction: str = "",
    severity: str = "moderate",
) -> dict:
    """Execute allergy documentation."""
    if not patient_id or not substance or not reaction:
        return {"result": "", "error": "patient_id, substance, and reaction are required"}
    result = await add_allergy(AddAllergyInput(
        patient_id=patient_id,
        substance=substance,
        reaction=reaction,
        severity=severity,
    ))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="add_allergy",
    description="Document allergy in patient chart",
    args={
        "patient_id": "patient ID",
        "substance": "allergen name",
        "reaction": "reaction description",
        "severity": "mild/moderate/severe",
    },
    executor=_add_allergy,
)


# --- Prescribe Medication ---
async def _prescribe_medication(
    patient_id: str = "",
    medication_name: str = "",
    dosage: str = "",
    frequency: str = "",
) -> dict:
    """Execute medication prescription."""
    if not patient_id or not medication_name or not dosage or not frequency:
        return {"result": "", "error": "patient_id, medication_name, dosage, and frequency are required"}
    result = await prescribe_medication(PrescribeMedicationInput(
        patient_id=patient_id,
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
    ))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="prescribe_medication",
    description="Prescribe medication for patient",
    args={
        "patient_id": "patient ID",
        "medication_name": "medication name",
        "dosage": "dosage (e.g., 500mg)",
        "frequency": "frequency (e.g., twice daily)",
    },
    executor=_prescribe_medication,
)


# --- Save Clinical Note ---
async def _save_clinical_note(
    patient_id: str = "",
    note_text: str = "",
    note_type: str = "clinical-note",
) -> dict:
    """Execute clinical note save."""
    if not patient_id or not note_text:
        return {"result": "", "error": "patient_id and note_text are required"}
    result = await save_clinical_note(SaveClinicalNoteInput(
        patient_id=patient_id,
        note_text=note_text,
        note_type=note_type,
    ))
    return result.model_dump()

TOOL_REGISTRY.register_tool(
    name="save_clinical_note",
    description="Save clinical note to patient chart",
    args={
        "patient_id": "patient ID",
        "note_text": "note content",
        "note_type": "note type (default: clinical-note)",
    },
    executor=_save_clinical_note,
)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_tool_names() -> list[str]:
    """Get list of registered tool names."""
    return TOOL_REGISTRY.names


def get_tools_for_prompt() -> str:
    """Get formatted tool list for prompts."""
    return TOOL_REGISTRY.generate_prompt_list()


async def execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool by name."""
    return await TOOL_REGISTRY.execute(tool_name, args)
