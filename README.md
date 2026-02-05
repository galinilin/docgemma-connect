# DocGemma Connect

An **agentic medical AI assistant** for the [Google MedGemma Impact Challenge](https://www.kaggle.com/competitions/med-gemma-impact-challenge) on Kaggle. Built with autonomous decision-making and tool-calling capabilities to help general practitioners and patients in resource-limited environments.

## Overview

DocGemma Connect is an **agentic AI system** that autonomously navigates complex medical queries through a decision-tree architecture. Rather than relying on monolithic LLM calls, the agent dynamically selects tools, retrieves information, and iterates until the task is complete—all powered by the lightweight MedGemma 4B model.

### Key Capabilities

- **Autonomous Tool Calling** - Agent selects and invokes appropriate tools (RAG retrieval, MCP servers, image analysis) based on query context
- **Agentic Loop Execution** - Self-directed iteration that continues until the task is fully resolved
- **Dynamic Routing** - Intelligent branching based on emergency detection, user type, and input modality
- **Structured Tool Outputs** - Constrained generation ensures reliable tool call formatting and response parsing

### Tool Calling

The agent leverages **MCP (Model Context Protocol)** for extensible tool integration:

- **Patient Context**: Public health databases, medication info, symptom checkers
- **Expert Context**: Clinical guidelines, research papers, diagnostic references

Tools are invoked through structured outputs, ensuring valid JSON schemas and reliable parsing even on the 4B parameter model.

## Technology Stack

- **LLM:** [MedGemma 1.5 4B IT](https://huggingface.co/google/medgemma-1.5-4b-it) - instruction-tuned medical SLM
- **Structured Output:** [Outlines](https://github.com/dottxt-ai/outlines) - constrained generation for reliable tool calls
- **Agent Orchestration:** LangGraph - stateful agentic workflows and decision graphs
- **Tool Protocol:** MCP - standardized tool calling interface

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

# Start the API server
uv run docgemma-serve

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Architecture, tech stack, development guide
- [doc/DOCGEMMA_IMPLEMENTATION_GUIDE.md](./doc/DOCGEMMA_IMPLEMENTATION_GUIDE.md) - Full implementation spec
- [doc/DOCGEMMA_FLOWCHART.md](./doc/DOCGEMMA_FLOWCHART.md) - Agent pipeline diagram
- [doc/DOCGEMMA_TEST_CASES_V2.md](./doc/DOCGEMMA_TEST_CASES_V2.md) - 120 test cases

## License

See LICENSE file for details.
