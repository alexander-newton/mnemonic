# OpenRouter Runtime Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dormant direct-Anthropic `AnthropicBackend` with an `OpenRouterBackend` that talks to OpenRouter's Anthropic-Messages endpoint via the `anthropic` SDK, reading exact cost in-band from `usage.cost`.

**Architecture:** Keep the `anthropic` SDK and the existing `Block`/`Message`/`cache_control` design; point `base_url` at `https://openrouter.ai/api` (the SDK appends `/v1/messages`) with an OpenRouter key. Read the response via `with_raw_response` and parse the raw JSON for text, token usage, and OpenRouter's in-band `usage.cost` (the SDK's typed usage drops it). Drop the hardcoded price table and the unused batch API.

**Tech Stack:** Python 3.11, `anthropic` SDK (as the wire format, pointed at OpenRouter), pytest (mock the SDK), uv.

Spec: `docs/superpowers/specs/2026-06-09-openrouter-backend-design.md`. Design was **live-verified** against the real OpenRouter API on 2026-06-09 (base URL, in-band `usage.cost`, raw-JSON access).

---

## Design facts locked from live verification

- Correct base URL is `https://openrouter.ai/api` — the anthropic SDK appends `/v1/messages`. (`…/api/v1` double-paths to a 404.)
- The `/messages` response carries cost in-band at `usage.cost` (USD float), plus token fields `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`.
- The anthropic SDK's **typed** `usage` drops the non-standard `cost`, so we read the **raw JSON** via `client.messages.with_raw_response.create(...)` then `json.loads(raw.text)`.
- `with_raw_response.create` still raises the usual `anthropic` status exceptions on errors.

---

## File Structure

**Create:**
- `backend/src/mnemonic/llm/backends/openrouter.py` — `OpenRouterBackend` (+ `_make_sdk_client`, `_to_sdk_blocks`, `DEFAULT_BASE_URL`).
- `backend/tests/unit/llm/test_openrouter_backend.py` — backend tests (mock SDK).
- `docs/source/developer/llm-backend.md` — short dev note incl. the model-slug convention split.

**Modify:**
- `backend/src/mnemonic/llm/client.py` — remove `BatchRequest`, `BatchHandle`, and `submit_batch` from the protocol.
- `backend/src/mnemonic/config.py` — add `api_base` to `LLMConfig`; load it.
- `backend/tests/unit/llm/test_client_types.py` — assert batch types are gone.
- `backend/tests/unit/test_config.py` — assert `api_base` default + override.

**Delete:**
- `backend/src/mnemonic/llm/backends/anthropic.py`
- `backend/tests/unit/llm/test_anthropic_backend.py`

All commands assume working directory `backend/`.

---

### Task 1: `OpenRouterBackend` (replace the direct-Anthropic backend)

**Files:**
- Create: `src/mnemonic/llm/backends/openrouter.py`
- Create: `tests/unit/llm/test_openrouter_backend.py`
- Delete: `src/mnemonic/llm/backends/anthropic.py`, `tests/unit/llm/test_anthropic_backend.py`

`AnthropicBackend` is never instantiated in `src/` and only its own test imports it, so replacing it is safe. Follow TDD.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/llm/test_openrouter_backend.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/llm/test_openrouter_backend.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.llm.backends.openrouter'`.

- [ ] **Step 3: Create the backend**

Create `src/mnemonic/llm/backends/openrouter.py` with EXACTLY this content:

```python
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
```

- [ ] **Step 4: Delete the old backend and its test**

Run:
```bash
git rm src/mnemonic/llm/backends/anthropic.py tests/unit/llm/test_anthropic_backend.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/llm/test_openrouter_backend.py -v`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/llm/backends/openrouter.py tests/unit/llm/test_openrouter_backend.py
git commit -m "feat(llm): OpenRouter backend via Anthropic SDK with in-band exact cost"
```

---

### Task 2: Slim the `LLMClient` protocol (remove the unused batch API)

**Files:**
- Modify: `src/mnemonic/llm/client.py`
- Test: `tests/unit/llm/test_client_types.py` (append)

`BatchRequest`/`BatchHandle`/`submit_batch` are unused (only the now-deleted backend referenced them) and OpenRouter has no Anthropic-batch endpoint.

- [ ] **Step 1: Append the failing test**

Append to `tests/unit/llm/test_client_types.py`:

```python
def test_batch_types_removed():
    import mnemonic.llm.client as c

    assert not hasattr(c, "BatchRequest")
    assert not hasattr(c, "BatchHandle")
    assert not hasattr(c.LLMClient, "submit_batch")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/llm/test_client_types.py::test_batch_types_removed -v`
Expected: FAIL (the attributes still exist).

- [ ] **Step 3: Remove the batch surface**

In `src/mnemonic/llm/client.py`:
- Delete the `BatchRequest` dataclass.
- Delete the `BatchHandle` dataclass.
- Delete the `submit_batch(...)` method line from the `LLMClient` Protocol.

The `LLMClient` Protocol must end up containing only the `generate(...)` method. Keep the `Block`, `Message`, `Usage`, `Completion` dataclasses and the `from typing import Any, Protocol, Sequence` import unchanged (`Sequence` is still used by `generate`'s `stop_sequences` parameter; `Any` by `Block.cache_control`).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/llm/test_client_types.py -v`
Expected: PASS (all, including the new test).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/llm/client.py tests/unit/llm/test_client_types.py
git commit -m "refactor(llm): drop unused batch API from LLMClient protocol"
```

---

### Task 3: Add `api_base` to `LLMConfig`

**Files:**
- Modify: `src/mnemonic/config.py`
- Test: `tests/unit/test_config.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `tests/unit/test_config.py`:

