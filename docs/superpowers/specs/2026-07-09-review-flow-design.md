# Review/Study Flow (B1-Loop) — Design

**Date:** 2026-07-09
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

Mnemonic is a spaced-repetition system, but there is no way to actually review cards.
The rating write path exists end-to-end (`POST /reviews/rate` → `ReviewService.rate` → FSRS
`schedule_review` → persists `SchedulingState` + `ReviewLog` with the next `due`), and
`preview_schedule()` can compute per-rating intervals — but nothing builds a queue of due cards,
nothing renders a card for display, and the frontend has no review screen. This sub-project
builds the review loop: pick due cards → show the front → reveal the answer → rate 1–4.

## Scope & decomposition

This is **B1-Loop**, the first of the review work. Two deliberate deferrals, each its own future
cycle:

- **B1-Policy (deferred)** — a cascading review-policy rules engine (a rules text file where later
  rules override earlier; limits by cards/day, time/day, time/session, cards/session, split by
  new vs due, global or per-deck; ordering/interleaving rules). B1-Loop builds a `ReviewPolicy`
  **seam** and a `SimplePolicy` placeholder; the engine plugs in behind that seam with no endpoint
  changes.
- **B2 (deferred)** — variation display (show a non-invalidated LLM variation instead of the base
  question during review). B1-Loop shows the base question only.

## Decisions (locked)

- **Rendering:** markdown + `$…$` math rendered **client-side**; the backend returns clean
  markdown faces (never raw cloze markers).
- **Queue (simple policy):** per-deck; due review cards (`due <= now`, not suspended,
  `state != "new"`) ordered by `due` asc, then new cards capped at `daily_new_limit`. No time
  limits, no cross-session daily counting yet (that is B1-Policy).
- **Rating:** reuse the existing `POST /reviews/rate` unchanged.
- **Theme:** a plain, muted **warm off-white** theme via the existing Tailwind setup (no Bootstrap
  — it would collide with Tailwind). **Font** configurable via a Settings-page dropdown.

## Architecture

### Backend

**Card faces — `core/review/faces.py` (pure).** Produces the two display faces per card from the
extractor output, as clean markdown (math untouched):
- `front`: the question, cloze/highlight blanks shown as `[...]` (already produced by extractors).
- `answer`: the revealed form. Cloze: replace each `{{cN::x}}` with `x` (the answer). Highlight:
  the extractor's `back` is already revealed — pass through. Callout: the extractor's `back` is the
  answer — pass through. Unknown syntax raises `RenderError` (loud, with `card_id` context) rather
  than leaking raw markers.

**Queue — `services/review_queue.py`.**
- `ReviewPolicy` protocol: `build_queue(cards: list[Card], now: datetime) -> list[Card]` — the seam
  B1-Policy replaces.
- `SimplePolicy(ReviewPolicy)`: due review cards (`due <= now`, not `suspended`, `state != "new"`)
  ordered by `due` asc, then new cards (`state == "new"`, not suspended) appended, capped at the
  deck's `daily_new_limit`.
- `QueueService(repo, engine)`: `build(deck_folder) -> list[QueuedCard]` — resolves the deck (404
  via `DeckNotFoundError` if missing), lists its cards, runs the policy, and for each card computes
  the faces (`faces.py`) and the 4 preview intervals (`preview_schedule` against the card's current
  FSRS state; a new card previews from `NEW_CARD_DEFAULTS`). `QueuedCard` is a frozen dataclass:
  `card_id`, `syntax`, `front`, `answer`, `previews: dict[int, int]` (rating → days).

**Endpoint — `GET /api/reviews/queue?deck=<folder>`** → list of serialized `QueuedCard`:
```json
[{ "card_id": "card-abc", "syntax": "cloze",
   "front": "What is a [...]?",
   "answer": "What is a **Nash equilibrium**?",
   "previews": { "1": 0, "2": 1, "3": 4, "4": 9 } }]
```
A `get_queue_service()` provider is added to `deps.py`. Rating stays on the existing
`POST /reviews/rate` (no change).

### Frontend

- **Route & launch:** `/study/:folder`, reached via a "Study" button on `DeckDetailPage`.
- **`hooks/useReviewQueue.ts`:** `useReviewQueue(folder)` query (+ `api.reviewQueue(folder)`).
- **`components/review/CardContent.tsx`:** renders markdown + math via `react-markdown` +
  `remark-math` + `rehype-katex` (KaTeX — lighter/more reliable in React than wiring the currently
  unused `mathjax` dep). Used for both faces.
