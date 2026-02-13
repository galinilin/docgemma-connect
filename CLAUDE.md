# DocGemma Connect (Backend)

## Overview

Medical AI assistant backend for the **Google MedGemma Impact Challenge**.

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
| LLM | MedGemma 1.5 4B IT (vLLM served, OpenAI-compatible API) |
| Structured Output | Outlines (vLLM guided decoding via `generate_outlines()`) |
| Agent Orchestration | LangGraph (StateGraph with MemorySaver checkpointer) |
| API Server | FastAPI + WebSockets + uvicorn |
| EHR Store | Local FHIR R4 JSON files (`data/fhir/{ResourceType}/{id}.json`) |
| Package Manager | uv |
| Python | >=3.12 |

## Project Structure

```
docgemma-connect/
├── src/docgemma/
│   ├── __init__.py              # Lazy imports
│   ├── model.py                 # DocGemma vLLM client (598 lines)
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py             # AgentState TypedDict (~20 fields, 90 lines)
│   │   ├── schemas.py           # Pydantic schemas for Outlines (149 lines)
│   │   ├── prompts.py           # System prompt + all node prompts (300+ lines)
│   │   ├── nodes.py             # 7 node implementations (600+ lines)
│   │   └── graph.py             # LangGraph build + GraphConfig (600+ lines)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory + lifespan + SPA static files (153 lines)
│   │   ├── config.py            # APIConfig dataclass from env vars (65 lines)
│   │   ├── models/
│   │   │   ├── events.py        # AgentEvent types + ClinicalTrace + TraceStep
│   │   │   ├── requests.py      # CreateSessionRequest, ChatRequest, ApproveToolRequest
│   │   │   ├── responses.py     # API response models
│   │   │   └── session.py       # Session model + SessionStatus enum
│   │   ├── routers/
│   │   │   ├── health.py        # GET /api/health
│   │   │   ├── sessions.py      # REST + WebSocket for sessions
│   │   │   └── patients.py      # EHR patient endpoints
│   │   └── services/
│   │       ├── agent_runner.py  # LangGraph wrapper with interrupt-based tool approval (150+ lines)
│   │       └── session_store.py # In-memory + file-backed session storage
│   └── tools/
│       ├── __init__.py
│       ├── registry.py          # ToolRegistry + 9 registered tools (425 lines)
│       ├── schemas.py           # Input/Output Pydantic schemas for all tools (150+ lines)
│       ├── drug_safety.py       # OpenFDA boxed warnings
│       ├── drug_interactions.py # RxNav drug-drug interactions
│       ├── medical_literature.py # PubMed/NCBI search
│       ├── clinical_trials.py   # ClinicalTrials.gov v2 API
│       ├── image_analysis.py    # MedGemma vision (TODO)
│       └── fhir_store/
│           ├── __init__.py
│           ├── store.py         # FhirJsonStore (drop-in MedplumClient replacement, 100+ lines)
│           ├── search.py        # Patient search by name/DOB
│           ├── chart.py         # Clinical summary builder (diagnoses, meds, allergies, vitals, notes)
│           ├── allergies.py     # AllergyIntolerance resource creation
│           ├── medications.py   # MedicationRequest resource creation
│           ├── notes.py         # DocumentReference resource creation
│           ├── schemas.py       # FHIR-specific Pydantic schemas
│           └── seed.py          # Seed store from Synthea FHIR bundles
├── eval/
│   ├── test_agent.py            # 120 test cases (12 categories × 10) with mock/real tools
│   ├── test_tools.py            # Individual tool tests (16+ drug, 12+ lit, 10+ interaction, 8+ trial)
│   ├── test_ehr_tools.py        # FHIR store operations
│   ├── test_tool_planning.py    # 50 prompt engineering test cases
│   ├── tool_selection_experiments.py   # Tool routing accuracy experiments
│   ├── synthesis_experiments.py        # Response quality metrics
│   ├── thinking_experiments.py         # Thinking token activation experiments
│   └── result_routing_experiments.py   # Result classification experiments
├── doc/
│   ├── DOCGEMMA_V3_AGENT_GRAPH.md     # Authoritative v3 architecture spec (1467 lines)
│   ├── MEDGEMMA_PROMPTING_GUIDE.md    # 856+ experiments, empirical findings
│   └── QUICK_DEMO_SHARING.md          # Demo setup instructions
├── data/
│   ├── fhir/                    # FHIR R4 JSON resources (seeded from Synthea)
│   │   ├── Patient/
│   │   ├── Condition/
│   │   ├── MedicationRequest/
│   │   ├── AllergyIntolerance/
│   │   ├── Observation/
│   │   ├── DiagnosticReport/
│   │   ├── DocumentReference/
│   │   └── Encounter/
│   └── sessions/                # Persisted session JSON files
├── pyproject.toml
├── .env.example
└── uv.lock
```

