# LLM Backend (OpenRouter)

The runtime LLM client is `OpenRouterBackend`
(`llm/backends/openrouter.py`), an implementation of the `LLMClient` protocol.

## How it talks to the LLM

It uses the `anthropic` SDK as the wire format, pointed at OpenRouter's
Anthropic-Messages-compatible endpoint: `base_url=https://openrouter.ai/api`
(the SDK appends `/v1/messages`). This is **not** the direct-Anthropic path — an
OpenRouter key + OpenRouter base URL route all traffic through OpenRouter. The
backend refuses to construct unless `base_url` points at `openrouter.ai`.

- Key: `OPENROUTER_API_KEY` (configurable via `[llm] api_key_env`).
- Base URL: `[llm] api_base` (default `https://openrouter.ai/api`).
- Prompt caching: `cache_control` ephemeral blocks pass straight through and are
  honored by OpenRouter for Claude models.

## Cost

Cost is read **in-band** from the response's `usage.cost` (USD) — OpenRouter
includes it on every `/messages` response. (The anthropic SDK's typed `usage`
model drops the field, so the backend parses the raw JSON via
`with_raw_response`.) If a response lacks `usage.cost`, the backend raises
`LLMError` rather than recording a fabricated cost. There is no price table.

## Model slug conventions (important)

- **Runtime backend** (anthropic SDK → `/v1/messages`): bare OpenRouter slugs,
  e.g. `anthropic/claude-3.5-haiku`.
- **Phase 2 DSPy/litellm path**: `openrouter/`-prefixed, e.g.
  `openrouter/anthropic/claude-3.5-haiku`.

These differ because they use different client libraries. Set `[llm]`
`model_default`/`model_rephrase` as bare slugs and `model_offline` as the
`openrouter/`-prefixed form (it feeds the DSPy compile path).

> **Status:** This backend is foundational — it is not yet constructed by a
> runtime composition root, and `[llm] api_base` / `api_key_env` are not yet
> plumbed into it. Wiring (passing `config.llm.api_base` and
> `config.llm.api_key_env` into `OpenRouterBackend`) is a follow-up.
