# Variation Display During Review (B2-Display) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a non-invalidated LLM variation in place of a card's question during review, with optional helpfulness feedback — degrading to the base card whenever no variation is available.

**Architecture:** A pure `core/variation/choose.py` picks a candidate (frequency-gated, least-shown-first). `QueueService` batches a `VariationMeta → TrainingExample` join filtered on `invalidated_at IS NULL` to recover displayable Q/A, and populates three new optional fields on `QueuedCard`. `StudyPage` renders the variation instead of the base front/answer with a badge, and posts `variation_id`/`variation_helpful` on rate; `ReviewService.rate` increments the variation's shown/helpful counters.

**Tech Stack:** Python 3.11, SQLAlchemy, FastAPI, pytest, `uv`; React 18, TypeScript, Vitest, `npm`.

Backend commands from `backend/`; frontend from `frontend/`. Spec: `docs/superpowers/specs/2026-07-14-variation-display-design.md`.

---

## File Structure

**Create (backend):** `src/mnemonic/core/variation/__init__.py`, `src/mnemonic/core/variation/choose.py`.
**Modify (backend):** `src/mnemonic/services/review_queue.py` (candidate query, `QueuedCard` fields, `_to_item` wiring), `src/mnemonic/api/routes/reviews.py` (serialize 3 fields), `src/mnemonic/services/review.py` (increment counters).
**Modify (frontend):** `src/types/index.ts` (`QueuedCard` fields + `rate` payload), `src/services/api.ts` (`rate` accepts variation fields), `src/pages/StudyPage.tsx` (render + helpfulness).
**Tests:** `tests/unit/core/variation/{__init__.py,test_choose.py}`; append to `tests/unit/services/test_review_queue.py`, `tests/unit/services/test_review_service.py`, `tests/unit/api/test_review_queue.py`, `frontend/tests/pages/StudyPage.test.tsx`.

Note: `mnemonic/core/variation/` is a NEW package. There is an existing unrelated `mnemonic/llm/variation/` (generation) — do not confuse them.

---

## Task 1: Pure variation chooser

**Files:**
- Create: `src/mnemonic/core/variation/__init__.py`, `src/mnemonic/core/variation/choose.py`
- Test: `tests/unit/core/variation/__init__.py`, `tests/unit/core/variation/test_choose.py`

- [ ] **Step 1: Create package markers**

Create `src/mnemonic/core/variation/__init__.py`:
```python
"""Pure variation-selection logic for review display."""
```
Create empty `tests/unit/core/variation/__init__.py` (no content).

- [ ] **Step 2: Write the failing tests** — Create `tests/unit/core/variation/test_choose.py`:

```python
"""Tests for the pure variation chooser."""

from __future__ import annotations

from datetime import datetime

from mnemonic.core.variation.choose import VariationCandidate, choose_variation


def _cand(vid: str, *, shown: int = 0, when: datetime | None = None) -> VariationCandidate:
    return VariationCandidate(
        variation_id=vid,
        question=f"q-{vid}",
        answer=f"a-{vid}",
        shown_count=shown,
        generated_at=when or datetime(2026, 7, 1, 12, 0, 0),
    )


def test_disabled_returns_none():
    assert choose_variation([_cand("v1")], enabled=False, frequency=1.0, roll=0.0) is None


def test_empty_candidates_returns_none():
    assert choose_variation([], enabled=True, frequency=1.0, roll=0.0) is None


def test_roll_at_or_above_frequency_returns_none():
    assert choose_variation([_cand("v1")], enabled=True, frequency=0.3, roll=0.3) is None
    assert choose_variation([_cand("v1")], enabled=True, frequency=0.3, roll=0.9) is None


def test_frequency_one_always_picks():
    got = choose_variation([_cand("v1")], enabled=True, frequency=1.0, roll=0.999)
    assert got is not None and got.variation_id == "v1"


def test_frequency_zero_never_picks():
    assert choose_variation([_cand("v1")], enabled=True, frequency=0.0, roll=0.0) is None


def test_lowest_shown_count_wins():
    got = choose_variation(
        [_cand("v1", shown=5), _cand("v2", shown=1), _cand("v3", shown=9)],
        enabled=True, frequency=1.0, roll=0.0,
    )
    assert got is not None and got.variation_id == "v2"


def test_tie_on_shown_count_breaks_to_newest():
    got = choose_variation(
        [
            _cand("old", shown=2, when=datetime(2026, 7, 1)),
            _cand("new", shown=2, when=datetime(2026, 7, 10)),
        ],
        enabled=True, frequency=1.0, roll=0.0,
    )
    assert got is not None and got.variation_id == "new"


def test_full_tie_breaks_stably_by_id():
    same = datetime(2026, 7, 5)
    got = choose_variation(
        [_cand("bbb", shown=1, when=same), _cand("aaa", shown=1, when=same)],
        enabled=True, frequency=1.0, roll=0.0,
    )
    assert got is not None and got.variation_id == "aaa"


def test_frequency_is_clamped():
    # frequency > 1 behaves as 1.0 (always), frequency < 0 behaves as 0.0 (never)
    assert choose_variation([_cand("v1")], enabled=True, frequency=5.0, roll=0.99) is not None
    assert choose_variation([_cand("v1")], enabled=True, frequency=-2.0, roll=0.0) is None


def test_returns_the_candidate_text():
    got = choose_variation([_cand("v1")], enabled=True, frequency=1.0, roll=0.0)
    assert got is not None
    assert got.question == "q-v1" and got.answer == "a-v1"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/variation/test_choose.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.variation.choose'`

