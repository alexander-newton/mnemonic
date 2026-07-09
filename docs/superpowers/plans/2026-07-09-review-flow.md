# Review/Study Flow (B1-Loop) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working review loop — pick due cards for a deck, show the front, reveal the answer, rate 1–4 — plus first-time Tailwind styling with a warm muted theme and a configurable font.

**Architecture:** Backend adds a due-queue behind a `ReviewPolicy` seam (`SimplePolicy` now), clean markdown card faces, per-rating preview intervals, and `GET /reviews/queue`; rating reuses the existing `POST /reviews/rate`. Frontend wires up Tailwind (currently referenced but never installed), applies a warm theme + font picker, and adds a `/study/:folder` screen rendering markdown+math via react-markdown + KaTeX.

**Tech Stack:** Backend — Python 3.11, SQLAlchemy, FastAPI, pytest, `uv`. Frontend — React 18, TypeScript, TanStack Query, Vitest + RTL, Tailwind (new), react-markdown/remark-math/rehype-katex, `npm`.

Backend commands run from `backend/`; frontend from `frontend/`. Spec: `docs/superpowers/specs/2026-07-09-review-flow-design.md`.

---

## File Structure

**Backend — create:** `src/mnemonic/core/review/__init__.py`, `src/mnemonic/core/review/faces.py`, `src/mnemonic/core/fsrs/state.py`, `src/mnemonic/services/review_queue.py`.
**Backend — modify:** `src/mnemonic/services/review.py` (use shared `to_card_state`), `src/mnemonic/api/routes/reviews.py` (add `GET /queue`), `src/mnemonic/api/deps.py` (queue provider).
**Frontend — create:** `postcss.config.js`, `tailwind.config.js`, `src/index.css`, `src/hooks/useFontPreference.ts`, `src/components/review/CardContent.tsx`, `src/components/review/RatingButtons.tsx`, `src/hooks/useReviewQueue.ts`, `src/pages/StudyPage.tsx`.
**Frontend — modify:** `src/main.tsx` (import css), `src/pages/SettingsPage.tsx` (font dropdown), `src/services/api.ts` (`reviewQueue`), `src/types/index.ts` (`QueuedCard`), `src/App.tsx` (route), `src/pages/DeckDetailPage.tsx` (Study button), `package.json` (deps), and a bounded `bg-gray-50`/`bg-white` sweep on existing pages.

---

# Phase 1 — Backend

## Task 1: Card faces (reveal)

**Files:**
- Create: `src/mnemonic/core/review/__init__.py`, `src/mnemonic/core/review/faces.py`
- Test: `tests/unit/core/review/__init__.py`, `tests/unit/core/review/test_faces.py`

- [ ] **Step 1: Create package markers**

Create `src/mnemonic/core/review/__init__.py`:
```python
"""Pure review-display logic (card faces)."""
```
Create empty `tests/unit/core/review/__init__.py` (no content).

- [ ] **Step 2: Write the failing tests** — Create `tests/unit/core/review/test_faces.py`:

```python
"""Tests for building review faces (question + revealed answer)."""

from __future__ import annotations

import pytest

from mnemonic.core.review.faces import build_faces
from mnemonic.exceptions import RenderError


def test_cloze_answer_reveals_markers_in_bold():
    faces = build_faces(
        syntax="cloze",
        front="The [...] is the powerhouse. ^card-aaaabbbb",
        back="The {{c1::mitochondria}} is the powerhouse. ^card-aaaabbbb",
    )
    assert faces.front == "The [...] is the powerhouse."
    assert faces.answer == "The **mitochondria** is the powerhouse."


def test_cloze_math_is_untouched():
    faces = build_faces(
        syntax="cloze",
        front="Derivative of $x^2$ is [...]",
        back="Derivative of $x^2$ is {{c1::2x}}",
    )
    assert faces.answer == "Derivative of $x^2$ is **2x**"


def test_highlight_answer_passes_through():
    faces = build_faces(
        syntax="highlight",
        front="A [...] equilibrium.",
        back="A Nash equilibrium.",
    )
    assert faces.front == "A [...] equilibrium."
    assert faces.answer == "A Nash equilibrium."


def test_callout_answer_passes_through():
    faces = build_faces(syntax="callout", front="What is NE?", back="A stable strategy profile.")
    assert faces.answer == "A stable strategy profile."


def test_unknown_syntax_raises():
    with pytest.raises(RenderError):
        build_faces(syntax="image_cloze", front="x", back="y")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/review/test_faces.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.review.faces'`

- [ ] **Step 4: Implement `faces.py`** — Create `src/mnemonic/core/review/faces.py`:

```python
"""Build the two display faces of a card: the question and the revealed answer.

Output is clean markdown (math untouched, block-ID token removed). Cloze answers are
revealed in bold; highlight/callout backs are already revealed and pass through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mnemonic.exceptions import RenderError

_CLOZE_RE = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")
_BLOCK_ID_RE = re.compile(r"\^card-[0-9a-z]+")


@dataclass(frozen=True)
class ReviewFaces:
    """The question face and the revealed-answer face, both clean markdown."""

    front: str
    answer: str


def _strip_block_id(text: str) -> str:
    return _BLOCK_ID_RE.sub("", text).strip()


def build_faces(*, syntax: str, front: str, back: str) -> ReviewFaces:
    """Produce (front, answer) markdown faces for a card.

    Args:
        syntax: "cloze" | "highlight" | "callout".
        front: The blanked question text from the extractor.
        back: The extractor's back text (raw cloze markers for cloze; revealed otherwise).

    Returns:
        ReviewFaces with block-ID-stripped, revealed markdown.

    Raises:
        RenderError: If ``syntax`` is not a supported display syntax.
    """
    if syntax == "cloze":
        answer = _CLOZE_RE.sub(lambda m: f"**{m.group(2)}**", back)
    elif syntax in ("highlight", "callout"):
        answer = back
    else:
        raise RenderError(
            f"Cannot build review faces for unsupported card syntax '{syntax}'."
        )
    return ReviewFaces(front=_strip_block_id(front), answer=_strip_block_id(answer))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/review/test_faces.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/core/review/ tests/unit/core/review/
git commit -m "feat(review): pure card faces (question + revealed answer markdown)"
```

