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
