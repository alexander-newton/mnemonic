# Card Integrity & Change Detection — Design

**Date:** 2026-06-11
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

Card identity in Mnemonic is the block ID `^card-xyz` (stored as `SchedulingState.card_id`),
which survives edits to a note. Today the **core content** a user authors (the `## Card`
section) is never hashed and card edits are completely untracked — Mnemonic assumes the user
edits freely in Obsidian and only ever appends to `## Variations`.

This means there is no way to know when the core of a card has materially changed, even though
such a change can invalidate downstream artefacts that were derived from the old core:

- **Variations** in `## Variations` were generated from the old core and may now be wrong.
- **FSRS scheduling history** (stability/difficulty) was earned against the old card.
- **DSPy training examples** reference the old base Q/A.

We also have no systematic detection of **orphaned references** (review logs, variation
metadata, or decomposition children pointing at cards that no longer exist) beyond the existing
`SchedulingState.orphan` flag set when a note/block is deleted, and no **duplicate** detection.

## Goals

1. Detect when a card's core content changes, distinguishing **trivial** edits (typo/format)
   from **material** edits (meaning may have shifted) and **structural** cloze changes.
2. On a material/structural change: automatically invalidate derived artefacts that are
   **reversible** (variations, training examples), and **surface** — never auto-apply — the
   **destructive** FSRS reset.
3. Detect orphaned references: dangling `ReviewLog.card_id`, `VariationMeta.card_id`, and
   `parent_card_id`.
4. Detect duplicate cards (identical normalized core).
5. Keep a timestamped audit history of core-hash transitions.

## Non-Goals

- No automatic FSRS reset. The destructive action is always a user decision (see Policy).
- No LLM-based change judgement. The materiality gate is deterministic (two-tier hash).
- No deletion of historical audit data (e.g. dangling `ReviewLog` rows are reported, not purged).
- The "review changed cards" **UI panel** is future work; this spec produces the data it reads.

## Policy (decided)

- **Materiality gate:** two-tier hash — a raw hash and a normalized hash, plus a separate
  cloze-structure signature. Raw-only difference ⇒ trivial. Normalized difference ⇒ material.
  Cloze-signature difference ⇒ structural. Deterministic, no LLM.
- **On material/structural change:** variations and training examples are auto-invalidated
  (reversible exclusion); FSRS scheduling is **surfaced only** — the card is flagged
  `core_changed` and listed in a review panel where the user chooses keep / soft-reset /
  full-reset per card. Nothing destructive happens without an explicit click.
- **Trivial change:** logged to the audit table for history, but does **not** flag the card or
  touch any derived artefact.

## Architecture (Approach C)

Pure decision logic lives in `core/integrity/` as small, stateless, I/O-free functions, each
independently testable to the `core/` 95% coverage bar. The existing vault scan / reconciliation
pass is the single stateful caller: it reads stored hashes, calls the pure functions, and writes
results back. No second vault walk; integrity logic stays out of the data-access layer.

```
core/integrity/
├── hashing.py      normalize_core, compute_core_hash, compute_normalized_hash, cloze_signature
├── classify.py     classify_change → ChangeVerdict
├── orphans.py      find_dangling_refs → DanglingRefs
└── duplicates.py   find_duplicates → list[DuplicateGroup]
```

### Pure function signatures

```python
# hashing.py
def normalize_core(card_body: str) -> str
    # NFC → strip block-ID token (^card-xyz) → reduce {{cN::ans}} to "ans"
    # → case-fold → collapse whitespace runs → trim. Pure string transform.
    # Conservative by design: case + whitespace only, NO punctuation stripping
    # (punctuation is meaningful in math/code cards). Raises on empty body.

def compute_core_hash(card_body: str) -> str          # SHA-256 of verbatim body (block-ID excluded)
def compute_normalized_hash(card_body: str) -> str    # SHA-256 of normalize_core(body)
def cloze_signature(card_body: str) -> str | None     # canonical hash of sorted (cN, answer) set; None if no cloze

# classify.py
@dataclass(frozen=True)
class ChangeVerdict:
    kind: Literal["new", "unchanged", "trivial", "material", "cloze_structure"]

def classify_change(stored: StoredHashes | None, current: CurrentHashes) -> ChangeVerdict

# orphans.py
def find_dangling_refs(
    live_card_ids: set[str],
    review_card_ids, variation_card_ids, parent_links,
) -> DanglingRefs   # buckets: review_logs, variations, parents

# duplicates.py
def find_duplicates(normalized_by_card: dict[str, str]) -> list[DuplicateGroup]
```

### `classify_change` decision table (first match wins)

| Condition | kind |
|---|---|
| `stored is None` | `new` |
| all three hashes equal | `unchanged` |
| raw differs, normalized **and** cloze_sig equal | `trivial` |
| cloze_sig differs | `cloze_structure` |
| normalized differs | `material` |

`cloze_structure` is checked before `material` so a pure renumber/add/remove is labelled
structurally even if it also nudges the normalized hash.

## Data model changes

One additive Alembic migration, all columns nullable/defaulted, no backfill. Existing cards get
hashes populated on the next scan; a null `core_hash` reads as "first time seen" (`new`).

