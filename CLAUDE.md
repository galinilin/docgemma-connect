# DocGemma Connect

## Overview

Medical AI assistant for the **Google MedGemma Impact Challenge** on Kaggle.

- **Competition:** https://www.kaggle.com/competitions/med-gemma-impact-challenge
- **Deadline:** February 24, 2026
- **Prize Pool:** $100,000
- **Model:** MedGemma 1.5 4B IT (instruction-tuned, multimodal)

## Philosophy

- **Cognitive Offloading**: Shift complexity from the 4B model to deterministic code
- Decision-tree architecture minimizes LLM compute burden
- LLM acts as logic engine + response synthesizer (not doing everything)
- Designed for resource-limited environments (offline-capable clinics)
- Target user: Medical experts (technical language, full tool access)

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | MedGemma 1.5 4B IT |
| Structured Output | Outlines (constrained generation) |
| Agent Orchestration | LangGraph |
| Tool Protocol | MCP |
| API Server | FastAPI + WebSockets |
| Package Manager | uv |

## Project Structure

```
docgemma-connect/
├── src/docgemma/
│   ├── __init__.py
│   ├── model.py              # DocGemma remote client (vLLM/OpenAI API + system prompt + thinking filter)
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py          # DocGemmaState TypedDict
│   │   ├── schemas.py        # Pydantic schemas (TriageDecision, ToolCallV2, DecomposedIntentV2, etc.)
│   │   ├── prompts.py        # SYSTEM_PROMPT + node prompts (TRIAGE, THINKING, SYNTHESIS, etc.)
│   │   ├── nodes.py          # All 18 node implementations
│   │   └── graph.py          # LangGraph workflow + GraphConfig + GRAPH_CONFIG + build_graph()
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app factory, lifespan (wires SYSTEM_PROMPT → DocGemma)
│   │   ├── config.py         # Configuration from env vars
│   │   ├── models/           # Pydantic request/response models
│   │   │   ├── events.py     # WebSocket event types (ClinicalTrace, CompletionEvent, etc.)
│   │   │   ├── requests.py
│   │   │   ├── responses.py
│   │   │   └── session.py
│   │   ├── routers/          # API endpoint handlers
│   │   │   ├── health.py     # /api/health
│   │   │   ├── sessions.py   # /api/sessions/* + WebSocket (persists image metadata)
│   │   │   ├── tools.py      # /api/tools
│   │   │   └── patients.py   # /api/patients/* (EHR UI endpoints)
│   │   └── services/         # Business logic
│   │       ├── agent_runner.py   # Graph-agnostic WebSocket streaming (consumes GraphConfig)
│   │       └── session_store.py  # In-memory session management
│   └── tools/
│       ├── __init__.py
│       ├── registry.py       # ToolRegistry + global registrations
│       ├── schemas.py        # Pydantic schemas for all tools
│       ├── drug_safety.py    # OpenFDA boxed warnings
│       ├── drug_interactions.py  # RxNav drug interactions
│       ├── medical_literature.py # PubMed search
│       ├── clinical_trials.py    # ClinicalTrials.gov search
│       └── fhir_store/       # Local FHIR JSON store
│           ├── store.py      # FhirJsonStore class (get/post interface)
│           ├── search.py     # Patient search by name/DOB
│           ├── chart.py      # Clinical summary builder
│           ├── allergies.py  # Allergy documentation
│           ├── medications.py # Medication orders
│           ├── notes.py      # Clinical notes
│           └── seed.py       # Seed from Synthea bundles
├── doc/
│   ├── DOCGEMMA_IMPLEMENTATION_GUIDE.md  # v1 architecture spec (see FLOWCHART_V2 for current)
│   ├── DOCGEMMA_FLOWCHART_V2.md          # v2 Mermaid diagram + architecture changes
│   └── DOCGEMMA_TEST_CASES_V2.md         # 120 test cases (YAML)
├── main.py                   # Model test script
├── test_agent.py             # Agent pipeline test script
├── test_tool_planning.py     # 50 prompt engineering test cases
├── test_tools.py
├── pyproject.toml
└── .env                      # Environment (RunPod endpoint)
```

## Implemented Tools

