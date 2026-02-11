"""
Thinking-mode experiments for MedGemma 4B IT.

Probes how the model enters "thinking mode" (<unused94>...<unused95>) under
different prompting strategies, temperatures, and guided-generation setups.
Generates a Markdown report with findings.

Usage:
    cd docgemma-connect
    uv run python thinking_experiments.py [--report-only PREV_RUN_DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import httpx

# ── Config ──────────────────────────────────────────────────────────────

ENDPOINT = os.environ.get(
    "DOCGEMMA_ENDPOINT", "https://sbx7zjulvioxoh-8000.proxy.runpod.net"
)
API_KEY = os.environ.get("DOCGEMMA_API_KEY", "sk-sbx7zjulvioxoh")
MODEL = os.environ.get("DOCGEMMA_MODEL", "google/medgemma-1.5-4b-it")
COMPLETIONS_URL = f"{ENDPOINT.rstrip('/')}/v1/chat/completions"

THINKING_OPEN = "<unused94>"
THINKING_CLOSE = "<unused95>"
# Match <unused94> through <unused95> (if present) or through end-of-string.
# The model almost never emits the closing tag.
THINKING_RE = re.compile(r"<unused94>(.*?)(?:<unused95>|$)", re.DOTALL)

TIMEOUT = 120.0

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# ── HTTP helper ─────────────────────────────────────────────────────────

_client: httpx.Client | None = None

def get_client() -> httpx.Client:
    global _client
    if _client is None:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        _client = httpx.Client(timeout=TIMEOUT, headers=headers)
    return _client


def call_model(
    messages: list[dict],
    *,
    max_tokens: int = 512,
    temperature: float = 0.0,
    response_format: dict | None = None,
    extra_body: dict | None = None,
) -> dict:
    """Raw OpenAI-compatible chat completion. Returns the full response JSON."""
    payload: dict = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format
    if extra_body:
        payload.update(extra_body)
    resp = get_client().post(COMPLETIONS_URL, json=payload)
    resp.raise_for_status()
    return resp.json()


# ── Result container ────────────────────────────────────────────────────

@dataclass
class ExperimentResult:
    experiment_id: str
    category: str
    description: str
    query: str
    messages: list[dict]
    params: dict

    raw_response: str = ""
    thinking_content: str = ""
    visible_content: str = ""
    has_thinking: bool = False
    has_close_tag: bool = False
    thinking_token_count: int = 0
    visible_token_count: int = 0
    latency_ms: float = 0.0
    error: str | None = None

    # Gemini judge fields (populated by --judge pass)
    gemini_thinks: bool | None = None
    gemini_score: int | None = None  # 0-10
    gemini_rationale: str | None = None

    def analyze(self):
        """Parse raw response to extract thinking vs. visible content.

        The model emits ``<unused94>thought\n...`` to start thinking but
        almost never emits the closing ``<unused95>`` tag.  We therefore
        match ``<unused94>`` through ``<unused95>`` *or* end-of-string.
        """
        matches = THINKING_RE.findall(self.raw_response)
        if matches:
            self.has_thinking = True
            # Strip the leading "thought\n" marker the model always prepends
            cleaned = []
            for m in matches:
                t = m.strip()
                if t.lower().startswith("thought"):
                    t = t[len("thought"):].lstrip("\n")
                cleaned.append(t)
            self.thinking_content = "\n---\n".join(cleaned)
            self.thinking_token_count = sum(len(c.split()) for c in cleaned)

        self.visible_content = THINKING_RE.sub("", self.raw_response).strip()
        self.visible_token_count = len(self.visible_content.split()) if self.visible_content else 0
        self.has_close_tag = THINKING_CLOSE in self.raw_response


# ── Test queries ────────────────────────────────────────────────────────

CLINICAL_QUERIES = {
    "simple": "What is hypertension?",
    "reasoning": "A 65-year-old male with CKD stage 3 and diabetes needs an antihypertensive. What would you recommend and why?",
    "complex": "Patient presents with sudden onset chest pain, diaphoresis, and shortness of breath. ECG shows ST elevation in leads II, III, aVF. Troponin pending. What is the differential diagnosis and immediate management plan?",
    "drug": "What are the risks of combining warfarin with aspirin in an elderly patient with atrial fibrillation?",
    "ambiguous": "Is metformin safe?",
}


# ── Experiment definitions ──────────────────────────────────────────────

def build_experiments() -> list[dict]:
    """
    Each experiment is a dict with:
        id, category, description, query_key, messages_fn, params
    where messages_fn(query) -> list[dict] and params are extra kwargs for call_model.
    """
    experiments = []
    exp_id = 0

    # ================================================================
    # CATEGORY 1: Baseline — No priming, vary temperature
    # ================================================================
    for temp in [0.0, 0.3, 0.6, 1.0]:
        for qk, qv in CLINICAL_QUERIES.items():
            exp_id += 1
            experiments.append({
                "id": f"baseline-t{temp}-{qk}",
                "category": "1_baseline_temperature",
                "description": f"No priming, temp={temp}, query={qk}",
                "query_key": qk,
                "messages_fn": lambda q: [{"role": "user", "content": q}],
                "params": {"temperature": temp, "max_tokens": 1024},
            })

    # ================================================================
    # CATEGORY 2: System prompt priming strategies
    # ================================================================
    system_prompts = {
        "clinical_assistant": (
            "You are DocGemma, a clinical decision-support assistant. "
            "Think through clinical problems step by step before answering."
        ),
        "think_first": (
            "You are a medical AI. Always think carefully before responding. "
            "Show your reasoning process."
        ),
        "chain_of_thought": (
            "You are a clinical reasoning engine. For every query, first analyze "
            "the clinical context, consider differentials, then provide your answer."
        ),
        "minimal": "You are a medical assistant. Be concise.",
        "none": None,
    }
    for sp_name, sp_text in system_prompts.items():
        for qk in ["reasoning", "complex"]:
            exp_id += 1
            qv = CLINICAL_QUERIES[qk]

            def make_msgs(q, _sp=sp_text):
                msgs = []
                if _sp:
                    msgs.append({"role": "system", "content": _sp})
                msgs.append({"role": "user", "content": q})
                return msgs

            experiments.append({
                "id": f"sysprompt-{sp_name}-{qk}",
                "category": "2_system_prompt",
                "description": f"System prompt='{sp_name}', query={qk}",
                "query_key": qk,
                "messages_fn": make_msgs,
                "params": {"temperature": 0.3, "max_tokens": 1024},
            })

    # ================================================================
    # CATEGORY 3: Prefix priming — pre-fill assistant response start
    # ================================================================
    prefixes = {
        "think_start": "Let me think through this step by step.\n\n",
        "analysis_start": "I'm analyzing the clinical information provided. ",
        "considering": "Considering the clinical context, I think that ",
        "reasoning_header": "**Clinical Reasoning:**\n\n",
        "internal_monologue": "Looking at this case, several things stand out. ",
        "structured_start": "Assessment:\n1. ",
        "differential_start": "Let me work through the differential diagnosis:\n\n",
    }
    for pfx_name, pfx_text in prefixes.items():
        for qk in ["reasoning", "complex"]:
            exp_id += 1

            def make_msgs(q, _pfx=pfx_text):
                return [
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": _pfx},
                ]

            experiments.append({
                "id": f"prefix-{pfx_name}-{qk}",
                "category": "3_prefix_priming",
                "description": f"Assistant prefix='{pfx_name}', query={qk}",
                "query_key": qk,
                "messages_fn": make_msgs,
                "params": {"temperature": 0.3, "max_tokens": 1024},
            })

    # ================================================================
    # CATEGORY 4: Explicit thinking triggers in user message
    # ================================================================
    trigger_templates = {
        "think_step_by_step": "Think step by step: {q}",
        "reason_carefully": "Reason carefully about the following clinical question: {q}",
        "analyze_then_answer": "First analyze, then answer: {q}",
        "lets_think": "Let's think about this carefully.\n\n{q}",
        "explain_reasoning": "{q}\n\nExplain your reasoning.",
        "show_work": "{q}\n\nShow your work.",
        "before_answering": "Before answering, consider all relevant factors.\n\n{q}",
        "what_factors": "{q}\n\nWhat factors should be considered?",
        "clinical_reasoning": "Apply clinical reasoning to this case:\n\n{q}",
        "plain": "{q}",
    }
    for trig_name, trig_tpl in trigger_templates.items():
        for qk in ["reasoning", "complex"]:
            exp_id += 1

            def make_msgs(q, _tpl=trig_tpl):
                return [{"role": "user", "content": _tpl.format(q=q)}]

            experiments.append({
                "id": f"trigger-{trig_name}-{qk}",
                "category": "4_user_triggers",
                "description": f"User trigger='{trig_name}', query={qk}",
                "query_key": qk,
                "messages_fn": make_msgs,
                "params": {"temperature": 0.3, "max_tokens": 1024},
            })

    # ================================================================
    # CATEGORY 5: Combined system + prefix + trigger
    # ================================================================
    combos = [
        {
            "name": "full_chain",
            "system": "You are a clinical reasoning engine. Think step by step.",
            "prefix": "Let me analyze this systematically.\n\n",
            "trigger": "{q}",
        },
        {
            "name": "reactive_fill",
            "system": "You are DocGemma. Use clinical reasoning.",
            "prefix": "I'm reviewing the clinical information. I think that ",
            "trigger": "{q}",
        },
        {
            "name": "structured_reactive",
            "system": "You are a medical AI. Structure your analysis.",
            "prefix": "Clinical Assessment:\n\n1. Key findings: ",
            "trigger": "{q}",
        },
        {
            "name": "socratic",
            "system": None,
            "prefix": "Several important clinical questions arise here. First, ",
            "trigger": "Consider this clinical scenario carefully:\n\n{q}",
        },
        {
            "name": "minimal_reactive",
            "system": None,
            "prefix": "Based on the information provided, ",
            "trigger": "{q}",
        },
    ]
    for combo in combos:
        for qk in ["reasoning", "complex"]:
            exp_id += 1
            c = combo

            def make_msgs(q, _c=c):
                msgs = []
                if _c["system"]:
                    msgs.append({"role": "system", "content": _c["system"]})
                msgs.append({"role": "user", "content": _c["trigger"].format(q=q)})
                msgs.append({"role": "assistant", "content": _c["prefix"]})
                return msgs

            experiments.append({
                "id": f"combo-{c['name']}-{qk}",
                "category": "5_combined_strategies",
                "description": f"Combo='{c['name']}', query={qk}",
                "query_key": qk,
                "messages_fn": make_msgs,
                "params": {"temperature": 0.3, "max_tokens": 1024},
            })

    # ================================================================
    # CATEGORY 6: Guided generation (Outlines) with thinking
    #
    # Test if structured output suppresses or enables thinking tokens.
    # ================================================================
    from pydantic import BaseModel, Field as PField

    class ThinkThenAnswer(BaseModel):
        thinking: str = PField(description="Step-by-step clinical reasoning")
        answer: str = PField(description="Final clinical answer")

    class ReasoningWithConfidence(BaseModel):
        reasoning: str = PField(description="Clinical reasoning chain")
        answer: str = PField(description="Clinical recommendation")
        confidence: str = PField(description="high, medium, or low")

    class DiagnosticAssessment(BaseModel):
        differential: str = PField(description="Differential diagnoses considered")
        key_findings: str = PField(description="Key clinical findings")
        recommendation: str = PField(description="Recommended next steps")

    guided_schemas = {
        "think_then_answer": ThinkThenAnswer,
        "reasoning_confidence": ReasoningWithConfidence,
        "diagnostic_assessment": DiagnosticAssessment,
    }

    for schema_name, schema_cls in guided_schemas.items():
        for qk in ["reasoning", "complex"]:
            exp_id += 1
            _schema_cls = schema_cls

            def make_msgs(q):
                return [{"role": "user", "content": q}]

            schema = _schema_cls.model_json_schema()
            experiments.append({
                "id": f"guided-{schema_name}-{qk}",
                "category": "6_guided_generation",
                "description": f"Outlines schema='{schema_name}', query={qk}",
                "query_key": qk,
                "messages_fn": make_msgs,
                "params": {
                    "temperature": 0.1,
                    "max_tokens": 1024,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": _schema_cls.__name__,
                            "schema": schema,
                            "strict": True,
                        },
                    },
                },
            })

    # ================================================================
    # CATEGORY 7: Guided generation + prefix priming
    #
    # Does a priming prefix interact differently when output is
    # constrained by Outlines?
    # ================================================================
    guided_prefix_combos = [
        {
            "name": "guided_think_prefix",
            "system": "You are a clinical reasoning engine.",
            "prefix": None,  # no prefix — let Outlines shape the output
            "schema": ThinkThenAnswer,
        },
        {
            "name": "guided_system_think",
            "system": "Think step by step. Output JSON.",
            "prefix": None,
            "schema": ThinkThenAnswer,
        },
        {
            "name": "guided_no_system",
            "system": None,
            "prefix": None,
            "schema": ThinkThenAnswer,
        },
    ]
    for gpc in guided_prefix_combos:
        for qk in ["reasoning", "complex"]:
            exp_id += 1
            _gpc = gpc

            def make_msgs(q, _g=_gpc):
                msgs = []
                if _g["system"]:
                    msgs.append({"role": "system", "content": _g["system"]})
                msgs.append({"role": "user", "content": q})
                return msgs

            schema = _gpc["schema"].model_json_schema()
            experiments.append({
                "id": f"guided-combo-{_gpc['name']}-{qk}",
                "category": "7_guided_plus_priming",
                "description": f"Guided combo='{_gpc['name']}', query={qk}",
                "query_key": qk,
                "messages_fn": make_msgs,
                "params": {
                    "temperature": 0.1,
                    "max_tokens": 1024,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": _gpc["schema"].__name__,
                            "schema": schema,
                            "strict": True,
                        },
                    },
                },
            })

    # ================================================================
    # CATEGORY 8: Max tokens effect on thinking
    #
    # Does giving the model more room encourage thinking tokens?
    # ================================================================
    for max_tok in [128, 256, 512, 1024, 2048]:
        for qk in ["reasoning", "complex"]:
            exp_id += 1
            experiments.append({
                "id": f"maxtok-{max_tok}-{qk}",
                "category": "8_max_tokens",
                "description": f"max_tokens={max_tok}, query={qk}",
                "query_key": qk,
                "messages_fn": lambda q: [{"role": "user", "content": q}],
                "params": {"temperature": 0.3, "max_tokens": max_tok},
            })

    # ================================================================
    # CATEGORY 9: Multi-turn context (does prior conversation trigger thinking?)
    # ================================================================
    multi_turn_setups = {
        "cold_start": lambda q: [
            {"role": "user", "content": q},
        ],
        "prior_simple_exchange": lambda q: [
            {"role": "user", "content": "What is hypertension?"},
            {"role": "assistant", "content": "Hypertension is sustained elevation of blood pressure above 130/80 mmHg."},
            {"role": "user", "content": q},
        ],
        "prior_reasoning_exchange": lambda q: [
            {"role": "user", "content": "What are first-line treatments for type 2 diabetes?"},
            {"role": "assistant", "content": "First-line: metformin (per ADA guidelines). Consider SGLT2i or GLP-1 RA if CVD/CKD risk. Lifestyle modification concurrent."},
            {"role": "user", "content": q},
        ],
        "explicit_think_history": lambda q: [
            {"role": "user", "content": "Think carefully: what are ACE inhibitor contraindications?"},
            {"role": "assistant", "content": "Let me think through this. ACE inhibitors are contraindicated in: bilateral renal artery stenosis, pregnancy, history of angioedema, hyperkalemia >5.5. Caution with CKD stage 4-5."},
            {"role": "user", "content": q},
        ],
    }
    for mt_name, mt_fn in multi_turn_setups.items():
        for qk in ["reasoning", "complex"]:
            exp_id += 1
            _mt_fn = mt_fn
            experiments.append({
                "id": f"multiturn-{mt_name}-{qk}",
                "category": "9_multi_turn",
                "description": f"Multi-turn='{mt_name}', query={qk}",
                "query_key": qk,
                "messages_fn": _mt_fn,
                "params": {"temperature": 0.3, "max_tokens": 1024},
            })

    return experiments


# ── Runner ──────────────────────────────────────────────────────────────

def run_experiment(exp: dict) -> ExperimentResult:
    """Execute a single experiment and return analyzed result."""
    query = CLINICAL_QUERIES[exp["query_key"]]
    messages = exp["messages_fn"](query)

    # Separate response_format from other params
    params = dict(exp["params"])
    response_format = params.pop("response_format", None)

    result = ExperimentResult(
        experiment_id=exp["id"],
        category=exp["category"],
        description=exp["description"],
        query=query,
        messages=messages,
        params=exp["params"],
    )

    try:
        t0 = time.monotonic()
        resp = call_model(
            messages,
            max_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature", 0.0),
            response_format=response_format,
        )
        result.latency_ms = (time.monotonic() - t0) * 1000
        result.raw_response = resp["choices"][0]["message"]["content"]
        result.analyze()
    except Exception as e:
        result.error = str(e)

    return result


def run_all(experiments: list[dict], output_dir: Path) -> list[ExperimentResult]:
    """Run all experiments sequentially, saving results incrementally."""
    results = []
    total = len(experiments)
    print(f"\nRunning {total} experiments...\n")

    for i, exp in enumerate(experiments, 1):
        tag = f"[{i:3d}/{total}]"
        print(f"{tag} {exp['id']:<55s}", end="", flush=True)

        result = run_experiment(exp)

        think_flag = "THINK" if result.has_thinking else "     "
        if result.error:
            print(f"  ERROR: {result.error[:60]}")
        else:
            print(
                f"  {think_flag}  "
                f"think_words={result.thinking_token_count:4d}  "
                f"visible_words={result.visible_token_count:4d}  "
                f"{result.latency_ms:6.0f}ms"
            )

        results.append(result)

        # Save incrementally
        with open(output_dir / "results.jsonl", "a") as f:
            f.write(json.dumps(asdict(result), default=str) + "\n")

    return results


# ── Gemini judge ────────────────────────────────────────────────────────

JUDGE_PROMPT = """\
You are evaluating whether a medical AI model engaged in **thinking / reasoning** \
before (or while) producing its response.

