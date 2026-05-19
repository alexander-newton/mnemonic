"""Anthropic SDK backend implementing LLMClient.

Translates Block/Message into the SDK shape, adds cache_control,
computes cost from a hardcoded price table, translates SDK exceptions
into Mnemonic's exception hierarchy.
"""

from __future__ import annotations

import math
import os
from typing import Any, Sequence

import anthropic

from mnemonic.exceptions import LLMConfigError, LLMError, LLMRateLimitError, LLMUnavailableError
from mnemonic.llm.client import Block, BatchHandle, BatchRequest, Completion, Message, Usage


# Prices in millicents per million tokens (1 cent = 1000 millicents).
# Update when Anthropic prices change.
PRICE_TABLE: dict[str, dict[str, int]] = {
    "claude-haiku-4-5":  {"input": 100,  "output": 500,  "cache_read": 10,  "cache_creation": 125},
    "claude-sonnet-4-6": {"input": 300,  "output": 1500, "cache_read": 30,  "cache_creation": 375},
    "claude-opus-4-7":   {"input": 1500, "output": 7500, "cache_read": 150, "cache_creation": 1875},
}


def _make_sdk_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def _to_sdk_blocks(blocks: list[Block]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        entry: dict[str, Any] = {"type": "text", "text": b.text}
        if b.cache_control is not None:
            entry["cache_control"] = b.cache_control
        out.append(entry)
    return out


def _compute_cost_millicents(model: str, usage: Any) -> int:
    if model not in PRICE_TABLE:
        raise LLMConfigError(
            f"Unknown model in price table: {model}. Add it to PRICE_TABLE in anthropic.py."
        )
    p = PRICE_TABLE[model]
    inp = getattr(usage, "input_tokens", 0)
    out = getattr(usage, "output_tokens", 0)
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    cc = getattr(usage, "cache_creation_input_tokens", 0) or 0
    total = (
        (inp - cr - cc) * p["input"]
        + cr * p["cache_read"]
        + cc * p["cache_creation"]
        + out * p["output"]
    ) / 1_000_000
    return max(0, math.ceil(total))


class AnthropicBackend:
    def __init__(self, *, api_key_env: str = "ANTHROPIC_API_KEY"):
        self.api_key_env = api_key_env

    def _client(self) -> anthropic.Anthropic:
        key = os.environ.get(self.api_key_env, "").strip()
        if not key:
            raise LLMConfigError(
                f"Anthropic API key missing. Set ${self.api_key_env} in your shell "
                "(e.g. in ~/.config/mnemonic/.env or your shell profile)."
            )
        return _make_sdk_client(key)

    def generate(
        self,
        *,
        system: list[Block],
        messages: list[Message],
        model: str,
        max_tokens: int,
        stop_sequences: Sequence[str] = (),
    ) -> Completion:
        client = self._client()
        sdk_messages = [
            {"role": m.role, "content": _to_sdk_blocks(m.blocks)} for m in messages
        ]
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_to_sdk_blocks(system),
                messages=sdk_messages,
                stop_sequences=list(stop_sequences),
            )
        except anthropic.AuthenticationError as e:
            raise LLMConfigError(
                f"Anthropic authentication failed. Verify ${self.api_key_env} is correct."
            ) from e
        except anthropic.RateLimitError as e:
            retry = 30
            try:
                retry = int(e.response.headers.get("retry-after", 30))
            except Exception:
                pass
            raise LLMRateLimitError(
                f"Anthropic rate limit hit. Retry in {retry}s, or reduce variation_frequency.",
                retry_after=retry,
            ) from e
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"Anthropic API returned {e.status_code} for model {model}: {getattr(e, 'message', '')}"
            ) from e
        except anthropic.APIConnectionError as e:
            raise LLMUnavailableError(f"Cannot reach Anthropic API: {e}") from e

        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        usage_obj = response.usage
        cost = _compute_cost_millicents(model, usage_obj)
        return Completion(
            text=text,
            model=model,
            usage=Usage(
                input_tokens=getattr(usage_obj, "input_tokens", 0),
                output_tokens=getattr(usage_obj, "output_tokens", 0),
                cache_read_tokens=getattr(usage_obj, "cache_read_input_tokens", 0) or 0,
                cache_creation_tokens=getattr(usage_obj, "cache_creation_input_tokens", 0) or 0,
                cost_millicents=cost,
            ),
        )

    def submit_batch(self, requests: Sequence[BatchRequest], *, model: str) -> BatchHandle:
        client = self._client()
        sdk_requests = []
        for r in requests:
            sdk_requests.append(
                {
                    "custom_id": r.custom_id,
                    "params": {
                        "model": model,
                        "max_tokens": r.max_tokens,
                        "system": _to_sdk_blocks(r.system),
                        "messages": [{"role": m.role, "content": _to_sdk_blocks(m.blocks)} for m in r.messages],
                        "stop_sequences": list(r.stop_sequences),
                    },
                }
            )
        try:
            batch = client.messages.batches.create(requests=sdk_requests)
        except anthropic.APIStatusError as e:
            raise LLMError(f"Batch submit failed: {getattr(e, 'message', '')}") from e
        return BatchHandle(batch_id=batch.id)
