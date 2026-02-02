"""Test script for DocGemma Agent pipeline with remote inference."""

import asyncio
import logging
import time

from dotenv import load_dotenv

load_dotenv()

# Configure logging to see agent flow
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

from src.docgemma import RemoteDocGemma, DocGemmaAgent


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
    print("DocGemma Agent Test (Remote)")
    print("=" * 60)

    # Initialize remote model (uses env vars: DOCGEMMA_ENDPOINT, DOCGEMMA_API_KEY)
    print("\n[1] Connecting to remote model...")
    model = RemoteDocGemma()
    print(f"    Endpoint: {model._endpoint}")
    print(f"    Model: {model._model}")
    print(f"    Health check: {model.health_check()}")

    # Create agent with mock tools
    print("\n[2] Creating agent...")
    agent = DocGemmaAgent(model, tool_executor=mock_tool_executor)

    # Test cases
    # Note: Complex queries with nested schemas have truncation issues with vLLM guided decoding
    test_cases = [
        ("Hello, how are you?", "Simple greeting (should be DIRECT)"),
        ("What is hypertension?", "Simple medical question (should be DIRECT)"),
        ("What are common side effects of ibuprofen?", "Drug info (should be DIRECT)"),
        # Complex queries disabled - vLLM truncates nested JSON schemas
        # ("Check drug interactions between warfarin and aspirin", "Tool required (COMPLEX)"),
        # ("What are the FDA warnings for Lipitor?", "Drug safety lookup (COMPLEX)"),
    ]

    print("\n[3] Running tests...")
    for query, label in test_cases:
        await run_test(agent, query, label)

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
