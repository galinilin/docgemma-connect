"""
Tool-selection & argument-extraction experiments for MedGemma 4B IT.

Probes which prompting strategies get the 4B model to reliably pick the
right tool and fill correct args under Outlines constrained generation.
Generates a Markdown report with findings.

Usage:
    cd docgemma-connect
    uv run python tool_selection_experiments.py
    uv run python tool_selection_experiments.py --report-only tool_selection_experiments/<ts>
    uv run python tool_selection_experiments.py --judge tool_selection_experiments/<ts>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field as PField

from dotenv import load_dotenv
load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────

ENDPOINT = os.environ.get(
    "DOCGEMMA_ENDPOINT", "https://sbx7zjulvioxoh-8000.proxy.runpod.net"
)
API_KEY = os.environ.get("DOCGEMMA_API_KEY", "sk-sbx7zjulvioxoh")
MODEL = os.environ.get("DOCGEMMA_MODEL", "google/medgemma-1.5-4b-it")
COMPLETIONS_URL = f"{ENDPOINT.rstrip('/')}/v1/chat/completions"

THINKING_OPEN = "<unused94>"
THINKING_CLOSE = "<unused95>"
THINKING_RE = re.compile(r"<unused94>(.*?)(?:<unused95>|$)", re.DOTALL)

TIMEOUT = 120.0

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# ── HTTP helper ─────────────────────────────────────────────────────────

_client: httpx.Client | None = None


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        _client = httpx.Client(timeout=TIMEOUT, headers=headers)
    return _client


def call_model(
    messages: list[dict],
    *,
    max_tokens: int = 512,
    temperature: float = 0.0,
    response_format: dict | None = None,
    extra_body: dict | None = None,
) -> dict:
    """Raw OpenAI-compatible chat completion. Returns the full response JSON."""
    payload: dict = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format
    if extra_body:
        payload.update(extra_body)
    resp = get_client().post(COMPLETIONS_URL, json=payload)
    resp.raise_for_status()
    return resp.json()


# ── Pydantic schemas ───────────────────────────────────────────────────

ToolName = Literal[
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "search_patient",
    "get_patient_chart",
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
    "analyze_medical_image",
    "none",
]

ALL_TOOLS = [
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "search_patient",
    "get_patient_chart",
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
    "analyze_medical_image",
]


# --- Production schema (critical-first field order) ---
class ToolCallV2(BaseModel):
    """Tool selection with explicit argument fields. Critical-first order."""
    tool_name: ToolName
    patient_id: str | None = PField(default=None, max_length=64)
    query: str | None = PField(default=None, max_length=128)
    drug_name: str | None = PField(default=None, max_length=64)
    drug_list: str | None = PField(default=None, max_length=128)
    name: str | None = PField(default=None, max_length=64)
    dob: str | None = PField(default=None, max_length=10)
    substance: str | None = PField(default=None, max_length=64)
    reaction: str | None = PField(default=None, max_length=64)
    severity: str | None = PField(default=None, max_length=16)
    medication_name: str | None = PField(default=None, max_length=64)
    dosage: str | None = PField(default=None, max_length=32)
    frequency: str | None = PField(default=None, max_length=32)
    note_text: str | None = PField(default=None, max_length=512)
    note_type: str | None = PField(default=None, max_length=32)


# --- Reversed nullable order (field-ordering experiment) ---
class ToolCallV2Reversed(BaseModel):
    """Same fields as ToolCallV2 but nullable fields reversed."""
    tool_name: ToolName
    note_type: str | None = PField(default=None, max_length=32)
    note_text: str | None = PField(default=None, max_length=512)
    frequency: str | None = PField(default=None, max_length=32)
    dosage: str | None = PField(default=None, max_length=32)
    medication_name: str | None = PField(default=None, max_length=64)
    severity: str | None = PField(default=None, max_length=16)
    reaction: str | None = PField(default=None, max_length=64)
    substance: str | None = PField(default=None, max_length=64)
    dob: str | None = PField(default=None, max_length=10)
    name: str | None = PField(default=None, max_length=64)
    drug_list: str | None = PField(default=None, max_length=128)
    drug_name: str | None = PField(default=None, max_length=64)
    query: str | None = PField(default=None, max_length=128)
    patient_id: str | None = PField(default=None, max_length=64)


# --- Boolean probe schema ---
class BoolProbe(BaseModel):
    """Single-tool suitability probe."""
    suitable: bool


# --- Tool selection only (for two-stage) ---
class ToolSelection(BaseModel):
    """First stage: just pick the tool."""
    tool_name: ToolName


# --- Per-tool arg schemas (for two-stage, no irrelevant nullable fields) ---
class DrugSafetyArgs(BaseModel):
    drug_name: str = PField(max_length=64)

class LiteratureArgs(BaseModel):
    query: str = PField(max_length=128)

class DrugInteractionArgs(BaseModel):
    drug_list: str = PField(max_length=128)

class ClinicalTrialArgs(BaseModel):
    query: str = PField(max_length=128)

class PatientSearchArgs(BaseModel):
    name: str = PField(max_length=64)
    dob: str | None = PField(default=None, max_length=10)

class PatientChartArgs(BaseModel):
    patient_id: str = PField(max_length=64)

class AllergyArgs(BaseModel):
    patient_id: str = PField(max_length=64)
    substance: str = PField(max_length=64)
    reaction: str | None = PField(default=None, max_length=64)
    severity: str | None = PField(default=None, max_length=16)

class PrescriptionArgs(BaseModel):
    patient_id: str = PField(max_length=64)
    medication_name: str = PField(max_length=64)
    dosage: str | None = PField(default=None, max_length=32)
    frequency: str | None = PField(default=None, max_length=32)

class ClinicalNoteArgs(BaseModel):
    patient_id: str = PField(max_length=64)
    note_text: str = PField(max_length=512)
    note_type: str | None = PField(default=None, max_length=32)

class ImageAnalysisArgs(BaseModel):
    query: str = PField(max_length=128)


TOOL_ARG_SCHEMAS: dict[str, type[BaseModel]] = {
    "check_drug_safety": DrugSafetyArgs,
    "search_medical_literature": LiteratureArgs,
    "check_drug_interactions": DrugInteractionArgs,
    "find_clinical_trials": ClinicalTrialArgs,
    "search_patient": PatientSearchArgs,
    "get_patient_chart": PatientChartArgs,
    "add_allergy": AllergyArgs,
    "prescribe_medication": PrescriptionArgs,
    "save_clinical_note": ClinicalNoteArgs,
    "analyze_medical_image": ImageAnalysisArgs,
}


# ── Test queries ───────────────────────────────────────────────────────

@dataclass
class QueryDef:
    """Ground-truth definition for a test query."""
    id: str
    query: str
    expected_tool: str
    expected_args: dict[str, str]
    acceptable_tools: list[str]  # includes expected_tool
    category: str  # clear / ambiguous / arg_complexity


QUERIES: dict[str, QueryDef] = {
    # === Clear single-tool (Q-01 to Q-10) ===
    "Q-01": QueryDef(
        id="Q-01",
        query="Check FDA boxed warnings for dofetilide",
        expected_tool="check_drug_safety",
        expected_args={"drug_name": "dofetilide"},
        acceptable_tools=["check_drug_safety"],
        category="clear",
    ),
    "Q-02": QueryDef(
        id="Q-02",
        query="Search PubMed for SGLT2 inhibitor cardiovascular outcomes",
        expected_tool="search_medical_literature",
        expected_args={"query": "SGLT2 inhibitor cardiovascular outcomes"},
        acceptable_tools=["search_medical_literature"],
        category="clear",
    ),
    "Q-03": QueryDef(
        id="Q-03",
        query="Check drug interactions between warfarin and amiodarone",
        expected_tool="check_drug_interactions",
        expected_args={"drug_list": "warfarin, amiodarone"},
        acceptable_tools=["check_drug_interactions"],
        category="clear",
    ),
    "Q-04": QueryDef(
        id="Q-04",
        query="Find clinical trials for triple-negative breast cancer",
        expected_tool="find_clinical_trials",
        expected_args={"query": "triple-negative breast cancer"},
        acceptable_tools=["find_clinical_trials"],
        category="clear",
    ),
    "Q-05": QueryDef(
        id="Q-05",
        query="Search for patient Maria Garcia in the EHR",
        expected_tool="search_patient",
        expected_args={"name": "Maria Garcia"},
        acceptable_tools=["search_patient"],
        category="clear",
    ),
    "Q-06": QueryDef(
        id="Q-06",
        query="Get the clinical summary for patient abc-123",
        expected_tool="get_patient_chart",
        expected_args={"patient_id": "abc-123"},
        acceptable_tools=["get_patient_chart"],
        category="clear",
    ),
    "Q-07": QueryDef(
        id="Q-07",
        query="Document penicillin allergy with anaphylaxis for patient abc-123",
        expected_tool="add_allergy",
        expected_args={
            "patient_id": "abc-123",
            "substance": "penicillin",
            "reaction": "anaphylaxis",
            "severity": "severe",
        },
        acceptable_tools=["add_allergy"],
        category="clear",
    ),
    "Q-08": QueryDef(
        id="Q-08",
        query="Prescribe metformin 500mg twice daily for patient abc-123",
        expected_tool="prescribe_medication",
        expected_args={
            "patient_id": "abc-123",
            "medication_name": "metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
        },
        acceptable_tools=["prescribe_medication"],
        category="clear",
    ),
    "Q-09": QueryDef(
        id="Q-09",
        query="Save a progress note for patient abc-123: BP well controlled on current regimen",
        expected_tool="save_clinical_note",
        expected_args={
            "patient_id": "abc-123",
            "note_text": "BP well controlled on current regimen",
            "note_type": "progress-note",
        },
        acceptable_tools=["save_clinical_note"],
        category="clear",
    ),
    "Q-10": QueryDef(
        id="Q-10",
        query="Analyze this chest X-ray for any abnormalities",
        expected_tool="analyze_medical_image",
        expected_args={"query": "chest X-ray abnormalities"},
        acceptable_tools=["analyze_medical_image"],
        category="clear",
    ),
    # === Ambiguous (Q-11 to Q-15) ===
    "Q-11": QueryDef(
        id="Q-11",
        query="Is metformin safe for a patient with CKD stage 4?",
        expected_tool="check_drug_safety",
        expected_args={"drug_name": "metformin"},
        acceptable_tools=["check_drug_safety", "search_medical_literature"],
        category="ambiguous",
    ),
    "Q-12": QueryDef(
        id="Q-12",
        query="What are the risks of combining lisinopril with potassium supplements?",
        expected_tool="check_drug_interactions",
        expected_args={"drug_list": "lisinopril, potassium"},
        acceptable_tools=["check_drug_interactions", "check_drug_safety"],
        category="ambiguous",
    ),
    "Q-13": QueryDef(
        id="Q-13",
        query="Are there any new treatments for multiple sclerosis?",
        expected_tool="find_clinical_trials",
        expected_args={"query": "multiple sclerosis"},
        acceptable_tools=["find_clinical_trials", "search_medical_literature"],
        category="ambiguous",
    ),
    "Q-14": QueryDef(
        id="Q-14",
        query="Look up patient James Wilson's medications",
        expected_tool="search_patient",
        expected_args={"name": "James Wilson"},
        acceptable_tools=["search_patient", "get_patient_chart"],
        category="ambiguous",
    ),
    "Q-15": QueryDef(
        id="Q-15",
        query="Check amoxicillin information for my patient",
        expected_tool="check_drug_safety",
        expected_args={"drug_name": "amoxicillin"},
        acceptable_tools=["check_drug_safety", "search_medical_literature"],
        category="ambiguous",
    ),
    # === Arg complexity (Q-16 to Q-20) ===
    "Q-16": QueryDef(
        id="Q-16",
        query="Patient f47ac10b needs lisinopril 10mg once daily",
        expected_tool="prescribe_medication",
        expected_args={
            "patient_id": "f47ac10b",
            "medication_name": "lisinopril",
            "dosage": "10mg",
            "frequency": "once daily",
        },
        acceptable_tools=["prescribe_medication"],
        category="arg_complexity",
    ),
    "Q-17": QueryDef(
        id="Q-17",
        query="Document that patient abc-123 is allergic to sulfa drugs",
        expected_tool="add_allergy",
        expected_args={
            "patient_id": "abc-123",
            "substance": "sulfa drugs",
        },
        acceptable_tools=["add_allergy"],
        category="arg_complexity",
    ),
    "Q-18": QueryDef(
        id="Q-18",
        query="Find studies on GLP-1 agonists",
        expected_tool="search_medical_literature",
        expected_args={"query": "GLP-1 agonists"},
        acceptable_tools=["search_medical_literature"],
        category="arg_complexity",
    ),
    "Q-19": QueryDef(
        id="Q-19",
        query="Check if there's a problem mixing warfarin, aspirin, and ibuprofen",
        expected_tool="check_drug_interactions",
        expected_args={"drug_list": "warfarin, aspirin, ibuprofen"},
        acceptable_tools=["check_drug_interactions"],
        category="arg_complexity",
    ),
    "Q-20": QueryDef(
        id="Q-20",
        query="Write a note for patient abc-123 about today's visit: diabetes management, A1c 7.2",
        expected_tool="save_clinical_note",
        expected_args={
            "patient_id": "abc-123",
            "note_text": "diabetes management, A1c 7.2",
        },
        acceptable_tools=["save_clinical_note"],
        category="arg_complexity",
    ),
}


# ── Tool descriptions at 3 verbosity levels ────────────────────────────

TOOL_DESC_NAMES_ONLY = "\n".join(f"- {t}" for t in ALL_TOOLS) + "\n- none"

TOOL_DESC_SHORT = """\
- check_drug_safety: drug_name (FDA boxed warnings lookup)
- search_medical_literature: query (PubMed article search)
- check_drug_interactions: drug_list (Drug-drug interaction check)
- find_clinical_trials: query (Search recruiting clinical trials)
- search_patient: name, dob (Search patients by name or DOB in EHR)
- get_patient_chart: patient_id (Get patient clinical summary from EHR)
- add_allergy: patient_id, substance, reaction, severity (Document allergy in patient chart)
- prescribe_medication: patient_id, medication_name, dosage, frequency (Prescribe medication for patient)
- save_clinical_note: patient_id, note_text, note_type (Save clinical note to patient chart)
- analyze_medical_image: query (Analyze medical image using MedGemma vision)
- none: no tool needed"""

TOOL_DESC_FULL = """\
- check_drug_safety(drug_name: str) — Look up FDA boxed warnings and safety alerts for a single drug. Returns structured warning data from the FDA adverse event reporting system. Use for drug safety questions.
- search_medical_literature(query: str) — Search PubMed for peer-reviewed medical literature. Returns article titles, abstracts, and PMIDs. Use for evidence-based questions or when looking for recent studies.
- check_drug_interactions(drug_list: str) — Check drug-drug interactions via RxNav. Accepts comma-separated drug names (minimum 2). Returns interaction severity and descriptions. Use when a patient is on multiple medications.
- find_clinical_trials(query: str) — Search ClinicalTrials.gov for actively recruiting trials. Accepts condition or drug name. Returns trial titles, phases, and enrollment status. Use for treatment-seeking patients.
- search_patient(name: str, dob: str | null) — Search the EHR for patients by name or date of birth. Returns matching patient records with IDs. Use as the first step when patient is referenced by name.
- get_patient_chart(patient_id: str) — Retrieve a clinical summary for a patient from the EHR. Requires patient_id. Returns conditions, medications, allergies, labs, and notes. Use after identifying a patient.
- add_allergy(patient_id: str, substance: str, reaction: str, severity: str) — Document an allergy in the patient's chart. Requires patient_id, substance, reaction type, and severity (mild/moderate/severe). Creates an AllergyIntolerance FHIR resource.
- prescribe_medication(patient_id: str, medication_name: str, dosage: str, frequency: str) — Create a medication order for a patient. Requires patient_id, medication name, dosage, and frequency. Creates a MedicationRequest FHIR resource.
- save_clinical_note(patient_id: str, note_text: str, note_type: str) — Save a clinical note to the patient's chart. Requires patient_id and note content. Default type is "clinical-note". Other types: "progress-note", "discharge-summary".
- analyze_medical_image(query: str) — Analyze an attached medical image using MedGemma's vision capabilities. Accepts a clinical question about the image. Use when a medical image is attached.
- none — No tool is needed. Use for greetings, general medical knowledge questions, or when the answer can be provided from medical knowledge alone."""


# ── Prompt templates ───────────────────────────────────────────────────

# 10-shot examples for the plan prompt (current production)
ALL_10_EXAMPLES = """\
Example 1 (drug safety):
Task: Look up FDA warnings for dofetilide
tool_name: check_drug_safety
patient_id: null
drug_name: dofetilide

