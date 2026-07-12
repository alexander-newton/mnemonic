# Review Policy Engine — Time Limits (B1-Policy-B) — Design

**Date:** 2026-07-12
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

B1-Policy-A built the card-limit + ordering half of the review-policy engine (`policy.toml`
cascade, `RulesPolicy`, per-deck cards/day and cards/session split new/due). The remaining
requested capability is **time-based limits**: minutes/day and minutes/session, per deck.

These live at two different enforcement points, which shapes the whole design:

- **time/day** is about time *already spent today* — derivable at **backend queue build** by
  summing the `response_time_ms` already stored on each `ReviewLog` (mirrors the `done_today`
  card counting). It acts as a **gate**: once the day's minutes are spent, the queue returns empty.
- **time/session** is about time spent in the *current* session, which the backend cannot know at
  build time (the time hasn't been spent yet). It is enforced at **runtime in the study screen**,
  which requires surfacing the budget to the frontend.

## Scope

This is **B1-Policy-B**, the time half of the policy engine. Decisions locked:

- **Overall only** — `minutes_per_day` / `minutes_per_session` apply to the whole deck's review
  time, not split new/due. (Card limits keep their new/due split from Policy-A.)
- **Wrapped queue response** — `GET /reviews/queue` returns `{ cards, limits }` so the effective
  `minutes_per_session` reaches the frontend in one fetch.
- **Wall-clock session clock** — time/session is real elapsed time since the study screen opened,
  enforced at card boundaries.
- Time keys live in `policy.toml` only this cycle (not `config [defaults]` / `_deck.md`, which
  would need new required-key handling). The time cascade is: built-in `None` (unlimited) →
  `policy.toml` rules (later wins).

Out of scope: B2 (variation display); adding time keys to `config`/`_deck.md`; a UI showing
remaining time budgets; a mid-card ticking timer (enforcement is at card boundaries).

## Architecture

### Section 1 — policy.toml time keys + resolution (`core/policy/`, pure)

`Rule` (in `rules.py`) gains `minutes_per_day: int | None` and `minutes_per_session: int | None`,
added to `_ALLOWED_KEYS`. Validation (loud `PolicyError`, naming the rule index):
- non-negative integers (same `_non_negative` helper as the card limits);
- because time is overall, either key present with `scope` != `"all"` (i.e. `"new"` or `"due"`)
  raises `PolicyError` — time keys are only meaningful on the `all` scope (scope defaults to `all`).

`EffectivePolicy` (in `resolve.py`) gains two **top-level** fields (not per-scope):
`minutes_per_day: int | None`, `minutes_per_session: int | None`. `resolve_policy` starts them at
`None` and `_apply` overwrites each only when the rule sets it (later matching rules win), exactly
like `order`/`interleave_new_every`.

```toml
[[rule]]
deck = "gt"
minutes_per_day = 40
minutes_per_session = 25
```

### Section 2 — Backend enforcement (time/day gate) + wrapped response

**time/day gate.** New `QueueService._minutes_today(deck_folder, now) -> int`:
```sql
SELECT COALESCE(SUM(response_time_ms), 0)
FROM review_log
WHERE deck_folder = :deck AND review_time >= :start_of_today
```
(local midnight → now; reuses the `(deck_folder, review_time)` index; mirrors `_done_today`).
Returns whole minutes (`ms // 60000`). In `build()`, after resolving the `EffectivePolicy`: if
`policy.minutes_per_day` is not None and `minutes_today >= policy.minutes_per_day`, the result's
`cards` is empty (the gate) — same semantics as cards/day. Otherwise the Policy-A card-limit /
ordering logic runs unchanged.

**Wrapped response.** `QueueService.build()` returns a `QueueResult` instead of a bare list:
```python
@dataclass(frozen=True)
class QueueLimits:
    minutes_per_session: int | None

@dataclass(frozen=True)
class QueueResult:
    cards: list[QueuedCard]
    limits: QueueLimits
```
`limits.minutes_per_session` carries the resolved value (or `None`). The `GET /reviews/queue`
endpoint serializes:
```json
{ "cards": [ ... ], "limits": { "minutes_per_session": 25 } }
```
`minutes_per_day` is NOT surfaced — it is fully enforced server-side. A malformed `policy.toml`
still raises `PolicyError` → 422 before any of this.

### Section 3 — Frontend session clock

**Response-shape update.** New type `QueueResponse { cards: QueuedCard[]; limits: {
minutes_per_session: number | null } }`. `api.reviewQueue` and `useReviewQueue` are typed to it;
`StudyPage` reads `data.cards` and `data.limits.minutes_per_session`. The existing
`useReviewQueue` and `StudyPage` tests update to the wrapped shape (mechanical).

**Session clock (wall-clock, card-boundary enforcement).** `StudyPage` records a `sessionStart`
timestamp on mount and checks the budget only at **card advance** (after a successful rating) — no
`setInterval`, no mid-card interruption:
- After a successful rate, `advance()` checks: if `minutes_per_session` is set and
  `Date.now() - sessionStart >= minutes_per_session * 60_000`, it ends the session instead of
  showing the next card.
- The end screen distinguishes "Session time limit reached — reviewed N cards" from the normal
  "Reviewed N cards · Done"; both offer "Back to deck".
- No limit set → runs the queue to the end exactly as today.

So `minutes_per_session = 25` stops at the first card boundary past 25 real minutes; you always
finish the current card, then it stops.

## Error handling (no silent failures)

- Time key on a non-`all` scope, or a negative time value, or malformed TOML → `PolicyError`
  (names the rule) → **422**, consistent with all other malformed-rule cases.
- `minutes_today >= minutes_per_day` → empty `cards` (a 200 → the existing "Nothing due" study
  screen), never an error.
- A failed rating keeps the user on the card (unchanged); the session clock only advances on a
  successful rate.

### Error mapping

| Exception | HTTP |
|---|---|
| `PolicyError` (bad time key / scope / value) | 422 |
| `DeckNotFoundError` (existing) | 404 |

## Testing

**Backend (pytest, TDD):**
- `rules.py`: parses `minutes_per_day`/`minutes_per_session`; negative → `PolicyError`; either key
  with `scope="new"`/`"due"` → `PolicyError`.
- `resolve.py`: time keys resolve top-level; later rule overrides earlier; unset → `None`.
- `QueueService._minutes_today`: sums `response_time_ms` for the deck since midnight; excludes
  other decks / yesterday / NULL-deck rows.
- `QueueService.build`: over `minutes_per_day` → empty `cards`; under → normal queue;
  `QueueResult.limits.minutes_per_session` carries the resolved value (and `None` when unset).
- API: response shape is `{cards, limits}`; `limits.minutes_per_session` present (null when unset);
  the time/day gate returns empty cards.

**Frontend (Vitest + RTL):**
- `useReviewQueue` returns the wrapped `{cards, limits}` shape.
- `StudyPage`: renders `data.cards`; with `minutes_per_session` set and a controlled clock,
  advancing past the budget shows the "time limit reached" end state; with no limit, runs to the
  normal end. Clock controlled via `vi.setSystemTime` (or by stubbing `Date.now`) around
  `sessionStart`.

**Coverage:** `core/policy` stays ≥ 95%; new service/route to backend 85%; frontend additions to
75%.

## Out of scope (follow-ups)

- **B2** — variation-display subsystem (separate spec; now has a review screen to render on).
- Time keys in `config [defaults]` / `_deck.md`.
- A UI surfacing remaining daily/session time.
- Deleting the dead `db/repositories/review_log.py`.
