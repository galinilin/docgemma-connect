"""Test script for DocGemma Agent pipeline with remote inference.

Loads test cases from test_cases_v2.json and runs random samples.
Enable/disable categories below to control which tests run.

Logs for each test case are saved to: test_logs/<test_id>_<timestamp>.log
"""

import asyncio
import io
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Create logs directory structure: test_agent/run-MMDDYYYY/
LOGS_BASE_DIR = Path(__file__).parent / "test_agent"
RUN_FOLDER = f"run-{datetime.now().strftime('%m%d%Y')}"
LOGS_DIR = LOGS_BASE_DIR / RUN_FOLDER
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging to see agent flow
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

from src.docgemma import DocGemma, DocGemmaAgent


# =============================================================================
# CATEGORY CONFIGURATION - Set True/False to enable/disable categories
# =============================================================================
ENABLED_CATEGORIES = {
    "simple_questions": False,        # SQ-01 to SQ-10: Direct factual questions
    "complex_thinking": True,        # CT-01 to CT-10: Reasoning without tools
    "thinking_single_tool": True,   # CTT-01 to CTT-10: Thinking + 1 tool
    "tool_failure": False,           # TF-01 to TF-10: Tool failure handling
    "missing_info": False,           # MI-01 to MI-10: Clarification needed
    "multi_tool": False,             # MT-01 to MT-10: 2-3 tool workflows
    "simple_image": False,           # SQI-01 to SQI-10: Simple image questions
    "complex_thinking_image": False, # CTI-01 to CTI-10: Image + reasoning
    "image_single_tool": False,      # ITT-01 to ITT-10: Image + 1 tool
    "image_missing_info": False,     # IMI-01 to IMI-10: Image + clarification
    "image_multi_tool": False,       # IMT-01 to IMT-10: Image + multi-tool
    "image_tool_failure": False,     # ITF-01 to ITF-10: Image + tool failure
}

# Number of random cases to run per enabled category
CASES_PER_CATEGORY = 3

# Set to a specific test ID to run only that test (e.g., "CT-01"), or None for random
RUN_SPECIFIC_TEST = None  # e.g., "CT-01", "SQ-05", "MT-02"


# =============================================================================
# TOOL EXECUTOR - Set USE_REAL_TOOLS to switch between mock and real
# =============================================================================
USE_REAL_TOOLS = True  # Set to False to use mock tools instead

# Import real tools from registry (unified executor)
from docgemma.tools import execute_tool as registry_execute_tool


async def mock_tool_executor(tool_name: str, args: dict) -> dict:
    """Mock tool executor that returns fake results for testing."""
    print(f"  [TOOL CALL - MOCK] {tool_name}({args})")

    if tool_name == "check_drug_safety":
        return {
            "brand_name": args.get("brand_name") or args.get("drug_name", "unknown"),
            "has_warning": True,
            "boxed_warning": "Mock warning: Use with caution. Monitor for adverse effects.",
        }
    if tool_name == "search_medical_literature":
        return {
            "query": args.get("query", ""),
            "total_found": 3,
            "articles": [
                {"pmid": "12345", "title": "Mock Study on Treatment Efficacy", "abstract": "Results showed..."},
                {"pmid": "12346", "title": "Guidelines Review", "abstract": "Current recommendations..."},
            ],
        }
    if tool_name == "check_drug_interactions":
        drug_list = args.get("drug_list", "")
        drugs = [d.strip() for d in drug_list.split(",")] if drug_list else []
        return {
            "drugs_checked": drugs,
            "interactions": [
                {"severity": "moderate", "description": f"Mock interaction between drugs: {', '.join(drugs) if drugs else 'unknown'}"}
            ] if len(drugs) >= 2 else [],
        }
    if tool_name == "find_clinical_trials":
        return {
            "condition": args.get("condition") or args.get("query", ""),
            "total_found": 2,
            "trials": [
                {"nct_id": "NCT00000001", "title": "Mock Phase 3 Trial", "status": "Recruiting"},
            ],
        }
    if tool_name == "get_patient_record":
        return {
            "patient_id": args.get("patient_id", "unknown"),
            "name": "Mock Patient",
            "medications": ["metformin 500mg BID", "lisinopril 10mg daily"],
            "conditions": ["Type 2 Diabetes", "Hypertension"],
            "allergies": ["Penicillin"],
        }
    if tool_name == "analyze_medical_image":
        return {
            "image_type": "chest_xray",
            "findings": "Mock findings: No acute abnormality identified.",
            "impression": "Normal study.",
        }
    return {"result": "mock", "tool": tool_name}


