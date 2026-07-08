# Review Changed Cards — Design (Sub-project A)

**Date:** 2026-06-12
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

The card-integrity feature sets `SchedulingState.core_changed = True` when a card's core
content changes materially or structurally (see
`2026-06-11-card-integrity-hashing-design.md`). By design, reconciliation **flags but never
resets** FSRS scheduling — the destructive decision is left to the user. Today nothing consumes
that flag: there is no way to see which cards changed or to act on them. This sub-project builds
the full vertical slice — backend service + endpoints and a React panel — so the user can review
flagged cards and choose, per card, what happens to its scheduling.

## Scope

This is sub-project **A** of two decomposed follow-ups. Sub-project **B** (the variation-display
subsystem that would let `invalidated_at` filter a variation read path) is out of scope here and
gets its own spec — it has no read path today and only the DSPy trainset builder currently
respects `invalidated_at`.

## Decisions (locked)

The three per-card actions:

| Decision | FSRS effect | Flag |
|---|---|---|
| `keep` | nothing | clear `core_changed`, `core_changed_at` |
| `soft_reset` | `due = now`; **preserve** `state`, `stability`, `difficulty`, `reps`, `lapses` | clear flag |
| `full_reset` | restore brand-new defaults (`state="new"`, `stability=0.0`, `difficulty=5.0`, `due=None`, `reps=0`, `lapses=0`) | clear flag |

Soft-reset surfaces the card for review immediately while keeping its memory model intact; if the
user still knows it, the history is undamaged. Full-reset discards real scheduling history and is
therefore confirmed in the UI.

## Architecture

Backend logic in a new focused service; two card-scoped endpoints; a React panel modeled on the
existing deck-list page. No changes to the read-path scan (GETs stay side-effect-free).

### Backend: reset logic + service

