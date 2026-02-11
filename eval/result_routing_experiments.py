"""
Result evaluation, planning & routing experiments for MedGemma 4B IT.

Probes whether the 4B model can:
1. Assess tool result quality (success/partial/empty/error)
2. Route next actions (synthesize/retry/call another/ask user)
3. Plan multi-step tasks (full-plan vs reactive step-by-step)

Follows the structural pattern of tool_selection_experiments.py.

Usage:
    cd docgemma-connect
    uv run python result_routing_experiments.py
    uv run python result_routing_experiments.py --report-only result_routing_experiments/<ts>
    uv run python result_routing_experiments.py --judge result_routing_experiments/<ts>
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


# Cat 1: Result Quality Assessment
class ResultAssessment(BaseModel):
    quality: Literal[
        "success_rich", "success_partial", "no_results",
        "error_retryable", "error_fatal",
    ]
    reasoning: str = PField(max_length=256)


# Cat 2: Next-Action Routing
class NextAction(BaseModel):
    action: Literal[
        "synthesize", "retry_same", "retry_different_args",
        "call_another_tool", "ask_user",
    ]
    reasoning: str = PField(max_length=256)
    next_tool: ToolName | None = None
    modified_query: str | None = PField(default=None, max_length=128)


# Cat 3: Full-Plan Decomposition
class TaskPlan(BaseModel):
    subtask_1: str = PField(max_length=100)
    tool_1: ToolName
    subtask_2: str | None = PField(default=None, max_length=100)
    tool_2: ToolName | None = None
    subtask_3: str | None = PField(default=None, max_length=100)
    tool_3: ToolName | None = None
    subtask_4: str | None = PField(default=None, max_length=100)
    tool_4: ToolName | None = None
    subtask_5: str | None = PField(default=None, max_length=100)
    tool_5: ToolName | None = None


# Cat 4: Reactive Step-by-Step
class NextStep(BaseModel):
    tool: ToolName
    query: str = PField(max_length=128)
    reasoning: str = PField(max_length=256)


# Cat 5: Sufficiency Assessment
class SufficiencyJudgment(BaseModel):
    sufficient: bool
    reasoning: str = PField(max_length=256)
    missing_info: str | None = PField(default=None, max_length=128)


# Cat 6: Error Recovery Strategy
class RecoveryStrategy(BaseModel):
    strategy: Literal[
        "retry_same", "retry_different_args",
        "skip_and_continue", "ask_user",
    ]
    reasoning: str = PField(max_length=256)
    modified_query: str | None = PField(default=None, max_length=128)


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


# ── Tool descriptions ──────────────────────────────────────────────────

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


# ── Mock tool results (20 scenarios) ───────────────────────────────────

MOCK_RESULTS: dict[str, dict] = {
    # === Success results (S-01 to S-06) ===
    "S-01": {
        "id": "S-01",
        "tool": "check_drug_safety",
        "label": "Boxed warning found for dofetilide",
        "result": {
            "brand_name": "dofetilide",
            "has_warning": True,
            "boxed_warning": "TIKOSYN (dofetilide) can cause serious ventricular arrhythmias, primarily Torsade de Pointes. Patients must be placed for a minimum of 3 days in a facility that can provide continuous ECG monitoring.",
            "error": None,
        },
        "expected_quality": "success_rich",
    },
    "S-02": {
        "id": "S-02",
        "tool": "search_medical_literature",
        "label": "3 articles found for SGLT2",
        "result": {
            "query": "SGLT2 inhibitor cardiovascular outcomes",
            "total_found": 3,
            "articles": [
                {"pmid": "34567890", "title": "SGLT2 Inhibitors Reduce Heart Failure Hospitalizations: EMPEROR-Preserved Trial", "authors": "Packer M, et al.", "journal": "N Engl J Med", "pub_date": "2024-01", "abstract": "Empagliflozin significantly reduced risk of cardiovascular death or hospitalization for heart failure in patients with HFpEF."},
                {"pmid": "34567891", "title": "Dapagliflozin in Patients with CKD", "authors": "Heerspink HJL, et al.", "journal": "N Engl J Med", "pub_date": "2024-03", "abstract": "Dapagliflozin reduced risk of sustained decline in eGFR, ESKD, or death from renal or cardiovascular causes."},
                {"pmid": "34567892", "title": "SGLT2 Inhibitors and Cardiovascular Outcomes: Meta-Analysis", "authors": "Zelniker TA, et al.", "journal": "Lancet", "pub_date": "2024-06", "abstract": "SGLT2 inhibitors reduce MACE in patients with T2DM and established ASCVD."},
            ],
            "error": None,
        },
        "expected_quality": "success_rich",
    },
    "S-03": {
        "id": "S-03",
        "tool": "check_drug_interactions",
        "label": "Warfarin+aspirin interaction found",
        "result": {
            "drugs_checked": ["warfarin", "aspirin"],
            "resolved_rxcuis": {"warfarin": "11289", "aspirin": "1191"},
            "interactions": [
                {"drug_pair": ["warfarin", "aspirin"], "severity": "high", "description": "Concurrent use increases bleeding risk. Monitor INR closely and watch for signs of hemorrhage."},
            ],
            "error": None,
        },
        "expected_quality": "success_rich",
    },
    "S-04": {
        "id": "S-04",
        "tool": "find_clinical_trials",
        "label": "2 breast cancer trials found",
        "result": {
            "condition": "triple-negative breast cancer",
            "location": None,
            "total_found": 2,
            "trials": [
                {"nct_id": "NCT05012345", "title": "Pembrolizumab Plus Chemotherapy in TNBC", "status": "Recruiting", "conditions": ["Triple Negative Breast Cancer"], "contact_name": "Dr. Smith", "contact_phone": "555-0100", "contact_email": "smith@example.com", "locations": ["Boston, MA"]},
                {"nct_id": "NCT05067890", "title": "Novel ADC vs Standard of Care in Metastatic TNBC", "status": "Recruiting", "conditions": ["Triple Negative Breast Cancer"], "contact_name": "Dr. Jones", "contact_phone": None, "contact_email": "jones@example.com", "locations": ["Houston, TX", "New York, NY"]},
            ],
            "error": None,
        },
        "expected_quality": "success_rich",
    },
    "S-05": {
        "id": "S-05",
        "tool": "search_patient",
        "label": "1 patient match for Maria Garcia",
        "result": {
            "patients": [
                {"patient_id": "abc-123", "name": "Maria Garcia", "date_of_birth": "1965-03-15"},
            ],
        },
        "expected_quality": "success_rich",
    },
    "S-06": {
        "id": "S-06",
        "tool": "get_patient_chart",
        "label": "Full chart for abc-123",
        "result": {
            "patient_id": "abc-123",
            "name": "Maria Garcia",
            "conditions": ["Type 2 Diabetes Mellitus", "Hypertension", "Hyperlipidemia"],
            "medications": ["Metformin 1000mg BID", "Lisinopril 20mg daily", "Atorvastatin 40mg daily"],
            "allergies": ["Penicillin (rash)"],
            "recent_labs": {"HbA1c": "7.2%", "LDL": "98 mg/dL", "Creatinine": "0.9 mg/dL"},
            "recent_notes": ["2024-01-15: Routine follow-up. Diabetes well controlled. Continue current regimen."],
        },
        "expected_quality": "success_rich",
    },

    # === Partial/ambiguous results (P-01 to P-04) ===
    "P-01": {
        "id": "P-01",
        "tool": "check_drug_safety",
        "label": "No boxed warning for metformin (but CKD question unanswered)",
        "result": {
            "brand_name": "metformin",
            "has_warning": False,
            "boxed_warning": None,
            "error": None,
        },
        "expected_quality": "success_partial",
    },
    "P-02": {
        "id": "P-02",
        "tool": "search_patient",
        "label": "Multiple matches for James Wilson",
        "result": {
            "patients": [
                {"patient_id": "pat-001", "name": "James Wilson", "date_of_birth": "1958-07-22"},
                {"patient_id": "pat-002", "name": "James T. Wilson", "date_of_birth": "1972-11-03"},
                {"patient_id": "pat-003", "name": "James Wilson Jr.", "date_of_birth": "1990-01-15"},
            ],
        },
        "expected_quality": "success_partial",
    },
    "P-03": {
        "id": "P-03",
        "tool": "check_drug_interactions",
        "label": "1 drug unresolved in interaction check",
        "result": {
            "drugs_checked": ["warfarin", "supplement X"],
            "resolved_rxcuis": {"warfarin": "11289", "supplement X": None},
            "interactions": [],
            "error": None,
        },
        "expected_quality": "success_partial",
    },
    "P-04": {
        "id": "P-04",
        "tool": "search_medical_literature",
        "label": "1 article with no abstract",
        "result": {
            "query": "rare enzyme deficiency treatment",
            "total_found": 1,
            "articles": [
                {"pmid": "99887766", "title": "Case Report: Novel Enzyme Replacement Therapy", "authors": "Lee K, et al.", "journal": "Orphanet J Rare Dis", "pub_date": "2023-09", "abstract": None},
            ],
            "error": None,
        },
        "expected_quality": "success_partial",
    },

    # === Empty results (E-01 to E-03) ===
    "E-01": {
        "id": "E-01",
        "tool": "search_medical_literature",
        "label": "0 articles for obscure query",
        "result": {
            "query": "xylotriazole enzyme deficiency zebrafish model",
            "total_found": 0,
            "articles": [],
            "error": None,
        },
        "expected_quality": "no_results",
    },
    "E-02": {
        "id": "E-02",
        "tool": "find_clinical_trials",
        "label": "0 trials for rare condition",
        "result": {
            "condition": "hereditary angioedema type IV",
            "location": None,
            "total_found": 0,
            "trials": [],
            "error": None,
        },
        "expected_quality": "no_results",
    },
    "E-03": {
        "id": "E-03",
        "tool": "search_patient",
        "label": "No match for Xyz Nonexist",
        "result": {
            "patients": [],
        },
        "expected_quality": "no_results",
    },

    # === Error results (X-01 to X-04) ===
    "X-01": {
        "id": "X-01",
        "tool": "check_drug_safety",
        "label": "API timeout",
        "result": {
            "brand_name": "amiodarone",
            "has_warning": False,
            "boxed_warning": None,
            "error": "Request timed out after 30 seconds",
        },
        "expected_quality": "error_retryable",
    },
    "X-02": {
        "id": "X-02",
        "tool": "get_patient_chart",
        "label": "Invalid patient ID",
        "result": {
            "error": "patient_id is required",
        },
        "expected_quality": "error_fatal",
    },
    "X-03": {
        "id": "X-03",
        "tool": "check_drug_interactions",
        "label": "Need 2+ drugs error",
        "result": {
            "drugs_checked": ["aspirin"],
            "resolved_rxcuis": {},
            "interactions": [],
            "error": "Need at least 2 drugs to check interactions",
        },
        "expected_quality": "error_fatal",
    },
    "X-04": {
        "id": "X-04",
        "tool": "search_medical_literature",
        "label": "HTTP 500 error",
        "result": {
            "query": "diabetes management",
            "total_found": 0,
            "articles": [],
            "error": "HTTP error 500: Internal Server Error",
        },
        "expected_quality": "error_retryable",
    },
}


# ── Multi-step accumulated results (M-01 to M-03) ─────────────────────

ACCUMULATED_RESULTS: dict[str, dict] = {
    "M-01": {
        "id": "M-01",
        "label": "search_patient + get_chart done",
        "steps_done": [
            {"tool": "search_patient", "result": {"patients": [{"patient_id": "abc-123", "name": "John Smith", "date_of_birth": "1970-05-20"}]}},
            {"tool": "get_patient_chart", "result": {"patient_id": "abc-123", "name": "John Smith", "conditions": ["Hypertension", "Type 2 Diabetes"], "medications": ["Metformin 500mg BID", "Lisinopril 10mg daily"], "allergies": [], "recent_labs": {"HbA1c": "7.8%"}, "recent_notes": []}},
        ],
    },
    "M-02": {
        "id": "M-02",
        "label": "search_patient + get_chart + check_interactions done",
        "steps_done": [
            {"tool": "search_patient", "result": {"patients": [{"patient_id": "abc-123", "name": "John Smith", "date_of_birth": "1970-05-20"}]}},
            {"tool": "get_patient_chart", "result": {"patient_id": "abc-123", "name": "John Smith", "conditions": ["Atrial Fibrillation", "DVT"], "medications": ["Warfarin 5mg daily", "Metoprolol 25mg BID"], "allergies": ["Aspirin (GI bleeding)"], "recent_labs": {"INR": "2.5"}, "recent_notes": []}},
            {"tool": "check_drug_interactions", "result": {"drugs_checked": ["warfarin", "metoprolol"], "resolved_rxcuis": {"warfarin": "11289", "metoprolol": "6918"}, "interactions": [{"drug_pair": ["warfarin", "metoprolol"], "severity": "moderate", "description": "Metoprolol may increase warfarin levels. Monitor INR."}], "error": None}},
        ],
    },
    "M-03": {
        "id": "M-03",
        "label": "search_patient done, chart not yet retrieved",
        "steps_done": [
            {"tool": "search_patient", "result": {"patients": [{"patient_id": "pat-456", "name": "Maria Garcia", "date_of_birth": "1965-03-15"}]}},
        ],
    },
}


# ── Multi-step tasks (10 tasks for planning experiments) ───────────────

@dataclass
class TaskDef:
    """Ground-truth definition for a multi-step task."""
    id: str
    task: str
    expected_tools: list[str]
    notes: str


TASKS: dict[str, TaskDef] = {
    "T-01": TaskDef(
        id="T-01",
        task="Find patient John Smith, get his chart, check if metformin is safe",
        expected_tools=["search_patient", "get_patient_chart", "check_drug_safety"],
        notes="3-step, sequential deps",
    ),
    "T-02": TaskDef(
        id="T-02",
        task="Check interactions between warfarin, aspirin, and metoprolol, then search for safer alternatives",
        expected_tools=["check_drug_interactions", "search_medical_literature"],
        notes="2-step, result-dependent",
    ),
    "T-03": TaskDef(
        id="T-03",
        task="Get chart for patient abc-123, check medication interactions, save a progress note",
        expected_tools=["get_patient_chart", "check_drug_interactions", "save_clinical_note"],
        notes="3-step, data flows",
    ),
    "T-04": TaskDef(
        id="T-04",
        task="Search for recent SGLT2 studies and find clinical trials for diabetic nephropathy",
        expected_tools=["search_medical_literature", "find_clinical_trials"],
        notes="2-step, independent",
    ),
    "T-05": TaskDef(
        id="T-05",
        task="Find patient Maria Garcia, document penicillin allergy, prescribe amoxicillin 500mg TID",
        expected_tools=["search_patient", "add_allergy", "prescribe_medication"],
        notes="3-step, should flag allergy-Rx conflict",
    ),
    "T-06": TaskDef(
        id="T-06",
        task="Prescribe lisinopril 10mg daily for patient abc-123 and save a note",
        expected_tools=["prescribe_medication", "save_clinical_note"],
        notes="2-step, simple",
    ),
    "T-07": TaskDef(
        id="T-07",
        task="Check dofetilide safety, check interactions with amiodarone, search literature for AF rhythm control",
        expected_tools=["check_drug_safety", "check_drug_interactions", "search_medical_literature"],
        notes="3-step, all external APIs",
    ),
    "T-08": TaskDef(
        id="T-08",
        task="Find patient James Wilson, get his chart, check if his meds have interactions",
        expected_tools=["search_patient", "get_patient_chart", "check_drug_interactions"],
        notes="3-step, each depends on prior",
    ),
    "T-09": TaskDef(
        id="T-09",
        task="Search literature on GLP-1 agonists for weight loss and find recruiting clinical trials",
        expected_tools=["search_medical_literature", "find_clinical_trials"],
        notes="2-step, parallel-capable",
    ),
    "T-10": TaskDef(
        id="T-10",
        task="Review patient abc-123's chart and determine if adding warfarin is safe given current meds",
        expected_tools=["get_patient_chart", "check_drug_safety", "check_drug_interactions"],
        notes="3-step, clinical reasoning",
    ),
}


# ── Routing scenarios (task + result → expected action) ────────────────

@dataclass
class RoutingScenario:
    """A task + tool result pairing with expected next action."""
    id: str
    task: str
    tool_used: str
    result_id: str
    expected_action: str
    acceptable_actions: list[str]
    expected_next_tool: str | None = None


ROUTING_SCENARIOS: dict[str, RoutingScenario] = {
    # Success → synthesize
    "R-01": RoutingScenario("R-01", "Check FDA warnings for dofetilide", "check_drug_safety", "S-01", "synthesize", ["synthesize"]),
    "R-02": RoutingScenario("R-02", "Search for SGLT2 cardiovascular studies", "search_medical_literature", "S-02", "synthesize", ["synthesize"]),
    "R-03": RoutingScenario("R-03", "Check warfarin and aspirin interactions", "check_drug_interactions", "S-03", "synthesize", ["synthesize"]),
    "R-04": RoutingScenario("R-04", "Find clinical trials for TNBC", "find_clinical_trials", "S-04", "synthesize", ["synthesize"]),
    # Partial → call another tool or ask user
    "R-05": RoutingScenario("R-05", "Is metformin safe for CKD stage 4?", "check_drug_safety", "P-01", "call_another_tool", ["call_another_tool", "synthesize"], expected_next_tool="search_medical_literature"),
    "R-06": RoutingScenario("R-06", "Look up James Wilson's medications", "search_patient", "P-02", "ask_user", ["ask_user", "synthesize"]),
    "R-07": RoutingScenario("R-07", "Check warfarin and supplement X interactions", "check_drug_interactions", "P-03", "synthesize", ["synthesize", "call_another_tool"]),
    "R-08": RoutingScenario("R-08", "Find studies on rare enzyme deficiency treatment", "search_medical_literature", "P-04", "synthesize", ["synthesize", "retry_different_args"]),
    # Empty → retry or synthesize (inform no results)
    "R-09": RoutingScenario("R-09", "Search for xylotriazole studies", "search_medical_literature", "E-01", "retry_different_args", ["retry_different_args", "synthesize"]),
    "R-10": RoutingScenario("R-10", "Find trials for hereditary angioedema type IV", "find_clinical_trials", "E-02", "synthesize", ["synthesize", "retry_different_args"]),
    "R-11": RoutingScenario("R-11", "Find patient Xyz Nonexist", "search_patient", "E-03", "ask_user", ["ask_user", "synthesize"]),
    # Error → retry or ask user
    "R-12": RoutingScenario("R-12", "Check amiodarone safety", "check_drug_safety", "X-01", "retry_same", ["retry_same"]),
    "R-13": RoutingScenario("R-13", "Get chart for the patient", "get_patient_chart", "X-02", "ask_user", ["ask_user", "retry_different_args"]),
    "R-14": RoutingScenario("R-14", "Check aspirin interactions", "check_drug_interactions", "X-03", "ask_user", ["ask_user", "retry_different_args"]),
    "R-15": RoutingScenario("R-15", "Search diabetes management literature", "search_medical_literature", "X-04", "retry_same", ["retry_same"]),
    # Multi-step context → next tool needed
    "R-16": RoutingScenario("R-16", "Find John Smith and check his drug safety", "search_patient", "S-05", "call_another_tool", ["call_another_tool"], expected_next_tool="get_patient_chart"),
    "R-17": RoutingScenario("R-17", "Get chart for abc-123 and check interactions", "get_patient_chart", "S-06", "call_another_tool", ["call_another_tool"], expected_next_tool="check_drug_interactions"),
    "R-18": RoutingScenario("R-18", "Find Maria Garcia and prescribe lisinopril", "search_patient", "S-05", "call_another_tool", ["call_another_tool"], expected_next_tool="prescribe_medication"),
    "R-19": RoutingScenario("R-19", "Search SGLT2 studies then find clinical trials", "search_medical_literature", "S-02", "call_another_tool", ["call_another_tool"], expected_next_tool="find_clinical_trials"),
    "R-20": RoutingScenario("R-20", "Find patient John Smith, get chart, check metformin safety", "get_patient_chart", "S-06", "call_another_tool", ["call_another_tool"], expected_next_tool="check_drug_safety"),
}


# ── Sufficiency scenarios ──────────────────────────────────────────────

@dataclass
class SufficiencyScenario:
    """Task + accumulated results → sufficient to answer?"""
    id: str
    task: str
    accumulated_data: str  # JSON string of steps done
    expected_sufficient: bool
    expected_missing: str | None


SUFFICIENCY_SCENARIOS: dict[str, SufficiencyScenario] = {
    # Clearly sufficient (5)
    "SUF-01": SufficiencyScenario("SUF-01", "Find John Smith and review his chart", json.dumps(ACCUMULATED_RESULTS["M-01"]["steps_done"]), True, None),
    "SUF-02": SufficiencyScenario("SUF-02", "Check if John Smith's medications interact", json.dumps(ACCUMULATED_RESULTS["M-02"]["steps_done"]), True, None),
    "SUF-03": SufficiencyScenario("SUF-03", "What are the FDA warnings for dofetilide?", json.dumps([{"tool": "check_drug_safety", "result": MOCK_RESULTS["S-01"]["result"]}]), True, None),
    "SUF-04": SufficiencyScenario("SUF-04", "Find SGLT2 inhibitor studies", json.dumps([{"tool": "search_medical_literature", "result": MOCK_RESULTS["S-02"]["result"]}]), True, None),
    "SUF-05": SufficiencyScenario("SUF-05", "Check warfarin and aspirin interactions", json.dumps([{"tool": "check_drug_interactions", "result": MOCK_RESULTS["S-03"]["result"]}]), True, None),
    # Clearly insufficient (5)
    "SUF-06": SufficiencyScenario("SUF-06", "Find Maria Garcia, get her chart, and check drug interactions", json.dumps(ACCUMULATED_RESULTS["M-03"]["steps_done"]), False, "chart and interactions not checked"),
    "SUF-07": SufficiencyScenario("SUF-07", "Find John Smith, get chart, check metformin safety", json.dumps(ACCUMULATED_RESULTS["M-01"]["steps_done"]), False, "drug safety not checked"),
    "SUF-08": SufficiencyScenario("SUF-08", "Check amiodarone safety", json.dumps([{"tool": "check_drug_safety", "result": MOCK_RESULTS["X-01"]["result"]}]), False, "tool returned error"),
    "SUF-09": SufficiencyScenario("SUF-09", "Find patient Xyz Nonexist and get their chart", json.dumps([{"tool": "search_patient", "result": MOCK_RESULTS["E-03"]["result"]}]), False, "patient not found"),
    "SUF-10": SufficiencyScenario("SUF-10", "Get chart for patient and save a progress note", json.dumps([{"tool": "get_patient_chart", "result": MOCK_RESULTS["X-02"]["result"]}]), False, "chart retrieval failed"),
    # Borderline (5)
    "SUF-11": SufficiencyScenario("SUF-11", "Is metformin safe for my CKD patient?", json.dumps([{"tool": "check_drug_safety", "result": MOCK_RESULTS["P-01"]["result"]}]), False, "CKD-specific safety not addressed"),
    "SUF-12": SufficiencyScenario("SUF-12", "Look up James Wilson's medications", json.dumps([{"tool": "search_patient", "result": MOCK_RESULTS["P-02"]["result"]}]), False, "multiple patients matched"),
    "SUF-13": SufficiencyScenario("SUF-13", "Check warfarin and supplement X interactions", json.dumps([{"tool": "check_drug_interactions", "result": MOCK_RESULTS["P-03"]["result"]}]), False, "supplement X not resolved"),
    "SUF-14": SufficiencyScenario("SUF-14", "Find studies on rare enzyme deficiency", json.dumps([{"tool": "search_medical_literature", "result": MOCK_RESULTS["P-04"]["result"]}]), True, None),
    "SUF-15": SufficiencyScenario("SUF-15", "Find trials for hereditary angioedema type IV", json.dumps([{"tool": "find_clinical_trials", "result": MOCK_RESULTS["E-02"]["result"]}]), True, None),
}


# ── Error recovery scenarios ───────────────────────────────────────────

@dataclass
class ErrorScenario:
    """Task + error result → expected recovery strategy."""
    id: str
    task: str
    tool_used: str
    error_result: dict
    expected_strategy: str
    acceptable_strategies: list[str]


ERROR_SCENARIOS: dict[str, ErrorScenario] = {
    # Timeouts → retry_same
    "ERR-01": ErrorScenario("ERR-01", "Check amiodarone safety", "check_drug_safety", MOCK_RESULTS["X-01"]["result"], "retry_same", ["retry_same"]),
    "ERR-02": ErrorScenario("ERR-02", "Search diabetes literature", "search_medical_literature", MOCK_RESULTS["X-04"]["result"], "retry_same", ["retry_same"]),
    # Bad args → retry_different_args or ask_user
    "ERR-03": ErrorScenario("ERR-03", "Get chart for the patient", "get_patient_chart", MOCK_RESULTS["X-02"]["result"], "ask_user", ["ask_user", "retry_different_args"]),
    "ERR-04": ErrorScenario("ERR-04", "Check aspirin interactions", "check_drug_interactions", MOCK_RESULTS["X-03"]["result"], "ask_user", ["ask_user", "retry_different_args"]),
    # Empty results → retry_different_args or skip
    "ERR-05": ErrorScenario("ERR-05", "Search for xylotriazole studies", "search_medical_literature", MOCK_RESULTS["E-01"]["result"], "retry_different_args", ["retry_different_args", "skip_and_continue"]),
    "ERR-06": ErrorScenario("ERR-06", "Find patient Xyz Nonexist", "search_patient", MOCK_RESULTS["E-03"]["result"], "ask_user", ["ask_user", "skip_and_continue"]),
    "ERR-07": ErrorScenario("ERR-07", "Find trials for hereditary angioedema type IV", "find_clinical_trials", MOCK_RESULTS["E-02"]["result"], "skip_and_continue", ["skip_and_continue", "retry_different_args"]),
    # Partial / ambiguous → various
    "ERR-08": ErrorScenario("ERR-08", "Look up James Wilson (3 matches)", "search_patient", MOCK_RESULTS["P-02"]["result"], "ask_user", ["ask_user"]),
    "ERR-09": ErrorScenario("ERR-09", "Check warfarin + supplement X (unresolved drug)", "check_drug_interactions", MOCK_RESULTS["P-03"]["result"], "ask_user", ["ask_user", "retry_different_args"]),
    # Contextual retries
    "ERR-10": ErrorScenario("ERR-10", "Search rare enzyme deficiency treatment", "search_medical_literature", {"query": "rare enzyme deficiency treatment options", "total_found": 0, "articles": [], "error": None}, "retry_different_args", ["retry_different_args", "skip_and_continue"]),
    "ERR-11": ErrorScenario("ERR-11", "Check safety of experimental drug XYZ-789", "check_drug_safety", {"brand_name": "XYZ-789", "has_warning": False, "boxed_warning": None, "error": "Drug not found in FDA database"}, "skip_and_continue", ["skip_and_continue", "retry_different_args"]),
    "ERR-12": ErrorScenario("ERR-12", "Get patient chart (server error)", "get_patient_chart", {"error": "HTTP error 503: Service Unavailable"}, "retry_same", ["retry_same"]),
    "ERR-13": ErrorScenario("ERR-13", "Search literature (rate limited)", "search_medical_literature", {"query": "cancer immunotherapy", "total_found": 0, "articles": [], "error": "HTTP error 429: Too Many Requests"}, "retry_same", ["retry_same"]),
    "ERR-14": ErrorScenario("ERR-14", "Check interactions (malformed drug list)", "check_drug_interactions", {"drugs_checked": [], "resolved_rxcuis": {}, "interactions": [], "error": "Invalid input: drug_list cannot be empty"}, "retry_different_args", ["retry_different_args", "ask_user"]),
    "ERR-15": ErrorScenario("ERR-15", "Find clinical trials (network error)", "find_clinical_trials", {"condition": "lung cancer", "location": None, "total_found": 0, "trials": [], "error": "ConnectionError: Failed to connect to ClinicalTrials.gov"}, "retry_same", ["retry_same"]),
}


# ── Reactive planning snapshots (3 per task) ──────────────────────────

def _build_reactive_snapshots() -> dict[str, list[dict]]:
    """Build 3 snapshots per task: step 0, step 1, step 2."""
    snapshots: dict[str, list[dict]] = {}

    for tid, tdef in TASKS.items():
        task_snaps = []

        # Snapshot 0: fresh start (no tools done)
        task_snaps.append({
            "snapshot": 0,
            "steps_done": [],
            "expected_next_tool": tdef.expected_tools[0],
        })

        # Snapshot 1: first tool done with mock result
        first_tool = tdef.expected_tools[0]
        mock_result_1 = _get_mock_for_tool(first_tool, tid)
        task_snaps.append({
            "snapshot": 1,
            "steps_done": [{"tool": first_tool, "result": mock_result_1}],
            "expected_next_tool": tdef.expected_tools[1] if len(tdef.expected_tools) > 1 else "none",
        })

        # Snapshot 2: two tools done (if task has 3+ steps)
        if len(tdef.expected_tools) >= 3:
            second_tool = tdef.expected_tools[1]
            mock_result_2 = _get_mock_for_tool(second_tool, tid)
            task_snaps.append({
                "snapshot": 2,
                "steps_done": [
                    {"tool": first_tool, "result": mock_result_1},
                    {"tool": second_tool, "result": mock_result_2},
                ],
                "expected_next_tool": tdef.expected_tools[2],
            })
        else:
            # 2-step tasks: after both done, should be "none"
            second_tool = tdef.expected_tools[1] if len(tdef.expected_tools) > 1 else "none"
            mock_result_2 = _get_mock_for_tool(second_tool, tid)
            task_snaps.append({
                "snapshot": 2,
                "steps_done": [
                    {"tool": first_tool, "result": mock_result_1},
                    {"tool": second_tool, "result": mock_result_2},
                ],
                "expected_next_tool": "none",
            })

        snapshots[tid] = task_snaps
    return snapshots


def _get_mock_for_tool(tool: str, task_id: str) -> dict:
    """Return a plausible mock result for a given tool in context of a task."""
    _task_mocks: dict[str, dict] = {
        "search_patient": {"patients": [{"patient_id": "abc-123", "name": "John Smith", "date_of_birth": "1970-05-20"}]},
        "get_patient_chart": {"patient_id": "abc-123", "name": "John Smith", "conditions": ["Type 2 Diabetes", "Hypertension"], "medications": ["Metformin 500mg BID", "Lisinopril 10mg daily"], "allergies": [], "recent_labs": {"HbA1c": "7.8%"}, "recent_notes": []},
        "check_drug_safety": {"brand_name": "metformin", "has_warning": False, "boxed_warning": None, "error": None},
        "check_drug_interactions": {"drugs_checked": ["metformin", "lisinopril"], "resolved_rxcuis": {"metformin": "6809", "lisinopril": "29046"}, "interactions": [], "error": None},
        "search_medical_literature": {"query": "SGLT2 inhibitor outcomes", "total_found": 2, "articles": [{"pmid": "111", "title": "SGLT2 Meta-Analysis", "authors": "Kim J et al.", "journal": "JAMA", "pub_date": "2024", "abstract": "Positive outcomes."}], "error": None},
        "find_clinical_trials": {"condition": "diabetic nephropathy", "location": None, "total_found": 1, "trials": [{"nct_id": "NCT99999", "title": "SGLT2 in CKD Trial", "status": "Recruiting", "conditions": ["Diabetic Nephropathy"], "contact_name": "Dr. Lee", "contact_phone": None, "contact_email": None, "locations": ["Boston, MA"]}], "error": None},
        "add_allergy": {"success": True, "message": "Allergy documented: penicillin"},
        "prescribe_medication": {"success": True, "message": "Prescribed lisinopril 10mg daily"},
        "save_clinical_note": {"success": True, "message": "Progress note saved"},
    }
    return _task_mocks.get(tool, {"error": None, "message": "OK"})


REACTIVE_SNAPSHOTS = _build_reactive_snapshots()


# ── Prompt templates ───────────────────────────────────────────────────

def make_result_assessment_prompt(tool: str, result: dict) -> str:
    """Cat 1: Assess quality of a tool result."""
    return f"""You are evaluating the quality of a tool result from a medical AI system.

