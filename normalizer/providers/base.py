from typing import Protocol


class LLMProvider(Protocol):
    """Interfaz mínima de un proveedor de LLM.

    Cada implementación queda fija a un modelo concreto en su construcción.
    La pipeline solo depende de `generate(prompt) -> str`.
    """

    name: str
    model: str

    def generate(self, prompt: str) -> str: ...
