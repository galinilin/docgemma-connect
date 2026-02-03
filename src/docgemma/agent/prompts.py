"""Prompt templates for DocGemma agent nodes.

All prompts are centralized here for easy optimization and iteration.
Each prompt includes documentation on its purpose and expected variables.

Temperature Guide for SLMs:
- 0.0-0.2: Deterministic, structured output (classification, JSON)
- 0.3-0.5: Focused reasoning with some exploration
- 0.5-0.7: Natural language generation with variation
"""

# =============================================================================
# TEMPERATURE SETTINGS
# =============================================================================
# Centralized temperature config for each node type.
# SLMs are sensitive to temperature - lower is better for structured output.

TEMPERATURE = {
    "complexity_router": 0.1,   # Classification task - very deterministic
    "thinking_mode": 0.4,       # Reasoning - some exploration allowed
    "decompose_intent": 0.2,    # Structured output - low temp
    "plan_tool": 0.1,           # Tool selection - deterministic
    "synthesize_response": 0.6, # Free-form text - natural variation
    "clarification": 0.5,       # Free-form question - natural
    "direct_response": 0.5,     # Free-form answer - natural variation
}

# =============================================================================
# COMPLEXITY ROUTER
# =============================================================================
# Purpose: Classify whether a query needs tools/complex processing or can be
#          answered directly from model knowledge.
# Variables: {user_input}, {image_present}
# Output: ComplexityClassification schema (complexity: "direct" | "complex")

COMPLEXITY_PROMPT = """Classify if this clinical query needs external tools/data or can be answered directly.

DIRECT: Greetings, thanks, simple factual questions from medical knowledge, basic definitions.
COMPLEX: Requires tools, image analysis, multi-step reasoning, external data lookup, patient records.

Query: `{user_input}`"""


# =============================================================================
# THINKING MODE
# =============================================================================
# Purpose: Generate reasoning/chain-of-thought for complex queries before
#          decomposing into subtasks. Helps the model think through the problem.
# Variables: {user_input}
# Output: ThinkingOutput schema (reasoning: str)

THINKING_PROMPT = """Extensively think and reason about the following user prompt.

Query: `{user_input}`
"""


# =============================================================================
# INTENT DECOMPOSITION
# =============================================================================
# Purpose: Break down a complex query into actionable subtasks, each mapping
#          to a specific tool call.
# Variables: {user_input}, {image_present}, {reasoning}, {max_subtasks}
# Output: DecomposedIntent schema (subtasks list, requires_clarification, etc.)

DECOMPOSE_PROMPT = """Break down this clinical query into actionable subtasks.

Available tools:
- check_drug_safety: FDA boxed warnings lookup
- search_medical_literature: PubMed article search
- check_drug_interactions: Drug-drug interaction check
- find_clinical_trials: Search recruiting trials
- get_patient_record: Fetch patient data by ID
- update_patient_record: Add diagnosis/medication/note to patient record
- analyze_medical_image: Analyze X-ray/CT/MRI images

Query: `{user_input}`
Image attached: {image_present}

Reasoning context:
{reasoning}

Decompose into 1-{max_subtasks} subtasks. Each subtask should map to one tool call."""


# =============================================================================
# TOOL PLANNING
# =============================================================================
# Purpose: Select the best tool and arguments for a specific subtask.
# Variables: {intent}, {context}, {suggested_tool}, {previous_results}, {tools}
# Output: ToolCall schema (tool_name, arguments, reasoning)

PLAN_PROMPT = """Select the best tool for this subtask.

Subtask: {intent}
Context: {context}
Suggested tool: {suggested_tool}

Previous results this turn:
{previous_results}

Available tools: {tools}

Select the tool and provide arguments. Use "none" if no tool needed."""


# =============================================================================
# RESPONSE SYNTHESIS
# =============================================================================
# Purpose: Synthesize a final clinical response from tool results.
# Variables: {user_input}, {tool_results}
# Output: Free-form text response

SYNTHESIS_PROMPT = """You are a clinical decision support system responding to a healthcare professional.

Original query: `{user_input}`

Findings from tools:
{tool_results}

Synthesize a helpful clinical response:
- Use standard medical terminology and abbreviations (HTN, DM2, BID, PRN)
- Be concise - clinicians don't need hand-holding
- Include source citations where applicable
- If information is incomplete, acknowledge limitations"""


# =============================================================================
# CLARIFICATION REQUEST
# =============================================================================
# Purpose: Generate a question to get missing information from the user.
# Variables: {user_input}, {missing_info}
# Output: Free-form text question

CLARIFICATION_PROMPT = """I need more information to complete this request.

Original query: `{user_input}`
What's missing: {missing_info}

Generate a concise, specific question to get the information needed."""


# =============================================================================
# DIRECT RESPONSE
# =============================================================================
# Purpose: Generate a direct response for simple queries (no tools needed).
# Variables: {user_input}
# Output: Free-form text response

DIRECT_RESPONSE_PROMPT = """You are a clinical decision support system. Respond concisely to this query:

`{user_input}`"""
