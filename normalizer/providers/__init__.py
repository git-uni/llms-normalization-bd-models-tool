from normalizer.providers.base import LLMProvider
from normalizer.providers.google import GoogleProvider

_REGISTRY: dict[str, type] = {
    "google": GoogleProvider,
}

DEFAULT_MODELS: dict[str, str] = {
    "google": "gemma-3-27b-it",
}


def available_providers() -> list[str]:
    return list(_REGISTRY)


def build_provider(name: str, model: str | None = None) -> LLMProvider:
    if name not in _REGISTRY:
        raise ValueError(
            f"Proveedor desconocido: '{name}'. Disponibles: {available_providers()}"
        )
    cls = _REGISTRY[name]
    return cls(model=model or DEFAULT_MODELS[name])


__all__ = ["LLMProvider", "available_providers", "build_provider"]
