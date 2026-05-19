---
name: evaluating-card-quality
description: Use when an agent is tasked with auditing the quality of Mnemonic cards — analysing review data, identifying leeches, spotting cards that violate good practice, recommending decomposition or rewrites. Covers SQL/Python data analysis and the (mutable) good-practice checklist this project uses. Triggers on "audit my cards", "which cards aren't working", "find the leeches", "evaluate this card", "what should I fix".
---

# Evaluating Card Quality

Mnemonic gives you two sources of truth for card analysis:

1. **The notes on disk** — every card-note in `<vault>/**/*.{md,qmd}`. The
   note tells you what the card IS.
2. **The SQLite sidecar** at `<vault>/.mnemonic/state.sqlite`. Every review
   and every LLM call leaves a row. The data tells you how the card
   PERFORMS.

Combine them. A card's content is good iff its scheduling data agrees.

## Discover the environment

```bash
VAULT=$(curl -s http://localhost:8000/api/config | jq -r '.vault.path')
DB="$VAULT/.mnemonic/state.sqlite"
```

If the backend isn't running, you can read `~/.config/mnemonic/config.toml`
directly to find `vault.path`.

## Schema summary

| Table | Key rows you'll query |
|---|---|
| `scheduling_state` | `card_id, state, stability, difficulty, due, reps, lapses, leech_score, suspended, orphan` |
| `review_log` | `card_id, rating, response_time_ms, review_time, state_before, state_after` (append-only) |
| `variation_meta` | `card_id, strategy, model, generated_at, shown_count, helpful_count` |
| `llm_usage` | `timestamp, model, purpose, input_tokens, output_tokens, cost_millicents, card_id` |
| `training_example` | labelled (q, a) pairs for offline DSPy use |

Schema and rationale: spec section 5 in
`docs/superpowers/specs/2026-05-10-vault-storage-design.md`.

## SQL recipes

Read-only — never write to `state.sqlite` from an evaluator agent.

```bash
# Top leeches
sqlite3 -header -column "$DB" "
  SELECT card_id, reps, lapses, leech_score, suspended
  FROM scheduling_state
  ORDER BY leech_score DESC
  LIMIT 20;
"

# Cards that have failed 3+ times in the last 30 days
sqlite3 -header -column "$DB" "
  SELECT card_id, COUNT(*) AS recent_fails
  FROM review_log
  WHERE rating = 1 AND review_time >= datetime('now', '-30 days')
  GROUP BY card_id
  HAVING recent_fails >= 3
  ORDER BY recent_fails DESC;
"

# Average rating per card (last 10 reviews each)
sqlite3 -header -column "$DB" "
  WITH ranked AS (
    SELECT card_id, rating,
           ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY review_time DESC) AS rn
    FROM review_log
  )
  SELECT card_id, AVG(rating) AS avg_recent
  FROM ranked
  WHERE rn <= 10
  GROUP BY card_id
  ORDER BY avg_recent ASC
  LIMIT 30;
"

# Cards that take the longest to answer (median response time)
sqlite3 -header -column "$DB" "
  SELECT card_id, COUNT(*) AS reps, AVG(response_time_ms) AS avg_ms
  FROM review_log
  GROUP BY card_id
  HAVING reps >= 5
  ORDER BY avg_ms DESC
  LIMIT 20;
"

# Variation helpfulness per strategy
sqlite3 -header -column "$DB" "
  SELECT strategy, COUNT(*) AS n, SUM(helpful_count) * 1.0 / COUNT(*) AS helpful_rate
  FROM variation_meta
  GROUP BY strategy;
"
```

## Python recipes

For anything beyond a single query — distributions, trends, correlations —
use pandas. Project venv has SQLAlchemy installed; sqlite3 is std-lib.

```python
import sqlite3
import pandas as pd
from pathlib import Path

db = Path("/path/to/vault/.mnemonic/state.sqlite")
con = sqlite3.connect(db)

state    = pd.read_sql("SELECT * FROM scheduling_state", con)
reviews  = pd.read_sql("SELECT * FROM review_log", con, parse_dates=["review_time"])
variants = pd.read_sql("SELECT * FROM variation_meta", con, parse_dates=["generated_at"])
usage    = pd.read_sql("SELECT * FROM llm_usage", con, parse_dates=["timestamp"])
con.close()

# Pass rate per card over the last N reviews
def pass_rate_recent(card_id: str, n: int = 10) -> float:
    r = reviews[reviews.card_id == card_id].sort_values("review_time").tail(n)
    return (r.rating >= 3).mean() if len(r) else float("nan")

# Distribution of average difficulty across all cards
state.difficulty.describe()

# Cards whose state is "review" but whose recent pass rate is below 0.5
weak = state[(state.state == "review")].copy()
weak["recent_pass"] = weak.card_id.map(lambda c: pass_rate_recent(c, 10))
weak = weak[weak.recent_pass < 0.5].sort_values("recent_pass")
weak[["card_id", "reps", "lapses", "leech_score", "recent_pass"]]

# Daily cost trend
usage.set_index("timestamp").resample("D").cost_millicents.sum().tail(30)
```

## Reading the note that backs a card

