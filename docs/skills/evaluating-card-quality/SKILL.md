---
name: evaluating-card-quality
description: Use when an agent is asked to audit Mnemonic cards, diagnose a struggling/leech card, decide what to suspend or split, or otherwise turn review-history data into actionable recommendations.
---

# Evaluating Card Quality

## Overview

Combine the note on disk with the FSRS state + review log in
`<vault>/.mnemonic/state.sqlite`. Anchor every recommendation to a metric
in the data; never cite "best practice" you can't trace to this file or
the vault.

For finding the vault and using the API, see `using-mnemonic`.

## Data sources

| Need | Source |
|---|---|
| Joined card (content + state) for one or all cards | `GET :8000/api/cards[/<id>]` |
| Per-review history, multi-card aggregates | SQLite `review_log` |
| Per-card scheduling fields | SQLite `scheduling_state` OR API |
| Variation usage / cost | SQLite `variation_meta`, `llm_usage` |
| Note text (`## Card`, `## Context`, prior variations) | Read the file |

Read-only on SQLite. Never write. State changes go through `POST /api/reviews/rate`.

## Metric glossary (precise — do not paraphrase)

- **state** — FSRS state: `new | learning | review | relearning`. Coarse signal.
- **stability** — FSRS-estimated days until retrievability decays to target. Grows with successful reviews.
- **difficulty** — FSRS-estimated card hardness, 1 (easy) to 10 (hard).
- **reps** — total successful or attempted reviews of the card.
- **lapses** — count of reviews with `rating == 1` (Again).
- **leech_score** — cumulative per-card score (higher = more problematic). Increments on lapses; specific formula in `mnemonic.core.leech`.
- **suspended** — boolean; suspended cards never appear in reviews.
- **orphan** — boolean; SQLite row exists but no matching note on disk.

**Common confusion to avoid:** `leech_threshold` (an integer in deck/global
config) is the cap *on lapses* that flags a card to the user. It is **not**
a cap on `leech_score`. They are different fields.

## Recipes

### Single-card diagnosis

```bash
curl -s :8000/api/cards/<card-id> | jq .
# all the FSRS fields are in there, joined with note metadata
```

For review history of one card:

```bash
sqlite3 -header "$DB" "SELECT review_time, rating, response_time_ms,
state_before, state_after FROM review_log
WHERE card_id='<card-id>' ORDER BY review_time;"
```

### Whole-corpus snapshot

```bash
sqlite3 -header -column "$DB" <<'SQL'
SELECT s.card_id, s.state, s.reps, s.lapses,
       ROUND(s.stability, 1) AS stab,
       ROUND(s.leech_score, 1) AS leech,
       ROUND(COALESCE(avg_rating, 0), 2) AS avg_r
  FROM scheduling_state s
  LEFT JOIN (
    SELECT card_id, AVG(rating) AS avg_rating
      FROM (SELECT card_id, rating,
                   ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY review_time DESC) AS rn
              FROM review_log)
     WHERE rn <= 5 GROUP BY card_id
  ) r USING (card_id)
 ORDER BY leech DESC, lapses DESC;
SQL
```

This gives every card joined with its recent-5-review average. Most
audits start here.

## Working thresholds (MUTABLE — edit as the project learns)

> These are **working hypotheses**, not gospel. If your analysis suggests
> a threshold needs tightening or loosening, propose the edit in your
> report and update this section in the same PR. Keep the changelog
> below current.

Each threshold is bound to a specific remediation. Don't apply a threshold
to a different remediation than the one listed (e.g., "recent decline"
does NOT mean suspend — it means watch).

| Category | Condition | Remediation |
|---|---|---|
| **Leech** | `lapses >= 4 AND state == 'relearning'`  *or*  `leech_score >= 3.0` | Split or suspend |
| **Struggling** | `reps >= 3 AND recent-5 avg rating < 2.5 AND not leech` | Attention — add context / rephrase / consider variations |
| **Recent decline** | last 3 ratings monotone non-increasing with at least one drop | Watch — early-warning only; do NOT suspend on this signal alone |
| **Slow recall** | median `response_time_ms` >= 10000 over >= 5 reviews | Consider split — often a multi-part question |
| **Well-mastered** | `reps >= 5 AND lapses == 0 AND recent-5 avg >= 3.5 AND stability >= 10` | None — leave alone |
| **Untested** | `reps == 0` | None — needs reviews first |

### Changelog
- 2026-05-19 — Initial set, calibrated against a 5-card test corpus.
- 2026-05-19 — Bound each threshold to an explicit remediation after a
  verification agent suspended a "recent decline" card based on the
  signal alone.

## Reporting format — match the ask

| User says | Produce |
|---|---|
| "audit my cards", "what's bad", "what's working" | Structured rundown grouped by category (leech / struggling / decline / well-mastered / untested). Card_id + 1-line justification per entry. |
| "is <card> a leech?" / "should I split this?" | One verdict (split / salvage / suspend / keep), with the specific metric values that drove it. |
| "what should I suspend?" | Plain list of card_ids, one reason per. No fluff. |

Always cite metric values, not adjectives. *"5 lapses, leech_score 3.2"*
beats *"failing a lot"*.

## Anti-patterns (the baseline agents hit all of these)

- **Inventing a threshold.** "Stability ≥ 10 means stable." If it's not
  in the Working thresholds above, you made it up. Cite the section or
  propose an edit.
- **Borrowing from Anki / Supermemo / general FSRS lore.** "Anki uses 8
  lapses as the leech default" is irrelevant — Mnemonic has its own
  config and may diverge. Use this file.
- **Confusing `leech_threshold` (config: lapses) with `leech_score` (per-card score).** Re-read the glossary.
- **Recommending content rewrites without being asked.** "Convert this
  callout to cloze" is a style change. Stay in your lane: report the
  data; let the user decide on rewrites unless they explicitly asked.
- **Verbose reports for terse asks.** "Give me what to suspend" wants a
  list, not a 2000-word audit.
- **Using SQL when the API would do.** `GET /api/cards/<id>` returns the
  joined view in one call. Reach for SQL when you need aggregates
  across cards or filters on `review_log` history.
- **Conclusions before 5 reviews.** For any rating-trend or pass-rate
  judgement, require `reps >= 5`. Below that, the signal is noise.

## When to escalate

- A threshold above seems wrong given the data you see. Note it in the
  report AND propose the edit to the Working thresholds section.
- A card has no `review_log` rows but a non-default `scheduling_state`
  row — there's drift; tell the user.
- `orphan == 1` on rows you encounter. Surface them; recommend removal
  or note recovery.