Tool used: {tool}
Tool result:
{json.dumps(result, indent=2)}

Classify the result quality:
- "success_rich": Complete, useful data returned (warnings found, articles with abstracts, patient match, full chart, interactions found)
- "success_partial": Some data returned but incomplete or ambiguous (no abstract, multiple patient matches, drug not resolved, tool answered a different question than asked)
- "no_results": Tool returned successfully but found nothing (0 articles, 0 trials, no patient match)
- "error_retryable": Tool failed with a transient error (timeout, HTTP 500, rate limit, connection error)
- "error_fatal": Tool failed with a permanent error (invalid args, missing required field, drug not in database)

Return the quality classification and brief reasoning."""


def make_routing_prompt(task: str, tool_used: str, result: dict) -> str:
    """Cat 2: Decide next action given a task and tool result."""
    return f"""You are a medical AI assistant deciding what to do next.

Original task: {task}
Tool used: {tool_used}
Tool result:
{json.dumps(result, indent=2)}

Available tools:
{TOOL_DESC_SHORT}

What should happen next?
- "synthesize": The result is sufficient — generate a response to the user
- "retry_same": The tool failed transiently (timeout, server error) — try the exact same call again
- "retry_different_args": The tool returned nothing or wrong results — try with modified query/args
- "call_another_tool": The result is good but the task needs more information from a different tool
- "ask_user": Need clarification from the user (ambiguous patient, missing info)

