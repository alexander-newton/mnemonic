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
- **Backend:** FastAPI, Python 3.11+, PostgreSQL 15+, Redis
- **Frontend:** React 18, TypeScript, Zustand, React Query
- **LLM:** OpenRouter (configurable model)
- **Package Manager:** uv (Python), npm (Node)

## Prerequisites

- Docker & Docker Compose 3.9+
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend development)
- PostgreSQL 15+ (if running locally without Docker)
- Redis (if running locally without Docker)

## Quick Start (Docker)

The fastest way to get started is with Docker Compose:

```bash
# Navigate to infrastructure directory
cd infrastructure

# Start all services
docker-compose -f docker-compose.dev.yml up

# In a new terminal, run database migrations
docker-compose -f docker-compose.dev.yml exec backend uv run alembic upgrade head
```

Services will be available at:
- **Frontend:** http://localhost:5173
- **API:** http://localhost:8000
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

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

# Run database migrations
uv run alembic upgrade head

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

## Docker Compose Commands

### Development Environment

```bash
cd infrastructure

# Start all services
docker-compose -f docker-compose.dev.yml up

# Start specific services
docker-compose -f docker-compose.dev.yml up postgres redis

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Reset database (WARNING: deletes all data)
docker-compose -f docker-compose.dev.yml down -v
```

### Production Environment

```bash
cd infrastructure

# Create .env file with required variables
cat > .env << EOF
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
OPENROUTER_API_KEY=<your-api-key>
EOF

# Start services
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose -f docker-compose.yml logs -f backend

# Stop services
docker-compose -f docker-compose.yml down
```

## Configuration

### Backend Configuration

Create `backend/.env` with:

```env
# Database
DATABASE_URL=postgresql://mnemonic:password@localhost:5432/mnemonic
REDIS_URL=redis://localhost:6379/0

# LLM
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=openai/gpt-4

# Server
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### Frontend Configuration

Environment variables in `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_LOG_LEVEL=debug
```

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
