# Outcome-Driven Prompt Optimization for Card Variations

**Status:** Design approved, pending spec review
**Date:** 2026-06-09
**Author:** Alexander (with Claude)

## Problem

Mnemonic generates LLM-powered variations of flashcards to defeat memorized
wording and deepen learning. Today those variations come from static,
hand-written prompts (Jinja templates + per-strategy markdown). There is no
mechanism to learn *which prompts actually make the user remember better* and to
improve the prompts over time.

`dspy-ai` is already a declared dependency and `TrainingExample` already exists
as an inert model "for DSPy optimisation," but nothing writes to it, reads it, or
imports DSPy.

This design specifies a closed loop that:

1. Collects a behavioral signal for how good each variation is at building
   *durable* memory of the underlying card.
2. Uses that signal as the metric for DSPy prompt optimization (metric-guided
   search over instruction text + few-shot demonstrations — DSPy's analogue of
   "gradient descent in prompt space").
3. Validates candidate prompts against the current best prompt with a real
   champion/challenger experiment before adopting them.

## Conceptual framing

DSPy does **not** do literal gradient descent through continuous prompt space —
there is no gradient through discrete text. Its optimizers (BootstrapFewShot,
MIPROv2, COPRO) perform **metric-guided search**: given
`metric(example, prediction) -> score`, they search over instruction phrasings
and few-shot demonstrations to maximize the mean metric on a trainset. The metric
*is* the loss function. The hard, interesting part of this project is designing a
metric that reflects durable memory rather than in-the-moment ease.

## Architecture: a two-loop system

```
                    ┌─────────────────────────────────────────┐
                    │ champion prompt version (per strategy)    │
                    │  = current markdown instruction (v0 seed) │
                    └───────────────┬───────────────────────────┘
   review time                      │ generates variation, tagged with
   ─────────────                    ▼  (strategy, prompt_version, arm)
   VariationGenerator ──▶ VariationMeta (+prompt_version_id, +arm)
                                     │
   base card's later reviews land    ▼
   ─────────────────────────  Labeling job: FSRS-adjusted, decayed
                              outcome → TrainingExample(reward, maturity)
                                     │
   offline `optimize` (Phase 2)      ▼
   ─────────────────────────  DSPy compile per strategy:
                              metric = maturity-weighted mean reward
                              on held-out labels → CHALLENGER version
                                     │
   field trial (Phase 3)             ▼
   ─────────────────────────  randomize champion vs challenger per card,
                              estimate lift, promote winner ──┐
                                     ▲                         │
                                     └─── new champion ────────┘
```

- **Outer loop (slow, causal):** deploy a challenger prompt against the champion,
  measure the real retention lift on the user's own reviews, promote the winner.
  This is the actual "step in prompt space."
- **Inner loop (fast, surrogate):** DSPy compiles a good challenger *offline*
  against historical outcome labels, so it never has to run a multi-week field
  trial for each of the many candidates it evaluates internally.

The work decomposes into three phases with a strict dependency chain. They are
specified together here but built (plan + implementation) in sequence.

---

## Core data model

Three new pieces of persistent state.

### 1. `prompt_version` (new table — the registry)

| column | type | notes |
|---|---|---|
| `id` | str (PK) | uuid hex |
| `strategy` | str | `rephrase` \| `specialize` \| `generalize` |
| `version_no` | int | monotonic per strategy; v0 = seed |
| `instruction_text` | text | the optimized (or seed) strategy instruction |
| `demos` | JSON | bootstrapped few-shot examples (empty for v0) |
| `status` | str | `champion` \| `challenger` \| `retired` |
| `parent_version_id` | str \| null | provenance (the champion it was compiled from) |
| `compiled_from_n_examples` | int \| null | trainset size at compile time |
| `created_at` | datetime | |

The current on-disk strategy markdown seeds one row per strategy with
`version_no=0, status=champion, demos=[]`. On-disk markdown remains the v0 source
of truth; all later versions live only in this table.

### 2. `TrainingExample` (extend existing model)

Add:

- `prompt_version_id: str` — which prompt produced the variation being labeled.
- `reward: float` — the continuous outcome score (see Phase 1).
- `maturity: int` — how many of the K subsequent reviews have landed.
- `finalized: bool` — true once K reviews landed or the card was retired.

Keep `label: int` as the binary **demo-worthy** flag, derived as
`reward > demo_margin_delta`.

### 3. `experiment` (new table)

| column | type | notes |
|---|---|---|
| `id` | str (PK) | |
| `strategy` | str | |
| `champion_version_id` | str | |
| `challenger_version_id` | str | |
| `status` | str | `running` \| `promoted` \| `rejected` \| `inconclusive` |
| `started_at` | datetime | |
| `decided_at` | datetime \| null | |

### `VariationMeta` (extend existing model)

Add `prompt_version_id: str` and `arm: str` (`champion` \| `challenger` \| `none`)
so every generated variation is traceable to the exact prompt that produced it
and the experiment arm it belonged to.

### Cold-start order

- Phase 1 logging works immediately against champion v0.
- Phase 2 `optimize` refuses to run (loud `InsufficientDataError`) until a strategy
  has `min_examples_to_compile` labeled examples.
- Phase 3 only starts an experiment when a challenger exists.

---

## Phase 1 — Attribution & Labeling

The data layer that makes optimization possible. Deliverable: a growing,
queryable trainset of `(prompt inputs → variation → outcome reward)`. No DSPy yet.

### Mechanics

At review *t* the user is shown a variation and rates it (1–4). The variation's
durable effect on the underlying concept appears in the **subsequent** reviews of
the same base card. We therefore label the variation shown at *t* by the
FSRS-adjusted outcomes of reviews *t+1 … t+K*.

### Reward formula

```
reward(V) = Σ_{k=1..K} wₖ · surprise(t+k)  /  Σ_{k=1..K} wₖ

  surprise(t+k) = success(t+k) − R_pred(t+k)
  success(t+k)  = 1 if rating ≥ 2 (recalled), 0 if rating = 1 (lapse)
  R_pred(t+k)   = FSRS-predicted retrievability at review t+k, from the card's
                  stability and elapsed interval
  wₖ            = γ^(k-1)      (γ = reward_decay_gamma ≈ 0.5)
  K             = reward_window_k ≈ 3
```

`reward` is **calibration surprise**: recalling a card FSRS expected you to fail
scores high; failing one it expected you to pass scores negative. It is centered
near zero so it is comparable across easy and hard cards. The next review (*t+1*,
weight 1) dominates; later reviews add a decayed durability tail.

### Contamination (known approximation)

Review *t+2* is also influenced by the variation shown at *t+1*, so crediting it
to V (shown at *t*) double-counts across overlapping variations. The decay keeps
this honest: the clean, uncontaminated *t+1* term dominates, and each contaminated
later term is down-weighted by the same γ that reflects diminishing confidence.
This is documented as a deliberate approximation. The clean causal read comes from
Phase 3's champion/challenger trial; this reward is only the dense inner-loop
label.

### Progressive (maturing) labels

- After *t+1* lands, write the `TrainingExample` immediately with a partial
  `reward` and `maturity = 1`. Fast availability on a thin data stream.
- The labeling job is an **idempotent upsert** (not append-once): each run
  revisits non-finalized examples and updates `reward` as *t+2*, *t+3* arrive,
  incrementing `maturity` and setting `finalized = true` once K reviews land.
- If the card is suspended/deleted/retired before K reviews, finalize early with
  whatever weight has accrued.

### Edge cases (explicit handling)

- **Card never reviewed again:** stays unlabeled. No fabricated signal — reported
  in job output, never guessed (NO SILENT FAILURES).
- **Suspended/deleted before t+1:** permanently unlabeled, logged.
- **Variation shown multiple times before next review:** attribute to the most
  recent pre-*t+1* variation.
- **Same-day cramming** (interval < `min_interval_hours`): the review is excluded
  from the reward window — same-session recall is not durable memory.

### Labeling job