Return the action, reasoning, and if applicable the next_tool or modified_query."""


def make_plan_prompt(task: str) -> str:
    """Cat 3: Decompose a multi-step task into a full plan."""
    return f"""Break this clinical task into sequential subtasks. Each subtask needs exactly one tool.

Task: {task}

Available tools:
{TOOL_DESC_SHORT}

Plan the subtasks in execution order. Later steps may depend on earlier results.
Fill subtask_1/tool_1 through subtask_5/tool_5 (use null for unused slots)."""


def make_plan_with_thinking_prompt(task: str) -> str:
    """Cat 3 variant: plan with thinking prefix."""
    return f"""Let me plan this step by step.

Task: {task}

Available tools:
{TOOL_DESC_SHORT}

Think about what needs to happen first, what depends on what, then fill the plan.
Fill subtask_1/tool_1 through subtask_5/tool_5 (use null for unused slots)."""


def make_plan_reasoning_prompt(task: str) -> str:
    """Cat 3 variant: free-form reasoning before structured plan."""
    return f"""Think through how to accomplish this clinical task step by step.
What tools are needed? What order? What data flows between steps?

Task: {task}

Available tools:
{TOOL_DESC_SHORT}"""


def make_plan_from_reasoning_prompt(task: str, reasoning: str) -> str:
    """Cat 3 variant: structured plan after free-form reasoning."""
    return f"""Based on this reasoning, create the plan.

