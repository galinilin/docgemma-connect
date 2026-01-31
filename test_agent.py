"""Test script for DocGemma Agent pipeline."""

import asyncio
import time

from dotenv import load_dotenv

load_dotenv()

from src.docgemma import DocGemma, DocGemmaAgent


# Simple mock tool executor for testing without real API calls
async def mock_tool_executor(tool_name: str, args: dict) -> dict:
    """Mock tool executor that returns fake results."""
    print(f"  [TOOL] {tool_name}({args})")

    if tool_name == "check_drug_safety":
        return {
            "brand_name": args.get("brand_name", "unknown"),
            "has_warning": True,
            "boxed_warning": "Mock warning: Use with caution.",
        }
    if tool_name == "search_medical_literature":
        return {
            "query": args.get("query", ""),
            "total_found": 1,
            "articles": [{"pmid": "12345", "title": "Mock Article", "abstract": "..."}],
        }
    if tool_name == "check_drug_interactions":
        return {
            "drugs_checked": args.get("drugs", []),
            "interactions": [],
        }
    if tool_name == "find_clinical_trials":
        return {
            "condition": args.get("condition", ""),
            "total_found": 0,
            "trials": [],
        }
    return {"result": "mock", "tool": tool_name}


async def run_test(agent: DocGemmaAgent, query: str, label: str) -> None:
    """Run a single test query."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"Query: {query}")
    print("-" * 60)

    start = time.perf_counter()
    response = await agent.run(query)
    elapsed = time.perf_counter() - start

    print(f"\nResponse ({elapsed:.2f}s):")
    print(response)


async def main() -> None:
    """Run agent tests."""
    print("=" * 60)
    print("DocGemma Agent Test")
    print("=" * 60)

    # Initialize model
    print("\n[1] Loading model...")
    model = DocGemma(model_id="google/medgemma-1.5-4b-it")
    model.load()
    print(f"    Loaded on {model.device}")

    # Create agent with mock tools
    print("\n[2] Creating agent...")
    agent = DocGemmaAgent(model, tool_executor=mock_tool_executor)

    # Test cases
    test_cases = [
        ("Hello, how are you?", "Simple greeting (should be DIRECT)"),
        ("What is hypertension?", "Simple medical question (should be DIRECT)"),
        (
            "Check drug interactions between warfarin and aspirin",
            "Tool required (should be COMPLEX)",
        ),
        (
            "What are the FDA warnings for Lipitor?",
            "Drug safety lookup (should be COMPLEX)",
        ),
    ]

    print("\n[3] Running tests...")
    for query, label in test_cases:
        await run_test(agent, query, label)

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