Example 2 (literature):
Task: Search for PCSK9 inhibitor studies
tool_name: search_medical_literature
patient_id: null
query: PCSK9 inhibitors efficacy LDL lowering

Example 3 (interactions):
Task: Check interactions between warfarin and azithromycin
tool_name: check_drug_interactions
patient_id: null
drug_list: warfarin, azithromycin

Example 4 (clinical trials):
Task: Find clinical trials for lung cancer
tool_name: find_clinical_trials
patient_id: null
query: lung cancer

Example 5 (patient search):
Task: Find patient John Smith
tool_name: search_patient
patient_id: null
name: John Smith

Example 6 (patient chart):
Task: Get chart for patient abc-123
tool_name: get_patient_chart
patient_id: abc-123

Example 7 (allergy):
Task: Document penicillin allergy for patient abc-123
tool_name: add_allergy
patient_id: abc-123
substance: penicillin
reaction: rash
severity: moderate

Example 8 (prescription):
Task: Prescribe lisinopril 10mg daily for patient abc-123
tool_name: prescribe_medication
patient_id: abc-123
medication_name: lisinopril
dosage: 10mg
frequency: once daily

Example 9 (clinical note):
Task: Save note about hypertension diagnosis for patient abc-123
tool_name: save_clinical_note
patient_id: abc-123
note_text: Patient diagnosed with hypertension. Starting lisinopril 10mg daily.
note_type: clinical-note

