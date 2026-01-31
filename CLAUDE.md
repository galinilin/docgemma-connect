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
| Agent Orchestration | LangGraph (TODO) |
| Tool Protocol | MCP |
| Package Manager | uv |

## Project Structure

```
docgemma-connect/
├── src/docgemma/
│   ├── __init__.py
│   ├── model.py              # DocGemma wrapper with Outlines integration
│   └── tools/
│       ├── __init__.py
│       ├── schemas.py        # Pydantic schemas for all tools
│       ├── drug_safety.py    # OpenFDA boxed warnings
│       ├── drug_interactions.py  # RxNav drug interactions
│       ├── medical_literature.py # PubMed search
│       └── clinical_trials.py    # ClinicalTrials.gov search
├── doc/
│   └── DOCGEMMA_IMPLEMENTATION_GUIDE.md  # Full architecture spec
├── main.py                   # Test script
├── test_tools.py
└── pyproject.toml
```

## Implemented Tools

| Tool | API | Status |
|------|-----|--------|
| `check_drug_safety` | OpenFDA | ✅ Done |
| `search_medical_literature` | PubMed | ✅ Done |
| `check_drug_interactions` | RxNav | ✅ Done |
| `find_clinical_trials` | ClinicalTrials.gov | ✅ Done |
| `get_patient_record` | Local EHR | ❌ TODO |
| `update_patient_record` | Local EHR | ❌ TODO |
| `analyze_medical_image` | MedGemma Vision | ❌ TODO |

## Agent Pipeline (TODO)

```
Image Detection → Complexity Router → Decompose Intent → Agentic Loop → Response Synthesis
     (code)           (LLM)              (LLM)         (Plan→Execute→Check)    (LLM)
```

Key nodes to implement:
1. **Image Detection** - Pure code, detect medical image attachments
2. **Complexity Router** - LLM + Outlines, route direct vs complex queries
3. **Decompose Intent** - LLM + Outlines, break query into subtasks
4. **Plan/Execute/Check** - Agentic loop with tool calls
5. **Response Synthesis** - Free-form LLM generation

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
```

## 4B Model Guidelines

1. **Keep prompts short** — Under 200 tokens for system prompts
2. **Use Outlines everywhere** — Don't ask for JSON, force it
3. **Deterministic stopping** — Never ask "are you done?"
4. **One decision per node** — Don't combine classification tasks
5. **Filter context aggressively** — Only pass what's needed per node

## Implementation Priority

### Phase 1: Core Pipeline
- [ ] State object (`DocGemmaState` TypedDict)
- [ ] LangGraph workflow skeleton
- [ ] Image detection node
- [ ] Complexity router node
- [ ] Basic synthesis node

### Phase 2: Agentic Loop
- [ ] Intent decomposition node
- [ ] Tool selection node (Outlines constrained)
- [ ] Result checking logic
- [ ] Loop control flow

### Phase 3: Missing Tools
- [ ] `get_patient_record` / `update_patient_record`
- [ ] `analyze_medical_image` (MedGemma vision)
- [ ] Pseudo-EHR data store

### Phase 4: Polish
- [ ] Demo UI
- [ ] Pre-cache queries for demo
- [ ] Technical writeup
- [ ] 3-minute video