## Commands

```bash
# Install dependencies
uv sync

# Start API server (default port 8000)
uv run docgemma-serve

# Run eval suite
uv run python eval/test_agent.py
uv run python eval/test_tools.py
uv run python eval/test_ehr_tools.py

# Run experiments
uv run python eval/tool_selection_experiments.py
uv run python eval/synthesis_experiments.py

# Seed FHIR store from Synthea bundles
uv run python -m docgemma.tools.fhir_store.seed --clean
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCGEMMA_ENDPOINT` | — | vLLM/OpenAI API endpoint (**required**) |
| `DOCGEMMA_API_KEY` | — | API authentication token (**required**) |
| `DOCGEMMA_MODEL` | `google/medgemma-1.5-4b-it` | Model identifier |
| `DOCGEMMA_HOST` | `0.0.0.0` | Server bind address |
| `DOCGEMMA_PORT` | `8000` | Server port |
| `DOCGEMMA_DEBUG` | `false` | Debug mode |
| `DOCGEMMA_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `DOCGEMMA_LOAD_MODEL` | `true` | Load model on startup |
| `DOCGEMMA_TOOL_APPROVAL` | `true` | Enable tool approval flow |
| `DOCGEMMA_SESSIONS_DIR` | `data/sessions` | Session persistence directory |
| `FHIR_DATA_DIR` | `data/fhir/` | FHIR JSON store root path |
| `HF_TOKEN` | — | HuggingFace token (model access) |
| `GOOGLE_API_KEY` | — | Google API key (Synthea augmentation) |

## Model Client (`model.py`)

```python
from docgemma import DocGemma
from docgemma.agent.prompts import SYSTEM_PROMPT

model = DocGemma(system_prompt=SYSTEM_PROMPT)

# Free-form generation (with conversation history)
response = model.generate("What is hypertension?", messages=history)

# Streaming generation
async for chunk in model.generate_stream("Explain HTN", messages=history):
    print(chunk, end="")

# Structured generation via Outlines (vLLM guided decoding)
from pydantic import BaseModel
class Result(BaseModel):
    answer: str
    confidence: float
