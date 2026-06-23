import json

import pytest

from app.services.llm_service import (
    LLMService,
    OllamaProvider,
    StubLLMProvider,
    create_provider,
)


@pytest.mark.asyncio
async def test_stub_provider():
    provider = StubLLMProvider()
    result = await provider.generate("test prompt")
    data = json.loads(result)
    assert "plan" in data
    assert "files" in data


@pytest.mark.asyncio
async def test_stub_provider_async():
    provider = StubLLMProvider()
    result = await provider.generate("test prompt", system_prompt="be helpful")
    data = json.loads(result)
    assert data["plan"] == "Implementation plan generated."


def test_create_provider_default():
    provider = create_provider()
    assert isinstance(provider, StubLLMProvider)


def test_llm_service_default():
    svc = LLMService()
    assert isinstance(svc._provider, StubLLMProvider)


def test_llm_service_custom():
    custom = StubLLMProvider()
    svc = LLMService(provider=custom)
    assert svc._provider is custom


@pytest.mark.asyncio
async def test_llm_service_generate():
    svc = LLMService()
    result = await svc.generate("hello")
    data = json.loads(result)
    assert "plan" in data
