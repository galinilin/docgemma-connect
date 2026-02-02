"""Protocol definitions for DocGemma interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pydantic import BaseModel


@runtime_checkable
class DocGemmaProtocol(Protocol):
    """Protocol defining the interface for DocGemma-compatible models.

    Both local DocGemma and RemoteDocGemma implement this interface,
    allowing them to be used interchangeably with DocGemmaAgent.
    """

    @property
    def is_loaded(self) -> bool:
        """Check if the model is ready for inference."""
        ...

    def load(self) -> DocGemmaProtocol:
        """Load/initialize the model. Returns self for chaining."""
        ...

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        **kwargs,
    ) -> str:
        """Generate free-form text response.

        Args:
            prompt: The input prompt.
            max_new_tokens: Maximum tokens to generate.
            **kwargs: Additional generation parameters.

        Returns:
            Generated text response.
        """
        ...

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
        ...