result = model.generate_outlines(prompt, Result, messages=history)
```

### DocGemma Client Configuration
- `endpoint`: vLLM API URL (from `DOCGEMMA_ENDPOINT`)
- `api_key`: Auth token (from `DOCGEMMA_API_KEY`)
- `model`: Model ID (default: `google/medgemma-1.5-4b-it`)
- `timeout`: HTTP timeout (default: 120s)
- `system_prompt`: Prepended to every API call via `_build_messages()`

### Thinking Token Handling
- Open tag: `<unused94>`, Close tag: `<unused95>`
- Regex: `r"<unused94>.*?<unused95>"` strips both tags and content
- Close tag rarely emitted (model runs to token limit)
- Max thinking words: 256 (enforced via `_THINKING_MAX_WORDS`)
- `last_thinking_text` property captures thinking for clinical trace
- `_truncate_thinking()`: Forces closure of runaway thinking blocks
- `_continue_after_thinking()`: Continuation call when thinking consumes all tokens

### Key Methods
| Method | Purpose | Returns |
|--------|---------|---------|
| `generate()` | Free-form generation with thinking filter | `str` |
| `generate_stream()` | Token-by-token async streaming | `AsyncGenerator[str]` |
| `generate_outlines()` | Structured generation via Pydantic schema | `BaseModel` |
| `health_check()` | Ping `/v1/models` endpoint | `bool` |

## Agent Architecture (v3 — 7-Node Reactive Pipeline)

### Pipeline Flow
```
User Query → input_assembly → intent_classify
                                    ↓
                    ┌── DIRECT ──→ synthesize → END
                    │
                    └── TOOL_NEEDED → tool_select → tool_execute → result_classify
                                          ↑                            ↓
                                          └── loop ← route_after_result
                                                         ↓ (error)
                                                    error_handler
```

### Nodes

#### Node 1: input_assembly (deterministic, async)
- Extracts patient IDs (regex: UUIDs + short forms like `abc-123`)
- Extracts drug mentions (dictionary matching against ~5000 COMMON_DRUGS)
- Extracts action verbs (keyword matching: prescribe, document, check, search, save)
- Detects image presence → runs image analysis
- Pre-fetches patient chart if `session_patient_id` is set
- Returns: `extracted_entities`, `image_findings`, `patient_context`

#### Node 2: intent_classify (LLM + Outlines, T=0.0)
- Schema: `IntentClassification` → `intent: Literal["DIRECT", "TOOL_NEEDED"]` (first field!), `task_summary: str`, `suggested_tool: Optional[str]`
- Respects `tool_calling_enabled=False` to force DIRECT
- 256 max tokens

#### Node 3: tool_select (LLM + Outlines, two-stage, T=0.0)
- **Stage 1** (64 tokens): `ToolSelection` → `tool_name: Literal[...]` — single field, no nullable distractors
- **Stage 2** (128 tokens): Per-tool argument schema from `TOOL_ARG_SCHEMAS` with entity hints
- 1-shot example matched to `suggested_tool` (91% arg accuracy)

#### Node 4: tool_execute (deterministic, async)
- Maps schema field names to registry executor params (e.g., `drug_names` → `drugs`)
- Executes via `ToolRegistry` (timeout: 10s)
- Pre-formats errors using `ERROR_TEMPLATES` (raw → 4.8/10, formatted → 10/10 quality)
- Formats results with clinical labels (no tool name leakage)
- **Interrupt point**: Write tools require user approval

#### Node 5: result_classify (LLM + Outlines, T=0.0)
- Schema: `ResultAssessment` → `quality: Literal["success_rich", "success_partial", "no_results", "error_retryable", "error_fatal"]`, `brief_summary: str`
- 94% accuracy (model's strongest capability)
- 128 max tokens

#### Node 5a: error_handler (hybrid: deterministic rules + LLM)
- **Deterministic ask_user** (model scores 0%): multiple patient matches, missing args, ambiguous drug
- **Deterministic skip_and_continue**: retry_count >= MAX_RETRIES, drug not found, service unavailable after 1 retry
- **LLM retry strategy** (92% accuracy): `RetryStrategy` → `strategy: Literal["retry_same", "retry_different_args"]`

#### Node 6: route_after_result_classify (deterministic)
- Error → error_handler
- Task pattern satisfied → synthesize
- Duplicate tool call detected → synthesize
- `step_count >= MAX_STEPS` (4) → synthesize
- Otherwise → tool_select (loop)

#### Node 7: synthesize (LLM free-form, T=0.5, async streaming)
- DIRECT route: lightweight `DIRECT_CHAT_PROMPT`, no tool context
- TOOL_NEEDED route: includes task_summary, formatted tool results, image findings, errors
- No thinking prefixes (causes 13% empty output)
- Max 256 tokens (quality 9.4→9.7 vs 512)
- Captures thinking via `model.last_thinking_text`
- Streams token-by-token to client

### State Object (`AgentState` TypedDict)

```python
# Input
user_query: str
conversation_history: list[dict[str, str]]
image_data: Optional[bytes]
extracted_entities: ExtractedEntities
image_findings: Optional[str]

