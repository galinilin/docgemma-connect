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

## License

See LICENSE file for details.
