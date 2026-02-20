"""Prompt templates for DocGemma v3 agent nodes.

Every prompt, temperature, and configuration here is grounded in empirical
findings from 856 experiments across 4 test suites on MedGemma 4B.

Key principles (from the Prompting Guide):
- T=0.0 for operational decisions (prevents thinking tokens, Part II §25)
- T=0.5 for synthesis (peak fact rate 90%, Part IV §43)
- max_tokens=256 for synthesis (quality 9.4→9.7 vs 512, Part IV §46)
- full_desc tool descriptions (95% accuracy, Part II §16)
- 1-shot matched examples (91% arg accuracy, Part II §19)
- Critical-first field ordering (Part II §20)
- No thinking prefixes for synthesis (13% empty output, Part IV §42)
- Error pre-formatting (4.8→10/10 quality, Part IV §48)
"""


# =============================================================================
# SYSTEM PROMPT (prepended to every API call via model.py)
# =============================================================================


def build_system_prompt() -> str:
    """Build system prompt with current date and time."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%H:%M UTC")

    return (
        "You are a clinical decision-support assistant integrated with an "
        "electronic health record system and medical knowledge tools. "
        f"Current date: {date_str}. Current time: {time_str}."
    )


# =============================================================================
# TEMPERATURE & MAX TOKEN SETTINGS
# =============================================================================

TEMPERATURE: dict[str, float] = {
    "intent_classify": 0.0,       # Operational — deterministic (Part II §25)
    "tool_select_stage1": 0.0,    # Operational — deterministic
    "tool_select_stage2": 0.0,    # Operational — deterministic
    "result_classify": 0.0,       # Classification — deterministic
    "synthesize": 0.5,            # Free-form — validated optimum (Part IV §43)
}

MAX_TOKENS: dict[str, int] = {
    "intent_classify": 256,
    "tool_select_stage1": 64,
    "tool_select_stage2": 128,
    "result_classify": 128,
    "synthesize": 256,            # Validated optimum (Part IV §46)
}


# =============================================================================
# TOOL CLINICAL LABELS (tool_name → clinician-facing label)
#   Eliminates source leakage at the root (Part IV §50, rec #5)
# =============================================================================

TOOL_CLINICAL_LABELS: dict[str, str] = {
    "check_drug_safety": "Drug Safety Report",
    "check_drug_interactions": "Drug Interaction Check",
    "search_medical_literature": "Medical Literature",
    "find_clinical_trials": "Clinical Trials",
    "search_patient": "Patient Search",
    "get_patient_chart": "Patient Record",
    "prescribe_medication": "Prescription",
    "add_allergy": "Allergy Documentation",
    "save_clinical_note": "Clinical Note",
}


# =============================================================================
# ERROR TEMPLATES (pre-format before LLM sees them — Part IV §48)
#   Raw errors → 4.8/10 Gemini.  Pre-formatted → 10/10.
# =============================================================================

ERROR_TEMPLATES: dict[str, str] = {
    "timeout": "The {tool_label} was temporarily unavailable. Please try again shortly.",
    "not_found": "No results were found for {entity} in the {tool_label}.",
    "invalid_args": (
        "The request to {tool_label} could not be completed "
        "— additional information is needed."
    ),
    "rate_limit": "The {tool_label} is temporarily busy. The system will retry automatically.",
    "server_error": "The {tool_label} experienced a temporary error. The system will retry automatically.",
    "multiple_matches": (
        "Multiple matches were found in {tool_label}. "
        "Please clarify which one you meant."
    ),
    "generic": "The {tool_label} was unable to complete the request.",
}


# =============================================================================
# FULL TOOL DESCRIPTIONS (full_desc — 95% accuracy, Part II §16)
#   Used in TOOL_SELECT Stage 1.
# =============================================================================

TOOL_DESCRIPTIONS = """Available tools:

- none — No tool is applicable. Select this when the user's request cannot be fulfilled
  by any of the tools below (e.g., non-medical tasks, scheduling, general conversation).

