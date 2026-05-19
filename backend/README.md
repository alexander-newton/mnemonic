# Mnemonic Backend

FastAPI-based backend for the Mnemonic adaptive spaced repetition system.

## Requirements

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

## Installation

### 1. Set Up Python Environment with uv

Install uv (fast Python package installer):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install dependencies:
```bash
uv sync
```

### 2. Set Up Database

With PostgreSQL running, create the database and run migrations:
```bash
# First, create the database if it doesn't exist
createdb mnemonic -U mnemonic  # Adjust user/password as needed

# Run migrations
uv run alembic upgrade head
```

#### Migration Management

Create a new migration after schema changes:
```bash
uv run alembic revision --autogenerate -m "your migration message"
```

View current migration status:
```bash
uv run alembic current  # Shows current revision
uv run alembic history  # Shows all revisions
```

Rollback to a previous migration:
```bash
uv run alembic downgrade -1  # Rollback one step
uv run alembic downgrade <revision_id>  # Rollback to specific revision
uv run alembic downgrade base  # Rollback all migrations
```

For more details on migrations, see [Migration Documentation](docs/source/developer/migrations.md).

### 3. Configure Environment

Copy `.env.example` to `.env` and update with your values:
```bash
cp .env.example .env
```

Required settings:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENROUTER_API_KEY`: Your OpenRouter API key (for LLM variations)
- `ENVIRONMENT`: `development` or `production`

## Running Tests

Run all tests with coverage:
```bash
uv run pytest --cov=mnemonic --cov-report=html
```

Run tests by category:
```bash
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests only
uv run pytest -k "test_fsrs"       # Pattern matching
```

Run specific test file:
```bash
uv run pytest tests/unit/core/test_fsrs.py
```

## Development Server

Start the development server with auto-reload:
```bash
uv run uvicorn mnemonic.main:app --reload
```

Server runs at http://localhost:8000

API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Linting & Type Checking

Format code with Black:
```bash
uv run black src tests
```

Check code style with Ruff:
```bash
uv run ruff check src tests
uv run ruff check --fix src tests  # Auto-fix
```

Type check with mypy:
```bash
uv run mypy src
```

## Docker

Build and run with Docker Compose (includes PostgreSQL and Redis):
```bash
docker-compose -f ../infrastructure/docker-compose.dev.yml up
```

The backend will be available at http://localhost:8000

To reset the database:
```bash
docker-compose -f ../infrastructure/docker-compose.dev.yml down -v
```

## Architecture

See [CLAUDE.md](../CLAUDE.md) for:
- Complete project architecture
- Database models
- Exception hierarchy
- Card content syntax
- Development workflow

## API Endpoints

See `/docs` (Swagger UI) for full API documentation. Key routes:

- `POST /auth/register` - Register user
- `POST /auth/login` - Login user
- `GET /decks` - List user's decks
- `POST /decks` - Create new deck
- `GET /cards?deck_id=...` - List cards in deck
- `POST /reviews` - Submit card review
- `GET /leeches` - Get leech cards
