# Prompt Optimization — Phase 1 (Attribution & Labeling)

Phase 1 records which prompt version produced each variation and scores how well
that variation helped the user remember the underlying card.

## Data model

- `prompt_version` — the registry. One `version_no=0` champion per strategy is
  seeded from the on-disk `llm/prompts/variation/strategies/<name>.md` files.
- `training_example` — extended with `prompt_version_id`, `reward` (nullable),
  `maturity`, and `finalized`. A row is created **unlabeled** when a variation is
  persisted; the labeling job fills in the reward later.
- `variation_meta` — extended with `prompt_version_id` and `arm`.

## Reward

`reward = Σ γ^(k-1) · (success(t+k) − R_pred(t+k)) / Σ γ^(k-1)` over up to
`reward_window_k` subsequent reviews. It is the FSRS *calibration surprise*:
recalling a card the scheduler expected you to fail scores positive. Labels mature
as later reviews arrive and finalize at the window cap or when the card is
suspended. Same-session cramming (gap below `min_interval_hours`) is excluded, and
reviews without a usable `stability_before` are skipped rather than guessed.

## Running the job

```bash
uv run mnemonic-label
```

Seeds champions (idempotent) and prints `labeled=… pending=… finalized_skipped=…`.

## Configuration (`[optimization]`)

| key | default | meaning |
|---|---|---|
| `reward_decay_gamma` | 0.5 | γ decay per later review |
| `reward_window_k` | 3 | max subsequent reviews scored |
| `min_interval_hours` | 20.0 | same-session cramming exclusion |
| `demo_margin_delta` | 0.1 | reward above which `label = 1` (demo-worthy) |

## Phase 2 — DSPy Compile Pipeline

`mnemonic-optimize <strategy>` compiles a **challenger** prompt version from the
reward-labeled `TrainingExample`s of Phase 1.

### LLM path (OpenRouter only)

The compile pipeline uses a native `dspy.LM` pinned to OpenRouter — it never uses
the direct-Anthropic backend. `build_openrouter_lm` requires `OPENROUTER_API_KEY`
(name configurable via `[optimization] openrouter_key_env`) and refuses any model
string that does not start with `openrouter/`. Set `[llm] model_offline` to e.g.
`openrouter/anthropic/claude-3.5-haiku` (pick a real slug from openrouter.ai/models).
Cost is harvested from the LM history into an `LLMUsage` row
(`purpose = "optimize:<strategy>"`): OpenRouter always returns an authoritative
`usage.cost` (USD) per response, preferred over litellm's computed cost. A budget
pre-check runs before compile.

### How it compiles

- Per-strategy `dspy.Signature` (`base_q, base_a, note_context -> question, answer`)
  seeded from the current champion's instruction text. (FSRS state and prior
  variations are runtime-only context, not part of the optimized demos, because
  Phase 1 did not capture them.)
- Trainset = finalized, non-null-reward `TrainingExample`s for the strategy
  (joined to `PromptVersion` for the strategy filter); below
  `min_examples_to_compile` it raises `InsufficientDataError`.
- `BootstrapFewShot` selects demos using `reward_metric`: `0.0` if the prediction
  is invalid (empty Q/A or a verbatim copy of the base), else the gold example's
  reward clamped to non-negative. This gates on validity and weights by durable
  memory built. It is **not** a semantic prediction-vs-gold score — that is a
  deliberate future extension.
- A validity gate runs the compiled program on the held-out split; if fewer than
  `validity_min_pass_rate` of predictions are valid, the challenger is rejected
  (`OptimizationError`) and not stored.
- On success a new `prompt_version` row is written: `status="challenger"`,
  `parent_version_id` = champion, `version_no` = max+1, `instruction_text` +
  serialized `demos`, `compiled_from_n_examples`. Nothing is deployed — Phase 3
  runs the champion/challenger experiment.

### Running

```bash
uv run mnemonic-optimize rephrase
```

### Phase 2 configuration (`[optimization]`)

| key | default | meaning |
|---|---|---|
| `min_examples_to_compile` | 20 | refuse to compile below this many finalized examples |
| `optimizer` | `bootstrap` | optimizer (only `bootstrap` implemented in Phase 2) |
| `max_bootstrapped_demos` | 4 | DSPy bootstrapped demo cap |
| `max_labeled_demos` | 8 | DSPy labeled demo cap |
| `val_fraction` | 0.3 | held-out fraction for the validity gate |
| `split_seed` | 0 | deterministic split seed |
| `validity_min_pass_rate` | 0.8 | min valid fraction on the val split to accept |
| `openrouter_key_env` | `OPENROUTER_API_KEY` | env var holding the OpenRouter key |
| `openrouter_api_base` | `https://openrouter.ai/api/v1` | OpenRouter base URL |
