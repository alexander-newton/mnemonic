"""Build a DSPy LM pinned to OpenRouter, and harvest its usage.

The compile pipeline must never use the direct-Anthropic path. This builder
configures a native ``dspy.LM`` explicitly with the OpenRouter key and base URL,
and refuses any model string that is not OpenRouter-routable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import dspy

from mnemonic.config import OptimizationConfig
from mnemonic.exceptions import LLMConfigError

# OpenRouter returns `cost` in USD credits (1 credit = 1 USD); litellm's
# response_cost is also USD. 1 USD = 100 cents = 100_000 millicents.
_MILLICENTS_PER_USD = 100_000


@dataclass(frozen=True)
class UsageTotals:
    """Aggregated token/cost totals harvested from a DSPy LM's history."""

    input_tokens: int
    output_tokens: int
    cost_millicents: int


def build_openrouter_lm(*, model: str, config: OptimizationConfig) -> dspy.LM:
    """Return a ``dspy.LM`` pinned to OpenRouter.

    Args:
        model: The litellm model string. MUST start with ``openrouter/`` so the
            call can only route through OpenRouter (never a direct provider key).
        config: Optimization config providing the key env name and API base.

    Returns:
        A configured ``dspy.LM``.

    Raises:
        LLMConfigError: If the model is not OpenRouter-routable or the API key
            environment variable is unset/empty.
    """
    if not model.startswith("openrouter/"):
        raise LLMConfigError(
            f"Refusing to build the optimization LM: model '{model}' is not "
            "OpenRouter-routable. Set [llm] model_offline to an 'openrouter/...' "
            "string (e.g. 'openrouter/anthropic/claude-3.5-haiku') so the compile "
            "pipeline never uses a direct provider key."
        )
    key = os.environ.get(config.openrouter_key_env, "").strip()
    if not key:
        raise LLMConfigError(
            f"OpenRouter API key missing: set ${config.openrouter_key_env} in your "
            "environment (e.g. ~/.config/mnemonic/.env). The prompt-optimization "
            "compile pipeline uses OpenRouter, not a direct Anthropic key."
        )
    return dspy.LM(
        model=model,
        api_key=key,
        api_base=config.openrouter_api_base,
    )


def harvest_usage(history: list[dict]) -> UsageTotals:
    """Sum token usage and cost from a DSPy LM history list.

    OpenRouter always returns an authoritative ``cost`` (USD) inside the response
    ``usage`` object; we prefer it. litellm's computed top-level ``cost`` is used
    only as a fallback (it can be 0/None for OpenRouter models litellm lacks
    pricing for).

    Args:
        history: The ``lm.history`` list; each entry has a ``usage`` dict
            (OpenAI-style ``prompt_tokens``/``completion_tokens``, and OpenRouter's
            ``cost``) and a top-level ``cost`` (litellm's response_cost, or None).

    Returns:
        UsageTotals with summed tokens and cost converted to millicents.
    """
    input_tokens = 0
    output_tokens = 0
    cost_usd = 0.0
    for entry in history:
        usage = entry.get("usage") or {}
        input_tokens += int(usage.get("prompt_tokens", 0) or 0)
        output_tokens += int(usage.get("completion_tokens", 0) or 0)
        entry_cost = usage.get("cost")
        if entry_cost is None:
            entry_cost = entry.get("cost")
        cost_usd += float(entry_cost or 0.0)
    return UsageTotals(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_millicents=round(cost_usd * _MILLICENTS_PER_USD),
    )
