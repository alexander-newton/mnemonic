# Vault-backed storage for Mnemonic

**Status:** Draft for user review
**Date:** 2026-05-10
**Phase:** Phase 1 storage rewrite

## 1. Summary

Replace Mnemonic's PostgreSQL storage with an Obsidian/Quarto vault. Cards live as
per-card-dossier `.md`/`.qmd` files inside the user's vault (initialised from
[`vault-cookiecutter`](https://github.com/alexander-newton/vault-cookiecutter)).
Application state (FSRS scheduling, review history, LLM caches) lives in a
SQLite sidecar inside the vault. The vault is a Git repository: Mnemonic clones
on first run, fast-forward-pulls at session start, and commits + pushes at
session end.

The FastAPI + React stack is retained. Only the storage layer is rewritten and a
new vault module is added. The single-user `User` model and authentication path
are dropped (Mnemonic is single-user self-hosted per `CLAUDE.md`). The dynamic
`CardType` table is replaced with a static enum (`cloze | highlight | callout`).

The LLM layer is built on the official Anthropic SDK behind a thin `LLMClient`
Protocol, with prompt caching, model tiering, and a daily/monthly budget guard
as first-class cost controls.

## 2. Goals and non-goals

**Goals**

- Vault-as-storage: cards are authored as Markdown notes in a vault, not as
  database rows.
- Per-card dossier convention: each note is structured input for the variation
  generator (base card + free-form context + auto-managed variation log).
- Stable card identity across edits via Obsidian-native `^card-xyz` block IDs,
  injected by Mnemonic on first scan.
- Single source of truth for state: SQLite sidecar (`.mnemonic/state.sqlite`)
  inside the vault, committed binary, gitignored WAL/SHM.
- Git lifecycle: clone → pull → review → commit → push, halting loudly on any
  non-fast-forward or dirty working tree.
- Cost-controlled LLM use: prompt caching, Haiku/Sonnet tiering, daily/monthly
  budget cap, batch API for offline jobs.
- Frontend continuity: React PWA shape unchanged except auth flow removal.
- Adherence to Principle #1: no silent failures anywhere.

**Non-goals**

- Multi-user support, OAuth, or any auth (single-user self-hosted).
- Generic Obsidian-plugin compatibility (e.g., `obsidian-spaced-repetition`
  syntax interop). The note convention is Mnemonic-specific.
- Multi-device concurrent sessions. The Git contract is one active device per
  vault at a time.
- Real-time multi-user collaboration, CRDT, or operational-transform.
- Replacing the FastAPI + React stack with a CLI or Obsidian plugin (deferred).

## 3. Architecture

### 3.1 Top-level shape

```
vault/                                  ← user's Git repo (cloned by Mnemonic)
├── .mnemonic/
│   ├── state.sqlite                    ← committed, binary
│   └── config.toml                     ← committed, vault-local config
├── .obsidian/
├── _quarto.yml
├── 01_Projects/
│   └── game-theory/                    ← deck (folder)
│       ├── _deck.md                    ← optional per-deck config
│       ├── nash-equilibrium.qmd        ← one card-dossier
│       └── minimax-thm.qmd             ← one card-dossier
├── 02_Areas/...
├── 03_Resources/...
├── 04_Archive/...
└── .gitignore                          ← .mnemonic/state.sqlite-wal etc.

backend/src/mnemonic/
├── api/                    auth route deleted; rest unchanged
├── services/               adapted to vault.repository
├── core/                   FSRS, leech, variation strategy (unchanged)
├── llm/                    Anthropic SDK + Protocol + prompt cache + budget
├── db/                     SQLite-only; app-state-only
└── vault/                  NEW MODULE
    ├── git_ops.py
    ├── scanner.py
    ├── note.py
    ├── extractors/{cloze,highlight,callout}.py
    ├── injector.py
    ├── deck.py
    ├── watcher.py
    ├── repository.py
    └── session.py
```

### 3.2 Session lifecycle

```
session start
  pre-flight checks:
    - vault_path exists; if missing and vault_remote set, clone
    - working tree is clean (no unstaged or uncommitted changes)
    - git fetch
    - remote is fast-forward-mergeable into local
    if any check fails → raise SessionPreflightError, halt session, surface
                          actionable message to user (per Principle #1)
  vault scan:
    - walk vault, parse notes following canonical structure (§4.1)
    - extract cards, inject ^card-xyz block IDs for any unmarked cards
    - reconcile with SchedulingState rows in SQLite (orphan cards → state
      retained but suspended; deleted notes → SchedulingState marked deleted)

review loop (per card):
    - if variation should be shown (per FSRS state + deck config), call
      llm.variation.generate() → append entry to note's ## Variations section
    - render card; user rates 1–4
    - update SchedulingState row; append ReviewLog row; update VariationMeta if
      a variation was shown
    - update leech score if needed

session end:
    - flush all in-memory writes
    - git add -A
    - git commit -m "mnemonic: review session YYYY-MM-DD (N reviews, M variations)"
    - git push; on transient failure (no network), keep local commit and retry
      next session; on permanent failure (rejected, conflict), halt and surface
```

### 3.3 Data flow

```
Read path:
  vault scan ──► extracted Cards + Decks ──┐
                                           ├──► joined ──► /api/* ──► React PWA
  SQLite (SchedulingState, etc.) ──────────┘

Write path (review):
  rate card ──► SQLite (SchedulingState updated, ReviewLog appended)

Write path (variation generation):
  LLM uses note (full text) as grounding ──► generates variation
       │                                        │
       │                                        ▼
       │                       VariationMeta row in SQLite
       │                                        │
       └────────► append entry to note's ## Variations (atomic write)

Write path (first scan of unmarked card):
  scanner detects unmarked card → injector appends ^card-xyz to note
                                  (atomic write; staged for end-of-session commit)
```

## 4. Vault contract

### 4.1 Canonical note structure

Every card-note must follow this layout. The scanner enforces it; notes that do
not match are skipped with a loud warning logged to `.mnemonic/scan.log` and
surfaced in the API response (no silent skips).

```markdown
---
title: Nash equilibrium
created: 2026-05-10
tags: [game-theory]
---

## Card

A {{c1::Nash equilibrium}} is a strategy profile in which
{{c1::no player can improve}} by deviating unilaterally. ^card-7f3a

## Context

Mutual best responses. Nash (1950) proved existence for any finite game.
Compare with: dominant strategy equilibrium, correlated equilibrium.

## Variations

<!-- mnemonic:variations:begin -->
### 2026-04-12 (rating: 4)
**Q:** When is a strategy profile a Nash equilibrium?
**A:** When no unilateral deviation improves any player's payoff.
<!-- mnemonic:variations:end -->
```

**Section semantics:**

| Section | Authored by | Required | Mnemonic mutates? |
|---|---|---|---|
| Frontmatter | User | Only `title` | No |
| `## Card` | User | Yes | Appends `^card-xyz` once |
| `## Context` | User | No (but recommended) | No |
| `## Variations` | Mnemonic | Auto-created on first variation | Append-only between markers |

A note with no `## Card` section is not a card-note and is skipped silently
(non-card notes are valid in the vault — only the structured ones become cards).

### 4.2 Card-marker syntaxes

Three syntaxes are accepted inside `## Card`. A note must use exactly one syntax;
mixed syntaxes within one note → loud parse error.

**Cloze deletion**

```markdown
A {{c1::Nash equilibrium}} is a strategy profile in which
{{c1::no player can improve}} by deviating unilaterally. ^card-7f3a
```

All clozes in the note (regardless of cloze number) reveal together at review
time. The note is one FSRS-scheduled unit. The cloze number can be used to group
clozes that should reveal together visually but does not split into separate
cards.

**Highlight cloze**

```markdown
A ==Nash equilibrium== is a strategy profile in which
==no player can improve== by deviating unilaterally. ^card-7f3a
```

Equivalent semantics to cloze: every `==text==` is blanked at review time;
revealed together.

**Callout block**

```markdown
> [!card]
> **Q:** Define Nash equilibrium.
> **A:** A strategy profile in which no player can improve by deviating
> unilaterally.

^card-7f3a
```

The callout's first paragraph after `**Q:**` is the question; everything after
`**A:**` is the answer.

### 4.3 Block-ID injection

On first scan, any card-note without a `^card-xyz` block ID inside `## Card`
gets one injected:

1. Read the note; locate the last paragraph of the `## Card` section.
2. Generate an ID: `card-` + 8 hex chars from `secrets.token_hex(4)`.
3. Append ` ^card-xyz` to the end of that last paragraph.
4. Write to `note.qmd.tmp`; `os.replace(tmp, note.qmd)` (atomic).
5. Stage the modification; the session-end commit picks it up.

Block IDs survive content edits as long as the user does not delete them. If a
user deletes a block ID, the next scan injects a new one — the prior
`SchedulingState` row is orphaned (retained but marked `orphan=True`, surfaced in
a "review orphans" UI panel for manual reconciliation).

### 4.4 `## Variations` section management

The section is bounded by HTML comment markers:

```markdown
## Variations

<!-- mnemonic:variations:begin -->
### YYYY-MM-DD (rating: pending|N)
**Q:** ...
**A:** ...
<!-- mnemonic:variations:end -->
```

**Write rules:**

- The injector inserts new entries immediately before the `:end` marker.
- A new entry is written when generated, with `(rating: pending)`.
- After the user rates the card, the injector finds the most recent `pending`
  entry for that card and updates it to `(rating: N)` in place.
- All writes are temp-file + `os.replace`.
- If the markers are missing on a note that has a `## Variations` section, the
  injector refuses to write and raises `MalformedVariationSectionError` with
  remediation text. This is a loud failure: the user has corrupted the
  convention; Mnemonic does not guess.
- If the user edits text inside the markers, those edits are respected (read as
  ground truth). The injector never deletes prior entries.

### 4.5 Deck resolution

A folder is a deck iff it contains at least one card-note. Subfolders nest:
`01_Projects/game-theory/` is a deck named "game-theory" with parent
"01_Projects".

Per-deck config lives in an optional `_deck.md` at the folder root:

```markdown
---
deck_name: Game Theory
variation_enabled: true
variation_frequency: 0.6
leech_threshold: 8
daily_review_limit: 50
daily_new_limit: 10
---

# Game Theory deck

(Free-form description for the human. Not used by Mnemonic.)
```

Inheritance: a folder without `_deck.md` inherits from its parent; the vault root
inherits from `.mnemonic/config.toml` global defaults. Missing fields in any
`_deck.md` cascade up the same chain.

### 4.6 What Mnemonic writes to the vault

Exactly four things, all temp-file + `os.replace` atomic:

1. **`.mnemonic/state.sqlite`** — main commit target each session.
2. **`.mnemonic/config.toml`** — only when settings change in the UI.
3. **Block IDs in `## Card` sections** — once per card on first scan.
4. **Entries in `## Variations` sections** — on each LLM variation + each rating.

Mnemonic never modifies frontmatter, `## Card` content (other than block-ID
append), `## Context`, or any other section.

### 4.7 `.gitignore` and `.gitattributes` Mnemonic manages

`.gitignore`:
```
# managed by mnemonic
.mnemonic/state.sqlite-wal
.mnemonic/state.sqlite-shm
.mnemonic/cache/
.mnemonic/scan.log
.mnemonic/.lock
```

`.gitattributes`:
```
.mnemonic/state.sqlite binary -diff -merge
```

The `-merge` attribute prevents Git from attempting any text-merge on the binary
state file (forces the conflict to surface clearly when it happens).

## 5. SQLite schema

`.mnemonic/state.sqlite` holds only application state. Cards and decks are NOT
stored — they are derived from vault scan and joined at query time.

```sql
CREATE TABLE scheduling_state (
    card_id          TEXT    PRIMARY KEY,    -- "card-7f3a" (block-ID suffix)
    state            TEXT    NOT NULL,       -- new|learning|review|relearning
    stability        REAL    NOT NULL,
    difficulty       REAL    NOT NULL,
    due              TEXT,                   -- ISO 8601, nullable for new
    reps             INTEGER NOT NULL DEFAULT 0,
    lapses           INTEGER NOT NULL DEFAULT 0,
    leech_score      REAL    NOT NULL DEFAULT 0,
    leech_notified   INTEGER NOT NULL DEFAULT 0,
    suspended        INTEGER NOT NULL DEFAULT 0,
    parent_card_id   TEXT,                   -- for card decomposition
    orphan           INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
);
CREATE INDEX idx_scheduling_due       ON scheduling_state (due);
CREATE INDEX idx_scheduling_orphan    ON scheduling_state (orphan);
CREATE INDEX idx_scheduling_suspended ON scheduling_state (suspended);

CREATE TABLE review_log (
    id                   TEXT    PRIMARY KEY,    -- UUID
    card_id              TEXT    NOT NULL,
    rating               INTEGER NOT NULL,        -- 1..4
    response_time_ms     INTEGER NOT NULL,
    review_time          TEXT    NOT NULL,
    state_before         TEXT,
    state_after          TEXT,
    stability_before     REAL,
    stability_after      REAL,
    difficulty_before    REAL,
    difficulty_after     REAL,
    variation_id         TEXT,                    -- nullable; FK to variation_meta
    variation_helpful    INTEGER                  -- nullable; 0/1
);
CREATE INDEX idx_review_card_time ON review_log (card_id, review_time DESC);
CREATE INDEX idx_review_time      ON review_log (review_time);

CREATE TABLE variation_meta (
    id              TEXT    PRIMARY KEY,
    card_id         TEXT    NOT NULL,
    strategy        TEXT    NOT NULL,    -- rephrase|specialize|generalize|compose
    model           TEXT    NOT NULL,
    generated_at    TEXT    NOT NULL,
    shown_count     INTEGER NOT NULL DEFAULT 0,
    helpful_count   INTEGER NOT NULL DEFAULT 0,
    content_hash    TEXT    NOT NULL,    -- SHA-256 of Q+A; for memoization
    note_path       TEXT    NOT NULL     -- relative path; for write-back
);
CREATE INDEX idx_variation_card_hash ON variation_meta (card_id, content_hash);
CREATE INDEX idx_variation_card_time ON variation_meta (card_id, generated_at DESC);

CREATE TABLE llm_usage (
    id                       TEXT    PRIMARY KEY,
    timestamp                TEXT    NOT NULL,
    model                    TEXT    NOT NULL,
    purpose                  TEXT    NOT NULL,    -- "variation:rephrase", etc.
    input_tokens             INTEGER NOT NULL,
    output_tokens            INTEGER NOT NULL,
    cache_read_tokens        INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens    INTEGER NOT NULL DEFAULT 0,
    cost_millicents          INTEGER NOT NULL,
    card_id                  TEXT
);
CREATE INDEX idx_usage_timestamp ON llm_usage (timestamp);
CREATE INDEX idx_usage_card      ON llm_usage (card_id);

CREATE TABLE training_example (
    id              TEXT    PRIMARY KEY,
    card_id         TEXT    NOT NULL,
    variation_id    TEXT,
    base_q          TEXT    NOT NULL,
    base_a          TEXT    NOT NULL,
    variation_q     TEXT    NOT NULL,
    variation_a     TEXT    NOT NULL,
    label           INTEGER NOT NULL,    -- 0=bad, 1=good (from variation_helpful)
    rating          INTEGER,
    note_context    TEXT,                -- snapshot of ## Context at gen time
    created_at      TEXT    NOT NULL
);
CREATE INDEX idx_training_label ON training_example (label);

-- Schema version tracking
CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
INSERT INTO schema_version VALUES (1, datetime('now'));
```

**Migrations** are managed by Alembic, retargeted to SQLite. The existing
PostgreSQL Alembic migrations are deleted; the new schema starts at revision
`0001_initial_sqlite_schema.py`.

**Why no `card`/`deck`/`card_type`/`user` tables:** content is derived from the
vault scan; user is single (configured in `config.toml`); card type is inferred
from the syntax in `## Card`. Persisting these would risk drift from the vault.

## 6. LLM API client

Per Section 4 of the brainstorming conversation, locked in: Anthropic SDK direct
behind a `LLMClient` Protocol.

### 6.1 Module layout

```
backend/src/mnemonic/llm/
├── client.py          LLMClient Protocol; Block, Message, Completion dataclasses
├── backends/
│   └── anthropic.py   AnthropicBackend (wraps `anthropic` SDK)
├── cache.py           build cache_control on system blocks
├── budget.py          daily/monthly cost guard
├── router.py          model-tier picker
├── batch.py           batch-API submitter for offline jobs
├── exceptions.py      LLMError hierarchy
├── prompts/
│   └── variation/
│       ├── SKILL.md
│       ├── system.j2
│       ├── user.j2
│       └── strategies/{rephrase,specialize,generalize}.md
│           # compose.md added in Phase 2 (deferred per §7.3)
├── variation/
│   ├── generator.py
│   ├── strategy.py
│   └── writer.py
└── dspy/
    └── variation_optimizer.py
```

### 6.2 Prompt-caching strategy

System blocks (in order), each with `cache_control={"type": "ephemeral"}`:

1. `SKILL.md` verbatim — 1-hour TTL (rarely changes).
2. Strategy template (one of `rephrase|specialize|generalize|compose`) —
   1-hour TTL.
3. Note's `## Context` section verbatim — 5-minute TTL (per-card, hot only
   during a session).

