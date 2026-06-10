# OpenRouter Runtime Backend (repoint from direct-Anthropic)

**Status:** Design approved, pending spec review
**Date:** 2026-06-09
**Author:** Alexander (with Claude)

## Problem

Mnemonic's runtime LLM client (`llm/backends/anthropic.py`, `AnthropicBackend`)
talks to Anthropic **directly** via the Anthropic SDK and an `ANTHROPIC_API_KEY`.
The project's intent (CLAUDE.md, `.env.example`) is to use **OpenRouter**, and the
owner wants to avoid direct-Anthropic keys. Phase 2 of the prompt-optimization
work already established OpenRouter as the LLM provider for the offline DSPy path.
This change moves the **runtime** variation path onto OpenRouter too.

The backend is currently **dormant** — `AnthropicBackend` is never instantiated in
`src/`, and its only consumer is `VariationGenerator` (via the `LLMClient`
protocol). `submit_batch`/`BatchRequest`/`BatchHandle` exist but have no callers.

## Decision summary

Repoint the existing backend at OpenRouter's **Anthropic-Messages-compatible
endpoint** using the `anthropic` SDK with an OpenRouter base URL + key. This keeps
the entire `Block`/`Message`/`cache_control` design and prompt caching intact;
only the destination, credentials, model slugs, and cost source change. Cost is
read **in-band** from OpenRouter's `usage.cost` (no second request). The unused
batch API is removed.

This was validated against the live OpenRouter API (see "Live verification").

## Key insight & safety

Using the `anthropic` SDK with `base_url=https://openrouter.ai/api` + an OpenRouter
key sends **all traffic to OpenRouter** — the SDK is just the wire format. This is
**not** the direct-Anthropic path. The backend refuses to construct unless pointed
at an `openrouter.ai` base URL (loud `LLMConfigError`), so it cannot silently
regress to direct-Anthropic.

**Model-string convention split (documented to avoid confusion):**
- Runtime path (this backend, anthropic SDK → `/v1/messages`): **bare** OpenRouter
  slugs, e.g. `anthropic/claude-3.5-haiku`.
- Phase 2 DSPy/litellm path: **`openrouter/`-prefixed**, e.g.
  `openrouter/anthropic/claude-3.5-haiku`.

## Live verification (2026-06-09)

A real Haiku call through the anthropic SDK to OpenRouter confirmed:
- Correct base URL is `https://openrouter.ai/api` (SDK appends `/v1/messages`;
  `…/api/v1` double-paths to a 404).
- The `/messages` response includes cost in-band:
  `usage.cost` (USD, e.g. `3.44e-05`) plus `usage.cost_details`.
- The anthropic SDK's **typed** `usage` model drops the non-standard `cost` field,
  so cost must be read from the **raw JSON** (`json.loads(raw.text)`).
- Token usage fields present: `input_tokens`, `output_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`.
- `cache_control` blocks accepted without error; response `id` is `gen-…`.

## Scope

**In scope:** rewrite `backends/anthropic.py` → `backends/openrouter.py`
(`OpenRouterBackend`); update `LLMConfig`; remove the batch API from the
`LLMClient` protocol and backend; tests.

**Out of scope / unchanged:** `cache.py` (ephemeral cache blocks pass straight
through), `VariationGenerator`, the `Block`/`Message`/`Completion`/`Usage` types,
the exception hierarchy.

## Components

### 1. `OpenRouterBackend` (`llm/backends/openrouter.py`)

Replaces `AnthropicBackend`. Still uses the `anthropic` SDK.

