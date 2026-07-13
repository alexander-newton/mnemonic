# Review Policy Engine — Time Limits (B1-Policy-B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-deck time budgets — `minutes_per_day` (backend gate) and `minutes_per_session` (frontend wall-clock) — to the review-policy engine.

**Architecture:** Two new overall-only keys on `policy.toml` rules resolve into top-level `EffectivePolicy` fields. `QueueService` gates the queue empty when today's summed `response_time_ms` meets `minutes_per_day`, and returns a `QueueResult { cards, limits }` so the frontend gets the session budget. `StudyPage` runs a wall-clock timer checked at card boundaries to end the session at `minutes_per_session`.

**Tech Stack:** Python 3.11, SQLAlchemy, FastAPI, pytest, `uv`; React 18, TypeScript, Vitest, `npm`.

Backend commands from `backend/`; frontend from `frontend/`. Spec: `docs/superpowers/specs/2026-07-12-review-policy-time-limits-design.md`.

---

## File Structure

**Modify (backend):** `src/mnemonic/core/policy/rules.py` (time keys on `Rule`), `src/mnemonic/core/policy/resolve.py` (time fields on `EffectivePolicy`), `src/mnemonic/services/review_queue.py` (`_minutes_today`, time/day gate, `QueueResult`/`QueueLimits`), `src/mnemonic/api/routes/reviews.py` (wrapped serialization).
**Modify (frontend):** `src/types/index.ts` (`QueueResponse`), `src/services/api.ts` (`reviewQueue` return type), `src/hooks/useReviewQueue.ts` (typed to `QueueResponse`), `src/pages/StudyPage.tsx` (session clock).
**Tests:** append to `tests/unit/core/policy/test_rules.py`, `test_resolve.py`, `tests/unit/services/test_review_queue.py`, `tests/unit/api/test_review_queue.py`; `frontend/tests/hooks/useReviewQueue.test.tsx`, `frontend/tests/pages/StudyPage.test.tsx`.

---

## Task 1: `Rule` time keys

**Files:**
- Modify: `src/mnemonic/core/policy/rules.py`
- Test: `tests/unit/core/policy/test_rules.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/core/policy/test_rules.py`:

```python
def test_parses_time_keys(tmp_path: Path):
    rules = load_rules(_write(tmp_path, '[[rule]]\nminutes_per_day = 40\nminutes_per_session = 25\n'))
    assert rules[0].minutes_per_day == 40
    assert rules[0].minutes_per_session == 25


def test_negative_minutes_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="minutes_per_day"):
        load_rules(_write(tmp_path, '[[rule]]\nminutes_per_day = -1\n'))


def test_time_key_on_non_all_scope_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="scope='all'"):
        load_rules(_write(tmp_path, '[[rule]]\nscope = "new"\nminutes_per_day = 10\n'))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/policy/test_rules.py::test_parses_time_keys -v`