User message blocks (NOT cached): last N variations from the note (truncated by
token budget), FSRS state summary (recent ratings + stability + reps + lapses),
base card markup with the explicit instruction to produce a fresh variation.

Cache hit-rate target: ≥ 80% on input tokens for a typical session of 35
variations. Telemetry surfaces this in the UI cost panel.

### 6.3 Model tiering

`router.pick_model(strategy, fsrs_state) → str`:

| Condition | Model |
|---|---|
| Strategy = `rephrase`, no recent struggles | `claude-haiku-4-5` |
| Strategy ∈ {`specialize`, `generalize`} (and `compose` once added in Phase 2) | `claude-sonnet-4-6` |
| Recent failures > 3 (regardless of strategy) | `claude-sonnet-4-6` |
| Offline DSPy / quality eval | `claude-opus-4-7` |

Overrides via `[llm]` table in `~/.config/mnemonic/config.toml`.

### 6.4 Budget guard

Reads `LLMUsage` for today and this month, sums `cost_millicents`. Caps in
`config.toml`:

```toml
[llm.budget]
daily_cents   = 25
monthly_cents = 500
```

Before each `generate()` call, the guard checks. Over budget → raises
`LLMBudgetExceededError(current_spend_cents, cap_cents, "Set [llm.budget] in
config.toml to raise the limit.")`. The session continues without variations
(card is shown in its base form); the UI surfaces a banner.

