"""Test script for DocGemma."""

from pydantic import BaseModel

from src.docgemma import DocGemma

from dotenv import load_dotenv
load_dotenv()


class TriageResult(BaseModel):
    """Structured triage classification output."""

    severity: str
    requires_immediate_attention: bool
    reasoning: str


def main() -> None:
    """Test DocGemma model loading and generation."""
    print("=" * 60)
    print("DocGemma Test Script")
    print("=" * 60)

    # Initialize (lazy - no loading yet)
    print("\n[1] Initializing DocGemma (lazy)...")
    gemma = DocGemma(model_id="google/medgemma-1.5-4b-it")
    print(f"    Model ID: {gemma.model_id}")
    print(f"    Device: {gemma.device}")
    print(f"    Dtype: {gemma.dtype}")
    print(f"    Is loaded: {gemma.is_loaded}")

    # Load model
    print("\n[2] Loading model...")
    gemma.load()
    print(f"    Is loaded: {gemma.is_loaded}")
    
    # Test structured generation with Pydantic
    print("\n[3] Testing structured generation (Pydantic)...")
    triage_prompt = """Analyze this patient query and provide triage information.

Query: "I've had a persistent excruciating headache for 5 days and some nausea, I have passed out once. What should I do?"

Provide severity (mild/moderate/severe), whether it requires immediate attention, and brief reasoning."""

    try:
        result = gemma.generate_outlines(triage_prompt, TriageResult, max_new_tokens=1024)
        result = TriageResult.model_validate_json(result)
        print(f"    Severity: {result.severity}")
        print(f"    Immediate attention: {result.requires_immediate_attention}")
        print(f"    Reasoning: {result.reasoning}")
    except Exception as e:
        print(f"    Error: {e}")

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
