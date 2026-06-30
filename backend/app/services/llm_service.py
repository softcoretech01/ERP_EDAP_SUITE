import httpx
import logging
import time
import traceback
from typing import List, Dict, Any, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.default_model = settings.OLLAMA_MODEL
        self._available_models: Optional[List[str]] = None
        self.max_retries = 3
        # Increased timeout to 300 seconds to handle large context windows (like full Excel files)
        self.timeout = 300.0
        # Primary and fallback model chain (most preferred first)
        self.model_chain = [
            self.default_model,
            "llama3.1:8b",
            "qwen2.5-coder:3b",
            "qwen2.5:3b",
            "qwen2.5:7b",
            "qwen3:8b",
            "llama3.2",
        ]

    async def _check_ollama_health(self) -> bool:
        """Quick health check to verify Ollama is reachable before generating."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False

    async def get_available_models(self) -> List[str]:
        if self._available_models is not None:
            return self._available_models
        
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    self._available_models = models
                    logger.info(f"LLMService: Available Ollama models: {self._available_models}")
                    return models
        except Exception as e:
            logger.warning(f"LLMService: Could not fetch Ollama models tags: {e}")
            
        return []

    async def select_model(self, preferred_model: str) -> str:
        # Resolve best available model from the chain.
        available = await self.get_available_models()
        
        # If preferred model is available, use it directly!
        if preferred_model in available:
            return preferred_model
            
        for model in self.model_chain:
            if model in available:
                return model
        # Fallback to default if none in chain are present.
        logger.info(f"LLMService: No preferred models found, falling back to default {self.default_model}")
        return self.default_model

    async def generate(self, prompt: str, system: str = "", model: str = None, temperature: float = 0.1, top_p: float = 0.1, num_predict: int = 300) -> str:
        # Resolve which model name to call using the chain.
        target_model = await self.select_model(model or self.default_model)
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": 4096,
                "num_predict": num_predict
            }
        }
        logger.info(f"LLM REQUEST | Model: {target_model} | Prompt length: {len(prompt)} chars | num_predict: {num_predict}")
        
        last_exception = None
        
        # Build the actual fallback list starting with the target model
        models_to_try = [target_model] + [m for m in self.model_chain if m != target_model]
        
        # Try each model in the chain sequentially until a successful response is obtained.
        for model_to_try in models_to_try:
            if model_to_try not in (await self.get_available_models()):
                continue
            payload["model"] = model_to_try
            for attempt in range(1, self.max_retries + 1):
                try:
                    start_time = time.time()
                    async with httpx.AsyncClient() as client:
                        response = await client.post(url, json=payload, timeout=self.timeout)
                        response.raise_for_status()
                        data = response.json()
                        # Log raw response for debugging before extracting.
                        logger.debug(f"LLM RAW RESPONSE (model={model_to_try}): {data}")
                        result = data.get("response", "").strip()
                    elapsed = time.time() - start_time
                    logger.info(
                        f"LLM RESPONSE | Model: {model_to_try} | Response length: {len(result)} chars | Time: {elapsed:.2f}s | Attempt: {attempt}/{self.max_retries}"
                    )
                    return result
                except httpx.TimeoutException as e:
                    elapsed = time.time() - start_time
                    last_exception = e
                    logger.warning(
                        f"LLM TIMEOUT | Model: {model_to_try} | Attempt {attempt}/{self.max_retries} | Elapsed: {elapsed:.2f}s | Error: {e}"
                    )
                except httpx.HTTPStatusError as e:
                    elapsed = time.time() - start_time
                    last_exception = e
                    logger.error(
                        f"LLM HTTP ERROR | Model: {model_to_try} | Status: {e.response.status_code} | Attempt {attempt}/{self.max_retries} | Body: {e.response.text[:500]}"
                    )
                except Exception as e:
                    elapsed = time.time() - start_time
                    last_exception = e
                    logger.error(
                        f"LLM UNEXPECTED ERROR | Model: {model_to_try} | Attempt {attempt}/{self.max_retries} | Error: {e}\n{traceback.format_exc()}"
                    )
                # Brief pause before retry
                if attempt < self.max_retries:
                    import asyncio
                    await asyncio.sleep(1.0 * attempt)
            # After exhausting retries for this model, move to next in chain.
            logger.info(f"LLM FAILED | All retries exhausted for model {model_to_try}, trying next fallback model.")
        # All models in chain failed.
        logger.error(f"LLM ALL MODELS FAILED | Exhausted all fallbacks after attempts. Raising last exception.")
        raise last_exception if last_exception else Exception("LLM generation failed for all models")

llm_service = LLMService()
