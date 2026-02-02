"""Modal test script for DocGemma with caching optimizations."""

import modal

MODEL_ID = "google/medgemma-27b-it"
CACHE_DIR = "/cache/huggingface"

app = modal.App("docgemma-test")

# Persistent volume for model weights (survives across runs)
model_cache = modal.Volume.from_name("docgemma-model-cache", create_if_missing=True)

# Build image with dependencies + hf-transfer for faster downloads
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "transformers>=5.0.0",
        "accelerate>=1.12.0",
        "outlines>=1.2.9",
        "pydantic>=2.0.0",
        "huggingface-hub>=1.3.4",
        "langgraph>=0.2.0",
        "hf-transfer",  # Faster model downloads
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_HOME": CACHE_DIR,
    })
)


@app.cls(
    image=image.add_local_dir("src", remote_path="/root/src"),
    gpu="A100",
    timeout=600,
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={CACHE_DIR: model_cache},
    scaledown_window=300,  # Keep warm for 5 min after last call
)
class DocGemmaService:
    """DocGemma service with model caching."""

    @modal.enter()
    def load_model(self):
        """Load model once when container starts (cached in memory)."""
        import sys
        sys.path.insert(0, "/root")

        import torch
        from src.docgemma import DocGemma

        print("=" * 60)
        print("Loading DocGemma (cached in volume + memory)")
        print("=" * 60)
        print(f"CUDA: {torch.cuda.is_available()}")
        print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

        self.gemma = DocGemma(
            model_id=MODEL_ID,
            cache_dir=CACHE_DIR,
        )
        self.gemma.load()
        print(f"Model loaded: {self.gemma.is_loaded}")

        # Commit volume to persist downloaded weights
        model_cache.commit()

    @modal.method()
    def test(self) -> dict:
        """Run test suite."""
        from pydantic import BaseModel

        print("\n[1] Testing free-form generation...")
        prompt = "What are the symptoms of hypertension?"
        response = self.gemma.generate(prompt, max_new_tokens=128)
        print(f"    Prompt: {prompt}")
        print(f"    Response: {response[:200]}...")

        print("\n[2] Testing structured generation (Outlines)...")

        class TriageResult(BaseModel):
            severity: str
            requires_immediate_attention: bool

        structured_prompt = """Classify severity: "I have a mild headache."
Return JSON with severity (mild/moderate/severe) and requires_immediate_attention (bool)."""

        result = self.gemma.generate_outlines(structured_prompt, TriageResult, max_new_tokens=64)
        print(f"    Severity: {result.severity}")
        print(f"    Immediate attention: {result.requires_immediate_attention}")

        print("\n" + "=" * 60)
        print("Tests completed!")
        print("=" * 60)
        return {"status": "success", "severity": result.severity}


@app.local_entrypoint()
def main():
    """Run the test from local machine."""
    service = DocGemmaService()
    result = service.test.remote()
    print(f"\nResult: {result}")