- check_drug_safety(drug_name: str) — Look up FDA boxed warnings, contraindications,
  and major safety alerts for a specific drug. Use when a clinician asks about drug
  safety, warnings, or whether a drug is safe for a particular patient.

- check_drug_interactions(drug_names: list[str]) — Check for known interactions between
  two or more drugs. Returns severity, mechanism, and clinical significance. Use when a
  clinician asks about combining medications or potential drug-drug interactions.

- search_medical_literature(query: str) — Search PubMed and medical literature databases
  for published studies, systematic reviews, and clinical evidence. Use when a clinician
  asks about research, evidence, studies, or medical literature on a topic.

- find_clinical_trials(condition: str, status: str = None) — Search ClinicalTrials.gov
  for active, recruiting, or completed clinical trials for a specific condition or
  treatment. Use when a clinician asks about experimental treatments, ongoing trials,
  or new therapies being studied.

- search_patient(name: str) — Search the electronic health record system for a patient
  by name. Returns matching patient IDs and basic demographics. Use when a clinician
  mentions a patient by name and needs to look them up.

- get_patient_chart(patient_id: str) — Retrieve the full clinical summary for a patient,
  including diagnoses, medications, allergies, lab results, and vitals. Requires a
  patient ID (not a name). Use when a clinician wants to review a patient's record.

- prescribe_medication(patient_id: str, medication_name: str, dosage: str,
  frequency: str) — Create a new medication order for a patient in the EHR. Use when
  a clinician wants to prescribe, order, or start a medication for a specific patient.

- add_allergy(patient_id: str, substance: str, reaction: str,
  severity: str = None) — Document an allergy or adverse reaction in a patient's
  record. Use when a clinician wants to record, document, or note an allergy.

- save_clinical_note(patient_id: str, note_type: str, note_text: str) — Save a
  clinical note (progress note, consult note, procedure note, etc.) to a patient's
  record. Use when a clinician wants to write, save, or document a clinical note.

"""


# =============================================================================
# 1-SHOT EXAMPLES PER TOOL (for TOOL_SELECT Stage 1 — Part II §19)
#   1-shot matched to suggested_tool is the sweet spot at 91% arg accuracy.
# =============================================================================

TOOL_EXAMPLES: dict[str, tuple[str, str]] = {
    "none": (
        "Edit my calendar for next Tuesday",
        "none",
    ),
    "check_drug_safety": (
        "Check FDA warnings for metformin",
        "check_drug_safety",
    ),
    "check_drug_interactions": (
        "Check interactions between warfarin and aspirin",
        "check_drug_interactions",
    ),
    "search_medical_literature": (
        "Search for studies on SGLT2 inhibitors and cardiovascular outcomes",
        "search_medical_literature",
    ),
    "find_clinical_trials": (
        "Find recruiting clinical trials for lung cancer",
        "find_clinical_trials",
    ),
    "search_patient": (
        "Search for patient John Smith",
        "search_patient",
    ),
    "get_patient_chart": (
        "Get the chart for patient abc-123",
        "get_patient_chart",
    ),
    "prescribe_medication": (
        "Prescribe lisinopril 10mg daily for patient abc-123",
        "prescribe_medication",
    ),
    "add_allergy": (
        "Document penicillin allergy for patient abc-123",
        "add_allergy",
    ),
    "save_clinical_note": (
        "Save a progress note for patient abc-123",
        "save_clinical_note",
    ),
}

# Fallback example when suggested_tool is None or unrecognised
_DEFAULT_EXAMPLE = TOOL_EXAMPLES["check_drug_safety"]


# =============================================================================
# NODE PROMPTS
# =============================================================================

# ── Node 2: INTENT_CLASSIFY ──────────────────────────────────────────────────

INTENT_CLASSIFY_PROMPT = """\
You are a clinical decision-support assistant integrated with an electronic health record
system and medical knowledge tools.

Your task: classify the user's query and provide a brief clinical summary.