`mnemonic label` scans `ReviewLog` + `VariationMeta` for variations whose
subsequent reviews have landed, computes/updates reward, and upserts
`TrainingExample`. Idempotent. Runs on demand and/or after review sessions.

---

## Phase 2 — DSPy Compile Pipeline (inner loop)

Deliverable: `mnemonic optimize <strategy>` produces a versioned challenger
prompt, offline and reproducibly.

### DSPy ↔ existing LLM stack integration

A thin adapter (`mnemonic.llm.dspy_lm`) routes DSPy's LM calls through the
existing `LLMClient` / Anthropic backend — same model config, same `LLMUsage`
cost logging, same budget guard. There is no second, untracked path to the LLM.
Invoking DSPy without a configured backend raises a loud `LLMConfigError`.

### Per-strategy modules

Each strategy becomes a `dspy.Signature`:

```
VariationSignature(strategy):
  inputs:  base_card_text, note_context, fsrs_state, prior_variations
  output:  question, answer
```

The signature's instruction is seeded from the current champion's
`instruction_text`. The 3-strategy structure and the rule-based selector
(`strategy.py`) are unchanged.

### Metric

`metric(example, pred, trace) -> float` does **not** call the LLM during search by
default. It returns the **maturity-weighted mean `reward`** over the held-out
`TrainingExample`s for that strategy. The optimizer thereby favors instruction +
demo selections that reproduce the patterns of historically high-reward
variations. The signal stays behavioral, avoiding LLM-grading-LLM circularity. An
optional LLM-judge tie-breaker may be added later.

### Optimizer

- Start with **`BootstrapFewShot`** — selects high-reward historical variations
  (`label = true`, i.e. `reward > demo_margin_delta`) as few-shot demos; stable on
  small data.
- Graduate to **`MIPROv2`** (also rewrites instruction text) once a strategy has
  enough finalized labels.
- `optimizer` is config (`bootstrap` | `mipro`).

### Trainset builder

Pulls finalized (and optionally maturing) `TrainingExample`s for one strategy,
splits train/validation deterministically with a fixed seed (reproducibility — no
nondeterministic drift), and refuses below `min_examples_to_compile` with a loud
`InsufficientDataError` naming how many more examples are needed.

### Output and validity gate

The compile writes a new `prompt_version` row (`status=challenger`,
`parent_version_id` = current champion, `compiled_from_n_examples`, optimized
instruction + demos). Nothing is deployed (that is Phase 3). Each compile is a
reproducible artifact per data snapshot.

Before storing, every challenger must pass a **validity gate**: generate
variations for a few held-out cards and assert they parse (`Q:/A:`), are not
duplicates of the base card, and respect cloze structure. A challenger that cannot
produce well-formed output is rejected at compile time, loudly
(`OptimizationError`).

---

## Phase 3 — Champion/Challenger Experiment & Promotion (outer loop)

Deliverable: the closed loop — promote a challenger only when it demonstrably
builds memory better than the incumbent.

### Randomization

**Per-card, per-epoch.** While an experiment runs for a strategy, each card is
assigned to one arm (champion or challenger) for the epoch's duration, via a
deterministic hash of `(card_id, experiment_id)` (stable, reproducible, ~50/50).
Per-card (not per-review) assignment keeps each card's durable trajectory
attributable to a single prompt, avoiding the contamination that per-review
flipping would introduce into the reward window.

### Measurement

Each arm accumulates the same maturity-weighted `reward` from Phase 1, aggregated
at the **arm level** across its cards. The comparison statistic is
`mean_reward(challenger) − mean_reward(champion)`.

### Promotion gate — Bayesian with a floor

Frequentist significance rarely triggers on a single user's data, so:

- Model each arm's per-card reward; compute the posterior probability that
  challenger exceeds champion by at least margin `m` (`promotion_margin_m`).
- **Promote** when `P(challenger − champion > m) ≥ promotion_probability` (0.95)
  **and** both arms have ≥ `min_cards_per_arm` cards with finalized labels (a hard
  floor — never promote on a few lucky reviews).