Example 10 (medical image):
Task: Analyze the attached medical image
tool_name: analyze_medical_image
patient_id: null
query: Describe this medical image in detail."""

# Subsets for few-shot variation
# 1-shot: one example matching the expected tool type
EXAMPLE_BY_TOOL: dict[str, str] = {
    "check_drug_safety": """\
Example:
Task: Look up FDA warnings for dofetilide
tool_name: check_drug_safety
patient_id: null
drug_name: dofetilide""",
    "search_medical_literature": """\
Example:
Task: Search for PCSK9 inhibitor studies
tool_name: search_medical_literature
patient_id: null
query: PCSK9 inhibitors efficacy LDL lowering""",
    "check_drug_interactions": """\
Example:
Task: Check interactions between warfarin and azithromycin
tool_name: check_drug_interactions
patient_id: null
drug_list: warfarin, azithromycin""",
    "find_clinical_trials": """\
Example:
Task: Find clinical trials for lung cancer
tool_name: find_clinical_trials
patient_id: null
query: lung cancer""",
    "search_patient": """\
Example:
Task: Find patient John Smith
tool_name: search_patient
patient_id: null
name: John Smith""",
    "get_patient_chart": """\
Example:
Task: Get chart for patient abc-123
tool_name: get_patient_chart
patient_id: abc-123""",
    "add_allergy": """\
Example:
Task: Document penicillin allergy for patient abc-123
tool_name: add_allergy
patient_id: abc-123
substance: penicillin
reaction: rash
severity: moderate""",
    "prescribe_medication": """\
Example:
Task: Prescribe lisinopril 10mg daily for patient abc-123
tool_name: prescribe_medication
patient_id: abc-123
medication_name: lisinopril
dosage: 10mg
frequency: once daily""",
    "save_clinical_note": """\
Example:
Task: Save note about hypertension diagnosis for patient abc-123
tool_name: save_clinical_note
patient_id: abc-123
note_text: Patient diagnosed with hypertension. Starting lisinopril 10mg daily.
note_type: clinical-note""",
    "analyze_medical_image": """\
Example:
Task: Analyze the attached medical image
tool_name: analyze_medical_image
patient_id: null
query: Describe this medical image in detail.""",
}

# 3-shot: diverse examples (drug, EHR, note)
THREE_SHOT_EXAMPLES = """\
Example 1:
Task: Look up FDA warnings for dofetilide
tool_name: check_drug_safety
patient_id: null
drug_name: dofetilide

Example 2:
Task: Get chart for patient abc-123
tool_name: get_patient_chart
patient_id: abc-123

Example 3:
Task: Save note about hypertension diagnosis for patient abc-123
tool_name: save_clinical_note
patient_id: abc-123
note_text: Patient diagnosed with hypertension.
note_type: clinical-note"""


def make_baseline_prompt(query: str, tools: str, examples: str) -> str:
    """Cat 1 / Cat 5 / Cat 6: direct selection prompt."""
    parts = ["Select tool and fill arguments. Output patient_id FIRST for EHR tools."]
    parts.append(f"\nTask: {query}")
    parts.append(f"\nTools:\n{tools}")
    if examples:
        parts.append(f"\n{examples}")
    parts.append("\n---\nReturn tool_name, then patient_id (extract from task or null), then remaining arguments.")
    return "\n".join(parts)


def make_two_stage_select_prompt(query: str, tools: str) -> str:
    """Cat 7, stage 1: tool selection only."""
    return f"""Which tool should be used for this task?

Task: {query}

Tools:
{tools}

Return tool_name only."""


def make_two_stage_args_prompt(query: str, tool_name: str) -> str:
    """Cat 7, stage 2: fill args for a specific tool."""
    return f"""Fill the arguments for {tool_name}.

Task: {query}

Return only the arguments needed for {tool_name}."""


def make_bool_probe_prompt(query: str, tool_name: str, tool_desc: str) -> str:
    """Cat 3: is this tool suitable?"""
    return f"""Is the tool "{tool_name}" ({tool_desc}) the right tool for this task?

Task: {query}

Answer true or false."""


def make_reasoning_then_select_prompt_1(query: str, tools: str) -> str:
    """Cat 4, call 1: free-form reasoning about which tool to use."""
    return f"""Which tool should I use for this task? Think about what the task needs.

Task: {query}

Available tools:
{tools}"""


def make_reasoning_then_select_prompt_2(query: str, reasoning: str) -> str:
    """Cat 4, call 2: structured selection after reasoning."""
    return f"""Based on this reasoning, select the tool and fill arguments.

Task: {query}
Reasoning: {reasoning}

Return tool_name, then patient_id (extract from task or null), then remaining arguments."""


# Short descriptions for bool probing
TOOL_SHORT_DESCS: dict[str, str] = {
    "check_drug_safety": "FDA boxed warnings lookup",
    "search_medical_literature": "PubMed article search",
    "check_drug_interactions": "Drug-drug interaction check",
    "find_clinical_trials": "Search recruiting clinical trials",
    "search_patient": "Search patients by name/DOB in EHR",
    "get_patient_chart": "Get patient clinical summary from EHR",
    "add_allergy": "Document allergy in patient chart",
    "prescribe_medication": "Prescribe medication for patient",
    "save_clinical_note": "Save clinical note to patient chart",
    "analyze_medical_image": "Analyze medical image using MedGemma vision",
}


# ── Result container ───────────────────────────────────────────────────

@dataclass
class ExperimentResult:
    experiment_id: str
    category: str
    description: str
    query_id: str
    query_text: str
    strategy: str
    params: dict

    # Ground truth
    expected_tool: str = ""
    expected_args: dict = field(default_factory=dict)
    acceptable_tools: list = field(default_factory=list)

    # Model output
    raw_response: str = ""
    parsed_tool: str = ""
    parsed_args: dict = field(default_factory=dict)

    # Deterministic eval
    tool_correct: bool = False
    tool_acceptable: bool = False
    args_present: dict = field(default_factory=dict)     # {arg: True/False}
    args_values_ok: dict = field(default_factory=dict)   # {arg: True/False}

    # Multi-call tracking
    num_llm_calls: int = 1
    per_call_latency_ms: list = field(default_factory=list)
    total_latency_ms: float = 0.0
    error: str | None = None

    # Thinking token cross-reference
    has_thinking_tokens: bool = False

    # Cat 3 specific
    boolean_results: dict = field(default_factory=dict)  # {tool: bool}

    # Cat 4 specific
    reasoning_text: str = ""

    # Gemini judge
    judge_tool_correct: str | None = None      # "correct" / "acceptable" / "wrong"
    judge_args_score: int | None = None         # 0-10
    judge_overall_score: int | None = None      # 0-10
    judge_rationale: str | None = None


# ── Outlines response_format helper ────────────────────────────────────

def make_response_format(schema_cls: type[BaseModel]) -> dict:
    """Build vLLM-compatible response_format from a Pydantic model."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_cls.__name__,
            "schema": schema_cls.model_json_schema(),
            "strict": True,
        },
    }


