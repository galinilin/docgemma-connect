"""DocGemma client for OpenAI-compatible vLLM endpoint."""

from __future__ import annotations

import json as _json
import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from pydantic import BaseModel


class DocGemma:
    """DocGemma client for OpenAI-compatible vLLM endpoint.

    Works with vLLM, OpenAI, or any OpenAI-compatible endpoint.

    Usage:
        export DOCGEMMA_ENDPOINT="https://your-vllm-endpoint.com"
        export DOCGEMMA_API_KEY="your-api-key"
        export DOCGEMMA_MODEL="google/medgemma-1.5-4b-it"

        from docgemma import DocGemma
        model = DocGemma()
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
        self._async_client = httpx.AsyncClient(timeout=timeout, headers=headers)

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

    def load(self) -> DocGemma:
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

    async def generate_stream(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        do_sample: bool = False,
        temperature: float = 0.6,
    ) -> AsyncGenerator[str, None]:
        """Stream free-form response token-by-token via SSE.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum tokens to generate.
            do_sample: Whether to use sampling.
            temperature: Sampling temperature (used if do_sample=True).

        Yields:
            Text chunks as they arrive.
        """
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_new_tokens,
            "stream": True,
        }

        if do_sample:
            payload["temperature"] = temperature
        else:
            payload["temperature"] = 0.0

        async with self._async_client.stream(
            "POST",
            f"{self._endpoint}/v1/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = _json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (_json.JSONDecodeError, IndexError, KeyError):
                    continue

    async def aclose(self) -> None:
        """Close the async HTTP client."""
        await self._async_client.aclose()

    def generate_outlines(
        self,
        prompt: str,
        out_type: type[BaseModel],
        max_new_tokens: int = 256,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> BaseModel:
        """Generate structured response matching Pydantic schema.

        Uses vLLM's guided decoding via response_format parameter.
        Includes retry logic for truncated/malformed JSON responses.

        Args:
            prompt: The input prompt.
            out_type: Pydantic model class defining output schema.
            max_new_tokens: Maximum tokens to generate.
            temperature: Sampling temperature. Lower = more deterministic.
                         Recommended: 0.0-0.2 for structured output.
            max_retries: Maximum retry attempts for JSON parsing failures.

        Returns:
            Instance of out_type with generated values.

        Raises:
            ValueError: If all retry attempts fail with JSON parsing errors.
        """
        import json
        import time

        messages = [{"role": "user", "content": prompt}]
        schema = out_type.model_json_schema()

        last_error = None
        last_response_text = None

        for attempt in range(max_retries):
            # Increase max_tokens on retry to handle truncation
            tokens_for_attempt = max_new_tokens + (attempt * 256)

            payload = {
                "model": self._model,
                "messages": messages,
                "max_tokens": tokens_for_attempt,
                "temperature": temperature,
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

            try:
                resp = self._client.post(
                    f"{self._endpoint}/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()

                response_text = resp.json()["choices"][0]["message"]["content"]
                last_response_text = response_text

                # Parse JSON response into Pydantic model
                response = out_type.model_validate_json(response_text)

                print("[*] Outlines:", json.dumps({"input": prompt, "response": response.model_dump()}, indent=2))
                print("*********************")
                return response

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Check if it's a JSON parsing error (truncation issue)
                is_json_error = any(
                    indicator in error_msg.lower()
                    for indicator in ["json", "eof", "parsing", "unterminated", "expecting"]
                )

                if is_json_error and attempt < max_retries - 1:
                    # Exponential backoff: 0.5s, 1s, 2s
                    backoff = 0.5 * (2 ** attempt)
                    print(f"[*] Outlines: JSON parsing failed (attempt {attempt + 1}/{max_retries}) retrying with more tokens in...")
                    continue
                elif not is_json_error:
                    # Non-JSON error, raise immediately
                    raise

        # All retries exhausted
        raise ValueError(
            f"Failed to generate valid JSON after {max_retries} attempts. "
            f"Last error: {last_error}\n"
            f"Last response (truncated): {last_response_text[:200] if last_response_text else 'None'}..."
        )

    def close(self) -> None:
        """Close HTTP clients (sync and async)."""
        self._client.close()
        # Async client should be closed via aclose() in async context,
        # but we attempt cleanup here as a fallback
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_client.aclose())
        except RuntimeError:
            pass

    def __enter__(self) -> DocGemma:
        return self

    def __exit__(self, *args) -> None:
        self.close()
