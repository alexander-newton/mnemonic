# Review Policy Engine — Card Limits & Ordering (B1-Policy-A) — Design

**Date:** 2026-07-10
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

The review queue is built by `SimplePolicy` behind the `ReviewPolicy` seam (see
`2026-07-09-review-flow-design.md`). The user wants a real, flexible review-policy engine:
per-deck and global limits on cards/day and cards/session (split by new vs due), plus
ordering/interleaving rules, driven by a rules file where later rules override earlier ones.

Two facts discovered during exploration shape this:

- **The existing daily limits barely work.** `daily_review_limit` is defined in config,
  `_deck.md`, and the deck API but is **read by no code at all**. `daily_new_limit` is only a
  *queue cap* (`new[:limit]`) — it never subtracts the new cards already done today, so it
  re-offers the full quota every session. There is no true daily budget anywhere.
- **There is no deck reference in the database.** `ReviewLog` has `card_id` but no deck; deck
  membership lives only on the filesystem (resolved at vault-scan time). Per-deck daily counting
  needs deck attribution that does not exist yet.

## Scope & decomposition

This is **B1-Policy-A**, the first of two policy cycles:

- **A (this spec):** the rules file + cascade, cards/day and cards/session limits (split
  new/due, global or per-deck), and ordering/interleaving — **all enforced at queue build,
  backend only**, fully testable without a UI.
- **B (deferred):** time-based limits (time/day, time/session), which require a session concept,
  a time-spent aggregation, and runtime enforcement in the study screen. None of that exists
  today (the `ReviewSession` TS type is dead code). Its own spec.

Also explicitly out of scope: a `GET /reviews/limits` endpoint or any UI showing remaining
budgets; deleting the dead/broken `db/repositories/review_log.py` (it queries a `user_id` column
that does not exist — noted for a separate cleanup).

## Decisions (locked)

- **Rules file:** a new `<vault>/.mnemonic/policy.toml` with an ordered `[[rule]]` list, sitting
  at the END of a cascade (built-in defaults → `config.toml [defaults]` → `_deck.md` → rules).
  Lives in the vault, git-committed with the cards. Existing config keeps working; rules override.
- **Deck attribution:** denormalize `deck_folder` onto `ReviewLog`, written at rate time. Stable
  history (moving a card between decks does not rewrite past per-deck counts).
- **Ordering vocabulary:** `due_first` (default), `new_first`, `interleave`
  (`interleave_new_every = N`), `shuffle` (seeded, reproducible).
- **"Today":** local calendar day (midnight local → now), matching human intuition and the naive
  `datetime.now()` used across the codebase.

## Architecture

### Section 1 — Rules file + cascade (`core/policy/`, pure)

**`rules.py` — parse `policy.toml` into an ordered `list[Rule]`.**
```python
@dataclass(frozen=True)
class Rule:
    deck: str | None                     # None = every deck
    scope: Literal["all", "new", "due"]  # default "all"
    per_day: int | None
    per_session: int | None
    order: Literal["due_first", "new_first", "interleave", "shuffle"] | None
    interleave_new_every: int | None
```
Parsing raises `PolicyError` (loud) on: malformed TOML; an unknown key in a rule; an unknown
`scope`/`order` value; a negative `per_day`/`per_session`/`interleave_new_every`; or
`order = "interleave"` without `interleave_new_every`. Every message names the offending **rule
index** (and key). A **missing** `policy.toml` is not an error → returns `[]`.

**`resolve.py` — collapse the cascade into one `EffectivePolicy` per deck.**

Precedence weakest → strongest:
1. Built-in defaults — `order = "due_first"`, no caps.
2. `config.toml [defaults]` — seeds `new.per_day = daily_new_limit`, `due.per_day = daily_review_limit`.
3. That deck's `_deck.md` frontmatter — same two keys, per deck.
4. `policy.toml` `[[rule]]` list, in file order — a rule applies if `deck` is absent or matches;
   later matching rules override earlier ones, **key by key**.

```python
@dataclass(frozen=True)
class Limits:
    per_day: int | None
    per_session: int | None

@dataclass(frozen=True)
class EffectivePolicy:
    all: Limits
    new: Limits
    due: Limits
    order: str
    interleave_new_every: int | None
```
`scope` targets which `Limits` slot a rule writes: `new` and `due` resolve independently; `all`
caps the combined queue.

### Section 2 — Enforcement + widened seam

The current `ReviewPolicy.build_queue(cards, now, daily_new_limit)` is too narrow (a single int,
no history). Widen it to a context object:

```python
@dataclass(frozen=True)
class DoneToday:
    new: int
    due: int
    total: int

@dataclass(frozen=True)
class QueueContext:
    cards: list[Card]
    now: datetime
    policy: EffectivePolicy
    done_today: DoneToday
    seed: int                # reproducible "shuffle"

class ReviewPolicy(Protocol):
    def build_queue(self, ctx: QueueContext) -> list[Card]: ...
```

