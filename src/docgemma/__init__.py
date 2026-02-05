"""DocGemma - Agentic medical AI with MedGemma and Outlines."""

# Lazy imports
def __getattr__(name: str):
    if name == "DocGemmaAgent":
        from .agent import DocGemmaAgent
        return DocGemmaAgent
    elif name == "DocGemma":
        from .model import DocGemma
        return DocGemma
    elif name == "create_app":
        from .api import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["DocGemmaAgent", "DocGemma", "create_app"]
