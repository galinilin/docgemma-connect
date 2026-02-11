# MedGemma 4B — Prompting Guide

**Model:** `google/medgemma-1.5-4b-it` (instruction-tuned, 4B parameters)
**Serving:** vLLM with Outlines constrained generation
**Date:** 2026-02-11

This document records empirical findings from four controlled experiment suites on MedGemma 4B behavior under various prompting and constrained-generation configurations.

- **Part I — Thinking Mode** (104 experiments): How the model enters/exits `<unused94>` thinking under different prompting strategies.
- **Part II — Tool Selection & Argument Extraction** (320 experiments, 540 LLM calls): Which prompting strategies get the model to reliably pick the right tool and fill correct args under Outlines.
- **Part III — Result Evaluation, Planning & Routing** (217 experiments, 260 LLM calls): Can the model assess tool results, decide next actions, plan multi-step tasks, and recover from errors?
- **Part IV — Response Synthesis** (215 experiments, 215 LLM calls): How well does the model generate free-form clinical responses from tool results? Prompt variants, temperature, reasoning context, token limits.

---

# Part I — Thinking Mode Experiment Findings

**Experiments:** 104 across 9 categories
**Data:** `thinking_experiments/20260211_014112/`

Varied temperature, system prompts, assistant prefixes, user trigger phrases, combined strategies, guided generation schemas, max token budgets, and multi-turn context — measuring thinking token emission, output quality (Gemini 2.0 Flash judge), and latency.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Thinking Token Mechanics](#2-thinking-token-mechanics)
3. [Temperature](#3-temperature)
4. [System Prompts](#4-system-prompts)
5. [User Trigger Phrases](#5-user-trigger-phrases)
6. [Assistant Prefix Priming](#6-assistant-prefix-priming)
7. [Combined Strategies](#7-combined-strategies)
8. [Guided Generation (Outlines)](#8-guided-generation-outlines)
9. [Max Tokens](#9-max-tokens)
10. [Multi-Turn Context](#10-multi-turn-context)
11. [The Hidden Thinking Phenomenon](#11-the-hidden-thinking-phenomenon)
12. [Trigger Heatmap](#12-trigger-heatmap)
13. [Implications](#13-implications)

---

## 1. Executive Summary

- **22/104** experiments (21.2%) triggered `<unused94>` thinking tokens
- **93/97** responses (95.9%) showed reasoning according to Gemini judge — regardless of token presence
- **Agreement** between token detection and Gemini assessment: only **26%**
- **72 cases** demonstrated sophisticated reasoning WITHOUT any thinking token
- Thinking token close tag (`<unused95>`) emitted in only **1/22** cases (5%)
- Latency overhead when thinking fires: **+1,447ms** (+9.4%)
- Average thinking depth when present: **551 words**
- Average Gemini reasoning score: **8.3/10**

**The core finding:** MedGemma 4B reasons well in its visible output as a baseline behavior. Thinking tokens are an unreliable, unpredictable side effect — not a lever you can control.

---

## 2. Thinking Token Mechanics

MedGemma 4B uses special tokens for internal chain-of-thought:

- **`<unused94>`** — opens thinking block
- **`<unused95>`** — closes thinking block (rarely emitted)
- When triggered, the model produces ~475–616 words of structured numbered reasoning inside the thinking block
- The close tag was emitted in only 1 out of 22 triggering cases — meaning 95% of the time, the thinking block runs to the token limit without closing
- When thinking fires, visible output drops to **0 words** in most cases — the model spends its entire token budget on internal reasoning

Thinking content follows a consistent pattern:
> "Here's a thinking process for [topic]: 1. **Identify the core question:** ... 2. **Consider comorbidities:** ..."

---

## 3. Temperature

Tested: 0.0, 0.3, 0.6, 1.0 across 5 query types (simple, reasoning, complex, drug, ambiguous).

| Temperature | Thinking Rate | Avg Visible Words | Avg Latency |
|:-----------:|:-------------:|:-----------------:|:-----------:|
| 0.0 | 1/5 (20%) | 484 | 16,660ms |
| 0.3 | 0/5 (0%) | 456 | 12,513ms |
| 0.6 | 0/5 | 505 | 13,211ms |
| 1.0 | 1/5 (20%) | 455 | 15,655ms |

**Findings:**

- Thinking tokens appear only at the extremes (T=0.0, T=1.0), never at moderate temperatures (0.3, 0.6)
- Both extreme triggers occurred on the **ambiguous** query ("Is metformin safe?") — not on complex clinical queries
- T=0.3 produced the **lowest latency** (12.5s avg vs 16.7s at T=0.0) with no thinking-token noise
- Visible word count is roughly stable across temperatures (455–505)

**Takeaway:** T=0.3 is the most predictable operating point. Thinking tokens at T=0.0 and T=1.0 are anomalous responses to ambiguity, not a controllable feature.

---

## 4. System Prompts

Tested 5 system prompt variants, each on reasoning + complex queries:

| System Prompt | Description | Thinking Tokens | Gemini Score (avg) |
|---------------|-------------|:---------------:|:------------------:|
| clinical_assistant | Detailed clinical identity | 0/2 | 9.0 |
| think_first | "Think carefully before answering" | 0/2 | 9.0 |
| chain_of_thought | "Use chain-of-thought reasoning" | 0/2 | 9.0 |
| minimal | "You are a medical assistant" | 0/2 | 7.0 |
| none | No system prompt at all | 0/2 | 8.5 |

**Findings:**

- **Zero thinking tokens from any system prompt** (0/10)
- Explicit CoT or "think first" instructions have **no effect** on thinking token emission
- However, system prompts DO affect visible output quality: detailed clinical prompts score 9.0, while overly minimal ones score 7.0
- No system prompt (8.5) actually outperforms an overly generic minimal prompt (7.0) — a vague identity hurts more than no identity
- The three detailed variants (clinical_assistant, think_first, chain_of_thought) all score identically (9.0), suggesting the model responds to domain framing but ignores reasoning strategy instructions

**Takeaway:** System prompts influence output quality through domain framing, not reasoning strategy. "Think carefully" does nothing; "You are a clinical decision-support assistant" helps.

---

## 5. User Trigger Phrases

Tested 10 user-message trigger phrases, each on reasoning + complex queries:

| Trigger Phrase | Thinking Tokens | Gemini Score (avg) |
|----------------|:---------------:|:------------------:|
| "Think step by step" | 0/2 | 9.0 |
| "Reason carefully" | 0/2 | 9.0 |
| "First analyze, then answer" | 0/2 | 9.0 |
| "Let's think about this" | 0/2 | 8.5 |
| "Explain your reasoning" | 0/2 | 8.5 |
| "Show your work" | 0/2 | 9.0 |
| "Before answering, consider..." | 0/2 | 9.0 |
| "What factors should be considered?" | 0/2 | 7.0 |
| "Apply clinical reasoning" | 0/2 | 9.0 |
| plain (no trigger) | 0/2 | 8.0 |

**Findings:**

- **Zero thinking tokens from any user trigger phrase** (0/20)
- Classic prompting techniques ("think step by step", "show your work") have absolutely no effect on thinking token activation
- Quality-wise, most trigger phrases score 9.0 — slightly above the plain baseline (8.0)
- The trigger phrases improve visible output formatting (structured headers, numbered steps) without activating internal thinking
- "What factors should be considered?" underperforms (7.0), possibly because it's too open-ended for the 4B model

**Takeaway:** User trigger phrases are completely inert for thinking token control. They mildly improve output structure through surface-level formatting.

---

## 6. Assistant Prefix Priming

Tested 7 assistant-turn prefixes (pre-filled start of the model's response), each on reasoning + complex queries:

| Prefix | Type | Reasoning | Complex | Total Rate |
|--------|------|:---------:|:-------:|:----------:|
| "Let me think through this..." | Cognitive verb | T(538) | . | 1/2 |
| "My analysis:" | Cognitive noun | T(498) | . | 1/2 |
| "Considering the clinical factors..." | Cognitive verb | T(535) | T(575) | 2/2 |
| "**Clinical Reasoning:**" | Header format | T(515) | . | 1/2 |
| "Internal considerations:" | Abstract noun | . | . | 0/2 |
| "1. " | Numbered list start | . | . | 0/2 |
| "Let me work through the differential..." | Cognitive verb | T(511) | . | 1/2 |

**Findings:**

- **6/14 triggered thinking** (43%) — the only single-technique strategy with meaningful trigger rates
- Cognitive verbs ("think", "analyze", "consider") consistently trigger thinking on reasoning queries
- Only "Considering the clinical factors..." triggered on BOTH reasoning and complex queries
- Structural prefixes ("1.", "Internal considerations:") never trigger thinking
- When thinking fires from a prefix, visible output drops to **0 words** — the model goes fully internal

**Takeaway:** Assistant prefix priming is the most effective single technique. Cognitive verbs activate thinking; structural cues do not. But it only works ~50% of the time on reasoning queries and rarely on complex queries.

---

## 7. Combined Strategies

Tested 5 combinations of system prompt + assistant prefix, each on reasoning + complex queries:

| Combination | Reasoning | Complex | Total Rate |
|-------------|:---------:|:-------:|:----------:|
| full_chain (CoT system + "Let me think..." prefix) | T(475) | T(616) | 2/2 |
| reactive_fill (clinical system + "My analysis:" prefix) | T(509) | T(604) | 2/2 |
| socratic (Socratic system + "Considering..." prefix) | T(539) | T(592) | 2/2 |
| minimal_reactive (minimal system + "Let me think..." prefix) | T(543) | T(588) | 2/2 |
| structured_reactive (structured system + "1. " prefix) | . | . | 0/2 |

**Findings:**

- **8/10 triggered thinking** (80%) — the highest rate of any category
- 4 out of 5 combinations achieved **100% trigger rate** on both reasoning and complex queries
- The one failure (structured_reactive) used the structural "1." prefix, which never works alone either
- Thinking depth was highest in this category: up to 616 words (combo-full_chain-complex)
- The system prompt variant barely matters — minimal_reactive (bare-bones system + cognitive prefix) works as well as full_chain (CoT system + cognitive prefix)

**Takeaway:** Combining any system prompt with a cognitive-verb prefix achieves the most reliable thinking activation. The prefix does the heavy lifting; the system prompt provides context. The "1." prefix is dead weight regardless of system prompt.

---

## 8. Guided Generation (Outlines)

Tested 3 JSON schemas (ThinkThenAnswer, ReasoningConfidence, DiagnosticAssessment), with and without prefix priming.

| Setup | Thinking Tokens | Gemini Score (avg) |
|-------|:---------------:|:------------------:|
| Guided only (3 schemas × 2 queries) | 0/6 | 8.5 |
| Guided + prefix priming (3 combos × 2 queries) | 0/6 | 8.8 |
| **Total** | **0/12** | **8.7** |

**Findings:**

- **Zero thinking tokens across all 12 guided-generation tests** — including when combined with prefix priming that works in free-form mode
- Outlines schema constraints completely suppress `<unused94>` token emission
- However, the model redirects its reasoning INTO the JSON fields. When given a `thinking` field, it populates it with quality reasoning:

```json
{
  "thinking": "The user is asking for a recommendation for an antihypertensive...",
  "answer": "Okay, let's break down the patient's profile and th..."
}
```

- Similarly, `reasoning`, `differential`, `key_findings` fields all receive structured analysis
- Gemini judge still rated these 8.5–8.8 on average, only slightly below free-form (8.7 baseline across categories)
- Prefix priming that reliably triggers thinking in free-form (e.g., "Let me think...") has **no effect** when Outlines is active

**Takeaway:** Guided generation and thinking tokens are mutually exclusive. The schema constraint redirects reasoning into visible JSON fields instead of hidden tokens. This is arguably preferable — you get transparent, parseable reasoning at the cost of internal thinking.

---

## 9. Max Tokens

Tested budgets from 128 to 2048 on reasoning + complex queries:

| Budget | Thinking Tokens | Avg Visible Words | Avg Latency | Gemini Score (avg) |
|-------:|:---------------:|:-----------------:|:-----------:|:------------------:|
| 128 | 0/2 | 78 | 2,184ms | 7.0 |
| 256 | 0/2 | 157 | 4,210ms | 7.5 |
| 512 | 0/2 | 315 | 8,468ms | 8.5 |
| 1024 | 0/2 | 586 | 16,815ms | 8.0 |
| 2048 | 0/2 | 836 | 24,534ms | 9.0 |

**Findings:**

- **Zero thinking tokens at any budget** (0/10) — token budget does not trigger thinking
- The model uses roughly all available tokens: visible word count scales nearly linearly with budget
- Latency scales linearly with token budget (~12ms per word)
- Quality improves with budget: 7.0 at 128 tokens → 9.0 at 2048
- The 512→1024 jump provides diminishing returns (8.5 → 8.0, anomalous) while 1024→2048 shows clear improvement (8.0 → 9.0)

**Takeaway:** More tokens = more detail = better Gemini scores, but with linear latency cost. The model never "decides" to start thinking based on having more room. Token budget is purely a quality-vs-latency knob.

---

## 10. Multi-Turn Context

Tested 4 conversation history scenarios, each on reasoning + complex queries:

| History Type | Thinking Rate | Gemini Score (avg) |
|-------------|:-------------:|:------------------:|
| Cold start (no history) | 0/2 | 8.5 |
| Prior simple exchange ("What is hypertension?" + answer) | 2/2 | 9.5 |
| Prior reasoning exchange (clinical Q + detailed answer) | 2/2 | 9.5 |
| Explicit thinking in history (response with thinking tokens) | 2/2 | 9.0 |

**Findings:**

- **6/8 triggered thinking** (75%) — second highest rate after combined strategies
- Cold starts NEVER trigger thinking; ANY prior exchange does (100% when history exists)
- The complexity of prior history doesn't matter much: a simple "What is hypertension?" exchange triggers thinking as reliably as a detailed clinical reasoning exchange
- Gemini scores are highest in this category (9.0–9.5), suggesting multi-turn context improves overall quality beyond just triggering thinking

**Takeaway:** Conversation history is the strongest natural trigger for thinking tokens. Even trivial prior exchanges prime the model for deeper engagement. This is likely the most important finding for production systems: if you want the model to reason deeply, give it context.

---

## 11. The Hidden Thinking Phenomenon

The most surprising result: **massive disagreement between thinking token detection and actual reasoning quality.**

| Metric | Value |
|--------|------:|
| Token-detected thinking | 22/104 (21.2%) |
| Gemini-judged as reasoning | 93/97 (95.9%) |
| Agreement (both say yes or both say no) | 25/97 (26%) |
| **Hidden thinking** (no token, Gemini says yes) | **72 cases** |
| Overt thinking (token present, Gemini says yes) | 21 cases |
| No reasoning (both say no) | 4 cases |

### Score Distribution

| Score | Count | With Token | Without Token |
|------:|------:|-----------:|--------------:|
| 10 | 6 | 6 | 0 |
| 9 | 57 | 15 | 42 |
| 8 | 20 | 0 | 20 |
| 7 | 8 | 0 | 8 |
| 6 | 2 | 0 | 2 |
| 2 | 3 | 0 | 3 |
| 1 | 1 | 0 | 1 |

**Observations:**

- Score 10 correlates perfectly with thinking tokens — all 6 perfect scores had `<unused94>` present
- But 42 cases scored 9/10 WITHOUT any thinking token — demonstrating excellent reasoning in visible output
- The 8-score tier (20 cases) is entirely token-free — solid reasoning without internal deliberation
- Low scores (1-2) correspond to simple definitional queries ("What is hypertension?") where reasoning isn't expected
- The Gemini judge confirms: the model naturally produces structured clinical analysis ("Okay, let's break down...") as a baseline behavior

### Example of Hidden Thinking (No Token, Score 9)

From `trigger-think_step_by_step-reasoning`:
> "Okay, let's break down the recommendations for an antihypertensive in this 65-year-old male with CKD stage 3 and diabetes. **Patient Profile:** ..."

No `<unused94>` token. Gemini score: 9/10. Rationale: "The model provides a structured, step-by-step analysis of the patient's condition."

**Takeaway:** The model reasons in the open. Thinking tokens add a score boost from 9 to 10 in some cases, but 9-quality reasoning is the baseline behavior for clinical queries. Systems should not depend on triggering thinking tokens to get good reasoning.

---

## 12. Trigger Heatmap

Which (strategy x query) combinations fire thinking tokens?

| Strategy | simple | reasoning | complex | drug | ambiguous |
|----------|:------:|:---------:|:-------:|:----:|:---------:|
| baseline-t0.0 | . | . | . | . | T(598) |
| baseline-t0.3 | . | . | . | . | . |
| baseline-t0.6 | . | . | . | . | . |
| baseline-t1.0 | . | . | . | . | T(606) |
| combo-full_chain | - | T(475) | T(616) | - | - |
| combo-reactive_fill | - | T(509) | T(604) | - | - |
| combo-socratic | - | T(539) | T(592) | - | - |
| combo-minimal_reactive | - | T(543) | T(588) | - | - |
| combo-structured_reactive | - | . | . | - | - |
| prefix-think_start | - | T(538) | . | - | - |
| prefix-analysis_start | - | T(498) | . | - | - |
| prefix-considering | - | T(535) | T(575) | - | - |
| prefix-reasoning_header | - | T(515) | . | - | - |
| prefix-differential_start | - | T(511) | . | - | - |
| prefix-internal_monologue | - | . | . | - | - |
| prefix-structured_start | - | . | . | - | - |
| multiturn-cold_start | - | . | . | - | - |
| multiturn-prior_simple | - | T(556) | T(598) | - | - |
| multiturn-prior_reasoning | - | T(491) | T(553) | - | - |
| multiturn-explicit_think | - | T(492) | T(580) | - | - |
| All system prompts (5) | - | . | . | - | - |
| All user triggers (10) | - | . | . | - | - |
| All guided generation (6) | - | . | . | - | - |
| All guided+priming (6) | - | . | . | - | - |
| All max_tokens (5) | - | . | . | - | - |

_T(n) = thinking triggered with n words. `.` = no thinking. `-` = not tested._

**Patterns visible in the heatmap:**

1. Thinking concentrates on **reasoning** and **complex** queries. Simple, drug, and ambiguous queries almost never trigger (2 exceptions at extreme temperatures).
2. The **simple** and **drug** query types NEVER triggered thinking under any strategy.
3. **Complex** queries require stronger triggers than **reasoning** queries — most prefix-only strategies trigger on reasoning but not complex.
4. Combined strategies and multi-turn history are the only approaches that reliably trigger on BOTH reasoning and complex.

---

## 13. Implications

### What the experiment tells us

1. **Thinking tokens are not a prompt-controllable feature.** System prompts and user messages have zero effect. Only assistant prefixes, combined strategies, and multi-turn history activate them — and even these are query-dependent.

2. **The model reasons well without thinking tokens.** 95.9% of responses demonstrate reasoning to an external judge. The visible output naturally includes structured clinical analysis. Building systems that require thinking token activation is unnecessary.

3. **Guided generation and thinking are mutually exclusive.** Outlines schema constraints completely suppress `<unused94>` tokens. Reasoning moves into explicit JSON fields instead. This is actually beneficial — it makes reasoning transparent and parseable.

4. **Multi-turn context is the most natural quality lever.** Any prior exchange primes the model for deeper reasoning. This is passive (no special prompting needed) and reliable (100% trigger rate with history).

5. **Temperature extremes are unpredictable.** T=0.0 and T=1.0 occasionally trigger thinking on ambiguous queries. T=0.3 is the stable operating point with the lowest latency and no thinking-token surprises.

6. **The close tag is effectively broken.** `<unused95>` appeared in only 1/22 cases. Any system using thinking tokens must handle unterminated blocks.

7. **Score 10 requires thinking tokens; score 9 does not.** If you need perfect Gemini-judge scores, you need thinking tokens. If 9/10 is sufficient (and it is for production), the model delivers it as baseline behavior.

### What the experiment does NOT tell us

- Whether thinking tokens improve factual accuracy (Gemini judged reasoning quality, not correctness)
- How these behaviors change with fine-tuning or different quantization
- Whether findings generalize to non-clinical domains
- Long-context behavior (our max was ~2 turns of history)

---

## Appendix: Test Queries

| Key | Query |
|-----|-------|
| simple | "What is hypertension?" |
| reasoning | "Recommend an antihypertensive for a 65-year-old male with CKD stage 3 and diabetes" |
| complex | "Patient presents with sudden onset chest pain, diaphoresis, shortness of breath. ECG shows ST elevation in leads II, III, aVF. Troponin pending. What is the differential diagnosis and immediate management plan?" |
| drug | "What are the risks of combining warfarin and aspirin in an elderly patient with atrial fibrillation?" |
| ambiguous | "Is metformin safe?" |

## Appendix: Category Summary

| Category | Tests | Thinking Rate | Avg Gemini Score |
|----------|------:|:-------------:|-----------------:|
| Baseline Temperature | 20 | 2/20 (10%) | 6.7 |
| System Prompt | 10 | 0/10 (0%) | 8.5 |
| Prefix Priming | 14 | 6/14 (43%) | 9.0 |
| User Triggers | 20 | 0/20 (0%) | 8.7 |
| Combined Strategies | 10 | 8/10 (80%) | 9.2 |
| Guided Generation | 6 | 0/6 (0%) | 8.5 |
| Guided + Priming | 6 | 0/6 (0%) | 8.8 |
| Max Tokens | 10 | 0/10 (0%) | 8.0 |
| Multi-Turn | 8 | 6/8 (75%) | 9.1 |

## Appendix: Top 10 by Thinking Depth

| Rank | Experiment | Words | Latency |
|-----:|-----------|------:|--------:|
| 1 | combo-full_chain-complex | 616 | 16,725ms |
| 2 | baseline-t1.0-ambiguous | 606 | 17,158ms |
| 3 | combo-reactive_fill-complex | 604 | 16,754ms |
| 4 | baseline-t0.0-ambiguous | 598 | 17,333ms |
| 5 | multiturn-prior_simple-complex | 598 | 16,819ms |
| 6 | combo-socratic-complex | 592 | 16,934ms |
| 7 | combo-minimal_reactive-complex | 588 | 16,975ms |
| 8 | multiturn-explicit_think-complex | 580 | 17,017ms |
| 9 | prefix-considering-complex | 575 | 16,640ms |
| 10 | multiturn-prior_simple-reasoning | 556 | 16,764ms |

---
---

# Part II — Tool Selection & Argument Extraction Experiment Findings

**Experiments:** 320 across 8 categories (~540 LLM calls)
**Data:** `tool_selection_experiments/20260211_031223/`

Probed 8 prompting strategies for selecting among 10 tools and extracting structured arguments under Outlines constrained generation. 20 test queries spanning clear single-tool (10), ambiguous (5), and complex-argument (5) cases. Deterministic eval + Gemini 2.0 Flash judge (100% agreement on tool correctness).

---

## Table of Contents (Part II)

14. [Executive Summary](#14-executive-summary)
15. [Strategy Ranking](#15-strategy-ranking)
16. [Tool Description Verbosity](#16-tool-description-verbosity)
17. [Two-Stage vs Joint Selection](#17-two-stage-vs-joint-selection)
18. [Prefix Completion](#18-prefix-completion)
19. [Few-Shot Scaling](#19-few-shot-scaling)
20. [Field Ordering — The Null Cascade](#20-field-ordering--the-null-cascade)
21. [Boolean Probing — Failure Mode](#21-boolean-probing--failure-mode)
22. [Reasoning-Then-Select — Overthinking](#22-reasoning-then-select--overthinking)
23. [Tool Confusion Matrix](#23-tool-confusion-matrix)
24. [Argument Extraction Patterns](#24-argument-extraction-patterns)
25. [Thinking Tokens Hurt Tool Selection](#25-thinking-tokens-hurt-tool-selection)
26. [Latency Budget](#26-latency-budget)
27. [Implications for Production](#27-implications-for-production)

---

## 14. Executive Summary

- **Tool exact match:** 251/320 (78.4%)
- **Tool acceptable match:** 281/320 (87.8%)
- **Arg value accuracy:** 399/528 (75.6%)
- **Best strategy:** `full_desc` — 95% exact, 100% acceptable, 94% arg accuracy
- **Worst strategy:** `boolean_probe` — 25% exact (complete failure)
- **Thinking tokens correlated with WORSE tool selection:** 55% exact vs 80% baseline
- **Gemini judge agreed with deterministic eval on tool correctness:** 320/320 (100%)
- **Avg latency (single-call strategies):** ~900ms. Multi-call: 1.8–9.3s

**The core finding:** The 4B model already knows which tool to pick from the tool name alone. The bottleneck is argument extraction, not tool selection. Field ordering in the schema is the single most impactful lever for arg quality, and splitting selection from args (two-stage) fixes edge cases.

---

## 15. Strategy Ranking

All 16 strategies ranked by tool exact match rate (20 queries each):

| Rank | Strategy | Category | Tool Exact | Tool Accept | Arg Accuracy | Latency |
|-----:|----------|----------|:----------:|:-----------:|:------------:|--------:|
| 1 | full_desc | Description Verbosity | **95%** | **100%** | **94%** | 987ms |
| 1 | names_only | Description Verbosity | **95%** | **100%** | 88% | 930ms |
| 3 | two_stage | Joint vs Two-Stage | **90%** | **100%** | 88% | 1,827ms |
| 4 | 1shot | Few-Shot Variation | 85% | 95% | 91% | 811ms |
| 4 | 3shot | Few-Shot Variation | 85% | 95% | 79% | 887ms |
| 4 | prefix_analytical | Prefix Completion | 85% | 95% | 88% | 911ms |
| 7 | baseline | Direct Baseline | 80% | 90% | 88% | 889ms |
| 7 | 0shot | Few-Shot Variation | 80% | 90% | 76% | 859ms |
| 7 | 10shot | Few-Shot Variation | 80% | 90% | 88% | 901ms |
| 7 | prefix_cognitive | Prefix Completion | 80% | 90% | 91% | 914ms |
| 7 | short_desc | Description Verbosity | 80% | 90% | 88% | 897ms |
| 7 | joint | Joint vs Two-Stage | 80% | 90% | 88% | 895ms |
| 7 | critical_first | Field Ordering | 80% | 90% | 88% | 902ms |
| 7 | critical_last | Field Ordering | 80% | 90% | **21%** | 878ms |
| 15 | reasoning_then_select | Reasoning-Then-Select | 55% | 65% | 55% | 9,349ms |
| 16 | boolean_probe | Boolean Probing | 25% | 35% | 0% | 2,396ms |

**Observations:**

- A large cluster at 80% (current production level). Breaking above 80% requires either richer descriptions, two-stage, 1-shot matching, or analytical prefix.
- The bottom two strategies (reasoning_then_select, boolean_probe) are dramatically worse — multi-call doesn't help when the calls themselves are poorly designed.
- `critical_last` has 80% tool accuracy but 21% arg accuracy — tool selection is robust to field ordering, but arg extraction is not.

---

## 16. Tool Description Verbosity

Tested three levels of tool descriptions in the prompt:

| Level | Example Format | Tool Exact | Tool Accept | Arg Accuracy |
|-------|---------------|:----------:|:-----------:|:------------:|
| **names_only** | `- check_drug_safety` | 95% | 100% | 88% |
| **short_desc** | `- check_drug_safety: drug_name (FDA boxed warnings)` | 80% | 90% | 88% |
| **full_desc** | `- check_drug_safety(drug_name: str) — Look up FDA boxed warnings...` | 95% | 100% | 94% |

**Findings:**

- **The model already knows what tools do from their names.** `names_only` (95%) matches `full_desc` (95%) and both significantly outperform `short_desc` (80%).
- `short_desc` is our current production format and is the WORST of the three. The parenthetical arg hints may actually confuse the model.
- `full_desc` achieves the highest arg accuracy (94%), likely because the multi-sentence descriptions clarify which args are needed for each tool.
- `names_only` fixes Q-11 ("Is metformin safe?") and Q-15 ("Check amoxicillin information") that `short_desc` gets wrong — suggesting the short descriptions mislead the model on ambiguous queries.

**Takeaway:** Either use just tool names (cheapest prompt tokens) or full verbose descriptions (best overall). The middle ground (one-line descriptions) is the worst option. For production, `full_desc` is recommended because it has the highest arg accuracy while matching `names_only` on tool selection.

---

## 17. Two-Stage vs Joint Selection

Compared single-call ToolCallV2 (all fields) vs two calls (ToolSelection → per-tool arg schema):

| Approach | Tool Exact | Tool Accept | Arg Accuracy | Avg Latency | Calls |
|----------|:----------:|:-----------:|:------------:|------------:|------:|
| **Joint** | 80% | 90% | 88% | 895ms | 1 |
| **Two-stage** | **90%** | **100%** | 88% | 1,827ms | 2 |

**Per-query delta (two-stage improvements):**

- **Q-14** (patient lookup): joint missed `name` arg, two-stage got it
- **Q-15** ("Check amoxicillin info"): joint→`get_patient_chart` (WRONG), two-stage→`check_drug_safety` (CORRECT)
- **Q-20** ("Write a note..."): joint→`get_patient_chart` (WRONG), two-stage→`save_clinical_note` (CORRECT)

**Why it works:** When the model only has to output `tool_name` (ToolSelection schema — 1 field), there are no irrelevant nullable fields creating null-cascade pressure. Then the per-tool arg schema has only the relevant fields (e.g., `DrugSafetyArgs` has just `drug_name`), so the model can't fill wrong fields.

**Tradeoffs:**
- +2x latency (two serial calls)
- +100% tool acceptance (every query gets an acceptable tool)
- Same arg accuracy (88% both) — the per-tool schemas don't help args much because the 10-shot examples already teach arg patterns well

**Takeaway:** Two-stage is worth the latency cost for edge cases. Consider it for the lookup/multi-step paths where tool selection accuracy matters most. The reasoning path already does two-stage naturally (think → extract_tool_needs).

---

## 18. Prefix Completion

Pre-filled the assistant's response with a cognitive prefix before Outlines constrained completion:

| Prefix | Tool Exact | Tool Accept | Arg Accuracy |
|--------|:----------:|:-----------:|:------------:|
| `"Given this task, I need to use "` (cognitive) | 80% | 90% | 91% |
| `"Analyzing the task requirements, "` (analytical) | **85%** | **95%** | 88% |

**Findings:**

- The `analytical` prefix improves tool selection by +5% over baseline (85% vs 80%), fixing Q-15 ("amoxicillin info") which baseline routes to `get_patient_chart`.
- The `cognitive` prefix ("I need to use") matches baseline (80%) — the completion trigger is too abrupt for the model.
- Both prefixes maintain or improve arg accuracy over baseline (88%).
- The analytical prefix likely works because "Analyzing the task requirements" primes the model to evaluate the query semantics before committing to a tool, whereas "I need to use" immediately forces tool selection.

**Takeaway:** The `analytical` prefix is a lightweight 5% improvement for free (no extra LLM calls, ~20ms latency cost). Use it if not using two-stage.

---

## 19. Few-Shot Scaling

Tested 0, 1, 3, and 10 examples in the prompt:

| Shots | Tool Exact | Tool Accept | Args Correct / Total |
|------:|:----------:|:-----------:|:--------------------:|
| 0 | 80% | 90% | 25/33 (76%) |
| **1** | **85%** | **95%** | **30/33 (91%)** |
| 3 | 85% | 95% | 26/33 (79%) |
| 10 | 80% | 90% | 29/33 (88%) |

**Findings:**

- **1-shot is the sweet spot.** 85% tool exact, 91% arg accuracy — best across both dimensions.
- The 1-shot example is matched to the expected tool type (e.g., for a drug safety query, the example is a drug safety example). This targeted matching outperforms 3 diverse examples.
- **0-shot works surprisingly well** for tool selection (80%) but has the worst arg accuracy (76%). The model knows tool semantics but needs examples to learn arg patterns.
- **10-shot provides no advantage** over 0-shot on tool selection (both 80%). The extra examples may cause the model to pattern-match surface features rather than semantic intent.
- **3-shot matches 1-shot** on tool selection (85%) but has worse arg accuracy (79%). The diverse examples (drug safety, patient chart, clinical note) may teach conflicting arg patterns.

**Takeaway:** For production prompts, include exactly 1 example matching the tool type from the triage/decompose stage. For the plan_tool prompt where you know `suggested_tool`, show only that tool's example. If `suggested_tool` is unknown, 3-shot diverse examples are the next best option.

---

## 20. Field Ordering — The Null Cascade

Tested the ToolCallV2 schema in two field orderings under Outlines:

| Ordering | Tool Exact | Tool Accept | Args Correct / Total |
|----------|:----------:|:-----------:|:--------------------:|
| **critical_first** (production) | 80% | 90% | **29/33 (88%)** |
| **critical_last** (reversed nullables) | 80% | 90% | **7/33 (21%)** |

**Per-query arg comparison:**

| Query | Critical-First | Critical-Last | Delta |
|-------|:--------------:|:-------------:|:-----:|
| Q-07 (add_allergy, 4 args) | 4/4 | 1/4 | -3 |
| Q-08 (prescribe_med, 4 args) | 4/4 | 1/4 | -3 |
| Q-09 (clinical_note, 3 args) | 3/3 | 1/3 | -2 |
| Q-16 (prescribe_med, 4 args) | 4/4 | 1/4 | -3 |
| Q-01 (drug_safety, 1 arg) | 1/1 | 0/1 | -1 |
| Q-06 (patient_chart, 1 arg) | 1/1 | 1/1 | 0 |

**What happens in `critical_last`:** With Outlines/vLLM, the model generates JSON fields in schema property order. In `ToolCallV2Reversed`, nullable fields like `note_type`, `note_text`, `frequency` come first. The model fills these with `null`, establishing a "null momentum" pattern. By the time it reaches the critical fields (`query`, `drug_name`, `patient_id`) at the end, it's locked into emitting `null` for everything.

**The only field that survives reversed ordering** is `patient_id` when it appears in queries that explicitly contain a UUID-like string (e.g., Q-06: "patient abc-123"). The model picks up on the pattern match regardless of field position. But semantic extraction (drug names from context, queries from intent) fails completely.

**Takeaway:** This is the most important finding for schema design. Field ordering in Pydantic schemas for Outlines is not cosmetic — it determines whether arguments get extracted at all. Always put the decision-critical fields (`tool_name` → `patient_id` → `query` → tool-specific args) before nullable/optional fields. The current production ToolCallV2 ordering is correct.

---

## 21. Boolean Probing — Failure Mode

For each query, asked the model "Is {tool} suitable? true/false" for all 10 tools:

| Metric | Value |
|--------|------:|
| Tool exact match | 5/20 (25%) |
| Tool acceptable | 7/20 (35%) |
| Multi-true rate (>1 tool marked suitable) | 19/20 (95%) |
| Zero-true rate | 0/20 |
| Average tools marked suitable per query | 6.5/10 |

**Per-tool true rate (how often each tool was marked suitable):**

| Tool | True Rate | Expected Queries |
|------|:---------:|:----------------:|
| search_medical_literature | 18/20 (90%) | 2 |
| prescribe_medication | 15/20 (75%) | 2 |
| get_patient_chart | 14/20 (70%) | 1 |
| check_drug_safety | 13/20 (65%) | 3 |
| find_clinical_trials | 13/20 (65%) | 1 |
| search_patient | 13/20 (65%) | 2 |
| check_drug_interactions | 12/20 (60%) | 2 |
| analyze_medical_image | 12/20 (60%) | 1 |
| save_clinical_note | 11/20 (55%) | 2 |
| add_allergy | 8/20 (40%) | 2 |

**Why it fails:** The 4B model lacks the discrimination ability to evaluate tools in isolation. When asked "Is X suitable for this task?", it considers any plausible connection and answers `true`. `search_medical_literature` is marked suitable for 90% of queries because almost any medical question could theoretically benefit from a literature search. The "first true wins" aggregation then always picks whichever tool appears first in the probe order.

**Takeaway:** Boolean probing is fundamentally incompatible with a 4B model. The model needs to see all tools simultaneously and make a comparative judgment, not evaluate each in isolation. Do not use this approach.

---

## 22. Reasoning-Then-Select — Overthinking

Two-stage: free-form reasoning (T=0.3) about which tool to use, then constrained selection (T=0.0):

| Metric | Value |
|--------|------:|
| Tool exact | 11/20 (55%) |
| Tool acceptable | 13/20 (65%) |
| Arg accuracy | 55% |
| Avg latency | 9,349ms (10.5x baseline) |

**Failure patterns:**

- Q-01 ("Check FDA warnings for dofetilide"): Free-form reasoning discusses literature review → selects `search_medical_literature` instead of `check_drug_safety`
- Q-04 ("Find clinical trials"): Reasoning focuses on evidence → selects `search_medical_literature` instead of `find_clinical_trials`
- Q-07 ("Document allergy"): Reasoning discusses chart review → selects `get_patient_chart` instead of `add_allergy`
- Q-16 ("Prescribe lisinopril"): Reasoning discusses patient chart → selects `get_patient_chart` instead of `prescribe_medication`

**Why it fails:** The 4B model's free-form reasoning about tool choice introduces semantic drift. The model over-reasons about what information would be helpful rather than what action the query is asking for. "Check FDA warnings" gets reinterpreted as "I should research this drug" → literature search. The intermediate reasoning corrupts the downstream constrained selection.

**Takeaway:** Don't ask a 4B model to reason about meta-decisions (which tool to use). It does better when you let Outlines constrain the choice directly. Reasoning is valuable for clinical analysis (the `thinking_mode` node), not for operational decisions.

---

## 23. Tool Confusion Matrix

Aggregated across all 320 experiments (rows = expected, columns = selected):

| Expected | Top Confusion | Confusion Rate | Root Cause |
|----------|--------------|:--------------:|------------|
| check_drug_safety | → search_medical_literature | 14/48 (29%) | "Safety info" interpreted as "literature search" |
| check_drug_safety | → get_patient_chart | 9/48 (19%) | "For my patient" triggers EHR tool |
| find_clinical_trials | → search_medical_literature | 18/32 (56%) | "Treatments" / "studies" overlap |
| save_clinical_note | → get_patient_chart | 12/32 (38%) | "Patient abc-123" triggers chart retrieval |
| check_drug_interactions | → check_drug_safety | 3/48 (6%) | Drug-focused queries overlap |
| prescribe_medication | → get_patient_chart | 1/32 (3%) | Minor — "patient" trigger |

**Persistent misroutes across nearly all strategies:**

1. **Q-15** ("Check amoxicillin information for my patient") → `get_patient_chart` in 10/16 strategies. The phrase "for my patient" overrides the drug safety intent. Fixed by: `full_desc`, `names_only`, `two_stage`, `1shot`, `3shot`, `prefix_analytical`.
2. **Q-20** ("Write a note for patient abc-123...") → `get_patient_chart` in 12/16 strategies. "Patient abc-123" triggers chart retrieval instead of note-saving. Fixed by: `full_desc`, `names_only`, `two_stage`.
3. **Q-11** ("Is metformin safe for a patient with CKD stage 4?") → `search_medical_literature` in 14/16 strategies. Routed as acceptable alternative — this is truly ambiguous.
4. **Q-13** ("Are there any new treatments for multiple sclerosis?") → `search_medical_literature` in 14/16 strategies. Also a legitimate ambiguity.

**Takeaway:** The two hard failures (Q-15, Q-20) share a pattern: the phrase "patient" or a patient ID in the query biases the model toward `get_patient_chart` regardless of the actual intent. The strategies that fix this (full_desc, names_only, two_stage) do so by either making tool boundaries clearer or by isolating tool selection from arg distraction.

---

## 24. Argument Extraction Patterns

Across all 320 experiments:

| Argument | Miss Rate | Correct Rate | Notes |
|----------|:---------:|:------------:|-------|
| patient_id | **6.2%** | 93.8% | Best — UUID-like strings are easy to extract |
| dosage | 12.5% | 87.5% | Good — "500mg" is an obvious pattern |
| frequency | 12.5% | 87.5% | Good — "twice daily" is obvious |
| query | 12.5% | 70.0% | Present but value often too specific/generic |
| medication_name | 15.6% | 84.4% | Good — drug names are salient |
| reaction | 18.8% | 81.2% | OK — "anaphylaxis" is extractable |
| substance | 18.8% | 81.2% | OK — allergen names are extractable |
| note_text | 18.8% | 43.8% | Poor value match — model paraphrases |
| severity | 25.0% | 75.0% | Sometimes omitted when implicit |
| note_type | 25.0% | 68.8% | "progress-note" vs "clinical-note" confusion |
| drug_name | **43.8%** | 56.2% | High miss — model puts drug in `query` instead |
| name | **50.0%** | 50.0% | Worst — patient names often put in `query` |

**Per-tool breakdown of problematic args:**

- **check_drug_safety → drug_name:** 27/48 correct. The model frequently puts the drug name in the `query` field instead. This is because `query` is a "universal" field that appears for many tools, while `drug_name` is tool-specific. The model defaults to the familiar field.
- **search_patient → name:** 16/32 correct. Same issue — patient name ends up in `query` instead of `name`.
- **save_clinical_note → note_text:** 14/32 correct. The model extracts the note content but often paraphrases or truncates it, failing fuzzy matching.
- **analyze_medical_image → query:** 0/16 correct. The model never extracts an analysis query because no image is actually attached — a test artifact.

**Takeaway:** The biggest arg extraction problem is field confusion: `drug_name` vs `query`, `name` vs `query`. The model gravitates toward "universal" fields. Solutions: (1) use per-tool arg schemas (two-stage) to eliminate ambiguity, (2) reinforce field-specific usage in examples, (3) consider renaming `query` to `search_query` to make it less of a catch-all.

---

## 25. Thinking Tokens Hurt Tool Selection

| Condition | Experiments | Tool Exact | Tool Accept |
|-----------|:----------:|:----------:|:-----------:|
| With `<unused94>` tokens | 20 | 55% | — |
| Without thinking tokens | 300 | 80% | — |

Thinking tokens appeared in 20/320 experiments (6.2%), concentrated in the `reasoning_then_select` category (free-form call 1 at T=0.3). When thinking tokens fire during a tool-selection task:

1. The model spends its token budget on internal deliberation about clinical nuances
2. This clinical reasoning introduces semantic drift (see [Section 22](#22-reasoning-then-select--overthinking))
3. The constrained output in the second call inherits the drifted context

**This is the opposite of the Part I finding** (thinking tokens associated with higher Gemini scores for clinical reasoning). For operational decisions like tool selection, thinking tokens are harmful noise. The 4B model should NOT be encouraged to "think" about which tool to use.

**Takeaway:** Use T=0.0 for all tool selection and arg extraction nodes. The Part I finding that T=0.3 is good for clinical reasoning does not extend to structured operational decisions.

---

## 26. Latency Budget

| Strategy | Avg Total | Avg Per-Call | Calls/Exp | Notes |
|----------|----------:|------------:|----------:|-------|
| 1shot | **811ms** | 811ms | 1 | Fastest — fewer prompt tokens |
| 0shot | 859ms | 859ms | 1 | |
| critical_last | 878ms | 878ms | 1 | |
| 3shot | 887ms | 887ms | 1 | |
| baseline/joint | 895ms | 895ms | 1 | Current production |
| short_desc | 897ms | 897ms | 1 | |
| critical_first | 902ms | 902ms | 1 | |
| prefix_* | ~912ms | ~912ms | 1 | ~2% overhead |
| names_only | 930ms | 930ms | 1 | |
| full_desc | 987ms | 987ms | 1 | +11% for best accuracy |
| two_stage | 1,827ms | 913ms | 2 | 2x for +10% tool accuracy |
| boolean_probe | 2,396ms | 240ms | 10 | Cheap per-call, useless total |
| reasoning_then_select | **9,349ms** | 4,675ms | 2 | 10x — free-form call is slow |

**Observations:**

- All single-call strategies cluster at 800–1000ms. The differences are from prompt token count (more examples = slightly more processing).
- Two-stage doubles latency but each call is ~900ms individually.
- reasoning_then_select is catastrophically slow because the free-form reasoning call generates many tokens at T=0.3.
- Boolean probing is cheap per-call (240ms for a single bool) but 10 calls total.
- 1-shot is the fastest because it has the fewest prompt tokens.

**Takeaway:** For production, the latency cost of improvements is modest. `full_desc` adds ~100ms for +15% tool accuracy. Two-stage adds ~900ms for +10%. The only strategies to avoid on latency grounds are reasoning_then_select (10x) and boolean_probe (useless anyway).

---

## 27. Implications for Production

### What to change

1. **Switch to `full_desc` tool descriptions** in `get_plan_prompt()`. This is the single highest-impact change: +15% tool exact accuracy over current `short_desc`, +6% arg accuracy, for only ~100ms extra latency. The verbose multi-sentence descriptions clarify tool boundaries and arg semantics.

2. **Use 1-shot examples matched to `suggested_tool`** instead of all 10. The `plan_tool` node already receives `suggested_tool` from triage/decompose — use it to select one matching example. Saves prompt tokens (faster) and improves both tool selection (+5%) and arg accuracy (+3%).

3. **Consider two-stage for the lookup path.** The lookup path is latency-tolerant (user is waiting for a tool result anyway). Two-stage eliminates the null-cascade problem and fixes the two persistent misroutes (Q-15, Q-20). The reasoning path already does this naturally via `extract_tool_needs`.

4. **Never put critical fields last in Outlines schemas.** The null-cascade effect is devastating (88% → 21% arg accuracy). This applies to any new schema added to the system. Rule: decision-critical fields first, tool-specific required fields next, nullable/optional fields last.

5. **Keep T=0.0 for all tool selection nodes.** T=0.3 is for reasoning; T=0.0 is for operational decisions. This was already correct in `TEMPERATURE` settings.

### What NOT to do

1. **Don't use boolean probing.** The 4B model can't discriminate tools in isolation. It needs comparative context (seeing all tools at once).

2. **Don't add a free-form reasoning step before tool selection.** It introduces semantic drift and 10x latency. The model over-reasons about what information would be useful rather than what action is requested.

3. **Don't use `short_desc` tool descriptions** (current production). They're actually worse than no descriptions at all for tool selection (80% vs 95% for `names_only`). The parenthetical arg hints create confusion.

4. **Don't add more examples beyond 3.** 10-shot provides no benefit over 0-shot (both 80%). The model pattern-matches surface features in examples rather than learning the intent→tool mapping. Fewer, better-targeted examples outperform many diverse ones.

### Recommended production configuration

```
Tool descriptions:  full_desc (multi-sentence per tool)
Examples:           1-shot (matched to suggested_tool)
Schema ordering:    critical-first (current ToolCallV2)
Temperature:        0.0
Assistant prefix:   "Analyzing the task requirements, " (optional, +5%)
Architecture:       Two-stage for lookup path (ToolSelection → per-tool args)
                    Joint ToolCallV2 for multi-step loop (latency-sensitive)
```

---

## Appendix: Test Queries (Part II)

### Clear Single-Tool (Q-01 to Q-10)

| ID | Query | Expected Tool |
|----|-------|---------------|
| Q-01 | "Check FDA boxed warnings for dofetilide" | check_drug_safety |
| Q-02 | "Search PubMed for SGLT2 inhibitor cardiovascular outcomes" | search_medical_literature |
| Q-03 | "Check drug interactions between warfarin and amiodarone" | check_drug_interactions |
| Q-04 | "Find clinical trials for triple-negative breast cancer" | find_clinical_trials |
| Q-05 | "Search for patient Maria Garcia in the EHR" | search_patient |
| Q-06 | "Get the clinical summary for patient abc-123" | get_patient_chart |
| Q-07 | "Document penicillin allergy with anaphylaxis for patient abc-123" | add_allergy |
| Q-08 | "Prescribe metformin 500mg twice daily for patient abc-123" | prescribe_medication |
| Q-09 | "Save a progress note for patient abc-123: BP well controlled" | save_clinical_note |
| Q-10 | "Analyze this chest X-ray for any abnormalities" | analyze_medical_image |

### Ambiguous (Q-11 to Q-15)

| ID | Query | Expected | Acceptable Alt |
|----|-------|----------|----------------|
| Q-11 | "Is metformin safe for a patient with CKD stage 4?" | check_drug_safety | search_medical_literature |
| Q-12 | "What are the risks of combining lisinopril with potassium?" | check_drug_interactions | check_drug_safety |
| Q-13 | "Are there any new treatments for multiple sclerosis?" | find_clinical_trials | search_medical_literature |
| Q-14 | "Look up patient James Wilson's medications" | search_patient | get_patient_chart |
| Q-15 | "Check amoxicillin information for my patient" | check_drug_safety | search_medical_literature |

### Arg Complexity (Q-16 to Q-20)

| ID | Query | Tool | Challenge |
|----|-------|------|-----------|
| Q-16 | "Patient f47ac10b needs lisinopril 10mg once daily" | prescribe_medication | All args explicit |
| Q-17 | "Document patient abc-123 allergic to sulfa drugs" | add_allergy | Reaction/severity implicit |
| Q-18 | "Find studies on GLP-1 agonists" | search_medical_literature | Minimal query |
| Q-19 | "Problem mixing warfarin, aspirin, and ibuprofen" | check_drug_interactions | 3 drugs, implicit tool |
| Q-20 | "Write note for patient abc-123: diabetes management, A1c 7.2" | save_clinical_note | Long implicit note_text |

## Appendix: Category Summary (Part II)

| Category | Experiments | Tool Exact | Tool Accept | Avg Arg Accuracy | Avg Latency |
|----------|:----------:|:----------:|:-----------:|:----------------:|------------:|
| Direct Baseline | 20 | 80% | 90% | 88% | 889ms |
| Prefix Completion | 40 | 82.5% | 92.5% | 90% | 912ms |
| Boolean Probing | 20 | 25% | 35% | 0% | 2,396ms |
| Reasoning-Then-Select | 20 | 55% | 65% | 55% | 9,349ms |
| Few-Shot Variation | 80 | 82.5% | 92.5% | 84% | 864ms |
| Tool Description Verbosity | 60 | 90% | 96.7% | 90% | 938ms |
| Joint vs Two-Stage | 40 | 85% | 95% | 88% | 1,361ms |
| Field Ordering | 40 | 80% | 90% | 55% | 890ms |

---
---

# Part III — Result Evaluation, Planning & Routing Experiment Findings

**Experiments:** 217 across 8 categories (~260 LLM calls)
**Data:** `result_routing_experiments/20260211_054317/`

Probed whether the 4B model can assess tool result quality, route next actions, plan multi-step tasks, judge information sufficiency, and recover from errors — all under Outlines constrained generation. 20 mock tool results, 10 multi-step tasks, 6 Pydantic schemas. Deterministic eval + Gemini 2.0 Flash judge (83.7% agreement).

---

## Table of Contents (Part III)

28. [Executive Summary](#28-executive-summary)
29. [Result Quality Assessment — Near-Perfect](#29-result-quality-assessment--near-perfect)
30. [Next-Action Routing — The ask_user Blind Spot](#30-next-action-routing--the-ask_user-blind-spot)
31. [Full-Plan Decomposition — Slot-Filling Pathology](#31-full-plan-decomposition--slot-filling-pathology)
32. [Reactive Step-by-Step — The Right Architecture](#32-reactive-step-by-step--the-right-architecture)
33. [Full-Plan vs Reactive Head-to-Head](#33-full-plan-vs-reactive-head-to-head)
34. [Sufficiency Assessment — The "Always Insufficient" Bias](#34-sufficiency-assessment--the-always-insufficient-bias)
35. [Error Recovery — Never Skips, Never Asks](#35-error-recovery--never-skips-never-asks)
36. [Thinking Prefixes Have No Effect](#36-thinking-prefixes-have-no-effect)
37. [Gemini Judge vs Deterministic Eval](#37-gemini-judge-vs-deterministic-eval)
38. [Latency Budget](#38-latency-budget)
39. [Implications for Production](#39-implications-for-production)

---

## 28. Executive Summary

- **Overall exact:** 97/210 (46.2%), **acceptable:** 123/210 (58.6%)
- **Result quality assessment:** 94.1% — essentially solved
- **Next-action routing:** 50% exact, 80% acceptable — workable but biased
- **Full-plan decomposition:** 0–10% exact — catastrophically broken
- **Reactive step-by-step:** 63% exact — clearly superior to full-plan
- **Sufficiency assessment:** 53% — hard "always insufficient" bias
- **Error recovery:** 54% exact, 69% acceptable — good at retries, blind to ask_user/skip
- **Thinking prefix effect:** Zero measurable improvement in any category
- **JSON parse errors:** 7/217 (3.2%) — all from max_length=256 reasoning field truncation

**The core finding:** The 4B model excels at classifying what happened (result quality: 94%) but struggles to decide what to do next (routing: 50%, planning: 0–10%). It has strong biases toward "keep going" (retry) and "not enough yet" (insufficient) while being almost completely unable to generate `ask_user` or `skip_and_continue` decisions. The architecture must compensate for these blind spots with deterministic code.

---

## 29. Result Quality Assessment — Near-Perfect

Schema: `ResultAssessment` — `quality` field: 5-way classification.

| Category | Expected | Predicted | Count | Accuracy |
|----------|----------|-----------|:-----:|:--------:|
| success_rich | 6 scenarios | 6 correct | 6/6 | 100% |
| success_partial | 4 scenarios | 3 correct, 1 → success_rich | 3/4 | 75% |
| no_results | 3 scenarios | 3 correct | 3/3 | 100% |
| error_retryable | 2 scenarios | 2 correct | 2/2 | 100% |
| error_fatal | 2 scenarios | 2 correct | 2/2 | 100% |
| **Total** | | | **16/17** | **94.1%** |

**The single miss:** P-01 (metformin `has_warning=False`) was classified as `success_rich` instead of `success_partial`. The tool successfully returned a clear negative result, but the user's actual question (CKD safety) was not addressed by an FDA warnings lookup. The model judged the tool's output quality, not its relevance to the question. Gemini agreed with the model here — this is a genuine labeling ambiguity.

**Key insight:** The model easily distinguishes between data-present, empty, and error states. The hard boundary is `success_rich` vs `success_partial`, which requires understanding whether the result actually answers the user's question — a higher-order judgment.

**Takeaway:** Result quality classification is production-ready as a single constrained call at T=0.0. The only failure mode (rich vs partial) requires contextual awareness of the original question, which could be addressed by including the user's task in the prompt alongside the result.

---

## 30. Next-Action Routing — The ask_user Blind Spot

Schema: `NextAction` — `action` field: 5-way routing decision.

| Expected Action | Predicted → | Accuracy | Notes |
|----------------|-------------|:--------:|-------|
| synthesize | synthesize | 10/12 (83%) | Solid — 2 leaked to retry_different |
| retry_same | retry_same | 4/4 (100%) | Perfect for timeouts/HTTP errors |
| retry_different_args | retry_different_args | 2/4 (50%) | OK |
| call_another_tool | call_another_tool | 6/12 (50%) | 4→synthesize, 2→retry_same |
| **ask_user** | ask_user | **0/8 (0%)** | **Never generated** |

**Action confusion matrix (38 valid experiments, both temperatures):**

```
                    synthesize  retry_same  retry_diff  call_another  ask_user
synthesize              10          .           2           .           .
retry_same               .          4           .           .           .
retry_different           .          .           2           .           .
call_another_tool        4          2           .           6           .
ask_user                 2          2           4           .           0
```

**Three failure patterns:**

1. **`ask_user` is completely absent from the model's output vocabulary.** In all 8 scenarios where the expected action was `ask_user` (ambiguous patient match, missing patient ID, single drug for interaction check), the model chose retry_same, retry_different_args, or synthesize instead. The model prefers to keep trying rather than admit uncertainty.

2. **`call_another_tool` bleeds to synthesize.** When the task explicitly requires more steps (e.g., "find patient AND check drug safety"), the model sometimes routes to `synthesize` after just the first tool — deciding the partial result is "enough." This is the opposite of the sufficiency bias (always insufficient) seen in Cat 5, suggesting the model's behavior depends heavily on how the question is framed.

3. **Temperature has negligible effect.** T=0.0 (50% exact, 80% acceptable) ≈ T=0.3 (50% exact, 78% acceptable). Plus T=0.3 caused 2 JSON parse errors from reasoning field overflow.

**Takeaway:** For production, hardcode `ask_user` triggers in deterministic code rather than relying on the model. Specific rules: (1) multiple patient matches → always ask user, (2) missing required args after tool error → always ask user, (3) unresolved drug names → ask user. The model is reliable for synthesize/retry_same/call_another decisions but blind to the "I don't know, ask the human" escape hatch.

---

## 31. Full-Plan Decomposition — Slot-Filling Pathology

Schema: `TaskPlan` — 5 subtask/tool slots, nullable beyond slot 1.

| Strategy | Sequence Exact | Tools Correct (any order) | Avg Latency |
|----------|:--------------:|:-------------------------:|------------:|
| no_prefix (T=0.0) | **0/10 (0%)** | 0/10 (0%) | 2,525ms |
| thinking_prefix (T=0.0) | **0/10 (0%)** | 1/10 (10%) | 2,645ms |
| reason_first (T=0.3→T=0.0) | **1/10 (10%)** | 2/10 (20%) | 11,067ms |

**What goes wrong — the slot-filling pathology:**

The model fills ALL 5 subtask slots regardless of how many steps the task actually needs. A 2-step task (e.g., T-04: "search SGLT2 studies and find clinical trials") becomes a 4-5 step plan with invented intermediate steps:

```
Expected: search_medical_literature → find_clinical_trials
Got:      search_medical_literature → find_clinical_trials → check_drug_interactions → check_drug_safety
```

This is the same "null cascade" problem from Part II but in reverse: instead of generating `null` for all fields after the first, the model fills every slot with plausible-sounding but unnecessary tool calls. Under Outlines constrained generation, once the model starts populating optional fields, it lacks a mechanism to "stop early" and leave remaining slots as null.

**Observed over-generation patterns:**

| Task Steps | Slots Filled (avg) | Extra Steps |
|:----------:|:------------------:|:-----------:|
| 2-step tasks | 4.3 | +2.3 |
| 3-step tasks | 4.6 | +1.6 |

The most common unnecessary additions:
- `check_drug_safety` and `check_drug_interactions` appended to nearly every plan (safety check reflex)
- `search_medical_literature` added for additional research
- `get_patient_chart` added even when patient context isn't needed

**reason_first helps marginally** because the free-form reasoning step establishes the correct number of steps before the constrained call. But it's 4x slower and still only 10% exact.

**Takeaway:** Full-plan decomposition is fundamentally incompatible with a 4B model under Outlines. The model cannot leave nullable slots empty when earlier slots are populated. This is a schema design problem, not a prompting problem. Don't decompose all steps at once — use reactive step-by-step instead.

---

## 32. Reactive Step-by-Step — The Right Architecture

Schema: `NextStep` — single tool + query + reasoning per call.

| Snapshot | Accuracy | Description |
|:--------:|:--------:|-------------|
| Step 0 (fresh) | **70%** | Pick the first tool with no context |
| Step 1 (1 tool done) | **60%** | Pick next tool given 1 result |
| Step 2 (2 tools done) | **60%** | Pick next tool given 2 results |

**Per-task breakdown:**

| Task | Step 0 | Step 1 | Step 2 | All 3 Correct |
|------|:------:|:------:|:------:|:--------------:|
| T-01 (search→chart→safety) | OK | OK | OK | **Yes** |
| T-07 (safety→interactions→literature) | OK | OK | OK | **Yes** |
| T-03 (chart→interactions→note) | X | OK | OK | No |
| T-10 (chart→safety→interactions) | OK | X | OK | No |

**Why reactive works better than full-plan:**

1. **One decision at a time.** The model only needs to output one tool, not five. This eliminates the slot-filling compulsion.
2. **Concrete context.** At step 1+, the model sees actual tool results and can reason about what's missing. The plan schema asks the model to imagine future results.
3. **Natural stopping.** The `NextStep` schema has `tool: "none"` as a valid output, giving the model an explicit stop signal.

**Where reactive fails:**

- **T-06** ("Prescribe lisinopril and save note"): Step 0 picks `search_patient` (wrong — patient ID is given). The model defaults to the "find patient first" pattern even when `abc-123` is explicit.
- **T-09** ("Search GLP-1 literature and find trials"): Step 0 picks `find_clinical_trials` instead of `search_medical_literature` — order preference confusion.
- **Step 1 failures** often involve the model repeating the tool it just used (e.g., calling `search_patient` again after already finding the patient).

**Takeaway:** Reactive step-by-step is the correct architecture for the 4B model's multi-step planning. The current production graph already uses this pattern (decompose → plan_tool → execute → assess_result loop). The 70% step-0 accuracy and 60% step-1/2 accuracy mean the model gets the right tool ~2 out of 3 times per step. With deterministic validation and retry, this is workable.

---

## 33. Full-Plan vs Reactive Head-to-Head

Direct comparison on the same 10 tasks (Cat 7):

| Metric | Full-Plan | Reactive Simulation |
|--------|:---------:|:-------------------:|
| Sequence exact | 0/10 (0%) | 0/10 (0%) |
| Tools correct (any order) | 0/10 (0%) | **6/10 (60%)** |
| Avg LLM calls | 1.0 | 5.0 |
| Avg latency | 2,406ms | 7,042ms |

**Per-task results:**

- **Reactive wins clearly on 6/10 tasks** — it gets the right tool set even if the sequence isn't perfect
- **Full-plan loses every task** — over-generates tools every time
- **Reactive never achieves exact sequence match** because it runs to 5 steps (the max) even for 2-3 step tasks, adding redundant tool calls. The model doesn't stop when the task is done.

**The "won't stop" problem:** The reactive simulation ran all 10 tasks to the 5-step maximum. The model never selected `tool: "none"` to indicate completion. This connects directly to the sufficiency bias (Section 34) — the model always believes more work is needed.

**Takeaway:** Reactive is clearly better at getting the right tools involved (60% vs 0% acceptable), but it needs external termination logic. The production graph's `assess_result` node provides this — it's a deterministic check, not an LLM decision. This is the right design.

---

## 34. Sufficiency Assessment — The "Always Insufficient" Bias

Schema: `SufficiencyJudgment` — `sufficient: bool`.

| Scenario Type | N | Expected | Model Says "Sufficient" | Accuracy |
|--------------|:-:|:--------:|:-----------------------:|:--------:|
| Clearly sufficient | 5 | True | **0/5** | **0%** |
| Clearly insufficient | 5 | False | 0/5 (all False) | **100%** |
| Borderline | 5 | Mixed | 0/5 (all False) | 60% |

**The model NEVER outputs `sufficient: true`.** Across all 30 experiments (15 scenarios x 2 modes), the model judged every scenario as insufficient — including cases where the data completely answers the question (e.g., SUF-01: "Find John Smith and review his chart" with a full chart already retrieved, SUF-03: "What are FDA warnings for dofetilide?" with boxed warning data present).

**Thinking prefix has zero effect:** Both `no_think` and `think` strategies produce identical results (8/15 correct each). The model's "insufficient" bias is not a reasoning problem — it's a calibration problem.

**Why this happens:**

1. **Safety bias.** The model is trained to be cautious about medical claims. Declaring data "sufficient" could mean endorsing a clinical decision — the model errs on the side of "gather more."
2. **Schema imbalance.** `SufficiencyJudgment` has `missing_info` as a field. The mere presence of this field primes the model to find something missing. Under Outlines, the model generates `sufficient: false` first, then has a slot to fill with a missing-info explanation, reinforcing the negative judgment.
3. **Framing effect.** The prompt asks "Is this data sufficient?" — a question that invites scrutiny. Reframing to "Can you answer the user's question with this data?" might yield different results.

**Gemini judge confirms the bias is wrong.** Gemini judged all 7 "clearly sufficient" misses as "wrong" — the model is genuinely incorrect, not making a defensible conservative call.

**Takeaway:** Never ask the 4B model "is this enough?" — it will always say no. Use deterministic sufficiency checks instead: (1) all required tools in the plan have been executed, (2) no tool returned an error, (3) a maximum step count has been reached. The production graph's `assess_result` node already does this correctly. If an LLM-based sufficiency check is ever needed, reverse the question: "What specific information is still needed that you don't already have?" and check if the answer is empty.

---

## 35. Error Recovery — Never Skips, Never Asks

Schema: `RecoveryStrategy` — `strategy` field: 4-way decision.

| Expected Strategy | Model Output Distribution | Accuracy |
|-------------------|--------------------------|:--------:|
| retry_same | retry_same: 9 | **9/9 (100%)** |
| retry_different_args | retry_different_args: 5, retry_same: 1 | **5/6 (83%)** |
| skip_and_continue | retry_same: 2, retry_different_args: 2 | **0/4 (0%)** |
| ask_user | retry_same: 3, retry_different_args: 4 | **0/7 (0%)** |

**Strategy confusion matrix (26 valid experiments):**

```
                      retry_same  retry_diff  skip  ask_user
retry_same                 9          .         .       .
retry_different_args       1          5         .       .
skip_and_continue          2          2         0       .
ask_user                   3          4         .       0
```

**The model has a strong "keep trying" bias** — identical to the routing finding (Section 30). It maps everything to retry_same or retry_different_args. The `skip_and_continue` and `ask_user` strategies are never generated.

**Pattern by error type:**

| Error Type | Expected | Model Picks | Correct? |
|-----------|----------|-------------|:--------:|
| Timeout / HTTP 500 / 503 | retry_same | retry_same | OK |
| HTTP 429 (rate limit) | retry_same | retry_same | OK |
| Connection error | retry_same | retry_same | OK |
| Empty results (no match) | retry_different / skip | retry_different | ~OK |
| Bad args (missing field) | ask_user | retry_different | Wrong |
| Ambiguous match (3 patients) | ask_user | retry_different | Wrong |
| Drug not in database | skip | retry_different | Wrong |

The model correctly handles transient errors (100%) and reasonably handles empty results (83%). But it fundamentally cannot generate "I need help" or "this step isn't critical" decisions.

**Thinking prefix has zero effect:** Identical results for `no_think` and `think` (7/13 exact, 9/13 acceptable, both modes).

**Takeaway:** Hardcode `skip_and_continue` and `ask_user` in the deterministic error handler. The current production `assess_result` node already does this with strategy logic. The model is reliable for retry decisions — use it for choosing between retry_same and retry_different_args, but never for skip/ask.

---

## 36. Thinking Prefixes Have No Effect

Tested across 3 categories (sufficiency, error recovery, hard routing scenarios):

| Category | no_think | think | Delta |
|----------|:--------:|:-----:|:-----:|
| Sufficiency (Cat 5) | 8/15 (53%) | 8/15 (53%) | **+0** |
| Error Recovery (Cat 6) | 7/13 (54%) | 7/13 (54%) | **+0** |
| Hard Routing (Cat 8) | 6/10 (60%) | 6/9 (67%) | **+7%** (but -1 sample from parse error) |

**Cross-category total: no_think=21/38 (55%) → think=21/37 (57%).** The +2% is entirely explained by one parse error removing a wrong answer from the think group.

**This is consistent with Part I findings:** Thinking tokens/prefixes don't improve operational decisions (tool selection, routing, sufficiency). The model's biases (always insufficient, never ask_user, never skip) are not reasoning failures — they're systematic calibration problems that thinking cannot fix.

The assistant-prefix thinking technique ("Let me analyze this carefully. ") worked for triggering `<unused94>` tokens in Part I, but those tokens improved clinical reasoning quality, not decision-making accuracy. Routing and recovery are classification tasks, not reasoning tasks.

**Takeaway:** Don't invest in thinking/prefix strategies for any agent-loop decision node. Save thinking for the `thinking_mode` node (clinical reasoning) and `synthesize_response` (response generation), where Part I showed it has value.

---

## 37. Gemini Judge vs Deterministic Eval

| Metric | Value |
|--------|------:|
| Total judged | 202/210 (8 Gemini rate-limit failures) |
| Agreement with deterministic eval | **169/202 (83.7%)** |
| Avg Gemini reasoning score | 7.0/10 |
| Avg Gemini overall score | 7.1/10 |

**Disagreement breakdown:**

| Gemini Verdict | Count | Det. Exact | Disagreement Source |
|---------------|:-----:|:----------:|---------------------|
| correct | 125 | 92 | 33 cases Gemini calls "correct" that det. calls wrong |
| acceptable | 22 | 0 | All 22 were deterministic misses — Gemini is more lenient |
| wrong | 55 | 0 | All align (both say wrong) |

**Where Gemini disagrees with deterministic eval:**

1. **Full-plan decomposition (Cat 3):** Gemini judged many over-generated plans as "correct" because the right tools were included (along with extras). Deterministic eval requires exact sequence match. Gemini is arguably more practical here — having the right tools plus extras is better than missing tools.

2. **Sufficiency (Cat 5):** Gemini agreed that all "clearly sufficient → model says insufficient" cases were "wrong." The Gemini judge validated that the model's always-insufficient bias is genuinely incorrect, not a defensible conservative stance.

3. **Result quality (Cat 1):** Gemini judged P-01 (metformin no-warning → model says success_rich) as "correct" — the tool DID return a clear result. The question of whether it's "partial" depends on whether you evaluate the tool output or its relevance to the user's question.

**Takeaway:** 84% agreement is solid. The 16% disagreement is concentrated in categories where "acceptable" vs "exact" is genuinely subjective (planning) or where the deterministic eval is stricter than needed (over-generated plans). For binary decisions (sufficiency, recovery strategy), agreement is higher.

---

## 38. Latency Budget

| Category | Strategy | Avg Total (ms) | Calls/Exp |
|----------|----------|:--------------:|:---------:|
| Result Quality | direct | **1,365** | 1 |
| Sufficiency | no_think / think | 1,382–1,760 | 1 |
| Reactive Planning | snapshot_0/1/2 | 1,413–1,661 | 1 |
| Error Recovery | no_think / think | 1,473–1,717 | 1 |
| Next-Action Routing | T0.0 / T0.3 | 1,499–1,753 | 1 |
| Full-Plan | no_prefix / thinking | 2,525–2,645 | 1 |
| Full-Plan | reason_first | **11,067** | 2 |
| Plan vs Reactive | reactive_sim | **7,042** | 5 |

**Observations:**

- All single-call decision tasks cluster at 1.3–1.8s. The variance comes from prompt length (more context = more processing time).
- Full-plan is ~2.5s per call (longer output generation for 5 slots).
- reason_first is 11s (free-form reasoning + constrained plan = 5.5s per call).
- Reactive simulation averages 1.4s per step — very efficient per decision, but 5 sequential calls total 7s.
- Prompts with tool results as context (routing, sufficiency) are slightly slower than prompts without (result quality), due to input length.

**Takeaway:** Any single-step agent decision (result check, next-action routing, error recovery) fits in the ~1.5s budget. Multi-step reactive simulation at 7s is acceptable for the multi_step agent path (user expects tool execution latency). Full-plan reason_first at 11s is too slow for no benefit.

---

## 39. Implications for Production

### What to change

1. **Remove any LLM-based sufficiency checks.** The model's "always insufficient" bias (0% accuracy on sufficient cases) makes it useless for "are we done?" decisions. Keep the current deterministic `assess_result` node that checks: all subtasks executed, no fatal errors, max steps reached. This is already correct in production.

2. **Hardcode `ask_user` and `skip_and_continue` in error handling.** The model never generates these. Add deterministic rules: (a) multiple patient matches → ask_user, (b) missing required patient_id → ask_user, (c) drug not in database → skip_and_continue, (d) all retries exhausted → skip_and_continue. The current `error_handler` node likely needs these explicit paths.

3. **Use result quality assessment as a fast_check node.** The 94% accuracy on `ResultAssessment` means this can replace or augment the current `fast_check` node. A single constrained call at T=0.0 reliably classifies results into success_rich/partial/empty/error buckets, which can drive deterministic routing downstream.

4. **Keep reactive step-by-step for multi-step planning.** Full-plan decomposition (0–10% exact) is catastrophically broken. The current production architecture (decompose → plan_tool → execute → assess loop) is the right pattern. If decompose must exist, use it only to estimate step count, not to plan tool sequences.

5. **Don't invest in thinking prefixes for decision nodes.** Zero improvement across sufficiency, recovery, and routing. Reserve thinking for clinical reasoning (thinking_mode) and synthesis where it demonstrably helps (Part I).

### What NOT to do

1. **Don't use `TaskPlan` (5-slot decomposition) with Outlines.** The model fills all slots, generating 4-5 steps for 2-step tasks. If you need upfront decomposition, limit the schema to 2-3 slots maximum, or use a `step_count: int` field first to constrain the plan.

2. **Don't ask the model "is this sufficient?"** It always says no. Frame sufficiency as a deterministic check, or if LLM-based, ask "What specific information is still needed?" and check for an empty response.

3. **Don't rely on the model for `ask_user` decisions.** The 4B model never voluntarily defers to the human. This must be a code-level guardrail.

4. **Don't add T=0.3 for decision nodes hoping for better results.** It matches T=0.0 accuracy while introducing JSON parse errors (3.2% error rate). Keep T=0.0 for all constrained-generation decision nodes.

### Recommended production configuration for agent-loop decisions

```
Result quality check:    ResultAssessment schema, T=0.0, ~1.4s        → Use it
Next-action routing:     Deterministic code (not LLM)                  → Bypass model
Sufficiency check:       Deterministic (all subtasks done + no errors) → Bypass model
Error recovery:          LLM for retry_same vs retry_diff (T=0.0)     → Use it
                         Deterministic for skip / ask_user             → Code handles
Multi-step planning:     Reactive NextStep per iteration (T=0.0)      → Use it
                         NOT full-plan TaskPlan                        → Avoid
Thinking prefixes:       None for decision nodes                       → Skip
```

### Capability summary for future reference

| Capability | Model Accuracy | Production Approach |
|-----------|:--------------:|---------------------|
| Classify tool result quality | **94%** | LLM call (reliable) |
| Decide retry_same vs retry_different | **92%** | LLM call (reliable) |
| Pick next tool (reactive, step 0) | **70%** | LLM call + deterministic validation |
| Pick next tool (reactive, step 1-2) | **60%** | LLM call + deterministic validation |
| Route to synthesize | **83%** | LLM call (reliable) |
| Route to call_another_tool | **50%** | LLM call (needs improvement) |
| Route to ask_user | **0%** | Deterministic code only |
| Route to skip_and_continue | **0%** | Deterministic code only |
| Judge sufficiency (insufficient) | **100%** | Not needed (model always says insufficient) |
| Judge sufficiency (sufficient) | **0%** | Deterministic code only |
| Full-plan decomposition | **0–10%** | Don't use |

---

## Appendix: Mock Tool Result Categories (Part III)

| Category | IDs | Count | Description |
|----------|-----|:-----:|-------------|
| Success (rich) | S-01 to S-06 | 6 | Complete data: warnings, articles, interactions, patient match, chart |
| Partial/ambiguous | P-01 to P-04 | 4 | Incomplete: no abstract, multiple matches, drug unresolved |
| Empty | E-01 to E-03 | 3 | Tool succeeded but found nothing |
| Error | X-01 to X-04 | 4 | Timeouts, bad args, HTTP errors |

## Appendix: Multi-Step Tasks (Part III)

| ID | Task | Steps | Expected Tools |
|----|------|:-----:|----------------|
| T-01 | Find patient John Smith, get chart, check metformin safety | 3 | search_patient → get_patient_chart → check_drug_safety |
| T-02 | Check warfarin/aspirin/metoprolol interactions, search alternatives | 2 | check_drug_interactions → search_medical_literature |
| T-03 | Get chart abc-123, check interactions, save note | 3 | get_patient_chart → check_drug_interactions → save_clinical_note |
| T-04 | Search SGLT2 studies, find diabetic nephropathy trials | 2 | search_medical_literature → find_clinical_trials |
| T-05 | Find Maria Garcia, document penicillin allergy, prescribe amoxicillin | 3 | search_patient → add_allergy → prescribe_medication |
| T-06 | Prescribe lisinopril for abc-123, save note | 2 | prescribe_medication → save_clinical_note |
| T-07 | Check dofetilide safety, interactions with amiodarone, AF literature | 3 | check_drug_safety → check_drug_interactions → search_medical_literature |
| T-08 | Find James Wilson, get chart, check med interactions | 3 | search_patient → get_patient_chart → check_drug_interactions |
| T-09 | Search GLP-1 literature, find weight loss trials | 2 | search_medical_literature → find_clinical_trials |
| T-10 | Review abc-123 chart, check warfarin safety and interactions | 3 | get_patient_chart → check_drug_safety → check_drug_interactions |

## Appendix: Category Summary (Part III)

| Category | Experiments | Exact | Acceptable | Avg Latency |
|----------|:----------:|:-----:|:----------:|------------:|
| Result Quality Assessment | 17 | 94.1% | 94.1% | 1,365ms |
| Next-Action Routing | 38 | 50.0% | 78.9% | 1,632ms |
| Full-Plan Decomposition | 30 | 3.3% | 10.0% | 5,412ms |
| Reactive Step-by-Step | 30 | 63.3% | 63.3% | 1,555ms |
| Sufficiency Assessment | 30 | 53.3% | 53.3% | 1,571ms |
| Error Recovery | 26 | 53.8% | 69.2% | 1,595ms |
| Plan vs Reactive | 20 | 0.0% | 30.0% | 4,724ms |
| Thinking Effect | 19 | 63.2% | 78.9% | 1,406ms |

---
---

# Part IV — Response Synthesis Experiment Findings

**Experiments:** 215 across 6 categories (~215 LLM calls)
**Data:** `synthesis_experiments/20260211_063350/`

Probed the final stage of the agent graph: generating free-form clinical responses from tool results, optional reasoning, and the user's query. Key difference from prior parts: no Outlines constrained generation — the model produces free text, evaluated by Gemini 2.0 Flash as the primary judge (6 dimensions) plus deterministic key-fact and source-leakage heuristics. 30 synthesis scenarios spanning success-rich, partial, empty, error, multi-tool, direct chat, and reasoning+tool result types.

---

## Table of Contents (Part IV)

40. [Executive Summary](#40-executive-summary)
41. [Baseline Synthesis — Strong but Error-Blind](#41-baseline-synthesis--strong-but-error-blind)
42. [Thinking Prefix — Harmful for Synthesis](#42-thinking-prefix--harmful-for-synthesis)
43. [Temperature — Flat Curve, T=0.5 Confirmed](#43-temperature--flat-curve-t05-confirmed)
44. [Prompt Variations — Brief Wins](#44-prompt-variations--brief-wins)
45. [Reasoning Context — The Clearest Win](#45-reasoning-context--the-clearest-win)
46. [Token Limits — 256 is the Sweet Spot](#46-token-limits--256-is-the-sweet-spot)
47. [Source Leakage Patterns](#47-source-leakage-patterns)
48. [Error Scenario Failure Mode](#48-error-scenario-failure-mode)
49. [Deterministic vs Gemini Agreement](#49-deterministic-vs-gemini-agreement)
50. [Implications for Production](#50-implications-for-production)

---

## 40. Executive Summary

- **Avg Gemini overall:** 8.9/10 across 211 judged results
- **Avg accuracy:** 9.6/10 — the model almost never hallucinates beyond tool results
- **Avg source hiding:** 10.0/10 — excellent at concealing internal tool names
- **Avg key fact rate (deterministic):** 83.9%
- **Source-clean rate (deterministic):** 86.5% (186/215)
- **Avg word count:** 70 words
- **Avg latency:** 2,480ms

**Gemini dimension breakdown:**

| Dimension | Avg Score | Notes |
|-----------|:---------:|-------|
| Completeness | 8.9/10 | Most key facts included |
| Accuracy | 9.6/10 | Rarely hallucinates |
| Conciseness | 9.1/10 | Appropriately brief |
| Clinical Tone | 9.5/10 | Professional language |
| Source Hiding | 10.0/10 | Tool names fully concealed |
| **Overall** | **8.9/10** | |

**The core finding:** MedGemma 4B is a strong synthesizer. It reliably transforms tool results into concise, accurate, clinically appropriate responses without leaking source information. The weakness is error handling — the model struggles to communicate tool failures gracefully (4.8/10 on error scenarios). The production prompt is near-optimal; reasoning context and a 256-token limit are the main levers for improvement.

---

## 41. Baseline Synthesis — Strong but Error-Blind

30 scenarios with production `SYNTHESIS_PROMPT` (T=0.5, max_tokens=512) or `DIRECT_CHAT_PROMPT` for direct route.

### By Scenario Type

| Type | N | Fact Rate | Clean | Avg Words | Gemini Overall |
|------|:-:|:---------:|:-----:|:---------:|:--------------:|
| success_rich | 6 | 100% | 4/6 | 42 | **9.7** |
| multi_tool | 3 | 100% | 3/3 | 27 | **10.0** |
| direct | 5 | 100% | 5/5 | 39 | **9.6** |
| reasoning_tool | 5 | 90% | 5/5 | 147 | 9.0 |
| partial | 4 | 88% | 3/4 | 34 | 8.8 |
| empty | 3 | 67% | 2/3 | 15 | 10.0 |
| **error** | **4** | **25%** | **4/4** | **121** | **4.8** |

**Key observations:**

1. **Success-rich scenarios are essentially solved** (9.7/10). The model extracts and presents key findings accurately and concisely.

2. **Multi-tool synthesis is excellent** (10.0/10). The model cleanly integrates results from 2-3 tools into a coherent response. SC-18 (search + chart) and SC-19 (search + chart + interactions) both scored 10/10.

3. **Direct chat is natural** (9.6/10). Greetings, medical knowledge questions, and acknowledgments all handled well without tool context.

4. **Error scenarios are the clear weakness** (4.8/10). SC-14 (timeout) and SC-16 (need 2+ drugs) scored 1/10 each. The model either ignores the error entirely or produces a verbose rambling response instead of concisely acknowledging the failure.

5. **Partial results are handled well** (8.8/10). The model correctly presents ambiguous results (multiple patient matches, unresolved drugs) and notes limitations.

---

## 42. Thinking Prefix — Harmful for Synthesis

30 scenarios with `"Let me synthesize these clinical findings step by step. "` prepended as partial assistant turn.

| Metric | Baseline | Thinking Prefix | Delta |
|--------|:--------:|:---------------:|:-----:|
| Gemini overall | 8.8 | 8.8 | +0.0 |
| Key fact rate | 83% | 68% | **-15%** |
| Source-clean | 26/30 | 28/30 | +2 |
| Avg words | 64 | 72 | +8 |
| Avg latency | 2,103ms | 4,448ms | **+2.1x** |

**Critical failure: empty responses.** The thinking prefix caused 4 scenarios (SC-01, SC-05, SC-06, SC-26) to produce **0 words** of visible output. The model spent its entire token budget on internal `<unused94>` thinking and never generated a user-facing response. These are all scenarios where the production baseline scored 10/10.

**Per-scenario comparison reveals mixed picture:**

| Thinking helps (Gemini higher) | Thinking neutral | Thinking hurts (empty/worse) |
|:------------------------------:|:----------------:|:----------------------------:|
| SC-14 (1→8), SC-16 (1→10), SC-17 (7→10), SC-29 (7→9) | 15 scenarios | SC-01 (10→—), SC-05 (10→—), SC-06 (10→—), SC-26 (9→—), SC-09 (9→4), SC-13 (10→0) |

The thinking prefix improved the error scenarios (where baseline was already poor) but destroyed several high-performing scenarios by triggering runaway internal thinking.

**Takeaway:** Do NOT use thinking prefixes for synthesis. The risk of empty responses (4/30 = 13%) outweighs any benefit on edge cases. This is consistent with Part I's finding that thinking tokens produce 0 visible words when they fire. For synthesis — where visible output IS the deliverable — this is catastrophic.

---

## 43. Temperature — Flat Curve, T=0.5 Confirmed

15 key scenarios tested at T={0.1, 0.3, 0.5, 0.7}:

| Temperature | Gemini Overall | Fact Rate | Clean | Avg Words | Avg Latency |
|:-----------:|:--------------:|:---------:|:-----:|:---------:|:-----------:|
| 0.1 | 8.9 | 80% | 14/15 | 40 | 1,210ms |
| 0.3 | 8.9 | 86% | 14/15 | 39 | 1,193ms |
| **0.5** | **8.7** | **90%** | **14/15** | **43** | **1,333ms** |
| 0.7 | 8.9 | 87% | 12/15 | 52 | 1,705ms |

**Findings:**

1. **Gemini scores are virtually identical across all temperatures** (8.7–8.9). The model produces qualitatively similar synthesis regardless of temperature. This contrasts with Part I (thinking mode) where temperature affected behavior, and Part II (tool selection) where T=0.0 was optimal.

2. **Deterministic fact rate peaks at T=0.5** (90%). Lower temperatures produce slightly more formulaic responses that miss some key facts. Higher temperatures add variability without improving coverage.

3. **T=0.7 increases leakage** (12/15 clean vs 14/15 at other temps) and word count (52 vs 39-43). The additional "creativity" at T=0.7 sometimes manifests as mentioning source details.

4. **Latency scales with temperature** — T=0.1 is fastest (1.2s), T=0.7 is slowest (1.7s). Higher temperature requires more sampling computation.

5. **SC-14 (timeout error) fails at ALL temperatures** (0% fact rate). The error handling problem is not a temperature issue — it's a prompting issue.

**Takeaway:** T=0.5 is confirmed as the optimal synthesis temperature. It maximizes fact inclusion while maintaining clean, concise output. This validates the current production setting (`TEMPERATURE["synthesize_response"] = 0.5`).

---

## 44. Prompt Variations — Brief Wins

15 key scenarios tested with 3 alternative prompt styles vs production baseline:

| Prompt | Gemini Overall | Fact Rate | Clean | Avg Words | Avg Latency |
|--------|:--------------:|:---------:|:-----:|:---------:|:-----------:|
| **Production** | **8.9** | **83%** | **11/15** | **45** | — |
| **Brief** | **9.3** | 86% | 10/15 | **47** | 1,800ms |
| Structured | 8.3 | 88% | 9/15 | 94 | 3,097ms |
| Comprehensive | 8.4 | 80% | 12/15 | 210 | 5,956ms |

**The Brief prompt:**
```
One-paragraph clinical summary.
Query: {user_input}
{reasoning_line}
{tool_results_line}
Respond in 2-3 sentences maximum. Include only the most critical findings.
```

**Why Brief wins:**

1. **Highest Gemini overall (9.3/10)** — the constraint to 2-3 sentences forces the model to prioritize the most important findings, producing tighter, more clinically useful responses.

2. **Similar fact rate to production** (86% vs 83%) — the brevity constraint doesn't cause key fact loss. The model successfully distills the essential information.

3. **Similar word count to production** (47 vs 45) — despite the "2-3 sentences" instruction, the model produces responses of similar length. The quality improvement comes from better information selection, not shorter output.

**Why Structured and Comprehensive are worse:**

- **Structured** (8.3/10): The "1. Key Findings / 2. Clinical Significance / 3. Recommendations" template produces 94 avg words (+109% vs production) and increases source leakage (9/15 clean). The model fills the template slots even when the content doesn't warrant all three sections, leading to repetitive or padded responses.

- **Comprehensive** (8.4/10): "Detailed clinical decision support" generates 210 avg words — 4.7x production. Despite being thorough, Gemini scores it lower because verbosity hurts conciseness, and the extra text doesn't add proportional clinical value. Latency is 3x production.

**Takeaway:** Consider switching from `SYNTHESIS_PROMPT` to the Brief variant, or incorporate its core instruction ("Respond in 2-3 sentences maximum. Include only the most critical findings.") into the production prompt. The structured and comprehensive variants are strictly worse than production — more words, more leakage, lower quality.

---

## 45. Reasoning Context — The Clearest Win

10 scenarios tested with and without reasoning text in the prompt:

| Condition | Gemini Overall | Fact Rate | Clean | Avg Words |
|-----------|:--------------:|:---------:|:-----:|:---------:|
| **With reasoning** | **9.5** | **100%** | **10/10** | 78 |
| Without reasoning | 9.1 | 94% | 9/10 | 79 |

**Paired comparison (scenarios where reasoning makes a difference):**

| Scenario | Without | With | Delta | What reasoning adds |
|----------|:-------:|:----:|:-----:|---------------------|
| SC-26 (CKD antihypertensive) | 7 | 9 | **+2** | ACE inhibitor recommendation grounded in KDIGO guidelines |
| SC-30 (medication review) | 9 | 10 | **+1** | Contextualizes chart review with medication cross-referencing intent |
| SC-27 (warfarin dental) | 9 | 10 | **+1** | Frames interaction data within perioperative context |
| SC-29 (TNBC treatment) | 7 | 8 | **+1** | Connects trial data to limited targeted therapy landscape |

**Why reasoning helps:**

1. **100% key fact rate** — reasoning text primes the model to attend to specific clinical details. Without reasoning, SC-26 only captured 67% of expected facts and SC-30 captured 75%.

2. **Perfect source cleanliness** — reasoning provides clinical framing that replaces the need to reference tools. Without reasoning, SC-26 leaked tool names (1/10 experiments).

3. **No word count overhead** — responses with and without reasoning are the same length (~78 words). Reasoning improves quality without increasing verbosity.

4. **The biggest gain is on the reasoning_tool scenarios** (SC-26 to SC-30), where the reasoning text provides clinical context that the tool results alone lack. Without reasoning, the model has tool output but no interpretive framework.

**Takeaway:** Always include reasoning context when available. The current production architecture correctly passes `reasoning + reasoning_continuation` to the synthesis node. This experiment validates that the reasoning path's output materially improves synthesis quality. For the lookup path (no reasoning), consider whether the triage or context assembler can provide a minimal reasoning frame.

---

## 46. Token Limits — 256 is the Sweet Spot

10 scenarios tested at max_tokens={128, 256, 512}:

| Max Tokens | Gemini Overall | Conciseness | Fact Rate | Avg Words | Clean |
|:----------:|:--------------:|:-----------:|:---------:|:---------:|:-----:|
| 128 | 9.4 | 8.8 | 86% | 48 | 9/10 |
| **256** | **9.7** | **9.4** | **90%** | **52** | **9/10** |
| 512 | 9.4 | 8.9 | 85% | 51 | 10/10 |

**Key observations:**

1. **256 tokens achieves the highest overall quality (9.7/10)** and the highest conciseness (9.4/10). The moderate limit encourages the model to be selective about what to include.

2. **128 tokens doesn't significantly hurt** (9.4/10) but drops fact rate to 86%. Some longer tool results (patient charts, multi-tool scenarios) get compressed too aggressively, losing detail.

3. **512 tokens is NOT better than 256** (9.4 vs 9.7). Despite having more room, the model doesn't produce better responses — it produces roughly the same length (51 vs 52 words) but occasionally introduces filler content that lowers conciseness scores.

4. **Word count is stable across limits** (48-52). The model naturally produces 40-60 word responses for most synthesis tasks. The token limit primarily affects the upper bound — longer reasoning_tool scenarios (SC-26, SC-30) get truncated at 128 but complete fine at 256.

5. **Source cleanliness improves with higher limits** (10/10 at 512 vs 9/10 at 128/256). The tighter limit occasionally forces the model to compress in ways that expose tool names.

**Takeaway:** Switch production `max_new_tokens` from 512 to 256 for the synthesis node. This improves Gemini quality (+0.3), maintains fact inclusion, and reduces worst-case latency. The model's natural response length (~50 words) fits comfortably within 256 tokens (~190 tokens), leaving room for longer chart summaries without excess padding.

---

## 47. Source Leakage Patterns

Across all 215 experiments:

| Leaked Term | Occurrences | % of Non-Direct Experiments |
|-------------|:-----------:|:---------------------------:|
| `search_patient` | 8 | 4.2% |
| `tool` | 8 | 4.2% |
| `get_patient_chart` | 5 | 2.6% |
| `search_medical_literature` | 3 | 1.6% |
| `PubMed` | 3 | 1.6% |
| `the tool` | 2 | 1.0% |
| `check_drug_safety` | 2 | 1.0% |
| `ClinicalTrials.gov` | 1 | 0.5% |
| `find_clinical_trials` | 1 | 0.5% |

**Leakage patterns:**

1. **EHR tool names leak most frequently.** `search_patient` (8x) and `get_patient_chart` (5x) are the worst offenders. These tool names appear in the formatted tool results that the model receives as input. The model sometimes echoes them verbatim instead of paraphrasing.

2. **The word `tool` leaks 8 times** — often in phrases like "the tool returned" or "tool results show." The production prompt instructs "Do NOT mention tool names, sources, references, internal processes" but the 4B model occasionally ignores this.

3. **External source names leak minimally** — `PubMed` (3x), `ClinicalTrials.gov` (1x). These are borderline: a clinician might reasonably mention PubMed, but the prompt explicitly forbids it.

4. **Gemini rates source hiding at 10.0/10 even on deterministic leakers.** The Gemini judge is more lenient — it considers a passing mention of "PubMed" as acceptable source attribution rather than harmful leakage. The deterministic check is stricter.

**Which strategies leak most?**

| Strategy | Leak Rate |
|----------|:---------:|
| Structured prompt | 6/15 (40%) — template forces elaboration that exposes tools |
| Brief prompt | 5/15 (33%) — brevity constraint occasionally compresses to tool names |
| Comprehensive | 3/15 (20%) — more room to paraphrase |
| Production | 4/30 (13%) — current level |
| With reasoning | 0/10 (0%) — reasoning provides clinical framing that replaces tool references |

**Takeaway:** Reasoning context is the best anti-leakage measure (0% leak rate). For the lookup path without reasoning, the production prompt's source-hiding instruction is mostly effective (87% clean). The main residual leakage is EHR tool names — consider adding a post-processing step or rephrasing the formatted tool results to use clinical terms instead of tool names (e.g., "[Patient Record]" instead of "[search_patient]").

---

## 48. Error Scenario Failure Mode

The 4 error scenarios (SC-14 to SC-17) are the only category where the model consistently fails:

| Scenario | Error Type | Baseline Gemini | What goes wrong |
|----------|-----------|:---------------:|-----------------|
| SC-14 | API timeout | **1/10** | Ignores the error entirely; responds as if it has data about amiodarone from its own knowledge |
| SC-15 | Invalid patient ID | 10/10 | Correctly asks for a valid patient ID |
| SC-16 | Need 2+ drugs | **1/10** | Produces a 269-word rambling response about aspirin pharmacology instead of noting the error |
| SC-17 | HTTP 500 | 7/10 | Acknowledges something went wrong but still tries to provide diabetes management info from knowledge |

**The failure pattern:** When the tool returns an error, the model falls back to answering from its pretrained medical knowledge rather than communicating the error state. This is the opposite of the desired behavior (acknowledge failure, suggest retry). The model's training to be "helpful" overrides the error signal.

**SC-15 succeeds because the error is about user input** ("patient_id is required"), which the model correctly interprets as needing clarification from the user. The other errors are about service failures, which the model treats as "I should still try to help."

**Thinking prefix partially fixes this** — SC-14 improved from 1→8, SC-16 from 1→10, SC-17 from 7→10 with thinking prefix. But thinking prefix has severe side effects (Section 42), making it impractical as a general fix.

**Takeaway:** Error handling should be deterministic, not LLM-driven. When a tool result contains an `"error"` field, the synthesis node should receive a pre-formatted error message template rather than raw error output. Example: instead of passing `[check_drug_safety] (FAILED)\n  Error: Request timed out`, pass a structured frame like `"The drug safety lookup for amiodarone was temporarily unavailable. Please try again shortly."` This keeps the error response under the model's control while preventing the "helpful fallback" behavior.

---

## 49. Deterministic vs Gemini Agreement

### Fact Rate vs Gemini Completeness

| Fact Rate Range | N | Avg Gemini Completeness | Avg Gemini Overall |
|:---------------:|:-:|:-----------------------:|:------------------:|
| 0-25% | 17 | 5.2 | 5.4 |
| 50-75% | 25 | 8.6 | 8.6 |
| 75-100% | 169 | 9.3 | 9.3 |

**Strong correlation.** The deterministic fact rate aligns well with Gemini's completeness judgment. The 0-25% bucket (mostly error scenarios and thinking-prefix empty responses) correctly gets low Gemini scores. The 75-100% bucket (most experiments) gets high scores.

**The outliers:** Gemini scores 10/10 for some 0% fact-rate scenarios (SC-11: "no articles found" — the model correctly states no results, but the deterministic check expects regex `no.*result` which the model phrases differently). This suggests the deterministic key-fact patterns could be broadened for empty/error scenarios.

### Source Hiding Disagreement

| Deterministic | N | Avg Gemini Source Hiding |
|:-------------:|:-:|:-----------------------:|
| Clean | 182 | 10.0 |
| Leaked | 29 | 10.0 |

**Total disagreement on leakage.** Gemini rates 10.0/10 for source hiding even when the deterministic check finds forbidden terms. This is because Gemini evaluates contextual appropriateness (mentioning "PubMed" in a literature summary is natural), while the deterministic check is a strict substring match.

**Takeaway:** For production monitoring, use the deterministic source-leakage check as a strict canary. Gemini's leniency means it won't catch leakage that a careful reviewer would notice. The deterministic false-positive rate is low (most flagged terms are genuine leaks, not natural usage).

---

## 50. Implications for Production

### What to change

1. **Reduce `max_new_tokens` from 512 to 256** for the synthesis node. Gemini overall improves from 9.4 to 9.7. The model's natural response length (~50 words) fits comfortably, and worst-case latency drops. This is a free quality improvement.

2. **Always include reasoning context when available.** The reasoning path already does this. For the lookup path, consider having the triage node emit a brief reasoning line (e.g., "User is asking about dofetilide safety warnings") to provide synthesis framing. Reasoning context achieves 100% fact rate and 0% source leakage.

3. **Handle tool errors deterministically before synthesis.** Don't pass raw error output to the LLM. When a tool result contains an error, generate a structured error message at the code level and pass that to synthesis instead. The model scores 4.8/10 on raw errors but 10/10 when given clear input.

4. **Consider the Brief prompt variant** for scenarios without reasoning. Adding "Include only the most critical findings" to the production prompt could improve Gemini overall from 8.9 to 9.3 without changing response length.

5. **Reformat tool result headers for synthesis.** Replace `[search_patient]` with `[Patient Search]` and `[get_patient_chart]` with `[Patient Record]` in the formatted tool results passed to synthesis. This is the primary source of tool name leakage.

### What NOT to do

1. **Don't use thinking prefixes for synthesis.** 13% chance of producing zero visible output. The risk is unacceptable for the node that generates user-facing responses.

2. **Don't use the Structured prompt template.** It produces 2x the words, 40% source leakage, and lower Gemini scores (8.3) than production (8.9). The template slots force the model to pad thin content.

3. **Don't use the Comprehensive prompt template.** 4.7x word count, 3x latency, lower quality (8.4). Verbosity doesn't equal thoroughness for a 4B model.

4. **Don't lower temperature below 0.5 for synthesis.** T=0.1 and T=0.3 produce marginally worse fact rates with no Gemini quality improvement. T=0.5 is the validated optimum.

5. **Don't increase `max_tokens` beyond 256.** 512 tokens doesn't improve quality, and the model's natural ~50-word responses won't use the extra budget meaningfully.

### Recommended production synthesis configuration

```
Prompt:             SYNTHESIS_PROMPT (production) — or Brief variant for lookup path
Temperature:        0.5 (validated)
Max tokens:         256 (down from 512)
Reasoning context:  Always include when available
Thinking prefix:    Never use
Tool result format: Clinical labels (not tool names)
Error handling:     Deterministic pre-formatting before LLM
```

### Synthesis quality by scenario type (production config)

| Scenario Type | Gemini Overall | Reliability | Notes |
|---------------|:--------------:|:-----------:|-------|
| Success-rich tool results | 9.7/10 | Solved | No changes needed |
| Multi-tool results | 10.0/10 | Solved | Excellent integration across tools |
| Direct chat | 9.6/10 | Solved | Natural, appropriate responses |
| Reasoning + tool | 9.0/10 | Strong | Reasoning context helps further (+0.5) |
| Partial results | 8.8/10 | Good | Correctly notes limitations |
| Empty results | 10.0/10 | Solved | Cleanly states "no results found" |
| **Error results** | **4.8/10** | **Broken** | **Needs deterministic pre-formatting** |

---

## Appendix: Synthesis Scenarios (Part IV)

### Success-Rich (SC-01 to SC-06)

| ID | Query | Tool Result | Gemini |
|----|-------|-------------|:------:|
| SC-01 | "Check FDA safety warnings for dofetilide" | Boxed warning (Torsade de Pointes, ECG monitoring) | 10 |
| SC-02 | "Search for studies on SGLT2 inhibitors and cardiovascular outcomes" | 3 articles (empagliflozin, dapagliflozin, meta-analysis) | 9 |
| SC-03 | "Check drug interactions between warfarin and aspirin" | High-severity interaction (bleeding, INR) | 10 |
| SC-04 | "Find clinical trials for triple-negative breast cancer" | 2 recruiting trials (pembrolizumab, ADC) | 9 |
| SC-05 | "Search for patient Maria Garcia" | 1 match (abc-123) | 10 |
| SC-06 | "Get the chart for patient abc-123" | Full chart (T2DM, HTN, HLD, meds, labs) | 10 |

### Partial / Empty / Error (SC-07 to SC-17)

| ID | Query | Scenario | Gemini |
|----|-------|----------|:------:|
| SC-07 | "Is metformin safe for CKD?" | No boxed warning (question partially unanswered) | 9 |
| SC-08 | "Find patient James Wilson" | 3 matches (clarification needed) | 9 |
| SC-11 | "Search for xylotriazole enzyme deficiency" | 0 articles | 10 |
| SC-14 | "Check FDA warnings for amiodarone" | Timeout error | **1** |
| SC-16 | "Check interactions for aspirin" | Need 2+ drugs error | **1** |

### Direct Chat (SC-21 to SC-25)

| ID | Query | Gemini |
|----|-------|:------:|
| SC-21 | "Hello, how are you?" | 10 |
| SC-22 | "What is hypertension?" | 8 |
| SC-23 | "Thanks for the help!" | 10 |
| SC-24 | "What are ACE inhibitors used for?" | 10 |
| SC-25 | "Explain the mechanism of action of metformin" | 10 |

## Appendix: Category Summary (Part IV)

| Category | Experiments | Fact Rate | Clean | Gemini Overall | Avg Latency |
|----------|:----------:|:---------:|:-----:|:--------------:|:-----------:|
| Baseline (Cat 1) | 30 | 83% | 26/30 | 8.8 | 2,103ms |
| Thinking Prefix (Cat 2) | 30 | 68% | 28/30 | 8.8 | 4,448ms |
| Temperature Sweep (Cat 3) | 60 | 86% | 54/60 | 8.9 | 1,360ms |
| Prompt Variations (Cat 4) | 45 | 85% | 31/45 | 8.7 | 3,618ms |
| Reasoning Context (Cat 5) | 20 | 97% | 19/20 | 9.3 | 2,196ms |
| Token Limit (Cat 6) | 30 | 87% | 28/30 | 9.5 | 1,612ms |