### 6.5 Batch API

`client.submit_batch(requests, model=...)` is used exclusively by:

- `scripts/optimize_variation_prompt.py` (offline DSPy)
- `scripts/eval_variation_quality.py` (nightly CI quality run)
- (Phase 2) Nightly pre-generation of variations for tomorrow's due cards

The hot path (review session) never uses batch.

### 6.6 Error handling per Principle #1

`AnthropicBackend` translates SDK exceptions into Mnemonic's hierarchy:

```python
except anthropic.AuthenticationError as e:
    raise LLMConfigError(
        "Anthropic API authentication failed. Set ANTHROPIC_API_KEY in "
        "~/.config/mnemonic/config.toml. Details: " + str(e)
    ) from e
except anthropic.RateLimitError as e:
    retry_after = int(e.response.headers.get("retry-after", 30))
    raise LLMRateLimitError(
        f"Anthropic rate limit exceeded. Retry in {retry_after}s, or reduce "
        f"variation_frequency in deck config.",
        retry_after=retry_after,
    ) from e
except anthropic.APIStatusError as e:
    raise LLMError(
        f"Anthropic API returned {e.status_code} for model {model}: "
        f"{e.message}"
    ) from e
```

No silent fallback to a default response, no swallowed exception.

## 7. Variation-writing skill