# ── Experiment definitions ─────────────────────────────────────────────

def build_experiments() -> list[dict]:
    """Build ~220 experiment definitions across 8 categories."""
    experiments = []

    # ================================================================
    # CAT 1: Direct Selection Baseline (20 exps)
    # Current production approach: full prompt + 10 examples + Outlines
    # ================================================================
    for qid, qdef in QUERIES.items():
        experiments.append({
            "id": f"cat1-baseline-{qid}",
            "category": "1_direct_baseline",
            "description": f"Baseline 10-shot, query={qid}",
            "query_id": qid,
            "strategy": "baseline",
            "run_fn": "single_call",
            "messages_fn": lambda q, _qid=qid: [
                {"role": "user", "content": make_baseline_prompt(q, TOOL_DESC_SHORT, ALL_10_EXAMPLES)},
            ],
            "schema_cls": ToolCallV2,
            "params": {"temperature": 0.0, "max_tokens": 512},
        })

    # ================================================================
    # CAT 2: Prefix Completion (40 exps = 20 queries x 2 prefixes)
    # Pre-fill assistant with cognitive prefix, Outlines completes
    # ================================================================
    prefix_strategies = {
        "cognitive": "Given this task, I need to use ",
        "analytical": "Analyzing the task requirements, ",
    }
    for pfx_name, pfx_text in prefix_strategies.items():
        for qid, qdef in QUERIES.items():
            experiments.append({
                "id": f"cat2-prefix-{pfx_name}-{qid}",
                "category": "2_prefix_completion",
                "description": f"Prefix='{pfx_name}', query={qid}",
                "query_id": qid,
                "strategy": f"prefix_{pfx_name}",
                "run_fn": "single_call",
                "messages_fn": lambda q, _pfx=pfx_text: [
                    {"role": "user", "content": make_baseline_prompt(q, TOOL_DESC_SHORT, ALL_10_EXAMPLES)},
                    {"role": "assistant", "content": _pfx},
                ],
                "schema_cls": ToolCallV2,
                "params": {"temperature": 0.0, "max_tokens": 512},
            })

    # ================================================================
    # CAT 3: Boolean Probing (20 exps, 200 LLM calls)
    # Per query, probe all 10 tools with true/false
    # ================================================================
    for qid, qdef in QUERIES.items():
        experiments.append({
            "id": f"cat3-bool-{qid}",
            "category": "3_boolean_probing",
            "description": f"Bool probe all 10 tools, query={qid}",
            "query_id": qid,
            "strategy": "boolean_probe",
            "run_fn": "boolean_probe",
            "params": {"temperature": 0.0, "max_tokens": 32},
        })

    # ================================================================
    # CAT 4: Reasoning-Then-Select (20 exps, 40 LLM calls)
    # Call 1: free-form reasoning, Call 2: constrained selection
    # ================================================================
    for qid, qdef in QUERIES.items():
        experiments.append({
            "id": f"cat4-reasoning-{qid}",
            "category": "4_reasoning_then_select",
            "description": f"Two-stage reasoning, query={qid}",
            "query_id": qid,
            "strategy": "reasoning_then_select",
            "run_fn": "reasoning_then_select",
            "params": {"temperature_reason": 0.3, "temperature_select": 0.0, "max_tokens": 512},
        })

    # ================================================================
    # CAT 5: Few-Shot Variation (80 exps = 20 queries x 4 shot counts)
    # 0, 1, 3, 10 examples
    # ================================================================
    shot_configs = {
        "0shot": "",
        "1shot": None,  # Will be filled per-query from EXAMPLE_BY_TOOL
        "3shot": THREE_SHOT_EXAMPLES,
        "10shot": ALL_10_EXAMPLES,
    }
    for shot_name, examples_text in shot_configs.items():
        for qid, qdef in QUERIES.items():
            if shot_name == "1shot":
                ex = EXAMPLE_BY_TOOL.get(qdef.expected_tool, "")
            else:
                ex = examples_text

            # Capture for closure
            _ex = ex
            experiments.append({
                "id": f"cat5-{shot_name}-{qid}",
                "category": "5_few_shot_variation",
                "description": f"{shot_name}, query={qid}",
                "query_id": qid,
                "strategy": shot_name,
                "run_fn": "single_call",
                "messages_fn": lambda q, _examples=_ex: [
                    {"role": "user", "content": make_baseline_prompt(q, TOOL_DESC_SHORT, _examples)},
                ],
                "schema_cls": ToolCallV2,
                "params": {"temperature": 0.0, "max_tokens": 512},
            })

    # ================================================================
    # CAT 6: Tool Description Verbosity (60 exps = 20 queries x 3 levels)
    # ================================================================
    desc_levels = {
        "names_only": TOOL_DESC_NAMES_ONLY,
        "short_desc": TOOL_DESC_SHORT,
        "full_desc": TOOL_DESC_FULL,
    }
    for level_name, tool_desc in desc_levels.items():
        for qid, qdef in QUERIES.items():
            _desc = tool_desc
            experiments.append({
                "id": f"cat6-{level_name}-{qid}",
                "category": "6_tool_description_verbosity",
                "description": f"Desc='{level_name}', query={qid}",
                "query_id": qid,
                "strategy": level_name,
                "run_fn": "single_call",
                "messages_fn": lambda q, _d=_desc: [
                    {"role": "user", "content": make_baseline_prompt(q, _d, ALL_10_EXAMPLES)},
                ],
                "schema_cls": ToolCallV2,
                "params": {"temperature": 0.0, "max_tokens": 512},
            })

    # ================================================================
    # CAT 7: Joint vs Two-Stage (40 exps, 60 LLM calls)
    # Joint: one-call ToolCallV2. Two-stage: ToolSelection + per-tool args.
    # ================================================================
    for qid, qdef in QUERIES.items():
        # Joint (same as baseline but explicitly labeled)
        experiments.append({
            "id": f"cat7-joint-{qid}",
            "category": "7_joint_vs_two_stage",
            "description": f"Joint (one call), query={qid}",
            "query_id": qid,
            "strategy": "joint",
            "run_fn": "single_call",
            "messages_fn": lambda q: [
                {"role": "user", "content": make_baseline_prompt(q, TOOL_DESC_SHORT, ALL_10_EXAMPLES)},
            ],
            "schema_cls": ToolCallV2,
            "params": {"temperature": 0.0, "max_tokens": 512},
        })
        # Two-stage
        experiments.append({
            "id": f"cat7-two_stage-{qid}",
            "category": "7_joint_vs_two_stage",
            "description": f"Two-stage, query={qid}",
            "query_id": qid,
            "strategy": "two_stage",
            "run_fn": "two_stage",
            "params": {"temperature": 0.0, "max_tokens": 256},
        })

    # ================================================================
    # CAT 8: Field Ordering (40 exps = 20 queries x 2 orderings)
    # ================================================================
    for qid, qdef in QUERIES.items():
        experiments.append({
            "id": f"cat8-critical_first-{qid}",
            "category": "8_field_ordering",
            "description": f"Critical-first ordering, query={qid}",
            "query_id": qid,
            "strategy": "critical_first",
            "run_fn": "single_call",
            "messages_fn": lambda q: [
                {"role": "user", "content": make_baseline_prompt(q, TOOL_DESC_SHORT, ALL_10_EXAMPLES)},
            ],
            "schema_cls": ToolCallV2,
            "params": {"temperature": 0.0, "max_tokens": 512},
        })
        experiments.append({
            "id": f"cat8-critical_last-{qid}",
            "category": "8_field_ordering",
            "description": f"Critical-last ordering, query={qid}",
            "query_id": qid,
            "strategy": "critical_last",
            "run_fn": "single_call",
            "messages_fn": lambda q: [
                {"role": "user", "content": make_baseline_prompt(q, TOOL_DESC_SHORT, ALL_10_EXAMPLES)},
            ],
            "schema_cls": ToolCallV2Reversed,
            "params": {"temperature": 0.0, "max_tokens": 512},
        })

    return experiments


# ── Evaluation helpers ─────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Normalize a string for fuzzy comparison."""
    return re.sub(r"\s+", " ", s.strip().lower())


def arg_value_match(expected: str, actual: str | None) -> bool:
    """Check if actual arg value is a reasonable match for expected."""
    if actual is None:
        return False
    e, a = normalize(expected), normalize(actual)
    # Exact match
    if e == a:
        return True
    # Containment (either direction)
    if e in a or a in e:
        return True
    # For drug lists: same drugs in any order
    if "," in e:
        e_set = {x.strip() for x in e.split(",")}
        a_set = {x.strip() for x in a.split(",")}
        if e_set == a_set:
            return True
    return False


