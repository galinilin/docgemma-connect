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
│   ├── model.py              # DocGemma remote client (vLLM/OpenAI API)
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py          # DocGemmaState TypedDict
│   │   ├── schemas.py        # Pydantic schemas for LLM nodes
│   │   ├── prompts.py        # System/user prompts for LLM nodes
│   │   ├── nodes.py          # All node implementations
│   │   └── graph.py          # LangGraph workflow + DocGemmaAgent
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app factory, lifespan
│   │   ├── config.py         # Configuration from env vars
│   │   ├── models/           # Pydantic request/response models
│   │   │   ├── events.py     # WebSocket event types
│   │   │   ├── requests.py
│   │   │   ├── responses.py
│   │   │   └── session.py
│   │   ├── routers/          # API endpoint handlers
│   │   │   ├── health.py     # /api/health
│   │   │   ├── sessions.py   # /api/sessions/*
│   │   │   └── tools.py      # /api/tools
│   │   └── services/         # Business logic
│   │       ├── agent_runner.py   # Async agent execution + WebSocket
│   │       └── session_store.py  # In-memory session management
│   └── tools/
│       ├── __init__.py
│       ├── registry.py       # ToolRegistry + global registrations
│       ├── schemas.py        # Pydantic schemas for all tools
│       ├── drug_safety.py    # OpenFDA boxed warnings
│       ├── drug_interactions.py  # RxNav drug interactions
│       ├── medical_literature.py # PubMed search
│       └── clinical_trials.py    # ClinicalTrials.gov search
├── doc/
│   ├── DOCGEMMA_IMPLEMENTATION_GUIDE.md  # Full architecture spec
│   ├── DOCGEMMA_FLOWCHART.md             # Mermaid diagram
│   └── DOCGEMMA_TEST_CASES_V2.md         # 120 test cases (YAML)
├── main.py                   # Model test script
├── test_agent.py             # Agent pipeline test script
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
| `search_patient` | Medplum FHIR | ✅ Done |
| `get_patient_chart` | Medplum FHIR | ✅ Done |
| `add_allergy` | Medplum FHIR | ✅ Done |
| `prescribe_medication` | Medplum FHIR | ✅ Done |
| `save_clinical_note` | Medplum FHIR | ✅ Done |
| `analyze_medical_image` | MedGemma Vision | ❌ TODO |

## Agent Pipeline

```
                                    ┌─ "direct" → Direct Response → END
Image Detection → Complexity Router ┤
                                    └─ "complex" → Thinking Mode → Decompose Intent → Agentic Loop → Synthesis → END
```

Nodes (all implemented in `agent/nodes.py`):
1. **Image Detection** - Pure code, detect medical image attachments
2. **Complexity Router** - LLM + Outlines, route direct vs complex queries
3. **Thinking Mode** - LLM + Outlines, generate reasoning for complex queries
4. **Decompose Intent** - LLM + Outlines, break query into subtasks (uses reasoning)
5. **Plan Tool** - LLM + Outlines, select tool for current subtask
6. **Execute Tool** - Pure code, call tool via executor
7. **Check Result** - Pure code, loop control logic
8. **Synthesize Response** - Free-form LLM generation

## Model Usage

```python
from docgemma import DocGemma
from pydantic import BaseModel

# Initialize and load
gemma = DocGemma(model_id="google/medgemma-1.5-4b-it")
gemma.load()

# Free-form generation
response = gemma.generate("What is hypertension?")

# Structured generation (Outlines)
class Result(BaseModel):
    answer: str
    confidence: float

result = gemma.generate_outlines(prompt, Result)
```

## Agent Usage

```python
from docgemma import DocGemma, DocGemmaAgent

# Initialize and load model
model = DocGemma(model_id="google/medgemma-1.5-4b-it")
model.load()

# Create agent with tool executor
async def my_tool_executor(tool_name: str, args: dict) -> dict:
    # Implement tool dispatch logic
    ...

agent = DocGemmaAgent(model, tool_executor=my_tool_executor)

# Run async
response = await agent.run("Check drug interactions between warfarin and aspirin")

# Or sync
response = agent.run_sync("What is hypertension?")
```

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

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check + model status |
| POST | `/api/sessions` | Create new session |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/{id}` | Get session details |
| DELETE | `/api/sessions/{id}` | Delete session |
| GET | `/api/sessions/{id}/graph` | Get graph state (nodes + edges) |
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

**Fix** (in `agent_runner.py`):
1. Reset ALL state at turn start: `final_response: None`, `complexity: None`, etc.
2. Only emit `CompletionEvent` from terminal nodes (`synthesize_response`, `direct_response`)
3. Use `completion_emitted` flag to prevent duplicate events

### Terminal Nodes
Only these nodes produce `final_response`:
- `synthesize_response` - Complex query path
- `direct_response` - Simple query path

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
- [x] Medplum FHIR client (`tools/medplum/client.py`)
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