### 7.1 SKILL.md

Lives at `llm/prompts/variation/SKILL.md`. Loaded verbatim into the system
prompt (cached). Contents:

- **Purpose** — generate a fresh review of a known card given the note's
  context and prior variations.
- **Inputs** — what the LLM receives, in what order.
- **Strategy table** — which strategy applies when (rule the LLM can also
  reason about).
- **Quality criteria** — validity (parseable Q/A; question is answerable),
  faithfulness (answer matches canonical), novelty (different from prior
  variations), difficulty preservation (same class as base).
- **Anti-patterns** — concrete examples of bad variations with one-line "why
  this is wrong" annotations.
- **Output schema** — strict `Q:` / `A:` blocks; nothing else. Non-conforming
  output is a loud failure.

### 7.2 Evaluation harness

```
backend/tests/llm/
├── golden/
│   ├── nash-equilibrium.qmd
│   ├── chebyshev-inequality.qmd
│   ├── derivative-product-rule.qmd
│   └── ...                         ~20 cards across math/econ topics
├── judges/
│   ├── valid.py
│   ├── faithful.py
│   ├── novel.py
│   └── difficulty.py
└── test_variation_quality.py
```

Marked `pytest -m llm_eval` and excluded from the default suite. Runs in a
nightly CI job and on demand.

