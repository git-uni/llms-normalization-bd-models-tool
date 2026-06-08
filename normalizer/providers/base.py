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

    `role` adopta la vocabulary de OpenAI (`system`/`user`/`assistant`/
    `tool`) como representación interna común; cada provider la traduce a
    su formato nativo:

    - `role="system"`: instrucción de sistema (p. ej. `DISCOVERY_SYSTEM`).
      Groq la envía como un mensaje normal con `role="system"`; Google la
      saca del historial y la pasa fuera de banda como `system_instruction`
      en la `GenerateContentConfig`.
    - `role="user"`: turno del usuario / orquestador (en el agente, el
      primer mensaje con URL + árbol del repo).
    - `role="assistant"`: turno del modelo. Puede traer `content` de texto,
      `tool_calls`, o ambos. Groq lo envía tal cual; Google lo emite como
      `role="model"` en su API — la traducción la hace `_to_gemini_contents`.
    - `role="tool"`: resultado de ejecutar una tool, reinyectado para que el
      modelo lo vea en el siguiente turno. Groq tiene rol `tool` nativo y
      empareja con la llamada por `tool_call_id`. Gemini no tiene rol
      `tool`: el provider envuelve el resultado en un `role="user"` con un
      `Part.from_function_response`, y empareja por nombre de función
      (`tool_name`). Por eso conviene rellenar ambos campos al construir
      el mensaje — uno u otro se ignora según el provider destino.

    `raw` guarda el objeto original del SDK del proveedor para reinyectarlo
    en turnos siguientes sin reconstruirlo. Hoy solo lo usa Google con los
    mensajes `assistant`: preserva metadatos opacos del `Content` devuelto
    (p. ej. firmas/`thought_signature`) que se perderían al recomponerlo a
    partir de `content` + `tool_calls`.
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
    - `list_models(for_agent)`: catálogo dinámico de modelos disponibles. La
      GUI lo consulta para poblar los combos de selección sin tener que
      mantener listas hardcoded. `for_agent=True` restringe a los modelos
      verificados con function-calling para el agente de descubrimiento.
    """

    name: str
    model: str

    def generate(self, prompt: str) -> str: ...

    def chat(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> ChatResponse: ...

    def list_models(self, for_agent: bool = False) -> list[str]: ...
