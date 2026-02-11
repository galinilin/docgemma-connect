# MedGemma 4B — Thinking Mode Experiment Findings

**Model:** `google/medgemma-1.5-4b-it` (instruction-tuned, 4B parameters)
**Serving:** vLLM with Outlines constrained generation
**Date:** 2026-02-11
**Experiments:** 104 across 9 categories
**Data:** `thinking_experiments/20260211_014112/`

This document records what we learned from a controlled experiment on MedGemma 4B's thinking token behavior. The experiment varied temperature, system prompts, assistant prefixes, user trigger phrases, combined strategies, guided generation schemas, max token budgets, and multi-turn context — measuring thinking token emission, output quality (Gemini 2.0 Flash judge), and latency.

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