```python
# The card_id (e.g. card-7f3a1234) is also the Obsidian block-ID inside the
# note. Find the note via the HTTP API or by grepping the vault:
import subprocess
result = subprocess.run(
    ["grep", "-rl", f"^card-7f3a1234", str(vault)],
    capture_output=True, text=True,
)
note_path = result.stdout.strip().splitlines()[0]
note_text = Path(note_path).read_text()
```

Or, simpler:

```bash
curl -s http://localhost:8000/api/cards/card-7f3a1234 | jq -r .note_path
```

The note's `## Context` and `## Variations` sections tell you what the LLM
has been told and how it has been rephrasing.

## Diagnosis ladder

Walk these in order when a card looks broken:

1. Is it suspended? (`state.suspended == 1` — already known bad, skip)
2. Is it an orphan? (`state.orphan == 1` — note was deleted; the row is dead)
3. Is `leech_score` high AND `lapses >= 4`? → leech. Recommend
   decomposition (split into 2+ atomic cards).
4. Is recent pass rate below 0.5 but `leech_score` low? → fresh struggle.
   Recommend rephrase variations, not decomposition.
5. Is `avg_response_time_ms` over ~10 s consistently? → card likely asks
   for too much. Decompose.
6. Does the note's `## Context` exist and have substance? Empty context
   means weak LLM grounding, which often correlates with confusing
   variations. Recommend adding context.

## Good practice (MUTABLE — edit me)

> This section is the **moving target**. Update it as the team learns what
> works. Each principle has a label and a one-line definition; keep it
> short. If a principle becomes obsolete, delete it (don't comment it out).

### Card content

- **Atomic** — one card, one fact. If you have to use the word "and" in
  the answer, you probably have two cards.
- **Minimum information principle** — the smallest possible question that
  still tests the concept. Prefer cloze over front-back when the answer
  fits in the surrounding prose.
- **Self-contained** — the question must be answerable without the user
  having to look up other notes. Pre-requisites go in `## Context`, not
  the card.
- **Stable wording** — once authored, prefer to add variations rather than
  edit `## Card`. Edits can invalidate FSRS history (especially if the
  block-ID got deleted by mistake).
- **No yes/no questions** — they leak too much information and don't
  exercise recall.
- **No questions that lean on the variation history** — each variation
  must be answerable on its own merits.

### Context section

- **Always include `## Context`** for non-trivial cards. The LLM uses it
  verbatim for variation grounding; without it, variations get fuzzier.
- **Cite definitions and sources** when the concept has a canonical source
  (Nash 1950; Chebyshev's inequality; etc.). Helps both the user and the
  LLM.
- **List the comparison neighbours**: "compare with X, Y, Z". This anchors
  the variation generator to specialize/generalize directions.

### Decomposition triggers (when to split a card)

- 4+ lapses with a pass rate below 0.6 → split.
- Answer has more than 3 distinct facts → split.
- Response time consistently above 15 s → split.

### Variation strategy hints

- `rephrase` is the default safety move; abuse it for leeches.
- `specialize` is best when the card is too abstract.
- `generalize` is best when the card is well-mastered AND the user is
  ready to push their understanding.
- Don't run `generalize` on something the user gets wrong half the time.

### Anti-patterns to flag in an audit

- Two notes with overlapping concepts → consolidate into one with
  variations.
- A note with `## Variations` but no `## Context` → weak grounding.
- A note whose `## Card` is more than 4 lines → almost certainly needs
  decomposition.
- A note whose answer (highlight/cloze content) is more than 30 words →
  too much per card.
- Cards generated entirely by LLM with no user-authored `## Context` →
  often drift over time; recommend the user write 3–5 lines of context.

(End of mutable section. Keep this checklist current; treat it as a
working hypothesis, not gospel.)

## Reporting findings

When you audit, return a structured summary so the user can act:

```
SUMMARY
  Cards analysed: 142
  Leeches: 7 (5% — within target)
  Cards with pass rate < 0.5: 18
  Cards with empty ## Context: 23

RECOMMENDATIONS (highest priority first)
  1. Decompose: card-7f3a1234 ("Nash equilibrium full statement")
     reason: 6 lapses, 0.42 pass rate, 4-fact answer
     suggested split: definition; existence theorem; uniqueness conditions
  2. Add context: card-9b21abcd, card-2e44ef01, card-...
     reason: empty ## Context section; variation generator fuzzy
  3. Suspend: card-deadbeef
     reason: 12 lapses, 0.18 pass rate, response time 22s; rewrite from scratch.
```

Cite specific `card_id`s and the metric that triggered each recommendation.
The user trusts evidence-backed claims; vague advice ("some cards look bad")
is unhelpful.

## Don't

- **Don't write to `state.sqlite`.** Evaluators are read-only. State
  changes are the review service's job.
- **Don't rewrite notes silently.** If you recommend a rewrite, surface
  it as a recommendation; the user (or a separate dedicated agent) does the
  edit.
- **Don't claim a card is "bad" with one data point.** Require at least 5
  reviews before drawing conclusions about pass rate or response time.
- **Don't trust this skill's good-practice list blindly.** It is mutable
  precisely because we're still learning. If the data contradicts a
  principle, surface that — and propose an edit to the section above.
