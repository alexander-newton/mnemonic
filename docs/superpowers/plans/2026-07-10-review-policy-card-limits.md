# Review Policy Engine — Card Limits & Ordering (B1-Policy-A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A real per-deck/global review-policy engine — cards/day (minus what you did today) and cards/session limits split new-vs-due, plus ordering/interleaving — driven by a cascading `policy.toml`, enforced at queue build.

**Architecture:** A pure `core/policy/` package parses `<vault>/.mnemonic/policy.toml` into ordered rules and resolves a cascade (built-in → config → `_deck.md` → rules) into an `EffectivePolicy`. `RulesPolicy` replaces `SimplePolicy` behind a widened `ReviewPolicy` seam (a `QueueContext` carrying the effective policy + today's done-counts). `ReviewLog` gains a denormalized `deck_folder` so per-deck daily counts are stable and cheap.

**Tech Stack:** Python 3.11, `tomllib`, SQLAlchemy, Alembic, FastAPI, pytest, `uv`.

Backend commands run from `backend/`. Spec: `docs/superpowers/specs/2026-07-10-review-policy-card-limits-design.md`.

---

## File Structure

**Create:** `src/mnemonic/core/policy/__init__.py`, `src/mnemonic/core/policy/rules.py` (Rule + `load_rules`), `src/mnemonic/core/policy/resolve.py` (Limits, EffectivePolicy, SeedLimits, `resolve_policy`), `alembic/versions/review_deck_0004_reviewlog_deck.py`.
**Modify:** `src/mnemonic/exceptions.py` (`PolicyError`), `src/mnemonic/db/models/review_log.py` (`deck_folder` + index), `src/mnemonic/services/review.py` (write `deck_folder`), `src/mnemonic/services/review_queue.py` (widened seam, `RulesPolicy`, `QueueContext`/`DoneToday`, QueueService assembler + `done_today`), `src/mnemonic/api/deps.py` (queue provider passes config limits), `src/mnemonic/api/routes/reviews.py` (`PolicyError` → 422).

---

## Task 1: `PolicyError` + rules parser

**Files:**
- Modify: `src/mnemonic/exceptions.py`
- Create: `src/mnemonic/core/policy/__init__.py`, `src/mnemonic/core/policy/rules.py`
- Test: `tests/unit/core/policy/__init__.py`, `tests/unit/core/policy/test_rules.py`

- [ ] **Step 1: Add the exception** — In `src/mnemonic/exceptions.py`, after the `IntegrityError` block, add:

```python
# Policy errors
class PolicyError(MnemonicError):
    """The review policy rules file (policy.toml) is malformed."""

    pass
```

- [ ] **Step 2: Create package markers**

Create `src/mnemonic/core/policy/__init__.py`:
```python
"""Pure review-policy rules parsing and cascade resolution."""
```
Create empty `tests/unit/core/policy/__init__.py`.

- [ ] **Step 3: Write the failing tests** — Create `tests/unit/core/policy/test_rules.py`:

```python
"""Tests for parsing policy.toml into rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from mnemonic.core.policy.rules import Rule, load_rules
from mnemonic.exceptions import PolicyError

_VALID = """
[[rule]]
per_day = 200
order = "due_first"

[[rule]]
scope = "new"
per_day = 20

[[rule]]
deck = "gt"
scope = "new"
per_day = 10
per_session = 5

[[rule]]
deck = "gt"
order = "interleave"
interleave_new_every = 5
"""


def _write(tmp_path: Path, body: str) -> Path:
    (tmp_path / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".mnemonic" / "policy.toml").write_text(body)
    return tmp_path


def test_missing_file_is_empty(tmp_path: Path):
    assert load_rules(tmp_path) == []


def test_parses_valid_rules_in_order(tmp_path: Path):
    rules = load_rules(_write(tmp_path, _VALID))
    assert len(rules) == 4
    assert rules[0] == Rule(
        deck=None, scope="all", per_day=200, per_session=None,
        order="due_first", interleave_new_every=None,
    )
    assert rules[2].deck == "gt" and rules[2].scope == "new"
    assert rules[2].per_day == 10 and rules[2].per_session == 5
    assert rules[3].order == "interleave" and rules[3].interleave_new_every == 5


def test_unknown_key_raises_with_index(tmp_path: Path):
    with pytest.raises(PolicyError, match="rule #0"):
        load_rules(_write(tmp_path, '[[rule]]\nper_dya = 5\n'))


def test_bad_scope_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="scope"):
        load_rules(_write(tmp_path, '[[rule]]\nscope = "everything"\n'))


def test_bad_order_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="order"):
        load_rules(_write(tmp_path, '[[rule]]\norder = "sideways"\n'))


def test_negative_limit_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="per_day"):
        load_rules(_write(tmp_path, '[[rule]]\nper_day = -3\n'))


def test_interleave_requires_positive_every(tmp_path: Path):
    with pytest.raises(PolicyError, match="interleave_new_every"):
        load_rules(_write(tmp_path, '[[rule]]\norder = "interleave"\n'))


def test_malformed_toml_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="valid TOML"):
        load_rules(_write(tmp_path, 'this is = = not toml'))
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/policy/test_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.policy.rules'`

- [ ] **Step 5: Implement `rules.py`** — Create `src/mnemonic/core/policy/rules.py`:

```python
"""Parse <vault>/.mnemonic/policy.toml into an ordered list of Rule objects."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from mnemonic.exceptions import PolicyError

_SCOPES = ("all", "new", "due")
_ORDERS = ("due_first", "new_first", "interleave", "shuffle")
_ALLOWED_KEYS = {"deck", "scope", "per_day", "per_session", "order", "interleave_new_every"}


@dataclass(frozen=True)
class Rule:
    """One rule from policy.toml. None fields mean 'do not touch this key'."""

    deck: str | None
    scope: Literal["all", "new", "due"]
    per_day: int | None
    per_session: int | None
    order: Literal["due_first", "new_first", "interleave", "shuffle"] | None
    interleave_new_every: int | None


def load_rules(vault_root: Path) -> list[Rule]:
    """Parse the vault's policy.toml. Missing file → []. Malformed → PolicyError."""
    path = vault_root / ".mnemonic" / "policy.toml"
    if not path.exists():
        return []
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"policy.toml is not valid TOML: {exc}") from exc
    raw = data.get("rule", [])
    if not isinstance(raw, list):
        raise PolicyError("policy.toml: [[rule]] must be an array of tables.")
    return [_parse_rule(i, r) for i, r in enumerate(raw)]


def _parse_rule(index: int, raw: dict) -> Rule:
    unknown = set(raw) - _ALLOWED_KEYS
    if unknown:
        raise PolicyError(f"policy.toml rule #{index}: unknown key(s) {sorted(unknown)}.")
    scope = raw.get("scope", "all")
    if scope not in _SCOPES:
        raise PolicyError(
            f"policy.toml rule #{index}: scope must be one of {_SCOPES}, got '{scope}'."
        )
    order = raw.get("order")
    if order is not None and order not in _ORDERS:
        raise PolicyError(
            f"policy.toml rule #{index}: order must be one of {_ORDERS}, got '{order}'."
        )
    per_day = _non_negative(index, "per_day", raw.get("per_day"))
    per_session = _non_negative(index, "per_session", raw.get("per_session"))
    ine = _non_negative(index, "interleave_new_every", raw.get("interleave_new_every"))
    if ine is not None and ine < 1:
        raise PolicyError(
            f"policy.toml rule #{index}: interleave_new_every must be >= 1, got {ine}."
        )
    if order == "interleave" and ine is None:
        raise PolicyError(
            f"policy.toml rule #{index}: order='interleave' requires interleave_new_every."
        )
    return Rule(
        deck=raw.get("deck"),
        scope=scope,
        per_day=per_day,
        per_session=per_session,
        order=order,
        interleave_new_every=ine,
    )


def _non_negative(index: int, key: str, value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PolicyError(
            f"policy.toml rule #{index}: {key} must be a non-negative integer, got {value!r}."
        )
    return value
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/policy/test_rules.py -v`
Expected: PASS (8 passed)

- [ ] **Step 7: Commit**

```bash
git add src/mnemonic/exceptions.py src/mnemonic/core/policy/ tests/unit/core/policy/
git commit -m "feat(policy): PolicyError + policy.toml rules parser"
```

---

## Task 2: Cascade resolution

**Files:**
- Create: `src/mnemonic/core/policy/resolve.py`
- Test: `tests/unit/core/policy/test_resolve.py`

- [ ] **Step 1: Write the failing tests** — Create `tests/unit/core/policy/test_resolve.py`:

```python
"""Tests for resolving the policy cascade into an EffectivePolicy."""

from __future__ import annotations

from mnemonic.core.policy.resolve import EffectivePolicy, Limits, SeedLimits, resolve_policy
from mnemonic.core.policy.rules import Rule


def _rule(**kw):
    base = dict(
        deck=None, scope="all", per_day=None, per_session=None,
        order=None, interleave_new_every=None,
    )
    base.update(kw)
    return Rule(**base)


SEED = SeedLimits(new_per_day=20, due_per_day=200)


def test_seed_only_defaults():
    eff = resolve_policy(seed=SEED, rules=[], deck="gt")
    assert eff == EffectivePolicy(
        all=Limits(None, None),
        new=Limits(20, None),
        due=Limits(200, None),
        order="due_first",
        interleave_new_every=None,
    )


def test_scopes_resolve_independently():
    rules = [_rule(scope="new", per_day=10), _rule(scope="due", per_session=50)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.new == Limits(10, None)
    assert eff.due == Limits(200, 50)


def test_later_rule_overrides_earlier_key_by_key():
    rules = [_rule(scope="new", per_day=10, per_session=5), _rule(scope="new", per_day=8)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.new == Limits(8, 5)   # per_day overridden, per_session preserved


def test_deck_scoped_rule_only_applies_to_that_deck():
    rules = [_rule(deck="gt", scope="new", per_day=3)]
    assert resolve_policy(seed=SEED, rules=rules, deck="gt").new.per_day == 3
    assert resolve_policy(seed=SEED, rules=rules, deck="econ").new.per_day == 20


def test_order_and_interleave_applied():
    rules = [_rule(order="interleave", interleave_new_every=4)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.order == "interleave" and eff.interleave_new_every == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/policy/test_resolve.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.policy.resolve'`

- [ ] **Step 3: Implement `resolve.py`** — Create `src/mnemonic/core/policy/resolve.py`:

```python
"""Collapse the policy cascade into one EffectivePolicy for a deck.

Precedence weakest -> strongest: built-in defaults, config [defaults] / _deck.md (both
folded into the SeedLimits the caller passes), then policy.toml rules in file order
(later matching rules override earlier ones, key by key).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from mnemonic.core.policy.rules import Rule


@dataclass(frozen=True)
class Limits:
    """Per-scope limits. None means unlimited."""

    per_day: int | None = None
    per_session: int | None = None


@dataclass(frozen=True)
class EffectivePolicy:
    """The fully-resolved policy for one deck."""

    all: Limits
    new: Limits
    due: Limits
    order: str
    interleave_new_every: int | None


@dataclass(frozen=True)
class SeedLimits:
    """The new/due per-day limits seeded from config [defaults] or the deck's _deck.md."""

    new_per_day: int | None
    due_per_day: int | None


def resolve_policy(*, seed: SeedLimits, rules: list[Rule], deck: str) -> EffectivePolicy:
    """Apply the ordered rules on top of the seed for a given deck."""
    eff = EffectivePolicy(
        all=Limits(),
        new=Limits(per_day=seed.new_per_day),
        due=Limits(per_day=seed.due_per_day),
        order="due_first",
        interleave_new_every=None,
    )
    for rule in rules:
        if rule.deck is not None and rule.deck != deck:
            continue
        eff = _apply(eff, rule)
    return eff


def _apply(eff: EffectivePolicy, rule: Rule) -> EffectivePolicy:
    slot: Limits = getattr(eff, rule.scope)
    new_slot = Limits(
        per_day=rule.per_day if rule.per_day is not None else slot.per_day,
        per_session=rule.per_session if rule.per_session is not None else slot.per_session,
    )
    order = rule.order if rule.order is not None else eff.order
    ine = rule.interleave_new_every if rule.interleave_new_every is not None else eff.interleave_new_every
    return replace(eff, order=order, interleave_new_every=ine, **{rule.scope: new_slot})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/policy/test_resolve.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/policy/resolve.py tests/unit/core/policy/test_resolve.py
git commit -m "feat(policy): resolve the cascade into an EffectivePolicy per deck"
```

---

## Task 3: `ReviewLog.deck_folder` column + migration

**Files:**
- Modify: `src/mnemonic/db/models/review_log.py`
- Create: `alembic/versions/review_deck_0004_reviewlog_deck.py`
- Test: `tests/unit/db/test_reviewlog_deck.py`

- [ ] **Step 1: Write the failing test** — Create `tests/unit/db/test_reviewlog_deck.py`:

```python
"""Round-trip test for ReviewLog.deck_folder."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import Base, ReviewLog
from mnemonic.db.sqlite import create_engine, session_scope


def test_reviewlog_deck_folder_roundtrip(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            ReviewLog(
                id="r1", card_id="card-a", rating=3, response_time_ms=1000,
                review_time=datetime(2026, 7, 10, 9, 0, 0), deck_folder="gt",
            )
        )
    with session_scope(engine) as s:
        assert s.get(ReviewLog, "r1").deck_folder == "gt"


def test_reviewlog_deck_folder_defaults_none(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            ReviewLog(
                id="r2", card_id="card-b", rating=1, response_time_ms=500,
                review_time=datetime(2026, 7, 10, 9, 0, 0),
            )
        )
    with session_scope(engine) as s:
        assert s.get(ReviewLog, "r2").deck_folder is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_reviewlog_deck.py -v`
Expected: FAIL with a `TypeError`/`AttributeError` about `deck_folder`.

- [ ] **Step 3: Add the column + index** — In `src/mnemonic/db/models/review_log.py`, add `Index` to the sqlalchemy import and add the column + `__table_args__`. Change the import line:

```python
from sqlalchemy import DateTime, Float, Index, Integer, String
```

Add this column after the `variation_helpful` column line:

```python
    deck_folder: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (Index("idx_review_log_deck_time", "deck_folder", "review_time"),)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_reviewlog_deck.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Create the migration** — Create `alembic/versions/review_deck_0004_reviewlog_deck.py`:

```python
"""Denormalize deck_folder onto review_log for per-deck daily counts.

Revision ID: review_deck_0004
Revises: card_integrity_0003
Create Date: 2026-07-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "review_deck_0004"
down_revision = "card_integrity_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_log", sa.Column("deck_folder", sa.String, nullable=True))
    op.create_index("idx_review_log_deck_time", "review_log", ["deck_folder", "review_time"])


def downgrade() -> None:
    op.drop_index("idx_review_log_deck_time", table_name="review_log")
    with op.batch_alter_table("review_log") as batch:
        batch.drop_column("deck_folder")
```

- [ ] **Step 6: Verify the migration applies + reverses**

Run: `uv run alembic upgrade head`
Expected: ends with `Running upgrade card_integrity_0003 -> review_deck_0004`, no errors.
Run: `uv run alembic downgrade -1 && uv run alembic upgrade head`
Expected: both succeed with no errors.

- [ ] **Step 7: Commit**

```bash
git add src/mnemonic/db/models/review_log.py alembic/versions/review_deck_0004_reviewlog_deck.py tests/unit/db/test_reviewlog_deck.py
git commit -m "feat(policy): denormalize deck_folder onto ReviewLog (+ migration)"
```

---

## Task 4: `ReviewService.rate` writes `deck_folder`

**Files:**
- Modify: `src/mnemonic/services/review.py`
- Test: `tests/unit/services/test_review_service.py`

- [ ] **Step 1: Write the failing test** — Append this self-contained test to `tests/unit/services/test_review_service.py` (it does not depend on any existing helper in the file):

```python
def test_rate_records_deck_folder(tmp_path):
    from mnemonic.db.models import Base, ReviewLog
    from mnemonic.db.sqlite import create_engine, session_scope
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    repo = VaultRepository(vault_root=vault, engine=engine)

    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb", rating=3, response_time_ms=1200
    )

    with session_scope(engine) as s:
        row = s.query(ReviewLog).filter(ReviewLog.card_id == "card-aaaabbbb").one()
        assert row.deck_folder == "gt"
```

Note: `ReviewService` is already imported at the top of this test file; if it is not, add `from mnemonic.services.review import ReviewService`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/services/test_review_service.py::test_rate_records_deck_folder -v`
Expected: FAIL (`row.deck_folder` is `None`, assertion fails).

- [ ] **Step 3: Write `deck_folder` in `rate`** — In `src/mnemonic/services/review.py`, the `rate` method already has `card = self.repo.get_card(card_id)` near the top (raising `CardNotFoundError` if None). In the `ReviewLog(...)` construction near the end of the method, add one field after `variation_helpful=variation_helpful,`:

```python
                    variation_helpful=variation_helpful,
                    deck_folder=card.deck_folder.name,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_service.py -q`
Expected: PASS (existing review tests + the new one).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review.py tests/unit/services/test_review_service.py
git commit -m "feat(policy): ReviewService.rate records the card's deck_folder"
```

---

## Task 5: Widened seam + `RulesPolicy`

**Files:**
- Modify: `src/mnemonic/services/review_queue.py`
- Test: `tests/unit/services/test_review_queue.py`

- [ ] **Step 1: Replace the policy tests** — In `tests/unit/services/test_review_queue.py`, REPLACE the three existing `SimplePolicy` tests (`test_due_cards_ordered_by_due_then_new_appended`, `test_suspended_and_future_due_excluded`, `test_new_cards_capped_by_daily_new_limit`) with the `RulesPolicy` tests below. KEEP the `_card` helper and `NOW` constant, and KEEP the two `QueueService` tests (`test_queue_service_builds_items`, `test_queue_service_unknown_deck_raises`) for now — Task 6 updates those.

```python
from mnemonic.core.policy.resolve import EffectivePolicy, Limits
from mnemonic.services.review_queue import DoneToday, QueueContext, RulesPolicy


def _policy(*, all_=Limits(), new=Limits(), due=Limits(), order="due_first", ine=None):
    return EffectivePolicy(all=all_, new=new, due=due, order=order, interleave_new_every=ine)


def _ctx(cards, policy, done=DoneToday(0, 0, 0), seed=0):
    return QueueContext(cards=cards, now=NOW, policy=policy, done_today=done, seed=seed)


def test_due_first_orders_due_by_due_then_new():
    cards = [
        _card("new1", state="new"),
        _card("due-late", due=datetime(2026, 7, 9, 10, 0, 0)),
        _card("due-early", due=datetime(2026, 7, 8, 10, 0, 0)),
    ]
    out = RulesPolicy().build_queue(_ctx(cards, _policy()))
    assert [c.card_id for c in out] == ["due-early", "due-late", "new1"]


def test_suspended_and_future_due_excluded():
    cards = [
        _card("suspended", due=datetime(2026, 7, 8, 0, 0, 0), suspended=True),
        _card("future", due=datetime(2026, 7, 20, 0, 0, 0)),
        _card("due", due=datetime(2026, 7, 9, 0, 0, 0)),
    ]
    out = RulesPolicy().build_queue(_ctx(cards, _policy()))
    assert [c.card_id for c in out] == ["due"]


def test_new_per_day_minus_done_today():
    cards = [_card(f"new{i}", state="new") for i in range(5)]
    policy = _policy(new=Limits(per_day=4))
    out = RulesPolicy().build_queue(_ctx(cards, policy, done=DoneToday(new=3, due=0, total=3)))
    assert len(out) == 1  # 4 per_day - 3 done = 1


def test_per_session_caps_new():
    cards = [_card(f"new{i}", state="new") for i in range(5)]
    out = RulesPolicy().build_queue(_ctx(cards, _policy(new=Limits(per_session=2))))
    assert len(out) == 2


def test_min_of_day_and_session_wins():
    cards = [_card(f"new{i}", state="new") for i in range(9)]
    policy = _policy(new=Limits(per_day=10, per_session=3))
    out = RulesPolicy().build_queue(_ctx(cards, policy, done=DoneToday(new=2, due=0, total=2)))
    assert len(out) == 3  # min(10-2, 3)


def test_over_budget_yields_zero():
    cards = [_card("new0", state="new")]
    policy = _policy(new=Limits(per_day=5))
    out = RulesPolicy().build_queue(_ctx(cards, policy, done=DoneToday(new=5, due=0, total=5)))
    assert out == []


def test_new_first_ordering():
    cards = [_card("d", due=datetime(2026, 7, 9, 0, 0, 0)), _card("n", state="new")]
    out = RulesPolicy().build_queue(_ctx(cards, _policy(order="new_first")))
    assert [c.card_id for c in out] == ["n", "d"]


def test_interleave_one_new_every_two_due():
    due = [_card(f"d{i}", due=datetime(2026, 7, i + 1, 0, 0, 0)) for i in range(4)]
    new = [_card(f"n{i}", state="new") for i in range(2)]
    out = RulesPolicy().build_queue(_ctx(due + new, _policy(order="interleave", ine=2)))
    assert [c.card_id for c in out] == ["d0", "d1", "n0", "d2", "d3", "n1"]


def test_shuffle_is_deterministic_for_seed():
    cards = [_card(f"d{i}", due=datetime(2026, 7, i + 1, 0, 0, 0)) for i in range(5)]
    a = RulesPolicy().build_queue(_ctx(cards, _policy(order="shuffle"), seed=7))
    b = RulesPolicy().build_queue(_ctx(cards, _policy(order="shuffle"), seed=7))
    assert [c.card_id for c in a] == [c.card_id for c in b]


def test_all_cap_trims_after_ordering():
    cards = [_card(f"d{i}", due=datetime(2026, 7, i + 1, 0, 0, 0)) for i in range(5)]
    out = RulesPolicy().build_queue(_ctx(cards, _policy(all_=Limits(per_day=2))))
    assert [c.card_id for c in out] == ["d0", "d1"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py::test_due_first_orders_due_by_due_then_new -v`
Expected: FAIL with `ImportError: cannot import name 'RulesPolicy'`.

- [ ] **Step 3: Rewrite the seam + policy** — In `src/mnemonic/services/review_queue.py`, replace the module docstring, imports, and the `ReviewPolicy`/`SimplePolicy` block (everything from the top of the file down to and including `SimplePolicy` and the `_DEFAULT_NEW_LIMIT = 20` line) with:

```python
"""Review queue: build an ordered, display-ready list of cards to review for a deck.

`ReviewPolicy` is the seam the policy engine plugs into; `RulesPolicy` selects and orders
cards from a resolved `EffectivePolicy` plus today's done-counts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import Engine, func

from mnemonic.core.fsrs.preview import preview_schedule
from mnemonic.core.fsrs.state import to_card_state
from mnemonic.core.policy.resolve import EffectivePolicy, Limits, SeedLimits, resolve_policy
from mnemonic.core.policy.rules import load_rules
from mnemonic.core.review.faces import build_faces
from mnemonic.db.models import ReviewLog
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import DeckNotFoundError
from mnemonic.vault.repository import Card, VaultRepository

_DEFAULT_LIMIT = 20


@dataclass(frozen=True)
class DoneToday:
    """Cards already reviewed today for a deck, split by new vs due."""

    new: int
    due: int
    total: int


@dataclass(frozen=True)
class QueueContext:
    """Everything a policy needs to build a queue."""

    cards: list[Card]
    now: datetime
    policy: EffectivePolicy
    done_today: DoneToday
    seed: int


class ReviewPolicy(Protocol):
    """Produces the ordered set of cards to review now."""

    def build_queue(self, ctx: QueueContext) -> list[Card]: ...


def _cap(limits: Limits, done: int) -> int | None:
    caps: list[int] = []
    if limits.per_day is not None:
        caps.append(max(0, limits.per_day - done))
    if limits.per_session is not None:
        caps.append(max(0, limits.per_session))
    return min(caps) if caps else None


def _take(items: list[Card], cap: int | None) -> list[Card]:
    return items if cap is None else items[:cap]


def _interleave(due: list[Card], new: list[Card], every: int) -> list[Card]:
    out: list[Card] = []
    di = ni = 0
    while di < len(due) or ni < len(new):
        for _ in range(every):
            if di < len(due):
                out.append(due[di])
                di += 1
        if ni < len(new):
            out.append(new[ni])
            ni += 1
    return out


def _order(order: str, due: list[Card], new: list[Card], ine: int | None, seed: int) -> list[Card]:
    if order == "new_first":
        return new + due
    if order == "shuffle":
        combined = due + new
        random.Random(seed).shuffle(combined)
        return combined
    if order == "interleave" and ine is not None:
        return _interleave(due, new, ine)
    return due + new  # due_first (default)


class RulesPolicy:
    """Select cards within resolved limits and order them per the effective policy."""

    def build_queue(self, ctx: QueueContext) -> list[Card]:
        p = ctx.policy
        due_all = sorted(
            [
                c
                for c in ctx.cards
                if not c.suspended and c.state != "new" and c.due is not None and c.due <= ctx.now
            ],
            key=lambda c: c.due or ctx.now,
        )
        new_all = [c for c in ctx.cards if not c.suspended and c.state == "new"]
        due = _take(due_all, _cap(p.due, ctx.done_today.due))
        new = _take(new_all, _cap(p.new, ctx.done_today.new))
        ordered = _order(p.order, due, new, p.interleave_new_every, ctx.seed)
        return _take(ordered, _cap(p.all, ctx.done_today.total))
```

Leave the `QueuedCard` dataclass and the `QueueService` class below this block in place for now (Task 6 rewrites `QueueService`). Important: the module still **imports** fine — the old `QueueService` methods reference the now-removed `SimplePolicy`/`_DEFAULT_NEW_LIMIT` only inside method bodies, which are evaluated at call time, not import time. So the policy tests (which never construct `QueueService`) import and run cleanly. The two `queue_service` tests will error at runtime in this intermediate state; that is expected and Task 6 fixes them — this task runs only the policy tests via `-k "not queue_service"`.

- [ ] **Step 4: Run the policy tests**

Run: `uv run pytest tests/unit/services/test_review_queue.py -k "not queue_service" -q`
Expected: PASS (10 policy tests). (The two `queue_service` tests may fail/error until Task 6 — that is expected and they are excluded here.)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review_queue.py tests/unit/services/test_review_queue.py
git commit -m "feat(policy): widen ReviewPolicy seam + RulesPolicy selection/ordering"
```

---

## Task 6: `QueueService` assembler + `done_today` + wiring

**Files:**
- Modify: `src/mnemonic/services/review_queue.py`, `src/mnemonic/api/deps.py`, `src/mnemonic/api/routes/reviews.py`
- Test: `tests/unit/services/test_review_queue.py`, `tests/unit/api/test_review_queue.py`

- [ ] **Step 1: Update the QueueService tests** — In `tests/unit/services/test_review_queue.py`, the two `QueueService` tests construct `QueueService(repo=..., engine=...)`. Update BOTH constructions to pass the new required limits:

```python
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine,
        default_new_per_day=20,
        default_due_per_day=200,
    )
```

Then add a test that a deck's `policy.toml` limit is honoured. Append:

```python
def test_queue_service_honours_policy_toml(tmp_path):
    from mnemonic.db.models import Base
    from mnemonic.db.sqlite import create_engine
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "_deck.md").write_text(
        "---\ndeck_name: GT\nvariation_enabled: false\nvariation_frequency: 0.0\n"
        "leech_threshold: 8\ndaily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )
    for i in range(4):
        (vault / "01_Projects" / "gt" / f"n{i}.qmd").write_text(
            f"---\ntitle: n{i}\n---\n## Card\n\nA {{{{c1::x}}}} card. ^card-n{i}\n"
        )
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text('[[rule]]\nscope = "new"\nper_day = 2\n')
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine, default_new_per_day=20, default_due_per_day=200,
    )

    items = svc.build("gt")

    assert len(items) == 2  # 4 new cards, policy.toml caps new per_day at 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py -k "queue_service" -v`
Expected: FAIL — `QueueService.__init__` got an unexpected keyword `default_new_per_day` (old signature).

- [ ] **Step 3: Rewrite `QueueService`** — In `src/mnemonic/services/review_queue.py`, replace the entire `QueueService` class (from `class QueueService:` to the end of the file) with:

```python
class QueueService:
    """Assemble a display-ready review queue: resolve policy, count today, order, render."""

    def __init__(
        self,
        *,
        repo: VaultRepository,
        engine: Engine,
        default_new_per_day: int = _DEFAULT_LIMIT,
        default_due_per_day: int = _DEFAULT_LIMIT,
        policy: ReviewPolicy | None = None,
    ) -> None:
        self.repo = repo
        self.engine = engine
        self.default_new_per_day = default_new_per_day
        self.default_due_per_day = default_due_per_day
        self.policy = policy or RulesPolicy()

    def build(self, deck_folder: str) -> list[QueuedCard]:
        """Build the queue for a deck.

        Raises:
            DeckNotFoundError: If no deck folder with that name exists.
            PolicyError: If the vault's policy.toml is malformed.
        """
        now = datetime.now()
        deck = next((d for d in self.repo.list_decks() if d.folder.name == deck_folder), None)
        if deck is None:
            raise DeckNotFoundError(
                f"Deck '{deck_folder}' not found in the vault. Check the deck folder name."
            )
        cards = [c for c in self.repo.list_cards() if c.deck_folder.name == deck_folder]
        seed_limits = SeedLimits(
            new_per_day=deck.config.daily_new_limit if deck.config else self.default_new_per_day,
            due_per_day=deck.config.daily_review_limit if deck.config else self.default_due_per_day,
        )
        effective = resolve_policy(
            seed=seed_limits, rules=load_rules(self.repo.vault_root), deck=deck_folder
        )
        ctx = QueueContext(
            cards=cards,
            now=now,
            policy=effective,
            done_today=self._done_today(deck_folder, now),
            seed=now.toordinal(),
        )
        ordered = self.policy.build_queue(ctx)
        last_reviews = self._last_reviews([c.card_id for c in ordered])
        return [self._to_item(c, last_reviews.get(c.card_id), now) for c in ordered]

    def _done_today(self, deck_folder: str, now: datetime) -> DoneToday:
        start = datetime(now.year, now.month, now.day)
        with session_scope(self.engine) as s:
            rows = (
                s.query(ReviewLog.state_before, func.count())
                .filter(ReviewLog.deck_folder == deck_folder, ReviewLog.review_time >= start)
                .group_by(ReviewLog.state_before)
                .all()
            )
        new = sum(n for sb, n in rows if sb == "new")
        due = sum(n for sb, n in rows if sb != "new")
        return DoneToday(new=new, due=due, total=new + due)

    def _last_reviews(self, card_ids: list[str]) -> dict[str, datetime]:
        if not card_ids:
            return {}
        with session_scope(self.engine) as s:
            rows = (
                s.query(ReviewLog.card_id, ReviewLog.review_time)
                .filter(ReviewLog.card_id.in_(card_ids))
                .all()
            )
        latest: dict[str, datetime] = {}
        for cid, when in rows:
            if cid not in latest or when > latest[cid]:
                latest[cid] = when
        return latest

    def _to_item(self, card: Card, last_review: datetime | None, now: datetime) -> QueuedCard:
        faces = build_faces(syntax=card.syntax, front=card.front, back=card.back)
        state = to_card_state(
            stability=card.stability,
            difficulty=card.difficulty,
            reps=card.reps,
            lapses=card.lapses,
            state=card.state,
            due=card.due,
            last_review=last_review,
            now=now,
        )
        previews = {r: opt.new_interval for r, opt in preview_schedule(state).items()}
        return QueuedCard(
            card_id=card.card_id,
            syntax=card.syntax,
            front=faces.front,
            answer=faces.answer,
            previews=previews,
        )
```

- [ ] **Step 4: Update the deps provider** — In `src/mnemonic/api/deps.py`, replace the `get_queue_service` function with:

```python
def get_queue_service() -> QueueService:
    cfg = get_config()
    return QueueService(
        repo=get_repo(),
        engine=get_engine(),
        default_new_per_day=cfg.defaults.daily_new_limit,
        default_due_per_day=cfg.defaults.daily_review_limit,
    )
```

- [ ] **Step 5: Map `PolicyError` to 422** — In `src/mnemonic/api/routes/reviews.py`, add `PolicyError` to the exceptions import, and add an `except` clause in the `review_queue` handler. The import line becomes:

```python
from mnemonic.exceptions import (
    CardNotFoundError,
    DeckNotFoundError,
    InvalidRatingError,
    PolicyError,
    RenderError,
)
```

And the `review_queue` try/except becomes:

```python
    try:
        items = svc.build(deck)
    except DeckNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RenderError, PolicyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

- [ ] **Step 6: Add an API test for the 422** — Append to `tests/unit/api/test_review_queue.py`:

```python
def test_queue_malformed_policy_returns_422(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text('[[rule]]\norder = "sideways"\n')
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert "order" in resp.json()["detail"]
```

Note: the existing `_override` in that file constructs `QueueService(repo=..., engine=...)` — update it to also pass `default_new_per_day=20, default_due_per_day=200` so the overridden service matches the new signature.

- [ ] **Step 7: Run the affected suites**

Run: `uv run pytest tests/unit/services/test_review_queue.py tests/unit/api/test_review_queue.py -q`
Expected: PASS (all policy + queue-service + api tests).

- [ ] **Step 8: Commit**

```bash
git add src/mnemonic/services/review_queue.py src/mnemonic/api/deps.py src/mnemonic/api/routes/reviews.py tests/unit/services/test_review_queue.py tests/unit/api/test_review_queue.py
git commit -m "feat(policy): QueueService resolves cascade + done-today; policy.toml wired, 422 on error"
```

---

## Task 7: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite**

Run (from `backend/`): `uv run pytest -q`
Expected: PASS except the 3 known pre-existing `tests/test_setup.py` dependency-import failures. No other failures.

- [ ] **Step 2: Lint + types on new/changed files**

Run (from `backend/`):
```bash
uv run ruff check src/mnemonic/core/policy src/mnemonic/services/review_queue.py src/mnemonic/services/review.py src/mnemonic/db/models/review_log.py src/mnemonic/api/deps.py src/mnemonic/api/routes/reviews.py
uv run black --check src/mnemonic/core/policy src/mnemonic/services/review_queue.py
uv run mypy src/mnemonic/core/policy src/mnemonic/services/review_queue.py
```
Expected: ruff clean (ignore the pre-existing `lint.select`/`lint.ignore` pyproject deprecation warning); black clean; mypy clean.

- [ ] **Step 3: Coverage on the pure policy package**

Run (from `backend/`): `uv run pytest --cov=mnemonic.core.policy --cov-report=term-missing tests/unit/core/policy -q`
Expected: `core/policy` ≥ 95%.

- [ ] **Step 4: Final commit (only if lint/type fixes were made)**

```bash
git add -A
git commit -m "chore(policy): lint and type fixes"
```

---

## Notes for the implementer

- **`SimplePolicy` is gone**, replaced by `RulesPolicy`. There is no second ordering source.
- **The cascade seed** captures config `[defaults]` and `_deck.md` (a deck's `_deck.md` fully overrides config for the two daily limits). `policy.toml` rules then override key-by-key, in file order. `resolve_policy` stays pure — the caller (`QueueService`) extracts the two ints and the vault path.
- **Real daily budget:** `_cap` subtracts `done_today` from `per_day` and clamps at 0, so an exhausted budget yields an empty queue (a 200 with `[]`, the existing "Nothing due" UI). The old code only capped the queue size and ignored today's completions.
- **`all` cap applies after ordering**, per-scope caps before — the combined ceiling wins (documented in the spec).
- **`done_today` uses `state_before == "new"`** to classify new vs due — exactly how `ReviewService.rate` records the pre-review state. Historical rows with `deck_folder = NULL` are excluded.
- **Migration head** before this work is `card_integrity_0003`; the new revision chains from it.
- **Do not touch** `db/repositories/review_log.py` (it queries a non-existent `user_id` column — dead code, separate cleanup). The new `done_today` query lives on `QueueService`.
- **Pre-existing failures to expect:** backend `tests/test_setup.py` (redis/jose/passlib not installed).