`SimplePolicy` is **replaced** by `RulesPolicy` (its tests migrate) — no vestigial second ordering
source. `RulesPolicy.build_queue(ctx)`:
1. **Partition** — `due` = not suspended, `state != "new"`, `due <= now`; `new` = not suspended,
   `state == "new"`.
2. **Budgets** — per scope, effective cap = `min(per_day − done_today, per_session)`, ignoring
   `None` (unlimited), **clamped at 0**. An over-budget day yields 0 of that scope.
3. **Select** — sort `due` by due ascending, take `due[:due_cap]`; take `new[:new_cap]`.
4. **Order** — `due_first` (due then new), `new_first` (new then due), `interleave` (one new after
   every `interleave_new_every` due), `shuffle` (seeded shuffle of the combined set).
5. **Trim** — apply the `all` cap to the ordered list LAST.

Consequence (intended): per-scope caps apply before ordering, the `all` cap after — so an `all`
cap can trim cards the per-scope caps admitted; the combined ceiling always wins (not a
proportional split).

`QueueService.build()` becomes the assembler: resolve the deck's `EffectivePolicy` (cascade),
query `DoneToday`, construct `QueueContext`, call the policy, then build display items exactly as
today. The `GET /reviews/queue` endpoint signature is unchanged.

### Section 3 — Deck attribution + `done_today`

**Schema:** `ReviewLog` gains `deck_folder: str | None` + an index on `(deck_folder,
review_time)` (every daily-budget query filters that pair). One additive Alembic migration
(`review_deck_0004`), nullable → no backfill.

**Populate:** `ReviewService.rate()` already fetches `repo.get_card(card_id)` (raising
`CardNotFoundError` if absent), so `card.deck_folder` is in hand; it writes
`deck_folder=card.deck_folder.name` on the new `ReviewLog` row. Two-line change to an existing,
tested method.

**Historical rows keep `deck_folder = NULL`** and are excluded from per-deck counts (honest
under-count rather than mis-attribution). On deploy day, that day's earlier reviews won't count
against budgets.

**`done_today` query** (a small live function/repository — NOT in the dead
`repositories/review_log.py`):
```sql
SELECT state_before, COUNT(*)
FROM review_log
WHERE deck_folder = :deck AND review_time >= :start_of_today
GROUP BY state_before
```
- `new` = rows with `state_before == "new"` (how `ReviewService` records a first-ever review).
- `due` = all other rows. `total` = both.
- "Today" = local midnight → now.

## Error handling (no silent failures)

- `PolicyError(MnemonicError)` for every malformed-rules case above, each naming the rule index +
  key. Surfaced by `GET /reviews/queue` as **422** with that detail. A broken rules file must
  never silently degrade to "no limits" (which would over-serve cards unseen).
- Missing `policy.toml` is valid (no rules; cascade layers 1–3 apply). Only a present-but-broken
  file raises.
- `done_today` counts clamp at 0 → an over-budget day yields an empty queue (a legitimate 200 with
  `[]`, the existing "Nothing due" UI), never a negative slice.

### Error mapping

| Exception | HTTP |
|---|---|
| `PolicyError` (broken policy.toml) | 422 |
| `DeckNotFoundError` (existing) | 404 |

## Testing

**Backend (pytest, TDD):**
- `rules.py`: parses a valid multi-rule file; missing file → `[]`; each raise-case (unknown key,
  bad `order`, bad `scope`, negative limit, interleave without `N`) → `PolicyError` naming the
  rule index.
- `resolve.py`: later rule overrides earlier, key by key; a `deck`-scoped rule beats a global one;
  `scope="new"` / `scope="due"` write independent slots; `_deck.md` overrides `config [defaults]`;
  rules override `_deck.md`.
- `RulesPolicy`: due sorted by due; suspended + future-due excluded; `per_day − done_today`;
  `per_session` cap; `min()` of both; over-budget → 0; each of the four orderings;
  `interleave_new_every`; `shuffle` deterministic under a fixed seed; `all` cap trims after
  ordering.
- `done_today`: splits new vs due on `state_before == "new"`; filters to the deck; excludes
  yesterday; ignores NULL-deck historical rows.
- `ReviewService.rate` writes `deck_folder` (existing review tests still green).
- API: a deck's queue honours its limits; a broken `policy.toml` → 422.

**Coverage:** `core/policy/` (pure) to the 95% `core/` bar; service/route to backend 85%.

## Out of scope (each its own follow-up)

- Time-based limits (time/day, time/session) + the session timer/aggregation + study-screen
  enforcement — **B1-Policy-B**.
- A `GET /reviews/limits` endpoint or any UI showing remaining budgets.
- Deleting the broken `db/repositories/review_log.py`.
- B2 (variation display) — separate spec.
