"""DocGemma client for OpenAI-compatible vLLM endpoint."""

from __future__ import annotations

import json as _json
import os
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING

import re

import httpx

if TYPE_CHECKING:
    from pydantic import BaseModel

# MedGemma wraps internal thinking in <unused94>...<unused95> tokens.
# Strip these from all free-form output so they never reach the user.
_THINKING_RE = re.compile(r"<unused94>.*?<unused95>", re.DOTALL)
_THINKING_OPEN = "<unused94>"
_THINKING_CLOSE = "<unused95>"
# The model often prefixes thinking content with "thought\n"; strip it.
_THINKING_PREFIX_RE = re.compile(r"^thought\s*", re.IGNORECASE)
# Max words to keep from a runaway thinking block before truncating and
# forcing the model to continue with actual output via assistant prefill.
_THINKING_MAX_WORDS = 256


class DocGemma:
    """DocGemma client for OpenAI-compatible vLLM endpoint.

    Works with vLLM, OpenAI, or any OpenAI-compatible endpoint.

    Usage:
        export DOCGEMMA_ENDPOINT="https://your-vllm-endpoint.com"
        export DOCGEMMA_API_KEY="your-api-key"
        export DOCGEMMA_MODEL="google/medgemma-27b-it"

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
        system_prompt: str | Callable[[], str] | None = None,
    ) -> None:
        """Initialize remote client.

        Args:
            endpoint: Base URL for OpenAI-compatible API.
                      If None, uses DOCGEMMA_ENDPOINT env var.
            api_key: API key for authentication.
                     If None, uses DOCGEMMA_API_KEY env var.
            model: Model ID to use. If None, uses DOCGEMMA_MODEL env var.
            timeout: HTTP request timeout in seconds.
            system_prompt: Optional system prompt prepended to every API call.
                           Can be a string or a callable that returns a string
                           (called per request for dynamic content like timestamps).
        """
        self._endpoint = endpoint or os.environ.get("DOCGEMMA_ENDPOINT")
        if not self._endpoint:
            raise ValueError(
                "No endpoint URL provided. Set DOCGEMMA_ENDPOINT environment variable "
                "or pass endpoint parameter."
            )
        self._endpoint = self._endpoint.rstrip("/")

        self._api_key = api_key or os.environ.get("DOCGEMMA_API_KEY", "")
        self._model = model or os.environ.get("DOCGEMMA_MODEL", "google/medgemma-27b-it")
        self._timeout = timeout
        self._system_prompt = system_prompt

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.Client(timeout=timeout, headers=headers)
        self._async_client = httpx.AsyncClient(timeout=timeout, headers=headers)

        # Captured thinking text from the most recent generate/generate_stream call.
        # Read by the synthesize node to include in the clinical trace.
        self.last_thinking_text: str | None = None

    def _build_messages(self, messages: list[dict]) -> list[dict]:
        """Prepend system prompt (if set) and merge consecutive same-role messages."""
        msgs = list(messages)
        if self._system_prompt:
            prompt = self._system_prompt() if callable(self._system_prompt) else self._system_prompt
            msgs = [{"role": "system", "content": prompt}] + msgs

        # Merge consecutive messages with the same role (vLLM rejects them)
        merged: list[dict] = []
        for msg in msgs:
            if merged and merged[-1]["role"] == msg["role"]:
                prev = merged[-1]["content"]
                curr = msg["content"]
                # Both strings — join with newline
                if isinstance(prev, str) and isinstance(curr, str):
                    merged[-1] = {**merged[-1], "content": prev + "\n" + curr}
                else:
                    # Multimodal content (list of parts) — concatenate lists
                    prev_parts = prev if isinstance(prev, list) else [{"type": "text", "text": prev}]
                    curr_parts = curr if isinstance(curr, list) else [{"type": "text", "text": curr}]
                    merged[-1] = {**merged[-1], "content": prev_parts + curr_parts}
            else:
                merged.append(msg)
        return merged

    @staticmethod
    def _clean_thinking(text: str) -> str | None:
        """Strip the ``thought\\n`` prefix and whitespace from thinking text."""
        text = _THINKING_PREFIX_RE.sub("", text.strip()).strip()
        return text or None

    @staticmethod
    def _extract_thinking(raw_response: str) -> str | None:
        """Extract the raw thinking content from a response (without tags)."""
        start = raw_response.find(_THINKING_OPEN)
        if start == -1:
            return None
        after_open = raw_response[start + len(_THINKING_OPEN):]
        end = after_open.find(_THINKING_CLOSE)
        if end != -1:
            return DocGemma._clean_thinking(after_open[:end])
        # Unclosed — return everything after the open tag
        return DocGemma._clean_thinking(after_open)

    @staticmethod
    def _truncate_thinking(raw_response: str) -> str:
        """Extract thinking content from a raw response and truncate it.

        Returns a closed thinking block: ``<unused94>...truncated...<unused95>``.
        """
        start = raw_response.find(_THINKING_OPEN)
        if start == -1:
            return ""
        thinking = raw_response[start + len(_THINKING_OPEN):]
        # Strip any accidental close tag (e.g. closed but empty after)
        thinking = thinking.replace(_THINKING_CLOSE, "")
        words = thinking.split()
        if len(words) > _THINKING_MAX_WORDS:
            words = words[:_THINKING_MAX_WORDS]
        return f"{_THINKING_OPEN}{' '.join(words)}{_THINKING_CLOSE}"

    def _continue_after_thinking(
        self,
        raw_response: str,
        all_messages: list[dict],
        max_new_tokens: int,
        temperature: float,
    ) -> str:
        """Make a continuation call after a runaway thinking block (sync).

        Truncates the thinking, closes it with <unused95>, then uses vLLM's
        ``continue_final_message`` to let the model produce the real answer.
        """
        import json

        prefix = self._truncate_thinking(raw_response)
        if not prefix:
            return raw_response

        continuation_messages = all_messages + [
            {"role": "assistant", "content": prefix},
        ]

        payload = {
            "model": self._model,
            "messages": continuation_messages,
            "max_tokens": max_new_tokens,
            "temperature": temperature,
            "continue_final_message": True,
            "add_generation_prompt": False,
        }

        print("[*] Continuation: thinking ran away, retrying with assistant prefill")
        resp = self._client.post(
            f"{self._endpoint}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()

        response = resp.json()["choices"][0]["message"]["content"]
        print("[*] Continuation result:", json.dumps({"response": response}, indent=2))
        print("*********************")
        return response

    async def _continue_after_thinking_stream(
        self,
        thinking_buffer: list[str],
        all_messages: list[dict],
        max_new_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Make a streaming continuation call after a runaway thinking block.

        Yields text chunks from the continuation response.
        """
        # Build truncated thinking prefix
        thinking_text = "".join(thinking_buffer)
        words = thinking_text.split()
        if len(words) > _THINKING_MAX_WORDS:
            thinking_text = " ".join(words[:_THINKING_MAX_WORDS])
        prefix = f"{_THINKING_OPEN}{thinking_text}{_THINKING_CLOSE}"

        continuation_messages = all_messages + [
            {"role": "assistant", "content": prefix},
        ]

        payload = {
            "model": self._model,
            "messages": continuation_messages,
            "max_tokens": max_new_tokens,
            "stream": True,
            "temperature": temperature,
            "continue_final_message": True,
            "add_generation_prompt": False,
        }

        print("[*] Continuation (stream): thinking ran away, retrying with assistant prefill")

        in_thinking = False
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
                    if not content:
                        continue

                    # Safety net: filter thinking in continuation too
                    while content:
                        if not in_thinking:
                            idx = content.find(_THINKING_OPEN)
                            if idx == -1:
                                yield content
                                break
                            if idx > 0:
                                yield content[:idx]
                            in_thinking = True
                            content = content[idx + len(_THINKING_OPEN):]
                        else:
                            idx = content.find(_THINKING_CLOSE)
                            if idx == -1:
                                break
                            in_thinking = False
                            content = content[idx + len(_THINKING_CLOSE):]

                except (_json.JSONDecodeError, IndexError, KeyError):
                    continue

    def health_check(self) -> bool:
        """Check if remote endpoint is reachable."""
        try:
            resp = self._client.get(f"{self._endpoint}/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        do_sample: bool = False,
        temperature: float = 0.6,
        image_base64: str | None = None,
        messages: list[dict] | None = None,
        **kwargs,
    ) -> str:
        """Generate free-form response via OpenAI-compatible API.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum tokens to generate.
            do_sample: Whether to use sampling.
            temperature: Sampling temperature (used if do_sample=True).
            image_base64: Optional base64-encoded image for vision queries.
            messages: Optional prior conversation turns to prepend.
            **kwargs: Additional arguments (ignored for compatibility).

        Returns:
            Generated text response.
        """
        import json

        if image_base64:
            current_msg = {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": prompt},
            ]}
        else:
            current_msg = {"role": "user", "content": prompt}

        all_messages = self._build_messages(list(messages or []) + [current_msg])

        payload = {
            "model": self._model,
            "messages": all_messages,
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
        print("[*] Raw:", json.dumps({"input": all_messages, "response": response}, indent=2))
        print("*********************")

        # Capture thinking text for clinical trace before stripping
        self.last_thinking_text = self._extract_thinking(response)

        # Detect runaway thinking: opened but never closed, or closed but
        # nothing useful after it (model spent all tokens on thinking).
        needs_continuation = False
        if _THINKING_OPEN in response and _THINKING_CLOSE not in response:
            needs_continuation = True
        elif _THINKING_OPEN in response and _THINKING_RE.sub("", response).strip() == "":
            needs_continuation = True

        if needs_continuation:
            response = self._continue_after_thinking(
                response, all_messages, max_new_tokens, payload["temperature"],
            )

        return _THINKING_RE.sub("", response).strip()

    async def generate_stream(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        do_sample: bool = False,
        temperature: float = 0.6,
        image_base64: str | None = None,
        messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream free-form response token-by-token via SSE.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum tokens to generate.
            do_sample: Whether to use sampling.
            temperature: Sampling temperature (used if do_sample=True).
            image_base64: Optional base64-encoded image for vision queries.
            messages: Optional prior conversation turns to prepend.

        Yields:
            Text chunks as they arrive.
        """
        if image_base64:
            current_msg = {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": prompt},
            ]}
        else:
            current_msg = {"role": "user", "content": prompt}

        all_messages = self._build_messages(list(messages or []) + [current_msg])

        payload = {
            "model": self._model,
            "messages": all_messages,
            "max_tokens": max_new_tokens,
            "stream": True,
        }

        if do_sample:
            payload["temperature"] = temperature
        else:
            payload["temperature"] = 0.0

        in_thinking = False
        full_response_parts: list[str] = []
        thinking_buffer: list[str] = []
        thinking_word_count = 0
        continuation_needed = False

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
                    if not content:
                        continue

                    # Filter out <unused94>...<unused95> thinking blocks
                    while content:
                        if not in_thinking:
                            idx = content.find(_THINKING_OPEN)
                            if idx == -1:
                                full_response_parts.append(content)
                                yield content
                                break
                            if idx > 0:
                                full_response_parts.append(content[:idx])
                                yield content[:idx]
                            in_thinking = True
                            content = content[idx + len(_THINKING_OPEN):]
                        else:
                            idx = content.find(_THINKING_CLOSE)
                            if idx == -1:
                                # Still inside thinking — buffer and count
                                thinking_buffer.append(content)
                                thinking_word_count += len(content.split())
                                if thinking_word_count > _THINKING_MAX_WORDS:
                                    continuation_needed = True
                                break
                            # Capture content before close tag
                            if idx > 0:
                                thinking_buffer.append(content[:idx])
                            in_thinking = False
                            content = content[idx + len(_THINKING_CLOSE):]

                except (_json.JSONDecodeError, IndexError, KeyError):
                    continue

                if continuation_needed:
                    break  # Exit the line-reading loop too

        # If stream ended while still in thinking, or nothing was yielded
        if in_thinking and not continuation_needed:
            continuation_needed = True

        if continuation_needed and not full_response_parts:
            # No real content was yielded yet — safe to do continuation
            temp = payload.get("temperature", 0.0)
            async for chunk in self._continue_after_thinking_stream(
                thinking_buffer, all_messages, max_new_tokens, temp,
            ):
                full_response_parts.append(chunk)
                yield chunk

        # Capture thinking text for clinical trace
        if thinking_buffer:
            self.last_thinking_text = self._clean_thinking("".join(thinking_buffer))
        else:
            self.last_thinking_text = None

        full_response = "".join(full_response_parts)
        print("[*] Stream:", _json.dumps({"input": all_messages, "response": full_response}, indent=2))
        print("*********************")

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
        messages: list[dict] | None = None,
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
            messages: Optional prior conversation turns to prepend.

        Returns:
            Instance of out_type with generated values.

        Raises:
            ValueError: If all retry attempts fail with JSON parsing errors.
        """
        import json
        import time

        all_messages = self._build_messages(
            list(messages or []) + [{"role": "user", "content": prompt}]
        )
        schema = out_type.model_json_schema()

        last_error = None
        last_response_text = None

        for attempt in range(max_retries):
            # Increase max_tokens on retry to handle truncation
            tokens_for_attempt = max_new_tokens + (attempt * 256)

            payload = {
                "model": self._model,
                "messages": all_messages,
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
