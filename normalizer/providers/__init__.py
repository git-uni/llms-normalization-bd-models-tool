from normalizer.providers.base import (
    ChatResponse,
    LLMProvider,
    Message,
    ToolCall,
    ToolSpec,
)
from normalizer.providers.google import GoogleProvider

_REGISTRY: dict[str, type] = {
    "google": GoogleProvider,
}

DEFAULT_MODELS: dict[str, str] = {
    # gemma-3-27b-it fue retirado por Google (mayo 2026); gemma-4-31b-it es
    # su sucesor directo dentro del catálogo gratuito.
    "google": "gemma-4-31b-it",
}

# Modelos por defecto para el agente de descubrimiento (requieren tool-use).
# Distintos del pipeline porque Gemma free no soporta function-calling.
DEFAULT_AGENT_MODELS: dict[str, str] = {
    # gemini-2.5-flash-lite: function-calling y 10 RPM en free tier
    # (gemini-2.5-flash es solo 5 RPM y se agota enseguida con un agente).
    "google": "gemini-2.5-flash-lite",
}


def available_providers() -> list[str]:
    return list(_REGISTRY)


def build_provider(
    name: str, model: str | None = None, *, for_agent: bool = False
) -> LLMProvider:
    if name not in _REGISTRY:
        raise ValueError(
            f"Proveedor desconocido: '{name}'. Disponibles: {available_providers()}"
        )
    cls = _REGISTRY[name]
    defaults = DEFAULT_AGENT_MODELS if for_agent else DEFAULT_MODELS
    return cls(model=model or defaults[name])


__all__ = [
    "ChatResponse",
    "LLMProvider",
    "Message",
    "ToolCall",
    "ToolSpec",
    "available_providers",
    "build_provider",
    "DEFAULT_MODELS",
    "DEFAULT_AGENT_MODELS",
]
