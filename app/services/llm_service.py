from __future__ import annotations

import json
from abc import ABC, abstractmethod


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


class LLMService:
    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider or StubLLMProvider()

    def set_provider(self, provider: LLMProvider):
        self._provider = provider

    async def generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        return await self._provider.generate(prompt, system_prompt)


llm_service = LLMService()