Classification rules:
- DIRECT: General medical questions, greetings, thanks, or questions answerable from
  medical knowledge alone (e.g., "What is hypertension?", "Hello", "Explain metformin MOA")
- TOOL_NEEDED: Requests requiring specific patient data, drug safety lookups, literature
  searches, clinical trial searches, prescriptions, allergy documentation, or clinical notes

Provide a task_summary that captures the clinical context in ~50 words or fewer.
If TOOL_NEEDED, suggest the most relevant tool name.
{patient_context_section}
Query: {user_query}"""


# ── Node 3 Stage 1: TOOL_SELECT (tool name only) ────────────────────────────

TOOL_SELECT_STAGE1_PROMPT = """\
You are a clinical tool router. Select the single most appropriate tool for the task.

{tool_descriptions}

Example:
User: "{example_query}"
Tool: {example_tool}

Now select the tool for the current task.

Task summary: {task_summary}
User query: {user_query}"""


# ── Node 3 Stage 2: TOOL_SELECT (per-tool args) ─────────────────────────────

TOOL_SELECT_STAGE2_PROMPT = """\
Extract the arguments for the {tool_name} tool from the user's request.

Tool: {tool_name}
Description: {tool_description}

User query: {user_query}
{entity_hints}
Fill in the required arguments."""


# ── Node 5: RESULT_CLASSIFY ──────────────────────────────────────────────────

RESULT_CLASSIFY_PROMPT = """\
You are evaluating a tool result. Classify the quality of the data returned.

User's original question: {user_query}
Clinical context: {task_summary}

Tool used: {tool_label}
Result:
{formatted_tool_result}

Classify the result quality and provide a brief summary."""


# ── Node 7: SYNTHESIZE (system prompt) ───────────────────────────────────────

SYNTHESIZE_SYSTEM_PROMPT = """\
You are a clinical decision-support assistant. Provide a clear, concise response to the
clinician based on the information below.

Guidelines:
- Include only the most critical findings
- If information was unavailable, state this clearly without speculating
- Do not reference any system internals, tool names, or databases
- Use standard medical terminology appropriate for a clinical audience"""


# ── Node 7: SYNTHESIZE (user message assembly template) ──────────────────────

SYNTHESIZE_USER_TEMPLATE = """\
Clinician's question: {user_query}

