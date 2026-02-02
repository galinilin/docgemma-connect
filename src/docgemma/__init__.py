"""DocGemma - Agentic medical AI with MedGemma and Outlines."""

# Lazy imports to avoid loading torch when only using RemoteDocGemma
def __getattr__(name: str):
    if name == "DocGemma":
        from .model import DocGemma
        return DocGemma
    elif name == "DocGemmaAgent":
        from .agent import DocGemmaAgent
        return DocGemmaAgent
    elif name == "RemoteDocGemma":
        from .remote import RemoteDocGemma
        return RemoteDocGemma
    elif name == "DocGemmaProtocol":
        from .protocols import DocGemmaProtocol
        return DocGemmaProtocol
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["DocGemma", "DocGemmaAgent", "RemoteDocGemma", "DocGemmaProtocol"]