# Intent Classification
intent: str          # "DIRECT" | "TOOL_NEEDED"
task_summary: str    # Clinical framing ~50 words
suggested_tool: Optional[str]

# Tool Loop
current_tool: Optional[str]
current_args: Optional[dict[str, Any]]
tool_results: Annotated[list[ToolResult], operator.add]  # Accumulates
step_count: int
retry_count: int

# Result Classification
last_result_classification: Optional[str]
last_result_summary: Optional[str]

# Error Handling
error_messages: list[str]
clarification_request: Optional[str]

# Internal (interrupt/approval)
_planned_tool: Optional[str]
_planned_args: Optional[dict[str, Any]]

# Session Context
session_patient_id: Optional[str]
tool_calling_enabled: Optional[bool]
patient_context: Optional[str]

# Output
final_response: Optional[str]
model_thinking: Optional[str]
```

### GraphConfig

The `GraphConfig` dataclass in `graph.py` provides a graph-agnostic interface for `agent_runner.py`:

- `interrupt_before`: `["tool_execute"]` — pause for write-tool approval
- `extract_tool_proposal()`: Read `_planned_tool` + `_planned_args` from interrupt state
- `build_rejection_update()`: State update for rejected tools
- `terminal_nodes`: `frozenset({"synthesize"})` — only node producing `final_response`
- `make_initial_state()`: Factory for fresh turn state (prevents checkpoint leakage)
- `get_status_text()`: Randomized, context-aware status messages
- `build_clinical_trace()`: Converts state + node durations → `ClinicalTrace` object

### Prompts & Constants (`prompts.py`)

**SYSTEM_PROMPT**: "You are a clinical decision-support assistant integrated with an electronic health record system and medical knowledge tools."

**Temperature Settings** (empirically validated):
| Node | Temperature | Rationale |
|------|-------------|-----------|
| intent_classify | 0.0 | Operational, deterministic |
| tool_select (both stages) | 0.0 | Operational, deterministic |
| result_classify | 0.0 | Operational, deterministic |
| error_retry | 0.0 | Operational, deterministic |
| synthesize | 0.5 | Free-form, peak fact rate 90% |

**Max Tokens**:
| Node | Tokens |
|------|--------|
| intent_classify | 256 |
| tool_select stage 1 | 64 |
| tool_select stage 2 | 128 |
| result_classify | 128 |
| error_retry | 64 |
| synthesize | 256 |

**TOOL_CLINICAL_LABELS** (eliminates source leakage):
| Internal Name | Clinical Label |
|---------------|----------------|
| `check_drug_safety` | Drug Safety Report |
| `check_drug_interactions` | Drug Interaction Check |
| `search_medical_literature` | Medical Literature |
| `find_clinical_trials` | Clinical Trials |
| `search_patient` | Patient Search |
| `get_patient_chart` | Patient Record |
| `prescribe_medication` | Prescription |
| `add_allergy` | Allergy Documentation |
| `save_clinical_note` | Clinical Note |

**ERROR_TEMPLATES**: Pre-format categories: timeout, not_found, invalid_args, rate_limit, server_error, multiple_matches, generic

**Constants**:
- `ACTION_VERBS`: ["prescribe", "document", "check", "search", "save", ...]
- `COMMON_DRUGS`: ~5000 generic/brand names
- `MAX_RETRIES`: 2 per tool
- `MAX_STEPS`: 4 total tool steps
- `WRITE_TOOLS`: {"prescribe_medication", "add_allergy", "save_clinical_note"}

## Tools

### Registry (`tools/registry.py`)

`ToolRegistry` class — central dispatcher:
- `register()` / `register_tool()`: Registration (decorator or programmatic)
- `get(name)`: Get `ToolDefinition`
- `execute(tool_name, args)`: Execute by name with arg mapping

`ToolDefinition`:
- `name`: Tool ID
- `description`: Short description
- `args`: Dict[arg_name, description]
- `executor`: Async callable
- `arg_mapping`: Optional schema_field → param_name mapping

### External API Tools

| Tool | API | Key Input | Key Output |
|------|-----|-----------|------------|
| `check_drug_safety` | OpenFDA `/drug/label.json` | `drug_name: str` | `brand_name, has_warning, boxed_warning` |
| `check_drug_interactions` | RxNav API | `drugs: list[str]` (≥2) | `drugs_checked, resolved_rxcuis, interactions` |
| `search_medical_literature` | PubMed NCBI API | `query: str`, `max_results=3` | `total_found, articles[]` |
| `find_clinical_trials` | ClinicalTrials.gov v2 | `condition: str`, optional `location` | `total_found, trials[]` (NCT ID, title, contact) |

**Arg Mapping Note**: `check_drug_interactions` has `drug_names` (schema) → `drugs` (executor). The mapping is declared in `registry.py` and applied in `_collect_args_for_registry()`.

### FHIR Store Tools

| Tool | Input | Output |
|------|-------|--------|
| `search_patient` | `name: str`, optional `dob` | `patients[]` (name, ID, DOB) |
| `get_patient_chart` | `patient_id: str` | Formatted clinical summary |
| `add_allergy` | `patient_id, substance, reaction, severity=moderate` | Confirmation |
| `prescribe_medication` | `patient_id, medication_name, dosage, frequency` | Confirmation |
| `save_clinical_note` | `patient_id, note_text, note_type=clinical-note` | Confirmation |

### FhirJsonStore (`tools/fhir_store/store.py`)

Drop-in `MedplumClient` replacement. Reads/writes FHIR R4 resources as JSON files under `data/fhir/{ResourceType}/{id}.json`.

- `get(path, params)`: Single resource read or search (returns FHIR Bundle)
- `post(path, data)`: Write new resource with auto-assigned UUID
- Search params: name, birthdate, subject, patient, status, category, _count, _sort

## API Server

### Application Factory (`api/main.py`)
- Lifespan handler: Model initialization on startup
- CORS middleware: Configurable origins (default: all)
- Routes: health, sessions, patients
- SPAStaticFiles: Serves frontend with fallback to `index.html`
- Entry point: `docgemma-serve` → `main()` → `uvicorn.run()`

### AgentRunner (`api/services/agent_runner.py`)
- Wraps LangGraph for interrupt-based tool approval
- `start_turn()`: Async generator yielding `AgentEvent` objects
- `resume_after_approval()`: Resume graph after user approves/rejects
- Sets session status: PROCESSING → COMPLETE/ERROR/INTERRUPTED

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check + model loaded status |
| POST | `/api/sessions` | Create new session |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/{id}` | Get session with messages |
| DELETE | `/api/sessions/{id}` | Delete session |
| WS | `/api/sessions/{id}/ws` | WebSocket for real-time agent events |
| GET | `/api/patients` | List/search patients (query: name, dob) |
| POST | `/api/patients` | Create patient |
| GET | `/api/patients/{id}` | Get full patient chart |
| POST | `/api/patients/{id}/allergies` | Add allergy |
| POST | `/api/patients/{id}/medications` | Prescribe medication |
| POST | `/api/patients/{id}/notes` | Save clinical note |