- [ ] **Step 4: Implement `choose.py`** — Create `src/mnemonic/core/variation/choose.py`:

```python
"""Choose which stored variation (if any) to show for a card.

Pure: the caller supplies the random ``roll`` so selection is deterministic in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VariationCandidate:
    """A non-invalidated variation with its displayable text."""

    variation_id: str
    question: str
    answer: str
    shown_count: int
    generated_at: datetime


def choose_variation(
    candidates: list[VariationCandidate],
    *,
    enabled: bool,
    frequency: float,
    roll: float,
) -> VariationCandidate | None:
    """Pick a variation to display, or None to show the base card.

    Args:
        candidates: Non-invalidated variations available for this card.
        enabled: The deck's ``variation_enabled`` flag.
        frequency: The deck's ``variation_frequency`` (clamped to [0.0, 1.0]).
        roll: A random draw in [0.0, 1.0); a variation is used when ``roll < frequency``.

    Returns:
        The chosen candidate — lowest ``shown_count``, ties broken by newest
        ``generated_at`` then by ``variation_id`` — or None.
    """
    if not enabled or not candidates:
        return None
    clamped = min(1.0, max(0.0, frequency))
    if roll >= clamped:
        return None
    return min(
        candidates,
        key=lambda c: (c.shown_count, -c.generated_at.timestamp(), c.variation_id),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/variation/test_choose.py -v`
Expected: PASS (10 passed)

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/core/variation/ tests/unit/core/variation/
git commit -m "feat(variation): pure frequency-gated, least-shown-first chooser"
```

---

## Task 2: Candidate query

**Files:**
- Modify: `src/mnemonic/services/review_queue.py`
- Test: `tests/unit/services/test_review_queue.py`

- [ ] **Step 1: Write the failing test** — Append to `tests/unit/services/test_review_queue.py`:

```python
def test_variation_candidates_filters_and_joins(tmp_path):
    from datetime import datetime

    from mnemonic.db.models import Base, TrainingExample, VariationMeta
    from mnemonic.db.sqlite import create_engine, session_scope
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    when = datetime(2026, 7, 1, 12, 0, 0)

    def _meta(vid, card_id, *, shown=0, invalidated=None):
        return VariationMeta(
            id=vid, card_id=card_id, strategy="rephrase", model="m", generated_at=when,
            shown_count=shown, helpful_count=0, content_hash="h", note_path="n.qmd",
            invalidated_at=invalidated,
        )

    def _example(vid, card_id):
        return TrainingExample(
            id=f"te-{vid}", card_id=card_id, variation_id=vid, base_q="bq", base_a="ba",
            variation_q=f"vq-{vid}", variation_a=f"va-{vid}", label=0, created_at=when,
        )

    with session_scope(engine) as s:
        s.add(_meta("v-ok", "card-a", shown=3))
        s.add(_example("v-ok", "card-a"))
        s.add(_meta("v-dead", "card-a", invalidated=when))   # excluded: invalidated
        s.add(_example("v-dead", "card-a"))
        s.add(_meta("v-orphan", "card-a"))                    # excluded: no TrainingExample
        s.add(_meta("v-other", "card-b"))                     # different card
        s.add(_example("v-other", "card-b"))

    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine, default_new_per_day=50, default_due_per_day=50,
    )
    got = svc._variation_candidates(["card-a", "card-b"])

    assert [c.variation_id for c in got["card-a"]] == ["v-ok"]
    assert got["card-a"][0].question == "vq-v-ok"
    assert got["card-a"][0].answer == "va-v-ok"
    assert got["card-a"][0].shown_count == 3
    assert [c.variation_id for c in got["card-b"]] == ["v-other"]


