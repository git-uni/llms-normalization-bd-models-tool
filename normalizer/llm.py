import os

from google import genai

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta GOOGLE_API_KEY (o GEMINI_API_KEY) en el entorno o en .env"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate(model: str, prompt: str) -> str:
    """Llamada genérica al modelo. Devuelve el texto plano de la respuesta."""
    client = get_client()
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text or ""