The default suite tests **plumbing only** — strategy selection, prompt
rendering, write-back to the note, cache-block construction, budget guard,
exception translation — using mocked `LLMClient`.

### 7.3 Phase 1 scope

- Directory layout, `SKILL.md` skeleton, three strategy files (`rephrase`,
  `specialize`, `generalize`).
- Working `generator.py` + `writer.py` integrated with the vault module.
- Plumbing tests with mocked `LLMClient` (≥ 95% coverage on `core/variation/`
  and `llm/variation/` per `CLAUDE.md` coverage requirements).
- One golden card + one judge (`valid.py`) as a smoke test.
- DSPy optimization, full golden set, all four judges, and `compose` strategy
  deferred to a follow-on iteration.

## 8. Sync, write-back, and file watching

### 8.1 Git operations

`vault/git_ops.py` shells to `git` via `subprocess.run` (not GitPython —
avoids pinning a heavyweight dep, and `git` is required on the host anyway).
All commands run with `cwd=vault_path`.

```python
def fetch() -> None: ...
def is_fast_forward_to(remote: str = "origin/main") -> bool: ...
def fast_forward_pull(remote: str = "origin/main") -> None: ...
def working_tree_clean() -> bool: ...
def commit_all(message: str) -> str: ...        # returns commit SHA
def push(remote: str = "origin", branch: str = "main") -> None: ...
def has_unpushed_commits() -> bool: ...
```