def evaluate_result(result: ExperimentResult):
    """Deterministic evaluation of tool selection + arg extraction."""
    # Tool correctness
    result.tool_correct = result.parsed_tool == result.expected_tool
    result.tool_acceptable = result.parsed_tool in result.acceptable_tools

    # Arg evaluation
    for arg_name, expected_val in result.expected_args.items():
        actual = result.parsed_args.get(arg_name)
        result.args_present[arg_name] = actual is not None and actual != ""
        result.args_values_ok[arg_name] = arg_value_match(expected_val, actual)


# ── Runners ────────────────────────────────────────────────────────────

def run_single_call(exp: dict, qdef: QueryDef) -> ExperimentResult:
    """Single LLM call with Outlines constrained schema."""
    messages = exp["messages_fn"](qdef.query)
    schema_cls = exp["schema_cls"]
    params = dict(exp["params"])

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        query_id=exp["query_id"],
        query_text=qdef.query,
        strategy=exp["strategy"],
        params=exp["params"],
        expected_tool=qdef.expected_tool,
        expected_args=qdef.expected_args,
        acceptable_tools=qdef.acceptable_tools,
        num_llm_calls=1,
    )

    try:
        t0 = time.monotonic()
        resp = call_model(
            messages,
            max_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature", 0.0),
            response_format=make_response_format(schema_cls),
        )
        latency = (time.monotonic() - t0) * 1000
        result.per_call_latency_ms = [latency]
        result.total_latency_ms = latency

        raw = resp["choices"][0]["message"]["content"]
        result.raw_response = raw
        result.has_thinking_tokens = THINKING_OPEN in raw

        # Parse JSON
        clean = THINKING_RE.sub("", raw).strip()
        parsed = json.loads(clean)
        result.parsed_tool = parsed.get("tool_name", "")
        result.parsed_args = {k: v for k, v in parsed.items() if k != "tool_name" and v is not None}
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


def run_boolean_probe(exp: dict, qdef: QueryDef) -> ExperimentResult:
    """Probe each of 10 tools with true/false."""
    params = dict(exp["params"])

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        query_id=exp["query_id"],
        query_text=qdef.query,
        strategy=exp["strategy"],
        params=exp["params"],
        expected_tool=qdef.expected_tool,
        expected_args=qdef.expected_args,
        acceptable_tools=qdef.acceptable_tools,
        num_llm_calls=10,
    )

    latencies = []
    boolean_results = {}
    selected_tool = "none"

    try:
        for tool in ALL_TOOLS:
            prompt = make_bool_probe_prompt(qdef.query, tool, TOOL_SHORT_DESCS[tool])
            messages = [{"role": "user", "content": prompt}]

            t0 = time.monotonic()
            resp = call_model(
                messages,
                max_tokens=params.get("max_tokens", 32),
                temperature=params.get("temperature", 0.0),
                response_format=make_response_format(BoolProbe),
            )
            latencies.append((time.monotonic() - t0) * 1000)

            raw = resp["choices"][0]["message"]["content"]
            clean = THINKING_RE.sub("", raw).strip()
            parsed = json.loads(clean)
            boolean_results[tool] = parsed.get("suitable", False)

        result.boolean_results = boolean_results
        result.per_call_latency_ms = latencies
        result.total_latency_ms = sum(latencies)

        # Select first true tool
        for tool in ALL_TOOLS:
            if boolean_results.get(tool, False):
                selected_tool = tool
                break

        result.parsed_tool = selected_tool
        # No args extracted in boolean mode
        result.raw_response = json.dumps(boolean_results)
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


def run_reasoning_then_select(exp: dict, qdef: QueryDef) -> ExperimentResult:
    """Two-stage: free-form reasoning, then constrained selection."""
    params = dict(exp["params"])

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        query_id=exp["query_id"],
        query_text=qdef.query,
        strategy=exp["strategy"],
        params=exp["params"],
        expected_tool=qdef.expected_tool,
        expected_args=qdef.expected_args,
        acceptable_tools=qdef.acceptable_tools,
        num_llm_calls=2,
    )

    latencies = []

    try:
        # Call 1: free-form reasoning
        prompt1 = make_reasoning_then_select_prompt_1(qdef.query, TOOL_DESC_SHORT)
        t0 = time.monotonic()
        resp1 = call_model(
            [{"role": "user", "content": prompt1}],
            max_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature_reason", 0.3),
        )
        latencies.append((time.monotonic() - t0) * 1000)
        reasoning = resp1["choices"][0]["message"]["content"]
        result.reasoning_text = THINKING_RE.sub("", reasoning).strip()
        result.has_thinking_tokens = THINKING_OPEN in reasoning

        # Call 2: constrained selection
        prompt2 = make_reasoning_then_select_prompt_2(qdef.query, result.reasoning_text)
        t0 = time.monotonic()
        resp2 = call_model(
            [{"role": "user", "content": prompt2}],
            max_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature_select", 0.0),
            response_format=make_response_format(ToolCallV2),
        )
        latencies.append((time.monotonic() - t0) * 1000)

        raw2 = resp2["choices"][0]["message"]["content"]
        result.raw_response = raw2
        clean = THINKING_RE.sub("", raw2).strip()
        parsed = json.loads(clean)
        result.parsed_tool = parsed.get("tool_name", "")
        result.parsed_args = {k: v for k, v in parsed.items() if k != "tool_name" and v is not None}

        result.per_call_latency_ms = latencies
        result.total_latency_ms = sum(latencies)
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


def run_two_stage(exp: dict, qdef: QueryDef) -> ExperimentResult:
    """Two-stage: tool selection, then per-tool arg extraction."""
    params = dict(exp["params"])

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        query_id=exp["query_id"],
        query_text=qdef.query,
        strategy=exp["strategy"],
        params=exp["params"],
        expected_tool=qdef.expected_tool,
        expected_args=qdef.expected_args,
        acceptable_tools=qdef.acceptable_tools,
        num_llm_calls=2,
    )

    latencies = []

    try:
        # Stage 1: tool selection
        prompt1 = make_two_stage_select_prompt(qdef.query, TOOL_DESC_SHORT)
        t0 = time.monotonic()
        resp1 = call_model(
            [{"role": "user", "content": prompt1}],
            max_tokens=64,
            temperature=params.get("temperature", 0.0),
            response_format=make_response_format(ToolSelection),
        )
        latencies.append((time.monotonic() - t0) * 1000)

        raw1 = resp1["choices"][0]["message"]["content"]
        clean1 = THINKING_RE.sub("", raw1).strip()
        tool_name = json.loads(clean1).get("tool_name", "none")
        result.parsed_tool = tool_name
        result.has_thinking_tokens = THINKING_OPEN in raw1

        # Stage 2: arg extraction (only if tool != none and schema exists)
        arg_schema = TOOL_ARG_SCHEMAS.get(tool_name)
        if arg_schema:
            prompt2 = make_two_stage_args_prompt(qdef.query, tool_name)
            t0 = time.monotonic()
            resp2 = call_model(
                [{"role": "user", "content": prompt2}],
                max_tokens=params.get("max_tokens", 256),
                temperature=params.get("temperature", 0.0),
                response_format=make_response_format(arg_schema),
            )
            latencies.append((time.monotonic() - t0) * 1000)

            raw2 = resp2["choices"][0]["message"]["content"]
            result.raw_response = raw2
            clean2 = THINKING_RE.sub("", raw2).strip()
            parsed_args = json.loads(clean2)
            result.parsed_args = {k: v for k, v in parsed_args.items() if v is not None}
        else:
            result.raw_response = raw1

        result.per_call_latency_ms = latencies
        result.total_latency_ms = sum(latencies)
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


# ── Dispatcher ─────────────────────────────────────────────────────────

RUN_DISPATCH = {
    "single_call": run_single_call,
    "boolean_probe": run_boolean_probe,
    "reasoning_then_select": run_reasoning_then_select,
    "two_stage": run_two_stage,
}


def run_experiment(exp: dict) -> ExperimentResult:
    """Execute a single experiment using the appropriate runner."""
    qdef = QUERIES[exp["query_id"]]
    runner = RUN_DISPATCH[exp["run_fn"]]
    return runner(exp, qdef)