Task: {task}
Reasoning: {reasoning}

Fill subtask_1/tool_1 through subtask_5/tool_5 (use null for unused slots)."""


def make_next_step_prompt(task: str, steps_done: list[dict]) -> str:
    """Cat 4: Decide the next step given what's done so far."""
    done_text = "None yet." if not steps_done else json.dumps(steps_done, indent=2)
    return f"""You are a medical AI assistant working on a multi-step task.

Task: {task}

Steps completed so far:
{done_text}

Available tools:
{TOOL_DESC_SHORT}

What is the NEXT single step to take? Pick the tool, write the query, and explain why.
If all steps are done, use tool "none"."""


def make_sufficiency_prompt(task: str, accumulated_data: str) -> str:
    """Cat 5: Assess whether accumulated results are sufficient."""
    return f"""You are a medical AI assistant. Determine if you have enough information to answer the user's question.

User's question: {task}

Data gathered so far:
{accumulated_data}

Is this data sufficient to provide a complete, accurate answer?
If not, what information is still missing?"""


def make_sufficiency_thinking_prompt(task: str, accumulated_data: str) -> str:
    """Cat 5 variant: with thinking prefix."""
    return f"""Let me think about whether I have enough information.

User's question: {task}

Data gathered so far:
{accumulated_data}

Consider: Does the data fully answer the question? Are there gaps? Is any tool result incomplete or an error?"""


def make_recovery_prompt(task: str, tool_used: str, error_result: dict) -> str:
    """Cat 6: Decide how to recover from an error."""
    return f"""A tool call failed or returned unexpected results. Decide how to recover.

Task: {task}
Tool used: {tool_used}
Result:
{json.dumps(error_result, indent=2)}

Recovery options:
- "retry_same": Try the exact same call again (for transient errors like timeouts, HTTP 500, rate limits)
- "retry_different_args": Try with modified arguments (for empty results, wrong query)
- "skip_and_continue": Skip this step and continue with remaining tasks (for non-critical failures)
- "ask_user": Ask the user for help (for ambiguous results, missing required info)

Choose the best recovery strategy and explain why."""


def make_recovery_thinking_prompt(task: str, tool_used: str, error_result: dict) -> str:
    """Cat 6 variant: with thinking prefix."""
    return f"""Let me analyze this error and decide the best recovery approach.

Task: {task}
Tool used: {tool_used}
Result:
{json.dumps(error_result, indent=2)}

Recovery options:
- "retry_same": Try the exact same call again (for transient errors like timeouts, HTTP 500, rate limits)
- "retry_different_args": Try with modified arguments (for empty results, wrong query)
- "skip_and_continue": Skip this step and continue with remaining tasks (for non-critical failures)
- "ask_user": Ask the user for help (for ambiguous results, missing required info)

Think about what went wrong, whether it's transient or permanent, and choose wisely."""


# ── Result container ──────────────────────────────────────────────────

@dataclass
class ExperimentResult:
    experiment_id: str
    category: str
    description: str
    scenario_id: str
    scenario_type: str  # "result_assessment", "routing", "planning", etc.
    strategy: str
    params: dict

    # Ground truth
    expected_output: dict = field(default_factory=dict)
    acceptable_outputs: list = field(default_factory=list)

    # Model output
    raw_response: str = ""
    parsed_output: dict = field(default_factory=dict)
    output_correct: bool = False
    output_acceptable: bool = False

    # Multi-call
    num_llm_calls: int = 1
    per_call_latency_ms: list = field(default_factory=list)
    total_latency_ms: float = 0.0
    error: str | None = None

    # Cross-reference
    has_thinking_tokens: bool = False
    thinking_prefix_used: bool = False
    reasoning_text: str = ""

    # Gemini judge
    judge_correct: str | None = None
    judge_reasoning_score: int | None = None
    judge_overall_score: int | None = None
    judge_rationale: str | None = None


# ── Experiment definitions ─────────────────────────────────────────────