### WebSocket Protocol

**Server → Client Events:**

| Event | Key Fields | Purpose |
|-------|------------|---------|
| `node_start` | `node_id`, `node_label` | Node execution started |
| `node_end` | `node_id`, `duration_ms` | Node execution completed |
| `agent_status` | `status_text`, `node_id`, `tool_name` | Status update |
| `tool_approval_request` | `tool_name`, `tool_args`, `subtask_intent` | Human-in-the-loop |
| `tool_execution_start` | `tool_name`, `tool_args` | Tool running |
| `tool_execution_end` | `tool_name`, `success`, `result`, `duration_ms` | Tool completed |
| `streaming_text` | `text`, `node_id` | Token-by-token synthesis |
| `completion` | `final_response`, `tool_calls_made`, `clinical_trace` | Turn complete |
| `error` | `error_type`, `message`, `recoverable` | Error occurred |

**Client → Server Actions:**
```json
{ "action": "send_message", "data": { "content": "...", "image_base64": null, "patient_id": null, "tool_calling_enabled": true } }
{ "action": "approve_tool", "data": {} }
{ "action": "reject_tool", "data": { "reason": "optional" } }
{ "action": "cancel", "data": {} }
```

### Clinical Trace (`ClinicalTrace`)

```python
class TraceStep:
    type: str          # "thought" | "tool_call" | "synthesis"
    label: str         # Clinical-friendly label
    description: str   # What happened
    duration_ms: float
    reasoning_text: Optional[str]       # Model thinking (thoughts only)
    tool_name: Optional[str]            # Tool calls only
    tool_result_summary: Optional[str]  # Brief summary
    tool_result_detail: Optional[str]   # Full markdown detail
    success: Optional[bool]

class ClinicalTrace:
    steps: list[TraceStep]
    total_duration_ms: float
    tools_consulted: int
```

