from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolSpec:
    """Declaración de una herramienta disponible para el agente.

    `parameters` sigue el formato JSON Schema (subset compatible con los SDK
    de los principales proveedores).
    """

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    """Invocación de una tool decidida por el modelo en un turno."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """Mensaje del historial de chat.

    - `role="tool"` requiere `tool_call_id` (id de la llamada respondida; lo
      usan OpenAI/Groq/Anthropic) y `tool_name` (nombre de la función; lo usa
      Gemini, que empareja por nombre en lugar de por id). Conviene rellenar
      ambos para que el mensaje funcione contra cualquier proveedor.
    - `role="assistant"` puede traer `tool_calls` además (o en lugar) de texto.
    - `raw` guarda el objeto original del SDK del proveedor para que el
      provider pueda reinyectarlo en turnos siguientes sin reconstruirlo.
    """

    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    tool_name: str | None = None
    raw: Any = None


@dataclass
class ChatResponse:
    """Respuesta de un turno de chat con tools."""

    assistant_message: Message
    text: str | None
    tool_calls: list[ToolCall]


class LLMProvider(Protocol):
    """Interfaz de un proveedor de LLM.

    - `generate(prompt)`: turno único texto-a-texto. Lo usa el pipeline lineal.
    - `chat(messages, tools)`: un turno de chat con tool-use opcional. Lo usa
      el agente de descubrimiento. Implementar solo si el proveedor/modelo
      soporta function-calling.
    """

    name: str
    model: str

    def generate(self, prompt: str) -> str: ...

    def chat(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> ChatResponse: ...
