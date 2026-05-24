import os
import re
import time
import uuid

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from normalizer.providers.base import (
    ChatResponse,
    Message,
    ToolCall,
    ToolSpec,
)

_MAX_RETRIES = 4
_FALLBACK_RETRY_DELAY_S = 15.0


class GoogleProvider:
    name = "google"

    def __init__(self, model: str):
        self.model = model
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta GOOGLE_API_KEY (o GEMINI_API_KEY) en el entorno o en .env"
            )
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self._call_with_retry(contents=prompt, config=None)
        return response.text or ""

    def chat(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> ChatResponse:
        system_instruction, contents = _to_gemini_contents(messages)
        gemini_tools = _to_gemini_tools(tools)

        config = types.GenerateContentConfig(
            systemInstruction=system_instruction,
            tools=gemini_tools,
            automaticFunctionCalling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )

        response = self._call_with_retry(contents=contents, config=config)

        assistant_content = response.candidates[0].content
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for part in assistant_content.parts or []:
            if getattr(part, "function_call", None):
                fc = part.function_call
                tool_calls.append(
                    ToolCall(
                        id=getattr(fc, "id", None) or f"call_{uuid.uuid4().hex[:8]}",
                        name=fc.name or "",
                        arguments=dict(fc.args or {}),
                    )
                )
            elif getattr(part, "text", None):
                text_parts.append(part.text)

        text = "\n".join(text_parts) if text_parts else None
        assistant_message = Message(
            role="assistant",
            content=text,
            tool_calls=tool_calls,
            raw=assistant_content,
        )
        return ChatResponse(
            assistant_message=assistant_message,
            text=text,
            tool_calls=tool_calls,
        )


    def _call_with_retry(self, *, contents, config):
        kwargs = {"model": self.model, "contents": contents}
        if config is not None:
            kwargs["config"] = config
        for attempt in range(_MAX_RETRIES):
            try:
                return self._client.models.generate_content(**kwargs)
            except genai_errors.ClientError as exc:
                if getattr(exc, "code", None) != 429 or attempt == _MAX_RETRIES - 1:
                    raise
                delay = _parse_retry_delay(exc) or _FALLBACK_RETRY_DELAY_S
                time.sleep(delay)
        raise RuntimeError("unreachable")  # pragma: no cover


def _parse_retry_delay(exc: genai_errors.ClientError) -> float | None:
    """Extrae el retryDelay (segundos) que Google sugiere en el error 429."""
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        for item in details.get("error", {}).get("details", []) or []:
            delay = item.get("retryDelay") if isinstance(item, dict) else None
            if isinstance(delay, str):
                seconds = _parse_duration(delay)
                if seconds is not None:
                    return seconds
    match = re.search(r"retry in ([\d.]+)s", str(exc))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _parse_duration(s: str) -> float | None:
    m = re.match(r"^([\d.]+)s$", s.strip())
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _to_gemini_tools(tools: list[ToolSpec]) -> list[types.Tool]:
    declarations = [
        types.FunctionDeclaration(
            name=t.name,
            description=t.description,
            parametersJsonSchema=t.parameters,
        )
        for t in tools
    ]
    return [types.Tool(function_declarations=declarations)] if declarations else []


def _to_gemini_contents(
    messages: list[Message],
) -> tuple[str | None, list[types.Content]]:
    system_instruction: str | None = None
    contents: list[types.Content] = []

    for msg in messages:
        if msg.role == "system":
            system_instruction = msg.content
            continue

        if msg.role == "assistant" and isinstance(msg.raw, types.Content):
            contents.append(msg.raw)
            continue

        if msg.role == "assistant":
            parts: list[types.Part] = []
            if msg.content:
                parts.append(types.Part(text=msg.content))
            for tc in msg.tool_calls:
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(
                            name=tc.name, args=tc.arguments
                        )
                    )
                )
            contents.append(types.Content(role="model", parts=parts))
            continue

        if msg.role == "user":
            contents.append(
                types.Content(role="user", parts=[types.Part(text=msg.content or "")])
            )
            continue

        if msg.role == "tool":
            # En Gemini la respuesta de una tool se manda como rol "user" con un
            # Part.from_function_response. Nuestro Message.content guarda el
            # resultado serializado y `tool_call_id` el nombre de la función
            # (Gemini no usa ids de llamada, hace matching por nombre).
            tool_name = msg.tool_call_id or ""
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"result": msg.content or ""},
                        )
                    ],
                )
            )
            continue

    return system_instruction, contents