| Tool | API | Status |
|------|-----|--------|
| `check_drug_safety` | OpenFDA | ✅ Done |
| `search_medical_literature` | PubMed | ✅ Done |
| `check_drug_interactions` | RxNav | ✅ Done |
| `find_clinical_trials` | ClinicalTrials.gov | ✅ Done |
| `search_patient` | Local FHIR JSON store | ✅ Done |
| `get_patient_chart` | Local FHIR JSON store | ✅ Done |
| `add_allergy` | Local FHIR JSON store | ✅ Done |
| `prescribe_medication` | Local FHIR JSON store | ✅ Done |
| `save_clinical_note` | Local FHIR JSON store | ✅ Done |
| `analyze_medical_image` | MedGemma Vision | ❌ TODO |

## Agent Pipeline (v2 — 4-Way Triage)

```
                                        ┌─ "direct"     → Synthesize (DIRECT_CHAT_PROMPT) → END
                                        │
Image Detection → Context Assembler →   │─ "lookup"     → Validate → Execute → Check → Synthesize → END
                                  Triage│
                                  Router│─ "reasoning"  → Think → Extract Tool Needs → [Execute → Continue Reasoning] → Synthesize → END
                                        │
                                        └─ "multi_step" → Decompose → Plan → Validate → Execute → Assess → Synthesize → END
```

18-node graph (all implemented in `agent/nodes.py`):

| Node | Type | Route(s) | Purpose |
|------|------|----------|---------|
| Image Detection | Pure code | all | Detect medical image attachments |
| Clinical Context Assembler | Pure code | all | Gather patient context, image metadata |
| Triage Router | LLM + Outlines | all | 4-way route: direct/lookup/reasoning/multi_step |
| Fast Validate | Pure code | lookup | Validate tool args from triage output |
| Fast Execute | Pure code (MCP) | lookup | Execute single tool (interrupt point) |
| Fast Check | Pure code | lookup | Check result, retry if needed |
| Fix Args | LLM + Outlines | lookup, multi_step | Reformulate invalid tool args |
| Thinking Mode | LLM (free-form) | reasoning | Clinical reasoning chain (max 1024 tokens) |
| Extract Tool Needs | LLM + Outlines | reasoning | Identify if reasoning needs a tool call |
| Reasoning Execute | Pure code (MCP) | reasoning | Execute tool for reasoning path (interrupt point) |
| Reasoning Continuation | LLM (free-form) | reasoning | Reason over tool results |
| Decompose Intent | LLM + Outlines | multi_step | Break query into subtasks (max 5) |
| Plan Tool | LLM + Outlines | multi_step | Select tool for current subtask |
| Loop Validate | Pure code | multi_step | Validate tool call before execution |
| Loop Execute | Pure code (MCP) | multi_step | Execute tool in agentic loop (interrupt point) |
| Assess Result | Pure code | multi_step | Success/retry/skip/error decision |
| Error Handler | Pure code | multi_step | retry_same / retry_reformulate / skip_subtask |
| Synthesize Response | LLM (free-form) | all | Generate final clinical response |

**3 interrupt points** (tool approval): fast_execute, reasoning_execute, loop_execute
**1 terminal node**: synthesize_response (handles all routes, including direct)

## Model Client (`model.py`)

```python
from docgemma import DocGemma
from docgemma.agent.prompts import SYSTEM_PROMPT

# Initialize with system prompt (auto-prepended to every API call)
model = DocGemma(system_prompt=SYSTEM_PROMPT)

# Free-form generation (with conversation history)
response = model.generate("What is hypertension?", messages=history)

# Streaming generation
async for chunk in model.generate_stream("Explain HTN", messages=history):
    print(chunk, end="")

# Structured generation (vLLM guided decoding)
from pydantic import BaseModel
class Result(BaseModel):
    answer: str
    confidence: float

result = model.generate_outlines(prompt, Result, messages=history)
```

**Key features:**
- `system_prompt` parameter → `_build_messages()` prepends system message to every API call
- `messages` parameter on `generate()`, `generate_stream()`, `generate_outlines()` → real multi-turn conversation context
- Thinking token filtering: `<unused94>...<unused95>` stripped automatically (regex for sync, stateful filter for streaming)

## Commands

