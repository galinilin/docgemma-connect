# DocGemma Connect - Project Reference

## Overview
Medical AI assistant for the Google MedGemma Impact Challenge on Kaggle. Designed to help general practitioners and patients with limited resources using a decision-tree architecture powered by MedGemma 4B.

**Competition:** https://www.kaggle.com/competitions/med-gemma-impact-challenge
**Model:** https://huggingface.co/google/medgemma-1.5-4b-it (4B parameter SLM)

## Core Philosophy
- Narrow down LLM workload through structured decision trees
- LLM acts as logic engine + response synthesizer (not doing everything)
- Designed for resource-limited environments (offline-capable clinics)

## Decision Tree Branches

1. **Emergency Detection**
   - Detect critical cases requiring immediate emergency services
   - Priority routing before other processing

2. **Reasoning Mode Toggle**
   - Decide whether to enable thinking/chain-of-thought mode

3. **User Type Classification (Patient vs Expert)**
   - Patients: simplified language, basic explanations
   - Experts/Doctors: technical jargon, detailed clinical info

4. **Input Type Detection (Image vs Text)**
   - Route to appropriate processing mode
   - Enable multimodal capabilities when images present

5. **RAG/MCP Usage**
   - Patients: basic MCP calls for public health information
   - Experts: access to technical details, private/specific data

6. **Agentic Loop**
   - Determine if task is complete
   - Continue processing or proceed to synthesis

7. **Response Synthesis**
   - Generate final response with context
   - Include reference links and supporting details

## Technology Stack
- **LLM:** MedGemma 1.5 4B IT (instruction-tuned)
- **Structured Output:** Outlines library (constrained generation)
- **Workflow/Graph:** LangGraph (decision tree orchestration)

## Key Design Decisions
- Decision-tree approach reduces LLM compute burden
- Outlines ensures structured/valid outputs at each branch
- LangGraph manages state and routing between nodes
