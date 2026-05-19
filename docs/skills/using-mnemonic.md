---
name: using-mnemonic
description: Use when an agent needs to read from, write to, or rate cards in a Mnemonic instance without going through the web UI. Covers the HTTP API surface (read + rate) and direct vault filesystem writes (add cards, append variations). Triggers on "add a card to Mnemonic", "what's due today", "rate this card", "list my decks", "fetch card data".
---

# Using Mnemonic from an agent

Mnemonic stores **card content** as Markdown notes inside a Git-backed vault on
disk, and **state** (FSRS scheduling, review log, variation metadata, LLM
usage) in a SQLite sidecar at `<vault>/.mnemonic/state.sqlite`. The HTTP API
is read-mostly. Adding cards = writing files in the vault. Adding variations
= editing those files.

## Discover the environment

Get the vault path and current config (read-only):

```bash
curl -s http://localhost:8000/api/config | jq .
```

The relevant fields: `vault.path`, `vault.branch`, `llm.budget`. If
`http://localhost:8000` is wrong, ask the user for the host/port.

## Read operations (HTTP API)

All routes are mounted under `/api`; no auth.

```bash
# Decks
curl -s http://localhost:8000/api/decks                       # list
curl -s http://localhost:8000/api/decks/{folder_name}         # one

# Cards (joined with FSRS state)
curl -s http://localhost:8000/api/cards                       # all
curl -s "http://localhost:8000/api/cards?deck=game-theory"    # by deck
curl -s http://localhost:8000/api/cards/card-7f3a1234         # one

# Vault Git state
curl -s http://localhost:8000/api/vault/status

# LLM cost telemetry
curl -s http://localhost:8000/api/usage
```

Each card returned includes: `card_id`, `note_path`, `deck_folder`, `syntax`,
`front`, `back`, `title`, `state` (`new|learning|review|relearning`),
`stability`, `difficulty`, `due` (ISO 8601 or null), `reps`, `lapses`,
`leech_score`, `suspended`.

### Get cards due now

```bash
curl -s http://localhost:8000/api/cards | \
  jq '[.[] | select(.due != null and (.due | fromdateiso8601) <= now)]'
```

### Get new cards (never reviewed)

```bash
curl -s http://localhost:8000/api/cards | jq '[.[] | select(.state == "new")]'
```

## Rate a card (HTTP API)

```bash
curl -s -X POST http://localhost:8000/api/reviews/rate \
  -H 'Content-Type: application/json' \
  -d '{
    "card_id": "card-7f3a1234",
    "rating": 3,
    "response_time_ms": 1500
  }'
```

`rating` is 1–4 (1=Again, 2=Hard, 3=Good, 4=Easy). The service updates the
SchedulingState row, appends a ReviewLog entry, recomputes `due`.

If the card showed a variation, include `variation_id` and (after the user
has feedback) `variation_helpful` (0 or 1).

## Write a new card (filesystem)

The API has no `POST /cards`. Cards are notes on disk. **Write a properly
structured file under the vault path.** Mnemonic picks it up on the next
session start (or the next `/api/cards` request).

```bash
VAULT=$(curl -s http://localhost:8000/api/config | jq -r '.vault.path')
DECK_FOLDER="$VAULT/01_Projects/game-theory"
mkdir -p "$DECK_FOLDER"

cat > "$DECK_FOLDER/nash-equilibrium.qmd" <<'EOF'
---
title: Nash equilibrium
tags: [game-theory]
---

## Card

A {{c1::Nash equilibrium}} is a strategy profile in which
{{c1::no player can improve}} by deviating unilaterally.

## Context

Mutual best responses. Nash (1950) proved existence for any finite game.
Compare with: dominant strategy equilibrium, correlated equilibrium.
EOF
```

**Conventions** (the scanner is strict — violations are skipped with a log
entry in `.mnemonic/scan.log`):

1. Frontmatter required, with at least `title`.
2. Section heading exactly `## Card` (case-sensitive). Use one syntax only:
   - Cloze: `{{c1::hidden text}}` (multiple markers reveal together).
   - Highlight: `==hidden text==`.
   - Callout:
     ```
     > [!card]
     > **Q:** Question text
     > **A:** Answer text
     ```
3. `## Context` is free-form; the LLM uses it for variation grounding.
4. `## Variations` is managed by Mnemonic; do not pre-create it for new
   cards. If you need to seed an initial variation, see "Append a variation"
   below.
5. Filename: any `.md` or `.qmd`. The folder name becomes the deck (so
   `01_Projects/game-theory/` → deck `game-theory`).
