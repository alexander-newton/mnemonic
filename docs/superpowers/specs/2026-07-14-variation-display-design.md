# Variation Display During Review (B2-Display) — Design

**Date:** 2026-07-14
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

Mnemonic's premise is LLM-generated question variations, but nothing has ever displayed one. The
`invalidated_at` column added by the card-integrity work (which marks variations stale when a
card's core changes) has no read path to filter — only the DSPy trainset builder respects it.
Now that a review screen exists (B1-Loop), variations have somewhere to live.

Two findings from exploration shape this spec:

- **Generation is not wired at all.** `persist_variation` / `VariationGenerator.generate` are
  called **only from tests** — no CLI, schedule, review hook, or route invokes them. A real vault
  today therefore contains **zero variations**; the `## Variations` note section is populated only
  by the test suite.
- **The displayable text is recoverable after all.** `VariationMeta` stores only a one-way
  `content_hash` and a whole-file `note_path`, with no link to a specific note entry (note entries
  carry no id or anchor). But `persist_variation` writes a `TrainingExample` in the same
  transaction sharing the same `variation_id`, with the verbatim text in `variation_q` /
  `variation_a`. So display text comes from a `VariationMeta → TrainingExample` join — no fragile
  note parsing, no missing-linkage problem.

## Scope & decomposition

This is **B2-Display**, the first of two cycles:

- **B2-Display (this spec):** select a non-invalidated variation per card, surface it into the
  queue item, render it in the study screen (replacing the question), and capture helpfulness
  feedback. Degrades to the base card whenever no variation is available — so it is fully testable
  against seeded variations even though generation is unwired.
- **B2-Gen (deferred):** actually wire generation (CLI and/or review-time trigger, budget-guarded
  via the existing `BudgetGuard`, honoring `variation_frequency`) so variations accrue in a real
  vault. Its own spec — it carries the LLM cost decisions.

## Decisions (locked)

- **Variation replaces the question.** The variation's question is shown in place of the base
  front; revealing shows the variation's answer. That is the point of variations — practising
  recall against a rephrasing rather than memorising one wording.
- **Frequency-gated, least-shown-first selection.** Per card, roll against the deck's
  `variation_frequency`; if it passes, pick the non-invalidated variation with the lowest
  `shown_count` (ties → newest `generated_at`, then `variation_id`).
- **Degrade, don't fail.** Any missing/!invalid variation data falls back to the base card.

## Architecture

### Section 1 — Backend: selection

**Pure chooser — `core/variation/choose.py`** (no I/O; 95% coverage bar):
```python
@dataclass(frozen=True)
class VariationCandidate:
    variation_id: str
    question: str
    answer: str
    shown_count: int
    generated_at: datetime


def choose_variation(
    candidates: list[VariationCandidate], *, enabled: bool, frequency: float, roll: float
) -> VariationCandidate | None
```
Returns `None` when `not enabled`, when `candidates` is empty, or when `roll >= frequency` (so
`frequency = 0.0` never varies and `1.0` always does). Otherwise selects the lowest `shown_count`,
breaking ties by newest `generated_at` and then by `variation_id` for total determinism.
`frequency` is clamped to `[0.0, 1.0]`. Taking `roll` as a parameter (rather than calling `random`
internally) keeps the function pure and seed-testable.

**Candidate query — `QueueService._variation_candidates(card_ids)`**, one batched query returning
`dict[card_id, list[VariationCandidate]]`:
```sql
SELECT vm.card_id, vm.id, te.variation_q, te.variation_a, vm.shown_count, vm.generated_at
FROM variation_meta vm
JOIN training_example te ON te.variation_id = vm.id
WHERE vm.card_id IN (:ids) AND vm.invalidated_at IS NULL
```
This is the first real consumer of `invalidated_at` on the display side. The inner join means a
`VariationMeta` row without its `TrainingExample` sibling simply produces no candidate (fallback to
base), rather than an error.

### Section 2 — Backend: queue item + rate feedback

**`QueuedCard`** gains three fields, all defaulted so existing constructions keep working:
```python
    variation_id: str | None = None
    variation_front: str | None = None
    variation_answer: str | None = None
```
`QueueService.build` batches the candidate query across the queue's cards; `_to_item` calls
`choose_variation(...)` with the deck's `variation_enabled` / `variation_frequency` (from
`_deck.md`; **disabled** when the deck has no config) and a roll from a seeded RNG. When a
variation is chosen the three fields are populated; otherwise they remain `None` and the card
renders exactly as today. This is the first code to consume `variation_enabled` /
`variation_frequency`, which until now were parsed and round-tripped but read by nothing.