Clinical context: {task_summary}
{patient_context_section}\
{image_section}\
{tool_results_section}\
{error_section}\
{clarification_section}"""


# ── Node 7: DIRECT_CHAT (lightweight, no tool context) ──────────────────────

DIRECT_CHAT_PROMPT = """\
You are responding to a clinician (not the patient). Be concise.
{patient_context_section}
Query: {user_query}"""


# =============================================================================
# TASK-PATTERN MATCHING (deterministic termination — V3 spec §11)
# =============================================================================

TASK_PATTERNS: dict[str, dict] = {
    "drug_safety": {
        "keywords": ["safety", "warning", "boxed warning", "FDA"],
        "requires": {"check_drug_safety"},
    },
    "drug_interaction": {
        "keywords": ["interaction", "combining", "together with"],
        "requires": {"check_drug_interactions"},
    },
    "patient_lookup_and_review": {
        "keywords_all": ["patient", "chart|record|summary"],
        "requires": {"search_patient", "get_patient_chart"},
    },
    "prescribe": {
        "keywords": ["prescribe", "order", "start medication"],
        "requires": {"prescribe_medication"},
    },
    "literature_search": {
        "keywords": ["studies", "research", "evidence", "literature", "pubmed"],
        "requires": {"search_medical_literature"},
    },
    "clinical_trial": {
        "keywords": ["trial", "recruiting", "experimental"],
        "requires": {"find_clinical_trials"},
    },
    "allergy_document": {
        "keywords": ["allergy", "allergic", "document allergy"],
        "requires": {"add_allergy"},
    },
    "clinical_note": {
        "keywords": ["note", "document", "write note"],
        "requires": {"save_clinical_note"},
    },
}


# =============================================================================
# COMMON DRUG NAMES (~200 most prescribed generics)
#   Used by input_assembly for deterministic entity extraction.
#   Case-insensitive matching — model still extracts in TOOL_SELECT.
# =============================================================================

COMMON_DRUGS: frozenset[str] = frozenset({
    # Cardiovascular
    "lisinopril", "amlodipine", "metoprolol", "losartan", "atorvastatin",
    "simvastatin", "rosuvastatin", "pravastatin", "carvedilol", "valsartan",
    "enalapril", "ramipril", "diltiazem", "verapamil", "nifedipine",
    "hydrochlorothiazide", "furosemide", "spironolactone", "digoxin",
    "warfarin", "apixaban", "rivaroxaban", "dabigatran", "clopidogrel",
    "aspirin", "ticagrelor", "prasugrel", "heparin", "enoxaparin",
    # Diabetes
    "metformin", "glipizide", "glyburide", "glimepiride", "insulin",
    "sitagliptin", "linagliptin", "saxagliptin", "empagliflozin",
    "dapagliflozin", "canagliflozin", "liraglutide", "semaglutide",
    "dulaglutide", "pioglitazone",
    # Respiratory
    "albuterol", "fluticasone", "budesonide", "montelukast", "tiotropium",
    "ipratropium", "prednisone", "prednisolone", "dexamethasone",
    "methylprednisolone",
    # Antibiotics
    "amoxicillin", "azithromycin", "ciprofloxacin", "levofloxacin",
    "doxycycline", "metronidazole", "trimethoprim", "sulfamethoxazole",
    "cephalexin", "ceftriaxone", "clindamycin", "vancomycin", "gentamicin",
    "nitrofurantoin", "penicillin", "ampicillin", "piperacillin",
    # Pain / Anti-inflammatory
    "ibuprofen", "naproxen", "acetaminophen", "celecoxib", "meloxicam",
    "tramadol", "morphine", "oxycodone", "hydrocodone", "fentanyl",
    "gabapentin", "pregabalin", "duloxetine",
    # Psychiatric
    "sertraline", "escitalopram", "fluoxetine", "citalopram", "paroxetine",
    "venlafaxine", "bupropion", "mirtazapine", "trazodone", "amitriptyline",
    "quetiapine", "olanzapine", "risperidone", "aripiprazole", "lithium",
    "lamotrigine", "valproate", "carbamazepine", "clonazepam", "lorazepam",
    "diazepam", "alprazolam", "zolpidem",
    # GI
    "omeprazole", "pantoprazole", "esomeprazole", "lansoprazole",
    "famotidine", "ondansetron", "sucralfate", "lactulose",
    # Thyroid
    "levothyroxine", "methimazole",
    # Antimalarials / Immunology
    "hydroxychloroquine", "azathioprine", "mycophenolate", "tacrolimus",
    "cyclosporine",
    # Antivirals
    "acyclovir", "valacyclovir", "oseltamivir",
    # Cardiac-specific
    "amiodarone", "sotalol", "dofetilide", "flecainide", "dronedarone",
    "nitroglycerin", "isosorbide", "hydralazine",
    # Other common
    "allopurinol", "colchicine", "finasteride", "tamsulosin",
    "sildenafil", "tadalafil", "methotrexate",
})


# =============================================================================
# ACTION VERBS for input assembly entity extraction
# =============================================================================

ACTION_VERBS: frozenset[str] = frozenset({
    "prescribe", "order", "start", "initiate",
    "document", "record", "note", "write",
    "check", "search", "find", "look up", "lookup",
    "review", "get", "retrieve", "pull up",
    "save", "add", "create",
    "analyze", "interpret",
})


# =============================================================================
# SAFETY CONSTANTS
# =============================================================================

MAX_STEPS = 2           # Hard limit on tool loop iterations

# Tools that modify patient data — require explicit user approval
WRITE_TOOLS: frozenset[str] = frozenset({
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
})