- **Reject** symmetrically when `P(champion ≥ challenger) ≥ promotion_probability`.
- **Inconclusive** stop: if neither threshold is hit within `max_epoch_days`, the
  experiment ends inconclusive — challenger retired, champion stays. No forced
  winner.

### State transitions

`experiment.status`: `running → promoted` (challenger becomes `champion`, old
champion `retired`) | `rejected` | `inconclusive`. A promotion is the actual step
in prompt space; the new champion seeds the next Phase 2 compile.

### Safety

- Only **one running experiment per strategy** at a time (`ExperimentStateError`
  on a second start).
- The whole experiment subsystem is behind `experiment_enabled`. With it off, the
  champion is always used and the system degrades to plain Phase 1 logging.

### Decision job

`mnemonic experiment start|evaluate <strategy>` manages the trial. `evaluate`
recomputes posteriors from current labels and applies the gate, loudly reporting
the decision and the numbers behind it.

---

## Error handling (NO SILENT FAILURES)

New exceptions under `MnemonicError`:

- `OptimizationError` — compile / trainset / validity-gate failures.
- `InsufficientDataError` — below a threshold; message names the shortfall.
- `ExperimentStateError` — e.g. starting a second experiment for a strategy.

DSPy LM failures surface as the existing `LLMError` family via the adapter.
Unlabeled variations are never fabricated; they stay unlabeled and are reported in
job output.

## Configuration surface

All in `config.py` / settings, with defaults:

| key | default | meaning |
|---|---|---|
| `optimization_enabled` | false | master switch for Phase 2 |
| `experiment_enabled` | false | master switch for Phase 3 |
| `reward_decay_gamma` | 0.5 | γ in the reward window |
| `reward_window_k` | 3 | K reviews in the reward window |
| `min_interval_hours` | 20 | same-day cramming exclusion |
| `demo_margin_delta` | (tune) | reward threshold for `label = true` |
| `min_examples_to_compile` | (tune) | gate before `optimize` runs |
| `min_cards_per_arm` | (tune) | floor before promotion can fire |
| `promotion_probability` | 0.95 | posterior threshold to promote/reject |
| `promotion_margin_m` | (tune) | minimum meaningful lift |
| `max_epoch_days` | (tune) | inconclusive-stop horizon |
| `optimizer` | `bootstrap` | `bootstrap` \| `mipro` |

## New commands

- `mnemonic label` — run the labeling job (idempotent).
- `mnemonic optimize <strategy>` — compile a challenger (offline, reproducible).
- `mnemonic experiment start|evaluate <strategy>` — manage the field trial.

All idempotent and loud about what they did or why they refused.

## Testing strategy

TDD throughout (CLAUDE.md: backend `core/` 95%).

- **Label math (pure unit):** `reward()` over hand-built review sequences —
  calibration-surprise sign, decay weights, maturity accrual, idempotent upsert,
  edge cases (suspended card, same-day exclusion, multi-show attribution). Highest
  value; pure and deterministic.
- **Trainset builder (unit):** deterministic split given a seed; loud failure
  below `min_examples_to_compile`.
- **DSPy compile (integration, mocked LM):** DSPy adapter calls a fake
  `LLMClient` returning canned variations; assert a challenger `prompt_version` is
  written with provenance and that the validity gate rejects malformed output. No
  network.
- **Experiment/promotion (unit):** deterministic arm hashing; Bayesian gate over
  synthetic arm rewards — promotes only above threshold *and* floor, rejects the
  symmetric case, goes inconclusive on timeout.
- **End-to-end (integration):** seed reviews → label → compile (mocked LM) → run
  experiment → feed synthetic outcomes → assert promotion and that the new
  champion generates subsequent variations. One walk of the whole loop.

## Out of scope (YAGNI for now)

- Learned reward model (premature on a single user's thin data; revisit once data
  is abundant).
- DSPy-optimized strategy *selection* (selector stays rule-based).
- Multi-review attribution windows beyond K, and per-review randomization.
- LLM-judge as a primary metric.
```