def test_variation_candidates_empty_for_no_ids(tmp_path):
    from mnemonic.db.models import Base
    from mnemonic.db.sqlite import create_engine
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine, default_new_per_day=50, default_due_per_day=50,
    )
    assert svc._variation_candidates([]) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py::test_variation_candidates_filters_and_joins -v`
Expected: FAIL — `AttributeError: 'QueueService' object has no attribute '_variation_candidates'`

- [ ] **Step 3: Implement the query** — In `src/mnemonic/services/review_queue.py`:

Add these imports to the existing import block (the `mnemonic.core...` group and the models import):
```python
from mnemonic.core.variation.choose import VariationCandidate, choose_variation
from mnemonic.db.models import ReviewLog, TrainingExample, VariationMeta
```
(Replace the existing `from mnemonic.db.models import ReviewLog` line with the three-model version.)

Add this method to `QueueService`, immediately after `_last_reviews`:
```python
    def _variation_candidates(self, card_ids: list[str]) -> dict[str, list[VariationCandidate]]:
        """Non-invalidated variations per card, joined to their displayable Q/A text."""
        if not card_ids:
            return {}
        with session_scope(self.engine) as s:
            rows = (
                s.query(
                    VariationMeta.card_id,
                    VariationMeta.id,
                    TrainingExample.variation_q,
                    TrainingExample.variation_a,
                    VariationMeta.shown_count,
                    VariationMeta.generated_at,
                )
                .join(TrainingExample, TrainingExample.variation_id == VariationMeta.id)
                .filter(
                    VariationMeta.card_id.in_(card_ids),
                    VariationMeta.invalidated_at.is_(None),
                )
                .all()
            )
        out: dict[str, list[VariationCandidate]] = {}
        for card_id, vid, question, answer, shown, generated in rows:
            out.setdefault(card_id, []).append(
                VariationCandidate(
                    variation_id=vid,
                    question=question,
                    answer=answer,
                    shown_count=shown,
                    generated_at=generated,
                )
            )
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_queue.py -q`
Expected: PASS (all queue tests including the 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review_queue.py tests/unit/services/test_review_queue.py
git commit -m "feat(variation): candidate query joining VariationMeta to TrainingExample text"
```

---

## Task 3: `QueuedCard` fields + `_to_item` wiring

**Files:**
- Modify: `src/mnemonic/services/review_queue.py`
- Test: `tests/unit/services/test_review_queue.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/services/test_review_queue.py`:

