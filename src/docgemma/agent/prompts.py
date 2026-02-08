"""Prompt templates for DocGemma v2 agent nodes.

V2: 4-way triage, 10 tools, reasoning path, validation/fix-args.

Optimized for SLMs (Small Language Models):
- Direct imperatives, no politeness
- One-shot examples where helpful
- Minimal context, maximum clarity
- Structure over prose

Temperature Guide:
- 0.0-0.1: Structured output (JSON, classification)
- 0.3-0.4: Focused reasoning
- 0.5-0.6: Natural text generation
"""

from ..tools.registry import get_tools_for_prompt

# =============================================================================
# TEMPERATURE SETTINGS
# =============================================================================

TEMPERATURE = {
    "triage_router": 0.0,          # Classification - deterministic
    "thinking_mode": 0.3,          # Reasoning - focused
    "extract_tool_needs": 0.0,     # Structured output - deterministic
    "decompose_intent": 0.1,       # Structured output
    "plan_tool": 0.0,              # Tool selection - deterministic
    "fix_args": 0.1,               # Structured output - very deterministic
    "reasoning_continuation": 0.3, # Reasoning - focused
    "synthesize_response": 0.5,    # Free-form text
    "clarification": 0.4,          # Free-form question
}

# =============================================================================
# TRIAGE ROUTER (4-way classification)
# =============================================================================

TRIAGE_PROMPT = """Classify query into one route.

DIRECT = answer from medical knowledge alone (definitions, mechanisms, guidelines)
LOOKUP = needs exactly ONE tool call (drug safety, drug interactions, literature, clinical trials, patient search)
REASONING = needs clinical reasoning, may optionally need one tool
MULTI_STEP = needs 2+ different tool calls or sequential steps

Examples:
Query: What is hypertension?
route: direct

Query: Check FDA warnings for metformin
route: lookup
tool: check_drug_safety
query: metformin

Query: Check drug interactions between warfarin and aspirin
route: lookup
tool: check_drug_interactions
query: warfarin, aspirin

Query: Search PubMed for GLP-1 agonist weight loss studies
route: lookup
tool: search_medical_literature
query: GLP-1 agonist weight loss

Query: Find clinical trials for lung cancer
route: lookup
tool: find_clinical_trials
query: lung cancer

Query: Search for patient John Smith
route: lookup
tool: search_patient
query: John Smith

Query: Best antihypertensive for a patient with CKD stage 3?
route: reasoning

Query: Find warfarin safety warnings and check interactions with aspirin
route: multi_step

Query: Search for patient John Smith, get his chart, and check metformin safety
route: multi_step

---
Query: {user_input}
{context_line}"""


# =============================================================================
# THINKING MODE (Chain-of-thought)
# =============================================================================

THINKING_PROMPT = """Analyze this clinical query step by step. Consider:
- What clinical information is relevant?
- What data sources or tools might help?
- What are the key considerations?

Query: {user_input}
{context_line}"""


# =============================================================================
# EXTRACT TOOL NEEDS (Reasoning path)
# =============================================================================

EXTRACT_TOOL_NEEDS_PROMPT = """Does this reasoning need a tool call to give a better answer?

Rules:
- If the reasoning mentions checking, looking up, searching, or verifying something → needs_tool=true
- If the reasoning is complete and self-sufficient → needs_tool=false

Example 1 (needs tool):
Reasoning: Metformin has FDA warnings about lactic acidosis. I should check the current FDA boxed warnings.
needs_tool: true
tool: check_drug_safety
query: metformin

Example 2 (needs tool):
Reasoning: SGLT2 inhibitors show cardiovascular benefits. I should search PubMed for the latest evidence.
needs_tool: true
tool: search_medical_literature
query: SGLT2 inhibitors cardiovascular outcomes

Example 3 (needs tool):
Reasoning: Warfarin interacts with many drugs. I should verify the interaction with amiodarone.
needs_tool: true
tool: check_drug_interactions
query: warfarin, amiodarone

Example 4 (no tool):
Reasoning: ACE inhibitors are first-line for CKD with proteinuria per KDIGO guidelines. The answer is clear.
needs_tool: false

---
Reasoning: {reasoning}
Query: {user_input}

Tools:
{tools}"""


# =============================================================================
# REASONING CONTINUATION (After tool result)
# =============================================================================

REASONING_CONTINUATION_PROMPT = """Continue clinical reasoning with tool results.

Query: {user_input}
Initial reasoning: {reasoning}

Tool result:
{tool_result}

Integrate findings and complete the analysis."""


# =============================================================================
# INTENT DECOMPOSITION (up to 5 subtasks)
# =============================================================================

def get_decompose_prompt(user_input: str, reasoning: str) -> str:
    """Generate decomposition prompt with dynamic tool list."""
    tools = get_tools_for_prompt()
    return f"""Decompose into 1-5 subtasks with tools.

Tools:
{tools}

Example 1 (drug safety):
Query: Check if metformin has any FDA warnings
subtask_1: Look up FDA boxed warnings for metformin
tool_1: check_drug_safety

Example 2 (drug interactions):
Query: Patient on warfarin needs azithromycin. Check interactions.
subtask_1: Check drug interactions between warfarin and azithromycin
tool_1: check_drug_interactions

Example 3 (EHR + drug check):
Query: Find patient John Smith and check his chart, then check safety of his metformin
subtask_1: Search for patient John Smith
tool_1: search_patient
subtask_2: Get patient chart
tool_2: get_patient_chart
subtask_3: Check drug safety for metformin
tool_3: check_drug_safety

Example 4 (prescription workflow):
Query: Prescribe lisinopril 10mg daily for patient abc-123 and document it
subtask_1: Prescribe lisinopril for patient
tool_1: prescribe_medication
subtask_2: Save clinical note about prescription
tool_2: save_clinical_note

---
Query: {user_input}

Context: {reasoning}

Return subtask_1, tool_1, and optionally subtask_2-5 with tool_2-5."""


# =============================================================================
# TOOL PLANNING (all 10 tools)
# =============================================================================

def get_plan_prompt(intent: str, suggested_tool: str) -> str:
    """Generate tool planning prompt with dynamic tool list."""
    tools = get_tools_for_prompt()
    return f"""Select tool and fill arguments. Output patient_id FIRST for EHR tools.

Task: {intent}
Suggested: {suggested_tool}

Tools:
{tools}

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

Example 8 (prescription — use medication_name NOT drug_name):
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

---
Return tool_name, then patient_id (extract from task or null), then remaining arguments."""


# =============================================================================
# FIX ARGS (Validation failure recovery)
# =============================================================================

FIX_ARGS_PROMPT = """Fix the tool arguments. The previous call had a validation error.

Tool: {tool_name}
Previous args: {previous_args}
Error: {validation_error}

Fix the arguments to resolve the error."""


# =============================================================================
# RESPONSE SYNTHESIS (all routes converge here)
# =============================================================================

SYNTHESIS_PROMPT = """Clinical decision support response.

Query: {user_input}
{reasoning_line}
{tool_results_line}

Respond concisely. Use medical abbreviations. Cite sources if available."""


# =============================================================================
# CLARIFICATION REQUEST
# =============================================================================

CLARIFICATION_PROMPT = """Need more information.

Query: {user_input}
Missing: {missing_info}

Ask one specific question."""
