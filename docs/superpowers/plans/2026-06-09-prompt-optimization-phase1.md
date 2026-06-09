# Prompt Optimization — Phase 1 (Attribution & Labeling) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data layer that records which prompt version produced each variation and computes an FSRS-adjusted, decaying "did this build durable memory" reward for it, landing labeled rows in `TrainingExample`.

**Architecture:** A prompt registry (`prompt_version`) seeds one champion per strategy from the existing on-disk markdown. `persist_variation` is extended to create an *unlabeled* `TrainingExample` at generation time (capturing prompt version + input/output text). A pure reward function (`core/optimization/reward.py`) turns a card's subsequent reviews into a calibration-surprise score with geometric decay. An idempotent labeling job (`core/optimization/labeling.py`) links each variation to the reviews that followed it (via `ReviewLog.variation_id`), computes the maturing reward, and upserts it onto the `TrainingExample`. A stdlib-argparse command (`mnemonic-label`) runs the job. No DSPy in this phase.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0 (declarative `Mapped`), Alembic, SQLite, pytest, uv. FSRS retrievability via existing `mnemonic.core.fsrs.algorithm.calculate_retrievability`.

This is **Phase 1 of 3** from `docs/superpowers/specs/2026-06-09-prompt-optimization-design.md`. Phases 2 (DSPy compile) and 3 (champion/challenger experiment) get their own plans after this lands.

---

## File Structure

**Create:**
- `backend/src/mnemonic/db/models/prompt_version.py` — `PromptVersion` ORM model (the registry).
- `backend/src/mnemonic/core/optimization/__init__.py` — package marker.
- `backend/src/mnemonic/core/optimization/reward.py` — pure reward math (`RewardConfig`, `SubsequentReview`, `RewardResult`, `compute_reward`).
- `backend/src/mnemonic/core/optimization/registry.py` — champion seeding/lookup (`ensure_champion_versions`, `get_champion`).
- `backend/src/mnemonic/core/optimization/labeling.py` — the labeling job (`run_labeling_job`, `LabelingReport`).
- `backend/src/mnemonic/cli/__init__.py` — package marker.
- `backend/src/mnemonic/cli/label.py` — `mnemonic-label` entrypoint (`main`).
- `backend/alembic/versions/prompt_opt_0002_phase1_attribution.py` — schema migration.
- `backend/tests/unit/test_reward.py`, `backend/tests/unit/test_registry.py`, `backend/tests/integration/test_labeling.py`, `backend/tests/integration/test_persist_training_example.py`.

**Modify:**
- `backend/src/mnemonic/db/models/training_example.py` — add `prompt_version_id`, `reward`, `maturity`, `finalized`.
- `backend/src/mnemonic/db/models/variation_meta.py` — add `prompt_version_id`, `arm`.
- `backend/src/mnemonic/db/models/__init__.py` — register `PromptVersion`.
- `backend/src/mnemonic/exceptions.py` — add `OptimizationError`, `InsufficientDataError`.
- `backend/src/mnemonic/config.py` — add `OptimizationConfig` and load `[optimization]`.
- `backend/src/mnemonic/llm/variation/writer.py` — extend `persist_variation` to record prompt version + unlabeled `TrainingExample`.
- `backend/pyproject.toml` — register the `mnemonic-label` console script.

All commands below assume working directory `backend/`.

---

### Task 1: `PromptVersion` model

**Files:**
- Create: `backend/src/mnemonic/db/models/prompt_version.py`
- Modify: `backend/src/mnemonic/db/models/__init__.py`
- Test: `backend/tests/unit/test_registry.py` (model smoke portion)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_registry.py`:

```python
"""Tests for the prompt-version registry model and seeding."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.db.models import Base, PromptVersion


def _memory_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_prompt_version_persists_with_defaults():
    engine = _memory_engine()
    with Session(engine) as s:
        s.add(
            PromptVersion(
                id="pv1",
                strategy="rephrase",
                version_no=0,
                instruction_text="seed text",
                demos="[]",
                status="champion",
                parent_version_id=None,
                compiled_from_n_examples=None,
                created_at=datetime(2026, 6, 9, 12, 0, 0),
            )
        )
        s.commit()
        row = s.get(PromptVersion, "pv1")
        assert row.strategy == "rephrase"
        assert row.version_no == 0
        assert row.status == "champion"
        assert row.demos == "[]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_registry.py::test_prompt_version_persists_with_defaults -v`
Expected: FAIL with `ImportError: cannot import name 'PromptVersion'`.

- [ ] **Step 3: Create the model**

Create `backend/src/mnemonic/db/models/prompt_version.py`:

```python
"""PromptVersion: a versioned, per-strategy variation prompt in the registry."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class PromptVersion(Base):
    __tablename__ = "prompt_version"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    demos: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String, nullable=False, default="challenger")
    parent_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    compiled_from_n_examples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

- [ ] **Step 4: Register the model**

In `backend/src/mnemonic/db/models/__init__.py`, add the import after the `llm_usage` import and add `"PromptVersion"` to `__all__`:

```python
from mnemonic.db.models.prompt_version import PromptVersion
```

Resulting `__all__` must include `"PromptVersion"` alongside the existing entries.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_registry.py::test_prompt_version_persists_with_defaults -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/db/models/prompt_version.py src/mnemonic/db/models/__init__.py tests/unit/test_registry.py
git commit -m "feat(optimization): add PromptVersion registry model"
```

---

### Task 2: Extend `TrainingExample` with label/reward columns

**Files:**
- Modify: `backend/src/mnemonic/db/models/training_example.py`
- Test: `backend/tests/integration/test_persist_training_example.py` (model portion)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_persist_training_example.py`:

```python
"""Tests for unlabeled TrainingExample creation and its new columns."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.db.models import Base, TrainingExample


def _memory_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_training_example_supports_unlabeled_state():
    engine = _memory_engine()
    with Session(engine) as s:
        s.add(
            TrainingExample(
                id="te1",
                card_id="c1",
                variation_id="v1",
                prompt_version_id="pv1",
                base_q="base front",
                base_a="base back",
                variation_q="vary front",
                variation_a="vary back",
                label=0,
                reward=None,
                maturity=0,
                finalized=False,
                rating=None,
                note_context=None,
                created_at=datetime(2026, 6, 9, 12, 0, 0),
            )
        )
        s.commit()
        row = s.get(TrainingExample, "te1")
        assert row.prompt_version_id == "pv1"
        assert row.reward is None
        assert row.maturity == 0
        assert row.finalized is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_persist_training_example.py::test_training_example_supports_unlabeled_state -v`
