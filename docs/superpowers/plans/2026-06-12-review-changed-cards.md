# Review Changed Cards Implementation Plan (Sub-project A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user review cards whose `core_changed` flag is set and apply keep / soft-reset / full-reset to their FSRS scheduling, via a backend service + two endpoints and a React panel.

**Architecture:** New `CoreChangeService` holds the decision logic (mutating inside `session_scope`); two card-scoped endpoints expose list + apply; a React panel at `/changed` (TanStack Query, modeled on `DeckListPage`) consumes them. Brand-new FSRS defaults are extracted once into `core/fsrs` and reused for full-reset and the two existing inline call sites.

**Tech Stack:** Backend — Python 3.11, SQLAlchemy 2.0, FastAPI, pytest, `uv`. Frontend — React 18, TypeScript, TanStack Query, Vitest + React Testing Library, `npm`.

Backend commands run from `backend/`; frontend commands from `frontend/`. Spec: `docs/superpowers/specs/2026-06-12-review-changed-cards-design.md`.

---

## File Structure

**Backend — create:**
- `src/mnemonic/core/fsrs/defaults.py` — `NEW_CARD_DEFAULTS` (single source of truth for brand-new state)
- `src/mnemonic/services/core_change.py` — `ChangedCard`, `SchedulingSnapshot`, `CoreChangeService`

**Backend — modify:**
- `src/mnemonic/services/review.py` — use `NEW_CARD_DEFAULTS` for the inline new-card construction
- `src/mnemonic/vault/repository.py` — use `NEW_CARD_DEFAULTS`; add `core_changed`/`core_changed_at` to `Card`
- `src/mnemonic/api/routes/cards.py` — `_serialize` gains `core_changed`/`core_changed_at`; add `GET /changed` and `POST /{card_id}/core-change`
- `src/mnemonic/api/deps.py` — add `get_core_change_service`

**Frontend — create:**
- `src/hooks/useChangedCards.ts` — `useChangedCards` query + `useApplyCoreChange` mutation
- `src/pages/ChangedCardsPage.tsx` — the panel
- `src/pages/components/ResetConfirmationDialog.tsx` — full-reset confirmation

**Frontend — modify:**
- `src/types/index.ts` — `CoreChangeDecision`, `ChangedCard`, `SchedulingSnapshot`
- `src/services/api.ts` — `listChangedCards`, `applyCoreChange`
- `src/App.tsx` — `/changed` route
- `src/components/Navigation.tsx` — "Changed Cards" link

**Tests — create:** `tests/unit/core/test_new_card_defaults.py`, `tests/unit/services/test_core_change.py`, `tests/unit/api/test_cards_changed.py` (backend); `frontend/tests/hooks/useChangedCards.test.tsx`, `frontend/tests/pages/ChangedCardsPage.test.tsx` (frontend).

---

## Task 1: Extract `NEW_CARD_DEFAULTS`

**Files:**
- Create: `src/mnemonic/core/fsrs/defaults.py`
- Test: `tests/unit/core/test_new_card_defaults.py`
- Modify: `src/mnemonic/services/review.py`, `src/mnemonic/vault/repository.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/core/test_new_card_defaults.py`:

```python
"""The brand-new FSRS defaults, single source of truth."""

from __future__ import annotations

import dataclasses

import pytest

from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS


def test_new_card_defaults_values():
    assert NEW_CARD_DEFAULTS.state == "new"
    assert NEW_CARD_DEFAULTS.stability == 0.0
    assert NEW_CARD_DEFAULTS.difficulty == 5.0
    assert NEW_CARD_DEFAULTS.due is None
    assert NEW_CARD_DEFAULTS.reps == 0
    assert NEW_CARD_DEFAULTS.lapses == 0


def test_new_card_defaults_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        NEW_CARD_DEFAULTS.stability = 9.9  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_new_card_defaults.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.fsrs.defaults'`

- [ ] **Step 3: Create `defaults.py`**

Create `src/mnemonic/core/fsrs/defaults.py`:

```python
"""Single source of truth for a brand-new card's FSRS state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewCardDefaults:
    """The FSRS field values of a freshly created (never-reviewed) card."""

    state: str = "new"
    stability: float = 0.0
    difficulty: float = 5.0
    due: datetime | None = None
    reps: int = 0
    lapses: int = 0


NEW_CARD_DEFAULTS = NewCardDefaults()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/core/test_new_card_defaults.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Use it in `review.py`**

In `src/mnemonic/services/review.py`, add the import after the existing `from mnemonic.core.fsrs.scheduler import schedule_review` line:

```python
from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS
```

Replace the inline new-card construction:

```python
                state = SchedulingState(
                    card_id=card_id,
                    state="new",
                    stability=0.0,
                    difficulty=5.0,
                    reps=0,
                    lapses=0,
                    leech_score=0.0,
                )
```

with:

```python
                state = SchedulingState(
                    card_id=card_id,
                    state=NEW_CARD_DEFAULTS.state,
                    stability=NEW_CARD_DEFAULTS.stability,
                    difficulty=NEW_CARD_DEFAULTS.difficulty,
                    reps=NEW_CARD_DEFAULTS.reps,
                    lapses=NEW_CARD_DEFAULTS.lapses,
                    leech_score=0.0,
                )
