"""Remote DocGemma client for Modal inference endpoint."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from pydantic import BaseModel


class RemoteDocGemma:
    """Remote client matching DocGemma interface.

    Calls Modal inference endpoint via HTTP. Drop-in replacement for local DocGemma.

    Usage:
        # Set endpoint base (from `modal deploy modal_inference.py` output)
        export DOCGEMMA_ENDPOINT="https://gali-nil-un--docgemma-inference-inference"

        # Use same interface as local DocGemma
        from docgemma.remote import RemoteDocGemma
        model = RemoteDocGemma()
        response = model.generate("What is hypertension?")
    """

    def __init__(
        self,
        endpoint: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """Initialize remote client.

        Args:
            endpoint: Base URL for Modal endpoint (without method suffix).
                      If None, uses DOCGEMMA_ENDPOINT env var.
                      Example: "https://gali-nil-un--docgemma-inference-inference"
            timeout: HTTP request timeout in seconds.
        """
        self._endpoint = endpoint or os.environ.get("DOCGEMMA_ENDPOINT")
        if not self._endpoint:
            raise ValueError(
                "No endpoint URL provided. Set DOCGEMMA_ENDPOINT environment variable "
                "or pass endpoint parameter.\n"
                "Example: https://gali-nil-un--docgemma-inference-inference"
            )
        # Remove trailing slash and .modal.run suffix for base URL
        self._endpoint = self._endpoint.rstrip("/")
        if self._endpoint.endswith(".modal.run"):
            # User passed full URL, extract base
            self._endpoint = self._endpoint.rsplit("-", 1)[0]

        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _url(self, method: str) -> str:
        """Build full URL for a method."""
        return f"{self._endpoint}-{method}.modal.run"

    @property
    def is_loaded(self) -> bool:
        """Check if remote model is available."""
        try:
            resp = self._client.get(self._url("health"))
            return resp.status_code == 200 and resp.json().get("model_loaded", False)
        except Exception:
            return False

    def load(self) -> RemoteDocGemma:
        """No-op for API compatibility. Remote model is always loaded."""
        return self

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        do_sample: bool = False,
        **kwargs,
    ) -> str:
        """Generate free-form response via remote endpoint.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum tokens to generate.
            do_sample: Whether to use sampling.
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            Generated text response.
        """
        import json

        resp = self._client.post(
            self._url("generate"),
            json={
                "prompt": prompt,
                "max_new_tokens": max_new_tokens,
                "do_sample": do_sample,
            },
        )
        resp.raise_for_status()
        response = resp.json()["response"]
        print("[*] Raw:", json.dumps({"input": [{"role": "user", "content": prompt}], "response": response}, indent=2))
        print("*********************")
        return response

    def generate_outlines(
        self,
        prompt: str,
        out_type: type[BaseModel],
        max_new_tokens: int = 256,
    ) -> BaseModel:
        """Generate structured response matching Pydantic schema.

        Args:
            prompt: The input prompt.
            out_type: Pydantic model class defining output schema.
            max_new_tokens: Maximum tokens to generate.

        Returns:
            Instance of out_type with generated values.
        """
        import json

        # Convert Pydantic model to JSON schema
        schema = out_type.model_json_schema()

        resp = self._client.post(
            self._url("generate-structured"),
            json={
                "prompt": prompt,
                "schema": schema,
                "max_new_tokens": max_new_tokens,
            },
        )
        resp.raise_for_status()
        response_data = resp.json()["response"]
        
        # Handle both string (JSON) and dict responses
        if isinstance(response_data, str):
            response = out_type.model_validate_json(response_data)
        else:
            response = out_type.model_validate(response_data)
        
        print("[*] Outlines:", json.dumps({"input": prompt, "response": response.model_dump()}, indent=2))
        print("*********************")
        return response

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()

    def __enter__(self) -> RemoteDocGemma:
        return self

    def __exit__(self, *args) -> None:
        self.close()
