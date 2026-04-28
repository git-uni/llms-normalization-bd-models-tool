import os

from google import genai


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
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text or ""
