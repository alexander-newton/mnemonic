# Variation Generation (B2-Gen) — Design

**Date:** 2026-07-16
**Status:** Approved (design)
**Author:** Alexander (with Claude)

## Problem

B2-Display can show LLM variations during review, but nothing ever creates them:
`VariationGenerator.generate` and `persist_variation` are called **only from tests** — no CLI,
schedule, route, or review hook invokes them. A real vault therefore holds zero variations and
B2-Display is a no-op in practice.

Every leaf piece already exists and is unit-tested (`VariationGenerator`, `persist_variation`,
`select_strategy`, `pick_model`, `get_champion`, `BudgetGuard`, `OpenRouterBackend`). What is
missing is the **orchestrator** that assembles them and an **entry point** that runs it.

Exploration also surfaced two defects this feature depends on:

- **`persist_variation` hardcodes `shown_count=1`** (`llm/variation/writer.py`), so a brand-new
  variation is born "already shown once" — skewing the least-shown-first rotation B2-Display
  built. Fixed here (→ `0`).
- **The generator reads strategy prompts from disk and ignores `PromptVersion.instruction_text`**,
  so compiled challengers from `mnemonic-optimize` are never used, and the recorded
  `prompt_version_id` names a version whose text was not applied. Fixed here.

## Scope

Build the generation orchestrator plus a `mnemonic-generate` CLI. Decisions locked:

- **Prompt source:** use the champion `PromptVersion.instruction_text` (via a new optional
  override on `generate`), making the already-merged DSPy optimization pipeline actually affect
  generation.
- **Targets:** non-suspended cards, in `variation_enabled` decks, with **zero non-invalidated
  variations**, capped by `--limit` (default 20), optionally filtered by `--deck`, with
  `--dry-run`.
- **Failure policy:** budget exhaustion **stops the run**; per-card errors are **skipped and
  reported**; exit `1` if anything was skipped or the budget stopped the run.

**No background mechanism** is introduced: `main.py` has no lifecycle hooks, `watchdog` is an
unused dependency, and `config.vault.watch` is inert plumbing. An explicitly-invoked CLI is the
only mechanism consistent with the existing architecture.

Out of scope: a review-time or scheduled trigger; an API route for generation; making
`persist_variation` transactional across vault+DB (see Known limitations).

## Architecture

### Section 1 — Card selection

New `services/variation_gen.py` holds the orchestrator.

```python
@dataclass(frozen=True)
class GenerationTarget:
    card: Card          # from VaultRepository.list_cards()
    deck_folder: str
```

`select_targets(repo, engine, *, deck: str | None, limit: int) -> list[GenerationTarget]`:
1. `repo.list_cards()`, optionally filtered to one deck folder.
2. Drop suspended cards, and cards whose deck has `variation_enabled = False`. **No deck config →
   excluded** (generation is opt-in; it costs money).
3. Query the `card_id`s having ≥1 `VariationMeta` with `invalidated_at IS NULL` — the aggregate
   twin of the display query — and drop them.
4. Return the first `limit` remaining, ordered by `card_id` (deterministic runs).

This naturally covers both never-generated cards and cards whose variations reconciliation just
invalidated after a core edit.

**Bug fix:** `persist_variation` sets `shown_count=1` on creation; change to `0` so
least-shown-first rotation starts fair.

### Section 2 — Per-card generation pipeline

Three new accessors supply inputs `Card` does not carry:

- **`_note_inputs(note_path)`** — re-parses via `parse_note`, returning `card_section` (the **raw**
  `## Card` markdown, cloze markers intact — what the prompt requires) and `context_section`.
  Note this is deliberately *not* `build_faces` output, which strips block IDs and bolds cloze
  answers.
- **`_recent_ratings(engine, card_id, n=5)`** — last *n* `ReviewLog.rating` by `review_time` desc;
  feeds both `select_strategy` and the `fsrs` dict.
- **`_prior_variations(engine, card_id)`** — the `VariationMeta ⋈ TrainingExample` join (live rows
  only) as `[{q, a, rating}]`, so the model can avoid repeating itself.

`generate_for_card(...) -> str` (returns the new `variation_id`) assembles:

```python
strategy = select_strategy(reps=…, lapses=…, recent_ratings=…)
model    = pick_model(strategy=…, recent_failures=…, model_default=…, model_rephrase=…)
champion = get_champion(session, strategy)
variation = generator.generate(
    strategy=strategy, base_card_text=card_section, note_context=context_section,
    prior_variations=…, fsrs={"stability", "reps", "lapses", "recent_ratings"}, model=model,
    instruction_text=champion.instruction_text,     # NEW override
)
persist_variation(…, prompt_version_id=champion.id, arm="champion",
                  base_q=faces.front, base_a=faces.answer, note_context=context_section)
```

**Generator change:** `VariationGenerator.generate` gains `instruction_text: str | None = None`;
when supplied it replaces reading `strategies/<name>.md` from disk. Omitting it preserves today's
disk behaviour.

