from mnemonic.llm.client import Block, Message, Completion, Usage, LLMClient
from typing import Protocol


def test_block_with_cache_control():
    b = Block(text="hello", cache_control={"type": "ephemeral"})
    assert b.text == "hello"
    assert b.cache_control == {"type": "ephemeral"}


def test_block_without_cache_control():
    b = Block(text="hi")
    assert b.cache_control is None


def test_completion_carries_usage():
    c = Completion(text="ok", model="m", usage=Usage(input_tokens=10, output_tokens=5,
                                          cache_read_tokens=0, cache_creation_tokens=0,
                                          cost_millicents=15))
    assert c.text == "ok"
    assert c.usage.cost_millicents == 15


def test_llm_client_is_protocol():
    # LLMClient is a Protocol; should have the typing.Protocol marker
    assert getattr(LLMClient, "_is_protocol", False) is True or issubclass(LLMClient, Protocol)