Built by `GraphConfig.build_clinical_trace()` using node durations and state. Uses `TOOL_CLINICAL_LABELS` for user-friendly names. `_describe_tool_call()` generates clinical descriptions (e.g., "Checked safety for metformin"). `_summarize_result()` provides content-rich summaries.

## Schemas (`agent/schemas.py`)

**CRITICAL RULE**: Decision-critical fields MUST come FIRST in Pydantic schemas. Reversing field order drops arg accuracy 88%→21%.

| Schema | Node | Key Fields (in order) |
|--------|------|-----------------------|
| `IntentClassification` | Node 2 | `intent: Literal[...]` (first!), `task_summary`, `suggested_tool` |
| `ToolSelection` | Node 3 Stage 1 | `tool_name: Literal[...]` (single field, no nullable distractors) |
| Per-tool arg schemas | Node 3 Stage 2 | Required fields first, then optional |
| `ResultAssessment` | Node 5 | `quality: Literal[...]` (first!), `brief_summary` |
| `RetryStrategy` | Node 5a | `strategy: Literal[...]` (first!), `reasoning` |

**Per-Tool Argument Schemas**:
- `DrugSafetyArgs`: `drug_name: str`
- `DrugInteractionArgs`: `drug_names: list[str]` (min_length=2)
- `LiteratureSearchArgs`: `query: str`
- `ClinicalTrialsArgs`: `condition: str`, optional `status`
- `PatientSearchArgs`: `name: str`
- `PatientChartArgs`: `patient_id: str`
- `PrescribeMedicationArgs`: `patient_id, medication_name, dosage, frequency`, optional `notes`
- `AddAllergyArgs`: `patient_id, substance, reaction`, optional `severity`
- `ClinicalNoteArgs`: `patient_id, note_type, note_text`

## Critical Implementation Notes

1. **Schema Field Ordering**: Always put required, decision-critical fields first. Reversing order drops accuracy 88%→21%.

2. **Thinking Token Filtering**: MedGemma uses `<unused94>...<unused95>` for internal reasoning. Strip from user-facing output. Close tag often not emitted.

