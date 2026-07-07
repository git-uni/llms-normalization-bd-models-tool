from normalizer.providers.base import (
    ChatResponse,
    LLMProvider,
    Message,
    ToolCall,
    ToolSpec,
)
from normalizer.providers.google import GoogleProvider
from normalizer.providers.groq import GroqProvider

_REGISTRY: dict[str, type] = {
    "google": GoogleProvider,
    "groq": GroqProvider,
}

DEFAULT_MODELS: dict[str, str] = {
    # gemma-3-27b-it fue retirado por Google (mayo 2026); gemma-4-31b-it es
    # su sucesor directo dentro del catálogo gratuito.
    "google": "gemma-4-31b-it",
    # Pipeline texto→texto, barato y capaz.
    "groq": "openai/gpt-oss-120b",
}

# Modelos por defecto para el agente de descubrimiento (requieren tool-use).
# Distintos del pipeline porque Gemma free no soporta function-calling.
DEFAULT_AGENT_MODELS: dict[str, str] = {
    # gemini-3.1-flash-lite: function-calling, 15 RPM / 500 RPD en free tier.
    # Sucesor del 2.5-flash-lite (10 RPM / 20 RPD), que se quedó corto tras
    # el recorte de cuotas de Google de diciembre 2025.
    "google": "gemini-3.1-flash-lite",
    # Único modelo de Groq en producción con tool_calls fiables; en la práctica
    # el agente se ejecuta con Google (frontera de tool-use y límites de TPM).
    "groq": "openai/gpt-oss-120b",
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