```python
def test_llm_api_base_defaults_to_openrouter(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[vault]\npath = "/tmp/v"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "OPENROUTER_API_KEY"\nmodel_default = "anthropic/claude-sonnet-4"\n'
        'model_rephrase = "anthropic/claude-3.5-haiku"\nmodel_offline = "openrouter/anthropic/claude-3.5-haiku"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    cfg = load_config(user_global_path=cfg_path)
    assert cfg.llm.api_base == "https://openrouter.ai/api"


def test_llm_api_base_override(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[vault]\npath = "/tmp/v"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "OPENROUTER_API_KEY"\nmodel_default = "anthropic/claude-sonnet-4"\n'
        'model_rephrase = "anthropic/claude-3.5-haiku"\nmodel_offline = "openrouter/anthropic/claude-3.5-haiku"\n'
        'api_base = "https://openrouter.ai/api"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    cfg = load_config(user_global_path=cfg_path)
    assert cfg.llm.api_base == "https://openrouter.ai/api"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_config.py::test_llm_api_base_defaults_to_openrouter -v`
Expected: FAIL with `AttributeError: 'LLMConfig' object has no attribute 'api_base'`.

- [ ] **Step 3: Implement**

In `src/mnemonic/config.py`:

(a) Add `api_base` as the last field of the `LLMConfig` dataclass (it has a default, so it must come after the non-default `budget` field):

```python
@dataclass(frozen=True)
class LLMConfig:
    api_key_env: str
    model_default: str
    model_rephrase: str
    model_offline: str
    budget: BudgetConfig
    api_base: str = "https://openrouter.ai/api"
```

(b) In `load_config`, in the `llm=LLMConfig(...)` construction, add `api_base` after the `budget=BudgetConfig(...)` argument:

```python
            api_base=llm_section.get("api_base", "https://openrouter.ai/api"),
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS (all, including the two new tests, and the pre-existing config tests).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/config.py tests/unit/test_config.py
git commit -m "feat(config): add llm.api_base (default OpenRouter)"
```

---

### Task 4: Developer doc + full verification

**Files:**
- Create: `docs/source/developer/llm-backend.md` (at the repo/worktree root, NOT under backend/)

- [ ] **Step 1: Write the dev doc**

Create `docs/source/developer/llm-backend.md`:

```markdown
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
```

- [ ] **Step 2: Full verification (from `backend/`)**

Run each; fix only files changed in this plan:
1. `uv run ruff check src/mnemonic/llm src/mnemonic/config.py tests/unit/llm tests/unit/test_config.py`
2. `uv run black --check src/mnemonic/llm src/mnemonic/config.py tests/unit/llm tests/unit/test_config.py` (run `black` to fix if needed, only on changed files)
3. `uv run mypy src/mnemonic/llm/backends/openrouter.py src/mnemonic/llm/client.py src/mnemonic/config.py` (fix type errors in these files; report pre-existing errors elsewhere without fixing)
4. `uv run pytest -q 2>&1 | tail -8`

For the test run: the only acceptable failures are the 3 known pre-existing ones (`test_redis_import`, `test_jose_import`, `test_passlib_import` in `tests/test_setup.py`). Everything else must pass. Confirm `test_anthropic_backend.py` is gone (no collection errors referencing it). Report the summary line.

- [ ] **Step 3: Commit**

```bash
git add docs/source/developer/llm-backend.md
# include any changed source files touched for lint/format/mypy
git commit -m "docs(llm): OpenRouter backend developer guide"
```

---

## Self-Review (completed during planning)

**Spec coverage:**
- Rename/replace backend → OpenRouter via anthropic SDK + base_url guard → Task 1.
- In-band exact cost from `usage.cost`; cost-missing → `LLMError`; drop PRICE_TABLE → Task 1.
- Token usage (input/output/cache_read/cache_creation) from raw usage → Task 1.
- cache_control passthrough preserved → Task 1 (test asserts it).
- Exception mapping (auth/ratelimit/status/connection) → Task 1.
- Missing key / non-OpenRouter base_url guards → Task 1.
- Remove batch API from protocol → Task 2.
- `LLMConfig.api_base` + `OPENROUTER_API_KEY` default (backend default in Task 1; config field in Task 3) → Tasks 1, 3.
- Model-slug convention split documented → Task 4.
- NO SILENT FAILURES (loud on missing key/base_url/cost) → Tasks 1.

**Placeholder scan:** none — every code step has complete code; every run step has an exact command + expected output.

**Type/name consistency:** `OpenRouterBackend(api_key_env=, base_url=)`, `_make_sdk_client(api_key, base_url)` (monkeypatched with the same 2-arg signature in tests), `DEFAULT_BASE_URL`, `_MILLICENTS_PER_USD`, `usage.cost` → `cost_millicents = round(cost_usd * 100_000)`. `Completion`/`Usage`/`Block`/`Message` fields match `client.py`. The exception-catch order (AuthenticationError, RateLimitError before APIStatusError) is correct since the first two subclass APIStatusError.

**Out of scope (per spec):** OpenAI-style endpoint, separate generation-cost call, price table, removing the `anthropic` dependency.
```
