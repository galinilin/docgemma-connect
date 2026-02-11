"""
Response synthesis experiments for MedGemma 4B IT.

Probes the final stage of the agent graph: generating a free-form clinical
response from tool results, optional reasoning, and the user's query.

Key differences from prior experiments:
- No Outlines constrained generation — the model produces free text
- Gemini is the PRIMARY evaluator (not secondary)
- Deterministic checks are heuristic: key-fact presence, forbidden-term absence

Questions answered:
1. Key fact inclusion from tool results
2. Response conciseness
3. Clinical tone and source hiding
4. Thinking prefix effect on synthesis quality
5. Optimal synthesis temperature
6. Best prompt formulation
7. Reasoning context effect
8. Error/empty result handling

Usage:
    cd docgemma-connect
    uv run python synthesis_experiments.py
    uv run python synthesis_experiments.py --report-only synthesis_experiments/<ts>
    uv run python synthesis_experiments.py --judge synthesis_experiments/<ts>
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
from typing import Any

import httpx

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
    temperature: float = 0.5,
) -> dict:
    """Raw OpenAI-compatible chat completion. Returns the full response JSON."""
    payload: dict = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = get_client().post(COMPLETIONS_URL, json=payload)
    resp.raise_for_status()
    return resp.json()


# ── System prompt (production) ──────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are DocGemma, a clinical decision-support assistant for healthcare professionals. "
    "Be concise and use standard medical terminology. "
    "For greetings or casual messages, respond naturally and briefly. "
    "Never fabricate clinical data. State uncertainty when unsure."
)

# ── Production prompts ──────────────────────────────────────────────────

PROD_SYNTHESIS_PROMPT = """\
Clinical decision support response.

Query: {user_input}
{reasoning_line}
{tool_results_line}

Respond concisely. Use medical abbreviations. Present findings directly as clinical knowledge.
Do NOT mention tool names, sources, references, internal processes, or how findings were obtained."""

DIRECT_CHAT_PROMPT = """\
Respond to the user. Keep it natural and concise.

Query: {user_input}"""

# ── Alternative prompt variants (Cat 4) ─────────────────────────────────

STRUCTURED_PROMPT = """\
Clinical summary.

Query: {user_input}
{reasoning_line}
{tool_results_line}

Structure your response as:
1. Key Findings
2. Clinical Significance
3. Recommendations (if applicable)

Be concise. Use medical abbreviations."""

BRIEF_PROMPT = """\
One-paragraph clinical summary.

Query: {user_input}
{reasoning_line}
{tool_results_line}

Respond in 2-3 sentences maximum. Include only the most critical findings."""

COMPREHENSIVE_PROMPT = """\
Detailed clinical decision support.

Query: {user_input}
{reasoning_line}
{tool_results_line}