```

- [ ] **Step 6: Use it in `repository.py`**

In `src/mnemonic/vault/repository.py`, add near the other imports:

```python
from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS
```

In `list_cards`, replace the literal fallbacks in the `Card(...)` construction:

```python
                    state=row.state if row else "new",
                    stability=row.stability if row else 0.0,
                    difficulty=row.difficulty if row else 5.0,
                    due=row.due if row else None,
                    reps=row.reps if row else 0,
                    lapses=row.lapses if row else 0,
```

with:

```python
                    state=row.state if row else NEW_CARD_DEFAULTS.state,
                    stability=row.stability if row else NEW_CARD_DEFAULTS.stability,
                    difficulty=row.difficulty if row else NEW_CARD_DEFAULTS.difficulty,
                    due=row.due if row else NEW_CARD_DEFAULTS.due,
                    reps=row.reps if row else NEW_CARD_DEFAULTS.reps,
                    lapses=row.lapses if row else NEW_CARD_DEFAULTS.lapses,
```

- [ ] **Step 7: Run the affected suites to confirm no regressions**

Run: `uv run pytest tests/unit/vault/test_repository.py tests/unit/services -q`
Expected: PASS (all existing review/repository tests still pass).

- [ ] **Step 8: Commit**

```bash
git add src/mnemonic/core/fsrs/defaults.py tests/unit/core/test_new_card_defaults.py src/mnemonic/services/review.py src/mnemonic/vault/repository.py
git commit -m "refactor(fsrs): extract NEW_CARD_DEFAULTS as single source of truth"
```

---

## Task 2: Add `core_changed` to the `Card` dataclass + serializer

**Files:**
- Modify: `src/mnemonic/vault/repository.py`, `src/mnemonic/api/routes/cards.py`
- Test: `tests/unit/vault/test_repository.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/vault/test_repository.py`:

```python
def test_list_cards_exposes_core_changed(tmp_path: Path):
    from datetime import datetime

    vault, engine = _setup(tmp_path)
    with session_scope(engine) as s:
        s.add(
            SchedulingState(
                card_id="card-aaaabbbb",
                state="review",
                stability=4.0,
                difficulty=6.0,
                reps=5,
                lapses=0,
                leech_score=0.0,
                core_changed=True,
                core_changed_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )
    repo = VaultRepository(vault_root=vault, engine=engine)
    card = repo.list_cards()[0]
    assert card.core_changed is True
    assert card.core_changed_at == datetime(2026, 6, 12, 9, 0, 0)


def test_list_cards_core_changed_defaults_false(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    card = repo.list_cards()[0]
    assert card.core_changed is False
    assert card.core_changed_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/vault/test_repository.py::test_list_cards_exposes_core_changed -v`
Expected: FAIL with `AttributeError: 'Card' object has no attribute 'core_changed'`

- [ ] **Step 3: Add fields to the `Card` dataclass**

In `src/mnemonic/vault/repository.py`, add two fields to the `Card` dataclass after `suspended: bool`:

```python
    suspended: bool
    core_changed: bool
    core_changed_at: datetime | None
```

- [ ] **Step 4: Populate them in `list_cards`**

In the `Card(...)` construction in `list_cards`, after the `suspended=...` line add:

```python
                    suspended=bool(row.suspended) if row else False,
                    core_changed=bool(row.core_changed) if row else False,
                    core_changed_at=row.core_changed_at if row else None,
```

(Replace the existing `suspended=...` line with these three lines.)

- [ ] **Step 5: Add fields to the card serializer**

In `src/mnemonic/api/routes/cards.py`, in `_serialize`, replace the exact ending of the returned dict:

```python
        "suspended": card.suspended,
    }
```

with:

```python
        "suspended": card.suspended,
        "core_changed": card.core_changed,
        "core_changed_at": card.core_changed_at.isoformat() if card.core_changed_at else None,
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/vault/test_repository.py -q`
Expected: PASS (all repository tests, including the 2 new ones).

- [ ] **Step 7: Commit**

```bash
git add src/mnemonic/vault/repository.py src/mnemonic/api/routes/cards.py tests/unit/vault/test_repository.py
git commit -m "feat(cards): expose core_changed/core_changed_at on Card and serializer"
```

---

## Task 3: `CoreChangeService.apply` (decision logic)

**Files:**
- Create: `src/mnemonic/services/core_change.py`
- Test: `tests/unit/services/test_core_change.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/services/test_core_change.py`:

```python
"""Tests for CoreChangeService."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from mnemonic.db.models import Base, SchedulingState
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.services.core_change import CoreChangeService


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nThe {{c1::Nash}} equilibrium.\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def _flagged_row(engine, **overrides):
    fields = dict(
        card_id="card-aaaabbbb",
        state="review",
        stability=12.4,
        difficulty=6.1,
        due=datetime(2026, 6, 20, 9, 0, 0),
        reps=5,
        lapses=1,
        leech_score=0.0,
        core_changed=True,
        core_changed_at=datetime(2026, 6, 12, 9, 0, 0),
    )
    fields.update(overrides)
    with session_scope(engine) as s:
        s.add(SchedulingState(**fields))


def _service(tmp_path):
    from mnemonic.vault.repository import VaultRepository

    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    return CoreChangeService(repo=repo, engine=engine), engine


NOW = datetime(2026, 6, 12, 12, 0, 0)


def test_keep_clears_flag_only(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    snap = svc.apply(card_id="card-aaaabbbb", decision="keep", now=NOW)
    assert snap.core_changed is False
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert bool(row.core_changed) is False
        assert row.core_changed_at is None
        assert row.stability == 12.4 and row.state == "review"  # FSRS untouched
        assert row.due == datetime(2026, 6, 20, 9, 0, 0)


def test_soft_reset_sets_due_now_preserves_memory(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    snap = svc.apply(card_id="card-aaaabbbb", decision="soft_reset", now=NOW)
    assert snap.due == NOW
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.due == NOW
        assert row.stability == 12.4 and row.difficulty == 6.1  # preserved
        assert row.reps == 5 and row.lapses == 1 and row.state == "review"
        assert bool(row.core_changed) is False


def test_full_reset_restores_defaults(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    snap = svc.apply(card_id="card-aaaabbbb", decision="full_reset", now=NOW)
    assert snap.state == "new" and snap.stability == 0.0 and snap.difficulty == 5.0
    assert snap.due is None and snap.reps == 0 and snap.lapses == 0
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.state == "new" and row.stability == 0.0 and row.difficulty == 5.0
        assert row.due is None and row.reps == 0 and row.lapses == 0
        assert bool(row.core_changed) is False


def test_apply_unflagged_card_raises(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine, core_changed=False, core_changed_at=None)
    with pytest.raises(CardNotFoundError):
        svc.apply(card_id="card-aaaabbbb", decision="keep", now=NOW)


def test_apply_missing_card_raises(tmp_path: Path):
    svc, _ = _service(tmp_path)
    with pytest.raises(CardNotFoundError):
        svc.apply(card_id="card-nope", decision="keep", now=NOW)


def test_apply_bad_decision_raises(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    with pytest.raises(ValidationError):
        svc.apply(card_id="card-aaaabbbb", decision="obliterate", now=NOW)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_core_change.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.services.core_change'`

- [ ] **Step 3: Implement the service (apply + dataclasses)**

Create `src/mnemonic/services/core_change.py`:

```python
"""Core-change service: list flagged cards and apply the user's reset decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import Engine

from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS
from mnemonic.db.models import SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.vault.repository import VaultRepository

Decision = Literal["keep", "soft_reset", "full_reset"]
_DECISIONS = ("keep", "soft_reset", "full_reset")


@dataclass(frozen=True)
class ChangedCard:
    """A flagged card enriched with its content and the reason it was flagged."""

    card_id: str
    title: str
    front: str
    syntax: str
    change_kind: str | None
    core_changed_at: datetime | None
    state: str
    due: datetime | None
    stability: float
    difficulty: float


@dataclass(frozen=True)
class SchedulingSnapshot:
    """The scheduling state of a card after a decision is applied."""

    card_id: str
    core_changed: bool
    state: str
    stability: float
    difficulty: float
    due: datetime | None
    reps: int
    lapses: int


class CoreChangeService:
    """List core-changed cards and apply keep / soft-reset / full-reset."""

    def __init__(self, *, repo: VaultRepository, engine: Engine) -> None:
        self.repo = repo
        self.engine = engine

    def apply(self, *, card_id: str, decision: str, now: datetime) -> SchedulingSnapshot:
        """Apply a decision to a flagged card and clear its flag.

        Args:
            card_id: The card to act on.
            decision: One of "keep", "soft_reset", "full_reset".
            now: Timestamp used as the new due date for a soft reset.

        Returns:
            A SchedulingSnapshot of the card after the change.

        Raises:
            ValidationError: If ``decision`` is not a known value.
            CardNotFoundError: If the card has no scheduling row or is not flagged.
        """
        if decision not in _DECISIONS:
            raise ValidationError(
                f"Unknown core-change decision '{decision}'. Expected one of {_DECISIONS}."
            )
        with session_scope(self.engine) as s:
            row = s.get(SchedulingState, card_id)
            if row is None or not row.core_changed:
                raise CardNotFoundError(
                    f"Card '{card_id}' is not flagged as changed — nothing to resolve. "
                    "Run a reconciliation scan, or refresh the changed-cards list."
                )
            self._apply_decision(row, decision, now)
            row.core_changed = False
            row.core_changed_at = None
            return SchedulingSnapshot(
                card_id=row.card_id,
                core_changed=False,
                state=row.state,
                stability=row.stability,
                difficulty=row.difficulty,
                due=row.due,
                reps=row.reps,
                lapses=row.lapses,
            )

    @staticmethod
    def _apply_decision(row: SchedulingState, decision: str, now: datetime) -> None:
        """Mutate FSRS fields per the decision (flag clearing handled by caller)."""
        if decision == "soft_reset":
            row.due = now
        elif decision == "full_reset":
            row.state = NEW_CARD_DEFAULTS.state
            row.stability = NEW_CARD_DEFAULTS.stability
            row.difficulty = NEW_CARD_DEFAULTS.difficulty
            row.due = NEW_CARD_DEFAULTS.due
            row.reps = NEW_CARD_DEFAULTS.reps
            row.lapses = NEW_CARD_DEFAULTS.lapses
        # "keep": no FSRS change
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_core_change.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/core_change.py tests/unit/services/test_core_change.py
git commit -m "feat(core-change): CoreChangeService.apply with keep/soft/full reset"
```

---

## Task 4: `CoreChangeService.list_changed`

**Files:**
- Modify: `src/mnemonic/services/core_change.py`
- Test: `tests/unit/services/test_core_change.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/services/test_core_change.py`:

```python
def test_list_changed_returns_only_flagged_with_kind(tmp_path: Path):
    from mnemonic.db.models import CoreChangeLog

    svc, engine = _service(tmp_path)
    _flagged_row(engine)  # card-aaaabbbb flagged, matches the seeded nash.qmd
    with session_scope(engine) as s:
        s.add(
            CoreChangeLog(
                id="log1",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )

    changed = svc.list_changed()

    assert len(changed) == 1
    item = changed[0]
    assert item.card_id == "card-aaaabbbb"
    assert item.title == "nash"
    assert item.change_kind == "material"
    assert item.stability == 12.4


def test_list_changed_uses_latest_change_kind(tmp_path: Path):
    from mnemonic.db.models import CoreChangeLog

    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    with session_scope(engine) as s:
        s.add(
            CoreChangeLog(
                id="old",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 10, 9, 0, 0),
            )
        )
        s.add(
            CoreChangeLog(
                id="new",
                card_id="card-aaaabbbb",
                change_kind="cloze_structure",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )

    assert svc.list_changed()[0].change_kind == "cloze_structure"


def test_list_changed_empty_when_none_flagged(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine, core_changed=False, core_changed_at=None)
    assert svc.list_changed() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_core_change.py::test_list_changed_returns_only_flagged_with_kind -v`
Expected: FAIL with `AttributeError: 'CoreChangeService' object has no attribute 'list_changed'`

- [ ] **Step 3: Implement `list_changed`**

In `src/mnemonic/services/core_change.py`, add these imports to the existing import block:

```python
from mnemonic.db.models import CoreChangeLog, SchedulingState
```

(Replace the existing `from mnemonic.db.models import SchedulingState` line with the line above.)

Add a module-level type alias just below the `_DECISIONS` constant near the top of the file (keeps the join helper's signature mypy-clean):

```python
# card_id -> (state, due, stability, difficulty, core_changed_at)
_FlaggedRow = tuple[str, "datetime | None", float, float, "datetime | None"]
```

Add this method to `CoreChangeService` (after `apply`, before `_apply_decision`):

```python
    def list_changed(self) -> list[ChangedCard]:
        """Return flagged cards, enriched with content and their latest change kind.

        Cards flagged but no longer present in the vault (orphaned) are skipped.
        """
        with session_scope(self.engine) as s:
            rows = (
                s.query(SchedulingState).filter(SchedulingState.core_changed.is_(True)).all()
            )
            flagged = {
                r.card_id: (r.state, r.due, r.stability, r.difficulty, r.core_changed_at)
                for r in rows
            }
            kinds = self._latest_kinds(s, list(flagged))
        return self._join_cards(flagged, kinds)

    @staticmethod
    def _latest_kinds(session, card_ids: list[str]) -> dict[str, str]:
        """Map each card_id to its most recent CoreChangeLog.change_kind."""
        if not card_ids:
            return {}
        logs = (
            session.query(CoreChangeLog)
            .filter(CoreChangeLog.card_id.in_(card_ids))
            .order_by(CoreChangeLog.detected_at.desc())
            .all()
        )
        latest: dict[str, str] = {}
        for log in logs:
            latest.setdefault(log.card_id, log.change_kind)
        return latest

    def _join_cards(
        self, flagged: dict[str, _FlaggedRow], kinds: dict[str, str]
    ) -> list[ChangedCard]:
        """Join flagged scheduling rows with vault card content."""
        cards = {c.card_id: c for c in self.repo.list_cards()}
        out: list[ChangedCard] = []
        for card_id, (state, due, stability, difficulty, changed_at) in flagged.items():
            card = cards.get(card_id)
            if card is None:
                continue
            out.append(
                ChangedCard(
                    card_id=card_id,
                    title=card.title,
                    front=card.front,
                    syntax=card.syntax,
                    change_kind=kinds.get(card_id),
                    core_changed_at=changed_at,
                    state=state,
                    due=due,
                    stability=stability,
                    difficulty=difficulty,
                )
            )
        out.sort(key=lambda c: (c.core_changed_at or datetime.min), reverse=True)
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_core_change.py -q`
Expected: PASS (9 passed — 6 from Task 3 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/core_change.py tests/unit/services/test_core_change.py
git commit -m "feat(core-change): list_changed joins flagged cards with content and kind"
```

---

## Task 5: Endpoints + deps provider

**Files:**
- Modify: `src/mnemonic/api/deps.py`, `src/mnemonic/api/routes/cards.py`
- Test: `tests/unit/api/test_cards_changed.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/api/test_cards_changed.py`:

```python
"""Tests for GET /api/cards/changed and POST /api/cards/{id}/core-change."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from mnemonic.api.deps import get_core_change_service
from mnemonic.db.models import Base, CoreChangeLog, SchedulingState
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.main import app
from mnemonic.services.core_change import CoreChangeService
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nThe {{c1::Nash}} equilibrium.\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def _flag(engine):
    with session_scope(engine) as s:
        s.add(
            SchedulingState(
                card_id="card-aaaabbbb",
                state="review",
                stability=12.4,
                difficulty=6.1,
                due=datetime(2026, 6, 20, 9, 0, 0),
                reps=5,
                lapses=1,
                leech_score=0.0,
                core_changed=True,
                core_changed_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )
        s.add(
            CoreChangeLog(
                id="log1",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )


def _override(vault, engine):
    app.dependency_overrides[get_core_change_service] = lambda: CoreChangeService(
        repo=VaultRepository(vault_root=vault, engine=engine), engine=engine
    )


def test_get_changed_returns_flagged_cards(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _flag(engine)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/cards/changed")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["card_id"] == "card-aaaabbbb"
    assert body[0]["change_kind"] == "material"
    assert body[0]["title"] == "nash"


def test_post_core_change_full_reset(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _flag(engine)
    _override(vault, engine)
    try:
        resp = TestClient(app).post(
            "/api/cards/card-aaaabbbb/core-change", json={"decision": "full_reset"}
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["core_changed"] is False
    assert body["state"] == "new" and body["stability"] == 0.0 and body["due"] is None


def test_post_core_change_unflagged_is_404(tmp_path: Path):
    vault, engine = _setup(tmp_path)  # no flag set
    _override(vault, engine)
    try:
        resp = TestClient(app).post(
            "/api/cards/card-aaaabbbb/core-change", json={"decision": "keep"}
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_post_core_change_bad_decision_is_422(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _flag(engine)
    _override(vault, engine)
    try:
        resp = TestClient(app).post(
            "/api/cards/card-aaaabbbb/core-change", json={"decision": "obliterate"}
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422  # rejected by the Literal body schema
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/api/test_cards_changed.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_core_change_service'`

- [ ] **Step 3: Add the deps provider**

In `src/mnemonic/api/deps.py`, add the import with the other service imports:

```python
from mnemonic.services.core_change import CoreChangeService
```

Add this provider at the end of the file:

```python
def get_core_change_service() -> CoreChangeService:
    return CoreChangeService(repo=get_repo(), engine=get_engine())
```

- [ ] **Step 4: Add the endpoints**

Replace the entire contents of `src/mnemonic/api/routes/cards.py` with:

```python
"""Card endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from mnemonic.api.deps import get_card_service, get_core_change_service
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.services.card import CardService
from mnemonic.services.core_change import ChangedCard, CoreChangeService, SchedulingSnapshot

router = APIRouter(prefix="/cards", tags=["cards"])


def _serialize(card) -> dict:
    return {
        "card_id": card.card_id,
        "note_path": str(card.note_path),
        "deck_folder": card.deck_folder.name,
        "syntax": card.syntax,
        "front": card.front,
        "back": card.back,
        "title": card.title,
        "state": card.state,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "due": card.due.isoformat() if card.due else None,
        "reps": card.reps,
        "lapses": card.lapses,
        "leech_score": card.leech_score,
        "suspended": card.suspended,
        "core_changed": card.core_changed,
        "core_changed_at": card.core_changed_at.isoformat() if card.core_changed_at else None,
    }


def _serialize_changed(c: ChangedCard) -> dict:
    return {
        "card_id": c.card_id,
        "title": c.title,
        "front": c.front,
        "syntax": c.syntax,
        "change_kind": c.change_kind,
        "core_changed_at": c.core_changed_at.isoformat() if c.core_changed_at else None,
        "state": c.state,
        "due": c.due.isoformat() if c.due else None,
        "stability": c.stability,
        "difficulty": c.difficulty,
    }


def _serialize_snapshot(s: SchedulingSnapshot) -> dict:
    return {
        "card_id": s.card_id,
        "core_changed": s.core_changed,
        "state": s.state,
        "stability": s.stability,
        "difficulty": s.difficulty,
        "due": s.due.isoformat() if s.due else None,
        "reps": s.reps,
        "lapses": s.lapses,
    }


class CoreChangePayload(BaseModel):
    decision: Literal["keep", "soft_reset", "full_reset"]


@router.get("")
def list_cards(deck: str | None = Query(None), svc: CardService = Depends(get_card_service)):
    return [_serialize(c) for c in svc.list(deck_folder_name=deck)]


@router.get("/changed")
def list_changed_cards(
    svc: CoreChangeService = Depends(get_core_change_service),
) -> list[dict]:
    """List cards whose core content changed since their scheduling was set."""
    return [_serialize_changed(c) for c in svc.list_changed()]


@router.post("/{card_id}/core-change")
def apply_core_change(
    card_id: str,
    payload: CoreChangePayload,
    svc: CoreChangeService = Depends(get_core_change_service),
) -> dict:
    """Apply keep / soft-reset / full-reset to a flagged card's scheduling."""
    try:
        snapshot = svc.apply(card_id=card_id, decision=payload.decision, now=datetime.now())
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_snapshot(snapshot)


@router.get("/{card_id}")
def get_card(card_id: str, svc: CardService = Depends(get_card_service)):
    c = svc.get(card_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found.")
    return _serialize(c)
```

Note: `GET /changed` is declared **before** `GET /{card_id}` so the literal path wins over the path parameter.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/api/test_cards_changed.py -q`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/api/deps.py src/mnemonic/api/routes/cards.py tests/unit/api/test_cards_changed.py
git commit -m "feat(api): GET /cards/changed and POST /cards/{id}/core-change"
```

---

## Task 6: Frontend types + API client methods

**Files:**
- Modify: `frontend/src/types/index.ts`, `frontend/src/services/api.ts`

- [ ] **Step 1: Add types**

In `frontend/src/types/index.ts`, append:

```typescript
export type CoreChangeDecision = 'keep' | 'soft_reset' | 'full_reset';

export interface ChangedCard {
  card_id: string;
  title: string;
  front: string;
  syntax: string;
  change_kind: string | null;
  core_changed_at: string | null;
  state: string;
  due: string | null;
  stability: number;
  difficulty: number;
}

export interface SchedulingSnapshot {
  card_id: string;
  core_changed: boolean;
  state: string;
  stability: number;
  difficulty: number;
  due: string | null;
  reps: number;
  lapses: number;
}
```

- [ ] **Step 2: Add API methods**

In `frontend/src/services/api.ts`, inside the `api` object after the `deleteCard` method, add:

```typescript
  /** List cards whose core content changed since scheduling was set. */
  listChangedCards: () => request<import('../types').ChangedCard[]>('/cards/changed'),

  /** Apply keep / soft-reset / full-reset to a flagged card. */
  applyCoreChange: (
    cardId: string,
    decision: import('../types').CoreChangeDecision,
  ) =>
    request<import('../types').SchedulingSnapshot>(`/cards/${cardId}/core-change`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    }),
```

- [ ] **Step 3: Verify it type-checks**

Run: `npm run build`
Expected: build succeeds (TypeScript compiles with the new types + methods).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat(frontend): ChangedCard types and core-change API methods"
```

---

## Task 7: `useChangedCards` hook

**Files:**
- Create: `frontend/src/hooks/useChangedCards.ts`
- Test: `frontend/tests/hooks/useChangedCards.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/tests/hooks/useChangedCards.test.tsx`:

```tsx
/** Tests for useChangedCards hooks. */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChangedCards, useApplyCoreChange } from '@/hooks/useChangedCards';

vi.mock('@/services/api', () => ({
  api: {
    listChangedCards: vi.fn(),
    applyCoreChange: vi.fn(),
  },
}));

import { api } from '@/services/api';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper(props: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{props.children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useChangedCards', () => {
  it('fetches changed cards', async () => {
    (api.listChangedCards as any).mockResolvedValue([{ card_id: 'card-a', title: 'A' }]);
    const { result } = renderHook(() => useChangedCards(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(api.listChangedCards).toHaveBeenCalledTimes(1);
  });
});

describe('useApplyCoreChange', () => {
  it('calls applyCoreChange with card id and decision', async () => {
    (api.applyCoreChange as any).mockResolvedValue({ card_id: 'card-a', core_changed: false });
    const { result } = renderHook(() => useApplyCoreChange(), { wrapper: createWrapper() });
    result.current.mutate({ cardId: 'card-a', decision: 'soft_reset' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.applyCoreChange).toHaveBeenCalledWith('card-a', 'soft_reset');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- useChangedCards`
Expected: FAIL — cannot resolve `@/hooks/useChangedCards`.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useChangedCards.ts`:

```typescript
/**
 * React Query hooks for the "review changed cards" panel.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
  UseMutationResult,
} from '@tanstack/react-query';
import { api } from '../services/api';
import type { ChangedCard, CoreChangeDecision, SchedulingSnapshot } from '../types';

const changedKeys = {
  all: ['changed-cards'] as const,
};

/** Fetch all cards whose core content changed since scheduling was set. */
export function useChangedCards(): UseQueryResult<ChangedCard[], Error> {
  return useQuery({
    queryKey: changedKeys.all,
    queryFn: () => api.listChangedCards(),
    staleTime: 60 * 1000,
  });
}

/** Apply keep / soft-reset / full-reset; refreshes the changed-cards list on success. */
export function useApplyCoreChange(): UseMutationResult<
  SchedulingSnapshot,
  Error,
  { cardId: string; decision: CoreChangeDecision },
  unknown
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, decision }) => api.applyCoreChange(cardId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: changedKeys.all });
    },
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- useChangedCards`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useChangedCards.ts frontend/tests/hooks/useChangedCards.test.tsx
git commit -m "feat(frontend): useChangedCards query and useApplyCoreChange mutation"
```

---

## Task 8: The panel + confirmation dialog

**Files:**
- Create: `frontend/src/pages/components/ResetConfirmationDialog.tsx`, `frontend/src/pages/ChangedCardsPage.tsx`
- Test: `frontend/tests/pages/ChangedCardsPage.test.tsx`

- [ ] **Step 1: Create the confirmation dialog**

Create `frontend/src/pages/components/ResetConfirmationDialog.tsx`:

```tsx
/** Confirmation dialog for the destructive full-reset action. */

import React from 'react';
import { Button } from '@/components/ui';

export interface ResetConfirmationDialogProps {
  cardTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

export const ResetConfirmationDialog: React.FC<ResetConfirmationDialogProps> = ({
  cardTitle,
  onConfirm,
  onCancel,
  isLoading,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Full reset?</h2>
        <p className="text-gray-600 mb-6">
          Reset <strong>{cardTitle}</strong> to new? Its review history (stability, difficulty,
          reps) will be discarded. This cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="ghost" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={isLoading} disabled={isLoading}>
            {isLoading ? 'Resetting…' : 'Full reset'}
          </Button>
        </div>
      </div>
    </div>
  );
};

ResetConfirmationDialog.displayName = 'ResetConfirmationDialog';
```

- [ ] **Step 2: Write the failing page tests**

Create `frontend/tests/pages/ChangedCardsPage.test.tsx`:

```tsx
/** Tests for ChangedCardsPage. */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const { mockUseChangedCards, mockMutate, mockUseApplyCoreChange } = vi.hoisted(() => ({
  mockUseChangedCards: vi.fn(),
  mockMutate: vi.fn(),
  mockUseApplyCoreChange: vi.fn(),
}));

vi.mock('@/hooks/useChangedCards', () => ({
  useChangedCards: mockUseChangedCards,
  useApplyCoreChange: mockUseApplyCoreChange,
}));

import { ChangedCardsPage } from '@/pages/ChangedCardsPage';

const CARD = {
  card_id: 'card-a',
  title: 'Nash equilibrium',
  front: 'What is a [...]?',
  syntax: 'cloze',
  change_kind: 'material',
  core_changed_at: '2026-06-12T09:00:00',
  state: 'review',
  due: '2026-06-20T09:00:00',
  stability: 12.4,
  difficulty: 6.1,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockMutate.mockReset();
  mockUseApplyCoreChange.mockReturnValue({ mutate: mockMutate, isPending: false, error: null });
  mockUseChangedCards.mockReturnValue({
    data: [CARD],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  });
});

describe('ChangedCardsPage', () => {
  it('renders each flagged card with its change kind', () => {
    render(<ChangedCardsPage />);
    expect(screen.getByText('Nash equilibrium')).toBeInTheDocument();
    expect(screen.getByText('material')).toBeInTheDocument();
  });

  it('Keep applies immediately with the keep decision', () => {
    render(<ChangedCardsPage />);
    fireEvent.click(screen.getByRole('button', { name: /keep/i }));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ cardId: 'card-a', decision: 'keep' }),
      expect.anything(),
    );
  });

  it('Soft reset applies immediately with the soft_reset decision', () => {
    render(<ChangedCardsPage />);
    fireEvent.click(screen.getByRole('button', { name: /soft reset/i }));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ cardId: 'card-a', decision: 'soft_reset' }),
      expect.anything(),
    );
  });

  it('Full reset asks for confirmation before mutating', async () => {
    render(<ChangedCardsPage />);
    fireEvent.click(screen.getByRole('button', { name: /full reset/i }));
    // dialog shown, no mutation yet
    expect(mockMutate).not.toHaveBeenCalled();
    expect(screen.getByText(/its review history/i)).toBeInTheDocument();
    // confirm
    fireEvent.click(screen.getByRole('button', { name: /^full reset$/i }));
    await waitFor(() =>
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ cardId: 'card-a', decision: 'full_reset' }),
        expect.anything(),
      ),
    );
  });

  it('shows the empty state when nothing is flagged', () => {
    mockUseChangedCards.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ChangedCardsPage />);
    expect(screen.getByText(/everything's in sync/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `npm test -- ChangedCardsPage`
Expected: FAIL — cannot resolve `@/pages/ChangedCardsPage`.

- [ ] **Step 4: Implement the page**

Create `frontend/src/pages/ChangedCardsPage.tsx`:

```tsx
/**
 * Review Changed Cards page.
 * Lists cards whose core content changed since scheduling was set and lets the
 * user keep / soft-reset / full-reset each card's FSRS state.
 */

import React, { useState } from 'react';
import { useChangedCards, useApplyCoreChange } from '@/hooks/useChangedCards';
import { Button, Badge, Skeleton, ErrorMessage, EmptyState } from '@/components/ui';
import { ResetConfirmationDialog } from './components/ResetConfirmationDialog';
import type { ChangedCard, CoreChangeDecision } from '@/types';

export const ChangedCardsPage: React.FC = () => {
  const { data: cards, isLoading, error, refetch } = useChangedCards();
  const { mutate: applyChange, isPending, error: applyError } = useApplyCoreChange();
  const [confirming, setConfirming] = useState<ChangedCard | null>(null);

  const apply = (cardId: string, decision: CoreChangeDecision) => {
    applyChange({ cardId, decision }, { onSuccess: () => setConfirming(null) });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto" data-testid="changed-skeleton">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">Changed Cards</h1>
          <Skeleton variant="rect" height={96} className="mb-4" />
          <Skeleton variant="rect" height={96} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">Changed Cards</h1>
          <ErrorMessage
            message={error instanceof Error ? error.message : 'Failed to load changed cards'}
            onRetry={() => refetch()}
          />
        </div>
      </div>
    );
  }

  if (!cards || cards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900 mb-8">Changed Cards</h1>
          <EmptyState
            title="No changed cards"
            description="Everything's in sync — no card cores have changed since their scheduling was set."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Changed Cards</h1>
        <p className="text-gray-600 mb-8">
          {cards.length} card{cards.length === 1 ? '' : 's'} changed since scheduling was set.
        </p>

        {applyError && (
          <div className="mb-6">
            <ErrorMessage
              message={applyError instanceof Error ? applyError.message : 'Action failed'}
            />
          </div>
        )}

        <ul className="space-y-4">
          {cards.map((card) => (
            <li key={card.card_id} className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between mb-1">
                <h2 className="font-semibold text-gray-900">{card.title}</h2>
                {card.change_kind && <Badge variant="warning">{card.change_kind}</Badge>}
              </div>
              <p className="text-gray-600 text-sm mb-3 line-clamp-2">{card.front}</p>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="ghost"
                  onClick={() => apply(card.card_id, 'keep')}
                  disabled={isPending}
                >
                  Keep
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => apply(card.card_id, 'soft_reset')}
                  disabled={isPending}
                >
                  Soft reset
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setConfirming(card)}
                  disabled={isPending}
                >
                  Full reset
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {confirming && (
        <ResetConfirmationDialog
          cardTitle={confirming.title}
          onConfirm={() => apply(confirming.card_id, 'full_reset')}
          onCancel={() => setConfirming(null)}
          isLoading={isPending}
        />
      )}
    </div>
  );
};

ChangedCardsPage.displayName = 'ChangedCardsPage';
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npm test -- ChangedCardsPage`
Expected: PASS (5 passed)

Note: if the `Button` component does not accept a `"secondary"` variant, use `"primary"` for the Soft-reset button instead — check `frontend/src/components/ui/Button.tsx` for the allowed variants and adjust the page + this note before committing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ChangedCardsPage.tsx frontend/src/pages/components/ResetConfirmationDialog.tsx frontend/tests/pages/ChangedCardsPage.test.tsx
git commit -m "feat(frontend): review-changed-cards panel with reset confirmation"
```

---

## Task 9: Wire route + navigation

**Files:**
- Modify: `frontend/src/App.tsx`, `frontend/src/components/Navigation.tsx`

- [ ] **Step 1: Add the route**

In `frontend/src/App.tsx`, add the import with the other page imports:

```typescript
import { ChangedCardsPage } from './pages/ChangedCardsPage';
```

Add the route inside `<Routes>`/`<Route element={<AppLayout />}>`, after the `/decks/:folder` route:

```tsx
            <Route path="/changed" element={<ChangedCardsPage />} />
```

- [ ] **Step 2: Add the nav link**

In `frontend/src/components/Navigation.tsx`, add the link after the Decks link:

```tsx
      <NavLink to="/decks">Decks</NavLink>
      <NavLink to="/changed">Changed Cards</NavLink>
```

- [ ] **Step 3: Verify build + full frontend test run**

Run: `npm run build && npm test -- --run`
Expected: build succeeds; all frontend tests pass (including the new hook + page tests).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Navigation.tsx
git commit -m "feat(frontend): route and nav entry for Changed Cards panel"
```

---

## Task 10: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite**

Run (from `backend/`): `uv run pytest -q`
Expected: PASS except the 3 known pre-existing `tests/test_setup.py` failures (`redis`/`jose`/`passlib` not installed). No other failures.

- [ ] **Step 2: Backend lint + types on new/changed files**

Run (from `backend/`):

```bash
uv run ruff check src/mnemonic/services/core_change.py src/mnemonic/core/fsrs/defaults.py src/mnemonic/api/routes/cards.py src/mnemonic/api/deps.py
uv run black --check src/mnemonic/services/core_change.py src/mnemonic/core/fsrs/defaults.py src/mnemonic/api/routes/cards.py
uv run mypy src/mnemonic/services/core_change.py src/mnemonic/core/fsrs/defaults.py
```

Expected: ruff clean (ignore the pre-existing `lint.select`/`lint.ignore` pyproject deprecation warning); black clean; mypy clean.

- [ ] **Step 2b: Backend coverage on the new service**

Run (from `backend/`): `uv run pytest --cov=mnemonic.services.core_change --cov=mnemonic.core.fsrs.defaults --cov-report=term-missing tests/unit/services/test_core_change.py tests/unit/core/test_new_card_defaults.py -q`
Expected: `core_change` and `defaults` at or above 95%.

- [ ] **Step 3: Frontend build, lint, tests**

Run (from `frontend/`):

```bash
npm run build
npm run lint
npm test -- --run
```

Expected: build succeeds; lint clean on new files; all tests pass.

- [ ] **Step 4: Final commit (only if lint/type fixes were made)**

```bash
git add -A
git commit -m "chore(review-changed-cards): lint and type fixes"
```

---

## Notes for the implementer

- **FastAPI route order:** `GET /cards/changed` MUST be registered before `GET /cards/{card_id}` (Task 5 does this) — otherwise `changed` is captured as a `card_id`.
- **No FSRS reset in reconciliation:** this feature is the *only* place that touches FSRS in response to a core change; reconciliation still only flags. Keep it that way.
- **`ValidationError` vs Pydantic:** the endpoint's `Literal` body schema already rejects bad decisions with 422, so the service's `ValidationError` path is defensive depth (still unit-tested at the service layer in Task 3).
- **Button variants:** verify the allowed `Button` variant names in `frontend/src/components/ui/Button.tsx` before finalizing Task 8 (the plan assumes `ghost`, `secondary`, `danger`, `primary`); adjust the Soft-reset button's variant if `secondary` is not available.
- **Legacy frontend `Card` type:** the existing `types/index.ts` `Card` is a stale camelCase shape unrelated to this feature — do not reuse it; the new `ChangedCard` type matches the backend JSON (snake_case) directly.
