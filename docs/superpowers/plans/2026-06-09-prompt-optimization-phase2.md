# Prompt Optimization — Phase 2 (DSPy Compile Pipeline) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline `mnemonic-optimize <strategy>` command that uses DSPy to compile a *challenger* prompt version for a strategy from the historical, reward-labeled `TrainingExample`s produced in Phase 1, talking to the LLM **only through OpenRouter**.

**Architecture:** A small adapter builds a native `dspy.LM` pinned to OpenRouter (never the direct-Anthropic path). Per-strategy `dspy.Signature`s are seeded from the current champion's instruction text. A trainset builder turns finalized `TrainingExample`s into `dspy.Example`s carrying their reward. `BootstrapFewShot` selects high-reward historical variations as few-shot demos, gated by a validity-checked, reward-weighted metric. The compiled program is written back as a new `challenger` `prompt_version` (instruction + demos + provenance); LLM cost is harvested from `lm.history` into `LLMUsage` and a budget pre-check runs before compile. No challenger is deployed — that is Phase 3.

**Tech Stack:** Python 3.11, **DSPy 3.1.2** (`dspy.LM`, `dspy.Signature`, `dspy.Predict`, `dspy.teleprompt.BootstrapFewShot`, `dspy.utils.dummies.DummyLM` for tests), litellm (OpenRouter routing), SQLAlchemy, pytest, uv.

This is **Phase 2 of 3** from `docs/superpowers/specs/2026-06-09-prompt-optimization-design.md`. Phase 1 (attribution & labeling) is already merged. Phase 3 (champion/challenger experiment + promotion) is a later plan.

---

## Design notes (decisions locked before writing tasks)

1. **OpenRouter only.** The installed DSPy is **3.1.2** (spec assumed 2.x). The repo's existing `LLMClient`/`AnthropicBackend` talks to Anthropic *directly* (`ANTHROPIC_API_KEY`); per the project owner we must avoid that path here. The compile pipeline uses a native `dspy.LM` explicitly configured with `api_key=<OPENROUTER_API_KEY>` and `api_base="https://openrouter.ai/api/v1"`, and **validates** that the configured model string starts with `openrouter/` so it can never silently route to a direct provider. Missing key or non-OpenRouter model → loud `LLMConfigError`.

2. **Captured-fields constraint.** Phase 1's `TrainingExample` captured `base_q`, `base_a`, `note_context`, `variation_q`, `variation_a`, and `reward` — but NOT `fsrs_state` or `prior_variations`. So the DSPy signature/demos use inputs `base_q, base_a, note_context → question, answer`. FSRS/prior-variation context remains runtime-only (applied by the existing Jinja generator) and is intentionally not part of the optimized demos. No Phase 1 schema change.

3. **Strategy of a `TrainingExample`** is resolved by joining to `PromptVersion` via `TrainingExample.prompt_version_id` (PromptVersion carries `strategy`).

4. **Metric semantics (deliberate first cut).** `reward_metric(example, pred, trace=None)` returns `0.0` if the prediction is invalid (empty Q or A, or a verbatim duplicate of the base card), else `max(0.0, example.reward)`. This gates demo selection on validity while weighting by how much durable memory the gold historical variation built. It does NOT do semantic prediction-vs-gold scoring (no embedding/LLM-judge) — that is an explicit future extension, documented in the developer doc. Non-circular and implementable on thin data.

5. **Optimizer:** `BootstrapFewShot` first (config-selectable name, but only `bootstrap` is implemented in this phase). `MIPROv2` is deferred.

6. **Budget seam:** the CLI does the budget pre-check (`BudgetGuard(engine, daily_cents, monthly_cents).assert_within_budget()`) and builds the LM; `compile_challenger` does the DSPy work, persistence, and usage harvest. This keeps `compile_challenger` testable with an injected `DummyLM`.

---

## File Structure

**Create:**
- `backend/src/mnemonic/core/optimization/dspy_lm.py` — `build_openrouter_lm(...)` (guarded `dspy.LM`) + `harvest_usage(history)`.
- `backend/src/mnemonic/core/optimization/signatures.py` — `make_variation_signature(instruction_text)` + `VariationModule`.
- `backend/src/mnemonic/core/optimization/metric.py` — `is_valid_variation(...)` + `reward_metric(...)`.
- `backend/src/mnemonic/core/optimization/examples.py` — `build_trainset(...)` + `split_examples(...)`.
- `backend/src/mnemonic/core/optimization/compile.py` — `compile_challenger(...)`.
- `backend/src/mnemonic/cli/optimize.py` — `mnemonic-optimize` entrypoint.
- Tests: `backend/tests/unit/test_dspy_lm.py`, `test_signatures.py`, `test_metric.py`, `test_examples.py`; `backend/tests/integration/test_compile.py`, `test_cli_optimize.py`.

**Modify:**
- `backend/src/mnemonic/config.py` — extend `OptimizationConfig` with Phase 2 keys.
- `backend/pyproject.toml` — register `mnemonic-optimize` console script.
- `docs/source/developer/prompt-optimization.md` — add a Phase 2 section.

All commands assume working directory `backend/`.

---

### Task 1: Extend `OptimizationConfig` with Phase 2 keys