- **`components/review/RatingButtons.tsx`:** four buttons (Again/Hard/Good/Easy) labeled with their
  preview intervals (`Again <1d`, `Good 4d`, …); disabled while a rating is in flight.
- **`pages/StudyPage.tsx`:** walks the queue in local state (index, revealed flag, per-card show
  time). Front only → "Show answer" reveals `answer` + rating buttons → on rate, `POST
  /reviews/rate` with `response_time_ms` (measured from card show to rating), then advance. End of
  queue → summary ("Reviewed N cards · Done", link back to deck). Empty queue → "Nothing due in
  this deck right now." Keyboard: Space/Enter reveals; `1`–`4` rate once revealed.

### Theme & font

- **Tokens as CSS variables** on `:root` (global stylesheet): `--app-bg: #f4f2ee`,
  `--app-surface: #faf9f6`, `--app-text: #1f2328`, `--app-text-muted: #5a5f66`,
  `--app-border: #e5e1d8`, `--app-font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
  `body` uses bg/text/font vars.
- **Tailwind** `tailwind.config` gains semantic colors (`app`, `surface`, `muted`, `border-app`)
  mapped to the vars → `bg-app`, `bg-surface`, `text-muted`, etc. A bounded sweep swaps top-level
  `bg-gray-50` → `bg-app` and `bg-white` → `bg-surface` on existing page/card wrappers; the review
  screen uses the tokens natively.
- **Font picker:** `hooks/useFontPreference.ts` reads a saved choice from `localStorage`, sets
  `--app-font` on `:root` at startup and on change (live, no reload). `SettingsPage.tsx` gains a
  **Font** dropdown of curated no-download stacks — *System sans* (default), *Humanist sans*
  (`"Segoe UI", Roboto, sans-serif`), *Serif* (`Georgia, "Times New Roman", serif`), *Monospace*
  (`"JetBrains Mono", "Courier New", monospace`) — persisted to `localStorage`.

## Error handling (no silent failures)

- Missing deck folder → `DeckNotFoundError` → 404. Empty queue → 200 with `[]` (the "nothing due"
  UI), not an error.
- `faces.py` raises `RenderError` (with `card_id`) on a card whose syntax it cannot reveal, rather
  than leaking raw `{{cN::}}`.
- A failed `POST /reviews/rate` keeps the user on the current card with an `ErrorMessage` and
  re-enabled buttons — the rating is never silently dropped or skipped.
- A new card (no scheduling row) previews from `NEW_CARD_DEFAULTS`.

### Error mapping

| Exception | HTTP |
|---|---|
| `DeckNotFoundError` | 404 |
| `RenderError` (un-revealable card) | 422 |

## Testing

**Backend (pytest, TDD):**
- `faces.py`: cloze reveal (`{{c1::x}}` → `x`; front blanks intact; math untouched); highlight
  passthrough; callout Q/A; unknown syntax raises `RenderError`.
- `SimplePolicy`: due cards ordered by `due`; suspended excluded; future-due excluded; new cards
  appended and capped at `daily_new_limit`.
- `QueueService` / `GET /reviews/queue`: item shape incl. `front`/`answer`/`previews`; 404 missing
  deck; empty deck → `[]`.

**Frontend (Vitest + RTL):**
- `useReviewQueue`: fetches and returns the queue.
- `CardContent`: renders markdown + inline math (KaTeX output present in the DOM).
- `StudyPage` flow: front → reveal → rating posts `rate` with correct `card_id`/`rating` → advances
  → end summary; queue-fetch error → `ErrorMessage`.
- `useFontPreference`: sets `--app-font` from a stored value; Settings change persists + updates the
  variable.

**Coverage:** `core/review/faces.py` (pure) + policy to the `core/` 95% bar; services/routes to
backend 85%; new frontend components/hooks to 75%.

## Out of scope

- B1-Policy (the cascading rules engine) — separate spec.
- B2 (variation display) — separate spec.
- Editing the review while studying, undo, bury/suspend from the review screen — YAGNI for now.
- Any change to the FSRS algorithm or the `POST /reviews/rate` write path.