3. **Error Pre-Formatting**: Raw API errors cause LLM to hallucinate from pretrained knowledge. Pre-format ALL errors into clinician-friendly messages via `ERROR_TEMPLATES` before synthesis.

4. **No Thinking Prefixes for Synthesis**: Prefixes like "Let me think..." cause 13% of responses to be empty (thinking consumes all tokens).

5. **Reactive Loop, Not Planning**: Never ask the model to plan all steps upfront (0-10% accuracy). Reactive: execute tool → classify result → decide next action deterministically.

6. **Deterministic Routing**: Model cannot judge sufficiency (0%), decide ask_user (0%), or decide skip (0%). All routing decisions in code with hardcoded rules.

7. **Clinical Labels**: Remove internal tool names from synthesis context. Use `TOOL_CLINICAL_LABELS` mapping.

8. **Fresh State Per Turn**: `GraphConfig.make_initial_state()` resets all fields to prevent checkpoint state leakage across turns.

9. **Patient Context Injection**: Pre-fetch patient chart (if selected) in `input_assembly`, inject into all downstream prompts.

10. **Image Handling**: Analyze images in `input_assembly` (before routing), so findings available to both DIRECT and TOOL_NEEDED paths.

11. **Two-Stage Tool Selection**: Stage 1 selects tool name (single field, no distractors → prevents null cascade). Stage 2 extracts per-tool args with entity hints.

12. **1-Shot Matched Examples**: `TOOL_EXAMPLES` provides one example per tool, matched to `suggested_tool` from intent classification. Yields 91% arg accuracy.

## Evaluation

### Test Suites
| Script | Cases | Description |
|--------|-------|-------------|
| `eval/test_agent.py` | 120 | Full pipeline (12 categories × 10): simple, complex, tool, failure, multi-tool, image |
| `eval/test_tools.py` | 46+ | Individual tool validation: drug safety, literature, interactions, trials |
| `eval/test_ehr_tools.py` | — | FHIR store CRUD operations |
| `eval/test_tool_planning.py` | 50 | Prompt engineering test cases |

### Experiment Scripts
| Script | Focus |
|--------|-------|
| `eval/tool_selection_experiments.py` | Tool routing accuracy |
| `eval/synthesis_experiments.py` | Response quality metrics |
| `eval/thinking_experiments.py` | Thinking token activation rates |
| `eval/result_routing_experiments.py` | Result classification accuracy |

## Key Documentation

| Document | Purpose |
|----------|---------|
| `doc/DOCGEMMA_V3_AGENT_GRAPH.md` | **Authoritative** v3 architecture spec (1467 lines) |
| `doc/MEDGEMMA_PROMPTING_GUIDE.md` | 856+ experiment findings, empirical thresholds |
| `doc/QUICK_DEMO_SHARING.md` | Demo setup instructions |

## Dependencies (from pyproject.toml)

```
httpx>=0.28.0          # Async HTTP client
langgraph>=0.2.0       # Agent orchestration
nest-asyncio>=1.6.0    # Nested event loops
outlines>=1.2.9        # Constrained generation
pillow>=12.1.0         # Image processing
pydantic>=2.0.0        # Data validation
python-dotenv>=1.2.1   # Environment loading
fastapi>=0.115.0       # Web framework
uvicorn[standard]>=0.34.0  # ASGI server
websockets>=14.0       # WebSocket support
python-multipart>=0.0.20   # File uploads
```

## 4B Model Guidelines

1. **Keep prompts short** — Under 200 tokens for system prompts
2. **Use Outlines everywhere** — Don't ask for JSON, force constrained generation
3. **Deterministic stopping** — Never ask "are you done?"
4. **One decision per node** — Don't combine classification tasks
5. **Filter context aggressively** — Only pass what's needed per node
6. **Critical fields first** — In Pydantic schemas, decision fields before optional fields
7. **Pre-format errors** — Don't let LLM interpret raw API errors
8. **No thinking prefixes** — They consume synthesis token budget
