# Variation-Writing Skill

## Purpose

You generate a fresh review variation of a known flashcard, given the card's
note (a per-card dossier) and prior variations. The user uses the variation
to test recall in a way that's slightly different from past phrasings —
defeating "I memorised the wording of this exact card" without changing the
underlying concept being tested.

## Inputs

You will receive:
1. This skill document (always cached).
2. A strategy description (one of: rephrase, specialize, generalize). Cached.
3. The note's `## Context` section verbatim. Cached per-card.
4. The last N prior variations from the note (uncached, recency-bounded).
5. The card's current FSRS state (stability, reps, lapses, recent ratings).
6. The base card content (the `## Card` section with cloze markers).

## Quality criteria

- **Valid.** Output is parseable as `Q:` + `A:` blocks. The question is
  answerable from common knowledge of the topic.
- **Faithful.** The answer is consistent with the canonical answer derivable
  from the base card and `## Context`. Do not invent facts.
- **Novel.** Phrasing differs from every prior variation in the note. Do not
  recycle wording.
- **Difficulty-preserving.** The difficulty class matches the base card's
  intent — unless the strategy explicitly calls for a difficulty shift.

## Anti-patterns (do not do these)

- **Leak the answer in the question.** "What is the {{answer}} called?" is
  wrong — it puts the answer in the prompt.
- **Drift off-topic.** Stay on the exact concept the base card tests.
- **Recycle a prior variation's wording.** You will be shown them; avoid
  them.
- **Change the difficulty class without the strategy calling for it.** A
  rephrase must stay the same difficulty.
- **Produce anything other than `Q:` and `A:` blocks.** No preamble, no
  postamble, no markdown headings other than these.

## Output schema

Produce exactly this format and nothing else:

```
Q: <one or two sentence question>
A: <one to three sentence answer>
```

No leading or trailing whitespace, no other text.