def build_experiments() -> list[dict]:
    """Build ~220 experiment definitions across 8 categories."""
    experiments = []

    # ================================================================
    # CAT 1: Result Quality Assessment (20 exps, 20 calls)
    # ================================================================
    for mid, mock in MOCK_RESULTS.items():
        experiments.append({
            "id": f"cat1-quality-{mid}",
            "category": "1_result_quality",
            "description": f"Quality assessment: {mock['label']}",
            "scenario_id": mid,
            "scenario_type": "result_assessment",
            "strategy": "direct",
            "run_fn": "single_call",
            "messages_fn": lambda _mid=mid: [
                {"role": "user", "content": make_result_assessment_prompt(
                    MOCK_RESULTS[_mid]["tool"], MOCK_RESULTS[_mid]["result"]
                )},
            ],
            "schema_cls": ResultAssessment,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"quality": mock["expected_quality"]},
            "acceptable": [mock["expected_quality"]],
        })

    # ================================================================
    # CAT 2: Next-Action Routing (40 exps = 20 scenarios x 2 temps)
    # ================================================================
    for temp in [0.0, 0.3]:
        temp_label = f"T{temp}"
        for rid, rsc in ROUTING_SCENARIOS.items():
            mock = MOCK_RESULTS[rsc.result_id]
            experiments.append({
                "id": f"cat2-routing-{temp_label}-{rid}",
                "category": "2_next_action_routing",
                "description": f"Routing {temp_label}: {rsc.task[:40]}",
                "scenario_id": rid,
                "scenario_type": "routing",
                "strategy": f"routing_{temp_label}",
                "run_fn": "single_call",
                "messages_fn": lambda _rid=rid: [
                    {"role": "user", "content": make_routing_prompt(
                        ROUTING_SCENARIOS[_rid].task,
                        ROUTING_SCENARIOS[_rid].tool_used,
                        MOCK_RESULTS[ROUTING_SCENARIOS[_rid].result_id]["result"],
                    )},
                ],
                "schema_cls": NextAction,
                "params": {"temperature": temp, "max_tokens": 512},
                "expected": {
                    "action": rsc.expected_action,
                    "next_tool": rsc.expected_next_tool,
                },
                "acceptable": rsc.acceptable_actions,
            })

    # ================================================================
    # CAT 3: Full-Plan Decomposition (30 exps = 10 tasks x 3 configs)
    # ================================================================
    for tid, tdef in TASKS.items():
        # Config A: no_prefix (T=0.0)
        experiments.append({
            "id": f"cat3-plan-no_prefix-{tid}",
            "category": "3_full_plan",
            "description": f"Plan no-prefix: {tdef.task[:40]}",
            "scenario_id": tid,
            "scenario_type": "planning",
            "strategy": "no_prefix",
            "run_fn": "single_call",
            "messages_fn": lambda _tid=tid: [
                {"role": "user", "content": make_plan_prompt(TASKS[_tid].task)},
            ],
            "schema_cls": TaskPlan,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"tools": tdef.expected_tools},
            "acceptable": [],
        })

        # Config B: thinking_prefix (T=0.0)
        experiments.append({
            "id": f"cat3-plan-thinking-{tid}",
            "category": "3_full_plan",
            "description": f"Plan with-thinking: {tdef.task[:40]}",
            "scenario_id": tid,
            "scenario_type": "planning",
            "strategy": "thinking_prefix",
            "run_fn": "single_call",
            "messages_fn": lambda _tid=tid: [
                {"role": "user", "content": make_plan_with_thinking_prompt(TASKS[_tid].task)},
            ],
            "schema_cls": TaskPlan,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"tools": tdef.expected_tools},
            "acceptable": [],
        })

        # Config C: free_reason_first (T=0.3 → T=0.0, 2 calls)
        experiments.append({
            "id": f"cat3-plan-reason_first-{tid}",
            "category": "3_full_plan",
            "description": f"Plan reason-first: {tdef.task[:40]}",
            "scenario_id": tid,
            "scenario_type": "planning",
            "strategy": "reason_first",
            "run_fn": "reason_then_plan",
            "params": {"temperature_reason": 0.3, "temperature_plan": 0.0, "max_tokens": 512},
            "expected": {"tools": tdef.expected_tools},
            "acceptable": [],
        })

    # ================================================================
    # CAT 4: Reactive Step-by-Step (30 exps = 10 tasks x 3 snapshots)
    # ================================================================
    for tid, tdef in TASKS.items():
        for snap in REACTIVE_SNAPSHOTS[tid]:
            snap_idx = snap["snapshot"]
            experiments.append({
                "id": f"cat4-reactive-{tid}-snap{snap_idx}",
                "category": "4_reactive_planning",
                "description": f"Reactive step {snap_idx}: {tdef.task[:30]}",
                "scenario_id": f"{tid}-snap{snap_idx}",
                "scenario_type": "reactive",
                "strategy": f"snapshot_{snap_idx}",
                "run_fn": "single_call",
                "messages_fn": lambda _tid=tid, _si=snap_idx: [
                    {"role": "user", "content": make_next_step_prompt(
                        TASKS[_tid].task,
                        REACTIVE_SNAPSHOTS[_tid][_si]["steps_done"],
                    )},
                ],
                "schema_cls": NextStep,
                "params": {"temperature": 0.0, "max_tokens": 512},
                "expected": {"tool": snap["expected_next_tool"]},
                "acceptable": [],
            })

    # ================================================================
    # CAT 5: Sufficiency Assessment (30 exps = 15 scenarios x 2 modes)
    # ================================================================
    for sid, ssc in SUFFICIENCY_SCENARIOS.items():
        # Without thinking
        experiments.append({
            "id": f"cat5-sufficiency-no_think-{sid}",
            "category": "5_sufficiency",
            "description": f"Sufficiency no-think: {ssc.task[:35]}",
            "scenario_id": sid,
            "scenario_type": "sufficiency",
            "strategy": "no_think",
            "run_fn": "single_call",
            "messages_fn": lambda _sid=sid: [
                {"role": "user", "content": make_sufficiency_prompt(
                    SUFFICIENCY_SCENARIOS[_sid].task,
                    SUFFICIENCY_SCENARIOS[_sid].accumulated_data,
                )},
            ],
            "schema_cls": SufficiencyJudgment,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"sufficient": ssc.expected_sufficient},
            "acceptable": [],
        })
        # With thinking
        experiments.append({
            "id": f"cat5-sufficiency-think-{sid}",
            "category": "5_sufficiency",
            "description": f"Sufficiency think: {ssc.task[:35]}",
            "scenario_id": sid,
            "scenario_type": "sufficiency",
            "strategy": "think",
            "run_fn": "single_call",
            "messages_fn": lambda _sid=sid: [
                {"role": "user", "content": make_sufficiency_thinking_prompt(
                    SUFFICIENCY_SCENARIOS[_sid].task,
                    SUFFICIENCY_SCENARIOS[_sid].accumulated_data,
                )},
            ],
            "schema_cls": SufficiencyJudgment,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"sufficient": ssc.expected_sufficient},
            "acceptable": [],
        })

    # ================================================================
    # CAT 6: Error Recovery Strategy (30 exps = 15 errors x 2 modes)
    # ================================================================
    for eid, esc in ERROR_SCENARIOS.items():
        # Without thinking
        experiments.append({
            "id": f"cat6-recovery-no_think-{eid}",
            "category": "6_error_recovery",
            "description": f"Recovery no-think: {esc.task[:35]}",
            "scenario_id": eid,
            "scenario_type": "recovery",
            "strategy": "no_think",
            "run_fn": "single_call",
            "messages_fn": lambda _eid=eid: [
                {"role": "user", "content": make_recovery_prompt(
                    ERROR_SCENARIOS[_eid].task,
                    ERROR_SCENARIOS[_eid].tool_used,
                    ERROR_SCENARIOS[_eid].error_result,
                )},
            ],
            "schema_cls": RecoveryStrategy,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"strategy": esc.expected_strategy},
            "acceptable": esc.acceptable_strategies,
        })
        # With thinking
        experiments.append({
            "id": f"cat6-recovery-think-{eid}",
            "category": "6_error_recovery",
            "description": f"Recovery think: {esc.task[:35]}",
            "scenario_id": eid,
            "scenario_type": "recovery",
            "strategy": "think",
            "run_fn": "single_call",
            "messages_fn": lambda _eid=eid: [
                {"role": "user", "content": make_recovery_thinking_prompt(
                    ERROR_SCENARIOS[_eid].task,
                    ERROR_SCENARIOS[_eid].tool_used,
                    ERROR_SCENARIOS[_eid].error_result,
                )},
            ],
            "schema_cls": RecoveryStrategy,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"strategy": esc.expected_strategy},
            "acceptable": esc.acceptable_strategies,
        })

    # ================================================================
    # CAT 7: Full-Plan vs Reactive Simulation (20 exps = 10 tasks x 2)
    # ================================================================
    for tid, tdef in TASKS.items():
        # Full-plan: 1 decompose call
        experiments.append({
            "id": f"cat7-comparison-fullplan-{tid}",
            "category": "7_plan_vs_reactive",
            "description": f"Full-plan: {tdef.task[:40]}",
            "scenario_id": tid,
            "scenario_type": "comparison_fullplan",
            "strategy": "full_plan",
            "run_fn": "single_call",
            "messages_fn": lambda _tid=tid: [
                {"role": "user", "content": make_plan_prompt(TASKS[_tid].task)},
            ],
            "schema_cls": TaskPlan,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"tools": tdef.expected_tools},
            "acceptable": [],
        })
        # Reactive: multi-step simulation
        experiments.append({
            "id": f"cat7-comparison-reactive-{tid}",
            "category": "7_plan_vs_reactive",
            "description": f"Reactive sim: {tdef.task[:40]}",
            "scenario_id": tid,
            "scenario_type": "comparison_reactive",
            "strategy": "reactive_sim",
            "run_fn": "reactive_simulation",
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"tools": tdef.expected_tools},
            "acceptable": [],
        })

    # ================================================================
    # CAT 8: Thinking Mode Across Tasks (20 exps = 10 scenarios x 2)
    # Hard scenarios from Cat 2 and Cat 5
    # ================================================================
    hard_routing_ids = ["R-05", "R-06", "R-09", "R-11", "R-13"]
    hard_suf_ids = ["SUF-07", "SUF-11", "SUF-12", "SUF-13", "SUF-06"]

    for rid in hard_routing_ids:
        rsc = ROUTING_SCENARIOS[rid]
        mock = MOCK_RESULTS[rsc.result_id]
        # No thinking
        experiments.append({
            "id": f"cat8-thinking-routing-no_think-{rid}",
            "category": "8_thinking_effect",
            "description": f"Hard routing no-think: {rsc.task[:30]}",
            "scenario_id": rid,
            "scenario_type": "thinking_routing",
            "strategy": "no_think",
            "run_fn": "single_call",
            "messages_fn": lambda _rid=rid: [
                {"role": "user", "content": make_routing_prompt(
                    ROUTING_SCENARIOS[_rid].task,
                    ROUTING_SCENARIOS[_rid].tool_used,
                    MOCK_RESULTS[ROUTING_SCENARIOS[_rid].result_id]["result"],
                )},
            ],
            "schema_cls": NextAction,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {
                "action": rsc.expected_action,
                "next_tool": rsc.expected_next_tool,
            },
            "acceptable": rsc.acceptable_actions,
        })
        # With thinking prefix
        experiments.append({
            "id": f"cat8-thinking-routing-think-{rid}",
            "category": "8_thinking_effect",
            "description": f"Hard routing think: {rsc.task[:30]}",
            "scenario_id": rid,
            "scenario_type": "thinking_routing",
            "strategy": "think",
            "run_fn": "single_call_with_prefix",
            "prefix": "Let me analyze this result carefully. ",
            "messages_fn": lambda _rid=rid: [
                {"role": "user", "content": make_routing_prompt(
                    ROUTING_SCENARIOS[_rid].task,
                    ROUTING_SCENARIOS[_rid].tool_used,
                    MOCK_RESULTS[ROUTING_SCENARIOS[_rid].result_id]["result"],
                )},
            ],
            "schema_cls": NextAction,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {
                "action": rsc.expected_action,
                "next_tool": rsc.expected_next_tool,
            },
            "acceptable": rsc.acceptable_actions,
        })

    for sid in hard_suf_ids:
        ssc = SUFFICIENCY_SCENARIOS[sid]
        # No thinking
        experiments.append({
            "id": f"cat8-thinking-suf-no_think-{sid}",
            "category": "8_thinking_effect",
            "description": f"Hard suf no-think: {ssc.task[:30]}",
            "scenario_id": sid,
            "scenario_type": "thinking_sufficiency",
            "strategy": "no_think",
            "run_fn": "single_call",
            "messages_fn": lambda _sid=sid: [
                {"role": "user", "content": make_sufficiency_prompt(
                    SUFFICIENCY_SCENARIOS[_sid].task,
                    SUFFICIENCY_SCENARIOS[_sid].accumulated_data,
                )},
            ],
            "schema_cls": SufficiencyJudgment,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"sufficient": ssc.expected_sufficient},
            "acceptable": [],
        })
        # With thinking
        experiments.append({
            "id": f"cat8-thinking-suf-think-{sid}",
            "category": "8_thinking_effect",
            "description": f"Hard suf think: {ssc.task[:30]}",
            "scenario_id": sid,
            "scenario_type": "thinking_sufficiency",
            "strategy": "think",
            "run_fn": "single_call",
            "messages_fn": lambda _sid=sid: [
                {"role": "user", "content": make_sufficiency_thinking_prompt(
                    SUFFICIENCY_SCENARIOS[_sid].task,
                    SUFFICIENCY_SCENARIOS[_sid].accumulated_data,
                )},
            ],
            "schema_cls": SufficiencyJudgment,
            "params": {"temperature": 0.0, "max_tokens": 512},
            "expected": {"sufficient": ssc.expected_sufficient},
            "acceptable": [],
        })

    return experiments


# ── Evaluation helpers ─────────────────────────────────────────────────

