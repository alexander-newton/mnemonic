# Mnemonic

An adaptive spaced repetition system with LLM-powered question variations.

## Overview

Mnemonic is a self-hosted, offline-first PWA designed for efficient learning. It combines the FSRS (Free Spaced Repetition Scheduler) algorithm with OpenRouter's LLM capabilities to automatically generate question variations, helping you learn smarter.

**Key Features:**
- Spaced repetition using FSRS algorithm
- LLM-powered question variation generation
- Leech detection and card decomposition
- Offline-first PWA with IndexedDB
- Support for Markdown, cloze deletions, and math notation
- DSPy-optimized prompts for better LLM usage

**Tech Stack:**
- **Backend:** FastAPI, Python 3.11+, SQLite sidecar
- **Frontend:** React 18, TypeScript, Zustand, React Query
- **Storage:** Obsidian/Quarto vault (Git repo), `.mnemonic/state.sqlite`
- **LLM:** Anthropic SDK with prompt caching (configurable model)
- **Package Manager:** uv (Python), npm (Node)

## Prerequisites

- Python 3.11+
- Node.js 20+
- Git (for vault initialization and syncing)
- An Anthropic API key (`ANTHROPIC_API_KEY` environment variable)

## Quick Start

Mnemonic uses your Obsidian/Quarto vault (a Git repo) as primary storage.
Application state lives in a SQLite sidecar (`.mnemonic/state.sqlite`) inside the vault.

### 1. Create your global config

Create `~/.config/mnemonic/config.toml`:

```toml
[vault]
path   = "/path/to/your/vault"
remote = "git@github.com:you/your-vault.git"
branch = "main"
watch  = false

[llm]
api_key_env       = "ANTHROPIC_API_KEY"
model_default     = "claude-sonnet-4-6"
model_rephrase    = "claude-haiku-4-5"
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

### 2. Set up your environment

```bash
# Export your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Initialize or clone your vault
# If new: use vault-cookiecutter or a blank git repo
# If existing: git clone your vault
git clone git@github.com:you/your-vault.git ~/path/to/vault
```

### 3. Run Mnemonic

```bash
# Backend
cd backend
uv sync
uv run uvicorn mnemonic.main:app --reload

# In a new terminal, run frontend
cd frontend
npm install
npm run dev
```

Services will be available at:
- **Frontend:** http://localhost:5173
- **API:** http://localhost:8000

### 4. Start reviewing

1. Open the frontend
2. View your decks (each subfolder of the vault that contains a card-note becomes a deck)
3. Start reviewing

Each review session pulls the vault, scans for cards, lets you review, commits + pushes back at the end.

**See `docs/source/adr/0001-vault-backed-storage.md` for the full design.**

## Local Development Setup

### Backend Setup

```bash
cd backend

# Create virtual environment (using uv)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Run tests
uv run pytest

# Start development server
uv run uvicorn mnemonic.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Run E2E tests
npm run test:e2e
```

### Documentation Setup

```bash
cd docs

# Build HTML documentation
make html

# Live rebuild on changes
make livehtml

# Check for broken links
make linkcheck
```

## Configuration

Mnemonic reads configuration from `~/.config/mnemonic/config.toml`. See **Quick Start** above for the full template.

**Required environment variables:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key

**Optional:**
- `MNEMONIC_CONFIG_PATH` - Override default config location (default: `~/.config/mnemonic/config.toml`)

## Project Structure

```
mnemonic/
├── backend/                    # FastAPI backend
│   ├── src/mnemonic/
│   │   ├── api/               # HTTP routes and middleware
│   │   ├── core/              # Business logic (95% test coverage)
│   │   ├── llm/               # LLM integration
│   │   ├── db/                # Database models and repositories
│   │   ├── services/          # Application services
│   │   └── exceptions.py      # Custom exceptions
│   ├── tests/                 # Unit, integration, E2E tests
│   ├── alembic/               # Database migrations
│   ├── Dockerfile
│   └── pyproject.toml         # uv dependencies
│
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Route pages
│   │   ├── hooks/             # Custom React hooks
│   │   ├── stores/            # Zustand state
│   │   ├── services/          # API client, IndexedDB
│   │   ├── types/             # TypeScript types
│   │   └── utils/
│   ├── tests/
│   ├── Dockerfile
│   └── package.json
│
├── docs/                       # Sphinx documentation
│   ├── source/
│   │   ├── user-guide/        # End-user docs
│   │   ├── developer/         # Developer docs
│   │   ├── api/               # API reference
│   │   └── adr/               # Architecture decisions
│   └── Makefile
│
├── infrastructure/             # Docker & deployment configs
│   ├── docker-compose.yml     # Production
│   └── docker-compose.dev.yml # Development
│
├── scripts/                    # Utility scripts
├── .github/workflows/          # CI/CD pipelines
├── CLAUDE.md                   # Development guidelines
└── README.md                   # This file
```

## Development Workflow

### Code Quality Standards

This project follows strict quality guidelines:

1. **No Silent Failures** - All errors must be informative and propagate to the user
2. **Test-Driven Development (TDD)** - Tests written before implementation
3. **Code Review Checklist** - Style, security, function size, type hints
4. **Test Verification** - Coverage thresholds, edge cases, determinism
5. **Documentation** - Docstrings, Sphinx docs, user guides, ADRs

### Running Tests

```bash
# Backend
cd backend
uv run pytest                              # All tests
uv run pytest --cov=mnemonic              # With coverage
uv run pytest tests/unit/                  # Unit tests only
uv run pytest -k "test_fsrs"               # Pattern matching

# Frontend
cd frontend
npm test                                   # All tests
npm run test:coverage                      # With coverage
npm run test:e2e                           # E2E tests
```

### Code Formatting

```bash
# Backend
cd backend
uv run black src tests                     # Format
uv run ruff check --fix src tests          # Lint
uv run mypy src                            # Type check

# Frontend
cd frontend
npm run format                             # Format with Prettier
npm run lint:fix                           # ESLint
```

### Database Migrations

```bash
cd backend

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback last migration
uv run alembic downgrade -1

# View current revision
uv run alembic current
```

## API Documentation

API documentation is available at:
- **Interactive Docs:** http://localhost:8000/docs (Swagger)
- **Alternative Docs:** http://localhost:8000/redoc (ReDoc)
- **OpenAPI Schema:** http://localhost:8000/openapi.json

## Contributing

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines including:
- Commit message conventions
- Pull request checklist
- Architecture decision records (ADR)
- Testing requirements

## Troubleshooting

### Docker Issues

**Port already in use:**
```bash
# Check what's using the port
lsof -i :8000

# Use different port in docker-compose.dev.yml
# Change "8000:8000" to "8001:8000"
```

**Database connection failed:**
```bash
# Check if PostgreSQL is healthy
docker-compose -f infrastructure/docker-compose.dev.yml ps

# View PostgreSQL logs
docker-compose -f infrastructure/docker-compose.dev.yml logs postgres

# Reset database
docker-compose -f infrastructure/docker-compose.dev.yml down -v
docker-compose -f infrastructure/docker-compose.dev.yml up postgres
```

**Backend won't start:**
```bash
# Check logs
docker-compose -f infrastructure/docker-compose.dev.yml logs backend

# Rebuild image
docker-compose -f infrastructure/docker-compose.dev.yml up --build backend
```

### Local Development Issues

**uv sync fails:**
```bash
# Update uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear cache and resync
rm -rf .uv/
uv sync
```

**npm install fails:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## License

TBD

## Support

For issues, questions, or feedback, please open an issue on GitHub or refer to [CLAUDE.md](./CLAUDE.md) for development guidelines.
