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
        prompt_lower = prompt.lower()

        if "architecture" in prompt_lower or "code quality" in prompt_lower:
            return json.dumps({
                "architecture": "Well-structured code",
                "quality": "Good practices followed",
                "improvements": ["Add type hints", "Add docstrings"],
                "security_notes": ["No security issues found"],
            })

        if "requirement" in prompt_lower and "recommend" in prompt_lower:
            return json.dumps({
                "recommendation": "FastAPI with SQLAlchemy",
                "alternatives": [
                    {
                        "name": "Django",
                        "pros": ["Batteries included", "Admin panel"],
                        "cons": ["Heavier", "More opinionated"],
                        "fit_score": 8,
                    }
                ],
                "reasoning": "Best for small team REST APIs",
            })

        if "research and review" in prompt_lower or "in-depth research" in prompt_lower:
            return json.dumps({
                "best_practices": {"score": 8, "findings": ["Good naming conventions"]},
                "design_patterns": ["Single Responsibility"],
                "performance": ["No bottlenecks detected"],
                "security": ["Input validation needed"],
                "testing_recommendations": ["Add unit tests for edge cases"],
            })

        if "review these project dependencies" in prompt_lower or "dependency" in prompt_lower:
            return json.dumps({
                "issues": [
                    {"package": "requests", "severity": "medium", "message": "Version is outdated"}
                ],
                "recommendations": ["Upgrade to latest version"],
            })

        if "identify the tech stack" in prompt_lower or "tech stack" in prompt_lower:
            return json.dumps({
                "primary_language": "Python",
                "framework": "FastAPI",
                "database": "PostgreSQL",
                "tools": ["Docker", "Git"],
                "confidence": 0.95,
            })

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
        self._cost_tracker = None

    def set_provider(self, provider: LLMProvider):
        self._provider = provider

    def set_cost_tracker(self, tracker):
        self._cost_tracker = tracker

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        project_id: str | None = None,
        agent_type: str | None = None,
    ) -> str:
        result = await self._provider.generate(prompt, system_prompt)
        if self._cost_tracker is not None:
            try:
                prompt_text = f"{system_prompt or ''}\n{prompt}"
                prompt_tokens = self._cost_tracker.estimate_tokens(prompt_text)
                completion_tokens = self._cost_tracker.estimate_tokens(result)
                self._cost_tracker.record_call(
                    model=settings.opencode_model
                    if isinstance(self._provider, OpenCodeProvider)
                    else settings.ollama_model
                    if isinstance(self._provider, OllamaProvider)
                    else "stub",
                    provider=self._provider.__class__.__name__.replace("Provider", "").lower(),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    project_id=project_id,
                    agent_type=agent_type,
                    prompt=prompt_text[:500],
                    response=result[:500],
                )
            except Exception as e:
                logger.warning("Cost tracking failed: %s", e)
        return result


llm_service = LLMService()