Every function raises a domain-specific exception on failure (e.g.,
`GitNonFastForwardError`, `GitDirtyWorkingTreeError`, `GitPushRejectedError`)
with the actionable message.

### 8.2 Pre-flight checks

Run at the start of every session, in order. Any failure halts and surfaces:

1. `vault_path` exists. If missing and `vault_remote` is set →
   `git clone vault_remote vault_path`. Otherwise raise `VaultNotConfiguredError`.
2. `working_tree_clean()` true → else `GitDirtyWorkingTreeError` with message
   advising the user to commit or stash via Obsidian or CLI.
3. `git fetch`. If network failure → log a warning, set `offline=True`, and
   skip steps 4–5 (offline session ok). Reconciliation happens at the next
   session that has network.
4. `is_fast_forward_to("origin/main")` true → else `GitNonFastForwardError`
   listing diverged commits.
5. `fast_forward_pull()`.

### 8.3 Session-end commit and push

After review loop completes (or on early termination — including errors):

1. Write any pending atomic file ops.
2. Close SQLite (commits WAL).
3. `git add -A`.
4. `git commit -m "mnemonic: review session YYYY-MM-DD (N reviews, M variations)"`.
   Skip if no changes to commit.
5. `git push` with up to 3 retries on transient errors (network).
6. On permanent push rejection (e.g., concurrent push from another device):
   `GitPushRejectedError`, halt, surface — local commit retained for
   reconciliation on next session.

### 8.4 Atomic file writes

All vault writes use the same pattern:

```python
def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
```

Plus a vault-wide lock file `.mnemonic/.lock` (gitignored) acquired at session
start, released at session end. Prevents concurrent Mnemonic processes on the
same vault on the same machine.

### 8.5 File watcher (optional)

`vault/watcher.py` uses the `watchdog` library to watch the vault for changes
during an active session. Purpose: if the user edits a note in Obsidian
mid-session, the in-memory card index is updated so the next review uses the
fresh content.

- Only active during a session (started after pre-flight, stopped before
  commit).
- Debounces by 500ms per file to avoid thrashing on rapid saves.
- On detected change: re-parse the file; update the in-memory `Card` object.
- The watcher does NOT inject block IDs. Block-ID injection happens only at
  session-start scan; new card-notes that appear during a session are picked
  up at the next session start. This avoids racing with the user's editor
  saving the same file.
- On detected delete or move of a card-note: mark the corresponding
  `SchedulingState` row `orphan=True`.
- The watcher is opt-in via `[vault] watch = true` in `config.toml`. Default
  off — start-of-session scan is sufficient for most workflows.

## 9. Frontend impact

### 9.1 Deletions

```
frontend/src/
├── pages/LoginPage.tsx        DELETE
├── pages/RegisterPage.tsx     DELETE
├── components/ProtectedRoute.tsx  DELETE
├── hooks/useAuth.ts           DELETE
├── stores/authStore.ts        DELETE
└── services/api.ts            REMOVE auth-related calls + JWT interceptor
```

App routes simplify to `/decks`, `/decks/:slug`, `/review/:cardId`,
`/settings`, `/usage`. No login wall.

### 9.2 Additions

- **Vault status panel** (in `AppLayout`): current commit SHA (short), last
  pull/push timestamp, working-tree clean indicator, "configure vault" link if
  `vault_path` is unset.
- **Cost panel** (`/usage`): today's cost, this month's cost, cache hit rate,
  per-strategy breakdown. Graphs optional.
- **Settings** (`/settings`): vault path + remote, default LLM models per
  strategy, budget caps. Writes to `~/.config/mnemonic/config.toml` via a
  `/api/config` PUT endpoint.

### 9.3 Adapted

- Deck list and deck detail pages: shape unchanged; backed by
  `/api/decks` returning vault-derived decks.
- Card render path: unchanged; `Card` shape preserved.
- Review session page: adds a session-start banner if pre-flight finds
  unpushed commits or new remote commits, so the user knows what's about to
  happen.

## 10. Backend module changes summary