**Construction:**
```python
OpenRouterBackend(
    api_key_env: str = "OPENROUTER_API_KEY",
    base_url: str = "https://openrouter.ai/api",
)
```
- Reads the key from `$api_key_env`; empty/missing → `LLMConfigError` (names the
  env var, says it's the OpenRouter key).
- Refuses to build unless `"openrouter.ai"` is in `base_url` → `LLMConfigError`
  (guard against silent direct-Anthropic regression).
- Builds `anthropic.Anthropic(api_key=key, base_url=base_url)`.

**`generate(*, system, messages, model, max_tokens, stop_sequences=()) -> Completion`:**
1. Translate `Block`s to SDK content dicts (`_to_sdk_blocks`, unchanged — carries
   `cache_control` through).
2. Call `client.messages.with_raw_response.create(model=..., max_tokens=...,
   system=..., messages=..., stop_sequences=...)`.
3. `raw_data = json.loads(raw.text)`.
4. Text = concatenation of `raw_data["content"][*]["text"]` for text blocks.
5. Token usage from `raw_data["usage"]`:
   `input_tokens`, `output_tokens`,
   `cache_read_tokens = cache_read_input_tokens` (or 0),
   `cache_creation_tokens = cache_creation_input_tokens` (or 0).
6. Cost: `cost_usd = raw_data["usage"].get("cost")`; if `None`/absent →
   `LLMError` (exact-or-fail; never fabricate). Else
   `cost_millicents = round(cost_usd * 100_000)`.
7. Return `Completion(text, model, Usage(...))`.

**Exception mapping** (anthropic SDK exceptions, messages reworded to OpenRouter):
- `anthropic.AuthenticationError` → `LLMConfigError`
- `anthropic.RateLimitError` → `LLMRateLimitError(retry_after=…)` (parse
  `retry-after` header, default 30)
- `anthropic.APIStatusError` → `LLMError`
- `anthropic.APIConnectionError` → `LLMUnavailableError`

Deletes the hardcoded `PRICE_TABLE` and `_compute_cost_millicents` (cost is now
authoritative from OpenRouter).

### 2. `LLMConfig` (`config.py`)

- `api_key_env` default → `"OPENROUTER_API_KEY"`.
- Add `api_base: str` (default `"https://openrouter.ai/api"`).
- `model_default` / `model_rephrase` / `model_offline` documented as OpenRouter
  slugs. (Note the `openrouter/`-prefix split for the Phase 2 litellm path — see
  above. `model_offline` is consumed by the Phase 2 DSPy path, which needs the
  prefix; the runtime models do not.)

### 3. `LLMClient` protocol (`client.py`)

- Remove `submit_batch` from the protocol.
- Remove `BatchRequest` and `BatchHandle` dataclasses (unused).
- Protocol shrinks to `generate(...)` only.

## Data flow

`VariationGenerator.generate()` → `OpenRouterBackend.generate()` →
`anthropic` SDK → `https://openrouter.ai/api/v1/messages` → raw JSON parsed for
text + token usage + in-band `usage.cost` → `Completion`.

## Error handling (NO SILENT FAILURES)

- Missing OpenRouter key → `LLMConfigError`.
- Non-OpenRouter `base_url` → `LLMConfigError`.
- Missing in-band cost → `LLMError` (never record a fabricated 0).
- SDK transport/status errors → mapped exceptions above (loud, OpenRouter-worded).

## Testing

The backend has external I/O; tests mock the anthropic SDK (existing test pattern).

- **`generate()` happy path:** mock `with_raw_response.create` to return a canned
  raw response (text content + `usage` with tokens + `cost`); assert `Completion`
  text, token counts, and `cost_millicents` (e.g. `cost=3.44e-05` → `3`).
- **Cost-missing:** raw `usage` without `cost` → asserts `LLMError`.
- **Construction guards:** missing `OPENROUTER_API_KEY` → `LLMConfigError`;
  `base_url` without `openrouter.ai` → `LLMConfigError`.
- **`cache_control` passthrough:** assert ephemeral blocks reach the SDK call
  unchanged (inspect the mocked call kwargs).
- **Exception mapping:** SDK `AuthenticationError`/`RateLimitError`/
  `APIConnectionError`/`APIStatusError` → the right Mnemonic exceptions.
- **Config:** `api_key_env` default is `OPENROUTER_API_KEY`; `api_base` default
  loads; overrides apply.
- **Protocol:** assert `BatchRequest`/`BatchHandle`/`submit_batch` are gone (import
  failure / attribute absence), and that `OpenRouterBackend` satisfies the slim
  `LLMClient` protocol.

One item requires a live key to fully exercise (the real `usage.cost` path); it is
covered above by a mocked canned response shaped exactly like the verified live
response.

## Out of scope (YAGNI)

- The OpenAI-style `/chat/completions` path (not needed; the Anthropic endpoint
  carries in-band cost).
- A separate `GET /generation` cost lookup (cost is in-band).
- Re-introducing a price table.
- Removing the `anthropic` dependency (still used as the wire SDK).