Provide a thorough clinical response. Include relevant findings, clinical significance, and actionable recommendations. Use medical terminology."""

# ── Forbidden terms (source leakage) ───────────────────────────────────

FORBIDDEN_TERMS = [
    "check_drug_safety", "search_medical_literature", "check_drug_interactions",
    "find_clinical_trials", "search_patient", "get_patient_chart",
    "add_allergy", "prescribe_medication", "save_clinical_note",
    "analyze_medical_image", "PubMed", "OpenFDA", "RxNav",
    "ClinicalTrials.gov", "tool", "API call", "database query",
    "according to the search", "the search returned", "the tool",
]

# ── Mock tool results (reused from result_routing_experiments) ──────────

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
    },

    # === Partial/ambiguous results (P-01 to P-04) ===
    "P-01": {
        "id": "P-01",
        "tool": "check_drug_safety",
        "label": "No boxed warning for metformin (CKD question unanswered)",
        "result": {
            "brand_name": "metformin",
            "has_warning": False,
            "boxed_warning": None,
            "error": None,
        },
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
    },
    "E-03": {
        "id": "E-03",
        "tool": "search_patient",
        "label": "No match for Xyz Nonexist",
        "result": {
            "patients": [],
        },
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
    },
    "X-02": {
        "id": "X-02",
        "tool": "get_patient_chart",
        "label": "Invalid patient ID",
        "result": {
            "error": "patient_id is required",
        },
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
    },
}

# ── Multi-tool accumulated results (M-01 to M-03) ──────────────────────

MULTI_RESULTS: dict[str, dict] = {
    "M-01": {
        "id": "M-01",
        "label": "search_patient + get_chart done",
        "steps": [
            {"tool": "search_patient", "success": True, "result": {"patients": [{"patient_id": "abc-123", "name": "John Smith", "date_of_birth": "1970-05-20"}]}},
            {"tool": "get_patient_chart", "success": True, "result": {"patient_id": "abc-123", "name": "John Smith", "conditions": ["Hypertension", "Type 2 Diabetes"], "medications": ["Metformin 500mg BID", "Lisinopril 10mg daily"], "allergies": [], "recent_labs": {"HbA1c": "7.8%"}, "recent_notes": []}},
        ],
    },
    "M-02": {
        "id": "M-02",
        "label": "search + chart + interactions done",
        "steps": [
            {"tool": "search_patient", "success": True, "result": {"patients": [{"patient_id": "abc-123", "name": "John Smith", "date_of_birth": "1970-05-20"}]}},
            {"tool": "get_patient_chart", "success": True, "result": {"patient_id": "abc-123", "name": "John Smith", "conditions": ["Atrial Fibrillation", "DVT"], "medications": ["Warfarin 5mg daily", "Metoprolol 25mg BID"], "allergies": ["Aspirin (GI bleeding)"], "recent_labs": {"INR": "2.5"}, "recent_notes": []}},
            {"tool": "check_drug_interactions", "success": True, "result": {"drugs_checked": ["warfarin", "metoprolol"], "resolved_rxcuis": {"warfarin": "11289", "metoprolol": "6918"}, "interactions": [{"drug_pair": ["warfarin", "metoprolol"], "severity": "moderate", "description": "Metoprolol may increase warfarin levels. Monitor INR."}], "error": None}},
        ],
    },
    "M-03": {
        "id": "M-03",
        "label": "search_patient done, chart not yet retrieved",
        "steps": [
            {"tool": "search_patient", "success": True, "result": {"patients": [{"patient_id": "pat-456", "name": "Maria Garcia", "date_of_birth": "1965-03-15"}]}},
        ],
    },
}


# ── Format tool results (replicates production _format_tool_results) ────

def format_tool_results_single(tool_name: str, result: dict) -> str:
    """Format a single tool result in the production format."""
    has_error = result.get("error")
    status = "FAILED" if has_error else "SUCCESS"
    lines = [f"[{tool_name}] ({status})"]
    if has_error:
        lines.append(f"  Error: {has_error}")
    else:
        result_str = str(result)
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."
        lines.append(f"  {result_str}")
    return "\n".join(lines)


def format_tool_results_multi(steps: list[dict]) -> str:
    """Format multi-step accumulated tool results."""
    lines = []
    for step in steps:
        status = "SUCCESS" if step["success"] else "FAILED"
        lines.append(f"[{step['tool']}] ({status})")
        result_str = str(step["result"])
        if len(result_str) > 500:
            result_str = result_str[:500] + "..."
        lines.append(f"  {result_str}")
    return "\n".join(lines)


# ── Synthesis scenarios (30 total) ──────────────────────────────────────

@dataclass
class SynthesisScenario:
    """A scenario for synthesis testing."""
    id: str
    query: str
    route: str              # "lookup", "direct", "reasoning", "multi_step"
    scenario_type: str      # "success_rich", "partial", "empty", "error", "multi_tool", "direct", "reasoning_tool"
    tool_results_text: str  # Pre-formatted tool results string
    reasoning: str          # Reasoning text (may be empty)
    key_facts: list[str]    # Expected key facts (case-insensitive substring match)
    notes: str


def _make_tool_results_text(mock_id: str) -> str:
    """Build formatted tool results from a mock result ID."""
    mock = MOCK_RESULTS[mock_id]
    return format_tool_results_single(mock["tool"], mock["result"])


SCENARIOS: dict[str, SynthesisScenario] = {
    # === Success-Rich (SC-01 to SC-06) ===
    "SC-01": SynthesisScenario(
        id="SC-01",
        query="Check FDA safety warnings for dofetilide",
        route="lookup",
        scenario_type="success_rich",
        tool_results_text=_make_tool_results_text("S-01"),
        reasoning="",
        key_facts=["dofetilide", "Torsade de Pointes|QT", "arrhythmia", "ECG monitoring|ECG"],
        notes="Boxed warning with multiple key findings",
    ),
    "SC-02": SynthesisScenario(
        id="SC-02",
        query="Search for studies on SGLT2 inhibitors and cardiovascular outcomes",
        route="lookup",
        scenario_type="success_rich",
        tool_results_text=_make_tool_results_text("S-02"),
        reasoning="",
        key_facts=["SGLT2", "heart failure|cardiovascular", "empagliflozin|dapagliflozin"],
        notes="3 articles with abstracts",
    ),
    "SC-03": SynthesisScenario(
        id="SC-03",
        query="Check drug interactions between warfarin and aspirin",
        route="lookup",
        scenario_type="success_rich",
        tool_results_text=_make_tool_results_text("S-03"),
        reasoning="",
        key_facts=["warfarin", "aspirin", "bleeding", "INR"],
        notes="High-severity drug interaction",
    ),
    "SC-04": SynthesisScenario(
        id="SC-04",
        query="Find clinical trials for triple-negative breast cancer",
        route="lookup",
        scenario_type="success_rich",
        tool_results_text=_make_tool_results_text("S-04"),
        reasoning="",
        key_facts=["triple-negative|TNBC", "recruiting|Recruiting", "pembrolizumab|NCT"],
        notes="2 recruiting trials",
    ),
    "SC-05": SynthesisScenario(
        id="SC-05",
        query="Search for patient Maria Garcia",
        route="lookup",
        scenario_type="success_rich",
        tool_results_text=_make_tool_results_text("S-05"),
        reasoning="",
        key_facts=["Maria Garcia", "abc-123"],
        notes="Single patient match",
    ),
    "SC-06": SynthesisScenario(
        id="SC-06",
        query="Get the chart for patient abc-123",
        route="lookup",
        scenario_type="success_rich",
        tool_results_text=_make_tool_results_text("S-06"),
        reasoning="",
        key_facts=["diabetes|T2DM|Diabetes", "metformin|Metformin", "lisinopril|Lisinopril", "HbA1c|7.2"],
        notes="Full patient chart with conditions, meds, labs",
    ),

    # === Partial/Ambiguous (SC-07 to SC-10) ===
    "SC-07": SynthesisScenario(
        id="SC-07",
        query="Is metformin safe for patients with CKD?",
        route="lookup",
        scenario_type="partial",
        tool_results_text=_make_tool_results_text("P-01"),
        reasoning="",
        key_facts=["metformin", "no.*warning|no.*boxed|no FDA"],
        notes="No boxed warning but CKD question partially unanswered",
    ),
    "SC-08": SynthesisScenario(
        id="SC-08",
        query="Find patient James Wilson",
        route="lookup",
        scenario_type="partial",
        tool_results_text=_make_tool_results_text("P-02"),
        reasoning="",
        key_facts=["James Wilson", "pat-001|pat-002|pat-003", "3|three|multiple"],
        notes="3 patient matches — should present all and ask to clarify",
    ),
    "SC-09": SynthesisScenario(
        id="SC-09",
        query="Check interactions between warfarin and supplement X",
        route="lookup",
        scenario_type="partial",
        tool_results_text=_make_tool_results_text("P-03"),
        reasoning="",
        key_facts=["warfarin", "supplement X|not found|unresolved|not recognized"],
        notes="One drug unresolved",
    ),
    "SC-10": SynthesisScenario(
        id="SC-10",
        query="Search for studies on rare enzyme deficiency treatment",
        route="lookup",
        scenario_type="partial",
        tool_results_text=_make_tool_results_text("P-04"),
        reasoning="",
        key_facts=["enzyme|Enzyme", "Case Report|Novel Enzyme Replacement"],
        notes="1 article with no abstract",
    ),

    # === Empty Results (SC-11 to SC-13) ===
    "SC-11": SynthesisScenario(
        id="SC-11",
        query="Search PubMed for xylotriazole enzyme deficiency in zebrafish",
        route="lookup",
        scenario_type="empty",
        tool_results_text=_make_tool_results_text("E-01"),
        reasoning="",
        key_facts=["no.*result|no.*found|no.*article|0 result"],
        notes="Zero articles",
    ),
    "SC-12": SynthesisScenario(
        id="SC-12",
        query="Find clinical trials for hereditary angioedema type IV",
        route="lookup",
        scenario_type="empty",
        tool_results_text=_make_tool_results_text("E-02"),
        reasoning="",
        key_facts=["no.*trial|no.*found|no.*result|0 trial"],
        notes="Zero trials",
    ),
    "SC-13": SynthesisScenario(
        id="SC-13",
        query="Search for patient Xyz Nonexist",
        route="lookup",
        scenario_type="empty",
        tool_results_text=_make_tool_results_text("E-03"),
        reasoning="",
        key_facts=["no.*patient|not found|no.*match|no.*result"],
        notes="No patient match",
    ),

    # === Error (SC-14 to SC-17) ===
    "SC-14": SynthesisScenario(
        id="SC-14",
        query="Check FDA warnings for amiodarone",
        route="lookup",
        scenario_type="error",
        tool_results_text=_make_tool_results_text("X-01"),
        reasoning="",
        key_facts=["timed out|unavailable|unable|error|retry|could not"],
        notes="API timeout",
    ),
    "SC-15": SynthesisScenario(
        id="SC-15",
        query="Get chart for this patient",
        route="lookup",
        scenario_type="error",
        tool_results_text=_make_tool_results_text("X-02"),
        reasoning="",
        key_facts=["patient.*id|patient.*identifier|specify|which patient|provide"],
        notes="Invalid patient ID — should ask for valid ID",
    ),
    "SC-16": SynthesisScenario(
        id="SC-16",
        query="Check interactions for aspirin",
        route="lookup",
        scenario_type="error",
        tool_results_text=_make_tool_results_text("X-03"),
        reasoning="",
        key_facts=["two|2|another|second|at least.*drug|additional"],
        notes="Need 2+ drugs",
    ),
    "SC-17": SynthesisScenario(
        id="SC-17",
        query="Search for diabetes management articles",
        route="lookup",
        scenario_type="error",
        tool_results_text=_make_tool_results_text("X-04"),
        reasoning="",
        key_facts=["error|unavailable|unable|service|issue|try again"],
        notes="HTTP 500 server error",
    ),

    # === Multi-Tool (SC-18 to SC-20) ===
    "SC-18": SynthesisScenario(
        id="SC-18",
        query="Find patient John Smith and review his chart",
        route="multi_step",
        scenario_type="multi_tool",
        tool_results_text=format_tool_results_multi(MULTI_RESULTS["M-01"]["steps"]),
        reasoning="",
        key_facts=["John Smith", "Hypertension|hypertension", "Diabetes|diabetes", "Metformin|metformin", "HbA1c|7.8"],
        notes="Search + chart complete",
    ),
    "SC-19": SynthesisScenario(
        id="SC-19",
        query="Review patient Smith's chart and check medication interactions",
        route="multi_step",
        scenario_type="multi_tool",
        tool_results_text=format_tool_results_multi(MULTI_RESULTS["M-02"]["steps"]),
        reasoning="",
        key_facts=["Atrial Fibrillation|atrial fibrillation", "Warfarin|warfarin", "Metoprolol|metoprolol", "interaction|Interaction", "INR|2.5"],
        notes="Search + chart + interactions",
    ),
    "SC-20": SynthesisScenario(
        id="SC-20",
        query="Find Maria Garcia and get her complete chart",
        route="multi_step",
        scenario_type="multi_tool",
        tool_results_text=format_tool_results_multi(MULTI_RESULTS["M-03"]["steps"]),
        reasoning="",
        key_facts=["Maria Garcia", "pat-456|found"],
        notes="Partial — chart not yet retrieved",
    ),

    # === Direct Chat (SC-21 to SC-25) ===
    "SC-21": SynthesisScenario(
        id="SC-21",
        query="Hello, how are you?",
        route="direct",
        scenario_type="direct",
        tool_results_text="",
        reasoning="",
        key_facts=["hello|hi|hey|welcome|assist|help"],
        notes="Friendly greeting",
    ),
    "SC-22": SynthesisScenario(
        id="SC-22",
        query="What is hypertension?",
        route="direct",
        scenario_type="direct",
        tool_results_text="",
        reasoning="",
        key_facts=["blood pressure|BP", "140|systolic|diastolic|mmHg|elevated"],
        notes="Medical knowledge question",
    ),
    "SC-23": SynthesisScenario(
        id="SC-23",
        query="Thanks for the help!",
        route="direct",
        scenario_type="direct",
        tool_results_text="",
        reasoning="",
        key_facts=["welcome|glad|happy|anytime|help"],
        notes="Acknowledgment",
    ),
    "SC-24": SynthesisScenario(
        id="SC-24",
        query="What are ACE inhibitors used for?",
        route="direct",
        scenario_type="direct",
        tool_results_text="",
        reasoning="",
        key_facts=["hypertension|blood pressure|heart failure", "angiotensin|ACE"],
        notes="Clinical knowledge",
    ),
    "SC-25": SynthesisScenario(
        id="SC-25",
        query="Explain the mechanism of action of metformin",
        route="direct",
        scenario_type="direct",
        tool_results_text="",
        reasoning="",
        key_facts=["hepatic|liver|glucose", "insulin|sensitivity|resistance"],
        notes="Detailed mechanism question",
    ),

    # === Reasoning + Tool (SC-26 to SC-30) ===
    "SC-26": SynthesisScenario(
        id="SC-26",
        query="Best antihypertensive for CKD stage 3?",
        route="reasoning",
        scenario_type="reasoning_tool",
        tool_results_text=_make_tool_results_text("S-01"),
        reasoning="ACE inhibitors are first-line per KDIGO guidelines for CKD with proteinuria. ARBs are alternatives. Let me check safety data for the recommended agents.",
        key_facts=["ACE inhibitor|ACEI|angiotensin", "CKD|kidney", "proteinuria|renal"],
        notes="Reasoning + drug safety check",
    ),
    "SC-27": SynthesisScenario(
        id="SC-27",
        query="Patient on warfarin needs dental procedure, what to consider?",
        route="reasoning",
        scenario_type="reasoning_tool",
        tool_results_text=_make_tool_results_text("S-03"),
        reasoning="Warfarin requires INR monitoring. Bleeding risk during procedures. Check interactions with commonly used perioperative drugs.",
        key_facts=["warfarin", "bleeding|hemorrhage", "INR", "dental|procedure"],
        notes="Reasoning + drug interaction check",
    ),
    "SC-28": SynthesisScenario(
        id="SC-28",
        query="New T2DM patient, what's the latest on SGLT2 inhibitors?",
        route="reasoning",
        scenario_type="reasoning_tool",
        tool_results_text=_make_tool_results_text("S-02"),
        reasoning="SGLT2 inhibitors have shown cardiovascular and renal benefits beyond glucose lowering.",
        key_facts=["SGLT2", "cardiovascular|heart failure", "renal|kidney|CKD|eGFR"],
        notes="Reasoning + literature search",
    ),
    "SC-29": SynthesisScenario(
        id="SC-29",
        query="Treatment options for triple-negative breast cancer?",
        route="reasoning",
        scenario_type="reasoning_tool",
        tool_results_text=_make_tool_results_text("S-04"),
        reasoning="TNBC has limited targeted therapy options. Immunotherapy combinations showing promise.",
        key_facts=["triple-negative|TNBC", "immunotherapy|pembrolizumab", "clinical trial|recruiting|NCT"],
        notes="Reasoning + clinical trials",
    ),
    "SC-30": SynthesisScenario(
        id="SC-30",
        query="Review Maria Garcia's medications for potential issues",
        route="reasoning",
        scenario_type="reasoning_tool",
        tool_results_text=_make_tool_results_text("S-06"),
        reasoning="Need to check patient chart and cross-reference current medications.",
        key_facts=["Maria Garcia", "Metformin|metformin", "Lisinopril|lisinopril", "diabetes|Diabetes|T2DM"],
        notes="Reasoning + chart review",
    ),
}

# ── Key scenario subset (for Cat 3, 4, 6) ──────────────────────────────

KEY_SCENARIOS = [
    "SC-01", "SC-02", "SC-03", "SC-04", "SC-05", "SC-06",
    "SC-07", "SC-08", "SC-11", "SC-14",
    "SC-18", "SC-19", "SC-21", "SC-22", "SC-26",
]

# ── Scenarios for Cat 5 (reasoning context effect) ──────────────────────

REASONING_SCENARIOS: dict[str, str] = {
    # SC-26 to SC-30 already have reasoning; add fabricated for 5 others
    "SC-01": "Dofetilide is a class III antiarrhythmic. Known to carry serious cardiac risks. Should verify current FDA warnings.",
    "SC-02": "SGLT2 inhibitors are a newer drug class for T2DM. Studies suggest benefits beyond glucose control.",
    "SC-03": "Patient on both warfarin and aspirin. Both affect hemostasis through different mechanisms. Need to quantify interaction risk.",
    "SC-06": "Patient requested chart review. Need to examine current medications, conditions, and recent lab values for any concerns.",
    "SC-18": "Patient lookup requested. Will need to search by name first, then pull the full clinical record.",
}

# ── Scenarios for Cat 6 (max token impact) ──────────────────────────────

TOKEN_SCENARIOS = [
    "SC-01", "SC-02", "SC-03", "SC-06", "SC-07",
    "SC-18", "SC-19", "SC-26", "SC-28", "SC-30",
]


# ── ExperimentResult ────────────────────────────────────────────────────

@dataclass
class ExperimentResult:
    experiment_id: str
    category: str
    description: str
    scenario_id: str
    scenario_type: str
    strategy: str
    params: dict

    # Ground truth
    expected_key_facts: list = field(default_factory=list)
    forbidden_terms: list = field(default_factory=list)

    # Model output
    raw_response: str = ""
    response_word_count: int = 0
    has_thinking_tokens: bool = False
    thinking_prefix_used: bool = False

    # Deterministic eval
    key_facts_found: dict = field(default_factory=dict)
    key_fact_rate: float = 0.0
    forbidden_terms_found: list = field(default_factory=list)
    forbidden_clean: bool = True

    # Latency
    num_llm_calls: int = 1
    per_call_latency_ms: list = field(default_factory=list)
    total_latency_ms: float = 0.0
    error: str | None = None

    # Gemini judge
    judge_completeness: int | None = None
    judge_accuracy: int | None = None
    judge_conciseness: int | None = None
    judge_clinical_tone: int | None = None
    judge_source_hiding: int | None = None
    judge_overall: int | None = None
    judge_rationale: str | None = None


# ── Prompt builder ──────────────────────────────────────────────────────

def build_synthesis_prompt(
    scenario: SynthesisScenario,
    prompt_template: str | None = None,
) -> str:
    """Build the user prompt for synthesis, choosing the right template."""
    # Direct chat scenarios use the direct prompt
    if scenario.route == "direct" and not scenario.tool_results_text and not scenario.reasoning:
        return DIRECT_CHAT_PROMPT.format(user_input=scenario.query)

    template = prompt_template or PROD_SYNTHESIS_PROMPT

    reasoning_line = ""
    if scenario.reasoning:
        reasoning_line = f"Reasoning:\n{scenario.reasoning}"

    tool_results_line = ""
    if scenario.tool_results_text:
        tool_results_line = f"Tool findings:\n{scenario.tool_results_text}"

    return template.format(
        user_input=scenario.query,
        reasoning_line=reasoning_line,
        tool_results_line=tool_results_line,
    )


# ── Run synthesis ───────────────────────────────────────────────────────

def run_synthesis(
    scenario: SynthesisScenario,
    *,
    temperature: float = 0.5,
    max_tokens: int = 512,
    thinking_prefix: str = "",
    prompt_template: str | None = None,
) -> tuple[str, float, bool]:
    """Run a single synthesis LLM call. Returns (response, latency_ms, has_thinking)."""
    prompt = build_synthesis_prompt(scenario, prompt_template=prompt_template)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    # If thinking prefix requested, prepend it as partial assistant turn
    if thinking_prefix:
        messages.append({"role": "assistant", "content": thinking_prefix})

    t0 = time.perf_counter()
    resp = call_model(
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    raw = resp["choices"][0]["message"]["content"]
    has_thinking = bool(THINKING_RE.search(raw))
    clean = THINKING_RE.sub("", raw).strip()

    # If we used a thinking prefix, prepend it to check full response
    # but don't include it in the cleaned output
    return clean, latency_ms, has_thinking


# ── Deterministic evaluation ────────────────────────────────────────────

def _check_fact(response_lower: str, fact_pattern: str) -> bool:
    """Check if a fact (possibly with | alternatives) is present in the response."""
    alternatives = fact_pattern.split("|")
    for alt in alternatives:
        alt = alt.strip()
        # Check if it looks like a regex pattern
        if any(c in alt for c in [".*", "\\", "^", "$", "+"]):
            try:
                if re.search(alt, response_lower, re.IGNORECASE):
                    return True
            except re.error:
                if alt.lower() in response_lower:
                    return True
        else:
            if alt.lower() in response_lower:
                return True
    return False


def evaluate_deterministic(response: str, scenario: SynthesisScenario) -> dict:
    """Run deterministic heuristic checks on the synthesis response."""
    response_lower = response.lower()
    word_count = len(response.split())

    # Key fact check
    facts_found = {}
    for fact in scenario.key_facts:
        facts_found[fact] = _check_fact(response_lower, fact)
    total_facts = len(scenario.key_facts)
    fact_rate = sum(facts_found.values()) / max(total_facts, 1)

    # Forbidden term check
    found_forbidden = []
    for term in FORBIDDEN_TERMS:
        if term.lower() in response_lower:
            found_forbidden.append(term)

    return {
        "key_facts_found": facts_found,
        "key_fact_rate": fact_rate,
        "forbidden_terms_found": found_forbidden,
        "forbidden_clean": len(found_forbidden) == 0,
        "response_word_count": word_count,
    }


# ── Experiment builder ──────────────────────────────────────────────────

THINKING_PREFIX = "Let me synthesize these clinical findings step by step. "


def build_experiments() -> list[dict]:
    """Build ~215 experiment definitions across 6 categories."""
    experiments = []

    # ================================================================
    # CAT 1: Baseline Synthesis Quality (30 exps, 30 calls)
    # ================================================================
    for sid, sc in SCENARIOS.items():
        experiments.append({
            "id": f"cat1_{sid}_baseline",
            "category": "1_baseline",
            "description": f"Baseline synthesis: {sc.query[:50]}",
            "scenario_id": sid,
            "scenario_type": sc.scenario_type,
            "strategy": "production",
            "params": {"temperature": 0.5, "max_tokens": 512},
            "temperature": 0.5,
            "max_tokens": 512,
            "thinking_prefix": "",
            "prompt_template": None,
        })

    # ================================================================
    # CAT 2: Thinking Prefix Effect (30 exps, 30 calls)
    # ================================================================
    for sid, sc in SCENARIOS.items():
        experiments.append({
            "id": f"cat2_{sid}_thinking",
            "category": "2_thinking",
            "description": f"Thinking prefix: {sc.query[:50]}",
            "scenario_id": sid,
            "scenario_type": sc.scenario_type,
            "strategy": "thinking_prefix",
            "params": {"temperature": 0.5, "max_tokens": 512, "thinking_prefix": THINKING_PREFIX},
            "temperature": 0.5,
            "max_tokens": 512,
            "thinking_prefix": THINKING_PREFIX,
            "prompt_template": None,
        })

    # ================================================================
    # CAT 3: Temperature Sweep (60 exps = 15 scenarios × 4 temps)
    # ================================================================
    for temp in [0.1, 0.3, 0.5, 0.7]:
        temp_label = f"T={temp}"
        for sid in KEY_SCENARIOS:
            sc = SCENARIOS[sid]
            experiments.append({
                "id": f"cat3_{sid}_{temp_label}",
                "category": "3_temperature",
                "description": f"Temp {temp}: {sc.query[:50]}",
                "scenario_id": sid,
                "scenario_type": sc.scenario_type,
                "strategy": temp_label,
                "params": {"temperature": temp, "max_tokens": 512},
                "temperature": temp,
                "max_tokens": 512,
                "thinking_prefix": "",
                "prompt_template": None,
            })

    # ================================================================
    # CAT 4: Prompt Variations (45 exps = 15 scenarios × 3 prompts)
    # ================================================================
    prompt_variants = {
        "structured": STRUCTURED_PROMPT,
        "brief": BRIEF_PROMPT,
        "comprehensive": COMPREHENSIVE_PROMPT,
    }
    for variant_name, variant_template in prompt_variants.items():
        for sid in KEY_SCENARIOS:
            sc = SCENARIOS[sid]
            # Skip direct chat scenarios for non-production prompts
            # (they use DIRECT_CHAT_PROMPT regardless)
            if sc.route == "direct" and not sc.tool_results_text:
                # Still include them but with the variant template
                # (build_synthesis_prompt will use DIRECT_CHAT_PROMPT for direct)
                pass
            experiments.append({
                "id": f"cat4_{sid}_{variant_name}",
                "category": "4_prompt_variation",
                "description": f"{variant_name}: {sc.query[:50]}",
                "scenario_id": sid,
                "scenario_type": sc.scenario_type,
                "strategy": variant_name,
                "params": {"temperature": 0.5, "max_tokens": 512, "prompt_variant": variant_name},
                "temperature": 0.5,
                "max_tokens": 512,
                "thinking_prefix": "",
                "prompt_template": variant_template,
            })

    # ================================================================
    # CAT 5: Reasoning Context Effect (20 exps = 10 scenarios × 2)
    # ================================================================
    # Use SC-26 to SC-30 (already have reasoning) + 5 from REASONING_SCENARIOS
    reasoning_test_ids = ["SC-01", "SC-02", "SC-03", "SC-06", "SC-18",
                          "SC-26", "SC-27", "SC-28", "SC-29", "SC-30"]
    for sid in reasoning_test_ids:
        sc = SCENARIOS[sid]
        # With reasoning
        reasoning_text = sc.reasoning if sc.reasoning else REASONING_SCENARIOS.get(sid, "")
        experiments.append({
            "id": f"cat5_{sid}_with_reasoning",
            "category": "5_reasoning_ctx",
            "description": f"With reasoning: {sc.query[:50]}",
            "scenario_id": sid,
            "scenario_type": sc.scenario_type,
            "strategy": "with_reasoning",
            "params": {"temperature": 0.5, "max_tokens": 512, "has_reasoning": True},
            "temperature": 0.5,
            "max_tokens": 512,
            "thinking_prefix": "",
            "prompt_template": None,
            "override_reasoning": reasoning_text,
        })
        # Without reasoning
        experiments.append({
            "id": f"cat5_{sid}_no_reasoning",
            "category": "5_reasoning_ctx",
            "description": f"No reasoning: {sc.query[:50]}",
            "scenario_id": sid,
            "scenario_type": sc.scenario_type,
            "strategy": "no_reasoning",
            "params": {"temperature": 0.5, "max_tokens": 512, "has_reasoning": False},
            "temperature": 0.5,
            "max_tokens": 512,
            "thinking_prefix": "",
            "prompt_template": None,
            "override_reasoning": "",
        })

    # ================================================================
    # CAT 6: Max Token Impact (30 exps = 10 scenarios × 3 limits)
    # ================================================================
    for max_tok in [128, 256, 512]:
        tok_label = f"tok={max_tok}"
        for sid in TOKEN_SCENARIOS:
            sc = SCENARIOS[sid]
            experiments.append({
                "id": f"cat6_{sid}_{tok_label}",
                "category": "6_token_limit",
                "description": f"Max {max_tok} tokens: {sc.query[:50]}",
                "scenario_id": sid,
                "scenario_type": sc.scenario_type,
                "strategy": tok_label,
                "params": {"temperature": 0.5, "max_tokens": max_tok},
                "temperature": 0.5,
                "max_tokens": max_tok,
                "thinking_prefix": "",
                "prompt_template": None,
            })

    return experiments


# ── Experiment runner ───────────────────────────────────────────────────

def run_experiment(exp: dict) -> ExperimentResult:
    """Execute a single synthesis experiment."""
    sid = exp["scenario_id"]
    sc = SCENARIOS[sid]

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        scenario_id=sid,
        scenario_type=exp["scenario_type"],
        strategy=exp["strategy"],
        params=exp["params"],
        expected_key_facts=list(sc.key_facts),
        forbidden_terms=list(FORBIDDEN_TERMS),
    )

    try:
        # Handle reasoning override for Cat 5
        run_scenario = sc
        if "override_reasoning" in exp:
            # Create a temporary scenario with overridden reasoning
            run_scenario = SynthesisScenario(
                id=sc.id,
                query=sc.query,
                route=sc.route,
                scenario_type=sc.scenario_type,
                tool_results_text=sc.tool_results_text,
                reasoning=exp["override_reasoning"],
                key_facts=sc.key_facts,
                notes=sc.notes,
            )

        response, latency_ms, has_thinking = run_synthesis(
            run_scenario,
            temperature=exp["temperature"],
            max_tokens=exp["max_tokens"],
            thinking_prefix=exp.get("thinking_prefix", ""),
            prompt_template=exp.get("prompt_template"),
        )

        result.raw_response = response
        result.has_thinking_tokens = has_thinking
        result.thinking_prefix_used = bool(exp.get("thinking_prefix", ""))
        result.per_call_latency_ms = [latency_ms]
        result.total_latency_ms = latency_ms

        # Deterministic eval
        det = evaluate_deterministic(response, sc)
        result.key_facts_found = det["key_facts_found"]
        result.key_fact_rate = det["key_fact_rate"]
        result.forbidden_terms_found = det["forbidden_terms_found"]
        result.forbidden_clean = det["forbidden_clean"]
        result.response_word_count = det["response_word_count"]

    except Exception as e:
        result.error = str(e)

    return result


def run_all(experiments: list[dict], output_dir: Path) -> list[ExperimentResult]:
    """Run all experiments sequentially, saving results incrementally."""
    results = []
    total = len(experiments)
    print(f"\nRunning {total} experiments (~{total} LLM calls)...\n")

    for i, exp in enumerate(experiments, 1):
        tag = f"[{i:3d}/{total}]"
        print(f"{tag} {exp['id']:<55s}", end="", flush=True)

        result = run_experiment(exp)

        if result.error:
            print(f"  ERROR: {result.error[:60]}")
        else:
            fact_flag = f"facts={result.key_fact_rate:.0%}"
            clean_flag = "clean" if result.forbidden_clean else "LEAK"
            print(
                f"  {fact_flag}  {clean_flag}  "
                f"words={result.response_word_count:3d}  "
                f"{result.total_latency_ms:6.0f}ms"
            )

        results.append(result)

        # Save incrementally
        with open(output_dir / "results.jsonl", "a") as f:
            f.write(json.dumps(asdict(result), default=str) + "\n")

    return results


# ── Gemini judge ────────────────────────────────────────────────────────

JUDGE_PROMPT = """\
You are evaluating a medical AI assistant's response synthesis quality.

