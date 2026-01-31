# DocGemma Connect - Implementation Guide

## Project Overview

**Competition:** [MedGemma Impact Challenge](https://www.kaggle.com/competitions/med-gemma-impact-challenge) on Kaggle
**Deadline:** February 24, 2026
**Prize Pool:** $100,000

DocGemma Connect is an agentic medical AI assistant designed to help healthcare professionals in resource-limited environments. It uses a decision-tree architecture powered by MedGemma 4B to minimize LLM compute burden while maintaining robust capabilities.

### Core Philosophy
- Narrow down LLM workload through structured decision trees
- LLM acts as logic engine + response synthesizer (not doing everything)
- Shift complexity from the model to deterministic code ("Cognitive Offloading")
- Designed for resource-limited environments (offline-capable clinics)

### Target User
- **Medical Experts** (physicians, nurses, clinical staff)
- Technical language, full tool access, EHR read/write capabilities

### Technology Stack
- **LLM:** MedGemma 1.5 4B IT (instruction-tuned, multimodal)
- **Structured Output:** Outlines library (constrained generation for reliable JSON)
- **Agent Orchestration:** LangGraph (stateful workflows and decision graphs)
- **Tool Protocol:** MCP (Model Context Protocol)

---

## Architecture Overview

The agent processes each turn through a streamlined pipeline:

1. **Image Detection** — Check if medical images are attached
2. **Complexity Routing** — Direct answer vs. tool-assisted response
3. **Intent Decomposition** — Break complex queries into subtasks
4. **Agentic Loop** — Plan → Execute → Check for each subtask
5. **Response Synthesis** — Generate final clinical response

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| User type | Expert only | Simplified scope, technical responses |
| Image processing | Hybrid: detect pre-loop (code), analyze via tool (LLM) | Metadata informs routing; analysis is lazy/on-demand |
| Loop termination | Deterministic flags + retry limit | 4B models fail at self-reflection ("am I done?") |
| Multi-intent queries | Decompose into subtasks | Handle sequentially for reliability |

---

## State Object

```python
from typing import Literal, TypedDict

class DocGemmaState(TypedDict):
    # === Turn-level inputs ===
    user_input: str
    image_present: bool
    image_data: bytes | None  # raw image, not yet analyzed
    
    # === Agentic loop state ===
    subtasks: list[dict]             # decomposed intents
    current_subtask_index: int
    tool_results: list[dict]         # accumulated findings
    loop_iterations: int
    tool_retries: int
    
    # === Control flags ===
    needs_more_info: bool            # requires user clarification
    needs_more_action: bool          # loop should continue
    
    # === Output ===
    final_response: str | None
```

---

## Decision Tree Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PER-TURN PROCESSING                           │
│                                                                  │
│  ┌──────────────┐                                                │
│  │ Image        │ → image_present: bool                          │
│  │ Detection    │   image_data: bytes | None                     │
│  │ (code only)  │                                                │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐    "DIRECT"                                    │
│  │ Complexity   │────────→ [Skip loop, answer directly]          │
│  │ Router       │                                                │
│  └──────┬───────┘                                                │
│         │ "COMPLEX"                                              │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │ Decompose    │ → list of subtasks                             │
│  │ Intent       │                                                │
│  └──────┬───────┘                                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────┐                 │
│  │            AGENTIC LOOP                      │                │
│  │                                              │                │
│  │  ┌─────────────────────────────────────┐    │                 │
│  │  │ Plan: Select tool for subtask       │    │                 │
│  │  └─────────────┬───────────────────────┘    │                 │
│  │                ▼                            │                 │
│  │  ┌─────────────────────────────────────┐    │                 │
│  │  │ Execute: Call MCP tool              │    │                 │
│  │  └─────────────┬───────────────────────┘    │                 │
│  │                ▼                            │                 │
│  │  ┌─────────────────────────────────────┐    │                 │
│  │  │ Check Result:                       │    │                 │
│  │  │  - success → next subtask or exit   │    │                 │
│  │  │  - needs_more_action → loop back    │    │                 │
│  │  │  - needs_user_input → exit to ask   │    │                 │
│  │  │  - error → retry (max 3) or exit    │    │                 │
│  │  └─────────────────────────────────────┘    │                 │
│  └──────────────────────────────────────────────┘                │
│                   │                                              │
│                   ▼                                              │
│  ┌──────────────────────────────────────────┐                    │
│  │         RESPONSE SYNTHESIS                │                   │
│  │  - Clinical precision, technical language │                   │
│  │  - Include citations/sources              │                   │
│  │  - OR request clarification if needed     │                   │
│  └──────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Node Specifications

### Node 1: Image Detection

| Property | Value |
|----------|-------|
| **Type** | Pure code |
| **Input** | Request metadata / file attachments |
| **Output** | `image_present: bool`, `image_data: bytes | None` |

**Implementation:**
```python
SUPPORTED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg", 
    "image/dicom",
    "application/dicom",
}

def detect_image(attachments: list[dict]) -> tuple[bool, bytes | None]:
    for attachment in attachments:
        mime_type = attachment.get("mime_type", "")
        if mime_type in SUPPORTED_IMAGE_TYPES:
            return True, attachment.get("data")
    return False, None
```

**Note:** Image TYPE classification (xray vs CT vs MRI) happens later via the `analyze_medical_image` tool, which uses MedGemma vision.

---

### Node 2: Complexity Router

| Property | Value |
|----------|-------|
| **Type** | LLM (constrained via Outlines) |
| **Input** | User message, image_present flag |
| **Output** | `Literal["direct", "complex"]` |

**Outlines Schema:**
```python
from pydantic import BaseModel
from typing import Literal

class ComplexityClassification(BaseModel):
    complexity: Literal["direct", "complex"]
    reasoning: str  # brief justification
```

**Routing Logic:**
- `direct`: Greetings, thanks, simple factual questions answerable from training, basic clinical knowledge
- `complex`: Requires tools, image analysis, multi-step reasoning, external data lookup

**Prompt:**
```
Classify if this clinical query needs external tools/data or can be answered directly.

DIRECT examples: "Hello", "Thank you", "What's the mechanism of action for metformin?", "Define hypertension"
COMPLEX examples: "Analyze this X-ray", "Check drug interactions for...", "Pull patient 402's records", "Find clinical trials for TNBC"

Query: {user_input}
Image attached: {image_present}

If an image is attached, classify as COMPLEX.
```

---

### Node 3: Decompose Intent

| Property | Value |
|----------|-------|
| **Type** | LLM (structured output via Outlines) |
| **Runs** | Only if complexity == "complex" |
| **Input** | User message, image_present flag |
| **Output** | List of subtasks |

**Outlines Schema:**
```python
class Subtask(BaseModel):
    intent: str  # brief description
    requires_tool: str | None  # suggested tool or None
    context: str  # relevant extracted info

class DecomposedIntent(BaseModel):
    subtasks: list[Subtask]
    requires_clarification: bool
    clarification_question: str | None
```

**Example Decomposition:**

User: *"CXR shows what looks like a mass in the right upper lobe. Patient ID 555. Pull their smoking history and find current screening guidelines for lung cancer."*

```json
{
  "subtasks": [
    {
      "intent": "Analyze the chest X-ray for mass characterization",
      "requires_tool": "analyze_medical_image",
      "context": "right upper lobe mass noted"
    },
    {
      "intent": "Retrieve patient 555 smoking history",
      "requires_tool": "get_patient_record", 
      "context": "patient ID 555"
    },
    {
      "intent": "Find lung cancer screening guidelines",
      "requires_tool": "search_medical_literature",
      "context": "lung cancer screening guidelines"
    }
  ],
  "requires_clarification": false,
  "clarification_question": null
}
```

---

### Node 4: Plan - Tool Selection (Agentic Loop)

| Property | Value |
|----------|-------|
| **Type** | LLM (constrained via Outlines) |
| **Runs** | Each loop iteration |
| **Input** | Current subtask, available tools, accumulated results |
| **Output** | Tool name + arguments |

**Outlines Schema:**
```python
class ToolCall(BaseModel):
    tool_name: Literal[
        "check_drug_safety",
        "search_medical_literature",
        "check_drug_interactions",
        "find_clinical_trials",
        "get_patient_record",
        "update_patient_record",
        "analyze_medical_image",
    ]
    arguments: dict
    reasoning: str
```

**Available Tools:**
```python
AVAILABLE_TOOLS = [
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "get_patient_record",
    "update_patient_record",
    "analyze_medical_image",
]
```

---

### Node 5: Execute Tool (Agentic Loop)

| Property | Value |
|----------|-------|
| **Type** | Pure code (MCP call) |
| **Runs** | Each loop iteration |
| **Input** | Tool name, arguments |
| **Output** | Tool result or error |

**Implementation:** Use existing MCP server infrastructure in `docgemma/tools/server.py`

---

### Node 6: Check Result (Agentic Loop)

| Property | Value |
|----------|-------|
| **Type** | Pure code |
| **Runs** | After each tool execution |
| **Input** | Tool result, loop state |
| **Output** | Control flow decision |

**Logic:**
```python
def check_result(
    tool_result: dict,
    state: DocGemmaState
) -> Literal["success", "needs_more_action", "needs_user_input", "error"]:
    
    if tool_result.get("error"):
        return "error"
    
    if tool_result.get("needs_user_input"):
        return "needs_user_input"
    
    if tool_result.get("needs_more_action"):
        return "needs_more_action"
    
    return "success"
```

**Loop Control:**
```python
MAX_ITERATIONS_PER_SUBTASK = 3
MAX_TOOL_RETRIES = 3

def should_continue_loop(state: DocGemmaState, result_status: str) -> bool:
    if result_status == "needs_user_input":
        return False  # exit to ask user
    
    if result_status == "error":
        if state["tool_retries"] < MAX_TOOL_RETRIES:
            state["tool_retries"] += 1
            return True  # retry
        return False  # give up
    
    if result_status == "needs_more_action":
        if state["loop_iterations"] < MAX_ITERATIONS_PER_SUBTASK:
            state["loop_iterations"] += 1
            return True
        return False  # max iterations
    
    # success - check for more subtasks
    if state["current_subtask_index"] < len(state["subtasks"]) - 1:
        state["current_subtask_index"] += 1
        state["loop_iterations"] = 0
        state["tool_retries"] = 0
        return True  # next subtask
    
    return False  # all done
```

---

### Node 7: Response Synthesis

| Property | Value |
|----------|-------|
| **Type** | LLM (free-form generation) |
| **Runs** | Once at end of turn |
| **Input** | Tool results, original query |
| **Output** | Final response string |

**Prompt Template:**
```python
def get_synthesis_prompt(state: DocGemmaState) -> str:
    return f"""
    You are a clinical decision support system responding to a healthcare professional.
    
    Respond with clinical precision using standard medical terminology.
    Use abbreviations appropriately (e.g., HTN, DM2, BID, PRN).
    Focus on actionable clinical insights.
    Be concise - clinicians don't need hand-holding.
    Include source citations where applicable.
    
    Original query: {state["user_input"]}
    
    Findings from tools:
    {format_tool_results(state["tool_results"])}
    
    Synthesize a helpful clinical response.
    If information is incomplete, acknowledge limitations and suggest next steps.
    """
```

**Clarification Request (if needs_user_input):**
```python
def get_clarification_prompt(state: DocGemmaState) -> str:
    return f"""
    I need more information to complete this request.
    
    Original query: {state["user_input"]}
    
    What's missing: {state.get("missing_info", "specific details")}
    
    Generate a concise, specific question to get the information needed.
    Be direct - this is a clinical setting.
    """
```

---

## Tool Inventory

### Existing Tools (Already Implemented)

| Tool | Source API | Input Schema | Purpose |
|------|------------|--------------|---------|
| `check_drug_safety` | OpenFDA | `DrugSafetyInput` | FDA boxed warnings lookup |
| `search_medical_literature` | PubMed | `MedicalLiteratureInput` | Search medical articles |
| `check_drug_interactions` | OpenFDA | `DrugInteractionsInput` | Drug-drug interaction check |
| `find_clinical_trials` | ClinicalTrials.gov | `ClinicalTrialsInput` | Find recruiting trials |

### Tools to Implement

| Tool | Type | Input Schema | Purpose |
|------|------|--------------|---------|
| `get_patient_record` | Local (pseudo-EHR) | `PatientRecordsInput` | Fetch patient data |
| `update_patient_record` | Local (pseudo-EHR) | TBD | Update patient data |
| `analyze_medical_image` | MedGemma Vision | `ImageAnalysisInput` | Analyze X-ray/CT/MRI |

### Image Analysis Tool Schema

```python
class ImageAnalysisInput(BaseModel):
    """Input for medical image analysis."""
    image_data: str  # base64 encoded
    clinical_context: str | None = None  # e.g., "patient complains of chest pain"

class ImageAnalysisOutput(BaseModel):
    """Output from medical image analysis."""
    image_type: Literal["chest_xray", "ct_scan", "mri", "pathology", "dermatology", "unknown"]
    findings: list[str]  # structured findings
    impression: str      # summary interpretation  
    confidence: Literal["high", "medium", "low"]
    requires_specialist_review: bool
```

---

## LangGraph Implementation Skeleton

```python
from typing import Literal
from langgraph.graph import StateGraph, END
from docgemma.state import DocGemmaState

# Create the graph
workflow = StateGraph(DocGemmaState)

# === Add Nodes ===
workflow.add_node("image_detection", image_detection_node)
workflow.add_node("complexity_router", complexity_router_node)
workflow.add_node("decompose_intent", decompose_intent_node)
workflow.add_node("plan_tool", plan_tool_node)
workflow.add_node("execute_tool", execute_tool_node)
workflow.add_node("check_result", check_result_node)
workflow.add_node("synthesize_response", synthesize_response_node)

# === Entry Point ===
workflow.set_entry_point("image_detection")

# === Flow ===
workflow.add_edge("image_detection", "complexity_router")

def route_complexity(state: DocGemmaState) -> str:
    if state.get("complexity") == "direct":
        return "synthesize_response"
    return "decompose_intent"

workflow.add_conditional_edges("complexity_router", route_complexity)
workflow.add_edge("decompose_intent", "plan_tool")

# === Agentic Loop ===
workflow.add_edge("plan_tool", "execute_tool")
workflow.add_edge("execute_tool", "check_result")

def route_result(state: DocGemmaState) -> str:
    result_status = state.get("last_result_status")
    
    if result_status == "needs_user_input":
        return "synthesize_response"
    
    if result_status == "error" and state["tool_retries"] < 3:
        return "execute_tool"  # retry
    
    if result_status == "needs_more_action" and state["loop_iterations"] < 3:
        return "plan_tool"  # continue loop
    
    if result_status == "success":
        if state["current_subtask_index"] < len(state["subtasks"]) - 1:
            return "plan_tool"  # next subtask
    
    return "synthesize_response"  # done or give up

workflow.add_conditional_edges("check_result", route_result)

# === Terminal ===
workflow.add_edge("synthesize_response", END)

# Compile
app = workflow.compile()
```

---

## File Structure

```
docgemma/
├── __init__.py
├── agent/
│   ├── __init__.py
│   ├── graph.py          # LangGraph workflow definition
│   ├── state.py          # DocGemmaState TypedDict
│   └── nodes/
│       ├── __init__.py
│       ├── routing.py    # image_detection, complexity_router
│       ├── planning.py   # decompose_intent, plan_tool
│       ├── execution.py  # execute_tool, check_result
│       └── synthesis.py  # synthesize_response
├── schemas/
│   ├── __init__.py
│   ├── classification.py # Outlines schemas for LLM nodes
│   └── tools.py          # Tool input/output schemas
├── tools/
│   ├── __init__.py       # (exists)
│   ├── server.py         # (exists) MCP server
│   ├── drug_safety.py    # (exists)
│   ├── drug_interactions.py  # (exists)
│   ├── medical_literature.py # (exists)
│   ├── clinical_trials.py    # (exists)
│   ├── patient_records.py    # TODO: implement
│   └── image_analysis.py     # TODO: implement
├── prompts/
│   ├── __init__.py
│   ├── complexity.py     # prompts for complexity routing
│   ├── decompose.py      # prompts for intent decomposition
│   ├── tool_select.py    # prompts for tool selection
│   └── synthesis.py      # prompts for response generation
└── config.py             # constants, limits, etc.
```

---

## Constants and Limits

```python
# config.py

# Loop limits (critical for 4B model stability)
MAX_ITERATIONS_PER_SUBTASK = 3
MAX_TOOL_RETRIES = 3
MAX_SUBTASKS = 5

# Model settings
MODEL_ID = "google/medgemma-1.5-4b-it"
MAX_NEW_TOKENS = 512
TEMPERATURE = 0.0  # deterministic for medical accuracy

# Available tools
AVAILABLE_TOOLS = [
    "check_drug_safety",
    "search_medical_literature",
    "check_drug_interactions",
    "find_clinical_trials",
    "get_patient_record",
    "update_patient_record",
    "analyze_medical_image",
]
```

---

## Implementation Priority

### Phase 1: Core Pipeline (Week 1)
1. ✅ Tool infrastructure (MCP server exists)
2. [ ] State object and LangGraph skeleton
3. [ ] Image detection node (pure code)
4. [ ] Complexity router node (Outlines)
5. [ ] Basic synthesis node

### Phase 2: Agentic Loop (Week 1-2)
1. [ ] Intent decomposition node
2. [ ] Tool selection node (Outlines constrained)
3. [ ] Result checking logic
4. [ ] Loop control flow

### Phase 3: Missing Tools (Week 2)
1. [ ] `get_patient_record` / `update_patient_record`
2. [ ] `analyze_medical_image` (MedGemma vision wrapper)
3. [ ] Pseudo-EHR data store

### Phase 4: Polish (Week 3)
1. [ ] UI for demo video
2. [ ] Pre-cache hard queries for demo
3. [ ] Technical writeup
4. [ ] 3-minute video recording

---

## Key Reminders for 4B Model

1. **Keep prompts short** — Under 200 tokens for system prompts
2. **Use Outlines everywhere** — Don't ask for JSON, force it
3. **Deterministic stopping** — Never ask "are you done?"
4. **One decision per node** — Don't combine classification tasks
5. **Filter context aggressively** — Only pass what's needed for each node
