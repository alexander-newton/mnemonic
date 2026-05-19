# Mnemonic Backend

FastAPI-based backend for the Mnemonic adaptive spaced repetition system.

Storage is a Git-backed Obsidian/Quarto vault (notes on disk) plus a SQLite
sidecar (`.mnemonic/state.sqlite` inside the vault) for FSRS scheduling state,
review history, variation metadata, and LLM usage. See
[ADR-0001](../docs/source/adr/0001-vault-backed-storage.md) for the rationale
and [`docs/superpowers/specs/2026-05-10-vault-storage-design.md`](../docs/superpowers/specs/2026-05-10-vault-storage-design.md)
for the full design.

## Requirements

- Python 3.11+
- `git` on PATH
- An Anthropic API key (set `ANTHROPIC_API_KEY` in the shell)
- A vault directory (a Git repo containing your card-notes)

## Installation

### 1. Set up the Python environment with uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if not installed
cd backend
uv sync
```

### 2. Configure Mnemonic

Create `~/.config/mnemonic/config.toml`:

```toml
[vault]
path   = "/path/to/your/vault"
remote = "git@github.com:you/your-vault.git"   # optional; used for clone
branch = "main"
watch  = false

[llm]
api_key_env    = "ANTHROPIC_API_KEY"
model_default  = "claude-sonnet-4-6"
model_rephrase = "claude-haiku-4-5"
model_offline  = "claude-opus-4-7"

[llm.budget]
daily_cents   = 25
monthly_cents = 500

[defaults]
variation_enabled   = true
variation_frequency = 0.5
leech_threshold     = 8
daily_review_limit  = 50
daily_new_limit     = 10
```

Per-vault overrides may live in `<vault>/.mnemonic/config.toml` (committed in
the vault, vault-local keys win on merge).

### 3. Initialise the SQLite sidecar

The first `VaultSession.start()` automatically creates `.mnemonic/state.sqlite`
and writes Mnemonic-managed lines into the vault's `.gitignore` and
`.gitattributes`. To populate the schema manually:

```bash
cd backend
uv run alembic upgrade head
```

See [docs/source/developer/migrations.md](../docs/source/developer/migrations.md)
for migration workflow details.

## Running Tests

```bash
uv run pytest                          # full suite
uv run pytest tests/unit               # fast unit tests
uv run pytest tests/integration        # git/scanner integration
uv run pytest tests/e2e                # full session lifecycle smoke
uv run pytest -k test_fsrs             # pattern matching
uv run pytest --cov=mnemonic --cov-report=html
```

## Development Server

```bash
uv run uvicorn mnemonic.main:app --reload
```

Server runs at <http://localhost:8000>.

Auto-generated API docs:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Linting & Type Checking

```bash
uv run black src tests
uv run ruff check src tests
uv run ruff check --fix src tests
uv run mypy src
```

## API Endpoints

Single-user; no authentication. Key routes:

- `GET  /api/decks`               — list decks (folders containing card-notes)
- `GET  /api/decks/{folder_name}` — single deck + config
- `GET  /api/cards[?deck=...]`    — list cards (vault scan + SQLite state)
- `GET  /api/cards/{card_id}`     — single card
- `POST /api/reviews/rate`        — rate a card (FSRS update + ReviewLog)
- `GET  /api/usage`               — LLM cost/cache-hit-rate summary
- `GET  /api/vault/status`        — Git working-tree state of the vault
- `GET  /api/config`              — current effective configuration
- `GET  /health`                  — liveness probe

See Swagger UI for full schemas.

## Architecture pointers

- Vault module: `src/mnemonic/vault/` — scanner, extractors, injector,
  git ops, session lifecycle, repository facade
- LLM module: `src/mnemonic/llm/` — Anthropic SDK client, prompt caching,
  budget guard, variation generator + writer, Jinja2 templates
- DB module: `src/mnemonic/db/` — SQLite engine, ORM models
  (SchedulingState, ReviewLog, VariationMeta, LLMUsage, TrainingExample)
- Core: `src/mnemonic/core/fsrs/` — FSRS-5 scheduler

See [CLAUDE.md](../CLAUDE.md) for the broader project context and the
"NO SILENT FAILURES" principle that all error handling adheres to.