def run_all(experiments: list[dict], output_dir: Path) -> list[ExperimentResult]:
    """Run all experiments sequentially, saving results incrementally."""
    results = []
    total = len(experiments)
    total_calls = sum(
        10 if e["run_fn"] == "boolean_probe" else
        2 if e["run_fn"] in ("reasoning_then_select", "two_stage") else
        1
        for e in experiments
    )
    print(f"\nRunning {total} experiments (~{total_calls} LLM calls)...\n")

    for i, exp in enumerate(experiments, 1):
        tag = f"[{i:3d}/{total}]"
        print(f"{tag} {exp['id']:<50s}", end="", flush=True)

        result = run_experiment(exp)

        if result.error:
            print(f"  ERROR: {result.error[:60]}")
        else:
            tool_flag = "OK" if result.tool_correct else ("~" if result.tool_acceptable else "X ")
            args_ok = sum(result.args_values_ok.values())
            args_tot = len(result.expected_args)
            print(
                f"  tool={tool_flag}  "
                f"args={args_ok}/{args_tot}  "
                f"calls={result.num_llm_calls}  "
                f"{result.total_latency_ms:6.0f}ms"
            )

        results.append(result)

        # Save incrementally
        with open(output_dir / "results.jsonl", "a") as f:
            f.write(json.dumps(asdict(result), default=str) + "\n")

    return results


# ── Gemini judge ───────────────────────────────────────────────────────

JUDGE_PROMPT = """\
You are evaluating a medical AI model's tool selection and argument extraction.

The model was given a clinical task and asked to select the right tool and fill \
its arguments. Evaluate on three dimensions:

1. **tool_correct**: Is the selected tool correct?
   - "correct" = exact match with expected tool
   - "acceptable" = not the primary expected tool but a reasonable alternative
   - "wrong" = completely wrong tool for the task

2. **args_score** (0-10): How well were the arguments extracted?
   - 10 = all args correct with exact/near-exact values
   - 7-9 = all critical args present, minor value differences
   - 4-6 = some args missing or incorrect
   - 1-3 = mostly wrong args
   - 0 = no args or completely wrong

3. **overall_score** (0-10): Combined quality (tool + args)
   - 10 = perfect tool and args
   - 0 = completely wrong

Respond with ONLY a JSON object (no markdown fences):
{{
  "tool_correct": "correct" / "acceptable" / "wrong",
  "args_score": <0-10>,
  "overall_score": <0-10>,
  "rationale": "<1-2 sentence explanation>"
}}

---

**Task:** {query}
**Expected tool:** {expected_tool}
**Acceptable tools:** {acceptable_tools}
**Expected args:** {expected_args}

**Model selected:** {parsed_tool}
**Model args:** {parsed_args}
"""

_gemini_client: httpx.Client | None = None


def _get_gemini_client() -> httpx.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = httpx.Client(timeout=30.0)
    return _gemini_client


def gemini_judge(result: ExperimentResult) -> dict:
    """Ask Gemini to evaluate tool selection + arg quality."""
    prompt = JUDGE_PROMPT.format(
        query=result.query_text,
        expected_tool=result.expected_tool,
        acceptable_tools=", ".join(result.acceptable_tools),
        expected_args=json.dumps(result.expected_args),
        parsed_tool=result.parsed_tool,
        parsed_args=json.dumps(result.parsed_args),
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
    }
    resp = _get_gemini_client().post(url, json=payload)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def judge_all(results: list[ExperimentResult]) -> list[ExperimentResult]:
    """Run Gemini judge on every result that has a parsed_tool."""
    if not GEMINI_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set. Cannot run Gemini judge.")
        sys.exit(1)

    judgeable = [r for r in results if r.parsed_tool and not r.error]
    total = len(judgeable)
    print(f"\nRunning Gemini judge on {total} results...\n")

    for i, r in enumerate(judgeable, 1):
        print(f"[{i:3d}/{total}] {r.experiment_id:<50s}", end="", flush=True)
        try:
            verdict = gemini_judge(r)
            r.judge_tool_correct = verdict.get("tool_correct", "wrong")
            r.judge_args_score = verdict.get("args_score", 0)
            r.judge_overall_score = verdict.get("overall_score", 0)
            r.judge_rationale = verdict.get("rationale", "")
            print(
                f"  tool={r.judge_tool_correct:<10s}  "
                f"args={r.judge_args_score:2d}  "
                f"overall={r.judge_overall_score:2d}  "
                f"{r.judge_rationale[:50]}"
            )
        except Exception as e:
            r.judge_tool_correct = None
            r.judge_args_score = None
            r.judge_overall_score = None
            r.judge_rationale = f"ERROR: {e}"
            print(f"  ERROR: {e}")

    return results


# ── Report generation ──────────────────────────────────────────────────

def load_results(output_dir: Path) -> list[ExperimentResult]:
    """Load results from JSONL file."""
    results = []
    with open(output_dir / "results.jsonl") as f:
        for line in f:
            d = json.loads(line)
            r = ExperimentResult(
                experiment_id=d["experiment_id"],
                category=d["category"],
                description=d["description"],
                query_id=d["query_id"],
                query_text=d["query_text"],
                strategy=d["strategy"],
                params=d["params"],
                expected_tool=d.get("expected_tool", ""),
                expected_args=d.get("expected_args", {}),
                acceptable_tools=d.get("acceptable_tools", []),
                raw_response=d.get("raw_response", ""),
                parsed_tool=d.get("parsed_tool", ""),
                parsed_args=d.get("parsed_args", {}),
                tool_correct=d.get("tool_correct", False),
                tool_acceptable=d.get("tool_acceptable", False),
                args_present=d.get("args_present", {}),
                args_values_ok=d.get("args_values_ok", {}),
                num_llm_calls=d.get("num_llm_calls", 1),
                per_call_latency_ms=d.get("per_call_latency_ms", []),
                total_latency_ms=d.get("total_latency_ms", 0),
                error=d.get("error"),
                has_thinking_tokens=d.get("has_thinking_tokens", False),
                boolean_results=d.get("boolean_results", {}),
                reasoning_text=d.get("reasoning_text", ""),
                judge_tool_correct=d.get("judge_tool_correct"),
                judge_args_score=d.get("judge_args_score"),
                judge_overall_score=d.get("judge_overall_score"),
                judge_rationale=d.get("judge_rationale"),
            )
            results.append(r)
    return results


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{100 * n / total:.1f}%"