def evaluate_result(result: ExperimentResult):
    """Per-category deterministic evaluation."""
    expected = result.expected_output
    parsed = result.parsed_output
    acceptable = result.acceptable_outputs

    if result.scenario_type == "result_assessment":
        # Exact match on quality field
        result.output_correct = parsed.get("quality") == expected.get("quality")
        result.output_acceptable = result.output_correct

    elif result.scenario_type == "routing":
        action = parsed.get("action", "")
        result.output_correct = action == expected.get("action")
        result.output_acceptable = action in acceptable if acceptable else result.output_correct
        # Check next_tool if applicable
        if expected.get("next_tool") and action == "call_another_tool":
            if parsed.get("next_tool") != expected["next_tool"]:
                result.output_correct = False

    elif result.scenario_type in ("planning", "comparison_fullplan"):
        # Extract tool sequence from plan
        plan_tools = _extract_plan_tools(parsed)
        expected_tools = expected.get("tools", [])
        result.output_correct = plan_tools == expected_tools
        # Acceptable: correct tools in any order, or subset
        result.output_acceptable = set(plan_tools) == set(expected_tools)

    elif result.scenario_type in ("reactive", "comparison_reactive"):
        expected_tool = expected.get("tool", "")
        if result.scenario_type == "comparison_reactive":
            # For reactive sim, check the full tool sequence
            reactive_tools = parsed.get("reactive_tools", [])
            expected_tools = expected.get("tools", [])
            result.output_correct = reactive_tools == expected_tools
            result.output_acceptable = set(reactive_tools) == set(expected_tools)
        else:
            result.output_correct = parsed.get("tool") == expected_tool
            result.output_acceptable = result.output_correct

    elif result.scenario_type == "sufficiency":
        result.output_correct = parsed.get("sufficient") == expected.get("sufficient")
        result.output_acceptable = result.output_correct

    elif result.scenario_type == "recovery":
        strategy = parsed.get("strategy", "")
        result.output_correct = strategy == expected.get("strategy")
        result.output_acceptable = strategy in acceptable if acceptable else result.output_correct

    elif result.scenario_type in ("thinking_routing",):
        action = parsed.get("action", "")
        result.output_correct = action == expected.get("action")
        result.output_acceptable = action in acceptable if acceptable else result.output_correct

    elif result.scenario_type in ("thinking_sufficiency",):
        result.output_correct = parsed.get("sufficient") == expected.get("sufficient")
        result.output_acceptable = result.output_correct


def _extract_plan_tools(parsed: dict) -> list[str]:
    """Extract ordered tool list from a TaskPlan parsed dict."""
    tools = []
    for i in range(1, 6):
        tool = parsed.get(f"tool_{i}")
        if tool and tool != "none":
            tools.append(tool)
    return tools


# ── Runners ────────────────────────────────────────────────────────────

def run_single_call(exp: dict) -> ExperimentResult:
    """Single LLM call with Outlines constrained schema."""
    messages = exp["messages_fn"]()
    schema_cls = exp["schema_cls"]
    params = dict(exp["params"])

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        scenario_id=exp["scenario_id"],
        scenario_type=exp["scenario_type"],
        strategy=exp["strategy"],
        params=exp["params"],
        expected_output=exp.get("expected", {}),
        acceptable_outputs=exp.get("acceptable", []),
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

        clean = THINKING_RE.sub("", raw).strip()
        parsed = json.loads(clean)
        result.parsed_output = parsed
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


def run_single_call_with_prefix(exp: dict) -> ExperimentResult:
    """Single LLM call with assistant prefix (thinking mode)."""
    messages = exp["messages_fn"]()
    prefix = exp.get("prefix", "Let me think step by step. ")
    messages.append({"role": "assistant", "content": prefix})
    schema_cls = exp["schema_cls"]
    params = dict(exp["params"])

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        scenario_id=exp["scenario_id"],
        scenario_type=exp["scenario_type"],
        strategy=exp["strategy"],
        params=exp["params"],
        expected_output=exp.get("expected", {}),
        acceptable_outputs=exp.get("acceptable", []),
        num_llm_calls=1,
        thinking_prefix_used=True,
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

        clean = THINKING_RE.sub("", raw).strip()
        parsed = json.loads(clean)
        result.parsed_output = parsed
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


def run_reason_then_plan(exp: dict) -> ExperimentResult:
    """Two-stage: free-form reasoning then constrained plan."""
    params = dict(exp["params"])
    tid = exp["scenario_id"]
    tdef = TASKS[tid]

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        scenario_id=exp["scenario_id"],
        scenario_type=exp["scenario_type"],
        strategy=exp["strategy"],
        params=exp["params"],
        expected_output=exp.get("expected", {}),
        acceptable_outputs=exp.get("acceptable", []),
        num_llm_calls=2,
    )

    latencies = []

    try:
        # Call 1: free-form reasoning
        prompt1 = make_plan_reasoning_prompt(tdef.task)
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

        # Call 2: constrained plan
        prompt2 = make_plan_from_reasoning_prompt(tdef.task, result.reasoning_text)
        t0 = time.monotonic()
        resp2 = call_model(
            [{"role": "user", "content": prompt2}],
            max_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature_plan", 0.0),
            response_format=make_response_format(TaskPlan),
        )
        latencies.append((time.monotonic() - t0) * 1000)

        raw2 = resp2["choices"][0]["message"]["content"]
        result.raw_response = raw2
        clean = THINKING_RE.sub("", raw2).strip()
        parsed = json.loads(clean)
        result.parsed_output = parsed

        result.per_call_latency_ms = latencies
        result.total_latency_ms = sum(latencies)
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


def run_reactive_simulation(exp: dict) -> ExperimentResult:
    """Multi-call reactive simulation: iterate step-by-step with mock results."""
    params = dict(exp["params"])
    tid = exp["scenario_id"]
    tdef = TASKS[tid]

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        scenario_id=exp["scenario_id"],
        scenario_type="comparison_reactive",
        strategy=exp["strategy"],
        params=exp["params"],
        expected_output=exp.get("expected", {}),
        acceptable_outputs=exp.get("acceptable", []),
    )

    latencies = []
    steps_done: list[dict] = []
    reactive_tools: list[str] = []
    max_steps = 5

    try:
        for step_i in range(max_steps):
            prompt = make_next_step_prompt(tdef.task, steps_done)
            t0 = time.monotonic()
            resp = call_model(
                [{"role": "user", "content": prompt}],
                max_tokens=params.get("max_tokens", 512),
                temperature=params.get("temperature", 0.0),
                response_format=make_response_format(NextStep),
            )
            latencies.append((time.monotonic() - t0) * 1000)

            raw = resp["choices"][0]["message"]["content"]
            if step_i == 0:
                result.has_thinking_tokens = THINKING_OPEN in raw

            clean = THINKING_RE.sub("", raw).strip()
            parsed = json.loads(clean)
            tool = parsed.get("tool", "none")

            if tool == "none":
                break

            reactive_tools.append(tool)
            mock_result = _get_mock_for_tool(tool, tid)
            steps_done.append({"tool": tool, "result": mock_result})

        result.num_llm_calls = len(latencies)
        result.per_call_latency_ms = latencies
        result.total_latency_ms = sum(latencies)
        result.raw_response = json.dumps({"reactive_tools": reactive_tools, "steps": len(reactive_tools)})
        result.parsed_output = {"reactive_tools": reactive_tools}
    except Exception as e:
        result.error = str(e)

    evaluate_result(result)
    return result


# ── Dispatcher ─────────────────────────────────────────────────────────

RUN_DISPATCH = {
    "single_call": run_single_call,
    "single_call_with_prefix": run_single_call_with_prefix,
    "reason_then_plan": run_reason_then_plan,
    "reactive_simulation": run_reactive_simulation,
}


def run_experiment(exp: dict) -> ExperimentResult:
    """Execute a single experiment using the appropriate runner."""
    runner = RUN_DISPATCH[exp["run_fn"]]
    return runner(exp)


def _estimate_calls(exp: dict) -> int:
    fn = exp["run_fn"]
    if fn == "reason_then_plan":
        return 2
    if fn == "reactive_simulation":
        return 4  # average estimate
    return 1