---

## Task 2: Extract shared `to_card_state`

**Files:**
- Create: `src/mnemonic/core/fsrs/state.py`
- Test: `tests/unit/core/test_card_state.py`
- Modify: `src/mnemonic/services/review.py`

- [ ] **Step 1: Write the failing test** — Create `tests/unit/core/test_card_state.py`:

```python
"""Tests for the shared CardState builder."""

from __future__ import annotations

from datetime import datetime

from mnemonic.core.fsrs.state import to_card_state


def test_new_card_has_zero_elapsed_and_no_last_review():
    now = datetime(2026, 7, 9, 12, 0, 0)
    st = to_card_state(
        stability=0.0, difficulty=5.0, reps=0, lapses=0, state="new",
        due=None, last_review=None, now=now,
    )
    assert st.elapsed_days == 0.0 and st.scheduled_days == 0.0 and st.last_review is None
    assert st.state == "new" and st.difficulty == 5.0


def test_elapsed_and_scheduled_derived_from_last_review():
    now = datetime(2026, 7, 9, 12, 0, 0)
    last = datetime(2026, 7, 4, 12, 0, 0)   # 5 days before now
    due = datetime(2026, 7, 8, 12, 0, 0)    # 4 days after last
    st = to_card_state(
        stability=10.0, difficulty=6.0, reps=3, lapses=1, state="review",
        due=due, last_review=last, now=now,
    )
    assert st.elapsed_days == 5.0
    assert st.scheduled_days == 4.0
    assert st.last_review == last
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_card_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.fsrs.state'`

- [ ] **Step 3: Create `state.py`** — Create `src/mnemonic/core/fsrs/state.py`:

```python
"""Build an FSRS CardState from stored scheduling fields plus the last review time."""

from __future__ import annotations

from datetime import datetime

from mnemonic.core.fsrs.models import CardState


def to_card_state(
    *,
    stability: float,
    difficulty: float,
    reps: int,
    lapses: int,
    state: str,
    due: datetime | None,
    last_review: datetime | None,
    now: datetime,
) -> CardState:
    """Construct a CardState, deriving elapsed/scheduled days from the last review.

    Args:
        stability, difficulty, reps, lapses, state: Stored FSRS fields.
        due: The card's current due date (or None for a new card).
        last_review: Timestamp of the last review (or None).
        now: Current time, used to compute elapsed days.

    Returns:
        A CardState suitable for schedule_review / preview_schedule.
    """
    if last_review is None:
        elapsed = 0.0
    else:
        elapsed = max(0.0, (now - last_review).total_seconds() / 86400.0)
    scheduled = 0.0
    if due is not None and last_review is not None:
        scheduled = max(0.0, (due - last_review).total_seconds() / 86400.0)
    return CardState(
        stability=stability,
        difficulty=difficulty,
        elapsed_days=elapsed,
        scheduled_days=scheduled,
        reps=reps,
        lapses=lapses,
        state=state,
        last_review=last_review,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/core/test_card_state.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Refactor `review.py` to use it** — In `src/mnemonic/services/review.py`, add the import after `from mnemonic.core.fsrs.scheduler import schedule_review`:

```python
from mnemonic.core.fsrs.state import to_card_state
```

Replace the entire body of `_to_fsrs_state` (the function that builds a `CardState` from a row) with a delegation:

```python
def _to_fsrs_state(row: SchedulingState, last_review: datetime | None) -> CardState:
    return to_card_state(
        stability=row.stability,
        difficulty=row.difficulty,
        reps=row.reps,
        lapses=row.lapses,
        state=row.state,
        due=row.due,
        last_review=last_review,
        now=datetime.now(),
    )
```

- [ ] **Step 6: Run review tests for regressions**

Run: `uv run pytest tests/unit/services -q`
Expected: PASS (existing review tests still pass).

- [ ] **Step 7: Commit**

```bash
git add src/mnemonic/core/fsrs/state.py tests/unit/core/test_card_state.py src/mnemonic/services/review.py
git commit -m "refactor(fsrs): extract shared to_card_state; review.py delegates to it"
```

---

## Task 3: `SimplePolicy` (queue ordering)

**Files:**
- Create: `src/mnemonic/services/review_queue.py`
- Test: `tests/unit/services/test_review_queue.py`

- [ ] **Step 1: Write the failing tests** — Create `tests/unit/services/test_review_queue.py`:

```python
"""Tests for the review-queue policy and service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.services.review_queue import SimplePolicy
from mnemonic.vault.repository import Card

NOW = datetime(2026, 7, 9, 12, 0, 0)


def _card(cid, *, state="review", due=None, suspended=False):
    return Card(
        card_id=cid, note_path=Path("n.qmd"), deck_folder=Path("gt"), syntax="cloze",
        front="f", back="b", title="t", state=state, stability=1.0, difficulty=5.0,
        due=due, reps=0, lapses=0, leech_score=0.0, suspended=suspended,
        core_changed=False, core_changed_at=None,
    )


def test_due_cards_ordered_by_due_then_new_appended():
    cards = [
        _card("new1", state="new"),
        _card("due-late", due=datetime(2026, 7, 9, 10, 0, 0)),
        _card("due-early", due=datetime(2026, 7, 8, 10, 0, 0)),
    ]
    out = SimplePolicy().build_queue(cards, NOW, daily_new_limit=10)
    assert [c.card_id for c in out] == ["due-early", "due-late", "new1"]


def test_suspended_and_future_due_excluded():
    cards = [
        _card("suspended", due=datetime(2026, 7, 8, 0, 0, 0), suspended=True),
        _card("future", due=datetime(2026, 7, 20, 0, 0, 0)),
        _card("due", due=datetime(2026, 7, 9, 0, 0, 0)),
    ]
    out = SimplePolicy().build_queue(cards, NOW, daily_new_limit=10)
    assert [c.card_id for c in out] == ["due"]


def test_new_cards_capped_by_daily_new_limit():
    cards = [_card(f"new{i}", state="new") for i in range(5)]
    out = SimplePolicy().build_queue(cards, NOW, daily_new_limit=2)
    assert len(out) == 2 and all(c.state == "new" for c in out)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.services.review_queue'`

- [ ] **Step 3: Implement the policy** — Create `src/mnemonic/services/review_queue.py`:

```python
"""Review queue: build an ordered list of cards to review for a deck.