Expected: FAIL with `TypeError: 'prompt_version_id' is an invalid keyword argument for TrainingExample`.

- [ ] **Step 3: Add the columns**

In `backend/src/mnemonic/db/models/training_example.py`, change the import line and add four columns. Replace the import:

```python
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
```

Insert these columns immediately after the existing `variation_id` column declaration:

```python
    prompt_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
```

And insert these immediately after the existing `label` column declaration:

```python
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    maturity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_persist_training_example.py::test_training_example_supports_unlabeled_state -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/db/models/training_example.py tests/integration/test_persist_training_example.py
git commit -m "feat(optimization): add prompt_version_id, reward, maturity, finalized to TrainingExample"
```

---

### Task 3: Extend `VariationMeta` with prompt version + arm

**Files:**
- Modify: `backend/src/mnemonic/db/models/variation_meta.py`
- Test: `backend/tests/unit/test_registry.py` (add one test)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/unit/test_registry.py`:

```python
def test_variation_meta_has_prompt_version_and_arm():
    from mnemonic.db.models import VariationMeta

    engine = _memory_engine()
    with Session(engine) as s:
        s.add(
            VariationMeta(
                id="vm1",
                card_id="c1",
                strategy="rephrase",
                model="claude",
                generated_at=datetime(2026, 6, 9, 12, 0, 0),
                shown_count=1,
                helpful_count=0,
                content_hash="abc",
                note_path="note.md",
                prompt_version_id="pv1",
                arm="champion",
            )
        )
        s.commit()
        row = s.get(VariationMeta, "vm1")
        assert row.prompt_version_id == "pv1"
        assert row.arm == "champion"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_registry.py::test_variation_meta_has_prompt_version_and_arm -v`
Expected: FAIL with `TypeError: 'prompt_version_id' is an invalid keyword argument for VariationMeta`.

- [ ] **Step 3: Add the columns**

In `backend/src/mnemonic/db/models/variation_meta.py`, add after the existing `note_path` column:

```python
    prompt_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    arm: Mapped[str] = mapped_column(String, nullable=False, default="none")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_registry.py::test_variation_meta_has_prompt_version_and_arm -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/db/models/variation_meta.py tests/unit/test_registry.py
git commit -m "feat(optimization): add prompt_version_id and arm to VariationMeta"
```

---

### Task 4: Alembic migration (schema only)

**Files:**
- Create: `backend/alembic/versions/prompt_opt_0002_phase1_attribution.py`

The migration creates `prompt_version` and adds the new columns to `training_example` and `variation_meta`. SQLite supports `ADD COLUMN`, so `op.add_column` works directly; the downgrade uses `batch_alter_table` because SQLite cannot drop columns in place.

- [ ] **Step 1: Write the migration**

Create `backend/alembic/versions/prompt_opt_0002_phase1_attribution.py`:

```python
"""Phase 1 prompt-optimization: prompt_version table + attribution columns.

Revision ID: prompt_opt_0002
Revises: vault_storage_0001
Create Date: 2026-06-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "prompt_opt_0002"
down_revision = "vault_storage_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_version",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("strategy", sa.String, nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("instruction_text", sa.Text, nullable=False),
        sa.Column("demos", sa.Text, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="challenger"),
        sa.Column("parent_version_id", sa.String, nullable=True),
        sa.Column("compiled_from_n_examples", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_prompt_version_strategy", "prompt_version", ["strategy", "status"])

    op.add_column("training_example", sa.Column("prompt_version_id", sa.String, nullable=True))
    op.add_column("training_example", sa.Column("reward", sa.Float, nullable=True))
    op.add_column("training_example", sa.Column("maturity", sa.Integer, nullable=False, server_default="0"))
    op.add_column("training_example", sa.Column("finalized", sa.Boolean, nullable=False, server_default="0"))
    op.create_index("idx_training_finalized", "training_example", ["finalized"])

    op.add_column("variation_meta", sa.Column("prompt_version_id", sa.String, nullable=True))
    op.add_column("variation_meta", sa.Column("arm", sa.String, nullable=False, server_default="none"))


def downgrade() -> None:
    op.drop_index("idx_training_finalized", table_name="training_example")
    with op.batch_alter_table("variation_meta") as batch:
        batch.drop_column("arm")
        batch.drop_column("prompt_version_id")
    with op.batch_alter_table("training_example") as batch:
        batch.drop_column("finalized")
        batch.drop_column("maturity")
        batch.drop_column("reward")
        batch.drop_column("prompt_version_id")
    op.drop_index("idx_prompt_version_strategy", table_name="prompt_version")
    op.drop_table("prompt_version")
```

- [ ] **Step 2: Apply the migration against a scratch DB to verify it runs**

Run:
```bash
uv run alembic -x db_url=sqlite:////tmp/mnemonic_phase1_check.sqlite upgrade head
```
Expected: alembic logs `Running upgrade vault_storage_0001 -> prompt_opt_0002`. No error.

> Note: if `alembic/env.py` does not read the `-x db_url` override, instead point the configured DB at a scratch path per the project's existing migration docs (`docs/source/developer/migrations.md`) and run `uv run alembic upgrade head`. The goal of this step is only to confirm `upgrade()`/`downgrade()` execute cleanly.

- [ ] **Step 3: Verify downgrade runs**

Run:
```bash
uv run alembic -x db_url=sqlite:////tmp/mnemonic_phase1_check.sqlite downgrade -1
```
Expected: `Running downgrade prompt_opt_0002 -> vault_storage_0001`. No error. Then delete the scratch DB: `rm -f /tmp/mnemonic_phase1_check.sqlite`.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/prompt_opt_0002_phase1_attribution.py
git commit -m "feat(optimization): phase 1 migration (prompt_version + attribution columns)"
```

---

### Task 5: Optimization exceptions

**Files:**
- Modify: `backend/src/mnemonic/exceptions.py`
- Test: `backend/tests/unit/test_optimization_exceptions.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_optimization_exceptions.py`:

```python
"""Tests for optimization exception hierarchy."""

from mnemonic.exceptions import (
    InsufficientDataError,
    MnemonicError,
    OptimizationError,
)


def test_optimization_errors_inherit_from_mnemonic_error():
    assert issubclass(OptimizationError, MnemonicError)
    assert issubclass(InsufficientDataError, OptimizationError)


def test_insufficient_data_error_message_names_shortfall():
    err = InsufficientDataError("rephrase", have=3, need=20)
    msg = str(err)
    assert "rephrase" in msg
    assert "3" in msg
    assert "20" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_optimization_exceptions.py -v`
Expected: FAIL with `ImportError: cannot import name 'OptimizationError'`.

- [ ] **Step 3: Add the exceptions**

Append to `backend/src/mnemonic/exceptions.py`:

```python
# Optimization errors
class OptimizationError(MnemonicError):
    """Base class for prompt-optimization failures."""

    pass


class InsufficientDataError(OptimizationError):
    """Not enough labeled examples to perform an optimization step."""

    def __init__(self, strategy: str, have: int, need: int) -> None:
        """Initialize insufficient-data error.

        Args:
            strategy: The strategy whose trainset is too small.
            have: Number of usable examples currently available.
            need: Minimum number of examples required.
        """
        self.strategy = strategy
        self.have = have
        self.need = need
        super().__init__(
            f"Not enough labeled examples for strategy '{strategy}': "
            f"have {have}, need {need}. Keep reviewing to accumulate more, "
            "or lower min_examples_to_compile in [optimization] config."
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_optimization_exceptions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/exceptions.py tests/unit/test_optimization_exceptions.py
git commit -m "feat(optimization): add OptimizationError and InsufficientDataError"
```

---

### Task 6: `OptimizationConfig` and `[optimization]` loading

**Files:**
- Modify: `backend/src/mnemonic/config.py`
- Test: `backend/tests/unit/test_optimization_config.py`

The `[optimization]` section is **optional**; absent keys fall back to defaults so existing configs keep working.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_optimization_config.py`:

```python
"""Tests for optimization config loading."""

from __future__ import annotations

from pathlib import Path

from mnemonic.config import OptimizationConfig, load_config


def _write_config(tmp_path: Path, vault_path: Path, extra: str = "") -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f"""
[vault]
path = "{vault_path}"