```python
def _vault_with_variation(tmp_path, *, enabled: bool, frequency: float):
    """A deck with one new card that has one valid variation. Returns (vault, engine)."""
    from datetime import datetime

    from mnemonic.db.models import Base, TrainingExample, VariationMeta
    from mnemonic.db.sqlite import create_engine, session_scope

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "_deck.md").write_text(
        f"---\ndeck_name: GT\nvariation_enabled: {str(enabled).lower()}\n"
        f"variation_frequency: {frequency}\nleech_threshold: 8\n"
        "daily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )
    (vault / "01_Projects" / "gt" / "n0.qmd").write_text(
        "---\ntitle: n0\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-n0\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    when = datetime(2026, 7, 1, 12, 0, 0)
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id="v1", card_id="card-n0", strategy="rephrase", model="m", generated_at=when,
                shown_count=0, helpful_count=0, content_hash="h", note_path="n0.qmd",
            )
        )
        s.add(
            TrainingExample(
                id="te1", card_id="card-n0", variation_id="v1", base_q="bq", base_a="ba",
                variation_q="Rephrased question?", variation_a="Rephrased answer.",
                label=0, created_at=when,
            )
        )
    return vault, engine


def _svc(vault, engine):
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    return QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine, default_new_per_day=50, default_due_per_day=50,
    )


def test_queue_item_carries_variation_when_enabled(tmp_path):
    vault, engine = _vault_with_variation(tmp_path, enabled=True, frequency=1.0)
    card = _svc(vault, engine).build("gt").cards[0]
    assert card.variation_id == "v1"
    assert card.variation_front == "Rephrased question?"
    assert card.variation_answer == "Rephrased answer."


def test_queue_item_has_no_variation_when_disabled(tmp_path):
    vault, engine = _vault_with_variation(tmp_path, enabled=False, frequency=1.0)
    card = _svc(vault, engine).build("gt").cards[0]
    assert card.variation_id is None
    assert card.variation_front is None
    assert card.variation_answer is None


def test_queue_item_has_no_variation_at_zero_frequency(tmp_path):
    vault, engine = _vault_with_variation(tmp_path, enabled=True, frequency=0.0)
    card = _svc(vault, engine).build("gt").cards[0]
    assert card.variation_id is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py::test_queue_item_carries_variation_when_enabled -v`
Expected: FAIL — `AttributeError: 'QueuedCard' object has no attribute 'variation_id'`

- [ ] **Step 3: Add the fields** — In `src/mnemonic/services/review_queue.py`, add three defaulted fields to the `QueuedCard` dataclass, after `previews`:

```python
    previews: dict[int, int]
    variation_id: str | None = None
    variation_front: str | None = None
    variation_answer: str | None = None
```

- [ ] **Step 4: Thread the choice through `build` and `_to_item`** — In `src/mnemonic/services/review_queue.py`:

In `build`, replace the two lines that compute `last_reviews` and `items` with:
```python
        last_reviews = self._last_reviews([c.card_id for c in ordered])
        candidates = self._variation_candidates([c.card_id for c in ordered])
        var_enabled = deck.config.variation_enabled if deck.config else False
        var_frequency = deck.config.variation_frequency if deck.config else 0.0
        rng = random.Random(ctx.seed)
        items = [
            self._to_item(
                c,
                last_reviews.get(c.card_id),
                now,
                choose_variation(
                    candidates.get(c.card_id, []),
                    enabled=var_enabled,
                    frequency=var_frequency,
                    roll=rng.random(),
                ),
            )
            for c in ordered
        ]
```

Replace the whole `_to_item` method with the version below (it gains a `variation` parameter):
```python
    def _to_item(
        self,
        card: Card,
        last_review: datetime | None,
        now: datetime,
        variation: VariationCandidate | None = None,
    ) -> QueuedCard:
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
            variation_id=variation.variation_id if variation else None,
            variation_front=variation.question if variation else None,
            variation_answer=variation.answer if variation else None,
        )
```