Expected: FAIL — `Rule.__init__` got unexpected keyword / attribute missing (the parser doesn't read the keys yet).

- [ ] **Step 3: Add the keys to `Rule` + parsing** — In `src/mnemonic/core/policy/rules.py`:

Add the two keys to the allowed set:
```python
_ALLOWED_KEYS = {
    "deck", "scope", "per_day", "per_session", "order", "interleave_new_every",
    "minutes_per_day", "minutes_per_session",
}
```

Add two fields to the `Rule` dataclass, WITH defaults `None` (so existing `Rule(...)` constructions keep working). After the `interleave_new_every` field:
```python
    interleave_new_every: int | None
    minutes_per_day: int | None = None
    minutes_per_session: int | None = None
```

In `_parse_rule`, after the interleave checks and before the `return Rule(...)`, add:
```python
    minutes_per_day = _non_negative(index, "minutes_per_day", raw.get("minutes_per_day"))
    minutes_per_session = _non_negative(index, "minutes_per_session", raw.get("minutes_per_session"))
    if (minutes_per_day is not None or minutes_per_session is not None) and scope != "all":
        raise PolicyError(
            f"policy.toml rule #{index}: minutes_per_day/minutes_per_session are only "
            f"allowed on scope='all', not '{scope}'."
        )
```

And pass them in the `return Rule(...)` (add two kwargs at the end):
```python
        interleave_new_every=ine,
        minutes_per_day=minutes_per_day,
        minutes_per_session=minutes_per_session,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/policy/test_rules.py -v`
Expected: PASS (all rules tests, including the 3 new ones).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/policy/rules.py tests/unit/core/policy/test_rules.py
git commit -m "feat(policy): minutes_per_day/minutes_per_session on policy rules"
```

---

## Task 2: Resolve time fields

**Files:**
- Modify: `src/mnemonic/core/policy/resolve.py`
- Test: `tests/unit/core/policy/test_resolve.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/core/policy/test_resolve.py`:

```python
def test_time_keys_unset_are_none():
    eff = resolve_policy(seed=SEED, rules=[], deck="gt")
    assert eff.minutes_per_day is None and eff.minutes_per_session is None


def test_time_keys_resolve_top_level():
    rules = [_rule(minutes_per_day=40, minutes_per_session=25)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.minutes_per_day == 40 and eff.minutes_per_session == 25


def test_later_time_rule_overrides_earlier():
    rules = [_rule(minutes_per_day=40), _rule(minutes_per_day=10)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.minutes_per_day == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/policy/test_resolve.py::test_time_keys_resolve_top_level -v`
Expected: FAIL — `EffectivePolicy` has no attribute `minutes_per_day`.

- [ ] **Step 3: Add fields + threading** — In `src/mnemonic/core/policy/resolve.py`:

Add two fields to `EffectivePolicy` WITH defaults `None` (keeps existing positional constructions working). After the `interleave_new_every` field:
```python
    interleave_new_every: int | None
    minutes_per_day: int | None = None
    minutes_per_session: int | None = None
```

In `_apply`, thread the two values (later-rule-wins) and include them in each `replace(...)` branch. Replace the whole `_apply` function body with:
```python
def _apply(eff: EffectivePolicy, rule: Rule) -> EffectivePolicy:
    slot: Limits = getattr(eff, rule.scope)
    new_slot = Limits(
        per_day=rule.per_day if rule.per_day is not None else slot.per_day,
        per_session=rule.per_session if rule.per_session is not None else slot.per_session,
    )
    order = rule.order if rule.order is not None else eff.order
    ine = (
        rule.interleave_new_every
        if rule.interleave_new_every is not None
        else eff.interleave_new_every
    )
    mpd = rule.minutes_per_day if rule.minutes_per_day is not None else eff.minutes_per_day
    mps = (
        rule.minutes_per_session
        if rule.minutes_per_session is not None
        else eff.minutes_per_session
    )
    common = dict(order=order, interleave_new_every=ine, minutes_per_day=mpd, minutes_per_session=mps)
    if rule.scope == "all":
        return replace(eff, all=new_slot, **common)
    elif rule.scope == "new":
        return replace(eff, new=new_slot, **common)
    else:  # rule.scope == "due"
        return replace(eff, due=new_slot, **common)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/policy/test_resolve.py -v`
Expected: PASS (all resolve tests, including the 3 new ones).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/policy/resolve.py tests/unit/core/policy/test_resolve.py
git commit -m "feat(policy): resolve minutes_per_day/minutes_per_session onto EffectivePolicy"
```

---

## Task 3: time/day gate + `QueueResult`

**Files:**
- Modify: `src/mnemonic/services/review_queue.py`
- Test: `tests/unit/services/test_review_queue.py`

- [ ] **Step 1: Update + write tests** — In `tests/unit/services/test_review_queue.py`:

(a) The two existing tests that call `svc.build(...)` (`test_queue_service_builds_items`, `test_queue_service_honours_policy_toml`) currently treat the return as a list. Update them to read `.cards`:
- In `test_queue_service_builds_items`: change `items = svc.build("gt")` → `result = svc.build("gt")` and then use `result.cards` everywhere `items` was used (`assert len(result.cards) == 1`, `item = result.cards[0]`).
- In `test_queue_service_honours_policy_toml`: change `items = svc.build("gt")` → `assert len(svc.build("gt").cards) == 2`.

(b) Append these new tests (they build a vault with a `_deck.md` deck `gt` and seed `ReviewLog` rows; adapt the helper style already used in the file):

```python
def test_minutes_today_gate_empties_queue(tmp_path):
    from datetime import datetime

    from mnemonic.db.models import Base, ReviewLog
    from mnemonic.db.sqlite import create_engine, session_scope
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    for i in range(3):
        (vault / "01_Projects" / "gt" / f"n{i}.qmd").write_text(
            f"---\ntitle: n{i}\n---\n## Card\n\nA {{{{c1::x}}}} card. ^card-n{i}\n"
        )
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text("[[rule]]\nminutes_per_day = 10\n")
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    # 12 minutes already spent today in this deck (> 10 min budget)
    with session_scope(engine) as s:
        s.add(
            ReviewLog(
                id="r1", card_id="card-n0", rating=3, response_time_ms=12 * 60_000,
                review_time=datetime.now(), deck_folder="gt",
            )
        )
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine, default_new_per_day=50, default_due_per_day=50,
    )

    result = svc.build("gt")
    assert result.cards == []
    assert result.limits.minutes_per_session is None


def test_result_surfaces_minutes_per_session(tmp_path):
    from mnemonic.db.models import Base
    from mnemonic.db.sqlite import create_engine
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "n0.qmd").write_text(
        "---\ntitle: n0\n---\n## Card\n\nA {{c1::x}} card. ^card-n0\n"
    )
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text("[[rule]]\nminutes_per_session = 25\n")
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine, default_new_per_day=50, default_due_per_day=50,
    )

    result = svc.build("gt")
    assert len(result.cards) == 1
    assert result.limits.minutes_per_session == 25
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_review_queue.py::test_result_surfaces_minutes_per_session -v`
Expected: FAIL — `AttributeError: 'list' object has no attribute 'cards'` (build still returns a list).

- [ ] **Step 3: Add `QueueResult`/`QueueLimits` + gate** — In `src/mnemonic/services/review_queue.py`:

Add these dataclasses right after the `QueuedCard` dataclass:
```python
@dataclass(frozen=True)
class QueueLimits:
    """Limits the frontend must enforce (time/session is wall-clock at runtime)."""

    minutes_per_session: int | None


@dataclass(frozen=True)
class QueueResult:
    """The built queue plus the client-enforced limits."""

    cards: list[QueuedCard]
    limits: QueueLimits
```

Change the `build` method's signature and body. Replace the whole `build` method with:
```python
    def build(self, deck_folder: str) -> QueueResult:
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
        limits = QueueLimits(minutes_per_session=effective.minutes_per_session)
        if (
            effective.minutes_per_day is not None
            and self._minutes_today(deck_folder, now) >= effective.minutes_per_day
        ):
            return QueueResult(cards=[], limits=limits)
        ctx = QueueContext(
            cards=cards,
            now=now,
            policy=effective,
            done_today=self._done_today(deck_folder, now),
            seed=now.toordinal(),
        )
        ordered = self.policy.build_queue(ctx)
        last_reviews = self._last_reviews([c.card_id for c in ordered])
        items = [self._to_item(c, last_reviews.get(c.card_id), now) for c in ordered]
        return QueueResult(cards=items, limits=limits)

    def _minutes_today(self, deck_folder: str, now: datetime) -> int:
        start = datetime(now.year, now.month, now.day)
        with session_scope(self.engine) as s:
            total_ms = s.query(
                func.coalesce(func.sum(ReviewLog.response_time_ms), 0)
            ).filter(
                ReviewLog.deck_folder == deck_folder, ReviewLog.review_time >= start
            ).scalar()
        return int(total_ms) // 60_000
```

(Keep `_done_today`, `_last_reviews`, `_to_item` exactly as they are.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_review_queue.py -q`
Expected: PASS (all policy + queue-service tests, including the 2 new ones and the updated `.cards` ones).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/review_queue.py tests/unit/services/test_review_queue.py
git commit -m "feat(policy): time/day gate + QueueResult wrapping cards and limits"
```

---

## Task 4: Wrapped queue endpoint

**Files:**
- Modify: `src/mnemonic/api/routes/reviews.py`
- Test: `tests/unit/api/test_review_queue.py`

- [ ] **Step 1: Update + write tests** — In `tests/unit/api/test_review_queue.py`:

(a) `test_queue_returns_items` currently asserts on `body[0][...]`. Update it to the wrapped shape:
```python
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["cards"]) == 1
    assert body["cards"][0]["card_id"] == "card-aaaabbbb"
    assert body["cards"][0]["front"] == "A [...] equilibrium."
    assert body["cards"][0]["answer"] == "A **Nash** equilibrium."
    assert set(body["cards"][0]["previews"].keys()) == {"1", "2", "3", "4"}
    assert body["limits"] == {"minutes_per_session": None}
```

(b) Append a test that the session limit is surfaced:
```python
def test_queue_surfaces_minutes_per_session(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text("[[rule]]\nminutes_per_session = 30\n")
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["limits"]["minutes_per_session"] == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/api/test_review_queue.py::test_queue_surfaces_minutes_per_session -v`
Expected: FAIL — the response is still a bare list, so `resp.json()["limits"]` raises `TypeError`/`KeyError`.

- [ ] **Step 3: Wrap the serialization** — In `src/mnemonic/api/routes/reviews.py`:

Add `QueueResult` to the review_queue import line:
```python
from mnemonic.services.review_queue import QueuedCard, QueueResult, QueueService
```

Add a result serializer after `_serialize_queued`:
```python
def _serialize_result(result: QueueResult) -> dict:
    return {
        "cards": [_serialize_queued(q) for q in result.cards],
        "limits": {"minutes_per_session": result.limits.minutes_per_session},
    }
```

Replace the `review_queue` handler with:
```python
@router.get("/queue")
def review_queue(deck: str, svc: QueueService = Depends(get_queue_service)) -> dict:
    """Return the ordered, display-ready review queue for a deck, plus client limits."""
    try:
        result = svc.build(deck)
    except DeckNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RenderError, PolicyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_result(result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/api/test_review_queue.py -q`
Expected: PASS (all api queue tests, including the updated shape + new limits test).

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/api/routes/reviews.py tests/unit/api/test_review_queue.py
git commit -m "feat(api): wrap /reviews/queue as {cards, limits}"
```

---

## Task 5: Frontend types + api + hook

**Files:**
- Modify: `frontend/src/types/index.ts`, `frontend/src/services/api.ts`, `frontend/src/hooks/useReviewQueue.ts`
- Test: `frontend/tests/hooks/useReviewQueue.test.tsx`

- [ ] **Step 1: Add the response type** — Append to `frontend/src/types/index.ts`:

```typescript
export interface QueueResponse {
  cards: QueuedCard[];
  limits: { minutes_per_session: number | null };
}
```

- [ ] **Step 2: Update the api method** — In `frontend/src/services/api.ts`, change the `reviewQueue` method's return type from `QueuedCard[]` to `QueueResponse`:

```typescript
  /** Fetch the review queue for a deck (cards plus client-enforced limits). */
  reviewQueue: (deck: string) =>
    request<import('../types').QueueResponse>(`/reviews/queue?deck=${encodeURIComponent(deck)}`),
```

- [ ] **Step 3: Update the failing hook test** — In `frontend/tests/hooks/useReviewQueue.test.tsx`, the `fetches the queue for a deck` test mocks `reviewQueue` to resolve a bare array and asserts `data` length. Change the mock + assertion to the wrapped shape:

```typescript
  it('fetches the queue for a deck', async () => {
    (api.reviewQueue as any).mockResolvedValue({
      cards: [{ card_id: 'c1' }],
      limits: { minutes_per_session: null },
    });
    const { result } = renderHook(() => useReviewQueue('gt'), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.cards).toHaveLength(1);
    expect(api.reviewQueue).toHaveBeenCalledWith('gt');
  });
```

- [ ] **Step 4: Run test to verify it fails**

Run (from `frontend/`): `npm test -- --run useReviewQueue`
Expected: FAIL — `result.current.data?.cards` is undefined because the hook's type is `QueuedCard[]` (compile error) OR the assertion fails.

- [ ] **Step 5: Retype the hook** — Replace `frontend/src/hooks/useReviewQueue.ts` with:

```typescript
/** React Query hook for a deck's review queue. */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { api } from '../services/api';
import type { QueueResponse } from '../types';

export function useReviewQueue(deck?: string): UseQueryResult<QueueResponse, Error> {
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

- [ ] **Step 6: Run test + build to verify**

Run (from `frontend/`): `npm test -- --run useReviewQueue`
Expected: PASS (2 passed).
Run: `npm run build`
Expected: build FAILS to compile in `StudyPage.tsx` (it still treats `data` as an array) — that is expected and Task 6 fixes it. If you want a clean intermediate, you may proceed to Task 6 before building; the hook test passing is the gate for this task.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts frontend/src/hooks/useReviewQueue.ts frontend/tests/hooks/useReviewQueue.test.tsx
git commit -m "feat(frontend): QueueResponse type; reviewQueue/useReviewQueue return {cards, limits}"
```

---

## Task 6: StudyPage session clock

**Files:**
- Modify: `frontend/src/pages/StudyPage.tsx`
- Test: `frontend/tests/pages/StudyPage.test.tsx`

- [ ] **Step 1: Update existing tests + add the timeout test** — In `frontend/tests/pages/StudyPage.test.tsx`:

(a) The `mockUseReviewQueue.mockReturnValue({ data: [CARD], ... })` calls now must return the wrapped shape. Update the `beforeEach` default and the empty-state test:
- `beforeEach`: `mockUseReviewQueue.mockReturnValue({ data: { cards: [CARD], limits: { minutes_per_session: null } }, isLoading: false, error: null });`
- the empty-state test: `mockUseReviewQueue.mockReturnValue({ data: { cards: [], limits: { minutes_per_session: null } }, isLoading: false, error: null });`

(b) Append the session-time-limit test (inside the `describe('StudyPage', ...)` block):

```tsx
  it('ends the session when the wall-clock time limit is passed', async () => {
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(1_000_000);
    const CARD2 = { ...CARD, card_id: 'c2' };
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [CARD, CARD2], limits: { minutes_per_session: 25 } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    // jump the clock 26 minutes past session start before rating
    nowSpy.mockReturnValue(1_000_000 + 26 * 60_000);
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    await waitFor(() =>
      expect(screen.getByText(/session time limit reached/i)).toBeInTheDocument(),
    );
    nowSpy.mockRestore();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `frontend/`): `npm test -- --run StudyPage`
Expected: FAIL — the existing tests error on `data.cards` (page still reads `data` as an array) and the new test can't find the "session time limit reached" text.

- [ ] **Step 3: Implement the session clock** — Replace `frontend/src/pages/StudyPage.tsx` with:

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
  const { deckId } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, error } = useReviewQueue(deckId);
  const queue = data?.cards;
  const minutesPerSession = data?.limits.minutes_per_session ?? null;

  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [shownAt, setShownAt] = useState(() => Date.now());
  const [sessionStart] = useState(() => Date.now());
  const [rating, setRating] = useState(false);
  const [rateError, setRateError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-app p-8">
        <Skeleton variant="rect" height={160} />
      </div>
    );
  }
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
  if (timedOut) {
    return (
      <div className="min-h-screen bg-app p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">
          Session time limit reached — reviewed {index} card{index === 1 ? '' : 's'}
        </h1>
        <Button onClick={() => navigate(`/decks/${deckId}`)}>Back to deck</Button>
      </div>
    );
  }
  if (index >= queue.length) {
    return (
      <div className="min-h-screen bg-app p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">
          Reviewed {queue.length} card{queue.length === 1 ? '' : 's'} · Done
        </h1>
        <Button onClick={() => navigate(`/decks/${deckId}`)}>Back to deck</Button>
      </div>
    );
  }

  const card = queue[index];

  const advance = () => {
    const overtime =
      minutesPerSession != null && Date.now() - sessionStart >= minutesPerSession * 60_000;
    setRevealed(false);
    setRateError(null);
    setShownAt(Date.now());
    setIndex((i) => i + 1);
    if (overtime) setTimedOut(true);
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
        <div className="text-sm text-muted mb-4">
          {index + 1} / {queue.length}
        </div>
        <div className="bg-surface rounded-lg shadow p-6 mb-6">
          <CardContent markdown={card.front} />
          {revealed && (
            <>
              <hr className="my-4 border-border-app" />
              <CardContent markdown={card.answer} />
            </>
          )}
        </div>
        {rateError && (
          <div className="mb-4">
            <ErrorMessage message={rateError} />
          </div>
        )}
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

Note on the timeout end-screen count: `index` has been incremented in `advance()` before `timedOut` renders, so `index` equals the number of cards reviewed this session.

- [ ] **Step 4: Run tests to verify they pass**

Run (from `frontend/`): `npm test -- --run StudyPage`
Expected: PASS (all StudyPage tests, including the new timeout test).

- [ ] **Step 5: Build**

Run (from `frontend/`): `npm run build`
Expected: build succeeds (StudyPage now consumes the wrapped shape).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/StudyPage.tsx frontend/tests/pages/StudyPage.test.tsx
git commit -m "feat(frontend): session wall-clock time limit in StudyPage"
```

---

## Task 7: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite + lint/type**

Run (from `backend/`):
```bash
uv run pytest -q
uv run ruff check src/mnemonic/core/policy src/mnemonic/services/review_queue.py src/mnemonic/api/routes/reviews.py
uv run black --check src/mnemonic/core/policy src/mnemonic/services/review_queue.py
uv run mypy src/mnemonic/core/policy src/mnemonic/services/review_queue.py
```
Expected: pytest passes except the 3 known pre-existing `tests/test_setup.py` failures; ruff clean (ignore the pyproject deprecation warning); black clean; mypy clean.

- [ ] **Step 2: Policy coverage**

Run (from `backend/`): `uv run pytest --cov=mnemonic.core.policy --cov-report=term-missing tests/unit/core/policy -q`
Expected: `core/policy` ≥ 95%.

- [ ] **Step 3: Frontend build, lint, tests**

Run (from `frontend/`):
```bash
npm run build
npm run lint
npm test -- --run
```
Expected: build succeeds; lint clean on changed files; all tests pass except the single pre-existing `DeckDetailPage.test.tsx` failure (unrelated). Confirm no NEW failures.

- [ ] **Step 4: Final commit (only if lint/type fixes were made)**

```bash
git add -A
git commit -m "chore(policy-time): lint and type fixes"
```

---

## Notes for the implementer

- **Two clocks by construction:** `minutes_per_day` is enforced from stored `response_time_ms` (active time); `minutes_per_session` is wall-clock in the browser. They differ intentionally — documented in the spec.
- **Defaults on new dataclass fields** (`Rule`, `EffectivePolicy`) are what keep existing positional/keyword constructions in tests compiling without edits.
- **time/day is a gate, not a trim** — over budget → empty `cards`; you can't trim a card list by predicted time.
- **time/session enforced at card boundaries** — `advance()` checks wall-clock after a successful rate; you always finish the current card. `index` is already incremented when the timeout screen renders, so it equals the reviewed count.
- **Response shape is now `{cards, limits}`** — the frontend change (Tasks 5–6) must land with the backend change (Tasks 3–4); between Task 4 and Task 6 the running app's study screen is broken, but each test suite is updated within its own task, and the branch merges atomically.
- **Pre-existing failures to expect:** backend `tests/test_setup.py` (redis/jose/passlib); frontend `DeckDetailPage.test.tsx` (`/create card/i` multiple-match).
