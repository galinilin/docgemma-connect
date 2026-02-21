# DocGemma Connect

> **Part of the DocGemma project:** [docgemma-app](https://github.com/galinilin/docgemma-app) (Docker deployment) | [docgemma-frontend](https://github.com/galinilin/docgemma-frontend) (Vue 3 UI)

Agentic medical AI backend with autonomous tool calling, powered by MedGemma via remote vLLM endpoint. Designed for resource-limited healthcare environments.

## Overview

DocGemma Connect is a FastAPI backend that orchestrates an AI agent capable of clinical decision support. It uses a LangGraph-based workflow with structured tool calling to query drug safety databases, search medical literature, manage electronic health records (FHIR R4), and analyze medical images — all with a human-in-the-loop approval system for write operations.

### Key Capabilities

- **Agentic reasoning** — 7-node LangGraph workflow with binary intent classification, tool selection, and streamed synthesis
- **10 integrated tools** — Drug safety (OpenFDA), drug interactions (RxNav), medical literature (PubMed), clinical trials (ClinicalTrials.gov), FHIR EHR operations, and medical image analysis
- **Human-in-the-loop** — Write tools (prescribe medication, add allergy, save note) require explicit user approval before execution
- **Real-time streaming** — WebSocket-based chat with incremental token streaming and agent status events
- **Clinical trace** — Full reasoning chain captured per turn (thinking, tool calls, synthesis) with step durations
- **Local FHIR R4 store** — JSON file-backed EHR with patient search, chart retrieval, and resource creation

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI + Uvicorn |
| Agent orchestration | LangGraph |
| Structured output | Outlines (JSON schema validation) |
| Model endpoint | vLLM-compatible (OpenAI API format) |
| Data validation | Pydantic v2 |
| Async HTTP | httpx |
| Real-time | WebSockets |
| Package manager | UV |
| Python | 3.12+ |

## Project Structure

```
src/docgemma/
├── api/
│   ├── main.py                # FastAPI app factory & lifespan
│   ├── config.py              # Environment-based configuration
│   ├── models/                # Pydantic request/response/event schemas
│   ├── routers/
│   │   ├── health.py          # GET /api/health
│   │   ├── sessions.py        # Session CRUD + WebSocket chat
│   │   ├── patients.py        # Patient/EHR endpoints
│   │   └── imaging.py         # Medical image upload/serving
│   └── services/
│       ├── agent_runner.py    # LangGraph execution with interrupt support
│       └── session_store.py   # Disk-backed session persistence
├── agent/
│   ├── graph.py               # 7-node LangGraph workflow definition
│   ├── nodes.py               # Node implementations
│   ├── state.py               # AgentState TypedDict
│   ├── prompts.py             # Empirically-tuned prompts (856 experiments)
│   └── schemas.py             # LLM output schemas
├── tools/
│   ├── registry.py            # Tool dispatcher & registration
│   ├── drug_safety.py         # OpenFDA API
│   ├── drug_interactions.py   # RxNav API
│   ├── medical_literature.py  # PubMed E-utilities
│   ├── clinical_trials.py     # ClinicalTrials.gov v2
│   ├── image_analysis.py      # Vision API (vLLM-compatible)
│   └── fhir_store/            # Local FHIR R4 JSON store
│       ├── store.py           # FhirJsonStore client
│       ├── search.py          # Patient search
│       ├── chart.py           # Chart retrieval
│       ├── allergies.py       # Allergy management
│       ├── medications.py     # Medication prescribing
│       ├── notes.py           # Clinical note creation
│       └── seed.py            # Database seeding
└── model.py                   # DocGemma LLM client wrapper
data/
├── fhir/                      # FHIR R4 resources (JSON by type)
├── imaging/                   # Medical images
└── sessions/                  # Session persistence
```

## Getting Started

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager (recommended)
- Access to a vLLM-compatible endpoint serving MedGemma

### Installation

```bash
# Clone the repository
git clone https://github.com/galinilin/docgemma-connect.git
cd docgemma-connect

# Install dependencies
uv sync
```

### Configuration

Create a `.env` file in the project root:

```ini
# Required — remote model endpoint
DOCGEMMA_ENDPOINT=https://your-vllm-endpoint.com
DOCGEMMA_API_KEY=your-api-key
DOCGEMMA_MODEL=google/medgemma-27b-it

# Optional — server settings
DOCGEMMA_HOST=0.0.0.0
DOCGEMMA_PORT=8000
DOCGEMMA_DEBUG=false

# Optional — feature flags
DOCGEMMA_LOAD_MODEL=true
DOCGEMMA_TOOL_APPROVAL=true

# Optional — storage paths
DOCGEMMA_SESSIONS_DIR=data/sessions

# Optional — external API keys (for tools)
HF_TOKEN=your-huggingface-token
```

### Running

```bash
# Via the CLI entrypoint
uv run docgemma-serve

# Or via uvicorn directly
uvicorn docgemma.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts at `http://localhost:8000` by default. API docs are available at `/docs` (Swagger UI).

## API Reference

### Health

```
GET /api/health
```

Returns server status, model loaded state, and version.

### Sessions

```
POST   /api/sessions                    # Create a new chat session
GET    /api/sessions                    # List all sessions
GET    /api/sessions/{session_id}       # Get session details
DELETE /api/sessions/{session_id}       # Delete a session
```

### Chat (WebSocket)

```
WS /api/sessions/{session_id}/ws
```

**Client messages:**
- `send_message` — Send a user message (with optional `image_base64`)
- `approve_tool` — Approve a pending tool call (with optional `edited_args`)
- `reject_tool` — Reject a pending tool call (with `reason`)
- `cancel` — Cancel the current agent run

**Server events:**
- `node_start` / `node_end` — Graph execution milestones
- `agent_status` — Human-readable status updates
- `tool_approval_request` — Requests user approval for a write tool
- `tool_execution_start` / `tool_execution_end` — Tool invocation lifecycle
- `streaming_text` — Incremental response tokens
- `completion` — Final response with full clinical trace

### Patients / EHR

```
GET    /api/patients                            # Search patients (?name=&dob=)
POST   /api/patients                            # Create a patient
GET    /api/patients/{patient_id}               # Full patient chart
POST   /api/patients/{patient_id}/allergies     # Add allergy
POST   /api/patients/{patient_id}/medications   # Prescribe medication
POST   /api/patients/{patient_id}/notes         # Save clinical note
```

### Medical Imaging

```
POST   /api/patients/{patient_id}/imaging       # Upload image (multipart)
GET    /api/imaging/{media_id}                  # Serve image
DELETE /api/imaging/{media_id}                  # Delete image
```

## Agent Architecture

The agent uses a 7-node LangGraph workflow with binary classification at each decision point:

```
input_assembly → preliminary_thinking → intent_classify
                                            │
                              ┌──────────────┴──────────────┐
                           DIRECT                      TOOL_NEEDED
                              │                             │
                              │                        tool_select
                              │                             │
                              │                        tool_execute (interrupt)
                              │                             │
                              │                      result_classify
                              │                        │         │
                              │                    SUFFICIENT  INSUFFICIENT
                              │                        │         │
                              │                        │    (loop back to
                              │                        │     tool_select)
                              └────────────┬───────────┘
                                           │
                                       synthesize (stream)
```

- **Temperature 0.0** for classification nodes (deterministic)
- **Temperature 0.5** for thinking and synthesis (controlled creativity)
- **Outlines** enforces valid JSON output on classification steps
- Prompts are empirically tuned from 856 MedGemma experiments

## Tools

| Tool | Source | Type |
|------|--------|------|
| `check_drug_safety` | OpenFDA | Read |
| `check_drug_interactions` | RxNav | Read |
| `search_medical_literature` | PubMed E-utilities | Read |
| `find_clinical_trials` | ClinicalTrials.gov v2 | Read |
| `search_patient` | Local FHIR | Read |
| `get_patient_chart` | Local FHIR | Read |
| `add_allergy` | Local FHIR | Write (requires approval) |
| `prescribe_medication` | Local FHIR | Write (requires approval) |
| `save_clinical_note` | Local FHIR | Write (requires approval) |
| `analyze_medical_image` | vLLM Vision API | Read |

## Related Repositories

| Repository | Description |
|---|---|
| [docgemma-app](https://github.com/galinilin/docgemma-app) | One-command Docker deployment — clone, configure, `docker compose up` |
| [docgemma-frontend](https://github.com/galinilin/docgemma-frontend) | Vue 3 web interface with real-time chat, EHR management, and tool approval UI |