(`random` is already imported at the top of this file for the shuffle ordering.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_queue.py -q`
Expected: PASS (all queue tests including the 3 new).

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/services/review_queue.py tests/unit/services/test_review_queue.py
git commit -m "feat(variation): carry the chosen variation on QueuedCard"
```

---

## Task 4: Serialize the variation fields

**Files:**
- Modify: `src/mnemonic/api/routes/reviews.py`
- Test: `tests/unit/api/test_review_queue.py`

- [ ] **Step 1: Write the failing test** — Append to `tests/unit/api/test_review_queue.py`:

```python
def test_queue_serializes_variation_fields_as_null_when_absent(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    card = resp.json()["cards"][0]
    assert card["variation_id"] is None
    assert card["variation_front"] is None
    assert card["variation_answer"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_review_queue.py::test_queue_serializes_variation_fields_as_null_when_absent -v`
Expected: FAIL with `KeyError: 'variation_id'`

- [ ] **Step 3: Add the fields to the serializer** — In `src/mnemonic/api/routes/reviews.py`, replace the `_serialize_queued` function with:

```python
def _serialize_queued(q: QueuedCard) -> dict:
    return {
        "card_id": q.card_id,
        "syntax": q.syntax,
        "front": q.front,
        "answer": q.answer,
        "previews": {str(rating): days for rating, days in q.previews.items()},
        "variation_id": q.variation_id,
        "variation_front": q.variation_front,
        "variation_answer": q.variation_answer,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/api/test_review_queue.py -q`
Expected: PASS (all api queue tests including the new one).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/api/routes/reviews.py tests/unit/api/test_review_queue.py
git commit -m "feat(api): serialize variation fields on queue items"
```

---

## Task 5: `rate()` increments variation counters

**Files:**
- Modify: `src/mnemonic/services/review.py`
- Test: `tests/unit/services/test_review_service.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/services/test_review_service.py`:

```python
def _vault_with_variation_meta(tmp_path, *, shown=0, helpful=0):
    """Vault with one card plus a VariationMeta row 'v1'. Returns (repo, engine)."""
    from datetime import datetime

    from mnemonic.db.models import Base, VariationMeta
    from mnemonic.db.sqlite import create_engine, session_scope
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id="v1", card_id="card-aaaabbbb", strategy="rephrase", model="m",
                generated_at=datetime(2026, 7, 1), shown_count=shown, helpful_count=helpful,
                content_hash="h", note_path="nash.qmd",
            )
        )
    return VaultRepository(vault_root=vault, engine=engine), engine


def test_rate_increments_shown_count(tmp_path):
    from mnemonic.db.models import VariationMeta
    from mnemonic.db.sqlite import session_scope

    repo, engine = _vault_with_variation_meta(tmp_path, shown=2)
    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb", rating=3, response_time_ms=1000, variation_id="v1"
    )
    with session_scope(engine) as s:
        row = s.get(VariationMeta, "v1")
        assert row.shown_count == 3
        assert row.helpful_count == 0


def test_rate_increments_helpful_count_when_helpful(tmp_path):
    from mnemonic.db.models import VariationMeta
    from mnemonic.db.sqlite import session_scope

    repo, engine = _vault_with_variation_meta(tmp_path)
    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb", rating=3, response_time_ms=1000,
        variation_id="v1", variation_helpful=1,
    )
    with session_scope(engine) as s:
        row = s.get(VariationMeta, "v1")
        assert row.shown_count == 1 and row.helpful_count == 1


def test_rate_unknown_variation_id_is_noop_but_logged(tmp_path):
    from mnemonic.db.models import ReviewLog
    from mnemonic.db.sqlite import session_scope

    repo, engine = _vault_with_variation_meta(tmp_path)
    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb", rating=3, response_time_ms=1000, variation_id="nope"
    )
    with session_scope(engine) as s:
        log = s.query(ReviewLog).filter(ReviewLog.card_id == "card-aaaabbbb").one()
        assert log.variation_id == "nope"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_service.py::test_rate_increments_shown_count -v`
Expected: FAIL — `assert 2 == 3` (the counter is never incremented).

- [ ] **Step 3: Increment the counters** — In `src/mnemonic/services/review.py`:

Change the models import line to include `VariationMeta`:
```python
from mnemonic.db.models import ReviewLog, SchedulingState, VariationMeta
```

Inside `rate`, immediately AFTER the `s.add(ReviewLog(...))` block (still inside the `with session_scope(self.engine) as s:` body), add:
```python
            if variation_id is not None:
                meta = s.get(VariationMeta, variation_id)
                if meta is not None:
                    meta.shown_count += 1
                    if variation_helpful:
                        meta.helpful_count += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_service.py -q`
Expected: PASS (existing review tests + the 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review.py tests/unit/services/test_review_service.py
git commit -m "feat(variation): rate() increments shown_count/helpful_count"
```

---

## Task 6: Frontend types, client, and StudyPage rendering

**Files:**
- Modify: `frontend/src/types/index.ts`, `frontend/src/services/api.ts`, `frontend/src/pages/StudyPage.tsx`
- Test: `frontend/tests/pages/StudyPage.test.tsx`

- [ ] **Step 1: Add the type fields** — In `frontend/src/types/index.ts`, add three fields to the existing `QueuedCard` interface (after `previews`):