**`core/fsrs` — `NEW_CARD_DEFAULTS`.** The brand-new field values are currently duplicated inline
in `services/review.py:96` and `vault/repository.py:75`. Extract them once into `core/fsrs` as the
single source of truth and reuse for full-reset. Refactor those two call sites to consume it (DRY
improvement to code we're touching; covered by regression tests).

**`services/core_change.py` — `CoreChangeService`** (mirrors `ReviewService`: constructed with
`repo` + `engine`, mutates inside `session_scope`):

- `list_changed() -> list[ChangedCard]` — selects `SchedulingState` rows where
  `core_changed == True`, joins card content from a single `repo.list_cards()` scan, and attaches
  the latest `CoreChangeLog.change_kind` per card (so the panel shows *why* a card is flagged).
  `ChangedCard` is a frozen dataclass: `card_id`, `title`, `front`, `syntax`, `change_kind`,
  `core_changed_at`, `state`, `due`, `stability`, `difficulty`.
- `apply(card_id: str, decision: str, now: datetime) -> None` — loads the `SchedulingState` row;
  applies the decision table above. `decision` is
  `Literal["keep", "soft_reset", "full_reset"]`.

Rationale for a separate service over extending `ReviewService`: keeps the rating path focused and
gives this feature its own clean, independently testable interface.

### Backend: endpoints + serialization

Both routes live in the existing `cards.py` router. A `get_core_change_service()` provider is
added to `deps.py` (so the endpoint is cleanly overridable in tests, like
`get_reconciliation_service`).

**`GET /api/cards/changed`** → list of `ChangedCard`, serialized:
```json
[{ "card_id": "card-abc", "title": "Nash equilibrium", "front": "...", "syntax": "cloze",
   "change_kind": "material", "core_changed_at": "2026-06-12T09:00:00",
   "state": "review", "due": "2026-06-10T...", "stability": 12.4, "difficulty": 6.1 }]
```

**`POST /api/cards/{card_id}/core-change`** body `{ "decision": "keep" | "soft_reset" | "full_reset" }`
→ updated scheduling snapshot:
```json
{ "card_id": "card-abc", "core_changed": false, "state": "new",
  "stability": 0.0, "difficulty": 5.0, "due": null, "reps": 0, "lapses": 0 }
```

One action endpoint with a `decision` enum in the body (not three paths) — small surface,
mirrors `POST /reviews/rate`.

**Serializer touch:** add `core_changed` + `core_changed_at` to the `Card` dataclass
(`vault/repository.py`) and the `cards.py` `_serialize` helper (currently omitted), keeping the
two card representations consistent.

### Frontend: the panel

Modeled on `pages/DeckListPage.tsx` (TanStack Query + `Skeleton`/`ErrorMessage`/`EmptyState`,
reusing the `ui/` kit). Frontend lives at repo-root `frontend/` (not under `backend/`); the live
API client is the flat `frontend/src/services/api.ts` (the modular `services/api/` dir is dead
code).

- **Route & nav:** new `/changed` route in `App.tsx`; a "Changed Cards" entry in
  `components/Navigation.tsx` with a count badge when > 0.
- **API client** (`services/api.ts`): `listChangedCards()` → `GET /api/cards/changed`;
  `applyCoreChange(cardId, decision)` → `POST /api/cards/{id}/core-change`.
- **Hook** (`hooks/useChangedCards.ts`): `useChangedCards()` query + `useApplyCoreChange()`
  mutation that invalidates the changed-cards query on success (query-key-factory pattern from
  `hooks/useCards.ts`).
- **Layout:** a list of rows, each showing title/front, a badge for `change_kind`, relative time,
  a `due`/`stability` line, and three action buttons.

```
┌─ Changed Cards ────────────────────────────────────────────┐
│  3 cards changed since their scheduling was set            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Nash equilibrium              [material]  2h ago     │ │
│  │ "What is a {{Nash equilibrium}}?"                    │ │
│  │ due in 4d · stability 12.4                           │ │
│  │              [ Keep ]  [ Soft reset ]  [ Full reset ]│ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

- **Interaction:** `keep` and `soft_reset` apply immediately; the row drops out on success.
  `full_reset` is destructive → confirmation dialog reusing the `DeleteConfirmationDialog`
  pattern ("Reset *Nash equilibrium* to new? Its review history will be discarded."). Each button
  shows a pending state and disables during its mutation; errors surface via `ErrorMessage`.
  Empty state: "No changed cards — everything's in sync".

## Error handling (no silent failures)

- `CoreChangeService.apply` raises `CardNotFoundError` if the card has no `SchedulingState` row or
  is not flagged (`core_changed == False`) — you cannot resolve a card that is not flagged; loud
  404, not a silent no-op.
- Unknown `decision` string raises `ValidationError` → 400 (behind FastAPI's own body validation).
- The mutation runs in one `session_scope` transaction; any failure rolls back — no partial write.
- Frontend surfaces every mutation error via `ErrorMessage`; buttons re-enable on failure.

### Error mapping

| Exception | HTTP |
|---|---|
| `CardNotFoundError` | 404 |
| `ValidationError` | 400 |
| malformed body | 422 (FastAPI) |

## Testing

**Backend (pytest, TDD):**
- `core/fsrs`: `NEW_CARD_DEFAULTS` values equal the brand-new state; `review.py` / `repository.py`
  unchanged in behavior after the DRY extraction (regression).
- `CoreChangeService.apply`: one test per decision — `keep` leaves FSRS untouched + clears flag;
  `soft_reset` sets `due ≈ now` + preserves stability/difficulty/reps/lapses + clears flag;
  `full_reset` restores defaults + clears flag; not-flagged / missing card → `CardNotFoundError`;
  bad decision → `ValidationError`.
- `CoreChangeService.list_changed`: returns only flagged cards, correct `change_kind` from the
  latest `CoreChangeLog`, joined to card content.
- API (TestClient + `dependency_overrides`, like `test_vault_reconcile`): `GET /cards/changed`
  shape; each `POST` decision path; 404 and 400 mappings.

**Frontend (Vitest + RTL, modeled on `DeckListPage.test.tsx` + `useCards.test.tsx`):** list
renders flagged cards; each button fires the correct mutation with the right decision; full-reset
opens the confirm dialog and only mutates on confirm; empty state; error state.

**Coverage:** `core/` additions to 95%; service + routes to backend 85%; frontend panel + hook to
75%.

## Out of scope

- Sub-project B (variation display + `invalidated_at` read-path filter) — separate spec.
- Bulk actions (apply one decision to all changed cards) — YAGNI for now; per-card only.
- Any change to the reconciliation pass or read-path scan behavior.