## Context
User query: {user_query}
Tool results provided to the model: {tool_results}
Reasoning context (if any): {reasoning}
Model's response: {response}

## Expected key facts that should be included:
{expected_key_facts}

## Evaluation Dimensions (score each 0-10)

1. **completeness**: Does the response include the key clinical findings from the tool results? (0=missing all key facts, 10=all relevant facts included)
2. **accuracy**: Is the response factually correct given the tool results? Does it avoid hallucinating data not present in the results? (0=major errors, 10=fully accurate)
3. **conciseness**: Is the response appropriately brief? Not rambling or repetitive? (0=extremely verbose/repetitive, 10=perfectly concise)
4. **clinical_tone**: Does it use professional medical language and abbreviations? Is it appropriate for a healthcare professional audience? (0=lay language, 10=expert clinical tone)
5. **source_hiding**: Does it avoid mentioning tool names (check_drug_safety, PubMed, etc.), API sources, internal processes, or "according to" phrases? (0=leaks multiple sources, 10=fully clean)
6. **overall**: Overall quality as a clinical decision support response. (0=unusable, 10=excellent)

Respond with ONLY a JSON object (no markdown fences):
{{
    "completeness": <int>,
    "accuracy": <int>,
    "conciseness": <int>,
    "clinical_tone": <int>,
    "source_hiding": <int>,
    "overall": <int>,
    "rationale": "<brief explanation>"
}}"""

_gemini_client: httpx.Client | None = None


def _get_gemini_client() -> httpx.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = httpx.Client(timeout=30.0)
    return _gemini_client


def gemini_judge(result: ExperimentResult, max_retries: int = 4) -> dict:
    """Ask Gemini to evaluate the synthesis quality. Retries on 429."""
    sc = SCENARIOS[result.scenario_id]
    prompt = JUDGE_PROMPT.format(
        user_query=sc.query,
        tool_results=sc.tool_results_text[:1000] if sc.tool_results_text else "(none)",
        reasoning=sc.reasoning[:500] if sc.reasoning else "(none)",
        response=result.raw_response[:1500],
        expected_key_facts="\n".join(f"- {f}" for f in sc.key_facts),
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
    }
    for attempt in range(max_retries + 1):
        resp = _get_gemini_client().post(url, json=payload)
        if resp.status_code == 429 and attempt < max_retries:
            wait = 2 ** attempt + 1  # 2, 3, 5, 9
            print(f" [429, wait {wait}s]", end="", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        break
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def judge_all(results: list[ExperimentResult]) -> list[ExperimentResult]:
    """Run Gemini judge on every result that has a response. Skips already-judged."""
    if not GEMINI_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set. Cannot run Gemini judge.")
        sys.exit(1)

    judgeable = [r for r in results if r.raw_response and not r.error and r.judge_overall is None]
    already = sum(1 for r in results if r.judge_overall is not None)
    total = len(judgeable)
    print(f"\nRunning Gemini judge on {total} results ({already} already judged)...\n")

    for i, r in enumerate(judgeable, 1):
        print(f"[{i:3d}/{total}] {r.experiment_id:<55s}", end="", flush=True)
        try:
            verdict = gemini_judge(r)
            r.judge_completeness = verdict.get("completeness")
            r.judge_accuracy = verdict.get("accuracy")
            r.judge_conciseness = verdict.get("conciseness")
            r.judge_clinical_tone = verdict.get("clinical_tone")
            r.judge_source_hiding = verdict.get("source_hiding")
            r.judge_overall = verdict.get("overall")
            r.judge_rationale = verdict.get("rationale", "")
            print(
                f"  comp={r.judge_completeness:2d}  "
                f"acc={r.judge_accuracy:2d}  "
                f"conc={r.judge_conciseness:2d}  "
                f"tone={r.judge_clinical_tone:2d}  "
                f"hide={r.judge_source_hiding:2d}  "
                f"overall={r.judge_overall:2d}"
            )
        except Exception as e:
            r.judge_rationale = f"ERROR: {e}"
            print(f"  ERROR: {e}")

    return results


# ── Save / Load ─────────────────────────────────────────────────────────

def save_results(results: list[ExperimentResult], output_dir: Path):
    """Write all results to JSONL (overwrites)."""
    with open(output_dir / "results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(asdict(r), default=str) + "\n")


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
                expected_key_facts=d.get("expected_key_facts", []),
                forbidden_terms=d.get("forbidden_terms", []),
                raw_response=d.get("raw_response", ""),
                response_word_count=d.get("response_word_count", 0),
                has_thinking_tokens=d.get("has_thinking_tokens", False),
                thinking_prefix_used=d.get("thinking_prefix_used", False),
                key_facts_found=d.get("key_facts_found", {}),
                key_fact_rate=d.get("key_fact_rate", 0.0),
                forbidden_terms_found=d.get("forbidden_terms_found", []),
                forbidden_clean=d.get("forbidden_clean", True),
                num_llm_calls=d.get("num_llm_calls", 1),
                per_call_latency_ms=d.get("per_call_latency_ms", []),
                total_latency_ms=d.get("total_latency_ms", 0),
                error=d.get("error"),
                judge_completeness=d.get("judge_completeness"),
                judge_accuracy=d.get("judge_accuracy"),
                judge_conciseness=d.get("judge_conciseness"),
                judge_clinical_tone=d.get("judge_clinical_tone"),
                judge_source_hiding=d.get("judge_source_hiding"),
                judge_overall=d.get("judge_overall"),
                judge_rationale=d.get("judge_rationale"),
            )
            results.append(r)
    return results


# ── Report helpers ──────────────────────────────────────────────────────

def _pct(n: int | float, total: int | float) -> str:
    if total == 0:
        return "0.0%"
    return f"{100 * n / total:.1f}%"


def _avg(values: list[int | float | None]) -> float:
    clean = [v for v in values if v is not None]
    return sum(clean) / max(len(clean), 1)


def _avg_str(values: list[int | float | None]) -> str:
    clean = [v for v in values if v is not None]
    if not clean:
        return "—"
    return f"{sum(clean) / len(clean):.1f}"


# ── Report generator ───────────────────────────────────────────────────

def generate_report(results: list[ExperimentResult], output_dir: Path):
    """Generate comprehensive Markdown report with 13 sections."""
    lines: list[str] = []
    w = lines.append

    ok = [r for r in results if not r.error]
    err = [r for r in results if r.error]

    w("# MedGemma 4B — Response Synthesis Experiments")
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
    avg_fact_rate = _avg([r.key_fact_rate for r in ok])
    clean_count = sum(1 for r in ok if r.forbidden_clean)
    avg_words = _avg([r.response_word_count for r in ok])
    avg_latency = _avg([r.total_latency_ms for r in ok])
    thinking_count = sum(1 for r in ok if r.has_thinking_tokens)

    w(f"- **Avg key fact rate:** {avg_fact_rate:.1%}")
    w(f"- **Source-clean responses:** {clean_count}/{len(ok)} ({_pct(clean_count, len(ok))})")
    w(f"- **Avg word count:** {avg_words:.0f}")
    w(f"- **Avg latency:** {avg_latency:.0f}ms")
    w(f"- **Thinking tokens observed:** {thinking_count}/{len(ok)} ({_pct(thinking_count, len(ok))})")

    # Gemini summary
    judged = [r for r in ok if r.judge_overall is not None]
    if judged:
        w(f"- **Gemini judged:** {len(judged)} results")
        w(f"- **Avg completeness:** {_avg_str([r.judge_completeness for r in judged])}/10")
        w(f"- **Avg accuracy:** {_avg_str([r.judge_accuracy for r in judged])}/10")
        w(f"- **Avg conciseness:** {_avg_str([r.judge_conciseness for r in judged])}/10")
        w(f"- **Avg clinical tone:** {_avg_str([r.judge_clinical_tone for r in judged])}/10")
        w(f"- **Avg source hiding:** {_avg_str([r.judge_source_hiding for r in judged])}/10")
        w(f"- **Avg overall:** {_avg_str([r.judge_overall for r in judged])}/10")
    w("")

    # ── 2. Strategy Comparison Table ───────────────────────────────
    w("## 2. Strategy Comparison Table")
    w("")
    w("| Category | Strategy | N | Fact Rate | Clean | Avg Words | Avg Latency | Gemini Overall |")
    w("|----------|----------|---|-----------|-------|-----------|-------------|----------------|")

    categories = sorted(set(r.category for r in results))
    for cat in categories:
        cat_results = [r for r in ok if r.category == cat]
        strategies = sorted(set(r.strategy for r in cat_results))
        cat_label = cat.split("_", 1)[1].replace("_", " ").title() if "_" in cat else cat
        for strat in strategies:
            s_results = [r for r in cat_results if r.strategy == strat]
            n = len(s_results)
            fact_r = _avg([r.key_fact_rate for r in s_results])
            clean = sum(1 for r in s_results if r.forbidden_clean)
            words = _avg([r.response_word_count for r in s_results])
            lat = _avg([r.total_latency_ms for r in s_results])
            gem = _avg_str([r.judge_overall for r in s_results])
            w(f"| {cat_label} | {strat} | {n} | {fact_r:.0%} | {clean}/{n} | {words:.0f} | {lat:.0f}ms | {gem} |")
    w("")

    # ── 3. Baseline Synthesis Analysis (Cat 1) ─────────────────────
    w("## 3. Baseline Synthesis Analysis (Cat 1)")
    w("")
    cat1 = [r for r in ok if r.category == "1_baseline"]
    if cat1:
        # Per-scenario-type breakdown
        w("### By Scenario Type")
        w("")
        w("| Type | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |")
        w("|------|---|---------------|-------|-----------|----------------|")
        stypes = sorted(set(r.scenario_type for r in cat1))
        for stype in stypes:
            st_results = [r for r in cat1 if r.scenario_type == stype]
            n = len(st_results)
            fr = _avg([r.key_fact_rate for r in st_results])
            cl = sum(1 for r in st_results if r.forbidden_clean)
            wd = _avg([r.response_word_count for r in st_results])
            gm = _avg_str([r.judge_overall for r in st_results])
            w(f"| {stype} | {n} | {fr:.0%} | {cl}/{n} | {wd:.0f} | {gm} |")
        w("")

        # Per-scenario detail
        w("### Per-Scenario Detail")
        w("")
        w("| Scenario | Query | Fact Rate | Clean | Words | Gemini |")
        w("|----------|-------|-----------|-------|-------|--------|")
        for r in sorted(cat1, key=lambda x: x.scenario_id):
            sc = SCENARIOS[r.scenario_id]
            gem = f"{r.judge_overall}" if r.judge_overall is not None else "—"
            cl = "Y" if r.forbidden_clean else "N"
            w(f"| {r.scenario_id} | {sc.query[:40]}... | {r.key_fact_rate:.0%} | {cl} | {r.response_word_count} | {gem} |")
        w("")

    # ── 4. Thinking Effect Analysis (Cat 2 vs Cat 1) ──────────────
    w("## 4. Thinking Effect Analysis (Cat 2 vs Cat 1)")
    w("")
    cat2 = [r for r in ok if r.category == "2_thinking"]
    if cat1 and cat2:
        w("### Paired Comparison")
        w("")
        w("| Scenario | Baseline Facts | Thinking Facts | Baseline Words | Thinking Words | Baseline Gemini | Thinking Gemini |")
        w("|----------|----------------|----------------|----------------|----------------|-----------------|-----------------|")
        for r1 in sorted(cat1, key=lambda x: x.scenario_id):
            r2_list = [r for r in cat2 if r.scenario_id == r1.scenario_id]
            if r2_list:
                r2 = r2_list[0]
                g1 = f"{r1.judge_overall}" if r1.judge_overall is not None else "—"
                g2 = f"{r2.judge_overall}" if r2.judge_overall is not None else "—"
                w(f"| {r1.scenario_id} | {r1.key_fact_rate:.0%} | {r2.key_fact_rate:.0%} | {r1.response_word_count} | {r2.response_word_count} | {g1} | {g2} |")
        w("")

        # Aggregates
        b_facts = _avg([r.key_fact_rate for r in cat1])
        t_facts = _avg([r.key_fact_rate for r in cat2])
        b_words = _avg([r.response_word_count for r in cat1])
        t_words = _avg([r.response_word_count for r in cat2])
        b_gem = _avg_str([r.judge_overall for r in cat1])
        t_gem = _avg_str([r.judge_overall for r in cat2])
        w(f"**Aggregates:** Baseline fact rate={b_facts:.0%}, Thinking={t_facts:.0%} | "
          f"Baseline words={b_words:.0f}, Thinking={t_words:.0f} | "
          f"Baseline Gemini={b_gem}, Thinking={t_gem}")
        w("")

    # ── 5. Temperature Analysis (Cat 3) ────────────────────────────
    w("## 5. Temperature Analysis (Cat 3)")
    w("")
    cat3 = [r for r in ok if r.category == "3_temperature"]
    if cat3:
        w("| Temperature | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |")
        w("|-------------|---|---------------|-------|-----------|----------------|")
        for temp in [0.1, 0.3, 0.5, 0.7]:
            temp_label = f"T={temp}"
            t_results = [r for r in cat3 if r.strategy == temp_label]
            if t_results:
                n = len(t_results)
                fr = _avg([r.key_fact_rate for r in t_results])
                cl = sum(1 for r in t_results if r.forbidden_clean)
                wd = _avg([r.response_word_count for r in t_results])
                gm = _avg_str([r.judge_overall for r in t_results])
                w(f"| {temp} | {n} | {fr:.0%} | {cl}/{n} | {wd:.0f} | {gm} |")
        w("")

        # Per-scenario temperature curves
        w("### Per-Scenario Temperature Effect")
        w("")
        w("| Scenario | T=0.1 Facts | T=0.3 Facts | T=0.5 Facts | T=0.7 Facts |")
        w("|----------|-------------|-------------|-------------|-------------|")
        for sid in KEY_SCENARIOS:
            row = f"| {sid}"
            for temp in [0.1, 0.3, 0.5, 0.7]:
                t_label = f"T={temp}"
                match = [r for r in cat3 if r.scenario_id == sid and r.strategy == t_label]
                if match:
                    row += f" | {match[0].key_fact_rate:.0%}"
                else:
                    row += " | —"
            row += " |"
            w(row)
        w("")

    # ── 6. Prompt Variation Analysis (Cat 4) ───────────────────────
    w("## 6. Prompt Variation Analysis (Cat 4)")
    w("")
    cat4 = [r for r in ok if r.category == "4_prompt_variation"]
    if cat4:
        w("| Variant | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |")
        w("|---------|---|---------------|-------|-----------|----------------|")
        for variant in ["structured", "brief", "comprehensive"]:
            v_results = [r for r in cat4 if r.strategy == variant]
            if v_results:
                n = len(v_results)
                fr = _avg([r.key_fact_rate for r in v_results])
                cl = sum(1 for r in v_results if r.forbidden_clean)
                wd = _avg([r.response_word_count for r in v_results])
                gm = _avg_str([r.judge_overall for r in v_results])
                w(f"| {variant} | {n} | {fr:.0%} | {cl}/{n} | {wd:.0f} | {gm} |")

        # Compare with baseline
        w("")
        w("### vs Production Baseline (Cat 1, same 15 scenarios)")
        w("")
        baseline_key = [r for r in cat1 if r.scenario_id in KEY_SCENARIOS]
        if baseline_key:
            b_fr = _avg([r.key_fact_rate for r in baseline_key])
            b_wd = _avg([r.response_word_count for r in baseline_key])
            b_gm = _avg_str([r.judge_overall for r in baseline_key])
            w(f"- **Production baseline:** fact_rate={b_fr:.0%}, words={b_wd:.0f}, gemini={b_gm}")
            for variant in ["structured", "brief", "comprehensive"]:
                v_results = [r for r in cat4 if r.strategy == variant]
                if v_results:
                    v_fr = _avg([r.key_fact_rate for r in v_results])
                    v_wd = _avg([r.response_word_count for r in v_results])
                    v_gm = _avg_str([r.judge_overall for r in v_results])
                    w(f"- **{variant}:** fact_rate={v_fr:.0%}, words={v_wd:.0f}, gemini={v_gm}")
        w("")

    # ── 7. Reasoning Context Effect (Cat 5) ────────────────────────
    w("## 7. Reasoning Context Effect (Cat 5)")
    w("")
    cat5 = [r for r in ok if r.category == "5_reasoning_ctx"]
    if cat5:
        with_r = [r for r in cat5 if r.strategy == "with_reasoning"]
        no_r = [r for r in cat5 if r.strategy == "no_reasoning"]

        w("| Condition | N | Avg Fact Rate | Clean | Avg Words | Gemini Overall |")
        w("|-----------|---|---------------|-------|-----------|----------------|")
        for label, group in [("With reasoning", with_r), ("No reasoning", no_r)]:
            if group:
                n = len(group)
                fr = _avg([r.key_fact_rate for r in group])
                cl = sum(1 for r in group if r.forbidden_clean)
                wd = _avg([r.response_word_count for r in group])
                gm = _avg_str([r.judge_overall for r in group])
                w(f"| {label} | {n} | {fr:.0%} | {cl}/{n} | {wd:.0f} | {gm} |")
        w("")

        # Paired comparison
        w("### Paired Comparison")
        w("")
        w("| Scenario | With Facts | Without Facts | With Gemini | Without Gemini |")
        w("|----------|-----------|--------------|-------------|----------------|")
        reasoning_test_ids = ["SC-01", "SC-02", "SC-03", "SC-06", "SC-18",
                              "SC-26", "SC-27", "SC-28", "SC-29", "SC-30"]
        for sid in reasoning_test_ids:
            wr = [r for r in with_r if r.scenario_id == sid]
            nr = [r for r in no_r if r.scenario_id == sid]
            if wr and nr:
                wg = f"{wr[0].judge_overall}" if wr[0].judge_overall is not None else "—"
                ng = f"{nr[0].judge_overall}" if nr[0].judge_overall is not None else "—"
                w(f"| {sid} | {wr[0].key_fact_rate:.0%} | {nr[0].key_fact_rate:.0%} | {wg} | {ng} |")
        w("")

    # ── 8. Token Limit Analysis (Cat 6) ────────────────────────────
    w("## 8. Token Limit Analysis (Cat 6)")
    w("")
    cat6 = [r for r in ok if r.category == "6_token_limit"]
    if cat6:
        w("| Max Tokens | N | Avg Fact Rate | Avg Words | Gemini Overall | Gemini Conciseness |")
        w("|------------|---|---------------|-----------|----------------|-------------------|")
        for max_tok in [128, 256, 512]:
            tok_label = f"tok={max_tok}"
            t_results = [r for r in cat6 if r.strategy == tok_label]
            if t_results:
                n = len(t_results)
                fr = _avg([r.key_fact_rate for r in t_results])
                wd = _avg([r.response_word_count for r in t_results])
                gm = _avg_str([r.judge_overall for r in t_results])
                gc = _avg_str([r.judge_conciseness for r in t_results])
                w(f"| {max_tok} | {n} | {fr:.0%} | {wd:.0f} | {gm} | {gc} |")
        w("")

        # Quality vs brevity tradeoff
        w("### Quality vs Brevity Tradeoff by Scenario")
        w("")
        w("| Scenario | 128 Facts / Words | 256 Facts / Words | 512 Facts / Words |")
        w("|----------|-------------------|-------------------|-------------------|")
        for sid in TOKEN_SCENARIOS:
            row = f"| {sid}"
            for max_tok in [128, 256, 512]:
                tok_label = f"tok={max_tok}"
                match = [r for r in cat6 if r.scenario_id == sid and r.strategy == tok_label]
                if match:
                    row += f" | {match[0].key_fact_rate:.0%} / {match[0].response_word_count}w"
                else:
                    row += " | —"
            row += " |"
            w(row)
        w("")

    # ── 9. Key Fact Inclusion Analysis ─────────────────────────────
    w("## 9. Key Fact Inclusion Analysis")
    w("")
    # Which facts get dropped most? Analyze Cat 1 baseline
    if cat1:
        w("### Most Frequently Missing Facts (Cat 1 Baseline)")
        w("")
        fact_miss_counts: dict[str, int] = defaultdict(int)
        fact_total_counts: dict[str, int] = defaultdict(int)
        for r in cat1:
            for fact, found in r.key_facts_found.items():
                fact_total_counts[fact] += 1
                if not found:
                    fact_miss_counts[fact] += 1

        w("| Fact Pattern | Times Missing | Times Tested | Hit Rate |")
        w("|-------------|---------------|--------------|----------|")
        sorted_facts = sorted(fact_miss_counts.items(), key=lambda x: x[1], reverse=True)
        for fact, miss in sorted_facts[:15]:
            total = fact_total_counts[fact]
            hit = total - miss
            w(f"| `{fact[:40]}` | {miss} | {total} | {_pct(hit, total)} |")
        w("")

    # ── 10. Source Leakage Analysis ────────────────────────────────
    w("## 10. Source Leakage Analysis")
    w("")
    leak_counts: dict[str, int] = defaultdict(int)
    total_non_direct = sum(1 for r in ok if r.scenario_type != "direct")
    for r in ok:
        for term in r.forbidden_terms_found:
            leak_counts[term] += 1

    if leak_counts:
        w("| Leaked Term | Occurrences | % of Non-Direct Experiments |")
        w("|-------------|-------------|----------------------------|")
        for term, count in sorted(leak_counts.items(), key=lambda x: x[1], reverse=True):
            w(f"| `{term}` | {count} | {_pct(count, total_non_direct)} |")
    else:
        w("No source leakage detected across any experiments.")
    w("")

    # ── 11. Deterministic vs Gemini Agreement ──────────────────────
    w("## 11. Deterministic vs Gemini Agreement")
    w("")
    judged = [r for r in ok if r.judge_overall is not None]
    if judged:
        # Correlation between fact_rate and judge_completeness
        w("### Fact Rate vs Gemini Completeness")
        w("")
        # Bucket by fact rate ranges
        buckets = [(0, 0.25, "0-25%"), (0.25, 0.5, "25-50%"), (0.5, 0.75, "50-75%"), (0.75, 1.01, "75-100%")]
        w("| Fact Rate Range | N | Avg Gemini Completeness | Avg Gemini Overall |")
        w("|-----------------|---|-------------------------|-------------------|")
        for lo, hi, label in buckets:
            bucket = [r for r in judged if lo <= r.key_fact_rate < hi]
            if bucket:
                avg_comp = _avg_str([r.judge_completeness for r in bucket])
                avg_ov = _avg_str([r.judge_overall for r in bucket])
                w(f"| {label} | {len(bucket)} | {avg_comp} | {avg_ov} |")
        w("")

        # Source-clean vs judge_source_hiding
        w("### Source Clean vs Gemini Source Hiding")
        w("")
        clean_j = [r for r in judged if r.forbidden_clean]
        leak_j = [r for r in judged if not r.forbidden_clean]
        w("| Deterministic | N | Avg Gemini Source Hiding |")
        w("|---------------|---|-------------------------|")
        if clean_j:
            w(f"| Clean | {len(clean_j)} | {_avg_str([r.judge_source_hiding for r in clean_j])} |")
        if leak_j:
            w(f"| Leaked | {len(leak_j)} | {_avg_str([r.judge_source_hiding for r in leak_j])} |")
        w("")

    # ── 12. Latency Analysis ───────────────────────────────────────
    w("## 12. Latency Analysis")
    w("")
    w("| Category | Strategy | N | Avg Latency (ms) | Min | Max |")
    w("|----------|----------|---|-------------------|-----|-----|")
    for cat in categories:
        cat_results = [r for r in ok if r.category == cat]
        strategies = sorted(set(r.strategy for r in cat_results))
        cat_label = cat.split("_", 1)[1].replace("_", " ").title() if "_" in cat else cat
        for strat in strategies:
            s_results = [r for r in cat_results if r.strategy == strat]
            n = len(s_results)
            lats = [r.total_latency_ms for r in s_results]
            w(f"| {cat_label} | {strat} | {n} | {_avg(lats):.0f} | {min(lats):.0f} | {max(lats):.0f} |")
    w("")

    # ── 13. Recommendations ────────────────────────────────────────
    w("## 13. Recommendations")
    w("")

    # Auto-generated best strategy per dimension
    if judged:
        w("### Best Strategy by Gemini Dimension")
        w("")
        dims = [
            ("completeness", "judge_completeness"),
            ("accuracy", "judge_accuracy"),
            ("conciseness", "judge_conciseness"),
            ("clinical_tone", "judge_clinical_tone"),
            ("source_hiding", "judge_source_hiding"),
            ("overall", "judge_overall"),
        ]
        for dim_name, dim_attr in dims:
            best_strat = None
            best_score = -1.0
            for cat in categories:
                cat_results = [r for r in judged if r.category == cat]
                for strat in set(r.strategy for r in cat_results):
                    s_results = [r for r in cat_results if r.strategy == strat]
                    scores = [getattr(r, dim_attr) for r in s_results if getattr(r, dim_attr) is not None]
                    if scores:
                        avg_s = sum(scores) / len(scores)
                        if avg_s > best_score:
                            best_score = avg_s
                            best_strat = f"{cat}/{strat}"
            if best_strat:
                w(f"- **{dim_name}:** {best_strat} ({best_score:.1f}/10)")
        w("")

    # Best overall based on key_fact_rate + forbidden_clean
    w("### Best Strategy by Deterministic Metrics")
    w("")
    for cat in categories:
        cat_results = [r for r in ok if r.category == cat]
        cat_label = cat.split("_", 1)[1].replace("_", " ").title() if "_" in cat else cat
        best_strat = None
        best_score = -1.0
        for strat in set(r.strategy for r in cat_results):
            s_results = [r for r in cat_results if r.strategy == strat]
            # Combined score: fact_rate * 0.7 + clean_rate * 0.3
            fr = _avg([r.key_fact_rate for r in s_results])
            cr = sum(1 for r in s_results if r.forbidden_clean) / max(len(s_results), 1)
            score = fr * 0.7 + cr * 0.3
            if score > best_score:
                best_score = score
                best_strat = strat
        if best_strat:
            w(f"- **{cat_label}:** {best_strat} (combined={best_score:.2f})")
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


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MedGemma 4B response synthesis experiments"
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
        judged = [r for r in results if r.judge_overall is not None and not r.error]
        avg_overall = _avg([r.judge_overall for r in judged])
        print(f"\nGemini judged {len(judged)} results. Avg overall: {avg_overall:.1f}/10")
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
    output_dir = Path("synthesis_experiments") / timestamp
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
    avg_fact = _avg([r.key_fact_rate for r in ok_results])
    clean = sum(1 for r in ok_results if r.forbidden_clean)
    print(f"\n{'=' * 60}")
    print(f"Done. Avg fact rate: {avg_fact:.1%}, source-clean: {clean}/{len(ok_results)}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