def generate_report(results: list[ExperimentResult], output_dir: Path):
    """Generate comprehensive Markdown report."""
    lines: list[str] = []
    w = lines.append

    ok = [r for r in results if not r.error]
    err = [r for r in results if r.error]

    w("# MedGemma 4B — Tool Selection & Argument Extraction Experiments")
    w("")
    w(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"**Model:** `{MODEL}`")
    w(f"**Endpoint:** `{ENDPOINT}`")
    w(f"**Total experiments:** {len(results)}")
    w(f"**Errors:** {len(err)}")
    w("")

    # ── 1. Executive Summary ───────────────────────────────────────
    w("## 1. Executive Summary")
    w("")
    tool_exact = sum(1 for r in ok if r.tool_correct)
    tool_accept = sum(1 for r in ok if r.tool_acceptable)
    avg_latency = sum(r.total_latency_ms for r in ok) / max(len(ok), 1)
    total_calls = sum(r.num_llm_calls for r in ok)

    w(f"- **Tool exact match:** {tool_exact}/{len(ok)} ({_pct(tool_exact, len(ok))})")
    w(f"- **Tool acceptable match:** {tool_accept}/{len(ok)} ({_pct(tool_accept, len(ok))})")
    w(f"- **Total LLM calls:** {total_calls}")
    w(f"- **Avg latency per experiment:** {avg_latency:.0f}ms")

    # Arg stats
    all_args_ok_count = 0
    all_args_total = 0
    for r in ok:
        for v in r.args_values_ok.values():
            all_args_total += 1
            if v:
                all_args_ok_count += 1
    if all_args_total:
        w(f"- **Arg value accuracy:** {all_args_ok_count}/{all_args_total} ({_pct(all_args_ok_count, all_args_total)})")

    thinking_count = sum(1 for r in ok if r.has_thinking_tokens)
    w(f"- **Thinking tokens observed:** {thinking_count}/{len(ok)} ({_pct(thinking_count, len(ok))})")
    w("")

    # ── 2. Strategy Comparison Table ───────────────────────────────
    w("## 2. Strategy Comparison Table")
    w("")
    w("| Category | Strategy | N | Tool Exact | Tool Accept | Avg Args OK | Avg Latency (ms) | Calls |")
    w("|----------|----------|---|-----------|-------------|-------------|-------------------|-------|")

    categories = sorted(set(r.category for r in results))
    for cat in categories:
        cat_results = [r for r in ok if r.category == cat]
        strategies = sorted(set(r.strategy for r in cat_results))
        cat_label = cat.split("_", 1)[1].replace("_", " ").title()
        for strat in strategies:
            s_results = [r for r in cat_results if r.strategy == strat]
            n = len(s_results)
            exact = sum(1 for r in s_results if r.tool_correct)
            accept = sum(1 for r in s_results if r.tool_acceptable)
            avg_args = 0.0
            args_count = 0
            for r in s_results:
                for v in r.args_values_ok.values():
                    args_count += 1
                    if v:
                        avg_args += 1
            args_rate = f"{avg_args / args_count:.0%}" if args_count else "N/A"
            avg_lat = sum(r.total_latency_ms for r in s_results) / max(n, 1)
            total_c = sum(r.num_llm_calls for r in s_results)
            w(f"| {cat_label} | {strat} | {n} | {exact}/{n} ({_pct(exact, n)}) | {accept}/{n} ({_pct(accept, n)}) | {args_rate} | {avg_lat:.0f} | {total_c} |")
    w("")

    # ── 3. Per-Category Deep Dives ─────────────────────────────────
    w("## 3. Per-Category Deep Dives")
    w("")

    for cat in categories:
        cat_results = [r for r in ok if r.category == cat]
        cat_label = cat.split("_", 1)[1].replace("_", " ").title()
        cat_exact = sum(1 for r in cat_results if r.tool_correct)

        w(f"### 3.{cat[0]}. {cat_label}")
        w("")
        w(f"Tool exact: **{cat_exact}/{len(cat_results)}** ({_pct(cat_exact, len(cat_results))})")
        w("")

        # Results table
        w("| Experiment | Query | Expected | Selected | Correct? | Args OK |")
        w("|------------|-------|----------|----------|----------|---------|")
        for r in cat_results:
            flag = "Exact" if r.tool_correct else ("Accept" if r.tool_acceptable else "WRONG")
            args_ok = sum(r.args_values_ok.values())
            args_tot = len(r.expected_args)
            w(f"| `{r.experiment_id}` | {r.query_id} | {r.expected_tool} | {r.parsed_tool} | {flag} | {args_ok}/{args_tot} |")
        w("")

        # Category-specific analysis
        if cat == "3_boolean_probing":
            multi_true = sum(1 for r in cat_results if sum(r.boolean_results.values()) > 1)
            zero_true = sum(1 for r in cat_results if sum(r.boolean_results.values()) == 0)
            w(f"**Multi-true rate:** {multi_true}/{len(cat_results)} queries had >1 tool marked suitable")
            w(f"**Zero-true rate:** {zero_true}/{len(cat_results)} queries had no tool marked suitable")
            w("")
            # Per-tool true rate
            tool_true_counts: dict[str, int] = defaultdict(int)
            for r in cat_results:
                for tool, val in r.boolean_results.items():
                    if val:
                        tool_true_counts[tool] += 1
            w("**Per-tool true rate:**")
            w("")
            w("| Tool | True Count |")
            w("|------|-----------|")
            for tool in ALL_TOOLS:
                w(f"| {tool} | {tool_true_counts.get(tool, 0)}/{len(cat_results)} |")
            w("")

        if cat == "4_reasoning_then_select":
            w("**Reasoning samples (first 200 chars):**")
            w("")
            for r in cat_results[:5]:
                snippet = r.reasoning_text[:200].replace("\n", " ")
                w(f"- `{r.query_id}`: _{snippet}_")
            w("")

    # ── 4. Tool Confusion Matrix ───────────────────────────────────
    w("## 4. Tool Confusion Matrix")
    w("")
    w("Rows = expected tool, Columns = selected tool. Cell = count across all experiments.")
    w("")

    # Build matrix
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in ok:
        confusion[r.expected_tool][r.parsed_tool] += 1

    all_selected = sorted(set(r.parsed_tool for r in ok if r.parsed_tool))
    expected_tools = sorted(set(r.expected_tool for r in ok))

    header = "| Expected \\ Selected | " + " | ".join(t.replace("_", " ")[:12] for t in all_selected) + " |"
    sep = "|" + "---|" * (len(all_selected) + 1)
    w(header)
    w(sep)
    for et in expected_tools:
        row = f"| {et.replace('_', ' ')[:20]} |"
        for st in all_selected:
            count = confusion[et].get(st, 0)
            cell = f" **{count}** " if et == st and count > 0 else f" {count} " if count > 0 else " . "
            row += cell + "|"
        w(row)
    w("")

    # ── 5. Argument Extraction Analysis ────────────────────────────
    w("## 5. Argument Extraction Analysis")
    w("")
    w("Per-argument miss rates across all experiments.")
    w("")

    arg_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"present": 0, "correct": 0, "total": 0})
    for r in ok:
        for arg, present in r.args_present.items():
            arg_stats[arg]["total"] += 1
            if present:
                arg_stats[arg]["present"] += 1
            if r.args_values_ok.get(arg, False):
                arg_stats[arg]["correct"] += 1

    w("| Argument | Expected N | Present | Correct | Miss Rate |")
    w("|----------|-----------|---------|---------|-----------|")
    for arg in sorted(arg_stats.keys()):
        s = arg_stats[arg]
        miss = s["total"] - s["present"]
        miss_rate = _pct(miss, s["total"])
        w(f"| {arg} | {s['total']} | {s['present']} | {s['correct']} | {miss_rate} |")
    w("")

    # Per-tool breakdown
    w("### Per-Tool Argument Accuracy")
    w("")
    for tool in ALL_TOOLS:
        tool_results = [r for r in ok if r.expected_tool == tool]
        if not tool_results:
            continue
        w(f"**{tool}:**")
        tool_arg_stats: dict[str, list[bool]] = defaultdict(list)
        for r in tool_results:
            for arg, val in r.args_values_ok.items():
                tool_arg_stats[arg].append(val)
        for arg, vals in sorted(tool_arg_stats.items()):
            correct = sum(vals)
            w(f"  - {arg}: {correct}/{len(vals)} correct")
        w("")

    # ── 6. Few-Shot Scaling Curve ──────────────────────────────────
    w("## 6. Few-Shot Scaling Curve")
    w("")
    fewshot_results = [r for r in ok if r.category == "5_few_shot_variation"]
    if fewshot_results:
        shot_order = ["0shot", "1shot", "3shot", "10shot"]
        w("| Shots | Tool Exact | Tool Accept | Avg Args OK |")
        w("|-------|-----------|-------------|-------------|")
        for shot in shot_order:
            sr = [r for r in fewshot_results if r.strategy == shot]
            if not sr:
                continue
            exact = sum(1 for r in sr if r.tool_correct)
            accept = sum(1 for r in sr if r.tool_acceptable)
            args_ok = sum(sum(r.args_values_ok.values()) for r in sr)
            args_tot = sum(len(r.args_values_ok) for r in sr)
            args_rate = f"{args_ok}/{args_tot}" if args_tot else "N/A"
            w(f"| {shot} | {exact}/{len(sr)} ({_pct(exact, len(sr))}) | {accept}/{len(sr)} ({_pct(accept, len(sr))}) | {args_rate} |")
        w("")
    else:
        w("No few-shot experiments completed.")
        w("")

    # ── 7. Field Ordering Effect ───────────────────────────────────
    w("## 7. Field Ordering Effect")
    w("")
    field_results = [r for r in ok if r.category == "8_field_ordering"]
    if field_results:
        for order in ["critical_first", "critical_last"]:
            fr = [r for r in field_results if r.strategy == order]
            exact = sum(1 for r in fr if r.tool_correct)
            accept = sum(1 for r in fr if r.tool_acceptable)
            args_ok = sum(sum(r.args_values_ok.values()) for r in fr)
            args_tot = sum(len(r.args_values_ok) for r in fr)
            w(f"**{order}:** tool exact={exact}/{len(fr)} ({_pct(exact, len(fr))}), "
              f"tool accept={accept}/{len(fr)} ({_pct(accept, len(fr))}), "
              f"args={args_ok}/{args_tot}")
        w("")

        # Per-query comparison
        w("| Query | Critical-First Tool | Critical-Last Tool | First Args | Last Args |")
        w("|-------|--------------------|--------------------|------------|-----------|")
        for qid in QUERIES:
            first = next((r for r in field_results if r.strategy == "critical_first" and r.query_id == qid), None)
            last = next((r for r in field_results if r.strategy == "critical_last" and r.query_id == qid), None)
            if first and last:
                f_ok = sum(first.args_values_ok.values())
                f_tot = len(first.args_values_ok)
                l_ok = sum(last.args_values_ok.values())
                l_tot = len(last.args_values_ok)
                f_flag = "OK" if first.tool_correct else first.parsed_tool
                l_flag = "OK" if last.tool_correct else last.parsed_tool
                w(f"| {qid} | {f_flag} | {l_flag} | {f_ok}/{f_tot} | {l_ok}/{l_tot} |")
        w("")
    else:
        w("No field ordering experiments completed.")
        w("")

    # ── 8. Latency Analysis ────────────────────────────────────────
    w("## 8. Latency Analysis")
    w("")
    w("| Strategy | Avg Total (ms) | Avg Per-Call (ms) | Calls/Exp |")
    w("|----------|---------------|-------------------|-----------|")
    for cat in categories:
        cat_ok = [r for r in ok if r.category == cat]
        strategies = sorted(set(r.strategy for r in cat_ok))
        for strat in strategies:
            sr = [r for r in cat_ok if r.strategy == strat]
            avg_total = sum(r.total_latency_ms for r in sr) / max(len(sr), 1)
            all_per_call = [c for r in sr for c in r.per_call_latency_ms]
            avg_per_call = sum(all_per_call) / max(len(all_per_call), 1) if all_per_call else 0
            avg_calls = sum(r.num_llm_calls for r in sr) / max(len(sr), 1)
            w(f"| {strat} | {avg_total:.0f} | {avg_per_call:.0f} | {avg_calls:.1f} |")
    w("")

    # ── 9. Thinking Token Correlation ──────────────────────────────
    w("## 9. Thinking Token Correlation")
    w("")
    think_yes = [r for r in ok if r.has_thinking_tokens]
    think_no = [r for r in ok if not r.has_thinking_tokens]

    if think_yes:
        think_exact = sum(1 for r in think_yes if r.tool_correct)
        no_think_exact = sum(1 for r in think_no if r.tool_correct)
        w(f"- **With thinking tokens:** {len(think_yes)} experiments, "
          f"tool exact={think_exact}/{len(think_yes)} ({_pct(think_exact, len(think_yes))})")
        w(f"- **Without thinking tokens:** {len(think_no)} experiments, "
          f"tool exact={no_think_exact}/{len(think_no)} ({_pct(no_think_exact, len(think_no))})")
    else:
        w("No thinking tokens observed in any experiment.")
    w("")

    # ── 10. Gemini vs Deterministic Eval Agreement ─────────────────
    w("## 10. Gemini vs Deterministic Eval Agreement")
    w("")
    judged = [r for r in ok if r.judge_tool_correct is not None]
    if judged:
        # Tool agreement
        agree_exact = sum(
            1 for r in judged
            if (r.tool_correct and r.judge_tool_correct == "correct") or
               (not r.tool_correct and r.judge_tool_correct != "correct")
        )
        w(f"- **Tool agreement:** {agree_exact}/{len(judged)} ({_pct(agree_exact, len(judged))})")

        avg_judge_args = sum(r.judge_args_score or 0 for r in judged) / len(judged)
        avg_judge_overall = sum(r.judge_overall_score or 0 for r in judged) / len(judged)
        w(f"- **Avg Gemini args score:** {avg_judge_args:.1f}/10")
        w(f"- **Avg Gemini overall score:** {avg_judge_overall:.1f}/10")
        w("")

        # Distribution
        w("| Gemini Tool Verdict | Count | Det. Exact Match |")
        w("|--------------------:|------:|-----------------:|")
        for verdict in ["correct", "acceptable", "wrong"]:
            v_results = [r for r in judged if r.judge_tool_correct == verdict]
            det_exact = sum(1 for r in v_results if r.tool_correct)
            w(f"| {verdict} | {len(v_results)} | {det_exact} |")
        w("")
    else:
        w("No Gemini judgments available. Run with `--judge` to populate.")
        w("")

    # ── 11. Recommendations ────────────────────────────────────────
    w("## 11. Recommendations")
    w("")
    w("_Based on experimental findings — fill in after reviewing results._")
    w("")

    # Find best strategy
    strat_scores: dict[str, dict[str, Any]] = {}
    for cat in categories:
        for strat in sorted(set(r.strategy for r in ok if r.category == cat)):
            sr = [r for r in ok if r.category == cat and r.strategy == strat]
            key = f"{cat}:{strat}"
            exact = sum(1 for r in sr if r.tool_correct)
            strat_scores[key] = {
                "exact_rate": exact / max(len(sr), 1),
                "n": len(sr),
                "exact": exact,
            }

    if strat_scores:
        best = max(strat_scores.items(), key=lambda x: (x[1]["exact_rate"], x[1]["n"]))
        w(f"1. **Best strategy:** `{best[0]}` ({best[1]['exact']}/{best[1]['n']} = {best[1]['exact_rate']:.0%} exact)")
    w("2. **Prefix completion effect:**")
    w("3. **Boolean probing viability:**")
    w("4. **Few-shot sweet spot:**")
    w("5. **Field ordering impact:**")
    w("6. **Two-stage vs joint:**")
    w("7. **Recommended production configuration:**")
    w("")

    # ── Errors ─────────────────────────────────────────────────────
    if err:
        w("## Errors")
        w("")
        for r in err:
            w(f"- `{r.experiment_id}`: {r.error[:200]}")
        w("")

    report_text = "\n".join(lines)
    report_path = output_dir / "report.md"
    report_path.write_text(report_text)
    print(f"\nReport written to: {report_path}")
    return report_text