**`SchedulingState`** (add):
- `core_hash: str | None` — SHA-256 of verbatim `## Card` body (block-ID token excluded).
- `core_hash_normalized: str | None` — SHA-256 of normalized body; the materiality signal.
- `cloze_signature: str | None` — canonical hash of the cloze identity set.
- `core_changed: bool = 0` — "material change awaiting reconciliation"; queried by the panel.
- `core_changed_at: datetime | None`.

**`VariationMeta`** (add):
- `invalidated_at: datetime | None` — non-null ⇒ stale (not shown). Reversible. Records *when*.

**`TrainingExample`** (add):
- `invalidated_at: datetime | None` — non-null ⇒ excluded from DSPy optimization. Reversible.

**New table `CoreChangeLog`** (audit history):
- `id, card_id, change_kind, old_hash, new_hash, old_normalized, new_normalized, detected_at`
- `change_kind ∈ {new, trivial, material, cloze_structure}`.

**Duplicate detection** — no table; query `GROUP BY core_hash_normalized HAVING COUNT(*) > 1`,
surfaced in the report on demand.

**Orphan-reference checks** — reuse existing `orphan` bool:
- Dangling `parent_card_id` ⇒ set child `orphan=True`.
- Dangling `VariationMeta.card_id` ⇒ set its `invalidated_at`.
- Dangling `ReviewLog.card_id` ⇒ retained + reported only (audit data, never mutated).

## Orchestration — reconciliation hook

The one stateful place wiring pure functions to the DB, run inside the existing scan pass.

```
scan_vault() → list[ScannedCard]              (already exists)
        │
        ▼
for each scanned card:
    current = CurrentHashes(compute_core_hash, compute_normalized_hash, cloze_signature)
    stored  = load StoredHashes from SchedulingState  (None if new card)
    verdict = classify_change(stored, current)
    apply(verdict, card, current)        ← the only mutating step
        │
        ▼
after the loop, on the full card set:
    find_dangling_refs(live_ids, review_ids, variation_ids, parent_links)
    find_duplicates(normalized_by_card)
        │
        ▼
return ReconciliationReport            ← structured result the API/panel reads
```

### `apply(verdict, …)` action matrix

| verdict | hashes written | `core_changed` | audit row | variations | training | FSRS |
|---|---|---|---|---|---|---|
| `new` | yes | no | `new` | — | — | untouched |
| `unchanged` | no-op | — | — | — | — | untouched |
| `trivial` | yes (refresh raw) | no | `trivial` | — | — | untouched |
| `material` | yes | **set** | `material` | `invalidated_at` set | `invalidated_at` set | **surfaced only** |
| `cloze_structure` | yes | **set** | `cloze_structure` | `invalidated_at` set | `invalidated_at` set | **surfaced only** |

Reversible invalidations fire automatically; the destructive FSRS reset never happens here — it
is only *listed* via `core_changed` for the review panel (keep / soft-reset / full-reset per
card). Idempotent by construction: a second scan with no edits classifies everything `unchanged`
and writes nothing.

**`ReconciliationReport`** carries: counts per change kind, the dangling-ref buckets, and
duplicate groups — one scan surfaces changes, orphans, and dupes in one structured object.

## Error handling (no silent failures)

- Malformed input **raises**, never coerces: `compute_core_hash` on an empty `## Card` body
  raises `IntegrityError("Card {id} has an empty core body — cannot hash. The note may be
  malformed.")` rather than hashing `""` and treating every empty card as a duplicate.
- A normalized-hash collision between genuinely different cards is surfaced as a **duplicate
  candidate** for the user to judge, never auto-merged.
- A DB error mid-loop **fails the whole scan loudly** with the offending `card_id` in the
  message; no partial-commit of a hash subset with the rest silently skipped. (Transaction
  granularity — single scan-wide vs per-card with aggregated error report — settled in the plan;
  the principle is no card silently skipped.)
- Dangling `ReviewLog` rows are reported, never deleted — destroying audit data to "clean up"
  would itself be silent data loss.

## Testing (TDD, `core/` → 95%)

- **hashing.py:** normalization idempotence (`normalize(normalize(x)) == normalize(x)`);
  whitespace/case folding → same hash; cloze-marker reduction; empty body raises; Unicode NFC
  equivalence.
- **classify.py:** one test per decision-table row; ordering guarantee (cloze renumber →
  `cloze_structure`, not `material`); `stored is None` → `new`.
- **orphans.py / duplicates.py:** dangling in each of the three buckets; no false positive when
  all refs live; duplicate grouping with 2 and 3+ members; case-only difference grouped,
  punctuation difference not grouped.
- **Integration (hook):** seed card, scan, assert hashes stored + `unchanged` on rescan; trivial
  edit → `trivial`, FSRS untouched, no flag; material edit → `material`, variations/training
  `invalidated_at` set, `core_changed` flagged, FSRS untouched; delete note → child
  `parent_card_id` orphaned; full `ReconciliationReport` shape asserted.

## Open items for the implementation plan

- Transaction granularity for the reconciliation loop (scan-wide vs per-card + aggregated errors).
- Exact `IntegrityError` placement in the exception hierarchy (`exceptions.py`).
- The "review changed cards" UI panel and its API endpoint (future work; out of scope here).