6. Don't add `^card-xyz` block IDs yourself — Mnemonic injects them on first
   scan and uses them as the stable card identity. If you must pre-set one,
   it must match `^card-[0-9a-f]{8}` exactly.

After writing, the next `GET /api/cards` returns it (and injects a block ID
if missing).

## Override deck defaults (filesystem)

To rename the deck or change variation frequency / leech threshold / daily
limits, add a `_deck.md` in the deck folder:

```bash
cat > "$DECK_FOLDER/_deck.md" <<'EOF'
---
deck_name: Game Theory
variation_enabled: true
variation_frequency: 0.6
leech_threshold: 8
daily_review_limit: 50
daily_new_limit: 10
---

# Game Theory deck (free-form description, ignored)
EOF
```

All six frontmatter keys are required if you create `_deck.md`. Folders
without one inherit from the nearest ancestor `_deck.md`, then global config.

## Append a variation to an existing card (filesystem)

The variation log lives between `<!-- mnemonic:variations:begin -->` and
`<!-- mnemonic:variations:end -->` in the note's `## Variations` section.
Insert new entries immediately before the `:end` marker. Format:

```markdown
### YYYY-MM-DD (rating: pending)
**Q:** Your variation's question
**A:** Your variation's answer
```

`(rating: pending)` becomes `(rating: N)` after the user rates. If
`## Variations` doesn't exist yet, append the whole section to the end of
the note:

```markdown
## Variations

<!-- mnemonic:variations:begin -->
### 2026-05-19 (rating: pending)
**Q:** When is a strategy profile a Nash equilibrium?
**A:** When no unilateral deviation improves any player's payoff.
<!-- mnemonic:variations:end -->
```

Use atomic writes (write to `<note>.tmp`, then `mv`/`rename`) so a partial
write can't corrupt the note.

## Generate a variation programmatically

There is no `POST /api/variations/generate` route. The variation generator
runs internally during review sessions. To generate one yourself, either:

1. **Write your own variation** directly to the note (recommended for
   agents). Follow [writing-card-variations.md](writing-card-variations.md)
   for craft guidance.
2. **Invoke the generator from Python** (heavier; needs the project venv):

   ```python
   from pathlib import Path
   from mnemonic.config import load_config
   from mnemonic.db.sqlite import create_engine
   from mnemonic.llm.backends.anthropic import AnthropicBackend
   from mnemonic.llm.variation.generator import VariationGenerator
   from mnemonic.llm.variation.strategy import select_strategy
   from mnemonic.llm.variation.writer import persist_variation
   from mnemonic.vault.repository import VaultRepository

   cfg = load_config()
   engine = create_engine(cfg.vault.path / ".mnemonic" / "state.sqlite")
   repo = VaultRepository(vault_root=cfg.vault.path, engine=engine)
   card = repo.get_card("card-7f3a1234")
   strategy = select_strategy(
       reps=card.reps,
       lapses=card.lapses,
       recent_ratings=[3, 4],  # supply or fetch from ReviewLog
   )
   gen = VariationGenerator(
       client=AnthropicBackend(),
       prompts_dir=Path(__file__).parents[2] / "backend/src/mnemonic/llm/prompts/variation",
   )
   variation = gen.generate(
       strategy=strategy,
       base_card_text=card.back,
       note_context="(read from note's ## Context section)",
       prior_variations=[],
       fsrs={"stability": card.stability, "reps": card.reps,
             "lapses": card.lapses, "recent_ratings": [3, 4]},
       model=cfg.llm.model_default,
   )
   persist_variation(
       engine=engine, note_path=card.note_path, card_id=card.card_id,
       variation=variation, vault_root=cfg.vault.path,
   )
   ```

## Error handling

The API translates domain exceptions to HTTP status codes:

- `404` — card or deck not found
- `400` — invalid rating (must be 1–4)
- `503` — Git error (dirty tree, vault not configured, push rejected)

LLM-side errors (config missing, rate limit, budget exceeded) surface in the
generator path, not the HTTP API. Check `/api/usage` to see if budget is the
limiter.

## Gotchas

- **Block ID is the stable identity.** Don't rename or delete `^card-xyz`
  markers — you'll orphan the FSRS history.
- **One syntax per note.** Mixing cloze + highlight in the same `## Card`
  raises `InvalidCardSyntaxError` at scan time.
- **Vault is a Git repo.** Each review session commits and pushes. If the
  agent writes a card and the user immediately starts a session, the agent's
  file gets committed with the session's changes. That's fine — just don't
  expect a separate commit.
- **The frontmatter must be a YAML mapping**, not a list or scalar.
- **`## Variations` markers are mandatory.** If you append a `## Variations`
  section without the begin/end comments, the parser will halt on that
  note. Always include both markers.
