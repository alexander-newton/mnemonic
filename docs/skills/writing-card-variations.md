---
name: writing-card-variations
description: Use when an agent is tasked with producing fresh question/answer variations on existing Mnemonic cards (defeating memorised wording without changing what's being tested). Lightweight craft guide — strategy selection, quality bar, output format. Triggers on "generate variations for these cards", "rephrase this card", "make harder versions", "make this card more concrete".
---

# Writing Card Variations

You generate fresh review variations of a **known** card. The user has
already learned the underlying concept; your job is to test recall without
recycling the exact wording they've memorised.

## Decide the strategy first

Three strategies. Pick based on the card's FSRS state (visible in the card
JSON returned by `GET /api/cards`):

| When | Strategy | Difficulty |
|---|---|---|
| `lapses >= 3` OR recent ratings average below 2.5 | **rephrase** | Same |
| `reps >= 10` AND recent ratings average ≥ 3.8 | **generalize** | Slightly harder |
| Otherwise | **specialize** | Slightly easier or same |

If you don't have FSRS state, default to **rephrase**.

### rephrase

Re-word the question to test the same concept differently. The user must
arrive at the **same answer**.

- Swap synonyms (define ↔ state ↔ give).
- Active ↔ passive voice; declarative ↔ interrogative.
- Reorder clauses, substitute equivalent notation.
- Don't add prerequisite knowledge; don't change scope; don't hint at the answer.

### specialize

Ask the user to apply the concept to a **concrete instance**. The
underlying definition/theorem stays the same.

- Plug specific numbers into a formula and ask for the result.
- Provide a worked-example setup and ask what the answer is.
- Restate an abstract definition with a concrete object.
- Don't ask for derivations the user hasn't seen; stay within the note's
  `## Context` material.

### generalize

Ask the user to apply the concept at a higher level of abstraction.

- Drop a specifying assumption and ask what survives.
- Lift to a broader object (group → category; ℝ → ℝⁿ).
- Ask for the unifying principle behind the base card's specific case.
- Don't ask for proofs the user hasn't seen; stay within `## Context`.

## Quality bar (every variation)

1. **Valid** — parseable as `Q:` + `A:`; the question is answerable.
2. **Faithful** — the answer is consistent with the canonical answer
   derivable from the base card and the note's `## Context`. Don't invent
   facts.
3. **Novel** — phrasing differs from every prior entry already in the
   note's `## Variations` section. Read them and avoid recycling.
4. **Difficulty-preserving** — matches the strategy's difficulty target;
   never silently shift class.

## Anti-patterns (never do these)

- Putting the answer in the question: *"What is the Nash equilibrium
  called?"* leaks the answer.
- Drifting off-topic: stay on the exact concept the base card tests, not
  related ideas.
- Recycling a prior variation's wording (you'll be shown them — read them).
- Adding new prerequisite knowledge the user hasn't been exposed to.
- Producing anything other than `Q:` + `A:` (no preamble, no explanation,
  no markdown headings beyond what's specified).

## Output format

Two lines, nothing else:

```
Q: <one or two sentence question>
A: <one to three sentence answer>
```

No leading/trailing whitespace. No code fences around the output.

## How to land your variation in the note

The variation belongs in the note's `## Variations` section, between the
managed markers. Append immediately before the `:end` marker:

```markdown
### YYYY-MM-DD (rating: pending)
**Q:** <your question>
**A:** <your answer>
```

If the note has no `## Variations` section yet, create one (see
[using-mnemonic.md](using-mnemonic.md) for the marker format).

`(rating: pending)` will be updated to `(rating: N)` when the user rates
this variation on next review.

## Worked example

Base card:

```
A {{c1::Nash equilibrium}} is a strategy profile in which
{{c1::no player can improve}} by deviating unilaterally.
```

Context excerpt:

```
Mutual best responses. Exists for any finite game (Nash 1950).
Compare with: dominant strategy equilibrium, correlated equilibrium.
```

FSRS state: reps=12, lapses=0, recent_ratings=[4,4,3] → average 3.67 →
strategy = **specialize** (not yet at the generalize threshold).

A good specialize variation:

```
Q: In a 2x2 game where each player chooses between Cooperate and Defect,
   what condition must hold for (Defect, Defect) to be a Nash equilibrium?
A: Neither player can unilaterally switch to Cooperate and increase their
   own payoff — i.e., Defect must be a best response to Defect for both.
```

A bad variation (anti-pattern: leaks the answer):

```
Q: What strategy profile, called a Nash equilibrium, is stable against
   unilateral deviation?
A: A Nash equilibrium.
```

## When you're unsure

- If you don't have the note's `## Context`, request it (or read the file
  from the vault path) before generating.
- If the base card's concept is ambiguous and you can't ground the answer
  in `## Context`, stop and ask the user — don't invent a faithful answer
  from training-knowledge alone.
- One variation per request unless explicitly asked for more. Quality over
  count.