`ReviewPolicy` is the seam the future cascading-rules engine (B1-Policy) plugs into.
`SimplePolicy` is the B1-Loop placeholder: due review cards ordered by due, then new
cards capped at the deck's daily_new_limit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mnemonic.vault.repository import Card


class ReviewPolicy(Protocol):
    """Produces the ordered set of cards to review now."""

    def build_queue(
        self, cards: list[Card], now: datetime, daily_new_limit: int
    ) -> list[Card]: ...


class SimplePolicy:
    """Due review cards (by due asc) then new cards capped at daily_new_limit."""

    def build_queue(
        self, cards: list[Card], now: datetime, daily_new_limit: int
    ) -> list[Card]:
        due = [
            c
            for c in cards
            if not c.suspended and c.state != "new" and c.due is not None and c.due <= now
        ]
        due.sort(key=lambda c: c.due)
        new = [c for c in cards if not c.suspended and c.state == "new"][:daily_new_limit]
        return due + new
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_queue.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review_queue.py tests/unit/services/test_review_queue.py
git commit -m "feat(review): ReviewPolicy seam + SimplePolicy queue ordering"
```

---

## Task 4: `QueueService` (faces + previews)

**Files:**
- Modify: `src/mnemonic/services/review_queue.py`
- Test (append): `tests/unit/services/test_review_queue.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/services/test_review_queue.py`:

```python
def test_queue_service_builds_items(tmp_path):
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
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(repo=VaultRepository(vault_root=vault, engine=engine), engine=engine)

    items = svc.build("gt")

    assert len(items) == 1
    item = items[0]
    assert item.card_id == "card-aaaabbbb"
    assert item.front == "A [...] equilibrium."
    assert item.answer == "A **Nash** equilibrium."
    assert set(item.previews.keys()) == {1, 2, 3, 4}
    assert all(isinstance(v, int) for v in item.previews.values())


def test_queue_service_unknown_deck_raises(tmp_path):
    from mnemonic.db.models import Base
    from mnemonic.db.sqlite import create_engine
    from mnemonic.exceptions import DeckNotFoundError
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(repo=VaultRepository(vault_root=vault, engine=engine), engine=engine)

    import pytest

    with pytest.raises(DeckNotFoundError):
        svc.build("nope")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py::test_queue_service_builds_items -v`
Expected: FAIL with `ImportError: cannot import name 'QueueService'`

- [ ] **Step 3: Implement `QueueService`** — In `src/mnemonic/services/review_queue.py`, extend the imports:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import Engine

from mnemonic.core.fsrs.preview import preview_schedule
from mnemonic.core.fsrs.state import to_card_state
from mnemonic.core.review.faces import build_faces
from mnemonic.db.models import ReviewLog
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import DeckNotFoundError
from mnemonic.vault.repository import Card, VaultRepository
```

(Replace the existing lone `from datetime import datetime` / `from typing import Protocol` / `from mnemonic.vault.repository import Card` lines with the block above.)

Add a default and the `QueuedCard` dataclass + `QueueService` at the end of the file:

```python
_DEFAULT_NEW_LIMIT = 20


@dataclass(frozen=True)
class QueuedCard:
    """One card ready to review: both faces plus per-rating preview intervals (days)."""

    card_id: str
    syntax: str
    front: str
    answer: str
    previews: dict[int, int]


class QueueService:
    """Build an ordered, display-ready review queue for a deck."""

    def __init__(
        self, *, repo: VaultRepository, engine: Engine, policy: ReviewPolicy | None = None
    ) -> None:
        self.repo = repo
        self.engine = engine
        self.policy = policy or SimplePolicy()

    def build(self, deck_folder: str) -> list[QueuedCard]:
        """Resolve the deck, order its cards by policy, and build display items.

        Raises:
            DeckNotFoundError: If no deck folder with that name exists.
        """
        now = datetime.now()
        deck = next((d for d in self.repo.list_decks() if d.folder.name == deck_folder), None)
        if deck is None:
            raise DeckNotFoundError(
                f"Deck '{deck_folder}' not found in the vault. Check the deck folder name."
            )
        cards = [c for c in self.repo.list_cards() if c.deck_folder.name == deck_folder]
        limit = deck.config.daily_new_limit if deck.config else _DEFAULT_NEW_LIMIT
        ordered = self.policy.build_queue(cards, now, limit)
        last_reviews = self._last_reviews([c.card_id for c in ordered])
        return [self._to_item(c, last_reviews.get(c.card_id), now) for c in ordered]

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_queue.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review_queue.py tests/unit/services/test_review_queue.py
git commit -m "feat(review): QueueService builds faces + preview intervals per card"
```