# Select which executor to use:
# - None: Uses the built-in registry (real tools)
# - mock_tool_executor: Uses fake results for testing
tool_executor = None if USE_REAL_TOOLS else mock_tool_executor


# =============================================================================
# TEST RUNNER
# =============================================================================
def load_test_cases() -> list[dict]:
    """Load test cases from JSON file."""
    path = Path(__file__).parent / "doc/docgemma_test_cases_v2.json"
    with open(path) as f:
        data = json.load(f)
    return data["test_cases"]


def filter_cases(cases: list[dict]) -> list[dict]:
    """Filter cases based on enabled categories."""
    return [c for c in cases if ENABLED_CATEGORIES.get(c["category"], False)]


def select_cases(cases: list[dict]) -> list[dict]:
    """Select random cases from each enabled category."""
    if RUN_SPECIFIC_TEST:
        # Find and return only the specific test
        for c in cases:
            if c["id"] == RUN_SPECIFIC_TEST:
                return [c]
        print(f"WARNING: Test '{RUN_SPECIFIC_TEST}' not found!")
        return []

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for c in cases:
        cat = c["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(c)

    # Select random samples from each
    selected = []
    for cat, cat_cases in by_category.items():
        n = min(CASES_PER_CATEGORY, len(cat_cases))
        selected.extend(random.sample(cat_cases, n))

    return selected


class TeeWriter:
    """Write to both a StringIO buffer and original stdout."""
    def __init__(self, original, buffer):
        self.original = original
        self.buffer = buffer

    def write(self, text):
        self.original.write(text)
        self.buffer.write(text)

    def flush(self):
        self.original.flush()
        self.buffer.flush()


def save_test_log(test_id: str, content: str, test_case: dict, result: dict) -> Path:
    """Save test log to file in run folder."""
    filename = f"{test_id}.txt"
    filepath = LOGS_DIR / filename

    with open(filepath, "w") as f:
        f.write(f"{'='*70}\n")
        f.write(f"TEST CASE: {test_id}\n")
        f.write(f"{'='*70}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Category: {test_case['category']}\n")
        f.write(f"Prompt: {test_case['prompt']}\n")
        f.write(f"\n")
        f.write(f"EXPECTED:\n")
        f.write(f"  Complexity: {test_case['expected_complexity']}\n")
        f.write(f"  Thinking: {test_case['expected_thinking']}\n")
        f.write(f"  Tools: {test_case['expected_tools']}\n")
        f.write(f"  Subtasks: {test_case['expected_subtasks']}\n")
        if test_case.get("requires_clarification"):
            f.write(f"  Clarification: {test_case['clarification_type']}\n")
        if test_case.get("simulate_tool_failure"):
            f.write(f"  Simulated Failure: {test_case['failure_type']}\n")
        f.write(f"\n{'='*70}\n")
        f.write(f"AGENT LOG:\n")
        f.write(f"{'='*70}\n\n")
        f.write(content)
        f.write(f"\n\n{'='*70}\n")
        f.write(f"RESULT:\n")
        f.write(f"{'='*70}\n")
        f.write(f"  Success: {result.get('success')}\n")
        f.write(f"  Time: {result.get('time', 0):.2f}s\n")
        if result.get("error"):
            f.write(f"  Error: {result['error']}\n")
        f.write(f"\nFINAL RESPONSE:\n")
        f.write(f"{result.get('response', result.get('error', 'N/A'))}\n")

    return filepath


async def run_test(agent: DocGemmaAgent, test_case: dict) -> dict:
    """Run a single test case and return results."""
    # Print header to console
    print(f"\n{'='*70}")
    print(f"TEST: {test_case['id']} ({test_case['category']})")
    print(f"{'='*70}")
    print(f"Prompt: {test_case['prompt']}")
    print(f"-" * 70)
    print(f"Expected:")
    print(f"  - Complexity: {test_case['expected_complexity']}")
    print(f"  - Thinking: {test_case['expected_thinking']}")
    print(f"  - Tools: {test_case['expected_tools']}")
    print(f"  - Subtasks: {test_case['expected_subtasks']}")
    if test_case.get("requires_clarification"):
        print(f"  - Clarification: {test_case['clarification_type']}")
    if test_case.get("simulate_tool_failure"):
        print(f"  - Simulated Failure: {test_case['failure_type']}")
    print(f"-" * 70)

    # Capture all output during agent run
    log_buffer = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = TeeWriter(original_stdout, log_buffer)

    start = time.perf_counter()
    try:
        response = await agent.run(test_case["prompt"])
        elapsed = time.perf_counter() - start
        sys.stdout = original_stdout

        print(f"\nResponse ({elapsed:.2f}s):")
        print(response)

        result = {"id": test_case["id"], "success": True, "time": elapsed, "response": response}

    except Exception as e:
        elapsed = time.perf_counter() - start
        sys.stdout = original_stdout

        print(f"\nERROR ({elapsed:.2f}s): {e}")
        import traceback
        traceback.print_exc()

        result = {"id": test_case["id"], "success": False, "time": elapsed, "error": str(e)}

    # Save log to file
    log_content = log_buffer.getvalue()
    log_path = save_test_log(test_case["id"], log_content, test_case, result)
    print(f"  Log saved: {log_path.name}")
    result["log_file"] = str(log_path)

    return result


async def main() -> None:
    """Run agent tests."""
    print("=" * 70)
    print("DocGemma Agent Test Runner (v2)")
    print("=" * 70)

    # Show enabled categories
    enabled = [k for k, v in ENABLED_CATEGORIES.items() if v]
    print(f"\nEnabled categories: {', '.join(enabled) or 'NONE'}")
    print(f"Cases per category: {CASES_PER_CATEGORY}")
    print(f"Tool executor: {'REAL APIs' if USE_REAL_TOOLS else 'MOCK'}")
    if RUN_SPECIFIC_TEST:
        print(f"Running specific test: {RUN_SPECIFIC_TEST}")

    # Load and filter test cases
    all_cases = load_test_cases()
    filtered = filter_cases(all_cases)
    selected = select_cases(filtered)

    if not selected:
        print("\nNo test cases selected! Enable some categories or check RUN_SPECIFIC_TEST.")
        return

    print(f"\nSelected {len(selected)} test cases: {[c['id'] for c in selected]}")

    # Initialize model
    print("\n[1] Connecting to remote model...")
    model = DocGemma()
    print(f"    Endpoint: {model._endpoint}")
    print(f"    Model: {model._model}")
    print(f"    Health check: {model.health_check()}")

    # Create agent
    print("\n[2] Creating agent...")
    executor_type = "REAL" if USE_REAL_TOOLS else "MOCK"
    print(f"    Tool executor: {executor_type}")
    agent = DocGemmaAgent(model, tool_executor=tool_executor)

    # Run tests
    print("\n[3] Running tests...")
    results = []
    for test_case in selected:
        result = await run_test(agent, test_case)
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    success_count = sum(1 for r in results if r["success"])
    print(f"Completed: {success_count}/{len(results)}")
    print(f"Total time: {sum(r['time'] for r in results):.2f}s")
    print(f"Logs folder: {LOGS_DIR}")
    print("\nResults:")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        log_name = Path(r.get("log_file", "")).name
        print(f"  [{status}] {r['id']} ({r['time']:.2f}s) -> {log_name}")


if __name__ == "__main__":
    asyncio.run(main())
