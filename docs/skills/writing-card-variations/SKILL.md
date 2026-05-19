---
name: writing-card-variations
description: Use when an agent is asked to write a fresh question/answer variation on an existing Mnemonic card, rephrase a card the user is forgetting, produce a harder version, or produce a more concrete/applied version.
---

# Writing Card Variations

## Overview

You write a **fresh review** of a card the user already knows. The goal is
to defeat memorised wording without changing what's being tested.

For where variations live in the note file, see `using-mnemonic`.

## Map the user's words to a strategy

| User says | Strategy | Difficulty target |
|---|---|---|
| "fresh phrasing", "I memorised the wording", "different wording" | **rephrase** | **identical** to original |
| "concrete", "applied", "worked example", "specific scenario" | **specialize** | same, or slightly easier |
| "harder", "push me", "deeper", "more abstract" | **generalize** | slightly harder — **never more than one step** |

If the user is vague, default to **rephrase**. If `card.lapses >= 3` or
recent ratings average below 2.5 (visible via `GET /api/cards/<id>`),
default to **rephrase** regardless of the user's words.

## Hard constraints (every variation)

1. **Append, never overwrite.** Insert before
   `<!-- mnemonic:variations:end -->`. Existing entries stay.
2. **Stay within the note's `## Context`.** If a concept isn't in the
   note (or the base card itself), you may not use it. Ignore tags,
   ignore deck name, ignore what "a researcher in X probably knows".
   The `## Context` section IS the user's known territory; outside it is
   training-data fabrication.
3. **One question per variation.** No "what is X, and why does Y, and
   how does Z…". A single question with a single answer.
4. **Faithful.** The canonical answer must be derivable from the base
   card plus `## Context`. Don't change which fact is being tested.
5. **Don't leak the answer in the question.** "What is the {answer}
   called?" is wrong.
6. **Difficulty target locked.** Re-read the strategy table. A rephrase
   that adds an abstraction layer is not a rephrase — it's a generalize.
   Pick the strategy and stick to it.

## Output format

Two lines. Append this block inside the `## Variations` markers:

```markdown
### YYYY-MM-DD (rating: pending)
**Q:** <one sentence question>
**A:** <one to three sentence answer>
```

No preamble, no postamble, no extra headings. `(rating: pending)` is
rewritten to `(rating: N)` after the user rates.

## Worked example

Base card (cloze): *"An allocation is {{c1::Pareto efficient}} if
{{c1::no one can be made better off without making someone else worse
off}}."*

`## Context`: *"Mutual best responses do not apply here; this is about
welfare, not equilibrium. Compare with: utilitarian welfare,
egalitarian fairness."*

- **rephrase (good)** — Q: *"Define the criterion an allocation must
  satisfy to count as the standard welfare-economic notion of
  efficiency."* A: *"There is no feasible alternative under which at
  least one agent is strictly better off and no agent is worse off."*
  (Same concept, same fact, different words.)

- **specialize (good)** — Q: *"Alice has 3 apples, Bob has 0 oranges.
  Alice prefers oranges; Bob prefers apples. Is the current allocation
  Pareto efficient?"* A: *"No — both could be made strictly better off
  by trading."* (Concrete instance; same definition applies.)

- **generalize (good)** — Q: *"State Pareto efficiency without reference
  to allocations, using only preferences and feasible outcomes."* A:
  *"A feasible outcome is Pareto efficient iff no other feasible
  outcome is weakly preferred by all agents and strictly preferred by
  at least one."* (One step more abstract; still in the user's
  vocabulary per Context.)

- **❌ generalize that drifted** — Q: *"A Nash equilibrium may fail to
  be Pareto efficient; what is this situation called?"* A: *"A social
  dilemma..."* Wrong: Nash equilibrium is not in `## Context`. You
  brought it in from training data.

## Common Mistakes

- **Overwriting prior variations.** "The user wants a fresh one, so I
  replaced the old one." No — append. Their review history depends on
  the prior entries staying put.
- **Drifting strategies.** Asked to rephrase, produced a generalize.
  Re-read the difficulty-target row before committing.
- **Importing concepts from training.** "The user probably knows X."
  If X isn't in `## Context`, it doesn't exist for this card.
- **Multi-part questions.** "What X, and why Y, and how Z?" Pick one.
- **Recycling wording.** Read the prior variations in `## Variations`
  before writing. Any phrase repeating verbatim across two entries is
  a failure of novelty.

## When to escalate

- The base card has no `## Context` and the concept could mean
  multiple things. Tell the user: "I need a couple of sentences of
  context before I write a variation that won't drift." Do not invent
  context from training.
- The user asked for N variations but the strategy table only justifies
  one per session. Tell them; offer to write one of each strategy
  instead of N near-duplicates of the same strategy.
- The card you're varying doesn't exist (`GET /api/cards/<id>` → 404).
  See `using-mnemonic`.
