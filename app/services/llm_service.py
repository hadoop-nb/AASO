from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        pass


class StubLLMProvider(LLMProvider):
    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        return json.dumps({
            "plan": "Implementation plan generated.",
            "files": [
                {
                    "path": "src/main.py",
                    "summary": "Main entry point",
                    "content": 'def main():\n    print("Hello from AASO")\n\nif __name__ == "__main__":\n    main()',
                    "language": "python",
                }
            ],
            "decision": {
                "question": "Architecture approach",
                "alternatives": ["Modular monolith", "Microservices"],
                "selected": "Modular monolith",
                "reason": "Simpler deployment, better for team size",
            },
            "lesson": {
                "problem": "Initial architecture complexity",
                "solution": "Started with modular monolith",
                "result": "Fast iteration, easy to refactor later",
            },
        })


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
    ):
        self.base_url = base_url
        self.model = model

    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]
            except Exception as e:
                logger.error("Ollama request failed: %s", e)
                raise


class OpenCodeProvider(LLMProvider):
    def __init__(
        self,
        base_url: str = settings.opencode_base_url,
        model: str = settings.opencode_model,
        api_key: str = settings.opencode_api_key,
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key

    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error("OpenCode request failed: %s", e)
                raise


def create_provider() -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    if provider_name == "ollama":
        logger.info("Using Ollama provider: %s with model %s", settings.ollama_base_url, settings.ollama_model)
        return OllamaProvider()
    if provider_name == "opencode":
        logger.info("Using OpenCode provider: %s with model %s", settings.opencode_base_url, settings.opencode_model)
        return OpenCodeProvider()
    logger.info("Using Stub provider")
    return StubLLMProvider()


class LLMService:
    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider or create_provider()

    def set_provider(self, provider: LLMProvider):
        self._provider = provider

    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        return await self._provider.generate(prompt, system_prompt)


llm_service = LLMService()