`base_q`/`base_a` remain `build_faces` output (clean display faces); `base_card_text` is the raw
section. The two serve different purposes and stay distinct.

### Section 3 — CLI, budget, failure handling

`cli/generate.py` follows the established shape (`cli/reconcile.py` + `cli/optimize.py::_resolve`):
a testable `run_generate(...)` seam with keyword-only args and no `load_config()` inside, plus a
thin `main(argv) -> int`.

```
mnemonic-generate                      # up to --limit cards across all decks
mnemonic-generate --deck gt --limit 5
mnemonic-generate --dry-run            # list targets, zero LLM calls
```

`--limit` defaults to 20. `main()` calls `ensure_champion_versions` first (as `mnemonic-label`
does) so `get_champion` cannot fail on a fresh vault, then builds the client:
`OpenRouterBackend(api_key_env=config.llm.api_key_env, base_url=config.llm.api_base)`.
`--dry-run` prints targets and exits 0 **without constructing a client or spending anything**.

**Budget:** `BudgetGuard.assert_within_budget()` runs **before each card**, not once per run — it
is a pre-flight check with no per-call decrement, so re-checking each iteration is what prevents a
long batch from blowing past the cap mid-run. `LLMBudgetExceededError` stops the run immediately.

**Per-card failures** (`LLMError`, `MalformedNoteError`, `ValueError`, `OptimizationError`) are
caught, recorded as `(card_id, reason)`, and the run continues.

```python
@dataclass(frozen=True)
class GenerationReport:
    generated: list[str]              # variation_ids
    skipped: list[tuple[str, str]]    # (card_id, reason)
    budget_stopped: bool
```

Summary output:
```
generated 18, skipped 2, budget stopped: no

skipped:
  card-3f2a  LLMError: could not parse Q:/A:
  card-91bc  MalformedNoteError: no ## Card
```

**Exit code:** `0` clean; `1` if anything was skipped or the budget stopped the run. This is new
behaviour (existing CLIs only ever return 0) and deliberate — a run that silently half-completed
while spending money should not pass unnoticed.

## Error handling (no silent failures)

| Condition | Behaviour |
|---|---|
| `LLMBudgetExceededError` | stop the run, `budget_stopped=True`, exit 1 |
| `LLMError` / `MalformedNoteError` / `ValueError` / `OptimizationError` on one card | skip, record `(card_id, reason)`, continue, exit 1 |
| `LLMConfigError` (missing API key / bad base url) | propagates — the run cannot proceed at all |
| `--dry-run` | no client constructed, no spend, exit 0 |

## Testing

Stubbing follows the established pattern: a `MagicMock` client whose `generate` returns a real
`Completion`, against the **real** shipped prompts dir. No network in any test.

**Selection (`select_targets`):** excludes cards with a live variation; **includes** cards whose
only variations are invalidated (the regenerate-after-core-change case); excludes suspended cards;
excludes `variation_enabled = false` decks and decks with no config; honors `--deck` and `limit`;
deterministic order.

**Accessors:** `_note_inputs` returns the raw `## Card` section with cloze markers intact
(asserting it differs from `build_faces` output) plus the context section; `_recent_ratings` is
newest-first and capped; `_prior_variations` excludes invalidated rows and shapes `{q, a, rating}`.

**Generator override:** `generate(instruction_text=...)` uses the supplied text and does not read
`strategies/<name>.md`; omitting it falls back to disk (regression cover).

**`generate_for_card`:** end-to-end with a stub client — writes the note entry, creates
`VariationMeta` + `LLMUsage` + `TrainingExample`, records `prompt_version_id = champion.id` and
`arm = "champion"`, and the new variation has **`shown_count == 0`** (the bug fix).

**`run_generate`:** happy path; one card raising `LLMError` is skipped with its reason while the
rest still generate; `LLMBudgetExceededError` stops the run and sets `budget_stopped`;
`--dry-run` makes **zero** client calls; `limit` caps the run.

**CLI:** `main([])` returns 0 on a clean run and 1 when anything was skipped (monkeypatching
`load_config`, as `test_cli_reconcile` does).

**Coverage:** the new service to backend 85%; the generator change keeps `llm/` at its current
level.

## Known limitations (pre-existing, not addressed here)

- `persist_variation` mutates the note file **before** writing DB rows, so a DB failure mid-persist
  can leave an orphan note entry. Not transactional across vault+DB.
- A generation that succeeds at the LLM but fails before `persist_variation` costs real money that
  is never recorded in `LLMUsage` (spend is written by the caller, not the client).
- `get_champion` uses `scalar_one_or_none()`; two champions for one strategy raise
  `MultipleResultsFound`, and no DB constraint prevents that.

## Out of scope (follow-ups)

- A review-time or scheduled generation trigger; an API route for generation.
- Arm randomisation (champion vs challenger A/B): v1 always uses the champion, `arm="champion"`.
- Making the vault+DB write transactional.
- Deleting the dead `db/repositories/review_log.py` and the unused `llm/prompts/variation/system.j2`.