# ── Main ───────────────────────────────────────────────────────────────

def save_results(results: list[ExperimentResult], output_dir: Path):
    """Write all results to JSONL (overwrites)."""
    with open(output_dir / "results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(asdict(r), default=str) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="MedGemma 4B tool-selection experiments"
    )
    parser.add_argument(
        "--report-only",
        metavar="DIR",
        help="Skip running experiments; generate report from existing results in DIR",
    )
    parser.add_argument(
        "--judge",
        metavar="DIR",
        help="Run Gemini judge on existing results in DIR, then regenerate report",
    )
    args = parser.parse_args()

    if args.judge:
        output_dir = Path(args.judge)
        if not (output_dir / "results.jsonl").exists():
            print(f"No results.jsonl in {output_dir}")
            sys.exit(1)
        results = load_results(output_dir)
        results = judge_all(results)
        save_results(results, output_dir)
        generate_report(results, output_dir)
        judged = [r for r in results if r.judge_tool_correct is not None and not r.error]
        correct = sum(1 for r in judged if r.judge_tool_correct == "correct")
        print(f"\nGemini judged {correct}/{len(judged)} as correct tool selection.")
        print(f"Report: {output_dir / 'report.md'}")
        return

    if args.report_only:
        output_dir = Path(args.report_only)
        if not (output_dir / "results.jsonl").exists():
            print(f"No results.jsonl in {output_dir}")
            sys.exit(1)
        results = load_results(output_dir)
        generate_report(results, output_dir)
        return

    # Connectivity check
    print(f"Endpoint: {ENDPOINT}")
    print(f"Model:    {MODEL}")
    print("Checking connectivity...", end=" ", flush=True)
    try:
        resp = get_client().get(f"{ENDPOINT.rstrip('/')}/v1/models")
        resp.raise_for_status()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("tool_selection_experiments") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    experiments = build_experiments()

    # Save experiment manifest
    manifest = []
    for exp in experiments:
        manifest.append({
            "id": exp["id"],
            "category": exp["category"],
            "description": exp["description"],
            "query_id": exp["query_id"],
            "strategy": exp["strategy"],
            "run_fn": exp["run_fn"],
            "params": exp["params"],
        })
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"Output directory: {output_dir}")
    print(f"Experiments: {len(experiments)}")

    results = run_all(experiments, output_dir)
    generate_report(results, output_dir)

    # Summary
    ok_results = [r for r in results if not r.error]
    tool_exact = sum(1 for r in ok_results if r.tool_correct)
    tool_accept = sum(1 for r in ok_results if r.tool_acceptable)
    print(f"\n{'=' * 60}")
    print(f"Done. Tool exact: {tool_exact}/{len(ok_results)}, acceptable: {tool_accept}/{len(ok_results)}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