[llm]
api_key_env = "KEY"
model_default = "m"
model_rephrase = "m"
model_offline = "m"
[llm.budget]
daily_cents = 100
monthly_cents = 1000

[defaults]
variation_enabled = true
variation_frequency = 0.3
leech_threshold = 8
daily_review_limit = 100
daily_new_limit = 20
{extra}
"""
    )
    return cfg


def test_optimization_defaults_when_section_absent(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg_path = _write_config(tmp_path, vault)
    config = load_config(user_global_path=cfg_path)
    assert isinstance(config.optimization, OptimizationConfig)
    assert config.optimization.reward_decay_gamma == 0.5
    assert config.optimization.reward_window_k == 3


def test_optimization_overrides_from_section(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    extra = "[optimization]\nreward_decay_gamma = 0.7\nreward_window_k = 5\n"
    cfg_path = _write_config(tmp_path, vault, extra)
    config = load_config(user_global_path=cfg_path)
    assert config.optimization.reward_decay_gamma == 0.7
    assert config.optimization.reward_window_k == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_optimization_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'OptimizationConfig'`.

- [ ] **Step 3: Add the config dataclass and loading**

In `backend/src/mnemonic/config.py`:

Add the import at the top (after `from pathlib import Path`):

```python
from dataclasses import dataclass, field
```

(Replace the existing `from dataclasses import dataclass` line with the one above.)

Add this dataclass after `DefaultsConfig`:

```python
@dataclass(frozen=True)
class OptimizationConfig:
    reward_decay_gamma: float = 0.5
    reward_window_k: int = 3
    min_interval_hours: float = 20.0
    demo_margin_delta: float = 0.1
```

Add a field to the `Config` dataclass (it must be last because it has a default):

```python
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
```

In `load_config`, after the `defaults_section = merged["defaults"]` line, add:

```python
    opt_section = merged.get("optimization", {})
    optimization = OptimizationConfig(
        reward_decay_gamma=opt_section.get("reward_decay_gamma", 0.5),
        reward_window_k=opt_section.get("reward_window_k", 3),
        min_interval_hours=opt_section.get("min_interval_hours", 20.0),
        demo_margin_delta=opt_section.get("demo_margin_delta", 0.1),
    )
```

And pass `optimization=optimization` as the final argument to the `Config(...)` constructor.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_optimization_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/config.py tests/unit/test_optimization_config.py
git commit -m "feat(optimization): add OptimizationConfig with [optimization] loading"
```

---

### Task 7: Pure reward math

**Files:**
- Create: `backend/src/mnemonic/core/optimization/__init__.py`
- Create: `backend/src/mnemonic/core/optimization/reward.py`
- Test: `backend/tests/unit/test_reward.py`

This is the heart of Phase 1 — pure functions, target 95% coverage. `compute_reward` receives already-prepared `SubsequentReview` objects (success flag + predicted retrievability); the labeling job (Task 9... see Task 8) is responsible for computing `predicted_retrievability` via FSRS. This keeps the math pure and trivially testable.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_reward.py`:

```python
"""Tests for the calibration-surprise reward with geometric decay."""

from __future__ import annotations

import math

from mnemonic.core.optimization.reward import (
    RewardConfig,
    SubsequentReview,
    compute_reward,
)


def test_passing_an_unexpected_card_scores_positive():
    # FSRS predicted 30% recall; the user recalled it -> positive surprise.
    reviews = [SubsequentReview(success=True, predicted_retrievability=0.3)]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert math.isclose(result.reward, 0.7)
    assert result.maturity == 1
    assert result.finalized is False  # only 1 of 3 reviews landed


def test_failing_an_easy_card_scores_negative():
    reviews = [SubsequentReview(success=False, predicted_retrievability=0.9)]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert math.isclose(result.reward, -0.9)


def test_geometric_decay_weights_later_reviews_less():
    # surprises: +0.5 (w=1), then -0.5 (w=0.5). Weighted mean:
    # (1*0.5 + 0.5*-0.5) / (1 + 0.5) = 0.25 / 1.5
    reviews = [
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=False, predicted_retrievability=0.5),
    ]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert math.isclose(result.reward, 0.25 / 1.5)
    assert result.maturity == 2


def test_window_caps_at_k_and_finalizes():
    reviews = [
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=True, predicted_retrievability=0.5),  # ignored
    ]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert result.maturity == 3
    assert result.finalized is True


def test_card_retired_finalizes_even_when_immature():
    reviews = [SubsequentReview(success=True, predicted_retrievability=0.5)]
    result = compute_reward(
        reviews, RewardConfig(gamma=0.5, window_k=3), card_retired=True
    )
    assert result.maturity == 1
    assert result.finalized is True


def test_empty_reviews_returns_no_signal():
    result = compute_reward([], RewardConfig(gamma=0.5, window_k=3))
    assert result.reward is None
    assert result.maturity == 0
    assert result.finalized is False


def test_empty_reviews_with_retired_card_finalizes_with_no_reward():
    result = compute_reward([], RewardConfig(gamma=0.5, window_k=3), card_retired=True)
    assert result.reward is None
    assert result.maturity == 0
    assert result.finalized is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_reward.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization'`.

- [ ] **Step 3: Create the package marker and reward module**

Create `backend/src/mnemonic/core/optimization/__init__.py`:

```python
"""Prompt-optimization core: reward math, registry, and labeling."""
```

Create `backend/src/mnemonic/core/optimization/reward.py`:

```python
"""Calibration-surprise reward with geometric decay over subsequent reviews.