### 10.1 Deleted

```
backend/src/mnemonic/db/models/user.py
backend/src/mnemonic/db/models/card.py
backend/src/mnemonic/db/models/deck.py
backend/src/mnemonic/db/models/card_type.py
backend/src/mnemonic/db/models/variation_cache.py   (replaced by variation_meta)
backend/src/mnemonic/db/repositories/user.py
backend/src/mnemonic/db/repositories/deck.py
backend/src/mnemonic/db/repositories/card.py
backend/src/mnemonic/services/auth.py
backend/src/mnemonic/api/routes/auth.py
backend/alembic/versions/0001_initial_schema_with_all_models.py
backend/alembic/versions/0002_seed_builtin_card_types.py
```

### 10.2 Rewritten

```
backend/src/mnemonic/db/models/review_log.py        SQLite-targeted
backend/src/mnemonic/db/models/training_example.py  SQLite-targeted
backend/src/mnemonic/db/models/llm_usage.py         SQLite-targeted
backend/src/mnemonic/services/deck.py               vault.repository-backed
backend/src/mnemonic/services/card.py               vault.repository-backed
backend/src/mnemonic/api/routes/decks.py            no auth dep
backend/src/mnemonic/api/routes/cards.py            no auth dep
backend/src/mnemonic/api/deps.py                    drop user dep
backend/src/mnemonic/main.py                        drop auth middleware
backend/src/mnemonic/config.py                      load from config.toml
```

### 10.3 New

```
backend/src/mnemonic/db/models/scheduling_state.py
backend/src/mnemonic/db/models/variation_meta.py
backend/alembic/versions/0001_initial_sqlite_schema.py
backend/src/mnemonic/vault/                         (full new module)
backend/src/mnemonic/llm/backends/anthropic.py
backend/src/mnemonic/llm/cache.py
backend/src/mnemonic/llm/budget.py
backend/src/mnemonic/llm/router.py
backend/src/mnemonic/llm/batch.py
backend/src/mnemonic/llm/prompts/variation/         (skill + templates)
backend/src/mnemonic/api/routes/config.py           settings UI backend
backend/src/mnemonic/api/routes/usage.py            cost panel backend
backend/src/mnemonic/api/routes/vault.py            status panel backend
```

## 11. Testing strategy

Per `CLAUDE.md`: backend ≥ 85% overall, ≥ 95% on `core/`. Frontend ≥ 75%.

### 11.1 Unit tests

- Each extractor (`cloze`, `highlight`, `callout`) on positive and malformed
  inputs.
- Note parser (canonical sections, missing sections, mixed syntaxes).
- Block-ID injector (atomic write, idempotency, marker integrity).
- Variation-section writer (insert, mark pending → resolved, missing markers
  → loud error).
- Deck resolver (folder → deck, `_deck.md` parsing, inheritance cascade).
- FSRS algorithm (unchanged from current; tests retained).
- LLM `cache.py` (cache-block construction; correct breakpoint count).
- LLM `budget.py` (under-budget pass, over-budget raise, edge: exactly at cap).
- LLM `router.pick_model` (each branch).
- LLM `AnthropicBackend` with mocked SDK (success path, each error type).

### 11.2 Integration tests

- Vault scanner end-to-end on a fixture vault (10–15 sample notes covering
  every syntax + edge cases).
- Git ops on a temp repo: clone, fetch, fast-forward pull, dirty-tree refusal,
  commit + push to a local bare-repo remote.
- Session lifecycle: pre-flight → scan → simulated review (mocked LLM) →
  commit → push, asserting the resulting commit contains expected files.
- SQLite migration round-trip via Alembic.

### 11.3 E2E tests

- Playwright walkthrough: launch backend pointed at a fixture vault, render
  deck list, start review, submit ratings, verify Git commit + state file
  changes.
- Critical paths covered (per `CLAUDE.md`): deck list, card review, settings
  edit, vault status banner.

### 11.4 LLM evaluation (gated)

- `pytest -m llm_eval` runs golden-set quality tests. One-card smoke test in
  Phase 1; full set later.

### 11.5 Coverage gates

CI fails if:
- `backend/src/mnemonic/core/` < 95%
- `backend/src/mnemonic/vault/` < 90%   (new — high coverage required since
  this is the storage layer)
- `backend/src/mnemonic/llm/` < 85%     (new — excludes prompts/ markdown)
- backend overall < 85%
- frontend overall < 75%

## 12. Configuration

`~/.config/mnemonic/config.toml` (user-global; created on first run):