def run_all(experiments: list[dict], output_dir: Path) -> list[ExperimentResult]:
    """Run all experiments sequentially, saving results incrementally."""
    results = []
    total = len(experiments)
    total_calls = sum(_estimate_calls(e) for e in experiments)
    print(f"\nRunning {total} experiments (~{total_calls} LLM calls)...\n")

    for i, exp in enumerate(experiments, 1):
        tag = f"[{i:3d}/{total}]"
        print(f"{tag} {exp['id']:<55s}", end="", flush=True)

        result = run_experiment(exp)

        if result.error:
            print(f"  ERROR: {result.error[:60]}")
        else:
            flag = "OK" if result.output_correct else ("~" if result.output_acceptable else "X ")
            print(
                f"  {flag}  "
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
You are evaluating a medical AI model's decision-making on a clinical task.
The model was asked to {task_type}. Evaluate on three dimensions:

**Category:** {category}
**Scenario:** {scenario_desc}

**Expected output:** {expected}
**Acceptable outputs:** {acceptable}

**Model output:** {model_output}
**Model reasoning:** {model_reasoning}

1. **correct**: Is the model's primary decision correct?
   - "correct" = exact match with expected output
   - "acceptable" = not the primary expected answer but a reasonable alternative
   - "wrong" = completely wrong decision

2. **reasoning_score** (0-10): Quality of the model's reasoning field
   - 10 = Clear, clinically sound reasoning that justifies the decision
   - 5 = Somewhat relevant but vague or incomplete
   - 0 = No reasoning or completely off-base

3. **overall_score** (0-10): Combined quality of decision + reasoning

Respond with ONLY a JSON object (no markdown fences):
{{
  "correct": "correct" / "acceptable" / "wrong",
  "reasoning_score": <0-10>,
  "overall_score": <0-10>,
  "rationale": "<1-2 sentence explanation>"
}}
"""

_TASK_TYPE_MAP = {
    "result_assessment": "assess the quality of a tool result",
    "routing": "decide the next action after receiving a tool result",
    "planning": "decompose a multi-step clinical task into subtasks",
    "comparison_fullplan": "decompose a multi-step clinical task into subtasks",
    "reactive": "pick the next step in a multi-step task",
    "comparison_reactive": "iteratively pick next steps in a multi-step task",
    "sufficiency": "assess whether accumulated results are sufficient to answer",
    "recovery": "choose a recovery strategy after a tool error",
    "thinking_routing": "decide the next action after receiving a tool result",
    "thinking_sufficiency": "assess whether accumulated results are sufficient",
}

_gemini_client: httpx.Client | None = None


def _get_gemini_client() -> httpx.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = httpx.Client(timeout=30.0)
    return _gemini_client


def gemini_judge(result: ExperimentResult) -> dict:
    """Ask Gemini to evaluate the model's decision."""
    # Extract reasoning from parsed output
    reasoning = (
        result.parsed_output.get("reasoning")
        or result.parsed_output.get("strategy")
        or result.reasoning_text
        or "(none)"
    )
    prompt = JUDGE_PROMPT.format(
        task_type=_TASK_TYPE_MAP.get(result.scenario_type, "make a clinical decision"),
        category=result.category,
        scenario_desc=result.description,
        expected=json.dumps(result.expected_output),
        acceptable=json.dumps(result.acceptable_outputs),
        model_output=json.dumps(result.parsed_output),
        model_reasoning=reasoning[:500],
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
    """Run Gemini judge on every result that has parsed output."""
    if not GEMINI_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set. Cannot run Gemini judge.")
        sys.exit(1)

    judgeable = [r for r in results if r.parsed_output and not r.error]
    total = len(judgeable)
    print(f"\nRunning Gemini judge on {total} results...\n")

    for i, r in enumerate(judgeable, 1):
        print(f"[{i:3d}/{total}] {r.experiment_id:<55s}", end="", flush=True)
        try:
            verdict = gemini_judge(r)
            r.judge_correct = verdict.get("correct", "wrong")
            r.judge_reasoning_score = verdict.get("reasoning_score", 0)
            r.judge_overall_score = verdict.get("overall_score", 0)
            r.judge_rationale = verdict.get("rationale", "")
            print(
                f"  {r.judge_correct:<10s}  "
                f"reason={r.judge_reasoning_score:2d}  "
                f"overall={r.judge_overall_score:2d}"
            )
        except Exception as e:
            r.judge_correct = None
            r.judge_reasoning_score = None
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
                scenario_id=d["scenario_id"],
                scenario_type=d["scenario_type"],
                strategy=d["strategy"],
                params=d["params"],
                expected_output=d.get("expected_output", {}),
                acceptable_outputs=d.get("acceptable_outputs", []),
                raw_response=d.get("raw_response", ""),
                parsed_output=d.get("parsed_output", {}),
                output_correct=d.get("output_correct", False),
                output_acceptable=d.get("output_acceptable", False),
                num_llm_calls=d.get("num_llm_calls", 1),
                per_call_latency_ms=d.get("per_call_latency_ms", []),
                total_latency_ms=d.get("total_latency_ms", 0),
                error=d.get("error"),
                has_thinking_tokens=d.get("has_thinking_tokens", False),
                thinking_prefix_used=d.get("thinking_prefix_used", False),
                reasoning_text=d.get("reasoning_text", ""),
                judge_correct=d.get("judge_correct"),
                judge_reasoning_score=d.get("judge_reasoning_score"),
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
    """Generate comprehensive Markdown report with 13 sections."""
    lines: list[str] = []
    w = lines.append

    ok = [r for r in results if not r.error]
    err = [r for r in results if r.error]

    w("# MedGemma 4B — Result Evaluation, Planning & Routing Experiments")
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
    correct = sum(1 for r in ok if r.output_correct)
    acceptable = sum(1 for r in ok if r.output_acceptable)
    avg_latency = sum(r.total_latency_ms for r in ok) / max(len(ok), 1)
    total_calls = sum(r.num_llm_calls for r in ok)

    w(f"- **Exact correct:** {correct}/{len(ok)} ({_pct(correct, len(ok))})")
    w(f"- **Acceptable:** {acceptable}/{len(ok)} ({_pct(acceptable, len(ok))})")
    w(f"- **Total LLM calls:** {total_calls}")
    w(f"- **Avg latency per experiment:** {avg_latency:.0f}ms")

    thinking_count = sum(1 for r in ok if r.has_thinking_tokens)
    w(f"- **Thinking tokens observed:** {thinking_count}/{len(ok)} ({_pct(thinking_count, len(ok))})")
    w("")

    # ── 2. Strategy Comparison Table ───────────────────────────────
    w("## 2. Strategy Comparison Table")
    w("")
    w("| Category | Strategy | N | Exact | Acceptable | Avg Latency (ms) | Calls |")
    w("|----------|----------|---|-------|------------|-------------------|-------|")

    categories = sorted(set(r.category for r in results))
    for cat in categories:
        cat_results = [r for r in ok if r.category == cat]
        strategies = sorted(set(r.strategy for r in cat_results))
        cat_label = cat.split("_", 1)[1].replace("_", " ").title()
        for strat in strategies:
            s_results = [r for r in cat_results if r.strategy == strat]
            n = len(s_results)
            exact = sum(1 for r in s_results if r.output_correct)
            accept = sum(1 for r in s_results if r.output_acceptable)
            avg_lat = sum(r.total_latency_ms for r in s_results) / max(n, 1)
            total_c = sum(r.num_llm_calls for r in s_results)
            w(f"| {cat_label} | {strat} | {n} | {exact}/{n} ({_pct(exact, n)}) | {accept}/{n} ({_pct(accept, n)}) | {avg_lat:.0f} | {total_c} |")
    w("")

    # ── 3. Result Quality Assessment (Cat 1) ──────────────────────
    w("## 3. Result Quality Assessment Analysis (Cat 1)")
    w("")
    cat1 = [r for r in ok if r.category == "1_result_quality"]
    if cat1:
        cat1_correct = sum(1 for r in cat1 if r.output_correct)
        w(f"**Accuracy:** {cat1_correct}/{len(cat1)} ({_pct(cat1_correct, len(cat1))})")
        w("")

        # Confusion matrix
        quality_labels = ["success_rich", "success_partial", "no_results", "error_retryable", "error_fatal"]
        confusion: dict[str, dict[str, int]] = {ql: defaultdict(int) for ql in quality_labels}
        for r in cat1:
            expected = r.expected_output.get("quality", "?")
            predicted = r.parsed_output.get("quality", "?")
            if expected in confusion:
                confusion[expected][predicted] += 1

        w("**Confusion Matrix (rows=expected, cols=predicted):**")
        w("")
        header = "| Expected \\ Predicted | " + " | ".join(ql[:12] for ql in quality_labels) + " |"
        w(header)
        w("|" + "---|" * (len(quality_labels) + 1))
        for ql in quality_labels:
            row = f"| {ql[:20]} |"
            for pl in quality_labels:
                count = confusion[ql].get(pl, 0)
                cell = f" **{count}** " if ql == pl and count > 0 else f" {count} " if count > 0 else " . "
                row += cell + "|"
            w(row)
        w("")

        # Per-scenario detail
        w("| Scenario | Tool | Expected | Predicted | Correct? |")
        w("|----------|------|----------|-----------|----------|")
        for r in cat1:
            flag = "OK" if r.output_correct else "WRONG"
            w(f"| {r.scenario_id} | {MOCK_RESULTS.get(r.scenario_id, {}).get('tool', '?')} | {r.expected_output.get('quality', '?')} | {r.parsed_output.get('quality', '?')} | {flag} |")
        w("")
    else:
        w("No Cat 1 experiments completed.")
        w("")

    # ── 4. Next-Action Routing (Cat 2) ────────────────────────────
    w("## 4. Next-Action Routing Analysis (Cat 2)")
    w("")
    cat2 = [r for r in ok if r.category == "2_next_action_routing"]
    if cat2:
        for temp_label in ["routing_T0.0", "routing_T0.3"]:
            temp_results = [r for r in cat2 if r.strategy == temp_label]
            if not temp_results:
                continue
            exact = sum(1 for r in temp_results if r.output_correct)
            accept = sum(1 for r in temp_results if r.output_acceptable)
            w(f"**{temp_label}:** exact={exact}/{len(temp_results)} ({_pct(exact, len(temp_results))}), "
              f"acceptable={accept}/{len(temp_results)} ({_pct(accept, len(temp_results))})")

        w("")

        # Action confusion matrix
        actions = ["synthesize", "retry_same", "retry_different_args", "call_another_tool", "ask_user"]
        action_confusion: dict[str, dict[str, int]] = {a: defaultdict(int) for a in actions}
        for r in cat2:
            expected = r.expected_output.get("action", "?")
            predicted = r.parsed_output.get("action", "?")
            if expected in action_confusion:
                action_confusion[expected][predicted] += 1

        w("**Action Confusion Matrix (all temps combined):**")
        w("")
        header = "| Expected \\ Predicted | " + " | ".join(a[:12] for a in actions) + " |"
        w(header)
        w("|" + "---|" * (len(actions) + 1))
        for ea in actions:
            row = f"| {ea[:20]} |"
            for pa in actions:
                count = action_confusion[ea].get(pa, 0)
                cell = f" **{count}** " if ea == pa and count > 0 else f" {count} " if count > 0 else " . "
                row += cell + "|"
            w(row)
        w("")
    else:
        w("No Cat 2 experiments completed.")
        w("")

    # ── 5. Full-Plan Decomposition (Cat 3) ────────────────────────
    w("## 5. Full-Plan Decomposition Analysis (Cat 3)")
    w("")
    cat3 = [r for r in ok if r.category == "3_full_plan"]
    if cat3:
        for strat in ["no_prefix", "thinking_prefix", "reason_first"]:
            s_results = [r for r in cat3 if r.strategy == strat]
            if not s_results:
                continue
            exact = sum(1 for r in s_results if r.output_correct)
            accept = sum(1 for r in s_results if r.output_acceptable)
            w(f"**{strat}:** sequence exact={exact}/{len(s_results)} ({_pct(exact, len(s_results))}), "
              f"tools correct (any order)={accept}/{len(s_results)} ({_pct(accept, len(s_results))})")
        w("")

        # Per-task comparison
        w("| Task | no_prefix | thinking | reason_first | Expected |")
        w("|------|-----------|----------|--------------|----------|")
        for tid in TASKS:
            row = f"| {tid} |"
            for strat in ["no_prefix", "thinking_prefix", "reason_first"]:
                r = next((r for r in cat3 if r.scenario_id == tid and r.strategy == strat), None)
                if r:
                    tools = _extract_plan_tools(r.parsed_output)
                    flag = "OK" if r.output_correct else "~" if r.output_acceptable else "X"
                    row += f" {flag} {','.join(t[:5] for t in tools)} |"
                else:
                    row += " - |"
            expected_tools = ",".join(t[:5] for t in TASKS[tid].expected_tools)
            row += f" {expected_tools} |"
            w(row)
        w("")
    else:
        w("No Cat 3 experiments completed.")
        w("")

    # ── 6. Reactive Planning (Cat 4) ──────────────────────────────
    w("## 6. Reactive Planning Analysis (Cat 4)")
    w("")
    cat4 = [r for r in ok if r.category == "4_reactive_planning"]
    if cat4:
        for snap_strat in ["snapshot_0", "snapshot_1", "snapshot_2"]:
            s_results = [r for r in cat4 if r.strategy == snap_strat]
            if not s_results:
                continue
            exact = sum(1 for r in s_results if r.output_correct)
            w(f"**{snap_strat}:** correct next tool={exact}/{len(s_results)} ({_pct(exact, len(s_results))})")
        w("")

        w("| Task | Snap 0 | Snap 1 | Snap 2 |")
        w("|------|--------|--------|--------|")
        for tid in TASKS:
            row = f"| {tid} |"
            for si in range(3):
                r = next((r for r in cat4 if r.scenario_id == f"{tid}-snap{si}"), None)
                if r:
                    tool = r.parsed_output.get("tool", "?")
                    flag = "OK" if r.output_correct else "X"
                    row += f" {flag} ({tool[:8]}) |"
                else:
                    row += " - |"
            w(row)
        w("")
    else:
        w("No Cat 4 experiments completed.")
        w("")

    # ── 7. Full-Plan vs Reactive Head-to-Head (Cat 7) ─────────────
    w("## 7. Full-Plan vs Reactive Head-to-Head (Cat 7)")
    w("")
    cat7 = [r for r in ok if r.category == "7_plan_vs_reactive"]
    if cat7:
        for strat in ["full_plan", "reactive_sim"]:
            s_results = [r for r in cat7 if r.strategy == strat]
            exact = sum(1 for r in s_results if r.output_correct)
            accept = sum(1 for r in s_results if r.output_acceptable)
            avg_calls = sum(r.num_llm_calls for r in s_results) / max(len(s_results), 1)
            avg_lat = sum(r.total_latency_ms for r in s_results) / max(len(s_results), 1)
            w(f"**{strat}:** exact={exact}/{len(s_results)} ({_pct(exact, len(s_results))}), "
              f"acceptable={accept}/{len(s_results)} ({_pct(accept, len(s_results))}), "
              f"avg calls={avg_calls:.1f}, avg latency={avg_lat:.0f}ms")
        w("")

        w("| Task | Full-Plan | Reactive | Expected |")
        w("|------|-----------|----------|----------|")
        for tid in TASKS:
            row = f"| {tid} |"
            for strat in ["full_plan", "reactive_sim"]:
                r = next((r for r in cat7 if r.scenario_id == tid and r.strategy == strat), None)
                if r:
                    if strat == "full_plan":
                        tools = _extract_plan_tools(r.parsed_output)
                    else:
                        tools = r.parsed_output.get("reactive_tools", [])
                    flag = "OK" if r.output_correct else "~" if r.output_acceptable else "X"
                    row += f" {flag} {','.join(t[:5] for t in tools)} |"
                else:
                    row += " - |"
            expected_tools = ",".join(t[:5] for t in TASKS[tid].expected_tools)
            row += f" {expected_tools} |"
            w(row)
        w("")
    else:
        w("No Cat 7 experiments completed.")
        w("")

    # ── 8. Sufficiency Assessment (Cat 5) ─────────────────────────
    w("## 8. Sufficiency Assessment Analysis (Cat 5)")
    w("")
    cat5 = [r for r in ok if r.category == "5_sufficiency"]
    if cat5:
        for strat in ["no_think", "think"]:
            s_results = [r for r in cat5 if r.strategy == strat]
            exact = sum(1 for r in s_results if r.output_correct)
            w(f"**{strat}:** correct={exact}/{len(s_results)} ({_pct(exact, len(s_results))})")
        w("")

        w("| Scenario | Expected | no_think | think |")
        w("|----------|----------|----------|-------|")
        for sid in SUFFICIENCY_SCENARIOS:
            ssc = SUFFICIENCY_SCENARIOS[sid]
            row = f"| {sid} | {'sufficient' if ssc.expected_sufficient else 'insufficient'} |"
            for strat in ["no_think", "think"]:
                r = next((r for r in cat5 if r.scenario_id == sid and r.strategy == strat), None)
                if r:
                    predicted = "suf" if r.parsed_output.get("sufficient") else "insuf"
                    flag = "OK" if r.output_correct else "X"
                    row += f" {flag} ({predicted}) |"
                else:
                    row += " - |"
            w(row)
        w("")
    else:
        w("No Cat 5 experiments completed.")
        w("")

    # ── 9. Error Recovery (Cat 6) ─────────────────────────────────
    w("## 9. Error Recovery Analysis (Cat 6)")
    w("")
    cat6 = [r for r in ok if r.category == "6_error_recovery"]
    if cat6:
        for strat in ["no_think", "think"]:
            s_results = [r for r in cat6 if r.strategy == strat]
            exact = sum(1 for r in s_results if r.output_correct)
            accept = sum(1 for r in s_results if r.output_acceptable)
            w(f"**{strat}:** exact={exact}/{len(s_results)} ({_pct(exact, len(s_results))}), "
              f"acceptable={accept}/{len(s_results)} ({_pct(accept, len(s_results))})")
        w("")

        # Strategy confusion
        strategies = ["retry_same", "retry_different_args", "skip_and_continue", "ask_user"]
        strat_confusion: dict[str, dict[str, int]] = {s: defaultdict(int) for s in strategies}
        for r in cat6:
            expected = r.expected_output.get("strategy", "?")
            predicted = r.parsed_output.get("strategy", "?")
            if expected in strat_confusion:
                strat_confusion[expected][predicted] += 1

        w("**Strategy Confusion Matrix:**")
        w("")
        header = "| Expected \\ Predicted | " + " | ".join(s[:12] for s in strategies) + " |"
        w(header)
        w("|" + "---|" * (len(strategies) + 1))
        for es in strategies:
            row = f"| {es[:20]} |"
            for ps in strategies:
                count = strat_confusion[es].get(ps, 0)
                cell = f" **{count}** " if es == ps and count > 0 else f" {count} " if count > 0 else " . "
                row += cell + "|"
            w(row)
        w("")
    else:
        w("No Cat 6 experiments completed.")
        w("")

    # ── 10. Thinking Mode Effect (Cat 8) ──────────────────────────
    w("## 10. Thinking Mode Effect (Cat 8 + Cross-Category)")
    w("")
    cat8 = [r for r in ok if r.category == "8_thinking_effect"]
    if cat8:
        for strat in ["no_think", "think"]:
            s_results = [r for r in cat8 if r.strategy == strat]
            exact = sum(1 for r in s_results if r.output_correct)
            accept = sum(1 for r in s_results if r.output_acceptable)
            w(f"**{strat}:** exact={exact}/{len(s_results)} ({_pct(exact, len(s_results))}), "
              f"acceptable={accept}/{len(s_results)} ({_pct(accept, len(s_results))})")
        w("")

        # Cross-category thinking effect (Cat 5 + Cat 6)
        w("**Cross-category thinking comparison (Cat 5 + Cat 6 + Cat 8):**")
        w("")
        for cat_name, cat_id in [("Sufficiency", "5_sufficiency"), ("Error Recovery", "6_error_recovery"), ("Hard Scenarios", "8_thinking_effect")]:
            cat_r = [r for r in ok if r.category == cat_id]
            no_think = [r for r in cat_r if r.strategy == "no_think"]
            think = [r for r in cat_r if r.strategy == "think"]
            nt_correct = sum(1 for r in no_think if r.output_correct)
            t_correct = sum(1 for r in think if r.output_correct)
            w(f"- **{cat_name}:** no_think={nt_correct}/{len(no_think)} → think={t_correct}/{len(think)}")
        w("")
    else:
        w("No Cat 8 experiments completed.")
        w("")

    # ── 11. Latency Analysis ──────────────────────────────────────
    w("## 11. Latency Analysis")
    w("")
    w("| Category | Strategy | Avg Total (ms) | Avg Per-Call (ms) | Calls/Exp |")
    w("|----------|----------|---------------|-------------------|-----------|")
    for cat in categories:
        cat_ok = [r for r in ok if r.category == cat]
        strats = sorted(set(r.strategy for r in cat_ok))
        for strat in strats:
            sr = [r for r in cat_ok if r.strategy == strat]
            avg_total = sum(r.total_latency_ms for r in sr) / max(len(sr), 1)
            all_per_call = [c for r in sr for c in r.per_call_latency_ms]
            avg_per_call = sum(all_per_call) / max(len(all_per_call), 1) if all_per_call else 0
            avg_calls = sum(r.num_llm_calls for r in sr) / max(len(sr), 1)
            cat_label = cat.split("_", 1)[1].replace("_", " ")[:15]
            w(f"| {cat_label} | {strat} | {avg_total:.0f} | {avg_per_call:.0f} | {avg_calls:.1f} |")
    w("")

    # ── 12. Gemini vs Deterministic Eval Agreement ────────────────
    w("## 12. Gemini vs Deterministic Eval Agreement")
    w("")
    judged = [r for r in ok if r.judge_correct is not None]
    if judged:
        agree = sum(
            1 for r in judged
            if (r.output_correct and r.judge_correct == "correct") or
               (not r.output_correct and r.judge_correct != "correct")
        )
        w(f"- **Agreement:** {agree}/{len(judged)} ({_pct(agree, len(judged))})")

        avg_reason = sum(r.judge_reasoning_score or 0 for r in judged) / len(judged)
        avg_overall = sum(r.judge_overall_score or 0 for r in judged) / len(judged)
        w(f"- **Avg Gemini reasoning score:** {avg_reason:.1f}/10")
        w(f"- **Avg Gemini overall score:** {avg_overall:.1f}/10")
        w("")

        w("| Gemini Verdict | Count | Det. Exact Match |")
        w("|---------------:|------:|-----------------:|")
        for verdict in ["correct", "acceptable", "wrong"]:
            v_results = [r for r in judged if r.judge_correct == verdict]
            det_exact = sum(1 for r in v_results if r.output_correct)
            w(f"| {verdict} | {len(v_results)} | {det_exact} |")
        w("")
    else:
        w("No Gemini judgments available. Run with `--judge` to populate.")
        w("")

    # ── 13. Recommendations ───────────────────────────────────────
    w("## 13. Recommendations")
    w("")

    # Auto-generate summary stats per category
    for cat in categories:
        cat_ok = [r for r in ok if r.category == cat]
        if not cat_ok:
            continue
        cat_label = cat.split("_", 1)[1].replace("_", " ").title()
        best_strat = None
        best_rate = -1
        for strat in set(r.strategy for r in cat_ok):
            sr = [r for r in cat_ok if r.strategy == strat]
            rate = sum(1 for r in sr if r.output_correct) / max(len(sr), 1)
            if rate > best_rate:
                best_rate = rate
                best_strat = strat
        if best_strat:
            w(f"- **{cat_label}:** Best strategy = `{best_strat}` ({best_rate:.0%} exact)")

    w("")
    w("_Fill in detailed recommendations after reviewing results._")
    w("")

    # ── Errors ────────────────────────────────────────────────────
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
        description="MedGemma 4B result evaluation, planning & routing experiments"
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
        judged = [r for r in results if r.judge_correct is not None and not r.error]
        correct = sum(1 for r in judged if r.judge_correct == "correct")
        print(f"\nGemini judged {correct}/{len(judged)} as correct.")
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
    output_dir = Path("result_routing_experiments") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    experiments = build_experiments()

    # Save experiment manifest
    manifest = []
    for exp in experiments:
        manifest.append({
            "id": exp["id"],
            "category": exp["category"],
            "description": exp["description"],
            "scenario_id": exp["scenario_id"],
            "scenario_type": exp["scenario_type"],
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
    correct = sum(1 for r in ok_results if r.output_correct)
    acceptable = sum(1 for r in ok_results if r.output_acceptable)
    print(f"\n{'=' * 60}")
    print(f"Done. Exact: {correct}/{len(ok_results)}, acceptable: {acceptable}/{len(ok_results)}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
