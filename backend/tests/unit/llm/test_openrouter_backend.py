import json
from unittest.mock import MagicMock

import pytest

from mnemonic.exceptions import LLMConfigError, LLMError, LLMRateLimitError
from mnemonic.llm.backends.openrouter import OpenRouterBackend
from mnemonic.llm.client import Block, Message


def _raw(text="result", cost=3.44e-05, input_tokens=18, output_tokens=5,
         cache_read=0, cache_creation=0):
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_creation,
    }
    if cost is not None:
        usage["cost"] = cost
    payload = {
        "content": [{"type": "text", "text": text}],
        "model": "anthropic/claude-3-5-haiku",
        "usage": usage,
    }
    return MagicMock(text=json.dumps(payload))


def _backend_with(fake_client, monkeypatch, key="sk-or-x"):
    monkeypatch.setattr(
        "mnemonic.llm.backends.openrouter._make_sdk_client",
        lambda api_key, base_url: fake_client,
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", key)
    return OpenRouterBackend()


def test_generate_success_reads_inband_cost(monkeypatch):
    fake = MagicMock()
    fake.messages.with_raw_response.create.return_value = _raw(text="result", cost=3.44e-05)
    backend = _backend_with(fake, monkeypatch)
    c = backend.generate(
        system=[Block(text="sys")],
        messages=[Message(role="user", blocks=[Block(text="hi")])],
        model="anthropic/claude-3.5-haiku",
        max_tokens=200,
    )
    assert c.text == "result"
    assert c.usage.input_tokens == 18
    assert c.usage.output_tokens == 5
    assert c.usage.cost_millicents == round(3.44e-05 * 100_000)  # 3


def test_generate_missing_cost_raises(monkeypatch):
    fake = MagicMock()
    fake.messages.with_raw_response.create.return_value = _raw(cost=None)
    backend = _backend_with(fake, monkeypatch)
    with pytest.raises(LLMError, match="usage.cost"):
        backend.generate(
            system=[Block(text="s")],
            messages=[Message(role="user", blocks=[Block(text="h")])],
            model="anthropic/claude-3.5-haiku",
            max_tokens=10,
        )


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    backend = OpenRouterBackend()
    with pytest.raises(LLMConfigError):
        backend.generate(
            system=[Block(text="s")],
            messages=[Message(role="user", blocks=[Block(text="h")])],
            model="anthropic/claude-3.5-haiku",
            max_tokens=10,
        )


def test_non_openrouter_base_url_raises():
    with pytest.raises(LLMConfigError, match="openrouter.ai"):
        OpenRouterBackend(base_url="https://api.anthropic.com")


def test_cache_control_passthrough(monkeypatch):
    fake = MagicMock()
    fake.messages.with_raw_response.create.return_value = _raw()
    backend = _backend_with(fake, monkeypatch)
    backend.generate(
        system=[Block(text="sys", cache_control={"type": "ephemeral"})],
        messages=[Message(role="user", blocks=[Block(text="hi")])],
        model="anthropic/claude-3.5-haiku",
        max_tokens=10,
    )
    _, kwargs = fake.messages.with_raw_response.create.call_args
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_rate_limit_translates(monkeypatch):
    import anthropic

    fake = MagicMock()
    err = anthropic.RateLimitError(
        message="rate", response=MagicMock(headers={"retry-after": "42"}), body=None
    )
    fake.messages.with_raw_response.create.side_effect = err
    backend = _backend_with(fake, monkeypatch)
    with pytest.raises(LLMRateLimitError) as ei:
        backend.generate(
            system=[Block(text="s")],
            messages=[Message(role="user", blocks=[Block(text="h")])],
            model="anthropic/claude-3.5-haiku",
            max_tokens=10,
        )
    assert ei.value.retry_after == 42
