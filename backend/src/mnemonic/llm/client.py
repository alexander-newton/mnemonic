"""LLM client Protocol and shared types.

Backends implement this Protocol. Only one backend exists in Phase 1
(Anthropic). The Protocol exists so we can slot in alternatives later
without rewriting consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class Block:
    """A single content block. Optional cache_control marks a cache breakpoint."""

    text: str
    cache_control: dict[str, Any] | None = None


@dataclass(frozen=True)
class Message:
    role: str  # "user" | "assistant"
    blocks: list[Block]


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_millicents: int


@dataclass(frozen=True)
class Completion:
    text: str
    usage: Usage
    model: str


@dataclass(frozen=True)
class BatchRequest:
    custom_id: str
    system: list[Block]
    messages: list[Message]
    max_tokens: int
    stop_sequences: Sequence[str] = ()


@dataclass(frozen=True)
class BatchHandle:
    batch_id: str


class LLMClient(Protocol):
    def generate(
        self,
        *,
        system: list[Block],
        messages: list[Message],
        model: str,
        max_tokens: int,
        stop_sequences: Sequence[str] = (),
    ) -> Completion: ...

    def submit_batch(self, requests: Sequence[BatchRequest], *, model: str) -> BatchHandle: ...
