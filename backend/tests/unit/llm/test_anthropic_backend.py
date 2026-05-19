import os
from unittest.mock import MagicMock, patch
import pytest
from mnemonic.llm.backends.anthropic import AnthropicBackend, PRICE_TABLE
from mnemonic.llm.client import Block, Message
from mnemonic.exceptions import LLMConfigError, LLMRateLimitError, LLMError


def _mock_message(input_tokens=100, output_tokens=50, cache_read=10, cache_creation=5):
    m = MagicMock()
    m.content = [MagicMock(text="result")]
    m.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_creation,
    )
    return m


def test_generate_success(monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_message()
    monkeypatch.setattr("mnemonic.llm.backends.anthropic._make_sdk_client", lambda key: fake_client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    backend = AnthropicBackend(api_key_env="ANTHROPIC_API_KEY")
    completion = backend.generate(
        system=[Block(text="sys")],
        messages=[Message(role="user", blocks=[Block(text="hi")])],
        model="claude-haiku-4-5",
        max_tokens=200,
    )
    assert completion.text == "result"
    assert completion.usage.input_tokens == 100
    assert completion.usage.cost_millicents > 0


def test_generate_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    backend = AnthropicBackend(api_key_env="ANTHROPIC_API_KEY")
    with pytest.raises(LLMConfigError):
        backend.generate(
            system=[Block(text="s")],
            messages=[Message(role="user", blocks=[Block(text="h")])],
            model="claude-haiku-4-5",
            max_tokens=10,
        )


def test_generate_rate_limit_translates(monkeypatch):
    import anthropic
    fake_client = MagicMock()
    err = anthropic.RateLimitError(message="rate", response=MagicMock(headers={"retry-after": "42"}), body=None)
    fake_client.messages.create.side_effect = err
    monkeypatch.setattr("mnemonic.llm.backends.anthropic._make_sdk_client", lambda key: fake_client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    backend = AnthropicBackend(api_key_env="ANTHROPIC_API_KEY")
    with pytest.raises(LLMRateLimitError) as ei:
        backend.generate(system=[Block(text="s")],
                         messages=[Message(role="user", blocks=[Block(text="h")])],
                         model="claude-haiku-4-5", max_tokens=10)
    assert ei.value.retry_after == 42


def test_price_table_has_required_models():
    for m in ("claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-7"):
        assert m in PRICE_TABLE