```typescript
  previews: Record<string, number>;
  variation_id: string | null;
  variation_front: string | null;
  variation_answer: string | null;
```

- [ ] **Step 2: Widen the rate payload** — In `frontend/src/services/api.ts`, replace the `rate` method with:

```typescript
  /** Submit a card rating (optionally reporting the variation shown). */
  rate: (payload: {
    card_id: string;
    rating: number;
    response_time_ms: number;
    variation_id?: string;
    variation_helpful?: number;
  }) =>
    request<{ ok: true }>('/reviews/rate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
```

- [ ] **Step 3: Write the failing tests** — In `frontend/tests/pages/StudyPage.test.tsx`:

(a) The `CARD` fixture needs the new fields. Add them to the existing `CARD` object:
```tsx
const CARD = {
  card_id: 'c1',
  syntax: 'cloze',
  front: 'A [...] equilibrium.',
  answer: 'A **Nash** equilibrium.',
  previews: { '1': 0, '2': 1, '3': 4, '4': 9 },
  variation_id: null,
  variation_front: null,
  variation_answer: null,
};
```

(b) Append these tests inside the `describe('StudyPage', ...)` block:
```tsx
  const VAR_CARD = {
    ...CARD,
    variation_id: 'v1',
    variation_front: 'Rephrased question?',
    variation_answer: 'Rephrased answer.',
  };

  it('renders the variation question and badge when a variation is present', () => {
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [VAR_CARD], limits: { minutes_per_session: null } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    expect(screen.getByText('Rephrased question?')).toBeInTheDocument();
    expect(screen.queryByText('A [...] equilibrium.')).toBeNull();
    expect(screen.getByText(/variation/i)).toBeInTheDocument();
  });

  it('reveals the variation answer and posts helpfulness with the rating', async () => {
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [VAR_CARD], limits: { minutes_per_session: null } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    expect(screen.getByText('Rephrased answer.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /helpful/i }));
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    expect(mockRate).toHaveBeenCalledWith(
      expect.objectContaining({ card_id: 'c1', rating: 3, variation_id: 'v1', variation_helpful: 1 }),
    );
  });

  it('posts no variation fields for a base card', () => {
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    const payload = mockRate.mock.calls[0][0];
    expect(payload.variation_id).toBeUndefined();
    expect(payload.variation_helpful).toBeUndefined();
  });
```

- [ ] **Step 4: Run tests to verify they fail**

Run (from `frontend/`): `npm test -- --run StudyPage`
Expected: FAIL — "Rephrased question?" is not rendered (the page still shows `card.front`).

- [ ] **Step 5: Implement the rendering + feedback** — In `frontend/src/pages/StudyPage.tsx`:

Add `Badge` to the ui import:
```typescript
import { Skeleton, ErrorMessage, EmptyState, Button, Badge } from '@/components/ui';
```

Add a `helpful` state alongside the other per-card state (after the `timedOut` state line):
```typescript
  const [helpful, setHelpful] = useState<number | null>(null);
```

After the `const card = queue[index];` line, add the face resolution:
```typescript
  const isVariation = card.variation_id != null;
  const frontText = card.variation_front ?? card.front;
  const answerText = card.variation_answer ?? card.answer;
```

In `advance()`, reset the feedback — add this line next to the other resets:
```typescript
    setHelpful(null);
```

Replace the `rate` function with:
```typescript
  const rate = (value: number) => {
    setRating(true);
    setRateError(null);
    api
      .rate({
        card_id: card.card_id,
        rating: value,
        response_time_ms: Date.now() - shownAt,
        ...(isVariation && card.variation_id
          ? {
              variation_id: card.variation_id,
              ...(helpful !== null ? { variation_helpful: helpful } : {}),
            }
          : {}),
      })
      .then(() => advance())
      .catch((e) => setRateError(e instanceof Error ? e.message : 'Rating failed'))
      .finally(() => setRating(false));
  };
```

In the JSX, replace the card-body block (the `<div className="bg-surface ...">` containing the two `CardContent`s) with:
```tsx
        <div className="bg-surface rounded-lg shadow p-6 mb-6">
          {isVariation && (
            <div className="mb-3">
              <Badge variant="info">variation</Badge>
            </div>
          )}
          <CardContent markdown={frontText} />
          {revealed && (
            <>
              <hr className="my-4 border-border-app" />
              <CardContent markdown={answerText} />
            </>
          )}
        </div>
```