**Files:**
- Modify: `backend/src/mnemonic/config.py`
- Test: `backend/tests/unit/test_optimization_config.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `backend/tests/unit/test_optimization_config.py`:

```python
def test_optimization_phase2_defaults(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg_path = _write_config(tmp_path, vault)
    config = load_config(user_global_path=cfg_path)
    o = config.optimization
    assert o.min_examples_to_compile == 20
    assert o.optimizer == "bootstrap"
    assert o.max_bootstrapped_demos == 4
    assert o.max_labeled_demos == 8
    assert o.val_fraction == 0.3
    assert o.split_seed == 0
    assert o.validity_min_pass_rate == 0.8
    assert o.openrouter_key_env == "OPENROUTER_API_KEY"
    assert o.openrouter_api_base == "https://openrouter.ai/api/v1"


def test_optimization_phase2_overrides(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    extra = (
        "[optimization]\n"
        "min_examples_to_compile = 5\n"
        'optimizer = "bootstrap"\n'
        "max_bootstrapped_demos = 2\n"
        'openrouter_key_env = "OR_KEY"\n'
    )
    cfg_path = _write_config(tmp_path, vault, extra)
    o = load_config(user_global_path=cfg_path).optimization
    assert o.min_examples_to_compile == 5
    assert o.max_bootstrapped_demos == 2
    assert o.openrouter_key_env == "OR_KEY"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_optimization_config.py::test_optimization_phase2_defaults -v`
Expected: FAIL with `AttributeError: 'OptimizationConfig' object has no attribute 'min_examples_to_compile'`.

- [ ] **Step 3: Extend the dataclass and loader**

In `backend/src/mnemonic/config.py`, replace the `OptimizationConfig` dataclass body so it reads exactly:

```python
@dataclass(frozen=True)
class OptimizationConfig:
    reward_decay_gamma: float = 0.5
    reward_window_k: int = 3
    min_interval_hours: float = 20.0
    demo_margin_delta: float = 0.1
    min_examples_to_compile: int = 20
    optimizer: str = "bootstrap"
    max_bootstrapped_demos: int = 4
    max_labeled_demos: int = 8
    val_fraction: float = 0.3
    split_seed: int = 0
    validity_min_pass_rate: float = 0.8
    openrouter_key_env: str = "OPENROUTER_API_KEY"
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
```

In `load_config`, replace the `optimization = OptimizationConfig(...)` construction with:

```python
    optimization = OptimizationConfig(
        reward_decay_gamma=opt_section.get("reward_decay_gamma", 0.5),
        reward_window_k=opt_section.get("reward_window_k", 3),
        min_interval_hours=opt_section.get("min_interval_hours", 20.0),
        demo_margin_delta=opt_section.get("demo_margin_delta", 0.1),
        min_examples_to_compile=opt_section.get("min_examples_to_compile", 20),
        optimizer=opt_section.get("optimizer", "bootstrap"),
        max_bootstrapped_demos=opt_section.get("max_bootstrapped_demos", 4),
        max_labeled_demos=opt_section.get("max_labeled_demos", 8),
        val_fraction=opt_section.get("val_fraction", 0.3),
        split_seed=opt_section.get("split_seed", 0),
        validity_min_pass_rate=opt_section.get("validity_min_pass_rate", 0.8),
        openrouter_key_env=opt_section.get("openrouter_key_env", "OPENROUTER_API_KEY"),
        openrouter_api_base=opt_section.get(
            "openrouter_api_base", "https://openrouter.ai/api/v1"
        ),
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/unit/test_optimization_config.py -v`
Expected: PASS (all, including the two new tests).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/config.py tests/unit/test_optimization_config.py
git commit -m "feat(optimization): phase 2 config keys (compile + openrouter)"
```

---

### Task 2: OpenRouter `dspy.LM` builder + usage harvest

**Files:**
- Create: `backend/src/mnemonic/core/optimization/dspy_lm.py`
- Test: `backend/tests/unit/test_dspy_lm.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_dspy_lm.py`:

```python
"""Tests for the OpenRouter-pinned DSPy LM builder and usage harvest."""

from __future__ import annotations

import pytest

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.dspy_lm import build_openrouter_lm, harvest_usage
from mnemonic.exceptions import LLMConfigError


def test_build_lm_requires_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = OptimizationConfig()
    with pytest.raises(LLMConfigError, match="OPENROUTER_API_KEY"):
        build_openrouter_lm(model="openrouter/anthropic/claude-3.5-haiku", config=cfg)


def test_build_lm_rejects_non_openrouter_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    cfg = OptimizationConfig()
    with pytest.raises(LLMConfigError, match="openrouter/"):
        build_openrouter_lm(model="anthropic/claude-3.5-haiku", config=cfg)


def test_build_lm_configures_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    cfg = OptimizationConfig()
    lm = build_openrouter_lm(model="openrouter/anthropic/claude-3.5-haiku", config=cfg)
    assert lm.model == "openrouter/anthropic/claude-3.5-haiku"
    # api_base is forwarded to litellm via kwargs
    assert lm.kwargs.get("api_base") == "https://openrouter.ai/api/v1"


def test_harvest_usage_prefers_openrouter_usage_cost():
    # OpenRouter always returns `cost` (USD) inside the usage object. We prefer
    # that authoritative value over litellm's computed top-level `cost`.
    history = [
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.001},
         "cost": 0.0},  # litellm computed 0 (no pricing) -> must NOT win
        {"usage": {"prompt_tokens": 50, "completion_tokens": 10, "cost": 0.0005},
         "cost": None},
    ]
    totals = harvest_usage(history)
    assert totals.input_tokens == 150
    assert totals.output_tokens == 30
    # (0.001 + 0.0005) USD * 100_000 millicents/USD = 150
    assert totals.cost_millicents == 150


def test_harvest_usage_falls_back_to_top_level_cost():
    # If OpenRouter usage.cost is absent, fall back to litellm's response_cost.
    history = [
        {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "cost": 0.002},
        {"usage": {"prompt_tokens": 0, "completion_tokens": 0}, "cost": None},
    ]
    totals = harvest_usage(history)
    assert totals.input_tokens == 10
    assert totals.output_tokens == 5
    assert totals.cost_millicents == 200  # 0.002 USD * 100_000
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_dspy_lm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.dspy_lm'`.

- [ ] **Step 3: Implement**

Create `backend/src/mnemonic/core/optimization/dspy_lm.py`:

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/unit/test_dspy_lm.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/dspy_lm.py tests/unit/test_dspy_lm.py
git commit -m "feat(optimization): OpenRouter-pinned DSPy LM builder + usage harvest"
```

---

### Task 3: Per-strategy signature + module

**Files:**
- Create: `backend/src/mnemonic/core/optimization/signatures.py`
- Test: `backend/tests/unit/test_signatures.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_signatures.py`:

```python
"""Tests for the variation DSPy signature and module."""

from __future__ import annotations

from mnemonic.core.optimization.signatures import (
    VariationModule,
    make_variation_signature,
)


def test_signature_has_expected_fields_and_instructions():
    sig = make_variation_signature("REPHRASE INSTRUCTIONS")
    assert sig.instructions == "REPHRASE INSTRUCTIONS"
    assert set(sig.input_fields.keys()) == {"base_q", "base_a", "note_context"}
    assert set(sig.output_fields.keys()) == {"question", "answer"}


def test_module_wraps_a_predict_with_the_signature():
    sig = make_variation_signature("X")
    module = VariationModule(sig)
    assert module.predict.signature.instructions == "X"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_signatures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.signatures'`.

- [ ] **Step 3: Implement**

Create `backend/src/mnemonic/core/optimization/signatures.py`:

```python
"""DSPy signature and module for variation generation.

Inputs are restricted to the fields Phase 1 actually captured in
``TrainingExample`` (base_q, base_a, note_context). FSRS state and prior
variations are runtime-only context applied by the Jinja generator and are
intentionally not part of the optimized signature/demos.
"""

from __future__ import annotations

import dspy

_SIGNATURE_SPEC = "base_q, base_a, note_context -> question, answer"


def make_variation_signature(instruction_text: str) -> type[dspy.Signature]:
    """Build a variation signature seeded with the given instruction text.

    Args:
        instruction_text: The strategy instruction (a champion's instruction_text).

    Returns:
        A dspy.Signature class with base_q/base_a/note_context inputs and
        question/answer outputs.
    """
    return dspy.Signature(_SIGNATURE_SPEC, instruction_text)


class VariationModule(dspy.Module):
    """A single-Predict module over the variation signature."""

    def __init__(self, signature: type[dspy.Signature]) -> None:
        """Initialize with a variation signature.

        Args:
            signature: The signature produced by ``make_variation_signature``.
        """
        super().__init__()
        self.predict = dspy.Predict(signature)

    def forward(self, **kwargs: str) -> dspy.Prediction:
        """Generate a variation. Keyword args are the signature input fields."""
        return self.predict(**kwargs)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/unit/test_signatures.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/signatures.py tests/unit/test_signatures.py
git commit -m "feat(optimization): per-strategy DSPy variation signature + module"
```

---

### Task 4: Validity check + reward metric

**Files:**
- Create: `backend/src/mnemonic/core/optimization/metric.py`
- Test: `backend/tests/unit/test_metric.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_metric.py`:

```python
"""Tests for the validity check and reward-weighted metric."""

from __future__ import annotations

import dspy

from mnemonic.core.optimization.metric import is_valid_variation, reward_metric


def _example(reward, base_q="What is X?", base_a="X is Y."):
    return dspy.Example(
        base_q=base_q, base_a=base_a, note_context="ctx",
        question="gold q", answer="gold a", reward=reward,
    ).with_inputs("base_q", "base_a", "note_context")


def _pred(question, answer):
    return dspy.Prediction(question=question, answer=answer)


def test_is_valid_rejects_empty_fields():
    assert is_valid_variation(base_q="q", base_a="a", question="", answer="x") is False
    assert is_valid_variation(base_q="q", base_a="a", question="x", answer="") is False


def test_is_valid_rejects_verbatim_duplicate_of_base():
    assert is_valid_variation(
        base_q="What is X?", base_a="X is Y.",
        question="What is X?", answer="X is Y.",
    ) is False


def test_is_valid_accepts_a_distinct_well_formed_variation():
    assert is_valid_variation(
        base_q="What is X?", base_a="X is Y.",
        question="Define X.", answer="It is Y.",
    ) is True


def test_metric_zero_for_invalid_prediction():
    ex = _example(reward=0.8)
    assert reward_metric(ex, _pred("", "a")) == 0.0


def test_metric_returns_clamped_reward_for_valid_prediction():
    ex = _example(reward=0.8)
    assert reward_metric(ex, _pred("Define X.", "It is Y.")) == 0.8


def test_metric_clamps_negative_reward_to_zero():
    ex = _example(reward=-0.5)
    assert reward_metric(ex, _pred("Define X.", "It is Y.")) == 0.0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_metric.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.metric'`.

- [ ] **Step 3: Implement**

Create `backend/src/mnemonic/core/optimization/metric.py`:

```python
"""Validity check and reward-weighted metric for DSPy compilation.

The metric gates demo/candidate selection on validity (well-formed, not a
verbatim copy of the base card) and weights by how much durable memory the gold
historical variation built (its Phase 1 reward, clamped to non-negative). It is
intentionally NOT a semantic prediction-vs-gold score — that is a future
extension; see the developer doc.
"""

from __future__ import annotations

from typing import Any


def is_valid_variation(*, base_q: str, base_a: str, question: str, answer: str) -> bool:
    """Return True if a generated variation is well-formed and non-trivial.

    Args:
        base_q: The base card question.
        base_a: The base card answer.
        question: The generated question.
        answer: The generated answer.

    Returns:
        False if either generated field is empty/whitespace, or if the generated
        Q and A both verbatim-match the base card (no variation). True otherwise.
    """
    if not question or not question.strip():
        return False
    if not answer or not answer.strip():
        return False
    duplicates_base = (
        question.strip() == base_q.strip() and answer.strip() == base_a.strip()
    )
    return not duplicates_base


def reward_metric(example: Any, pred: Any, trace: Any = None) -> float:
    """Score a prediction: 0.0 if invalid, else the gold reward clamped to >= 0.

    Args:
        example: A dspy.Example carrying base_q/base_a and the gold ``reward``.
        pred: A dspy.Prediction with ``question`` and ``answer``.
        trace: DSPy trace (unused; present for the optimizer's metric contract).

    Returns:
        A float score for the optimizer.
    """
    if not is_valid_variation(
        base_q=getattr(example, "base_q", ""),
        base_a=getattr(example, "base_a", ""),
        question=getattr(pred, "question", "") or "",
        answer=getattr(pred, "answer", "") or "",
    ):
        return 0.0
    return max(0.0, float(getattr(example, "reward", 0.0) or 0.0))
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/unit/test_metric.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/metric.py tests/unit/test_metric.py
git commit -m "feat(optimization): validity check + reward-weighted DSPy metric"
```

---

### Task 5: Trainset builder + deterministic split

**Files:**
- Create: `backend/src/mnemonic/core/optimization/examples.py`
- Test: `backend/tests/unit/test_examples.py`

`build_trainset` joins `TrainingExample` to `PromptVersion` via `prompt_version_id` to filter by strategy, keeps finalized rows with a non-null reward, and builds `dspy.Example`s. Below `min_examples_to_compile` it raises `InsufficientDataError`. `split_examples` does a deterministic shuffle+split.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_examples.py`:

```python
"""Tests for the DSPy trainset builder and deterministic split."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.examples import build_trainset, split_examples
from mnemonic.db.models import Base, PromptVersion, TrainingExample
from mnemonic.exceptions import InsufficientDataError


def _engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def _champion(s, strategy="rephrase", pv_id="pv-r"):
    s.add(PromptVersion(
        id=pv_id, strategy=strategy, version_no=0, instruction_text="seed",
        demos="[]", status="champion", parent_version_id=None,
        compiled_from_n_examples=None, created_at=datetime(2026, 6, 1),
    ))


def _example(s, i, pv_id="pv-r", finalized=True, reward=0.5):
    s.add(TrainingExample(
        id=f"te{i}", card_id=f"c{i}", variation_id=f"v{i}", prompt_version_id=pv_id,
        base_q=f"bq{i}", base_a=f"ba{i}", variation_q=f"vq{i}", variation_a=f"va{i}",
        label=1, reward=reward, maturity=3, finalized=finalized, rating=None,
        note_context=f"ctx{i}", created_at=datetime(2026, 6, 1),
    ))


def test_build_trainset_filters_by_strategy_and_finalized():
    engine = _engine()
    with Session(engine) as s:
        _champion(s, "rephrase", "pv-r")
        _champion(s, "specialize", "pv-s")
        for i in range(3):
            _example(s, i, "pv-r", finalized=True)
        _example(s, 99, "pv-r", finalized=False)       # excluded: not finalized
        _example(s, 100, "pv-s", finalized=True)        # excluded: other strategy
        s.commit()
        cfg = OptimizationConfig(min_examples_to_compile=1)
        train = build_trainset(s, strategy="rephrase", config=cfg)
        assert len(train) == 3
        ex = train[0]
        assert set(ex.inputs().keys()) == {"base_q", "base_a", "note_context"}
        assert ex.question.startswith("vq")
        assert ex.answer.startswith("va")
        assert isinstance(ex.reward, float)


def test_build_trainset_raises_when_too_few():
    engine = _engine()
    with Session(engine) as s:
        _champion(s, "rephrase", "pv-r")
        _example(s, 0, "pv-r", finalized=True)
        s.commit()
        cfg = OptimizationConfig(min_examples_to_compile=20)
        with pytest.raises(InsufficientDataError) as ei:
            build_trainset(s, strategy="rephrase", config=cfg)
        assert ei.value.have == 1
        assert ei.value.need == 20


def test_split_is_deterministic_for_a_seed():
    items = list(range(10))
    a_train, a_val = split_examples(items, val_fraction=0.3, seed=0)
    b_train, b_val = split_examples(items, val_fraction=0.3, seed=0)
    assert a_train == b_train and a_val == b_val
    assert len(a_val) == 3 and len(a_train) == 7
    # different seed -> (very likely) different partition order
    c_train, c_val = split_examples(items, val_fraction=0.3, seed=1)
    assert sorted(c_train + c_val) == items
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_examples.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.examples'`.

- [ ] **Step 3: Implement**

Create `backend/src/mnemonic/core/optimization/examples.py`:

```python
"""Build a DSPy trainset from finalized, reward-labeled TrainingExamples."""

from __future__ import annotations

import random
from typing import Any, TypeVar

import dspy
from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.db.models import PromptVersion, TrainingExample
from mnemonic.exceptions import InsufficientDataError

T = TypeVar("T")


def build_trainset(
    session: Session, *, strategy: str, config: OptimizationConfig
) -> list[dspy.Example]:
    """Build dspy.Examples for a strategy from finalized, rewarded examples.

    Args:
        session: Active SQLAlchemy session.
        strategy: Strategy name (resolved via PromptVersion.prompt_version_id).
        config: Optimization config (provides ``min_examples_to_compile``).

    Returns:
        A list of dspy.Example with base_q/base_a/note_context inputs, the
        historical variation as question/answer, and the gold ``reward``.

    Raises:
        InsufficientDataError: If fewer than ``min_examples_to_compile`` rows
            qualify.
    """
    rows = session.execute(
        select(TrainingExample)
        .join(PromptVersion, TrainingExample.prompt_version_id == PromptVersion.id)
        .where(
            PromptVersion.strategy == strategy,
            TrainingExample.finalized.is_(True),
            TrainingExample.reward.is_not(None),
        )
        .order_by(TrainingExample.created_at.asc(), TrainingExample.id.asc())
    ).scalars().all()

    if len(rows) < config.min_examples_to_compile:
        raise InsufficientDataError(
            strategy, have=len(rows), need=config.min_examples_to_compile
        )

    examples: list[dspy.Example] = []
    for row in rows:
        examples.append(
            dspy.Example(
                base_q=row.base_q,
                base_a=row.base_a,
                note_context=row.note_context or "",
                question=row.variation_q,
                answer=row.variation_a,
                reward=float(row.reward),
            ).with_inputs("base_q", "base_a", "note_context")
        )
    return examples


def split_examples(
    items: list[T], *, val_fraction: float, seed: int
) -> tuple[list[T], list[T]]:
    """Deterministically shuffle and split items into (train, val).

    Args:
        items: The full list to split.
        val_fraction: Fraction of items to place in the validation split.
        seed: RNG seed for reproducibility.

    Returns:
        A (train, val) tuple. ``val`` gets ``floor(len*val_fraction)`` items.
    """
    shuffled = list(items)
    random.Random(seed).shuffle(shuffled)
    n_val = int(len(shuffled) * val_fraction)
    val = shuffled[:n_val]
    train = shuffled[n_val:]
    return train, val
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/unit/test_examples.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/examples.py tests/unit/test_examples.py
git commit -m "feat(optimization): DSPy trainset builder + deterministic split"
```

---

### Task 6: Compile a challenger prompt version

**Files:**
- Create: `backend/src/mnemonic/core/optimization/compile.py`
- Test: `backend/tests/integration/test_compile.py`

`compile_challenger` configures DSPy with the given LM (injected `DummyLM` in tests), loads the champion, builds + splits the trainset, seeds a `VariationModule` from the champion's instruction, runs `BootstrapFewShot` with `reward_metric`, runs a validity gate on the val split, writes a new `challenger` `PromptVersion`, and records an `LLMUsage` row from `lm.history`.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/integration/test_compile.py`:

```python
"""Integration tests for compile_challenger (DummyLM, no network)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from dspy.utils.dummies import DummyLM
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.compile import compile_challenger
from mnemonic.db.models import Base, LLMUsage, PromptVersion, TrainingExample
from mnemonic.exceptions import InsufficientDataError


def _engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def _seed(engine, n=6, strategy="rephrase", pv_id="pv-r"):
    with Session(engine) as s:
        s.add(PromptVersion(
            id=pv_id, strategy=strategy, version_no=0,
            instruction_text="Rephrase the card.", demos="[]", status="champion",
            parent_version_id=None, compiled_from_n_examples=None,
            created_at=datetime(2026, 6, 1),
        ))
        for i in range(n):
            s.add(TrainingExample(
                id=f"te{i}", card_id=f"c{i}", variation_id=f"v{i}",
                prompt_version_id=pv_id, base_q=f"What is X{i}?", base_a=f"X{i} is Y.",
                variation_q=f"hist q{i}", variation_a=f"hist a{i}", label=1,
                reward=0.6, maturity=3, finalized=True, rating=None,
                note_context="ctx", created_at=datetime(2026, 6, 1),
            ))
        s.commit()


def _dummy_lm(n=40):
    # Valid, distinct Q/A so the validity gate passes.
    return DummyLM([{"question": f"gen q{i}", "answer": f"gen a{i}"} for i in range(n)])


def test_compile_writes_challenger_with_provenance_and_usage():
    engine = _engine()
    _seed(engine, n=6)
    cfg = OptimizationConfig(min_examples_to_compile=2, max_bootstrapped_demos=2,
                             val_fraction=0.34, validity_min_pass_rate=0.5)
    challenger = compile_challenger(
        engine, strategy="rephrase", config=cfg, lm=_dummy_lm(),
        now=datetime(2026, 6, 9, 12, 0, 0),
    )
    with Session(engine) as s:
        row = s.get(PromptVersion, challenger.id)
        assert row.status == "challenger"
        assert row.strategy == "rephrase"
        assert row.parent_version_id == "pv-r"
        assert row.version_no == 1
        assert row.compiled_from_n_examples is not None
        demos = json.loads(row.demos)
        assert isinstance(demos, list)
        usage = s.execute(
            select(LLMUsage).where(LLMUsage.purpose == "optimize:rephrase")
        ).scalars().all()
        assert len(usage) == 1


def test_compile_raises_on_insufficient_data():
    engine = _engine()
    _seed(engine, n=1)
    cfg = OptimizationConfig(min_examples_to_compile=20)
    with pytest.raises(InsufficientDataError):
        compile_challenger(
            engine, strategy="rephrase", config=cfg, lm=_dummy_lm(),
            now=datetime(2026, 6, 9),
        )
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/integration/test_compile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.compile'`.

- [ ] **Step 3: Implement**

Create `backend/src/mnemonic/core/optimization/compile.py`:

```python
"""Compile a challenger prompt version for a strategy using DSPy."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import dspy
from dspy.teleprompt import BootstrapFewShot
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.dspy_lm import harvest_usage
from mnemonic.core.optimization.examples import build_trainset, split_examples
from mnemonic.core.optimization.metric import is_valid_variation, reward_metric
from mnemonic.core.optimization.registry import get_champion
from mnemonic.core.optimization.signatures import VariationModule, make_variation_signature
from mnemonic.db.models import LLMUsage, PromptVersion
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import OptimizationError


def _next_version_no(session: Session, strategy: str) -> int:
    current = session.execute(
        select(func.max(PromptVersion.version_no)).where(
            PromptVersion.strategy == strategy
        )
    ).scalar_one_or_none()
    return (current or 0) + 1


def _run_validity_gate(
    program: VariationModule, val: list[dspy.Example], min_pass_rate: float
) -> None:
    """Raise OptimizationError if too few val predictions are valid."""
    if not val:
        return
    valid = 0
    for example in val:
        pred = program(**example.inputs())
        if is_valid_variation(
            base_q=example.base_q,
            base_a=example.base_a,
            question=getattr(pred, "question", "") or "",
            answer=getattr(pred, "answer", "") or "",
        ):
            valid += 1
    pass_rate = valid / len(val)
    if pass_rate < min_pass_rate:
        raise OptimizationError(
            f"Compiled challenger failed the validity gate: {valid}/{len(val)} "
            f"valid ({pass_rate:.0%} < {min_pass_rate:.0%}). Not storing it."
        )


def compile_challenger(
    engine: Engine,
    *,
    strategy: str,
    config: OptimizationConfig,
    lm: dspy.BaseLM,
    now: datetime,
) -> PromptVersion:
    """Compile and persist a challenger prompt version for a strategy.

    Args:
        engine: SQLAlchemy engine for the state DB.
        strategy: Strategy to optimize (must have a champion).
        config: Optimization config.
        lm: A configured DSPy LM (real OpenRouter LM in production; DummyLM in
            tests). Used for bootstrapping and the validity gate.
        now: Timestamp for the new row and the usage record.

    Returns:
        The newly written challenger PromptVersion (detached copy of fields).

    Raises:
        OptimizationError: If the optimizer name is unsupported or the compiled
            program fails the validity gate.
        InsufficientDataError: If the trainset is too small.
    """
    if config.optimizer != "bootstrap":
        raise OptimizationError(
            f"Unsupported optimizer '{config.optimizer}'. Phase 2 implements "
            "only 'bootstrap'."
        )

    dspy.configure(lm=lm)

    with session_scope(engine) as session:
        champion = get_champion(session, strategy)
        champion_id = champion.id
        instruction = champion.instruction_text
        examples = build_trainset(session, strategy=strategy, config=config)
        version_no = _next_version_no(session, strategy)

    train, val = split_examples(
        examples, val_fraction=config.val_fraction, seed=config.split_seed
    )

    student = VariationModule(make_variation_signature(instruction))
    optimizer = BootstrapFewShot(
        metric=reward_metric,
        metric_threshold=0.0,
        max_bootstrapped_demos=config.max_bootstrapped_demos,
        max_labeled_demos=config.max_labeled_demos,
    )
    compiled = optimizer.compile(student, trainset=train)

    _run_validity_gate(compiled, val, config.validity_min_pass_rate)

    demos_state = compiled.predict.dump_state().get("demos", [])
    challenger_id = uuid.uuid4().hex
    totals = harvest_usage(lm.history)

    with session_scope(engine) as session:
        session.add(PromptVersion(
            id=challenger_id,
            strategy=strategy,
            version_no=version_no,
            instruction_text=compiled.predict.signature.instructions,
            demos=json.dumps(demos_state),
            status="challenger",
            parent_version_id=champion_id,
            compiled_from_n_examples=len(examples),
            created_at=now,
        ))
        session.add(LLMUsage(
            id=uuid.uuid4().hex,
            timestamp=now,
            model=getattr(lm, "model", "unknown"),
            purpose=f"optimize:{strategy}",
            input_tokens=totals.input_tokens,
            output_tokens=totals.output_tokens,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_millicents=totals.cost_millicents,
            card_id=None,
        ))

    with session_scope(engine) as session:
        return session.get(PromptVersion, challenger_id)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/integration/test_compile.py -v`
Expected: PASS (2 passed). If the validity gate or DummyLM interaction needs a tweak, read the actual error — do NOT weaken assertions; adjust the DummyLM canned outputs or config knobs in the test setup so the gate genuinely passes.

- [ ] **Step 5: Run the optimization suite + coverage**

Run: `uv run pytest tests/unit/test_dspy_lm.py tests/unit/test_signatures.py tests/unit/test_metric.py tests/unit/test_examples.py tests/integration/test_compile.py --cov=mnemonic.core.optimization --cov-report=term-missing`
Expected: all pass; report coverage for the new modules (target core ≥ 95%; `compile.py` may be slightly lower due to the unsupported-optimizer branch — that is fine if ≥ 90%).

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/core/optimization/compile.py tests/integration/test_compile.py
git commit -m "feat(optimization): compile_challenger writes a DSPy-optimized challenger"
```

---

### Task 7: `mnemonic-optimize` CLI

**Files:**
- Create: `backend/src/mnemonic/cli/optimize.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/integration/test_cli_optimize.py`

The CLI loads config, runs a budget pre-check, builds the OpenRouter LM, calls `compile_challenger`, and prints the new challenger's version. `run_optimize` is factored out (LM injected) for testing without network/keys.

- [ ] **Step 1: Write failing test**

Create `backend/tests/integration/test_cli_optimize.py`:

```python
"""Integration test for the mnemonic-optimize CLI (DummyLM, no network)."""

from __future__ import annotations

from datetime import datetime

from dspy.utils.dummies import DummyLM
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.cli.optimize import run_optimize
from mnemonic.config import OptimizationConfig
from mnemonic.db.models import Base, PromptVersion, TrainingExample


def _engine_path(tmp_path):
    db = tmp_path / "state.sqlite"
    engine = create_engine(f"sqlite:///{db}", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_run_optimize_creates_challenger(tmp_path):
    engine = _engine_path(tmp_path)
    with Session(engine) as s:
        s.add(PromptVersion(
            id="pv-r", strategy="rephrase", version_no=0,
            instruction_text="Rephrase.", demos="[]", status="champion",
            parent_version_id=None, compiled_from_n_examples=None,
            created_at=datetime(2026, 6, 1),
        ))
        for i in range(4):
            s.add(TrainingExample(
                id=f"te{i}", card_id=f"c{i}", variation_id=f"v{i}",
                prompt_version_id="pv-r", base_q=f"What is X{i}?", base_a="Y.",
                variation_q=f"q{i}", variation_a=f"a{i}", label=1, reward=0.6,
                maturity=3, finalized=True, rating=None, note_context="ctx",
                created_at=datetime(2026, 6, 1),
            ))
        s.commit()

    cfg = OptimizationConfig(min_examples_to_compile=2, max_bootstrapped_demos=2,
                             val_fraction=0.34, validity_min_pass_rate=0.5)
    lm = DummyLM([{"question": f"gen q{i}", "answer": f"gen a{i}"} for i in range(40)])

    challenger = run_optimize(
        engine=engine, strategy="rephrase", config=cfg, lm=lm,
        now=datetime(2026, 6, 9, 12, 0, 0),
    )
    assert challenger.status == "challenger"
    assert challenger.version_no == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/integration/test_cli_optimize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.cli.optimize'`.

- [ ] **Step 3: Implement**

Create `backend/src/mnemonic/cli/optimize.py`:

```python
"""`mnemonic-optimize <strategy>`: compile a challenger prompt via DSPy/OpenRouter."""

from __future__ import annotations

import argparse
from datetime import datetime

import dspy
from sqlalchemy import Engine

from mnemonic.config import Config, OptimizationConfig, load_config
from mnemonic.core.optimization.compile import compile_challenger
from mnemonic.core.optimization.dspy_lm import build_openrouter_lm
from mnemonic.core.optimization.registry import DEFAULT_STRATEGIES
from mnemonic.db.models import PromptVersion
from mnemonic.db.sqlite import create_engine
from mnemonic.llm.budget import BudgetGuard


def run_optimize(
    *,
    engine: Engine,
    strategy: str,
    config: OptimizationConfig,
    lm: dspy.BaseLM,
    now: datetime,
) -> PromptVersion:
    """Compile a challenger with an injected LM (testable seam).

    Args:
        engine: SQLAlchemy engine for the state DB.
        strategy: Strategy to optimize.
        config: Optimization config.
        lm: A configured DSPy LM.
        now: Timestamp for the new rows.

    Returns:
        The new challenger PromptVersion.
    """
    return compile_challenger(engine, strategy=strategy, config=config, lm=lm, now=now)


def _resolve(config: Config, engine: Engine) -> tuple[OptimizationConfig, dspy.BaseLM]:
    """Budget pre-check and OpenRouter LM construction from full config."""
    BudgetGuard(
        engine=engine,
        daily_cents=config.llm.budget.daily_cents,
        monthly_cents=config.llm.budget.monthly_cents,
    ).assert_within_budget()
    lm = build_openrouter_lm(model=config.llm.model_offline, config=config.optimization)
    return config.optimization, lm


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-optimize",
        description="Compile a challenger variation prompt for a strategy.",
    )
    parser.add_argument("strategy", choices=DEFAULT_STRATEGIES)
    args = parser.parse_args(argv)

    config = load_config()
    engine = create_engine(config.vault.path / ".mnemonic" / "state.sqlite")
    opt_config, lm = _resolve(config, engine)
    challenger = run_optimize(
        engine=engine,
        strategy=args.strategy,
        config=opt_config,
        lm=lm,
        now=datetime.now(),
    )
    print(
        f"compiled challenger {challenger.strategy} v{challenger.version_no} "
        f"({challenger.id}) from {challenger.compiled_from_n_examples} examples"
    )
    return 0
```

- [ ] **Step 4: Register the console script**

In `backend/pyproject.toml`, the `[project.scripts]` table already exists (from Phase 1, with `mnemonic-label`). Add this line to it:

```toml
mnemonic-optimize = "mnemonic.cli.optimize:main"
```

Then run `uv sync --extra dev`.

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/integration/test_cli_optimize.py -v`
Expected: PASS.

Also confirm the entrypoint parses args: `uv run mnemonic-optimize --help`
Expected: usage text listing the `strategy` positional with choices rephrase/specialize/generalize.

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/cli/optimize.py pyproject.toml tests/integration/test_cli_optimize.py
git commit -m "feat(optimization): mnemonic-optimize CLI to compile challengers"
```

---

### Task 8: Developer docs + full verification

**Files:**
- Modify: `docs/source/developer/prompt-optimization.md` (at the worktree/repo root, NOT under backend/)

- [ ] **Step 1: Append a Phase 2 section**

Append to `docs/source/developer/prompt-optimization.md`:

```markdown

## Phase 2 — DSPy Compile Pipeline

`mnemonic-optimize <strategy>` compiles a **challenger** prompt version from the
reward-labeled `TrainingExample`s of Phase 1.

### LLM path (OpenRouter only)

The compile pipeline uses a native `dspy.LM` pinned to OpenRouter — it never uses
the direct-Anthropic backend. `build_openrouter_lm` requires `OPENROUTER_API_KEY`
(name configurable via `[optimization] openrouter_key_env`) and refuses any model
string that does not start with `openrouter/`. Set `[llm] model_offline` to e.g.
`openrouter/anthropic/claude-3.5-haiku` (pick a real slug from
openrouter.ai/models). Cost is harvested from the LM history into an `LLMUsage`
row (`purpose = "optimize:<strategy>"`): OpenRouter always returns an
authoritative `usage.cost` (USD) per response, which we prefer over litellm's
computed cost. A budget pre-check runs before compile.

### How it compiles

- Per-strategy `dspy.Signature` (`base_q, base_a, note_context -> question, answer`)
  seeded from the current champion's instruction text. (FSRS state and prior
  variations are runtime-only context, not part of the optimized demos, because
  Phase 1 did not capture them.)
- Trainset = finalized, non-null-reward `TrainingExample`s for the strategy
  (joined to `PromptVersion` for the strategy filter), below
  `min_examples_to_compile` it raises `InsufficientDataError`.
- `BootstrapFewShot` selects demos using `reward_metric`: `0.0` if the prediction
  is invalid (empty Q/A or a verbatim copy of the base), else the gold example's
  reward clamped to non-negative. This gates on validity and weights by durable
  memory built. It is **not** a semantic prediction-vs-gold score — that is a
  deliberate future extension.
- A validity gate runs the compiled program on the held-out split; if fewer than
  `validity_min_pass_rate` of predictions are valid, the challenger is rejected
  (`OptimizationError`) and not stored.
- On success a new `prompt_version` row is written: `status="challenger"`,
  `parent_version_id` = champion, `version_no` = max+1, `instruction_text` +
  serialized `demos`, `compiled_from_n_examples`. Nothing is deployed — Phase 3
  runs the champion/challenger experiment.

### Running

```bash
uv run mnemonic-optimize rephrase
```

### Phase 2 configuration (`[optimization]`)

| key | default | meaning |
|---|---|---|
| `min_examples_to_compile` | 20 | refuse to compile below this many finalized examples |
| `optimizer` | `bootstrap` | optimizer (only `bootstrap` implemented in Phase 2) |
| `max_bootstrapped_demos` | 4 | DSPy bootstrapped demo cap |
| `max_labeled_demos` | 8 | DSPy labeled demo cap |
| `val_fraction` | 0.3 | held-out fraction for the validity gate |
| `split_seed` | 0 | deterministic split seed |
| `validity_min_pass_rate` | 0.8 | min valid fraction on the val split to accept |
| `openrouter_key_env` | `OPENROUTER_API_KEY` | env var holding the OpenRouter key |
| `openrouter_api_base` | `https://openrouter.ai/api/v1` | OpenRouter base URL |
```

- [ ] **Step 2: Full verification (from `backend/`)**

Run each; fix only Phase 2 files:
1. `uv run ruff check src/mnemonic/core/optimization src/mnemonic/cli/optimize.py`
2. `uv run black --check src/mnemonic/core/optimization src/mnemonic/cli`
3. `uv run mypy src/mnemonic/core/optimization src/mnemonic/cli/optimize.py` (fix type errors in Phase 2 files; pre-existing errors elsewhere are out of scope)
4. `uv run pytest -q 2>&1 | tail -8`

For the test run: the only acceptable failures are the 3 known pre-existing ones (`test_redis_import`, `test_jose_import`, `test_passlib_import` in `tests/test_setup.py`). Everything else must pass. Report the summary line.

- [ ] **Step 3: Commit**

```bash
git add docs/source/developer/prompt-optimization.md
# include any Phase 2 source files touched for lint/format/mypy
git commit -m "docs(optimization): phase 2 DSPy compile pipeline developer guide"
```

---

## Self-Review (completed during planning)

**Spec coverage (Phase 2 section of the design doc):**
- DSPy↔LLM adapter (single tracked path, loud on misconfig) → Task 2, reframed to **OpenRouter-only** per owner decision (the spec's "wrap LLMClient" wording assumed dspy 2.x and the direct-Anthropic client; this is the safer realization of the same intent).
- Per-strategy `dspy.Signature` seeded from champion → Tasks 3, 6.
- Behavioral metric over historical labels (no LLM-judge circularity) → Task 4 (`reward_metric`), documented as validity-gated reward-weighting.
- `BootstrapFewShot` first; MIPRO deferred → Task 6 (unsupported-optimizer branch raises loudly).
- Trainset builder, deterministic split, loud `InsufficientDataError` → Task 5.
- Validity gate rejecting malformed challengers at compile time → Task 6 (`_run_validity_gate`).
- Challenger artifact with provenance (status/parent/version_no/compiled_from_n_examples/instruction/demos), nothing deployed → Task 6.
- `mnemonic optimize <strategy>` command → Task 7.
- Cost logged (`LLMUsage purpose=optimize:<strategy>`) + budget pre-check → Tasks 2, 6, 7.
- Config surface (`min_examples_to_compile`, `optimizer`, demos caps, etc.) → Task 1.

**Deviations from spec (intentional, documented):** (a) LM path is native `dspy.LM`→OpenRouter, not a `BaseLM` wrapping `LLMClient` (dspy 3.x + owner's key-safety preference). (b) Signature inputs limited to Phase-1-captured fields (no fsrs/prior). (c) Metric is validity-gated reward-weighting rather than semantic match — a deliberate first cut; richer scoring is future work. These are recorded in the developer doc.

**Out of scope (Phase 3):** arm assignment, the `experiment` table, Bayesian promotion, deploying/serving the challenger, `ExperimentStateError`. Challengers are written but never used at runtime in Phase 2.

**Placeholder scan:** none — every code step has complete code; every run step has an exact command and expected output.

**Type/name consistency:** `OptimizationConfig` new fields are referenced consistently across Tasks 1/2/5/6/7. `build_openrouter_lm(*, model, config)`, `harvest_usage(history)->UsageTotals`, `make_variation_signature(instruction_text)`, `VariationModule(signature)`, `reward_metric(example, pred, trace=None)`, `is_valid_variation(*, base_q, base_a, question, answer)`, `build_trainset(session, *, strategy, config)`, `split_examples(items, *, val_fraction, seed)`, `compile_challenger(engine, *, strategy, config, lm, now)`, `run_optimize(*, engine, strategy, config, lm, now)` — signatures match between definition and all call sites/tests. `DEFAULT_STRATEGIES` is reused from the Phase 1 `registry` module. `get_champion` (Phase 1) is reused.
```
