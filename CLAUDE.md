# Mnemonic - Claude Code Instructions

## Project Overview

Mnemonic is an adaptive spaced repetition system with LLM-powered question variations.

**Key characteristics:**
- Single-user, self-hosted
- Offline-first PWA (Android app planned for future)
- FSRS algorithm for scheduling
- LLM variations via OpenRouter
- Leech detection and card decomposition
- DSPy for prompt optimization

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11+, SQLAlchemy |
| Python Env | **uv** (not pip/poetry) |
| Database | PostgreSQL 15+ |
| Cache | Redis |
| Frontend | React 18, TypeScript, Zustand, React Query |
| Offline Storage | IndexedDB (Dexie.js) |
| Rendering | Pandoc, MathJax |
| LLM | OpenRouter (configurable model), DSPy |
| Documentation | **Sphinx** |
| Testing | pytest, Vitest, Playwright |

---

## Critical Principles

### 1. NO SILENT FAILURES

This is the most important principle. **All errors must fail loudly and informatively.**

- Never catch exceptions and return defaults silently
- Never use fallbacks that hide problems from the user
- If something fails, the user must know WHAT failed, WHY, and WHAT TO DO
- Log errors with full context for debugging

```python
# ❌ WRONG - Silent fallback
def get_variation(card):
    try:
        return llm.generate_variation(card)
    except Exception:
        return card.front  # User never knows it failed!

# ❌ WRONG - Generic error
def get_variation(card):
    try:
        return llm.generate_variation(card)
    except Exception:
        raise Exception("Something went wrong")  # Useless!

# ✅ CORRECT - Explicit, informative failure
def get_variation(card):
    try:
        return llm.generate_variation(card)
    except OpenRouterAuthError as e:
        raise LLMConfigError(
            "OpenRouter authentication failed. "
            "Please check your API key in Settings > LLM Configuration. "
            f"Details: {e}"
        ) from e
    except OpenRouterRateLimitError as e:
        raise LLMRateLimitError(
            f"OpenRouter rate limit exceeded. Try again in {e.retry_after}s. "
            "You can reduce variation frequency in Settings, or upgrade your OpenRouter plan."
        ) from e
    except OpenRouterError as e:
        raise LLMError(
            f"Failed to generate variation for card {card.id}. "
            f"OpenRouter returned: {e.message}. "
            "Check your network connection and OpenRouter status."
        ) from e
```

```typescript
// ❌ WRONG - Silent failure in frontend
const fetchCards = async () => {
  try {
    return await api.getCards();
  } catch {
    return []; // User sees empty list, no idea why
  }
};

// ✅ CORRECT - Propagate error to UI
const fetchCards = async () => {
  const response = await api.getCards();
  if (!response.ok) {
    throw new ApiError(
      `Failed to fetch cards: ${response.status} ${response.statusText}`,
      response.status
    );
  }
  return response.data;
};
```

### 2. Test-Driven Development (TDD)

**Always write tests BEFORE implementation.**

```
1. Write a failing test that defines expected behavior
2. Run the test - verify it fails for the RIGHT reason
3. Write the minimal code to make the test pass
4. Run the test - verify it passes
5. Refactor while keeping tests green
6. Run ALL tests - verify no regressions
7. Repeat
```

**Coverage requirements:**
| Area | Minimum |
|------|---------|
| Backend overall | 85% |
| Backend `core/` | 95% |
| Frontend overall | 75% |
| E2E | Critical paths covered |

### 3. Subagent Workflow

Before completing ANY task, run these verification steps:

#### Code Review Checklist
- [ ] Follows style guide (Black, Ruff for Python; Prettier, ESLint for TS)
- [ ] No security vulnerabilities (SQL injection, XSS, etc.)
- [ ] Functions are < 30 lines
- [ ] Files are < 300 lines
- [ ] No silent error handling (see Principle #1)
- [ ] Proper type hints (Python) / types (TypeScript)
- [ ] No magic numbers or strings (use constants)
- [ ] No code duplication

#### Test Verification Checklist
- [ ] All tests pass
- [ ] Coverage thresholds met
- [ ] New code has corresponding tests
- [ ] Tests are deterministic (no flaky tests)
- [ ] Edge cases covered
- [ ] Error cases tested

#### Documentation Checklist
- [ ] Docstrings on all public functions (Google style)
- [ ] Sphinx docs updated if API changed
- [ ] User guide updated if UX changed
- [ ] ADR written if architectural decision made
- [ ] README updated if setup steps changed

---

## Directory Structure

```
mnemonic/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Test + lint on PR
│       ├── cd.yml              # Deploy on merge to main
│       └── docs.yml            # Build + deploy Sphinx docs
│
├── docs/
│   ├── source/
│   │   ├── conf.py             # Sphinx config
│   │   ├── index.rst
│   │   ├── user-guide/         # End-user documentation
│   │   ├── developer/          # Developer documentation
│   │   ├── api/                # Auto-generated API docs
│   │   └── adr/                # Architecture Decision Records
│   └── Makefile
│
├── backend/
│   ├── src/mnemonic/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   │
│   │   ├── api/                # HTTP layer
│   │   │   ├── deps.py         # Dependency injection
│   │   │   ├── middleware.py   # Error handling, logging
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── decks.py
│   │   │       ├── cards.py
│   │   │       ├── reviews.py
│   │   │       ├── leeches.py
│   │   │       └── settings.py
│   │   │
│   │   ├── core/               # Business logic (95% coverage!)
│   │   │   ├── fsrs/           # FSRS algorithm
│   │   │   ├── leech/          # Leech detection
│   │   │   ├── variation/      # Question variation
│   │   │   └── rendering/      # Pandoc/MathJax rendering
│   │   │
│   │   ├── llm/                # LLM integration
│   │   │   ├── openrouter.py   # OpenRouter client
│   │   │   ├── prompts.py      # Prompt templates
│   │   │   └── dspy/           # DSPy modules
│   │   │
│   │   ├── db/                 # Data layer
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── repositories/   # Data access
│   │   │   └── migrations/     # Alembic (via alembic/)
│   │   │
│   │   ├── services/           # Application services
│   │   │
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── tests/
│   │   ├── conftest.py         # Fixtures
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── alembic/                # Database migrations
│   ├── pyproject.toml          # uv/Python config
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/             # Generic UI components
│   │   │   ├── review/         # Review session components
│   │   │   ├── deck/           # Deck management
│   │   │   ├── card/           # Card display/editing
│   │   │   └── leech/          # Leech dashboard/wizard
│   │   │
│   │   ├── pages/              # Route pages
│   │   ├── hooks/              # Custom React hooks
│   │   ├── stores/             # Zustand stores
│   │   ├── services/           # API client, IndexedDB
│   │   ├── types/              # TypeScript types
│   │   └── utils/
│   │
│   ├── tests/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── infrastructure/
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── scripts/
│   ├── setup-dev.sh
│   └── seed-data.py
│
├── CLAUDE.md                   # This file
└── README.md
```

---

## Commands Reference

### Backend

```bash
cd backend

# Environment setup (first time)
uv venv
uv sync

# Run tests
uv run pytest
uv run pytest --cov=mnemonic --cov-report=html  # With coverage
uv run pytest tests/unit/                        # Unit only
uv run pytest -k "test_fsrs"                     # Pattern match

# Linting & formatting
uv run black src tests
uv run ruff check src tests
uv run ruff check --fix src tests               # Auto-fix
uv run mypy src

# Database
uv run alembic upgrade head                      # Run migrations
uv run alembic revision --autogenerate -m "msg"  # Create migration

# Run server
uv run uvicorn mnemonic.main:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run tests
npm test
npm run test:coverage
npm run test:e2e                                 # Playwright

# Linting & formatting
npm run lint
npm run lint:fix
npm run format

# Development
npm run dev

# Build
npm run build
```

### Documentation

```bash
cd docs

# Build HTML docs
make html

# Auto-rebuild on changes (dev)
make livehtml

# Check for broken links
make linkcheck
```

### Docker

```bash
# Start all services (dev)
docker-compose -f docker-compose.dev.yml up

# Start specific service
docker-compose -f docker-compose.dev.yml up postgres redis

# Reset database
docker-compose -f docker-compose.dev.yml down -v
```

---

## Card Content Syntax

Cards use Markdown with special shortcodes, rendered via Pandoc + MathJax.

### Basic Front/Back Card

```markdown
:::{.front}
What is the capital of France?
:::

:::{.back}
Paris
:::
```

### Card with Math (MathJax)

```markdown
:::{.front}
What is the derivative of $f(x) = x^2$?
:::

:::{.back}
$$f'(x) = 2x$$
:::
```

### Cloze Deletion

Single cloze:
```markdown
The {{cloze:1::mitochondria}} is the powerhouse of the cell.
```

Layered cloze (multiple cards generated):
```markdown
The {{cloze:1::mitochondria}} is the {{cloze:2::powerhouse}} of the cell.
```

### Image Cloze

```markdown
:::{.image-cloze}
![Anatomy diagram](anatomy.png)

{{region:1::x=100,y=200,w=50,h=50::Heart}}
{{region:2::x=200,y=150,w=40,h=40::Lungs}}
:::
```

---

## Database Models (Key Entities)

```
User
├── id, email, password_hash
├── fsrs_params (JSON)
└── settings (JSON)

Deck
├── id, user_id, name, description
├── variation_enabled, variation_frequency
├── leech_threshold
└── daily_review_limit, daily_new_limit

CardType
├── id, user_id (null for builtins)
├── name, description
├── parent_type_id (for inheritance)
├── syntax_type: "frontback" | "cloze" | "image_cloze" | "custom"
├── fields (JSON array)
├── render_pipeline (JSON - Pandoc filters)
└── is_builtin

Card
├── id, deck_id, card_type_id
├── content (Markdown with shortcodes)
├── notes (user's personal notes)
├── tags (JSON array)
├── FSRS: state, stability, difficulty, due, reps, lapses
├── Leech: leech_score, leech_notified, parent_card_id
└── suspended

ReviewLog
├── id, card_id, user_id
├── rating (1-4), response_time_ms, review_time
├── state_before/after, stability_before/after, difficulty_before/after
└── variation_used, variation_id, variation_helpful
```

---

## Exception Hierarchy

```python
# backend/src/mnemonic/exceptions.py

class MnemonicError(Exception):
    """Base exception for all Mnemonic errors."""
    pass

# Database errors
class NotFoundError(MnemonicError):
    """Resource not found."""
    pass

class CardNotFoundError(NotFoundError):
    pass

class DeckNotFoundError(NotFoundError):
    pass

# Validation errors
class ValidationError(MnemonicError):
    """Invalid input data."""
    pass

class InvalidRatingError(ValidationError):
    pass

class InvalidCardSyntaxError(ValidationError):
    pass

# LLM errors
class LLMError(MnemonicError):
    """Base class for LLM-related errors."""
    pass

class LLMConfigError(LLMError):
    """LLM configuration issue (API key, model selection)."""
    pass

class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after

class LLMUnavailableError(LLMError):
    """LLM service unavailable."""
    pass

# Rendering errors  
class RenderError(MnemonicError):
    """Card rendering failed."""
    pass

class PandocError(RenderError):
    pass

class MathJaxError(RenderError):
    pass
```

---

## Git Workflow

### Branches

- `main` - Production (protected)
- `develop` - Integration branch
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation only

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add cloze card rendering
fix: prevent silent failure in variation generation
docs: update API documentation for review endpoints
test: add edge cases for FSRS scheduler
refactor: extract card parser into separate module
chore: update dependencies
```

### Pull Request Checklist

Before merging:
- [ ] All CI checks pass
- [ ] Code review approved
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No silent error handling
- [ ] Coverage thresholds met

---

## Current Phase: Phase 1 - Foundation

**Goal:** Local database, server, and basic web app working.

**Priority order:**
1. Project setup (Docker, uv, CI/CD, pre-commit hooks)
2. Database models & Alembic migrations
3. FSRS algorithm implementation with comprehensive tests
4. Basic API (auth, CRUD for decks/cards)
5. Card type system with Pandoc/MathJax rendering
6. Frontend foundation (routing, API client, deck list)

**User Stories for Phase 1:** US-001 through US-023

---

## Reminders

1. **Tests first.** Always.

2. **Errors must be informative.** If you catch an exception, you must either:
   - Re-raise with more context, OR
   - Handle it completely (log, notify user, recover)
   - NEVER swallow silently

3. **Run all three checklists** before marking any task complete:
   - Code Review
   - Test Verification  
   - Documentation

4. **When in doubt, fail loudly.** It's better for the user to see an error than to silently get wrong behavior.

5. **Keep functions small.** If a function is over 30 lines, split it.

6. **Type everything.** Python type hints, TypeScript types. No `Any` unless absolutely necessary.

7. **Document public APIs.** Every public function needs a docstring explaining what it does, its parameters, return value, and possible exceptions.