```bash
# Install dependencies (CPU)
uv sync --extra cpu

# Install dependencies (CUDA 12.8)
uv sync --extra cu128

# Run test script
uv run python main.py

# Run tool tests
uv run python test_tools.py

# Run agent tests
uv run python test_agent.py

# Start API server
uv run docgemma-serve
```

## API Server

The API server provides REST and WebSocket endpoints for the frontend.

**Environment Variables:**
- `DOCGEMMA_ENDPOINT` - vLLM/OpenAI API endpoint
- `DOCGEMMA_API_KEY` - Authentication token
- `DOCGEMMA_MODEL` - Model ID (default: `google/medgemma-1.5-4b-it`)
- `DOCGEMMA_HOST` - Server host (default: `0.0.0.0`)
- `DOCGEMMA_PORT` - Server port (default: `8000`)
- `DOCGEMMA_LOAD_MODEL` - Load model on startup (default: `true`)
- `DOCGEMMA_TOOL_APPROVAL` - Enable tool approval flow (default: `true`)
- `FHIR_DATA_DIR` - Local FHIR JSON store path (default: `data/fhir/`)

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check + model status |
| POST | `/api/sessions` | Create new session |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/{id}` | Get session details |
| DELETE | `/api/sessions/{id}` | Delete session |
| GET | `/api/sessions/{id}/messages` | Get conversation history |
| WS | `/api/sessions/{id}/ws` | WebSocket for real-time events |
| GET | `/api/tools` | List available tools |

**WebSocket Events (Server → Client):**
- `node_start` / `node_end` - Node execution lifecycle
- `tool_approval_request` - Request user approval for tool
- `tool_execution_start` / `tool_execution_end` - Tool execution lifecycle
- `streaming_text` - Streaming response text
- `completion` - Final response ready (includes `clinical_trace` for UI)
- `error` - Error occurred

**Clinical Trace (`completion` event):**
The `completion` event includes a `clinical_trace` object for frontend display:
```python
class ClinicalTrace:
    steps: list[TraceStep]  # thought, tool_call, synthesis
    total_duration_ms: float
    tools_consulted: int
```
Built by `AgentRunner._build_clinical_trace()` using `TOOL_CLINICAL_LABELS` for user-friendly names.

## Known Issues & Fixes

### LangGraph Checkpoint State Leakage
**Problem**: With `MemorySaver` checkpointer, state fields like `final_response` persist across turns, causing stale responses.

**Fix**: `GraphConfig.make_initial_state()` resets all fields + `GraphConfig.terminal_nodes` tells `agent_runner.py` which nodes produce final output + `completion_emitted` flag prevents duplicate events.

### Terminal Node
Only `synthesize_response` produces `final_response` (handles all 4 routes, including direct via `DIRECT_CHAT_PROMPT`).

## 4B Model Guidelines

1. **Keep prompts short** — Under 200 tokens for system prompts
2. **Use Outlines everywhere** — Don't ask for JSON, force it
3. **Deterministic stopping** — Never ask "are you done?"
4. **One decision per node** — Don't combine classification tasks
5. **Filter context aggressively** — Only pass what's needed per node

## Implementation Priority

### Phase 1: Core Pipeline ✅
- [x] State object (`DocGemmaState` TypedDict)
- [x] LangGraph workflow skeleton
- [x] Image detection node
- [x] Complexity router node
- [x] Basic synthesis node

### Phase 2: Agentic Loop ✅
- [x] Intent decomposition node
- [x] Tool selection node (Outlines constrained)
- [x] Result checking logic
- [x] Loop control flow

### Phase 3: API & Frontend ✅
- [x] FastAPI server with REST + WebSocket
- [x] Session management (in-memory)
- [x] Real-time agent state streaming
- [x] Vue 3 frontend with inline clinical trace display
- [x] Tool approval flow

### Phase 4: EHR Integration ✅
- [x] Local FHIR JSON store (`tools/fhir_store/store.py`)
- [x] `search_patient` - Search by name/DOB
- [x] `get_patient_chart` - Clinical summary
- [x] `add_allergy` - Document allergies
- [x] `prescribe_medication` - Medication orders
- [x] `save_clinical_note` - Clinical documentation
- [ ] `analyze_medical_image` (MedGemma vision) - TODO

### Phase 5: Polish
- [ ] Pre-cache queries for demo
- [ ] Technical writeup
- [ ] 3-minute video
