---
name: using-mnemonic
description: Use when an agent is asked to add a card to Mnemonic, list due cards, rate a card, append a variation, or otherwise act on a Mnemonic instance instead of going through its web UI.
---

# Using Mnemonic

## Overview

Cards live as Markdown notes in a Git-backed vault. State (FSRS, reviews, LLM
usage) lives in `<vault>/.mnemonic/state.sqlite`. There is an HTTP API on
`localhost:8000` for reads + rating; new cards and variations are written by
**editing files in the vault**, not via the API.

## Core Pattern: discovery, then act

```
1. curl -s http://localhost:8000/api/config | jq -r .vault.path
       → success ⇒ you have the vault path AND know the backend is up.
2. Otherwise read ~/.config/mnemonic/config.toml for vault.path.
3. Neither works ⇒ STOP. Tell the user: "Mnemonic isn't configured on
   this machine — where is your vault?" Do not create a vault.
```

API is authoritative when the backend is up. Check existence with
`GET /api/cards/<id>` (404 = absent) before grepping disk.

## Quick Reference

| Task | Command |
|---|---|
| List decks | `curl -s :8000/api/decks` |
| List all cards | `curl -s :8000/api/cards` |
| Cards in one deck | `curl -s ":8000/api/cards?deck=<folder>"` |
| One card | `curl -s :8000/api/cards/card-xxxxxxxx` |
| Vault git state | `curl -s :8000/api/vault/status` |
| Rate a card | `curl -X POST :8000/api/reviews/rate -H 'Content-Type: application/json' -d '{"card_id":"card-…","rating":3,"response_time_ms":1500}'` (rating ∈ {1,2,3,4}) |
| Due today | `curl -s :8000/api/cards \| jq '[.[] \| select(.state=="new" or (.due!=null and (.due\|fromdateiso8601)<=now))]'` |

## Adding a new card (filesystem)

No `POST /cards`. Write a note file in the vault. Folder = deck.

```bash
VAULT=$(curl -s :8000/api/config | jq -r .vault.path)
# Folder = deck. Follow the vault's existing structure (e.g. `01_Projects/`
# if it uses PARA; flat top-level folders otherwise). Discover with `curl :8000/api/decks`.
DECK="<existing-deck-folder-or-new-one>"
mkdir -p "$VAULT/$DECK"
cat > "$VAULT/$DECK/<slug>.qmd" <<'EOF'
---
title: <Card title>
tags: [<tag>]
---

## Card

<Prose containing {{c1::the hidden term}}.>

## Context

<Free-form grounding for the LLM variation generator. Strongly recommended.>
EOF
```

Pick **exactly one** card syntax (mixed = parse error):

- **Default: cloze** `{{c1::hidden text}}` — prose with blanks.
- **Highlight** `==hidden text==` — same semantics, lighter visual weight.
- **Callout** `> [!card]` block containing `**Q:** …` and `**A:** …` — when you really want a separate Q/A.

Mnemonic auto-injects `^card-xxxxxxxx` block IDs on first scan. **Don't write your own.**

## Appending a variation (filesystem)

The note's `## Variations` section is delimited by HTML-comment markers.
Insert the new entry immediately before the `:end` marker:

```markdown
### YYYY-MM-DD (rating: pending)
**Q:** Your variation's question
**A:** Your variation's answer
```

If the note has no `## Variations` section yet, append the whole block:

```markdown
## Variations

<!-- mnemonic:variations:begin -->
### YYYY-MM-DD (rating: pending)
**Q:** …
**A:** …
<!-- mnemonic:variations:end -->
```

`(rating: pending)` is rewritten to `(rating: N)` when the user rates it.

## Common Mistakes

- **Inventing a vault.** If neither `:8000/api/config` nor
  `~/.config/mnemonic/config.toml` works, STOP and ask. Never create a
  fresh config + vault to "make the task work" — changes land where the
  user can't see them.
- **Grepping before checking the API.** `GET /api/cards/<id>` returns 404
  in milliseconds.
- **Writing your own block ID.** Mnemonic injects them. **Deleting an
  existing block ID orphans the card's review history** — never edit
  `^card-xxxxxxxx` markers.
- **Mixed syntaxes in one note.** Pick one of cloze / highlight / callout.
- **`## Variations` without markers.** Always include both
  `<!-- mnemonic:variations:begin -->` and `<!-- mnemonic:variations:end -->`.
- **Starting your own backend.** If `curl :8000/health` 200s, it's
  already running.
- **Proceeding with a card the user named that doesn't exist.** When
  `GET /api/cards/<id>` returns 404, tell the user — don't create the
  card silently.
