"""Test script for DocGemma v2 tool planning accuracy.

Tests the model's ability to:
1. Triage queries into the correct route (direct/lookup/reasoning/multi_step)
2. Select the correct tool for lookup queries (triage_tool)
3. Plan correct tool + args for each subtask (plan_tool node)
4. Decompose multi-step queries into correct subtasks
5. Extract tool needs from reasoning chains
6. End-to-end: verify the right tool is called with correct args

Run:
    cd docgemma-connect
    uv run python test_tool_planning.py

Logs saved to: test_tool_planning/<run-timestamp>/
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
LOGS_BASE = Path(__file__).parent / "test_tool_planning"
RUN_DIR = LOGS_BASE / f"run-{datetime.now().strftime('%m%d%Y-%H%M%S')}"
RUN_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.WARNING, format="%(message)s")
# Silence chatty loggers during test
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("docgemma").setLevel(logging.WARNING)

from src.docgemma import DocGemma
from src.docgemma.agent.nodes import (
    clinical_context_assembler,
    decompose_intent,
    extract_tool_needs,
    fast_tool_validate,
    image_detection,
    plan_tool,
    thinking_mode,
    triage_router,
)
from src.docgemma.agent.state import DocGemmaState


# =============================================================================
# Test infrastructure
# =============================================================================

@dataclass
class TestResult:
    test_id: str
    test_name: str
    category: str
    passed: bool
    expected: dict
    actual: dict
    details: str = ""
    elapsed_s: float = 0.0


@dataclass
class TestSuite:
    results: list[TestResult] = field(default_factory=list)
    _start: float = 0.0

    def add(self, r: TestResult):
        self.results.append(r)
        icon = "PASS" if r.passed else "FAIL"
        print(f"  [{icon}] {r.test_id}: {r.test_name} ({r.elapsed_s:.1f}s)")
        if not r.passed:
            print(f"         expected: {r.expected}")
            print(f"         actual:   {r.actual}")
            if r.details:
                print(f"         details:  {r.details}")

    def summary(self) -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        lines = [
            "",
            "=" * 70,
            "TEST RESULTS SUMMARY",
            "=" * 70,
            f"Total: {total}  |  Passed: {passed}  |  Failed: {failed}",
            "",
        ]

        # By category
        categories: dict[str, list[TestResult]] = {}
        for r in self.results:
            categories.setdefault(r.category, []).append(r)

        for cat, results in categories.items():
            cat_passed = sum(1 for r in results if r.passed)
            lines.append(f"  {cat}: {cat_passed}/{len(results)}")

        if failed:
            lines.append("")
            lines.append("FAILURES:")
            for r in self.results:
                if not r.passed:
                    lines.append(f"  {r.test_id}: {r.test_name}")
                    lines.append(f"    expected: {r.expected}")
                    lines.append(f"    actual:   {r.actual}")
                    if r.details:
                        lines.append(f"    details:  {r.details}")

        lines.append("")
        lines.append(f"Logs: {RUN_DIR}")
        return "\n".join(lines)


def _make_state(user_input: str, **overrides) -> DocGemmaState:
    """Create a minimal agent state for testing a single node."""
    state: dict = {
        "user_input": user_input,
        "image_data": None,
        "image_present": False,
        "clinical_context": None,
        "triage_route": None,
        "triage_tool": None,
        "triage_query": None,
        "reasoning": None,
        "reasoning_tool_needs": None,
        "reasoning_continuation": None,
        "subtasks": [],
        "current_subtask_index": 0,
        "tool_results": [],
        "loop_iterations": 0,
        "tool_retries": 0,
        "_planned_tool": None,
        "_planned_args": None,
        "validation_error": None,
        "error_strategy": None,
        "last_result_status": None,
        "needs_user_input": False,
        "missing_info": None,
        "final_response": None,
    }
    state.update(overrides)
    return state


# =============================================================================
# 1. TRIAGE ROUTER TESTS
# =============================================================================

TRIAGE_CASES = [
    # (id, query, expected_route, expected_tool_if_lookup)
    # --- DIRECT ---
    ("TR-01", "What is hypertension?", "direct", None),
    ("TR-02", "What are the symptoms of diabetes?", "direct", None),
    ("TR-03", "Explain the mechanism of action of ACE inhibitors", "direct", None),
    ("TR-04", "What is the difference between type 1 and type 2 diabetes?", "direct", None),
    # --- LOOKUP ---
    ("TR-05", "Check FDA warnings for metformin", "lookup", "check_drug_safety"),
    ("TR-06", "Search PubMed for GLP-1 agonist studies", "lookup", "search_medical_literature"),
    ("TR-07", "Check drug interactions between warfarin and aspirin", "lookup", "check_drug_interactions"),
    ("TR-08", "Find clinical trials for lung cancer", "lookup", "find_clinical_trials"),
    ("TR-09", "Search for patient John Smith", "lookup", "search_patient"),
    ("TR-10", "Check safety profile of dofetilide", "lookup", "check_drug_safety"),
    # --- REASONING ---
    ("TR-11", "Best antihypertensive for a patient with CKD stage 3?", "reasoning", None),
    ("TR-12", "What would be the safest NSAID for an elderly patient with heart failure?", "reasoning", None),
    ("TR-13", "Should I start metformin or a GLP-1 agonist for a newly diagnosed diabetic with obesity?", "reasoning", None),
    # --- MULTI_STEP ---
    ("TR-14", "Find warfarin safety warnings and check interactions with aspirin", "multi_step", None),
    ("TR-15", "Search for patient John Smith, get his chart, and check if his metformin has safety issues", "multi_step", None),
    ("TR-16", "Check interactions between lisinopril and potassium, then search literature on hyperkalemia risk", "multi_step", None),
]


def run_triage_tests(model: DocGemma, suite: TestSuite):
    print("\n" + "=" * 70)
    print("1. TRIAGE ROUTER TESTS")
    print("=" * 70)

    for test_id, query, expected_route, expected_tool in TRIAGE_CASES:
        start = time.perf_counter()

        # Run image_detection + clinical_context_assembler + triage_router
        state = _make_state(query)
        state = image_detection(state)
        state = clinical_context_assembler(state)
        state = triage_router(state, model)

        elapsed = time.perf_counter() - start

        actual_route = state.get("triage_route")
        actual_tool = state.get("triage_tool")

        route_ok = actual_route == expected_route
        tool_ok = True
        details = ""

        if expected_route == "lookup" and expected_tool:
            tool_ok = actual_tool == expected_tool
            if not tool_ok:
                details = f"tool: expected={expected_tool}, got={actual_tool}"

        passed = route_ok and tool_ok

        suite.add(TestResult(
            test_id=test_id,
            test_name=f"Triage: {query[:50]}...",
            category="triage",
            passed=passed,
            expected={"route": expected_route, "tool": expected_tool},
            actual={"route": actual_route, "tool": actual_tool, "query": state.get("triage_query")},
            details=details,
            elapsed_s=elapsed,
        ))


# =============================================================================
# 2. PLAN TOOL TESTS (tool selection + arg extraction)
# =============================================================================

PLAN_TOOL_CASES = [
    # (id, intent, suggested_tool, expected_tool, expected_args_keys, expected_args_values)
    # --- Drug safety ---
    ("PT-01", "Look up FDA boxed warnings for metformin", "check_drug_safety",
     "check_drug_safety", ["drug_name"], {"drug_name": "metformin"}),
    ("PT-02", "Check safety profile of dofetilide", "check_drug_safety",
     "check_drug_safety", ["drug_name"], {"drug_name": "dofetilide"}),
    # --- Literature ---
    ("PT-03", "Search PubMed for PCSK9 inhibitor studies on LDL", "search_medical_literature",
     "search_medical_literature", ["query"], None),
    ("PT-04", "Find recent studies on GLP-1 agonists for weight loss", "search_medical_literature",
     "search_medical_literature", ["query"], None),
    # --- Drug interactions ---
    ("PT-05", "Check interactions between warfarin and aspirin", "check_drug_interactions",
     "check_drug_interactions", ["drug_list"], None),
    ("PT-06", "Check if azithromycin interacts with warfarin", "check_drug_interactions",
     "check_drug_interactions", ["drug_list"], None),
    # --- Clinical trials ---
    ("PT-07", "Find clinical trials for lung cancer", "find_clinical_trials",
     "find_clinical_trials", ["query"], None),
    # --- Patient search ---
    ("PT-08", "Find patient John Smith", "search_patient",
     "search_patient", ["name"], {"name": "John Smith"}),
    ("PT-09", "Search for patient records for Jane Doe", "search_patient",
     "search_patient", ["name"], None),
    # --- Patient chart ---
    ("PT-10", "Get clinical summary for patient abc-123", "get_patient_chart",
     "get_patient_chart", ["patient_id"], {"patient_id": "abc-123"}),
    # --- Allergy ---
    ("PT-11", "Document penicillin allergy with rash reaction for patient abc-123", "add_allergy",
     "add_allergy", ["patient_id", "substance", "reaction"], {"patient_id": "abc-123"}),
    # --- Prescription ---
    ("PT-12", "Prescribe lisinopril 10mg once daily for patient abc-123", "prescribe_medication",
     "prescribe_medication", ["patient_id", "medication_name", "dosage", "frequency"], {"patient_id": "abc-123"}),
    # --- Clinical note ---
    ("PT-13", "Save a clinical note for patient abc-123 about hypertension diagnosis", "save_clinical_note",
     "save_clinical_note", ["patient_id", "note_text"], {"patient_id": "abc-123"}),
]


def run_plan_tool_tests(model: DocGemma, suite: TestSuite):
    print("\n" + "=" * 70)
    print("2. PLAN TOOL TESTS (tool selection + argument extraction)")
    print("=" * 70)

    for test_id, intent, suggested, expected_tool, expected_keys, expected_vals in PLAN_TOOL_CASES:
        start = time.perf_counter()

        state = _make_state(
            user_input=intent,
            subtasks=[{"intent": intent, "requires_tool": suggested, "context": intent}],
            current_subtask_index=0,
        )
        state = plan_tool(state, model)

        elapsed = time.perf_counter() - start

        actual_tool = state.get("_planned_tool")
        actual_args = state.get("_planned_args", {})

        tool_ok = actual_tool == expected_tool

        # Check required args are present
        keys_ok = all(k in actual_args and actual_args[k] for k in expected_keys)
        missing_keys = [k for k in expected_keys if k not in actual_args or not actual_args[k]]

        # Check specific values if provided
        vals_ok = True
        wrong_vals = {}
        if expected_vals:
            for k, v in expected_vals.items():
                actual_v = actual_args.get(k, "")
                # Case-insensitive comparison for names
                if isinstance(v, str) and isinstance(actual_v, str):
                    if v.lower() not in actual_v.lower():
                        vals_ok = False
                        wrong_vals[k] = f"expected '{v}', got '{actual_v}'"

        passed = tool_ok and keys_ok and vals_ok
        details = ""
        if not tool_ok:
            details = f"wrong tool: {actual_tool}"
        if missing_keys:
            details += f" missing args: {missing_keys}"
        if wrong_vals:
            details += f" wrong vals: {wrong_vals}"

        suite.add(TestResult(
            test_id=test_id,
            test_name=f"Plan: {intent[:50]}...",
            category="plan_tool",
            passed=passed,
            expected={"tool": expected_tool, "required_args": expected_keys, "values": expected_vals},
            actual={"tool": actual_tool, "args": actual_args},
            details=details.strip(),
            elapsed_s=elapsed,
        ))


# =============================================================================
# 3. DECOMPOSE INTENT TESTS (multi-step planning)
# =============================================================================

DECOMPOSE_CASES = [
    # (id, query, min_subtasks, max_subtasks, expected_tools_subset)
    ("DI-01",
     "Find warfarin safety warnings and check interactions with aspirin",
     2, 3,
     ["check_drug_safety", "check_drug_interactions"]),
    ("DI-02",
     "Search for patient John Smith, get his chart, and check safety of his metformin",
     2, 4,
     ["search_patient", "get_patient_chart"]),
    ("DI-03",
     "Check interactions between lisinopril and potassium, then search literature on hyperkalemia risk",
     2, 3,
     ["check_drug_interactions", "search_medical_literature"]),
    ("DI-04",
     "Prescribe lisinopril 10mg daily for patient abc-123 and save a clinical note about the prescription",
     2, 3,
     ["prescribe_medication", "save_clinical_note"]),
    ("DI-05",
     "Find clinical trials for breast cancer and search literature for HER2 targeted therapy",
     2, 3,
     ["find_clinical_trials", "search_medical_literature"]),
]


def run_decompose_tests(model: DocGemma, suite: TestSuite):
    print("\n" + "=" * 70)
    print("3. DECOMPOSE INTENT TESTS (multi-step subtask planning)")
    print("=" * 70)

    for test_id, query, min_sub, max_sub, expected_tools in DECOMPOSE_CASES:
        start = time.perf_counter()

        state = _make_state(query, reasoning="Complex multi-step query requiring multiple tools.")
        state = decompose_intent(state, model)

        elapsed = time.perf_counter() - start

        subtasks = state.get("subtasks", [])
        n_subtasks = len(subtasks)
        actual_tools = [s.get("requires_tool") for s in subtasks]

        count_ok = min_sub <= n_subtasks <= max_sub
        # Check that expected tools appear somewhere in the subtask list
        tools_ok = all(t in actual_tools for t in expected_tools)
        missing_tools = [t for t in expected_tools if t not in actual_tools]

        passed = count_ok and tools_ok
        details = ""
        if not count_ok:
            details = f"count: expected {min_sub}-{max_sub}, got {n_subtasks}"
        if missing_tools:
            details += f" missing tools: {missing_tools}"

        suite.add(TestResult(
            test_id=test_id,
            test_name=f"Decompose: {query[:50]}...",
            category="decompose",
            passed=passed,
            expected={"subtask_count": f"{min_sub}-{max_sub}", "tools": expected_tools},
            actual={"subtask_count": n_subtasks, "tools": actual_tools,
                    "subtasks": [s.get("intent") for s in subtasks]},
            details=details.strip(),
            elapsed_s=elapsed,
        ))


# =============================================================================
# 4. EXTRACT TOOL NEEDS TESTS (reasoning path)
# =============================================================================

EXTRACT_TOOL_CASES = [
    # (id, query, reasoning, should_need_tool, expected_tool)
    ("ET-01",
     "Best antihypertensive for CKD stage 3?",
     "CKD stage 3 requires careful BP management. ACE inhibitors like lisinopril are first-line. "
     "Need to consider GFR, proteinuria, and diabetic status. The reasoning is sufficient from "
     "clinical guidelines alone.",
     False, None),
    ("ET-02",
     "Is metformin safe for my patient with CKD?",
     "Metformin has FDA warnings about lactic acidosis risk in renal impairment. "
     "I should check the current FDA boxed warnings to give accurate guidance.",
     True, "check_drug_safety"),
    ("ET-03",
     "What are the latest studies on SGLT2 inhibitors for heart failure?",
     "SGLT2 inhibitors have shown remarkable cardiovascular benefits. Recent trials like "
     "DAPA-HF and EMPEROR-Reduced demonstrate mortality reduction. I should search PubMed "
     "for the latest evidence.",
     True, "search_medical_literature"),
    ("ET-04",
     "Can I give warfarin with amiodarone?",
     "Warfarin has many drug interactions. Amiodarone is a well-known CYP inhibitor that "
     "increases warfarin levels significantly. I should verify the interaction details.",
     True, "check_drug_interactions"),
]


def run_extract_tool_tests(model: DocGemma, suite: TestSuite):
    print("\n" + "=" * 70)
    print("4. EXTRACT TOOL NEEDS TESTS (reasoning path tool detection)")
    print("=" * 70)

    for test_id, query, reasoning, should_need_tool, expected_tool in EXTRACT_TOOL_CASES:
        start = time.perf_counter()

        state = _make_state(query, reasoning=reasoning)
        state = extract_tool_needs(state, model)

        elapsed = time.perf_counter() - start

        tool_needs = state.get("reasoning_tool_needs")
        actual_needs = tool_needs is not None and tool_needs.get("tool") is not None
        actual_tool = tool_needs.get("tool") if tool_needs else None

        needs_ok = actual_needs == should_need_tool
        tool_ok = True
        if should_need_tool and expected_tool:
            tool_ok = actual_tool == expected_tool

        passed = needs_ok and tool_ok
        details = ""
        if not needs_ok:
            details = f"needs_tool: expected={should_need_tool}, got={actual_needs}"
        if not tool_ok:
            details += f" tool: expected={expected_tool}, got={actual_tool}"

        suite.add(TestResult(
            test_id=test_id,
            test_name=f"ExtractTool: {query[:45]}...",
            category="extract_tool_needs",
            passed=passed,
            expected={"needs_tool": should_need_tool, "tool": expected_tool},
            actual={"needs_tool": actual_needs, "tool": actual_tool},
            details=details.strip(),
            elapsed_s=elapsed,
        ))


# =============================================================================
# 5. FAST VALIDATE TESTS (lookup path validation)
# =============================================================================

VALIDATE_CASES = [
    # (id, tool, query, should_be_valid)
    ("FV-01", "check_drug_safety", "metformin", True),
    ("FV-02", "check_drug_interactions", "warfarin, aspirin", True),
    ("FV-03", "check_drug_interactions", "warfarin", False),  # only 1 drug, no comma
    ("FV-04", "get_patient_chart", "abc-123", False),  # query goes to query, not patient_id
    ("FV-05", "search_patient", "John Smith", True),
    ("FV-06", None, "", False),  # no tool
    ("FV-07", "analyze_medical_image", "chest xray", False),  # no image attached
]


def run_validate_tests(suite: TestSuite):
    print("\n" + "=" * 70)
    print("5. FAST VALIDATE TESTS (lookup path arg validation)")
    print("=" * 70)

    for test_id, tool, query, should_valid in VALIDATE_CASES:
        start = time.perf_counter()

        state = _make_state(
            user_input=f"Test query for {tool}",
            triage_tool=tool,
            triage_query=query,
        )
        state = fast_tool_validate(state)

        elapsed = time.perf_counter() - start

        has_error = state.get("validation_error") is not None
        actual_valid = not has_error

        passed = actual_valid == should_valid
        details = ""
        if not passed:
            details = f"error: {state.get('validation_error')}"

        suite.add(TestResult(
            test_id=test_id,
            test_name=f"Validate: {tool}({query[:30]})",
            category="validation",
            passed=passed,
            expected={"valid": should_valid},
            actual={"valid": actual_valid, "error": state.get("validation_error"),
                    "planned_tool": state.get("_planned_tool"),
                    "planned_args": state.get("_planned_args")},
            details=details,
            elapsed_s=elapsed,
        ))


# =============================================================================
# 6. END-TO-END TESTS (full pipeline with recording executor)
# =============================================================================

E2E_CASES = [
    # (id, query, expected_route, expected_tool_calls: list of (tool_name, required_arg_keys))
    ("E2E-01", "What is hypertension?",
     "direct", []),
    ("E2E-02", "Check FDA warnings for warfarin",
     "lookup", [("check_drug_safety", ["drug_name"])]),
    ("E2E-03", "Check drug interactions between warfarin and aspirin",
     "lookup", [("check_drug_interactions", ["drug_list"])]),
    ("E2E-04", "Find clinical trials for breast cancer",
     "lookup", [("find_clinical_trials", ["query"])]),
    ("E2E-05", "Search PubMed for SGLT2 inhibitors and heart failure",
     "lookup", [("search_medical_literature", ["query"])]),
]


async def run_e2e_tests(model: DocGemma, suite: TestSuite):
    print("\n" + "=" * 70)
    print("6. END-TO-END TESTS (full pipeline with recording executor)")
    print("=" * 70)

    from src.docgemma.agent.graph import build_graph

    # Recording tool executor: captures calls and returns mock results
    recorded_calls: list[tuple[str, dict]] = []

    async def recording_executor(tool_name: str, args: dict) -> dict:
        recorded_calls.append((tool_name, args))
        # Return plausible mock data so synthesis doesn't choke
        if tool_name == "check_drug_safety":
            return {"brand_name": args.get("drug_name", ""), "has_warning": True,
                    "boxed_warnings": ["Test warning"], "warnings_count": 1}
        if tool_name == "check_drug_interactions":
            return {"drugs_checked": args.get("drug_list", "").split(","),
                    "interactions": [{"severity": "moderate", "description": "Test interaction"}]}
        if tool_name == "search_medical_literature":
            return {"query": args.get("query", ""), "total_found": 1,
                    "articles": [{"pmid": "12345", "title": "Test Article", "abstract": "..."}]}
        if tool_name == "find_clinical_trials":
            return {"condition": args.get("query", ""), "total_found": 1,
                    "trials": [{"nct_id": "NCT001", "title": "Test Trial", "status": "Recruiting"}]}
        if tool_name == "search_patient":
            return {"patients": [{"id": "test-id", "name": args.get("name", "")}]}
        if tool_name == "get_patient_chart":
            return {"patient_id": args.get("patient_id", ""), "summary": "Test chart"}
        return {"result": "mock", "tool": tool_name}

    for test_id, query, expected_route, expected_calls in E2E_CASES:
        recorded_calls.clear()
        start = time.perf_counter()

        try:
            graph = build_graph(model, tool_executor=recording_executor)
            initial_state: dict = {
                "user_input": query,
                "image_data": None,
                "image_present": False,
                "clinical_context": None,
                "triage_route": None,
                "triage_tool": None,
                "triage_query": None,
                "reasoning": None,
                "reasoning_tool_needs": None,
                "reasoning_continuation": None,
                "subtasks": [],
                "current_subtask_index": 0,
                "tool_results": [],
                "loop_iterations": 0,
                "tool_retries": 0,
                "_planned_tool": None,
                "_planned_args": None,
                "validation_error": None,
                "error_strategy": None,
                "last_result_status": None,
                "needs_user_input": False,
                "missing_info": None,
                "final_response": None,
            }
            result = await graph.ainvoke(initial_state)
            elapsed = time.perf_counter() - start

            actual_route = result.get("triage_route")
            final_response = result.get("final_response")

            route_ok = actual_route == expected_route

            # Check tool calls
            calls_ok = True
            details_parts = []

            if len(expected_calls) == 0:
                # Direct route: should not have made any tool calls
                if len(recorded_calls) > 0:
                    calls_ok = False
                    details_parts.append(f"expected 0 calls, got {len(recorded_calls)}: {recorded_calls}")
            else:
                # Check that each expected tool was called with required args
                actual_tool_names = [c[0] for c in recorded_calls]
                for exp_tool, exp_args in expected_calls:
                    matching = [c for c in recorded_calls if c[0] == exp_tool]
                    if not matching:
                        calls_ok = False
                        details_parts.append(f"missing call to {exp_tool} (called: {actual_tool_names})")
                    else:
                        call_args = matching[0][1]
                        for arg_key in exp_args:
                            if arg_key not in call_args or not call_args[arg_key]:
                                calls_ok = False
                                details_parts.append(f"{exp_tool} missing arg '{arg_key}' (args: {call_args})")

            has_response = final_response is not None and len(final_response) > 10
            passed = route_ok and calls_ok and has_response
            details = "; ".join(details_parts)
            if not has_response:
                details += f" no response (got: {repr(final_response)[:80]})"

            suite.add(TestResult(
                test_id=test_id,
                test_name=f"E2E: {query[:50]}...",
                category="end_to_end",
                passed=passed,
                expected={"route": expected_route, "tool_calls": expected_calls},
                actual={"route": actual_route,
                        "tool_calls": recorded_calls,
                        "response_len": len(final_response) if final_response else 0},
                details=details,
                elapsed_s=elapsed,
            ))

        except Exception as e:
            elapsed = time.perf_counter() - start
            suite.add(TestResult(
                test_id=test_id,
                test_name=f"E2E: {query[:50]}...",
                category="end_to_end",
                passed=False,
                expected={"route": expected_route},
                actual={"error": str(e)},
                details=f"Exception: {e}",
                elapsed_s=elapsed,
            ))


# =============================================================================
# MAIN
# =============================================================================

async def main():
    print("=" * 70)
    print("DocGemma v2 Tool Planning Test Suite")
    print("=" * 70)

    print("\nConnecting to model...")
    model = DocGemma()
    health = model.health_check()
    print(f"  Endpoint: {model._endpoint}")
    print(f"  Model:    {model._model}")
    print(f"  Health:   {health}")

    if not health:
        print("\nERROR: Model endpoint not reachable. Aborting.")
        sys.exit(1)

    suite = TestSuite()

    # 1. Triage router
    run_triage_tests(model, suite)

    # 2. Plan tool
    run_plan_tool_tests(model, suite)

    # 3. Decompose intent
    run_decompose_tests(model, suite)

    # 4. Extract tool needs
    run_extract_tool_tests(model, suite)

    # 5. Fast validate (no LLM needed)
    run_validate_tests(suite)

    # 6. End-to-end
    await run_e2e_tests(model, suite)

    # Summary
    summary = suite.summary()
    print(summary)

    # Save full results to JSON
    results_path = RUN_DIR / "results.json"
    with open(results_path, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "model": model._model,
                "endpoint": model._endpoint,
                "results": [
                    {
                        "test_id": r.test_id,
                        "test_name": r.test_name,
                        "category": r.category,
                        "passed": r.passed,
                        "expected": r.expected,
                        "actual": _safe_serialize(r.actual),
                        "details": r.details,
                        "elapsed_s": r.elapsed_s,
                    }
                    for r in suite.results
                ],
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nFull results: {results_path}")

    # Exit code
    failed = sum(1 for r in suite.results if not r.passed)
    sys.exit(1 if failed else 0)


def _safe_serialize(obj):
    """Make objects JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, bytes):
        return f"<bytes len={len(obj)}>"
    return obj


if __name__ == "__main__":
    asyncio.run(main())