The reward for a variation is how much the base card's later reviews beat the
FSRS-predicted retrievability, weighted so the next review dominates and later
reviews contribute a decayed durability tail. See
docs/superpowers/specs/2026-06-09-prompt-optimization-design.md (Phase 1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardConfig:
    """Parameters controlling the reward window.

    Attributes:
        gamma: Geometric decay applied to each later review (0 < gamma <= 1).
        window_k: Maximum number of subsequent reviews to consider.
        min_interval_hours: Reviews closer than this to their predecessor are
            excluded upstream (same-session cramming); unused here but kept for
            documentation alongside the other reward parameters.
        demo_margin_delta: Reward above which an example is marked demo-worthy
            (used by the labeling job, not by compute_reward).
    """

    gamma: float = 0.5
    window_k: int = 3
    min_interval_hours: float = 20.0
    demo_margin_delta: float = 0.1


@dataclass(frozen=True)
class SubsequentReview:
    """One review that followed the shown variation.

    Attributes:
        success: True if the user recalled the card (rating >= 2).
        predicted_retrievability: FSRS R at the moment of this review (0..1).
    """

    success: bool
    predicted_retrievability: float


@dataclass(frozen=True)
class RewardResult:
    """Outcome of a reward computation.

    Attributes:
        reward: Weighted calibration surprise, or None when no usable reviews
            were available (we never fabricate a signal).
        maturity: Number of reviews that contributed (0..window_k).
        finalized: True once the window is full or the card was retired.
    """

    reward: float | None
    maturity: int
    finalized: bool


def compute_reward(
    reviews: list[SubsequentReview],
    config: RewardConfig,
    *,
    card_retired: bool = False,
) -> RewardResult:
    """Compute the maturity-weighted calibration-surprise reward.

    Args:
        reviews: Subsequent reviews of the base card, in chronological order,
            already filtered for same-session cramming. Only the first
            ``config.window_k`` are used.
        config: Reward window parameters.
        card_retired: True if the card was suspended/deleted, which finalizes
            the label even when the window is not full.

    Returns:
        A RewardResult. ``reward`` is None when there are no usable reviews.
    """
    used = reviews[: config.window_k]
    if not used:
        return RewardResult(reward=None, maturity=0, finalized=card_retired)

    numerator = 0.0
    denominator = 0.0
    for index, review in enumerate(used):
        weight = config.gamma**index
        surprise = (1.0 if review.success else 0.0) - review.predicted_retrievability
        numerator += weight * surprise
        denominator += weight

    reward = numerator / denominator
    maturity = len(used)
    finalized = maturity >= config.window_k or card_retired
    return RewardResult(reward=reward, maturity=maturity, finalized=finalized)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_reward.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/__init__.py src/mnemonic/core/optimization/reward.py tests/unit/test_reward.py
git commit -m "feat(optimization): pure calibration-surprise reward with geometric decay"
```

---

### Task 8: Champion registry seeding and lookup

**Files:**
- Create: `backend/src/mnemonic/core/optimization/registry.py`
- Test: `backend/tests/unit/test_registry.py` (add seeding tests)

`ensure_champion_versions` seeds one `version_no=0` champion per strategy from the on-disk strategy markdown, and is idempotent (skips strategies that already have any version). `get_champion` returns the current champion or fails loudly.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/unit/test_registry.py`:

```python
def test_ensure_champion_versions_seeds_each_strategy(tmp_path):
    from mnemonic.core.optimization.registry import ensure_champion_versions

    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "strategies").mkdir(parents=True)
    for strat in ("rephrase", "specialize", "generalize"):
        (prompts_dir / "strategies" / f"{strat}.md").write_text(f"{strat} instructions")

    engine = _memory_engine()
    with Session(engine) as s:
        created = ensure_champion_versions(
            s, prompts_dir=prompts_dir, now=datetime(2026, 6, 9, 12, 0, 0)
        )
        s.commit()
        assert {pv.strategy for pv in created} == {"rephrase", "specialize", "generalize"}
        champ = s.query(PromptVersion).filter_by(strategy="rephrase").one()
        assert champ.version_no == 0
        assert champ.status == "champion"
        assert champ.instruction_text == "rephrase instructions"


def test_ensure_champion_versions_is_idempotent(tmp_path):
    from mnemonic.core.optimization.registry import ensure_champion_versions

    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "strategies").mkdir(parents=True)
    for strat in ("rephrase", "specialize", "generalize"):
        (prompts_dir / "strategies" / f"{strat}.md").write_text(f"{strat} v0")

    engine = _memory_engine()
    with Session(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=datetime(2026, 6, 9))
        s.commit()
        second = ensure_champion_versions(
            s, prompts_dir=prompts_dir, now=datetime(2026, 6, 10)
        )
        s.commit()
        assert second == []
        assert s.query(PromptVersion).count() == 3


def test_get_champion_returns_current_champion(tmp_path):
    from mnemonic.core.optimization.registry import (
        ensure_champion_versions,
        get_champion,
    )

    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "strategies").mkdir(parents=True)
    (prompts_dir / "strategies" / "rephrase.md").write_text("rephrase v0")

    engine = _memory_engine()
    with Session(engine) as s:
        ensure_champion_versions(
            s, prompts_dir=prompts_dir, strategies=("rephrase",), now=datetime(2026, 6, 9)
        )
        s.commit()
        champ = get_champion(s, "rephrase")
        assert champ.strategy == "rephrase"
        assert champ.status == "champion"


def test_get_champion_without_seed_fails_loudly():
    from mnemonic.core.optimization.registry import get_champion
    from mnemonic.exceptions import OptimizationError

    engine = _memory_engine()
    with Session(engine) as s:
        try:
            get_champion(s, "rephrase")
            assert False, "expected OptimizationError"
        except OptimizationError as err:
            assert "rephrase" in str(err)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: the four new tests FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.registry'`.

- [ ] **Step 3: Create the registry module**

Create `backend/src/mnemonic/core/optimization/registry.py`:

```python
"""Champion prompt-version seeding and lookup."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemonic.db.models import PromptVersion
from mnemonic.exceptions import OptimizationError

DEFAULT_STRATEGIES = ("rephrase", "specialize", "generalize")


def ensure_champion_versions(
    session: Session,
    *,
    prompts_dir: Path,
    now: datetime,
    strategies: tuple[str, ...] = DEFAULT_STRATEGIES,
) -> list[PromptVersion]:
    """Seed a version_no=0 champion for each strategy that has none yet.

    Idempotent: strategies that already have any PromptVersion row are skipped.

    Args:
        session: Active SQLAlchemy session.
        prompts_dir: Directory containing ``strategies/<name>.md`` seed files.
        now: Timestamp to stamp on created rows.
        strategies: Strategy names to seed.

    Returns:
        The list of newly created PromptVersion rows (empty if all existed).

    Raises:
        OptimizationError: If a strategy's seed markdown file is missing.
    """
    created: list[PromptVersion] = []
    for strategy in strategies:
        existing = session.execute(
            select(PromptVersion).where(PromptVersion.strategy == strategy).limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            continue

        seed_path = prompts_dir / "strategies" / f"{strategy}.md"
        if not seed_path.exists():
            raise OptimizationError(
                f"Cannot seed champion for strategy '{strategy}': "
                f"seed file not found at {seed_path}."
            )

        version = PromptVersion(
            id=uuid.uuid4().hex,
            strategy=strategy,
            version_no=0,
            instruction_text=seed_path.read_text(),
            demos="[]",
            status="champion",
            parent_version_id=None,
            compiled_from_n_examples=None,
            created_at=now,
        )
        session.add(version)
        created.append(version)
    return created


def get_champion(session: Session, strategy: str) -> PromptVersion:
    """Return the current champion PromptVersion for a strategy.

    Args:
        session: Active SQLAlchemy session.
        strategy: Strategy name.

    Returns:
        The champion PromptVersion.

    Raises:
        OptimizationError: If no champion exists for the strategy.
    """
    champion = session.execute(
        select(PromptVersion).where(
            PromptVersion.strategy == strategy,
            PromptVersion.status == "champion",
        )
    ).scalar_one_or_none()
    if champion is None:
        raise OptimizationError(
            f"No champion prompt version for strategy '{strategy}'. "
            "Run the labeling job once to seed champions from the on-disk prompts."
        )
    return champion
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/registry.py tests/unit/test_registry.py
git commit -m "feat(optimization): champion seeding and lookup in registry"
```

---

### Task 9: Extend `persist_variation` to record provenance + unlabeled example

**Files:**
- Modify: `backend/src/mnemonic/llm/variation/writer.py`
- Test: `backend/tests/integration/test_persist_training_example.py` (add a test)

`persist_variation` gains four keyword args: `prompt_version_id`, `arm`, `base_q`, `base_a`. It stamps `VariationMeta.prompt_version_id`/`arm` and inserts an unlabeled `TrainingExample` capturing the input/output text. (`note_context` is already available at call sites that render the prompt; pass it through.)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_persist_training_example.py`:

```python
def test_persist_variation_writes_unlabeled_training_example(tmp_path):
    from mnemonic.db.models import VariationMeta
    from mnemonic.db.sqlite import create_engine
    from mnemonic.llm.variation.generator import GeneratedVariation
    from mnemonic.llm.variation.writer import persist_variation

    vault = tmp_path / "vault"
    note = vault / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Card\n\nfront\n\n## Answer\n\nback\n")

    engine = create_engine(tmp_path / "state.sqlite")
    Base.metadata.create_all(engine)

    variation = GeneratedVariation(
        strategy="rephrase",
        question="reworded?",
        answer="same answer",
        model="claude",
        cost_millicents=10,
        raw_response="Q: reworded?\nA: same answer",
        input_tokens=5,
        output_tokens=5,
    )

    variation_id = persist_variation(
        engine=engine,
        note_path=note,
        card_id="c1",
        variation=variation,
        vault_root=vault,
        prompt_version_id="pv1",
        arm="champion",
        base_q="front",
        base_a="back",
        note_context="some context",
    )

    with Session(engine) as s:
        te = s.query(TrainingExample).filter_by(variation_id=variation_id).one()
        assert te.prompt_version_id == "pv1"
        assert te.reward is None
        assert te.finalized is False
        assert te.base_q == "front"
        assert te.variation_q == "reworded?"
        vm = s.query(VariationMeta).filter_by(id=variation_id).one()
        assert vm.prompt_version_id == "pv1"
        assert vm.arm == "champion"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_persist_training_example.py::test_persist_variation_writes_unlabeled_training_example -v`
Expected: FAIL with `TypeError: persist_variation() got an unexpected keyword argument 'prompt_version_id'`.

- [ ] **Step 3: Update `persist_variation`**

In `backend/src/mnemonic/llm/variation/writer.py`:

Add to the imports at the top:

```python
from mnemonic.db.models import LLMUsage, TrainingExample, VariationMeta
```

Change the `persist_variation` signature to add the new keyword-only args (after `vault_root`):

```python
def persist_variation(
    *,
    engine: Engine,
    note_path: Path,
    card_id: str,
    variation: GeneratedVariation,
    vault_root: Path,
    prompt_version_id: str,
    arm: str = "none",
    base_q: str,
    base_a: str,
    note_context: str | None = None,
) -> str:
```

In the `VariationMeta(...)` construction inside `session_scope`, add the two new fields:

```python
            prompt_version_id=prompt_version_id,
            arm=arm,
```

Immediately after the `s.add(LLMUsage(...))` block (still inside the `with session_scope` block), add the unlabeled training example:

```python
        s.add(TrainingExample(
            id=uuid.uuid4().hex,
            card_id=card_id,
            variation_id=variation_id,
            prompt_version_id=prompt_version_id,
            base_q=base_q,
            base_a=base_a,
            variation_q=variation.question,
            variation_a=variation.answer,
            label=0,
            reward=None,
            maturity=0,
            finalized=False,
            rating=None,
            note_context=note_context,
            created_at=now,
        ))
```

Update the docstring's Args section to document `prompt_version_id`, `arm`, `base_q`, `base_a`, and `note_context`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_persist_training_example.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/llm/variation/writer.py tests/integration/test_persist_training_example.py
git commit -m "feat(optimization): record prompt version and unlabeled TrainingExample on persist"
```

---

### Task 10: The labeling job

**Files:**
- Create: `backend/src/mnemonic/core/optimization/labeling.py`
- Test: `backend/tests/integration/test_labeling.py`

The job, for each non-finalized `TrainingExample` that has a `variation_id`:
1. Finds the **anchor** review (the `ReviewLog` whose `variation_id` matches — i.e. the review where the variation was shown). If none yet, leaves the example pending.
2. Collects subsequent `ReviewLog` rows for the same card with `review_time` after the anchor, in order.
3. Excludes any review whose gap from its predecessor is below `min_interval_hours` (same-session cramming).
4. Computes each kept review's `predicted_retrievability` via `calculate_retrievability(stability_before, elapsed_days)`; reviews with missing/zero `stability_before` are skipped (cannot form a prediction — no fabricated signal).
5. Checks `SchedulingState.suspended` to set `card_retired`.
6. Calls `compute_reward`, then upserts `reward`, `maturity`, `finalized`, and `label = int(reward > demo_margin_delta)` onto the example.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/integration/test_labeling.py`:

```python
"""Integration tests for the labeling job."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.labeling import run_labeling_job
from mnemonic.db.models import (
    Base,
    ReviewLog,
    SchedulingState,
    TrainingExample,
)


def _engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def _unlabeled_example(variation_id: str = "v1", card_id: str = "c1") -> TrainingExample:
    return TrainingExample(
        id="te-" + variation_id,
        card_id=card_id,
        variation_id=variation_id,
        prompt_version_id="pv1",
        base_q="q",
        base_a="a",
        variation_q="vq",
        variation_a="va",
        label=0,
        reward=None,
        maturity=0,
        finalized=False,
        rating=None,
        note_context=None,
        created_at=datetime(2026, 6, 1),
    )


def _review(card_id, variation_id, when, rating, stability_before):
    return ReviewLog(
        id=f"r-{when.isoformat()}",
        card_id=card_id,
        rating=rating,
        response_time_ms=1000,
        review_time=when,
        state_before="review",
        state_after="review",
        stability_before=stability_before,
        stability_after=stability_before,
        difficulty_before=5.0,
        difficulty_after=5.0,
        variation_id=variation_id,
        variation_helpful=None,
    )


def test_labels_example_after_next_review_lands():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        # Anchor review (variation shown), then a next review 5 days later.
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        s.add(_review("c1", None, t0 + timedelta(days=5), rating=3, stability_before=10.0))
        s.commit()

        report = run_labeling_job(engine, OptimizationConfig())

        te = s.get(TrainingExample, "te-v1")
        assert te.reward is not None
        assert te.maturity == 1
        assert te.finalized is False
        assert report.labeled == 1


def test_example_without_anchor_review_stays_pending():
    engine = _engine()
    with Session(engine) as s:
        s.add(_unlabeled_example())  # no ReviewLog with variation_id="v1"
        s.commit()

        report = run_labeling_job(engine, OptimizationConfig())

        te = s.get(TrainingExample, "te-v1")
        assert te.reward is None
        assert te.maturity == 0
        assert te.finalized is False
        assert report.pending == 1


def test_same_day_cram_review_is_excluded():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        # Only 2 hours later -> below min_interval_hours -> excluded.
        s.add(_review("c1", None, t0 + timedelta(hours=2), rating=1, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig(min_interval_hours=20.0))

        te = s.get(TrainingExample, "te-v1")
        # No usable subsequent reviews -> stays pending (reward None, maturity 0).
        assert te.maturity == 0
        assert te.reward is None


def test_finalizes_when_window_full_and_sets_demo_label():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        # Three later reviews, all passed against low predicted retrievability
        # (long gaps -> low R_pred -> high positive surprise).
        for i, days in enumerate((30, 60, 90), start=1):
            s.add(_review("c1", None, t0 + timedelta(days=days), rating=3, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig(demo_margin_delta=0.1))

        te = s.get(TrainingExample, "te-v1")
        assert te.maturity == 3
        assert te.finalized is True
        assert te.reward > 0.1
        assert te.label == 1


def test_suspended_card_finalizes_immature_example():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        s.add(_review("c1", None, t0 + timedelta(days=5), rating=3, stability_before=10.0))
        s.add(SchedulingState(card_id="c1", suspended=1))
        s.commit()

        run_labeling_job(engine, OptimizationConfig())

        te = s.get(TrainingExample, "te-v1")
        assert te.maturity == 1
        assert te.finalized is True


def test_job_is_idempotent_on_finalized_examples():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        for days in (30, 60, 90):
            s.add(_review("c1", None, t0 + timedelta(days=days), rating=3, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig())
        second = run_labeling_job(engine, OptimizationConfig())
        # Finalized example is not revisited.
        assert second.labeled == 0
        assert second.finalized_skipped == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_labeling.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.optimization.labeling'`.

- [ ] **Step 3: Create the labeling module**

Create `backend/src/mnemonic/core/optimization/labeling.py`:

```python
"""The labeling job: turn shown variations into rewarded TrainingExamples."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.fsrs.algorithm import calculate_retrievability
from mnemonic.core.optimization.reward import (
    RewardConfig,
    SubsequentReview,
    compute_reward,
)
from mnemonic.db.models import ReviewLog, SchedulingState, TrainingExample
from mnemonic.db.sqlite import session_scope


@dataclass(frozen=True)
class LabelingReport:
    """Summary of one labeling run.

    Attributes:
        labeled: Examples that received or updated a reward this run.
        pending: Examples left unlabeled (no anchor / no usable reviews yet).
        finalized_skipped: Already-finalized examples that were not revisited.
    """

    labeled: int = 0
    pending: int = 0
    finalized_skipped: int = 0


def _to_reward_config(config: OptimizationConfig) -> RewardConfig:
    return RewardConfig(
        gamma=config.reward_decay_gamma,
        window_k=config.reward_window_k,
        min_interval_hours=config.min_interval_hours,
        demo_margin_delta=config.demo_margin_delta,
    )


def _subsequent_reviews(
    session: Session,
    *,
    card_id: str,
    anchor_time: datetime,
    config: OptimizationConfig,
) -> list[SubsequentReview]:
    """Build the FSRS-adjusted subsequent-review list for a card."""
    rows = session.execute(
        select(ReviewLog)
        .where(ReviewLog.card_id == card_id, ReviewLog.review_time > anchor_time)
        .order_by(ReviewLog.review_time.asc())
    ).scalars().all()

    result: list[SubsequentReview] = []
    prev_time = anchor_time
    for row in rows:
        gap_hours = (row.review_time - prev_time).total_seconds() / 3600.0
        if gap_hours < config.min_interval_hours:
            # Same-session cramming: skip, and do not advance prev_time so the
            # next genuine review is measured from the anchor/last kept review.
            continue
        if not row.stability_before or row.stability_before <= 0:
            # Cannot form an FSRS prediction; exclude rather than fabricate.
            prev_time = row.review_time
            continue
        elapsed_days = (row.review_time - prev_time).total_seconds() / 86400.0
        r_pred = calculate_retrievability(
            stability=row.stability_before, elapsed_days=elapsed_days
        )
        result.append(
            SubsequentReview(success=row.rating >= 2, predicted_retrievability=r_pred)
        )
        prev_time = row.review_time
    return result


def run_labeling_job(engine: Engine, config: OptimizationConfig) -> LabelingReport:
    """Label all non-finalized TrainingExamples whose reviews have landed.

    Idempotent: finalized examples are never revisited; non-finalized ones are
    re-evaluated each run as more reviews accrue.

    Args:
        engine: SQLAlchemy engine for the state database.
        config: Optimization configuration (reward window parameters).

    Returns:
        A LabelingReport summarizing the run.
    """
    reward_config = _to_reward_config(config)
    labeled = pending = finalized_skipped = 0

    with session_scope(engine) as session:
        examples = session.execute(
            select(TrainingExample).where(TrainingExample.variation_id.is_not(None))
        ).scalars().all()

        for example in examples:
            if example.finalized:
                finalized_skipped += 1
                continue

            anchor = session.execute(
                select(ReviewLog)
                .where(ReviewLog.variation_id == example.variation_id)
                .order_by(ReviewLog.review_time.asc())
                .limit(1)
            ).scalar_one_or_none()
            if anchor is None:
                pending += 1
                continue

            scheduling = session.get(SchedulingState, example.card_id)
            card_retired = bool(scheduling and scheduling.suspended)

            reviews = _subsequent_reviews(
                session,
                card_id=example.card_id,
                anchor_time=anchor.review_time,
                config=config,
            )
            result = compute_reward(reviews, reward_config, card_retired=card_retired)

            if result.reward is None and not result.finalized:
                pending += 1
                continue

            example.reward = result.reward
            example.maturity = result.maturity
            example.finalized = result.finalized
            example.label = int(
                result.reward is not None and result.reward > config.demo_margin_delta
            )
            labeled += 1

    return LabelingReport(
        labeled=labeled, pending=pending, finalized_skipped=finalized_skipped
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_labeling.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/labeling.py tests/integration/test_labeling.py
git commit -m "feat(optimization): labeling job computing maturing FSRS-adjusted rewards"
```

---

### Task 11: `mnemonic-label` CLI entrypoint

**Files:**
- Create: `backend/src/mnemonic/cli/__init__.py`
- Create: `backend/src/mnemonic/cli/label.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/integration/test_cli_label.py`

The command loads config, opens the state DB, seeds champions (idempotent), runs the labeling job, and prints a one-line summary. It returns a process exit code.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_cli_label.py`:

```python
"""Integration test for the mnemonic-label CLI."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session

from mnemonic.cli.label import run_labeling
from mnemonic.config import OptimizationConfig
from mnemonic.db.models import Base, PromptVersion


def test_run_labeling_seeds_champions_and_reports(tmp_path):
    # Real prompts dir from the package so seeding finds the strategy files.
    from mnemonic.llm.prompts import variation as variation_pkg
    from pathlib import Path

    prompts_dir = Path(variation_pkg.__file__).parent

    db_path = tmp_path / "state.sqlite"
    engine = sa_create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    engine.dispose()

    report = run_labeling(
        db_path=db_path,
        prompts_dir=prompts_dir,
        config=OptimizationConfig(),
        now=datetime(2026, 6, 9, 12, 0, 0),
    )

    assert report.labeled == 0  # no variations yet
    check_engine = sa_create_engine(f"sqlite:///{db_path}", future=True)
    with Session(check_engine) as s:
        assert s.query(PromptVersion).count() == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_cli_label.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.cli'`.

- [ ] **Step 3: Create the CLI package and module**

Create `backend/src/mnemonic/cli/__init__.py`:

```python
"""Command-line entrypoints for Mnemonic maintenance jobs."""
```

Create `backend/src/mnemonic/cli/label.py`:

```python
"""`mnemonic-label`: seed champions and run the variation labeling job."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from mnemonic.config import OptimizationConfig, load_config
from mnemonic.core.optimization.labeling import LabelingReport, run_labeling_job
from mnemonic.core.optimization.registry import ensure_champion_versions
from mnemonic.db.sqlite import create_engine, session_scope


def _default_prompts_dir() -> Path:
    from mnemonic.llm.prompts import variation as variation_pkg

    return Path(variation_pkg.__file__).parent


def run_labeling(
    *,
    db_path: Path,
    prompts_dir: Path,
    config: OptimizationConfig,
    now: datetime,
) -> LabelingReport:
    """Seed champions (idempotent) and run the labeling job.

    Args:
        db_path: Path to the SQLite state database.
        prompts_dir: Directory containing ``strategies/<name>.md`` seed files.
        config: Optimization configuration.
        now: Timestamp used when seeding champion versions.

    Returns:
        The LabelingReport from the run.
    """
    engine = create_engine(db_path)
    with session_scope(engine) as session:
        ensure_champion_versions(session, prompts_dir=prompts_dir, now=now)
    return run_labeling_job(engine, config)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-label",
        description="Compute durability rewards for shown variations.",
    )
    parser.parse_args(argv)

    config = load_config()
    db_path = config.vault.path / ".mnemonic" / "state.sqlite"
    report = run_labeling(
        db_path=db_path,
        prompts_dir=_default_prompts_dir(),
        config=config.optimization,
        now=datetime.now(),
    )
    print(
        f"labeled={report.labeled} pending={report.pending} "
        f"finalized_skipped={report.finalized_skipped}"
    )
    return 0
```

- [ ] **Step 4: Register the console script**

In `backend/pyproject.toml`, add a `[project.scripts]` table (place it immediately after the `dependencies = [...]` array's closing bracket, before any `[tool.*]` sections):

```toml
[project.scripts]
mnemonic-label = "mnemonic.cli.label:main"
```

Then re-sync so the entrypoint installs: `uv sync`.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_cli_label.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/cli/__init__.py src/mnemonic/cli/label.py pyproject.toml tests/integration/test_cli_label.py
git commit -m "feat(optimization): mnemonic-label CLI to seed champions and run labeling"
```

---

### Task 12: Developer docs + full verification

**Files:**
- Create: `backend/../docs/source/developer/prompt-optimization.md` (i.e. `docs/source/developer/prompt-optimization.md`)
- Modify: none (code complete)

- [ ] **Step 1: Write the developer doc**

Create `docs/source/developer/prompt-optimization.md`:

```markdown
# Prompt Optimization — Phase 1 (Attribution & Labeling)

Phase 1 records which prompt version produced each variation and scores how well
that variation helped the user remember the underlying card.

## Data model

- `prompt_version` — the registry. One `version_no=0` champion per strategy is
  seeded from the on-disk `llm/prompts/variation/strategies/<name>.md` files.
- `training_example` — extended with `prompt_version_id`, `reward` (nullable),
  `maturity`, and `finalized`. A row is created **unlabeled** when a variation is
  persisted; the labeling job fills in the reward later.
- `variation_meta` — extended with `prompt_version_id` and `arm`.

## Reward

`reward = Σ γ^(k-1) · (success(t+k) − R_pred(t+k)) / Σ γ^(k-1)` over up to
`reward_window_k` subsequent reviews. It is the FSRS *calibration surprise*:
recalling a card the scheduler expected you to fail scores positive. Labels mature
as later reviews arrive and finalize at the window cap or when the card is
suspended. Same-session cramming (gap below `min_interval_hours`) is excluded, and
reviews without a usable `stability_before` are skipped rather than guessed.

## Running the job

```bash
uv run mnemonic-label
```

Seeds champions (idempotent) and prints `labeled=… pending=… finalized_skipped=…`.

## Configuration (`[optimization]`)

| key | default | meaning |
|---|---|---|
| `reward_decay_gamma` | 0.5 | γ decay per later review |
| `reward_window_k` | 3 | max subsequent reviews scored |
| `min_interval_hours` | 20.0 | same-session cramming exclusion |
| `demo_margin_delta` | 0.1 | reward above which `label = 1` (demo-worthy) |
```

- [ ] **Step 2: Run the full backend test suite with coverage**

Run: `uv run pytest --cov=mnemonic --cov-report=term-missing`
Expected: all tests pass; `mnemonic/core/optimization/reward.py` at or near 100%, `core/` overall ≥ 95%.

- [ ] **Step 3: Lint, format, type-check**

Run:
```bash
uv run ruff check src tests
uv run black --check src tests
uv run mypy src
```
Expected: no errors. Fix any reported issues, then re-run.

- [ ] **Step 4: Commit**

```bash
git add docs/source/developer/prompt-optimization.md
git commit -m "docs(optimization): phase 1 attribution & labeling developer guide"
```

---

## Self-Review (completed during planning)

**Spec coverage (Phase 1 sections of the design doc):**
- Prompt registry (`prompt_version`, v0 seed champion) → Tasks 1, 4, 8.
- `TrainingExample`/`VariationMeta` extensions → Tasks 2, 3, 4.
- Reward formula (calibration surprise, γ decay, K window) → Task 7.
- Contamination handling (decay dominates, t+1 clean) → encoded in Task 7 weights; documented in Task 12.
- Progressive/maturing labels, idempotent upsert → Tasks 7 (`finalized`/`maturity`), 10.
- Edge cases (never-reviewed → pending; suspended → finalize; multi-show → earliest anchor; same-day exclusion) → Task 10 tests + logic.
- Unlabeled example created at generation time → Task 9.
- Labeling job + command → Tasks 10, 11.
- `OptimizationError`, `InsufficientDataError` → Task 5.
- Config surface (Phase 1 keys) → Task 6.
- NO SILENT FAILURES (no fabricated rewards; loud missing-seed/missing-champion) → Tasks 8, 10.

**Out of scope here (Phases 2–3, separate plans):** DSPy compile, the `experiment` table, arm assignment/randomization, Bayesian promotion, `ExperimentStateError`, `min_examples_to_compile`/`min_cards_per_arm`/promotion config keys. `arm` defaults to `"none"` until Phase 3 sets it.

**Type consistency check:** `RewardResult.reward` is `float | None` and every consumer (Task 10) guards for `None` before comparing to `demo_margin_delta`. `RewardConfig` fields (`gamma`, `window_k`, `min_interval_hours`, `demo_margin_delta`) map 1:1 to `OptimizationConfig` fields via `_to_reward_config`. `persist_variation` keyword args match the Task 9 test call. `LabelingReport` fields (`labeled`, `pending`, `finalized_skipped`) match all assertions.

**Placeholder scan:** none — every code step contains complete code; every run step has an exact command and expected output.
```