And in the `revealed ? (...)` branch, wrap the rating buttons so the feedback control sits above them:
```tsx
        {revealed ? (
          <div className="space-y-4">
            {isVariation && (
              <div className="flex items-center justify-center gap-3 text-sm">
                <span className="text-muted">Was this rephrasing helpful?</span>
                <Button
                  variant={helpful === 1 ? 'primary' : 'ghost'}
                  onClick={() => setHelpful(1)}
                >
                  👍 Helpful
                </Button>
                <Button
                  variant={helpful === 0 ? 'primary' : 'ghost'}
                  onClick={() => setHelpful(0)}
                >
                  👎 No
                </Button>
              </div>
            )}
            <RatingButtons previews={card.previews} onRate={rate} disabled={rating} />
          </div>
        ) : (
          <div className="flex justify-center">
            <Button onClick={() => setRevealed(true)}>Show answer</Button>
          </div>
        )}
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `frontend/`): `npm test -- --run StudyPage`
Expected: PASS (all StudyPage tests including the 3 new).

Note on the button labels: the positive button is "👍 Helpful" and the negative is "👎 No" (NOT "👎 Not helpful"). This is deliberate — the test queries `getByRole('button', { name: /helpful/i })`, which must match exactly one button. Labelling the negative one "Not helpful" would match both and make `getByRole` throw.

- [ ] **Step 7: Build**

Run (from `frontend/`): `npm run build`
Expected: build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts frontend/src/pages/StudyPage.tsx frontend/tests/pages/StudyPage.test.tsx
git commit -m "feat(frontend): render variations in review with helpfulness feedback"
```

---

## Task 7: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite + lint/type**

Run (from `backend/`):
```bash
uv run pytest -q
uv run ruff check src/mnemonic/core/variation src/mnemonic/services/review_queue.py src/mnemonic/services/review.py src/mnemonic/api/routes/reviews.py
uv run black --check src/mnemonic/core/variation src/mnemonic/services/review_queue.py src/mnemonic/services/review.py
uv run mypy src/mnemonic/core/variation src/mnemonic/services/review_queue.py src/mnemonic/services/review.py
```
Expected: pytest passes except the 3 known pre-existing `tests/test_setup.py` failures; ruff clean (ignore the pyproject deprecation warning); black clean; mypy clean.

- [ ] **Step 2: Variation coverage**

Run (from `backend/`): `uv run pytest --cov=mnemonic.core.variation --cov-report=term-missing tests/unit/core/variation -q`
Expected: `core/variation` ≥ 95%.

- [ ] **Step 3: Frontend build, lint, tests**

Run (from `frontend/`):
```bash
npm run build
npm run lint
npm test -- --run
```
Expected: build succeeds; lint clean on changed files; all tests pass except the single pre-existing `DeckDetailPage.test.tsx` failure. Confirm no NEW failures.

- [ ] **Step 4: Final commit (only if lint/type fixes were made)**

```bash
git add -A
git commit -m "chore(variation): lint and type fixes"
```

---

## Notes for the implementer

- **This ships as a no-op on a real vault** until B2-Gen wires generation — nothing creates variations today (`persist_variation` is called only from tests). The feature is exercised by seeded variations in tests and degrades to the base card everywhere else. That is expected, not a bug.
- **`core/variation/` is new** and unrelated to the existing `llm/variation/` (generation). Don't merge them.
- **The display text comes from `TrainingExample`**, joined on `variation_id` — `VariationMeta` stores only a one-way `content_hash`. An inner join means a `VariationMeta` without its `TrainingExample` sibling silently yields no candidate (fallback to base), which is intended.
- **`variation_frequency` is clamped, not validated** in the chooser — a `_deck.md` typo must not fail a study session (unlike `policy.toml`, which raises).
- **Counters matter:** without the `rate()` increments in Task 5, least-shown-first selection would never rotate between a card's variations.
- **Pre-existing failures to expect:** backend `tests/test_setup.py` (redis/jose/passlib); frontend `DeckDetailPage.test.tsx` (`/create card/i` multiple-match).
