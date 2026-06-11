# Mnemonic

An adaptive spaced-repetition system with LLM-powered question variations, backed by your own Markdown vault.

## Overview

Mnemonic is a self-hosted, offline-first learning tool. It schedules reviews with the **FSRS** algorithm and uses an LLM (via **OpenRouter**) to generate fresh *variations* of your cards — re-phrasings and related questions that test the same concept differently, so you learn the idea rather than memorising one exact wording.

Your cards live in an **Obsidian/Quarto vault** (an ordinary Git repository). Mnemonic never owns your content: it reads the vault, tracks scheduling state in a small SQLite sidecar, and commits changes back to Git.

A distinctive piece is the **outcome-driven prompt optimizer**: Mnemonic records how well each generated variation actually helped you remember (an FSRS-adjusted reward), then uses **DSPy** to compile better variation prompts from that signal.

**Key features**

- Spaced repetition with the FSRS scheduler
- LLM-generated question variations (rephrase / specialize / generalize) via OpenRouter, with prompt caching
- Outcome-driven prompt optimization (DSPy) that learns from your review history
- Leech detection
- Vault-backed storage — Markdown + Git, with a SQLite sidecar for state
- Markdown, cloze deletions, and math (MathJax) support
- Offline-first PWA frontend (IndexedDB)

> **Status:** Under active development. The vault/review/scheduling core, the OpenRouter backend, and the prompt-optimization pipeline (Phases 1–2) are implemented and tested; some pieces (e.g. wiring variation generation into the live review loop, Phase 3 champion/challenger promotion) are in progress.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11+, SQLAlchemy |
| Python env | **uv** |
| Storage | Obsidian/Quarto vault (Git) + `.mnemonic/state.sqlite` (SQLite) |
| LLM (runtime) | OpenRouter via the `anthropic` SDK (Anthropic-Messages endpoint), with prompt caching |
| LLM (optimization) | DSPy + litellm → OpenRouter |
| Frontend | React 18, TypeScript, Zustand, React Query, IndexedDB (Dexie) |
| Rendering | Pandoc, MathJax |
| Docs | Sphinx |
| Testing | pytest, Vitest, Playwright |