---

## Task 5: `GET /reviews/queue` endpoint

**Files:**
- Modify: `src/mnemonic/api/deps.py`, `src/mnemonic/api/routes/reviews.py`
- Test: `tests/unit/api/test_review_queue.py`

- [ ] **Step 1: Write the failing tests** — Create `tests/unit/api/test_review_queue.py`:

```python
"""Tests for GET /api/reviews/queue."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mnemonic.api.deps import get_queue_service
from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.main import app
from mnemonic.services.review_queue import QueueService
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "_deck.md").write_text(
        "---\ndeck_name: GT\nvariation_enabled: false\nvariation_frequency: 0.0\n"
        "leech_threshold: 8\ndaily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def _override(vault, engine):
    app.dependency_overrides[get_queue_service] = lambda: QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine), engine=engine
    )


def test_queue_returns_items(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["card_id"] == "card-aaaabbbb"
    assert body[0]["front"] == "A [...] equilibrium."
    assert body[0]["answer"] == "A **Nash** equilibrium."
    assert set(body[0]["previews"].keys()) == {"1", "2", "3", "4"}


def test_queue_unknown_deck_404(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=nope")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/api/test_review_queue.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_queue_service'`

- [ ] **Step 3: Add the deps provider** — In `src/mnemonic/api/deps.py`, add the import with the other service imports:

```python
from mnemonic.services.review_queue import QueueService
```

Add at the end of the file:

```python
def get_queue_service() -> QueueService:
    return QueueService(repo=get_repo(), engine=get_engine())
```

- [ ] **Step 4: Add the endpoint** — Replace the entire contents of `src/mnemonic/api/routes/reviews.py` with:

```python
"""Review endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mnemonic.api.deps import get_engine, get_queue_service, get_repo
from mnemonic.exceptions import CardNotFoundError, DeckNotFoundError, InvalidRatingError, RenderError
from mnemonic.services.review import ReviewService
from mnemonic.services.review_queue import QueuedCard, QueueService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class RatePayload(BaseModel):
    card_id: str
    rating: int = Field(..., ge=1, le=4)
    response_time_ms: int = Field(..., ge=0)
    variation_id: str | None = None
    variation_helpful: int | None = None


def _serialize_queued(q: QueuedCard) -> dict:
    return {
        "card_id": q.card_id,
        "syntax": q.syntax,
        "front": q.front,
        "answer": q.answer,
        "previews": {str(rating): days for rating, days in q.previews.items()},
    }


@router.get("/queue")
def review_queue(
    deck: str, svc: QueueService = Depends(get_queue_service)
) -> list[dict]:
    """Return the ordered, display-ready review queue for a deck."""
    try:
        items = svc.build(deck)
    except DeckNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RenderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [_serialize_queued(q) for q in items]


@router.post("/rate")
def rate(payload: RatePayload, repo=Depends(get_repo), engine=Depends(get_engine)):
    """Record a card review rating."""
    svc = ReviewService(repo=repo, engine=engine)
    try:
        svc.rate(
            card_id=payload.card_id,
            rating=payload.rating,
            response_time_ms=payload.response_time_ms,
            variation_id=payload.variation_id,
            variation_helpful=payload.variation_helpful,
        )
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidRatingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/api/test_review_queue.py tests/unit/api -q`
Expected: PASS (new queue tests + existing api tests, no regressions).

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/api/deps.py src/mnemonic/api/routes/reviews.py tests/unit/api/test_review_queue.py
git commit -m "feat(api): GET /reviews/queue returning display-ready queue items"
```

---

# Phase 2 — Frontend styling (Tailwind + theme + font)

## Task 6: Wire up Tailwind + warm theme

**Files:**
- Create: `frontend/postcss.config.js`, `frontend/tailwind.config.js`, `frontend/src/index.css`
- Modify: `frontend/src/main.tsx`, `frontend/package.json` (via install)

- [ ] **Step 1: Install Tailwind toolchain**

Run (from `frontend/`): `npm install -D tailwindcss@^3 postcss autoprefixer`
Expected: the three packages are added to `devDependencies`.

- [ ] **Step 2: Create `postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 3: Create `tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: 'var(--app-bg)',
        surface: 'var(--app-surface)',
        muted: 'var(--app-text-muted)',
        'border-app': 'var(--app-border)',
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 4: Create `src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --app-bg: #f4f2ee;
  --app-surface: #faf9f6;
  --app-text: #1f2328;
  --app-text-muted: #5a5f66;
  --app-border: #e5e1d8;
  --app-font: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}