"Thinking" means the model performed explicit step-by-step analysis, deliberated \
between options, considered clinical factors, weighed evidence, or showed any form \
of internal reasoning process — regardless of whether it used a special token or tag \
to mark it. Thinking can appear as:
- A clearly structured chain-of-thought (numbered steps, bullet points)
- Phrases like "Let me consider…", "First, I need to…", "Key factors are…"
- Explicit differential diagnosis work-up
- Weighing pros/cons of treatment options
- Any metacognitive process (reflecting on what information is needed)

"NOT thinking" means the model jumped straight to a final answer, a definition, \
a list of facts, or a direct recommendation without showing deliberation.

Respond with ONLY a JSON object (no markdown fences):
{{
  "thinks": true/false,
  "score": <0-10 integer, 0=no reasoning at all, 10=deep multi-step deliberation>,
  "rationale": "<1-2 sentence explanation>"
}}

---

**Original query:** {query}

**Model response:**
{response}
"""

_gemini_client: httpx.Client | None = None


def _get_gemini_client() -> httpx.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = httpx.Client(timeout=30.0)
    return _gemini_client


def gemini_judge(query: str, raw_response: str) -> dict:
    """Ask Gemini to evaluate whether the response contains thinking.

    Returns dict with keys: thinks (bool), score (int 0-10), rationale (str).
    """
    prompt = JUDGE_PROMPT.format(query=query, response=raw_response[:3000])
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
    }
    resp = _get_gemini_client().post(url, json=payload)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def judge_all(results: list[ExperimentResult]) -> list[ExperimentResult]:
    """Run Gemini judge on every result that has a raw_response."""
    if not GEMINI_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set. Cannot run Gemini judge.")
        sys.exit(1)

    total = len([r for r in results if r.raw_response and not r.error])
    print(f"\nRunning Gemini judge on {total} responses...\n")

    i = 0
    for r in results:
        if not r.raw_response or r.error:
            continue
        i += 1
        print(f"[{i:3d}/{total}] {r.experiment_id:<55s}", end="", flush=True)
        try:
            verdict = gemini_judge(r.query, r.raw_response)
            r.gemini_thinks = verdict.get("thinks", False)
            r.gemini_score = verdict.get("score", 0)
            r.gemini_rationale = verdict.get("rationale", "")
            flag = "THINKS" if r.gemini_thinks else "      "
            print(f"  {flag}  score={r.gemini_score:2d}  {r.gemini_rationale[:60]}")
        except Exception as e:
            r.gemini_thinks = None
            r.gemini_score = None
            r.gemini_rationale = f"ERROR: {e}"
            print(f"  ERROR: {e}")

    return results


# ── Report generation ───────────────────────────────────────────────────

def load_results(output_dir: Path) -> list[ExperimentResult]:
    """Load results from JSONL file, re-analyzing raw_response with the
    fixed regex (handles missing ``<unused95>`` close tags)."""
    results = []
    with open(output_dir / "results.jsonl") as f:
        for line in f:
            d = json.loads(line)
            r = ExperimentResult(
                experiment_id=d["experiment_id"],
                category=d["category"],
                description=d["description"],
                query=d["query"],
                messages=d["messages"],
                params=d["params"],
                raw_response=d.get("raw_response", ""),
                latency_ms=d.get("latency_ms", 0),
                error=d.get("error"),
                gemini_thinks=d.get("gemini_thinks"),
                gemini_score=d.get("gemini_score"),
                gemini_rationale=d.get("gemini_rationale"),
            )
            # Re-analyze with the corrected regex
            if r.raw_response:
                r.analyze()
            results.append(r)
    return results


def generate_report(results: list[ExperimentResult], output_dir: Path):
    """Generate Markdown report analyzing the experiment results."""
    lines: list[str] = []
    w = lines.append

    w("# MedGemma 4B — Thinking Mode Experiments")
    w("")
    w(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"**Model:** `{MODEL}`")
    w(f"**Endpoint:** `{ENDPOINT}`")
    w(f"**Total experiments:** {len(results)}")
    w(f"**Errors:** {sum(1 for r in results if r.error)}")
    w("")

    # ── Overall summary ─────────────────────────────────────────────
    thinking_results = [r for r in results if r.has_thinking and not r.error]
    no_thinking = [r for r in results if not r.has_thinking and not r.error]
    successful = [r for r in results if not r.error]

    w("## Executive Summary")
    w("")
    w(f"- **{len(thinking_results)}/{len(successful)}** experiments triggered thinking tokens "
      f"({100 * len(thinking_results) / max(len(successful), 1):.1f}%)")
    if thinking_results:
        avg_think_words = sum(r.thinking_token_count for r in thinking_results) / len(thinking_results)
        avg_think_latency = sum(r.latency_ms for r in thinking_results) / len(thinking_results)
        avg_no_think_latency = (
            sum(r.latency_ms for r in no_thinking) / len(no_thinking)
            if no_thinking else 0
        )
        closed = sum(1 for r in thinking_results if r.has_close_tag)
        w(f"- **Avg thinking words** (when present): {avg_think_words:.0f}")
        w(f"- **Close tag emitted:** {closed}/{len(thinking_results)} "
          f"({100 * closed / len(thinking_results):.0f}%)")
        w(f"- **Avg latency with thinking:** {avg_think_latency:.0f}ms")
        w(f"- **Avg latency without thinking:** {avg_no_think_latency:.0f}ms")
        w(f"- **Latency overhead:** {avg_think_latency - avg_no_think_latency:+.0f}ms")

    # Gemini judge summary
    judged = [r for r in successful if r.gemini_thinks is not None]
    if judged:
        gemini_yes = [r for r in judged if r.gemini_thinks]
        avg_score = sum(r.gemini_score or 0 for r in judged) / len(judged)
        w("")
        w(f"### Gemini Judge")
        w(f"- **{len(gemini_yes)}/{len(judged)}** responses judged as thinking "
          f"({100 * len(gemini_yes) / len(judged):.1f}%)")
        w(f"- **Avg reasoning score:** {avg_score:.1f}/10")
        # Agreement stats
        agree = sum(
            1 for r in judged
            if r.has_thinking == r.gemini_thinks
        )
        w(f"- **Agreement with token detection:** {agree}/{len(judged)} "
          f"({100 * agree / len(judged):.0f}%)")
        # Cases where Gemini sees thinking but no token
        extra = [r for r in judged if r.gemini_thinks and not r.has_thinking]
        if extra:
            w(f"- **Thinking without `<unused94>` token:** {len(extra)} cases")
    w("")

    # ── Per-category analysis ───────────────────────────────────────
    categories = sorted(set(r.category for r in results))
    w("## Per-Category Results")
    w("")

    for cat in categories:
        cat_results = [r for r in results if r.category == cat and not r.error]
        cat_thinking = [r for r in cat_results if r.has_thinking]
        cat_label = cat.split("_", 1)[1].replace("_", " ").title()

        w(f"### {cat_label}")
        w("")
        w(f"Thinking triggered: **{len(cat_thinking)}/{len(cat_results)}** "
          f"({100 * len(cat_thinking) / max(len(cat_results), 1):.0f}%)")
        w("")

        # Table — include Gemini columns if judging was done
        has_gemini = any(r.gemini_thinks is not None for r in cat_results)
        if has_gemini:
            w("| Experiment | Thinking? | Closed? | Think Words | Visible Words | Latency | Gemini Thinks? | Gemini Score |")
            w("|------------|-----------|---------|-------------|---------------|---------|----------------|--------------|")
            for r in cat_results:
                think = "Yes" if r.has_thinking else "No"
                closed = "Yes" if r.has_close_tag else ("No" if r.has_thinking else "-")
                g_thinks = ("Yes" if r.gemini_thinks else "No") if r.gemini_thinks is not None else "-"
                g_score = str(r.gemini_score) if r.gemini_score is not None else "-"
                w(f"| `{r.experiment_id}` | {think} | {closed} | {r.thinking_token_count} | {r.visible_token_count} | {r.latency_ms:.0f} | {g_thinks} | {g_score} |")
        else:
            w("| Experiment | Thinking? | Closed? | Think Words | Visible Words | Latency (ms) |")
            w("|------------|-----------|---------|-------------|---------------|--------------|")
            for r in cat_results:
                think = "Yes" if r.has_thinking else "No"
                closed = "Yes" if r.has_close_tag else ("No" if r.has_thinking else "-")
                w(f"| `{r.experiment_id}` | {think} | {closed} | {r.thinking_token_count} | {r.visible_token_count} | {r.latency_ms:.0f} |")
        w("")

        # Category-specific insights
        if cat_thinking:
            w("**Thinking samples (first 200 chars):**")
            w("")
            for r in cat_thinking[:3]:
                snippet = r.thinking_content[:200].replace("\n", " ")
                w(f"- `{r.experiment_id}`: _{snippet}_")
            w("")

    # ── Thinking trigger heatmap ────────────────────────────────────
    w("## Thinking Trigger Heatmap")
    w("")
    w("Which (strategy × query) combinations trigger thinking?")
    w("")

    # Group by category + query
    query_keys = list(CLINICAL_QUERIES.keys())
    w("| Strategy | " + " | ".join(query_keys) + " |")
    w("|----------|" + "|".join("---" for _ in query_keys) + "|")

    # Build lookup
    result_lookup = {}
    for r in results:
        if not r.error:
            # Extract query key from experiment id
            for qk in query_keys:
                if r.experiment_id.endswith(f"-{qk}"):
                    strategy = r.experiment_id[:-(len(qk) + 1)]
                    result_lookup[(strategy, qk)] = r
                    break

    strategies = sorted(set(k[0] for k in result_lookup))
    for strat in strategies:
        row = f"| `{strat}` |"
        for qk in query_keys:
            r = result_lookup.get((strat, qk))
            if r is None:
                row += " - |"
            elif r.has_thinking:
                row += f" **T**({r.thinking_token_count}) |"
            else:
                row += " . |"
        w(row)
    w("")
    w("_**T**(n) = thinking triggered with n words, **.** = no thinking, **-** = not tested_")
    w("")

    # ── Best strategies ─────────────────────────────────────────────
    w("## Best Strategies for Triggering Thinking")
    w("")
    if thinking_results:
        # Rank by thinking word count
        ranked = sorted(thinking_results, key=lambda r: r.thinking_token_count, reverse=True)
        w("### Top 10 by thinking depth (word count)")
        w("")
        for i, r in enumerate(ranked[:10], 1):
            w(f"{i}. **`{r.experiment_id}`** — {r.thinking_token_count} words, "
              f"{r.latency_ms:.0f}ms")
            snippet = r.thinking_content[:150].replace("\n", " ")
            w(f"   > _{snippet}_")
            w("")
    else:
        w("No experiments triggered thinking tokens.")
        w("")

    # ── Guided generation analysis ──────────────────────────────────
    w("## Guided Generation (Outlines) Analysis")
    w("")
    guided_results = [r for r in results if "guided" in r.category and not r.error]
    if guided_results:
        guided_thinking = [r for r in guided_results if r.has_thinking]
        w(f"Thinking in guided generation: **{len(guided_thinking)}/{len(guided_results)}**")
        w("")
        w("When Outlines constrains output to a JSON schema, the model's behavior "
          "changes. The thinking tokens may appear *before* the JSON begins, "
          "*inside* string fields, or be suppressed entirely.")
        w("")
        for r in guided_results:
            w(f"**`{r.experiment_id}`**")
            w(f"- Thinking: {'Yes' if r.has_thinking else 'No'} ({r.thinking_token_count} words)")
            # Try to parse as JSON for structured analysis
            try:
                parsed = json.loads(r.visible_content or r.raw_response)
                for k, v in parsed.items():
                    preview = str(v)[:100]
                    w(f"- `{k}`: _{preview}_")
            except (json.JSONDecodeError, TypeError):
                w(f"- Raw (first 200): _{r.visible_content[:200]}_")
            w("")
    else:
        w("No guided generation experiments completed successfully.")
        w("")

    # ── Temperature analysis ────────────────────────────────────────
    w("## Temperature Effect")
    w("")
    temp_results = [r for r in results if r.category == "1_baseline_temperature" and not r.error]
    if temp_results:
        temps_seen = sorted(set(r.params.get("temperature", 0) for r in temp_results))
        w("| Temperature | Thinking Rate | Avg Think Words | Avg Visible Words | Avg Latency |")
        w("|-------------|---------------|-----------------|-------------------|-------------|")
        for t in temps_seen:
            t_results = [r for r in temp_results if r.params.get("temperature", 0) == t]
            t_thinking = [r for r in t_results if r.has_thinking]
            rate = f"{len(t_thinking)}/{len(t_results)}"
            avg_tw = sum(r.thinking_token_count for r in t_results) / max(len(t_results), 1)
            avg_vw = sum(r.visible_token_count for r in t_results) / max(len(t_results), 1)
            avg_lat = sum(r.latency_ms for r in t_results) / max(len(t_results), 1)
            w(f"| {t} | {rate} | {avg_tw:.0f} | {avg_vw:.0f} | {avg_lat:.0f}ms |")
    w("")

    # ── Max tokens analysis ─────────────────────────────────────────
    w("## Max Tokens Effect")
    w("")
    mt_results = [r for r in results if r.category == "8_max_tokens" and not r.error]
    if mt_results:
        tokens_seen = sorted(set(r.params.get("max_tokens", 0) for r in mt_results))
        w("| Max Tokens | Thinking Rate | Avg Think Words | Avg Visible Words |")
        w("|------------|---------------|-----------------|-------------------|")
        for mt in tokens_seen:
            m_results = [r for r in mt_results if r.params.get("max_tokens", 0) == mt]
            m_thinking = [r for r in m_results if r.has_thinking]
            rate = f"{len(m_thinking)}/{len(m_results)}"
            avg_tw = sum(r.thinking_token_count for r in m_results) / max(len(m_results), 1)
            avg_vw = sum(r.visible_token_count for r in m_results) / max(len(m_results), 1)
            w(f"| {mt} | {rate} | {avg_tw:.0f} | {avg_vw:.0f} |")
    w("")

    # ── Errors ──────────────────────────────────────────────────────
    error_results = [r for r in results if r.error]
    if error_results:
        w("## Errors")
        w("")
        for r in error_results:
            w(f"- `{r.experiment_id}`: {r.error[:200]}")
        w("")

    # ── Gemini judge deep-dive ────────────────────────────────────
    judged_all = [r for r in results if r.gemini_thinks is not None and not r.error]
    if judged_all:
        w("## Gemini Judge — Deep Dive")
        w("")

        # Disagreements: Gemini sees thinking, token detection doesn't
        hidden_thinking = [r for r in judged_all if r.gemini_thinks and not r.has_thinking]
        if hidden_thinking:
            w(f"### Hidden Thinking (Gemini=Yes, Token=No) — {len(hidden_thinking)} cases")
            w("")
            w("These responses exhibit reasoning behavior without the `<unused94>` token:")
            w("")
            w("| Experiment | Gemini Score | Rationale | Response Preview |")
            w("|------------|-------------|-----------|------------------|")
            for r in sorted(hidden_thinking, key=lambda r: r.gemini_score or 0, reverse=True):
                rationale = (r.gemini_rationale or "")[:80].replace("|", "/")
                preview = r.raw_response[:80].replace("|", "/").replace("\n", " ")
                w(f"| `{r.experiment_id}` | {r.gemini_score} | {rationale} | {preview} |")
            w("")

        # Disagreements: Token detected, Gemini says no
        false_positive = [r for r in judged_all if r.has_thinking and not r.gemini_thinks]
        if false_positive:
            w(f"### Token Thinking without Reasoning Quality (Token=Yes, Gemini=No) — {len(false_positive)} cases")
            w("")
            w("| Experiment | Gemini Score | Rationale |")
            w("|------------|-------------|-----------|")
            for r in false_positive:
                rationale = (r.gemini_rationale or "")[:100].replace("|", "/")
                w(f"| `{r.experiment_id}` | {r.gemini_score} | {rationale} |")
            w("")

        # Score distribution
        w("### Score Distribution")
        w("")
        w("| Score | Count | With Token | Without Token |")
        w("|-------|-------|------------|---------------|")
        for s in range(11):
            at_score = [r for r in judged_all if r.gemini_score == s]
            with_tok = sum(1 for r in at_score if r.has_thinking)
            without_tok = len(at_score) - with_tok
            if at_score:
                w(f"| {s} | {len(at_score)} | {with_tok} | {without_tok} |")
        w("")

        # Per-category Gemini thinking rate
        w("### Gemini Thinking Rate by Category")
        w("")
        w("| Category | Token Rate | Gemini Rate | Avg Gemini Score |")
        w("|----------|-----------|-------------|------------------|")
        for cat in categories:
            cat_judged = [r for r in judged_all if r.category == cat]
            if not cat_judged:
                continue
            cat_label = cat.split("_", 1)[1].replace("_", " ").title()
            tok_rate = sum(1 for r in cat_judged if r.has_thinking)
            gem_rate = sum(1 for r in cat_judged if r.gemini_thinks)
            avg_s = sum(r.gemini_score or 0 for r in cat_judged) / len(cat_judged)
            w(f"| {cat_label} | {tok_rate}/{len(cat_judged)} | {gem_rate}/{len(cat_judged)} | {avg_s:.1f} |")
        w("")

    # ── Recommendations ─────────────────────────────────────────────
    w("## Recommendations")
    w("")
    w("_Based on experimental findings — fill in after reviewing results._")
    w("")
    w("1. **Best strategy for reliable thinking:**")
    w("2. **Best temperature range:**")
    w("3. **Does guided generation suppress thinking?**")
    w("4. **Does prefix priming help?**")
    w("5. **Recommended production configuration:**")
    w("")

    report_text = "\n".join(lines)
    report_path = output_dir / "report.md"
    report_path.write_text(report_text)
    print(f"\nReport written to: {report_path}")
    return report_text


# ── Main ────────────────────────────────────────────────────────────────

def save_results(results: list[ExperimentResult], output_dir: Path):
    """Write all results to JSONL (overwrites)."""
    with open(output_dir / "results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(asdict(r), default=str) + "\n")


def main():
    parser = argparse.ArgumentParser(description="MedGemma 4B thinking-mode experiments")
    parser.add_argument(
        "--report-only",
        metavar="DIR",
        help="Skip running experiments; generate report from existing results in DIR",
    )
    parser.add_argument(
        "--judge",
        metavar="DIR",
        help="Run Gemini judge on existing results in DIR, then regenerate report",
    )
    args = parser.parse_args()

    if args.judge:
        output_dir = Path(args.judge)
        if not (output_dir / "results.jsonl").exists():
            print(f"No results.jsonl in {output_dir}")
            sys.exit(1)
        results = load_results(output_dir)
        results = judge_all(results)
        save_results(results, output_dir)
        generate_report(results, output_dir)
        judged = [r for r in results if r.gemini_thinks is not None and not r.error]
        gem_yes = sum(1 for r in judged if r.gemini_thinks)
        print(f"\nGemini judged {gem_yes}/{len(judged)} as thinking.")
        print(f"Report: {output_dir / 'report.md'}")
        return

    if args.report_only:
        output_dir = Path(args.report_only)
        if not (output_dir / "results.jsonl").exists():
            print(f"No results.jsonl in {output_dir}")
            sys.exit(1)
        results = load_results(output_dir)
        generate_report(results, output_dir)
        return

    # Connectivity check
    print(f"Endpoint: {ENDPOINT}")
    print(f"Model:    {MODEL}")
    print("Checking connectivity...", end=" ", flush=True)
    try:
        resp = get_client().get(f"{ENDPOINT.rstrip('/')}/v1/models")
        resp.raise_for_status()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("thinking_experiments") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    experiments = build_experiments()

    # Save experiment manifest
    manifest = []
    for exp in experiments:
        manifest.append({
            "id": exp["id"],
            "category": exp["category"],
            "description": exp["description"],
            "query_key": exp["query_key"],
            "params": exp["params"],
        })
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"Output directory: {output_dir}")
    print(f"Experiments: {len(experiments)}")

    results = run_all(experiments, output_dir)
    generate_report(results, output_dir)

    # Summary
    ok = [r for r in results if not r.error]
    thinking = [r for r in ok if r.has_thinking]
    print(f"\n{'='*60}")
    print(f"Done. {len(thinking)}/{len(ok)} experiments triggered thinking tokens.")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
