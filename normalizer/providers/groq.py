import json
import os
import re
import time
import uuid

from groq import Groq, RateLimitError

from normalizer._log import log
from normalizer.providers.base import (
    ChatResponse,
    Message,
    ToolCall,
    ToolSpec,
)

_MAX_RETRIES = 4
_FALLBACK_RETRY_DELAY_S = 5.0


class GroqProvider:
    name = "groq"

    def __init__(self, model: str):
        self.model = model
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Falta GROQ_API_KEY en el entorno o en .env")
        # max_retries=0 desactiva el retry interno del SDK para que el nuestro
        # (que respeta el retry-after) sea quien manda.
        self._client = Groq(api_key=api_key, max_retries=0)

    def generate(self, prompt: str) -> str:
        response = self._call_with_retry(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            op="generate",
        )
        return response.choices[0].message.content or ""

    def chat(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> ChatResponse:
        groq_messages = _to_groq_messages(messages)
        groq_tools = _to_groq_tools(tools)

        response = self._call_with_retry(
            messages=groq_messages, tools=groq_tools, op="chat"
        )

        msg = response.choices[0].message
        text = msg.content
        tool_calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.id or f"call_{uuid.uuid4().hex[:8]}",
                    name=tc.function.name or "",
                    arguments=args,
                )
            )

        assistant_message = Message(
            role="assistant",
            content=text,
            tool_calls=tool_calls,
            raw=msg,
        )
        return ChatResponse(
            assistant_message=assistant_message,
            text=text,
            tool_calls=tool_calls,
        )

    def _call_with_retry(self, *, messages, tools, op: str):
        kwargs = {"model": self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        for attempt in range(_MAX_RETRIES):
            try:
                return self._client.chat.completions.create(**kwargs)
            except RateLimitError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise
                delay = _parse_retry_delay(exc) or _FALLBACK_RETRY_DELAY_S
                log(
                    f"  429 en groq.{op} — esperando {delay:.0f}s "
                    f"(intento {attempt + 1}/{_MAX_RETRIES})"
                )
                time.sleep(delay)
        raise RuntimeError("unreachable")  # pragma: no cover


def _parse_retry_delay(exc: RateLimitError) -> float | None:
    """Extrae el retry-after que Groq sugiere en sus errores 429."""
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers:
        for key in ("retry-after", "x-ratelimit-reset"):
            value = headers.get(key)
            if value:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
    match = re.search(r"try again in ([\d.]+)s", str(exc), re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _to_groq_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def _to_groq_messages(messages: list[Message]) -> list[dict]:
    """Traduce nuestro historial al formato OpenAI-compatible de Groq."""
    result: list[dict] = []
    for msg in messages:
        if msg.role == "system":
            result.append({"role": "system", "content": msg.content or ""})
            continue

        if msg.role == "user":
            result.append({"role": "user", "content": msg.content or ""})
            continue

        if msg.role == "assistant":
            entry: dict = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            result.append(entry)
            continue

        if msg.role == "tool":
            # Groq/OpenAI emparejan por tool_call_id (no por nombre, como
            # hace Gemini). tool_name aquí se ignora.
            result.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.content or "",
                }
            )
            continue

    return result