body {
  background-color: var(--app-bg);
  color: var(--app-text);
  font-family: var(--app-font);
}
```

- [ ] **Step 5: Import the stylesheet** — In `frontend/src/main.tsx`, add as the first import:

```typescript
import './index.css';
```

- [ ] **Step 6: Verify the CSS pipeline builds**

Run (from `frontend/`): `npm run build`
Expected: build succeeds and emits a CSS asset (look for `dist/assets/*.css` in the output). If no `.css` asset appears, Tailwind is not wired — recheck the config/import before continuing.

- [ ] **Step 7: Commit**

```bash
git add frontend/postcss.config.js frontend/tailwind.config.js frontend/src/index.css frontend/src/main.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): wire up Tailwind + warm muted theme tokens"
```

---

## Task 7: Warm-theme sweep of existing pages

**Files:**
- Modify: existing pages using `bg-gray-50` / `bg-white` top-level wrappers.

- [ ] **Step 1: Find the wrappers to swap**

Run (from `frontend/`): `grep -rn "bg-gray-50\|bg-white" src/pages src/layouts src/components/Navigation.tsx`
Note each top-level page/card wrapper occurrence.

- [ ] **Step 2: Swap page/card backgrounds to theme tokens**

For each top-level page container className, replace `bg-gray-50` with `bg-app`, and for card/surface containers replace `bg-white` with `bg-surface`. Do this across `src/pages/*.tsx`, `src/layouts/*.tsx`, and `src/pages/components/*.tsx`. Example (DeckListPage):

```tsx
// before
<div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
// after
<div className="min-h-screen bg-app py-8 px-4 sm:px-6 lg:px-8">
```

Leave semantic colors that should stay (e.g. `bg-red-*` error, `bg-blue-*` accents) untouched — only swap the neutral page/surface backgrounds.

- [ ] **Step 3: Verify build + existing tests**

Run (from `frontend/`): `npm run build && npm test -- --run`
Expected: build succeeds; test totals unchanged from before this task (the one pre-existing `DeckDetailPage.test.tsx` failure may remain — it is unrelated; confirm no NEW failures).

- [ ] **Step 4: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): apply warm theme tokens to existing page backgrounds"
```

---

## Task 8: Configurable font (hook + Settings dropdown)

**Files:**
- Create: `frontend/src/hooks/useFontPreference.ts`
- Test: `frontend/tests/hooks/useFontPreference.test.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`, `frontend/src/main.tsx`

- [ ] **Step 1: Write the failing tests** — Create `frontend/tests/hooks/useFontPreference.test.tsx`:

```tsx
/** Tests for the font-preference hook. */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useFontPreference, FONT_OPTIONS } from '@/hooks/useFontPreference';

beforeEach(() => {
  localStorage.clear();
  document.documentElement.style.removeProperty('--app-font');
});