All LLM traffic goes through **OpenRouter** — there is no direct-provider key path.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Git (the vault is a Git repo)
- An **OpenRouter** API key (https://openrouter.ai) exported as `OPENROUTER_API_KEY`

## Quick start

Mnemonic uses your vault (a Git repo) as primary storage; application state lives in `.mnemonic/state.sqlite` inside the vault.

### 1. Create your global config

Create `~/.config/mnemonic/config.toml`:

```toml
[vault]
path   = "/path/to/your/vault"
remote = "git@github.com:you/your-vault.git"
branch = "main"
watch  = false

[llm]
api_key_env   = "OPENROUTER_API_KEY"
# Runtime backend uses bare OpenRouter slugs (anthropic SDK -> /v1/messages).
# Pick real slugs from https://openrouter.ai/models
model_default  = "anthropic/claude-3.5-sonnet"
model_rephrase = "anthropic/claude-3.5-haiku"
# The offline DSPy optimizer uses the litellm "openrouter/"-prefixed form.
model_offline  = "openrouter/anthropic/claude-3.5-haiku"
# api_base defaults to https://openrouter.ai/api; override only if needed.

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

> **Model-slug conventions** (they differ by client library):
> - **Runtime backend** (anthropic SDK): bare slugs, e.g. `anthropic/claude-3.5-haiku`.
> - **DSPy optimizer** (litellm): `openrouter/`-prefixed, e.g. `openrouter/anthropic/claude-3.5-haiku`.

### 2. Set up your environment

```bash
# OpenRouter API key (the only required secret)
export OPENROUTER_API_KEY="sk-or-v1-..."

# Clone (or create) your vault
git clone git@github.com:you/your-vault.git /path/to/your/vault
```

### 3. Run Mnemonic

```bash
# Backend
cd backend
uv sync
uv run uvicorn mnemonic.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- **Frontend:** http://localhost:5173
- **API:** http://localhost:8000 (docs at `/docs`)

### 4. Review

Open the frontend and start a session. Each subfolder of the vault that contains a card-note becomes a deck. A session pulls the vault, scans for cards, lets you review, and commits + pushes the updated state at the end.

See `docs/source/adr/0001-vault-backed-storage.md` for the storage design.

## Prompt optimization

Mnemonic can improve its own variation prompts from your review outcomes. This runs as offline CLI jobs (installed by `uv sync`):

```bash
# Phase 1 — label variations with an FSRS-adjusted "did this build memory" reward
uv run mnemonic-label

# Phase 2 — compile a challenger prompt for a strategy from the labeled data (DSPy)
uv run mnemonic-optimize rephrase      # or: specialize | generalize
```

`mnemonic-label` seeds champion prompts from the on-disk strategy files and computes rewards as later reviews land. `mnemonic-optimize` uses DSPy `BootstrapFewShot` to compile a versioned **challenger** prompt, talking to OpenRouter and recording exact in-band cost. See `docs/source/developer/prompt-optimization.md` and `docs/source/developer/llm-backend.md`.

## Configuration

Config is read from `~/.config/mnemonic/config.toml` (user-global), optionally overlaid by `<vault>/.mnemonic/config.toml` (vault-local wins per key). See **Quick start** for the full template.

- **Required env:** `OPENROUTER_API_KEY` (name configurable via `[llm] api_key_env`).
- `[optimization]` is an optional section with tuning knobs for the reward/compile pipeline (see `docs/source/developer/prompt-optimization.md`).

## Project structure

```
mnemonic/
├── backend/
│   ├── src/mnemonic/
│   │   ├── api/                # FastAPI routes, deps, middleware
│   │   ├── core/               # Business logic (FSRS, optimization) — high coverage
│   │   │   ├── fsrs/           # FSRS scheduler
│   │   │   └── optimization/   # Reward, labeling, DSPy compile, registry
│   │   ├── llm/                # OpenRouter backend, prompts, variation, DSPy LM
│   │   │   └── backends/openrouter.py
│   │   ├── vault/              # Vault scan/parse/inject, Git ops, session
│   │   ├── db/                 # SQLAlchemy models, repositories, SQLite engine
│   │   ├── services/           # Application services
│   │   ├── cli/                # mnemonic-label, mnemonic-optimize
│   │   └── exceptions.py
│   ├── alembic/                # SQLite migrations
│   ├── tests/                  # unit / integration / e2e
│   └── pyproject.toml          # uv dependencies + console scripts
│
├── frontend/                   # React + TypeScript PWA
│   └── src/                    # components, pages, hooks, stores, services
│
├── docs/                       # Sphinx docs (user-guide, developer, adr) + specs/plans
├── infrastructure/             # docker-compose files
├── scripts/                    # setup-dev.sh
├── CLAUDE.md                   # Development guidelines
└── README.md
```

## Development

```bash
# Backend
cd backend
uv sync --extra dev
uv run pytest                         # all tests
uv run pytest --cov=mnemonic          # with coverage
uv run pytest -k test_fsrs            # pattern match
uv run black src tests                # format
uv run ruff check --fix src tests     # lint
uv run mypy src                       # type check

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# Frontend
cd frontend
npm install
npm test                              # unit (Vitest)
npm run test:e2e                      # Playwright
npm run lint:fix && npm run format

# Docs
cd docs && make html
```

This project follows strict guidelines (see [CLAUDE.md](./CLAUDE.md)): **no silent failures**, **TDD**, small functions, full type hints, and coverage thresholds (backend `core/` ≥ 95%).

## License

MIT.

## Support

Open an issue on GitHub. For development conventions, architecture decisions, and the contribution checklist, see [CLAUDE.md](./CLAUDE.md).
