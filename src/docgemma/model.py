"""DocGemma model wrapper with Outlines integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import outlines
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json

if TYPE_CHECKING:
    from pydantic import BaseModel

class DocGemma:
    """MedGemma model wrapper with lazy loading and Outlines-based structured generation."""

    def __init__(
        self,
        model_id: str = "google/medgemma-1.5-4b-it",
        device: str | None = None,
        dtype: torch.dtype | None = None,
        device_map: str = "auto",
        cache_dir: str | None = None,
    ) -> None:
        """Initialize DocGemma configuration without loading the model.

        Args:
            model_id: HuggingFace model identifier.
            device: Target device ('cuda', 'cpu'). Auto-detected if None.
            dtype: Model dtype (torch.bfloat16, torch.float32). Auto-detected if None.
            device_map: Device map strategy for model loading.
            cache_dir: Directory to cache model weights. Use Google Drive path
                in Colab to persist across sessions (e.g., '/content/drive/MyDrive/hf_cache').
        """
        self.model_id = model_id
        self._device = device
        self._dtype = dtype
        self._device_map = device_map
        self._cache_dir = cache_dir

        # Lazy-loaded attributes
        self._model: AutoModelForCausalLM | None = None
        self._tokenizer: AutoTokenizer | None = None
        self._outlines_model = None

    @property
    def is_loaded(self) -> bool:
        """Check if the model has been loaded."""
        return self._model is not None

    @property
    def device(self) -> str:
        """Get the device (auto-detected if not specified)."""
        if self._device is not None:
            return self._device
        return "cuda" if torch.cuda.is_available() else "cpu"

    @property
    def dtype(self) -> torch.dtype:
        """Get the dtype (auto-detected if not specified)."""
        if self._dtype is not None:
            return self._dtype
        return torch.bfloat16 if torch.cuda.is_available() else torch.float32

    def _ensure_loaded(self) -> None:
        """Raise an error if the model is not loaded."""
        if not self.is_loaded:
            raise RuntimeError(
                "Model not loaded. Call load() before using generation methods."
            )

    def load(self, _model=None, _tokenizer=None) -> DocGemma:
        """Load the model, tokenizer, and initialize Outlines generators.

        Returns:
            Self for method chaining.
        """
        if self.is_loaded:
            return self

        # Load tokenizer & model or use provided ones
        if _model is not None and _tokenizer is not None:
            self._tokenizer = _tokenizer
            self._model = _model
        else:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                cache_dir=self._cache_dir,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
                device_map=self._device_map,
                cache_dir=self._cache_dir,
            )

        # Wrap with Outlines
        self._outlines_model = outlines.from_transformers(
            self._model, self._tokenizer
        )
        
        return self

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        do_sample: bool = False,
        temperature: float = 0.6,
        top_p: float = 1.0,
        top_k: int = 50,
    ) -> str:
        """Generate a response using the raw model with chat template.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum number of tokens to generate.
            do_sample: Whether to use sampling (vs greedy decoding).
            temperature: Sampling temperature (higher = more random).
            top_p: Nucleus sampling probability threshold.
            top_k: Top-k sampling parameter.

        Returns:
            Generated text response.
        """
        self._ensure_loaded()

        messages = [{"role": "user", "content": prompt}]

        input_ids = self._tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
        )
        # Handle both tensor and BatchEncoding returns
        if hasattr(input_ids, "input_ids"):
            input_ids = input_ids.input_ids
        input_ids = input_ids.to(self._model.device)
        input_length = input_ids.shape[1]

        with torch.inference_mode():
            outputs = self._model.generate(
                input_ids=input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
                top_p=top_p if do_sample else None,
                top_k=top_k if do_sample else None,
                pad_token_id=self._tokenizer.eos_token_id
            )

        # Decode only new tokens
        response = self._tokenizer.decode(
            outputs[0][input_length:],
            skip_special_tokens=True,
        )
        print("[*] Raw:", json.dumps({"input": messages, "response": response}, indent=2))
        print("*********************")
        return response.strip()

    def generate_outlines(
        self,
        prompt: str,
        out_type: type[BaseModel],
        max_new_tokens: int = 256,
    ) -> BaseModel:
        """Generate constrained with respect to given type.

        Args:
            prompt: The input prompt.
            out_type: Pydantic model class defining the output schema.
            max_new_tokens: Maximum number of tokens to generate.
        Returns:
            Instance of the schema class with generated values.
        """
        self._ensure_loaded()
        raw_response = self._outlines_model(
            prompt,
            out_type,
            max_new_tokens=max_new_tokens,
            pad_token_id=self._tokenizer.eos_token_id
        )
        try:
            import json
            response = out_type.model_validate_json(raw_response)
            print("[*] Outlines:", json.dumps({"input": prompt, "response": response.model_dump()}, indent=2))
            print("*********************")
            return response
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse Outlines response into {out_type}: {e}\nRaw response: {raw_response}"
            )