describe('useFontPreference', () => {
  it('defaults to the first option and sets the CSS variable', () => {
    const { result } = renderHook(() => useFontPreference());
    expect(result.current.font).toBe(FONT_OPTIONS[0].value);
    expect(document.documentElement.style.getPropertyValue('--app-font')).toBe(
      FONT_OPTIONS[0].value,
    );
  });

  it('persists a change to localStorage and updates the variable', () => {
    const { result } = renderHook(() => useFontPreference());
    const serif = FONT_OPTIONS.find((o) => o.label === 'Serif')!;
    act(() => result.current.setFont(serif.value));
    expect(result.current.font).toBe(serif.value);
    expect(localStorage.getItem('mnemonic.font')).toBe(serif.value);
    expect(document.documentElement.style.getPropertyValue('--app-font')).toBe(serif.value);
  });

  it('reads a previously stored value on mount', () => {
    const mono = FONT_OPTIONS.find((o) => o.label === 'Monospace')!;
    localStorage.setItem('mnemonic.font', mono.value);
    const { result } = renderHook(() => useFontPreference());
    expect(result.current.font).toBe(mono.value);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --run useFontPreference`
Expected: FAIL — cannot resolve `@/hooks/useFontPreference`.

- [ ] **Step 3: Implement the hook** — Create `frontend/src/hooks/useFontPreference.ts`:

```typescript
/** Reads/writes the user's font choice and applies it as the --app-font CSS variable. */

import { useCallback, useEffect, useState } from 'react';

export interface FontOption {
  label: string;
  value: string;
}

export const FONT_OPTIONS: FontOption[] = [
  { label: 'System sans', value: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" },
  { label: 'Humanist sans', value: "'Segoe UI', Roboto, 'Helvetica Neue', sans-serif" },
  { label: 'Serif', value: "Georgia, 'Times New Roman', serif" },
  { label: 'Monospace', value: "'JetBrains Mono', 'Courier New', monospace" },
];

const STORAGE_KEY = 'mnemonic.font';

function applyFont(value: string): void {
  document.documentElement.style.setProperty('--app-font', value);
}

export function useFontPreference(): { font: string; setFont: (value: string) => void } {
  const [font, setFontState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? FONT_OPTIONS[0].value,
  );

  useEffect(() => {
    applyFont(font);
  }, [font]);

  const setFont = useCallback((value: string) => {
    localStorage.setItem(STORAGE_KEY, value);
    setFontState(value);
  }, []);

  return { font, setFont };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test -- --run useFontPreference`
Expected: PASS (3 passed)

- [ ] **Step 5: Apply the font at app startup** — In `frontend/src/main.tsx`, after the `import './index.css';` line, add:

```typescript
const savedFont = localStorage.getItem('mnemonic.font');
if (savedFont) document.documentElement.style.setProperty('--app-font', savedFont);
```

- [ ] **Step 6: Add the Settings dropdown** — In `frontend/src/pages/SettingsPage.tsx`, add the import at the top:

```typescript
import { useFontPreference, FONT_OPTIONS } from '../hooks/useFontPreference';
```

Inside `SettingsPage`, call the hook at the top of the component body:

```typescript
  const { font, setFont } = useFontPreference();
```

And add an Appearance section just before the closing `</section>`:

```tsx
      <h2>Appearance</h2>
      <label htmlFor="font-select">Font</label>
      <select
        id="font-select"
        value={font}
        onChange={(e) => setFont(e.target.value)}
      >
        {FONT_OPTIONS.map((opt) => (
          <option key={opt.label} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
```

Note: the `useQuery` early-return `if (isLoading || !data) return <div>Loading…</div>;` sits above this — move the `useFontPreference()` call ABOVE that early return so the hook always runs (React hook rules).

- [ ] **Step 7: Verify build + tests**

Run: `npm run build && npm test -- --run useFontPreference`
Expected: build succeeds; hook tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useFontPreference.ts frontend/tests/hooks/useFontPreference.test.tsx frontend/src/pages/SettingsPage.tsx frontend/src/main.tsx
git commit -m "feat(frontend): configurable font via Settings dropdown (--app-font)"
```

---

# Phase 3 — Frontend review UI

## Task 9: `CardContent` (markdown + math)

**Files:**
- Create: `frontend/src/components/review/CardContent.tsx`
- Test: `frontend/tests/components/CardContent.test.tsx`
- Modify: `frontend/package.json` (via install)

- [ ] **Step 1: Install rendering deps**

Run (from `frontend/`): `npm install react-markdown remark-math rehype-katex katex`
Expected: four packages added to `dependencies`.

- [ ] **Step 2: Write the failing test** — Create `frontend/tests/components/CardContent.test.tsx`:

```tsx
/** Tests for the CardContent markdown+math renderer. */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CardContent } from '@/components/review/CardContent';

describe('CardContent', () => {
  it('renders markdown emphasis', () => {
    render(<CardContent markdown="A **Nash** equilibrium." />);
    expect(screen.getByText('Nash').tagName).toBe('STRONG');
  });

  it('renders inline math via KaTeX', () => {
    const { container } = render(<CardContent markdown={'Derivative of $x^2$'} />);
    expect(container.querySelector('.katex')).not.toBeNull();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm test -- --run CardContent`
Expected: FAIL — cannot resolve `@/components/review/CardContent`.

- [ ] **Step 4: Implement the component** — Create `frontend/src/components/review/CardContent.tsx`:

```tsx
/** Renders card-face markdown with inline/display math via KaTeX. */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

export interface CardContentProps {
  markdown: string;
}

export const CardContent: React.FC<CardContentProps> = ({ markdown }) => {
  return (
    <div className="prose max-w-none text-app">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
};

CardContent.displayName = 'CardContent';
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- --run CardContent`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/review/CardContent.tsx frontend/tests/components/CardContent.test.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): CardContent renders markdown + KaTeX math"
```

---

## Task 10: Queue types + hook

**Files:**
- Modify: `frontend/src/types/index.ts`, `frontend/src/services/api.ts`
- Create: `frontend/src/hooks/useReviewQueue.ts`
- Test: `frontend/tests/hooks/useReviewQueue.test.tsx`

- [ ] **Step 1: Add the type** — Append to `frontend/src/types/index.ts`:

```typescript
export interface QueuedCard {
  card_id: string;
  syntax: string;
  front: string;
  answer: string;
  previews: Record<string, number>;
}
```

- [ ] **Step 2: Add the API method** — In `frontend/src/services/api.ts`, inside the `api` object (after `applyCoreChange`), add:

```typescript
  /** Fetch the review queue for a deck. */
  reviewQueue: (deck: string) =>
    request<import('../types').QueuedCard[]>(`/reviews/queue?deck=${encodeURIComponent(deck)}`),
```

- [ ] **Step 3: Write the failing test** — Create `frontend/tests/hooks/useReviewQueue.test.tsx`:

```tsx
/** Tests for useReviewQueue. */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useReviewQueue } from '@/hooks/useReviewQueue';

vi.mock('@/services/api', () => ({ api: { reviewQueue: vi.fn() } }));
import { api } from '@/services/api';

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => vi.clearAllMocks());

describe('useReviewQueue', () => {
  it('fetches the queue for a deck', async () => {
    (api.reviewQueue as any).mockResolvedValue([{ card_id: 'c1' }]);
    const { result } = renderHook(() => useReviewQueue('gt'), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(api.reviewQueue).toHaveBeenCalledWith('gt');
  });

  it('is disabled without a deck', () => {
    const { result } = renderHook(() => useReviewQueue(undefined), { wrapper: wrapper() });
    expect(result.current.fetchStatus).toBe('idle');
    expect(api.reviewQueue).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `npm test -- --run useReviewQueue`
Expected: FAIL — cannot resolve `@/hooks/useReviewQueue`.

- [ ] **Step 5: Implement the hook** — Create `frontend/src/hooks/useReviewQueue.ts`:

```typescript
/** React Query hook for a deck's review queue. */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { api } from '../services/api';
import type { QueuedCard } from '../types';

export function useReviewQueue(deck?: string): UseQueryResult<QueuedCard[], Error> {
  return useQuery({
    queryKey: ['review-queue', deck],
    queryFn: () => {
      if (!deck) throw new Error('Deck is required');
      return api.reviewQueue(deck);
    },
    enabled: !!deck,
    staleTime: 0,
  });
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `npm test -- --run useReviewQueue`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts frontend/src/hooks/useReviewQueue.ts frontend/tests/hooks/useReviewQueue.test.tsx
git commit -m "feat(frontend): QueuedCard type, reviewQueue api, useReviewQueue hook"
```

---

## Task 11: `RatingButtons`

**Files:**
- Create: `frontend/src/components/review/RatingButtons.tsx`
- Test: `frontend/tests/components/RatingButtons.test.tsx`

- [ ] **Step 1: Write the failing test** — Create `frontend/tests/components/RatingButtons.test.tsx`:

```tsx
/** Tests for RatingButtons. */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RatingButtons } from '@/components/review/RatingButtons';

const PREVIEWS = { '1': 0, '2': 1, '3': 4, '4': 9 };

describe('RatingButtons', () => {
  it('labels each button with its interval', () => {
    render(<RatingButtons previews={PREVIEWS} onRate={vi.fn()} disabled={false} />);
    expect(screen.getByRole('button', { name: /again/i })).toHaveTextContent('<1d');
    expect(screen.getByRole('button', { name: /good/i })).toHaveTextContent('4d');
    expect(screen.getByRole('button', { name: /easy/i })).toHaveTextContent('9d');
  });

  it('calls onRate with the rating number', () => {
    const onRate = vi.fn();
    render(<RatingButtons previews={PREVIEWS} onRate={onRate} disabled={false} />);
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    expect(onRate).toHaveBeenCalledWith(3);
  });

  it('disables all buttons when disabled', () => {
    render(<RatingButtons previews={PREVIEWS} onRate={vi.fn()} disabled />);
    screen.getAllByRole('button').forEach((b) => expect(b).toBeDisabled());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run RatingButtons`
Expected: FAIL — cannot resolve `@/components/review/RatingButtons`.

- [ ] **Step 3: Implement the component** — Create `frontend/src/components/review/RatingButtons.tsx`:

```tsx
/** The four FSRS rating buttons, each labelled with its preview interval. */

import React from 'react';

export interface RatingButtonsProps {
  previews: Record<string, number>;
  onRate: (rating: number) => void;
  disabled: boolean;
}

const RATINGS: { rating: number; name: string }[] = [
  { rating: 1, name: 'Again' },
  { rating: 2, name: 'Hard' },
  { rating: 3, name: 'Good' },
  { rating: 4, name: 'Easy' },
];

function intervalLabel(days: number): string {
  return days < 1 ? '<1d' : `${days}d`;
}

export const RatingButtons: React.FC<RatingButtonsProps> = ({ previews, onRate, disabled }) => {
  return (
    <div className="flex gap-2 justify-center">
      {RATINGS.map(({ rating, name }) => (
        <button
          key={rating}
          type="button"
          disabled={disabled}
          onClick={() => onRate(rating)}
          className="px-4 py-2 rounded border border-border-app bg-surface disabled:opacity-50"
        >
          {name} {intervalLabel(previews[String(rating)] ?? 0)}
        </button>
      ))}
    </div>
  );
};

RatingButtons.displayName = 'RatingButtons';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run RatingButtons`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/review/RatingButtons.tsx frontend/tests/components/RatingButtons.test.tsx
git commit -m "feat(frontend): RatingButtons with per-rating interval labels"
```

---

## Task 12: `StudyPage` + route + launch button

**Files:**
- Create: `frontend/src/pages/StudyPage.tsx`
- Test: `frontend/tests/pages/StudyPage.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/pages/DeckDetailPage.tsx`

- [ ] **Step 1: Write the failing test** — Create `frontend/tests/pages/StudyPage.test.tsx`:

```tsx
/** Tests for the StudyPage review flow. */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const { mockUseReviewQueue, mockRate } = vi.hoisted(() => ({
  mockUseReviewQueue: vi.fn(),
  mockRate: vi.fn(),
}));

vi.mock('@/hooks/useReviewQueue', () => ({ useReviewQueue: mockUseReviewQueue }));
vi.mock('@/services/api', () => ({ api: { rate: mockRate } }));
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({ folder: 'gt' }), useNavigate: () => vi.fn() };
});
// CardContent renders markdown; stub it to plain text for these flow tests
vi.mock('@/components/review/CardContent', () => ({
  CardContent: ({ markdown }: { markdown: string }) => <div>{markdown}</div>,
}));

import { StudyPage } from '@/pages/StudyPage';

const CARD = {
  card_id: 'c1', syntax: 'cloze', front: 'A [...] equilibrium.',
  answer: 'A **Nash** equilibrium.', previews: { '1': 0, '2': 1, '3': 4, '4': 9 },
};

beforeEach(() => {
  vi.clearAllMocks();
  mockRate.mockResolvedValue({ ok: true });
  mockUseReviewQueue.mockReturnValue({ data: [CARD], isLoading: false, error: null });
});

describe('StudyPage', () => {
  it('shows the front and hides rating buttons until revealed', () => {
    render(<StudyPage />);
    expect(screen.getByText('A [...] equilibrium.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /good/i })).toBeNull();
    expect(screen.getByRole('button', { name: /show answer/i })).toBeInTheDocument();
  });

  it('reveals the answer and rates, advancing to the summary', async () => {
    mockUseReviewQueue.mockReturnValue({ data: [CARD], isLoading: false, error: null });
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    expect(screen.getByText('A **Nash** equilibrium.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    expect(mockRate).toHaveBeenCalledWith(expect.objectContaining({ card_id: 'c1', rating: 3 }));
    await waitFor(() => expect(screen.getByText(/reviewed 1 card/i)).toBeInTheDocument());
  });

  it('shows an empty state when nothing is due', () => {
    mockUseReviewQueue.mockReturnValue({ data: [], isLoading: false, error: null });
    render(<StudyPage />);
    expect(screen.getByText(/nothing due/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run StudyPage`
Expected: FAIL — cannot resolve `@/pages/StudyPage`.

- [ ] **Step 3: Implement the page** — Create `frontend/src/pages/StudyPage.tsx`:

```tsx
/** Review/study screen: walk a deck's queue, reveal answers, rate 1–4. */

import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useReviewQueue } from '@/hooks/useReviewQueue';
import { api } from '@/services/api';
import { CardContent } from '@/components/review/CardContent';
import { RatingButtons } from '@/components/review/RatingButtons';
import { Skeleton, ErrorMessage, EmptyState, Button } from '@/components/ui';

export const StudyPage: React.FC = () => {
  const { folder } = useParams();
  const navigate = useNavigate();
  const { data: queue, isLoading, error } = useReviewQueue(folder);

  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [shownAt, setShownAt] = useState(() => Date.now());
  const [rating, setRating] = useState(false);
  const [rateError, setRateError] = useState<string | null>(null);

  if (isLoading) return <div className="min-h-screen bg-app p-8"><Skeleton variant="rect" height={160} /></div>;
  if (error) {
    return (
      <div className="min-h-screen bg-app p-8">
        <ErrorMessage message={error instanceof Error ? error.message : 'Failed to load queue'} />
      </div>
    );
  }
  if (!queue || queue.length === 0) {
    return (
      <div className="min-h-screen bg-app p-8">
        <EmptyState title="Nothing due" description="Nothing due in this deck right now." />
      </div>
    );
  }
  if (index >= queue.length) {
    return (
      <div className="min-h-screen bg-app p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">Reviewed {queue.length} card{queue.length === 1 ? '' : 's'} · Done</h1>
        <Button onClick={() => navigate(`/decks/${folder}`)}>Back to deck</Button>
      </div>
    );
  }

  const card = queue[index];

  const advance = () => {
    setRevealed(false);
    setRateError(null);
    setShownAt(Date.now());
    setIndex((i) => i + 1);
  };

  const rate = (value: number) => {
    setRating(true);
    setRateError(null);
    api
      .rate({ card_id: card.card_id, rating: value, response_time_ms: Date.now() - shownAt })
      .then(() => advance())
      .catch((e) => setRateError(e instanceof Error ? e.message : 'Rating failed'))
      .finally(() => setRating(false));
  };

  return (
    <div className="min-h-screen bg-app p-8">
      <div className="max-w-2xl mx-auto">
        <div className="text-sm text-muted mb-4">{index + 1} / {queue.length}</div>
        <div className="bg-surface rounded-lg shadow p-6 mb-6">
          <CardContent markdown={card.front} />
          {revealed && (
            <>
              <hr className="my-4 border-border-app" />
              <CardContent markdown={card.answer} />
            </>
          )}
        </div>
        {rateError && <div className="mb-4"><ErrorMessage message={rateError} /></div>}
        {revealed ? (
          <RatingButtons previews={card.previews} onRate={rate} disabled={rating} />
        ) : (
          <div className="flex justify-center">
            <Button onClick={() => setRevealed(true)}>Show answer</Button>
          </div>
        )}
      </div>
    </div>
  );
};

StudyPage.displayName = 'StudyPage';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run StudyPage`
Expected: PASS (3 passed)

- [ ] **Step 5: Add the route** — In `frontend/src/App.tsx`, add the import with the other pages:

```typescript
import { StudyPage } from './pages/StudyPage';
```

and the route inside the `<Route element={<AppLayout />}>` group, after the `/changed` route:

```tsx
            <Route path="/study/:folder" element={<StudyPage />} />
```

- [ ] **Step 6: Add the Study button** — In `frontend/src/pages/DeckDetailPage.tsx`, in the deck header action area (near the `<h1 className="text-3xl font-bold mb-2">{deck.name}</h1>` and its sibling action `<Button>`s around lines 184–202), add a Study button:

```tsx
            <Button variant="primary" onClick={() => navigate(`/study/${folder}`)}>
              Study
            </Button>
```

`folder` is available from `useParams()` at the top of `DeckDetailPage` (the route is `/decks/:folder`); if the param is destructured under another name, use that name. Place the button among the existing header buttons.

- [ ] **Step 7: Verify build + the new tests**

Run: `npm run build && npm test -- --run StudyPage`
Expected: build succeeds; StudyPage tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/StudyPage.tsx frontend/tests/pages/StudyPage.test.tsx frontend/src/App.tsx frontend/src/pages/DeckDetailPage.tsx
git commit -m "feat(frontend): StudyPage review flow + route + deck Study button"
```

---

## Task 13: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite + lint/type/coverage**

Run (from `backend/`):
```bash
uv run pytest -q
uv run ruff check src/mnemonic/core/review src/mnemonic/core/fsrs/state.py src/mnemonic/services/review_queue.py src/mnemonic/api/routes/reviews.py
uv run black --check src/mnemonic/core/review src/mnemonic/core/fsrs/state.py src/mnemonic/services/review_queue.py
uv run mypy src/mnemonic/core/review src/mnemonic/core/fsrs/state.py src/mnemonic/services/review_queue.py
uv run pytest --cov=mnemonic.core.review --cov=mnemonic.core.fsrs.state --cov-report=term-missing tests/unit/core/review tests/unit/core/test_card_state.py -q
```
Expected: pytest passes except the 3 known pre-existing `tests/test_setup.py` dependency-import failures; ruff/black/mypy clean; `core/review` + `state` coverage ≥ 95%.

- [ ] **Step 2: Frontend build, lint, tests**

Run (from `frontend/`):
```bash
npm run build
npm run lint
npm test -- --run
```
Expected: build succeeds and emits a CSS asset; lint clean on new files; all NEW tests pass. The single pre-existing `DeckDetailPage.test.tsx` failure (unrelated) may remain — confirm no other failures.

- [ ] **Step 3: Final commit (only if lint/type fixes were made)**

```bash
git add -A
git commit -m "chore(review-flow): lint and type fixes"
```

---

## Notes for the implementer

- **Rating write path is unchanged** — `POST /reviews/rate` already runs FSRS and persists the next `due`. The review screen just calls it; do not reimplement scheduling.
- **Policy seam** — `ReviewPolicy` is where the future cascading-rules engine (B1-Policy) plugs in. Keep `QueueService` depending on the protocol, not `SimplePolicy` directly (it already does, via the `policy` constructor arg).
- **Cloze `back` still carries markers** — that is why `faces.build_faces` reveals them; never send raw `{{cN::}}` to the client.
- **Tailwind is new** — Task 6 must emit a CSS asset; if `npm run build` produces no `dist/assets/*.css`, the pipeline is misconfigured. The warm theme deliberately restyles the whole (previously unstyled) app.
- **KaTeX CSS** is imported inside `CardContent.tsx` (`import 'katex/dist/katex.min.css'`); no separate wiring needed.
- **Pre-existing failures to expect:** backend `tests/test_setup.py` (redis/jose/passlib not installed) and frontend `tests/pages/DeckDetailPage.test.tsx` (a `/create card/i` multiple-match) both fail on `main` already — not regressions.