```toml
[vault]
path   = "/path/to/your/vault"
remote = "git@github.com:you/vault.git"
branch = "main"
watch  = false

[llm]
api_key_env       = "ANTHROPIC_API_KEY"   # name of env var holding the key
model_rephrase    = "claude-haiku-4-5"
model_default     = "claude-sonnet-4-6"
model_offline     = "claude-opus-4-7"

[llm.budget]
daily_cents   = 25
monthly_cents = 500

[defaults]
variation_enabled    = true
variation_frequency  = 0.5
leech_threshold      = 8
daily_review_limit   = 50
daily_new_limit      = 10
```

Vault-local `vault/.mnemonic/config.toml` (committed; overrides specific keys
for this vault):

```toml
[defaults]
variation_frequency = 0.6
```

The vault-local file wins for any key it specifies.

## 13. Migration from current state

Phase 1 has minimal real data per `CLAUDE.md` ("local database, server, and
basic web app working"). Treated as a clean cutover:

1. Drop the existing PostgreSQL schema (no longer used after this rewrite).
2. Delete the old Alembic migrations.
3. Stand up the new SQLite schema via `0001_initial_sqlite_schema.py`.
4. Provide a one-shot script `scripts/migrate_pg_to_vault.py` for the user's
   own benefit if any data is worth carrying forward (reads the user's running
   PostgreSQL instance, renders each `Card` row as a canonical note in the new
   vault, populates `SchedulingState` from FSRS columns). Optional, not on the
   critical path.

`docker-compose.dev.yml` drops the `postgres` service. `redis` is retained for
session/state caching if needed by the API layer; otherwise droppable.

## 14. Open risks and mitigations

| Risk | Mitigation |
|---|---|
| Binary `state.sqlite` merge conflicts | `.gitattributes` `-merge`; halt-and-surface on non-FF pull; documented "one active device per vault" rule |
| Repo bloat from binary state | Accepted (~18MB/year); git-lfs is opt-in escape hatch if it becomes painful |
| User edits inside `## Variations` markers | Respected as ground truth; injector never overwrites prior entries |
| User deletes a `^card-xyz` block ID | New ID injected on next scan; old `SchedulingState` marked `orphan=True`; reconciliation UI surfaces it |
| LLM cost overrun | `budget.py` halts before request; daily/monthly caps in config; cost panel in UI |
| LLM rate limits | Translated to `LLMRateLimitError` with retry-after; session continues without variations |
| Concurrent Mnemonic processes | `.mnemonic/.lock` file; second process refuses to start |
| Note convention violations | Loud parse error per Principle #1; never silent skip |
| Vault not configured | Pre-flight raises `VaultNotConfiguredError` with first-run guidance |

## 15. Out of scope (for follow-on specs)

- Image cloze syntax. The legacy `CardType` table supported it; the new
  static enum (`cloze | highlight | callout`) does not. A future spec can add
  an `image_cloze` syntax + extractor when image-card workflows are
  prioritised.
- Anki-style "different cloze numbers = separate cards" semantic. Current
  convention: one note = one card.
- Bulk pre-generation of variations for tomorrow's due queue (Phase 2).
- DSPy-driven prompt optimization productionisation (offline scripts only in
  Phase 1).
- Android app or Obsidian plugin frontends (per `CLAUDE.md` future-phase).
- Multi-vault support (one configured vault path at a time).
- Cloud-hosted variant.

## 16. Acceptance criteria

The rewrite is complete when:

1. A user can run `mnemonic init`, supply a Git remote, and Mnemonic clones the
   vault, creates `.mnemonic/state.sqlite`, and starts a review session.
2. Authoring a note with the canonical structure and saving it (in Obsidian
   or any editor) results in the card being available for review on the next
   session start.
3. After review, `git log --oneline -1` in the vault shows
   `mnemonic: review session YYYY-MM-DD (N reviews, M variations)`.
4. After 50 review sessions, the vault repo size growth is dominated by
   binary SQLite churn (≤ 100KB/session typical).
5. Cache hit rate on LLM input tokens (visible in `/usage`) is ≥ 80% across a
   typical 35-variation session.
6. Triggering a budget overrun shows a UI banner and continues the session
   without variations; ratings still apply.
7. Editing a note while a session is running (with `watch = true`) reflects
   in subsequent cards in the queue.
8. Coverage gates pass: `core/` ≥ 95%, `vault/` ≥ 90%, `llm/` ≥ 85%, backend
   ≥ 85%, frontend ≥ 75%.
9. No silent failure paths exist in any added module (review against
   Principle #1).
