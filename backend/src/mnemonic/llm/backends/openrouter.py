"""OpenRouter backend implementing LLMClient via the Anthropic SDK.

Talks to OpenRouter's Anthropic-Messages-compatible endpoint
(base_url=https://openrouter.ai/api; the SDK appends /v1/messages). This is NOT
the direct-Anthropic path: an OpenRouter key + OpenRouter base URL route all
traffic through OpenRouter. Cost is read in-band from the response's
``usage.cost`` (USD); the SDK's typed usage drops that field, so we parse the raw
JSON.
"""

from __future__ import annotations

import json
import os
from typing import Any, Sequence

import anthropic

from mnemonic.exceptions import (
    LLMConfigError,
    LLMError,
    LLMRateLimitError,
    LLMUnavailableError,
)
from mnemonic.llm.client import Block, Completion, Message, Usage

DEFAULT_BASE_URL = "https://openrouter.ai/api"
_MILLICENTS_PER_USD = 100_000


def _make_sdk_client(api_key: str, base_url: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key, base_url=base_url)


def _to_sdk_blocks(blocks: list[Block]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        entry: dict[str, Any] = {"type": "text", "text": b.text}
        if b.cache_control is not None:
            entry["cache_control"] = b.cache_control
        out.append(entry)
    return out


class OpenRouterBackend:
    """LLMClient backed by OpenRouter via the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key_env: str = "OPENROUTER_API_KEY",
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Initialize the backend.

        Args:
            api_key_env: Environment variable holding the OpenRouter API key.
            base_url: OpenRouter base URL (the SDK appends ``/v1/messages``).

        Raises:
            LLMConfigError: If base_url does not point at openrouter.ai.
        """
        if "openrouter.ai" not in base_url:
            raise LLMConfigError(
                f"OpenRouterBackend refuses base_url '{base_url}': it must point at "
                "openrouter.ai. This guards against silently using a direct-provider "
                "endpoint/key."
            )
        self.api_key_env = api_key_env
        self.base_url = base_url

    def _client(self) -> anthropic.Anthropic:
        key = os.environ.get(self.api_key_env, "").strip()
        if not key:
            raise LLMConfigError(
                f"OpenRouter API key missing. Set ${self.api_key_env} in your shell "
                "(e.g. in ~/.config/mnemonic/.env or your shell profile)."
            )
        return _make_sdk_client(key, self.base_url)

    def generate(
        self,
        *,
        system: list[Block],
        messages: list[Message],
        model: str,
        max_tokens: int,
        stop_sequences: Sequence[str] = (),
    ) -> Completion:
        """Generate a completion via OpenRouter.

        Args:
            system: System blocks (may carry cache_control).
            messages: Conversation messages.
            model: OpenRouter model slug, e.g. ``anthropic/claude-3.5-haiku``.
            max_tokens: Max output tokens.
            stop_sequences: Optional stop sequences.

        Returns:
            A Completion with text, model, token usage, and in-band cost.

        Raises:
            LLMConfigError: Missing key / auth failure.
            LLMRateLimitError: Rate limited.
            LLMUnavailableError: Transport failure.
            LLMError: API status error, or response missing ``usage.cost``.
        """
        client = self._client()
        sdk_messages = [
            {"role": m.role, "content": _to_sdk_blocks(m.blocks)} for m in messages
        ]
        try:
            raw = client.messages.with_raw_response.create(
                model=model,
                max_tokens=max_tokens,
                system=_to_sdk_blocks(system),
                messages=sdk_messages,
                stop_sequences=list(stop_sequences),
            )
        except anthropic.AuthenticationError as e:
            raise LLMConfigError(
                f"OpenRouter authentication failed. Verify ${self.api_key_env} is correct."
            ) from e
        except anthropic.RateLimitError as e:
            retry = 30
            try:
                retry = int(e.response.headers.get("retry-after", 30))
            except Exception:
                pass
            raise LLMRateLimitError(
                f"OpenRouter rate limit hit. Retry in {retry}s, or reduce variation_frequency.",
                retry_after=retry,
            ) from e
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"OpenRouter API returned {e.status_code} for model {model}: "
                f"{getattr(e, 'message', '')}"
            ) from e
        except anthropic.APIConnectionError as e:
            raise LLMUnavailableError(f"Cannot reach OpenRouter API: {e}") from e

        data = json.loads(raw.text)
        text = "".join(
            part.get("text", "")
            for part in data.get("content", [])
            if part.get("type") == "text"
        )
        usage = data.get("usage") or {}
        cost_usd = usage.get("cost")
        if cost_usd is None:
            raise LLMError(
                f"OpenRouter response for model {model} did not include usage.cost; "
                "cannot record exact cost. Check the model slug and your OpenRouter account."
            )
        return Completion(
            text=text,
            model=data.get("model", model),
            usage=Usage(
                input_tokens=int(usage.get("input_tokens", 0) or 0),
                output_tokens=int(usage.get("output_tokens", 0) or 0),
                cache_read_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
                cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
                cost_millicents=round(float(cost_usd) * _MILLICENTS_PER_USD),
            ),
        )
