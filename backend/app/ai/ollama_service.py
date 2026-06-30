import httpx
from ..core.config import settings

class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.0, top_p: float = 0.1, num_predict: int = 128) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": 16384,
                "num_predict": num_predict
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=180.0)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

ollama_service = OllamaService()
