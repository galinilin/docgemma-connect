"""Remote DocGemma client for OpenAI-compatible vLLM endpoint."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from pydantic import BaseModel


class RemoteDocGemma:
    """Remote client matching DocGemma interface via OpenAI-compatible API.

    Works with vLLM, OpenAI, or any OpenAI-compatible endpoint.

    Usage:
        export DOCGEMMA_ENDPOINT="https://your-vllm-endpoint.com"
        export DOCGEMMA_API_KEY="your-api-key"
        export DOCGEMMA_MODEL="google/medgemma-1.5-4b-it"

        from docgemma.remote import RemoteDocGemma
        model = RemoteDocGemma()
        response = model.generate("What is hypertension?")
    """

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """Initialize remote client.

        Args:
            endpoint: Base URL for OpenAI-compatible API.
                      If None, uses DOCGEMMA_ENDPOINT env var.
            api_key: API key for authentication.
                     If None, uses DOCGEMMA_API_KEY env var.
            model: Model ID to use. If None, uses DOCGEMMA_MODEL env var.
            timeout: HTTP request timeout in seconds.
        """
        self._endpoint = endpoint or os.environ.get("DOCGEMMA_ENDPOINT")
        if not self._endpoint:
            raise ValueError(
                "No endpoint URL provided. Set DOCGEMMA_ENDPOINT environment variable "
                "or pass endpoint parameter."
            )
        self._endpoint = self._endpoint.rstrip("/")

        self._api_key = api_key or os.environ.get("DOCGEMMA_API_KEY", "")
        self._model = model or os.environ.get("DOCGEMMA_MODEL", "google/medgemma-1.5-4b-it")
        self._timeout = timeout

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.Client(timeout=timeout, headers=headers)

    @property
    def is_loaded(self) -> bool:
        """Remote model is always considered loaded (managed server-side)."""
        return True

    def health_check(self) -> bool:
        """Check if remote endpoint is reachable."""
        try:
            resp = self._client.get(f"{self._endpoint}/v1/models")
            return resp.status_code == 200
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
        temperature: float = 0.6,
        **kwargs,
    ) -> str:
        """Generate free-form response via OpenAI-compatible API.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum tokens to generate.
            do_sample: Whether to use sampling.
            temperature: Sampling temperature (used if do_sample=True).
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            Generated text response.
        """
        import json

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_new_tokens,
        }

        if do_sample:
            payload["temperature"] = temperature
        else:
            payload["temperature"] = 0.0

        resp = self._client.post(
            f"{self._endpoint}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()

        response = resp.json()["choices"][0]["message"]["content"]
        print("[*] Raw:", json.dumps({"input": messages, "response": response}, indent=2))
        print("*********************")
        return response

    def generate_outlines(
        self,
        prompt: str,
        out_type: type[BaseModel],
        max_new_tokens: int = 256,
    ) -> BaseModel:
        """Generate structured response matching Pydantic schema.

        Uses vLLM's guided decoding via response_format parameter.

        Args:
            prompt: The input prompt.
            out_type: Pydantic model class defining output schema.
            max_new_tokens: Maximum tokens to generate.

        Returns:
            Instance of out_type with generated values.
        """
        import json

        messages = [{"role": "user", "content": prompt}]
        schema = out_type.model_json_schema()

        import json as json_module

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_new_tokens,
            "temperature": 0.0,
            # vLLM guided decoding via response_format
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": out_type.__name__,
                    "schema": schema,
                    "strict": True,
                },
            },
        }

        resp = self._client.post(
            f"{self._endpoint}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()

        response_text = resp.json()["choices"][0]["message"]["content"]

        # Parse JSON response into Pydantic model
        response = out_type.model_validate_json(response_text)

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
