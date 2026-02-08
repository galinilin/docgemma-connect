# DocGemma Connect

An **agentic medical AI assistant** for the [Google MedGemma Impact Challenge](https://www.kaggle.com/competitions/med-gemma-impact-challenge) on Kaggle. Built with autonomous decision-making and tool-calling capabilities to help healthcare professionals in resource-limited environments.

## Overview

DocGemma Connect is an **agentic AI system** that autonomously navigates complex medical queries through a 4-way triage architecture. Rather than relying on monolithic LLM calls, the agent dynamically routes queries, selects tools, retrieves information, and iterates until the task is complete—all powered by the lightweight MedGemma 4B model.

### Key Capabilities

- **4-Way Triage** — Intelligent routing: direct answers, single-tool lookups, clinical reasoning, or multi-step workflows
- **Autonomous Tool Calling** — Agent selects and invokes appropriate tools based on query context
- **Agentic Loop Execution** — Self-directed iteration with validation, error handling, and retry strategies
- **Structured Tool Outputs** — vLLM guided decoding ensures reliable JSON schemas even on the 4B model
- **System Prompt + Multi-Turn Context** — Conversation history passed as messages array for real context
- **Thinking Token Filtering** — MedGemma's internal `<unused94>...<unused95>` tokens stripped automatically

## Technology Stack

- **LLM:** [MedGemma 1.5 4B IT](https://huggingface.co/google/medgemma-1.5-4b-it) - instruction-tuned medical SLM
- **Structured Output:** [Outlines](https://github.com/dottxt-ai/outlines) - constrained generation for reliable tool calls
- **Agent Orchestration:** LangGraph - 18-node stateful workflow with 4-way triage
- **EHR Store:** Local FHIR JSON Store (seeded from Synthea bundles)
- **API Server:** FastAPI + WebSockets

## Installation

Requires Python 3.12+.

```bash
# CPU only
uv sync --extra cpu

# CUDA 12.8
uv sync --extra cu128
```

## Quick Start

```bash
# Configure environment
cp .env.example .env
# Edit .env with your RunPod/vLLM endpoint

# Seed EHR data (optional)
uv run python -m docgemma.tools.fhir_store.seed

# Start the API server
uv run docgemma-serve

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Architecture, tech stack, development guide
- [doc/DOCGEMMA_FLOWCHART_V2.md](./doc/DOCGEMMA_FLOWCHART_V2.md) - v2 agent pipeline diagram + architecture changes

## License

See LICENSE file for details.