**Serialization** adds the three fields to `_serialize_queued` (null when absent):
```json
{ "card_id": "…", "front": "…", "answer": "…", "previews": {…},
  "variation_id": "var-abc", "variation_front": "In a 2-player game…",
  "variation_answer": "A Nash equilibrium." }
```

**Rate feedback.** `POST /reviews/rate` already accepts `variation_id` / `variation_helpful` and
writes both to `ReviewLog` — no contract change. One gap is closed here: `ReviewService.rate`
never incremented `VariationMeta.shown_count` / `helpful_count`, so least-shown-first selection
would never rotate. `rate()` now increments `shown_count` when a `variation_id` is supplied, and
`helpful_count` when `variation_helpful` is truthy. An unknown `variation_id` is ignored for the
counters (optional telemetry, not a correctness invariant) but is still recorded on the
`ReviewLog`.

### Section 3 — Frontend: rendering + helpfulness

**Types & client.** `QueuedCard` gains `variation_id`, `variation_front`, `variation_answer` (all
`string | null`). `api.rate`'s payload type widens to accept optional `variation_id` and
`variation_helpful` — the backend already accepts them; the client currently strips them.

**Display.** `StudyPage` resolves the faces per card:
```ts
const isVariation = card.variation_id != null;
const front  = card.variation_front  ?? card.front;
const answer = card.variation_answer ?? card.answer;
```
With no variation the behaviour is byte-identical to today. A small `Badge` ("variation") marks
when a rephrasing is being shown — without it the changed wording is unexplained and undermines
trust in the card.

**Helpfulness.** When `isVariation`, an optional control appears *after reveal* beside the rating
buttons: "Was this rephrasing helpful?" 👍 / 👎, setting local state (`helpful: 1 | 0 | null`).
Rating without answering is allowed. On rate:
```ts
api.rate({
  card_id, rating, response_time_ms,
  ...(isVariation && { variation_id: card.variation_id, variation_helpful: helpful ?? undefined }),
})
```
`helpful` resets on advance with the other per-card state. The reveal flow, rating buttons, session
clock, and end screens are untouched.

## Error handling (degrade, never break the review)

- `VariationMeta` with no matching `TrainingExample` → no candidate → base card. A data-shape gap
  must not fail a study session.
- `variation_frequency` outside `[0.0, 1.0]` is **clamped**, not raised — it comes from `_deck.md`
  (already validated at parse time), and a study session is the wrong place to hard-fail on a
  config typo. (Contrast `policy.toml`, which *does* raise, because a silent mis-parse there would
  silently over-serve cards.)
- No deck config → variations disabled (conservative default).
- Unknown `variation_id` at rate time → counters skipped; the `ReviewLog` still records it.
- A failing variation query propagates — that means a broken DB, not absent variations.

## Testing

**Backend (pytest, TDD):**
- `choose_variation` (pure): disabled → `None`; empty → `None`; `roll >= frequency` → `None`;
  `frequency=1.0` always picks; lowest `shown_count` wins; tie → newest `generated_at`; further tie
  → stable by `variation_id`; frequency clamping.
- Candidate query: only `invalidated_at IS NULL` rows; joins the Q/A text; a `VariationMeta`
  without its `TrainingExample` is absent; batches across multiple cards.
- `QueueService.build`: card with a valid variation gets the three fields; `variation_enabled=false`
  → all `None`; no deck config → `None`; only-invalidated variations → `None`.
- `ReviewService.rate`: increments `shown_count`; increments `helpful_count` only when helpful;
  unknown `variation_id` is a no-op but still lands on the `ReviewLog`.
- API: the three fields serialize, and are `null` when absent.

**Frontend (Vitest + RTL):**
- `StudyPage` renders `variation_front` when present and the base `front` when not; the "variation"
  badge appears only for variations.
- The helpfulness control appears only after reveal and only for variations; 👍 then rate posts
  `variation_id` + `variation_helpful: 1`; rating without touching it omits `variation_helpful`.
- A non-variation card posts no variation fields (unchanged behaviour).

**Coverage:** `core/variation/` to the 95% `core/` bar; service/route to backend 85%; frontend
additions to 75%.

## Out of scope (follow-ups)

- **B2-Gen** — wiring variation generation (CLI / review-time trigger, budget-guarded) so
  variations actually accrue. Separate spec.
- Per-entry ids/anchors in the note's `## Variations` section, or denormalizing `variation_q` /
  `variation_a` onto `VariationMeta` (the `TrainingExample` join covers display today).
- Editing or deleting variations from the UI.
- Deleting the dead `db/repositories/review_log.py`.
