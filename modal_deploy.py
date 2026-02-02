"""Modal inference endpoint for DocGemma with memory snapshots."""

import modal

MODEL_ID = "google/medgemma-1.5-4b-it"
CACHE_DIR = "/cache/huggingface"

app = modal.App("docgemma-inference")

# Persistent volume for model weights
model_cache = modal.Volume.from_name("docgemma-model-cache", create_if_missing=True)

# Build image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "transformers>=5.0.0",
        "accelerate>=1.12.0",
        "outlines>=1.2.9",
        "pydantic>=2.0.0",
        "huggingface-hub>=1.3.4",
        "hf-transfer",
        "fastapi[standard]",
        "langgraph>=0.2.0",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_HOME": CACHE_DIR,
    })
)


@app.cls(
    image=image.add_local_dir("src", remote_path="/root/src"),
    gpu="T4",
    timeout=300,
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={CACHE_DIR: model_cache},
    scaledown_window=300,
    enable_memory_snapshot=True,
)
class Inference:
    """Inference service with memory snapshot caching."""

    @modal.enter(snap=True)
    def load_model(self):
        """Load model once, snapshot VRAM state."""
        import sys
        sys.path.insert(0, "/root")

        from src.docgemma import DocGemma

        print("Loading DocGemma for snapshot...")
        self.gemma = DocGemma(model_id=MODEL_ID, cache_dir=CACHE_DIR)
        self.gemma.load()
        print(f"Model loaded: {self.gemma.is_loaded}")

        # Persist weights to volume
        model_cache.commit()

    @modal.fastapi_endpoint(method="POST")
    def generate(self, request: dict) -> dict:
        """Generate free-form response.

        Request body:
            prompt: str
            max_new_tokens: int (default 256)
            do_sample: bool (default False)
        """
        prompt = request.get("prompt", "")
        max_new_tokens = request.get("max_new_tokens", 256)
        do_sample = request.get("do_sample", False)

        response = self.gemma.generate(
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
        )
        return {"response": response}

    @modal.fastapi_endpoint(method="POST")
    def generate_structured(self, request: dict) -> dict:
        """Generate structured response matching a Pydantic schema.

        Request body:
            prompt: str
            schema: dict (JSON schema)
            max_new_tokens: int (default 256)
        """
        from pydantic import create_model

        prompt = request.get("prompt", "")
        schema = request.get("schema", {})
        max_new_tokens = request.get("max_new_tokens", 256)

        # Build Pydantic model from schema
        fields = {}
        for field_name, field_info in schema.get("properties", {}).items():
            field_type = _json_type_to_python(field_info.get("type", "string"))
            required = field_name in schema.get("required", [])
            fields[field_name] = (field_type, ... if required else None)

        DynamicModel = create_model("DynamicModel", **fields)

        result = self.gemma.generate_outlines(
            prompt=prompt,
            out_type=DynamicModel,
            max_new_tokens=max_new_tokens,
        )
        return {"response": result.model_dump()}

    @modal.fastapi_endpoint(method="GET")
    def health(self) -> dict:
        """Health check endpoint."""
        return {"status": "ok", "model_loaded": self.gemma.is_loaded}


def _json_type_to_python(json_type: str) -> type:
    """Convert JSON schema type to Python type."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
    }
    return mapping.get(json_type, str)
