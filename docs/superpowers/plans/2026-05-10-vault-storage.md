# Vault-Backed Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Mnemonic's PostgreSQL storage with an Obsidian/Quarto vault Git repo + SQLite sidecar, add an Anthropic-SDK-direct LLM client with prompt caching, and a per-card-dossier note convention with a variation-writing skill.

**Architecture:** Vault is the source of truth for card content (per-card `.md`/`.qmd` notes following a canonical `## Card` / `## Context` / `## Variations` structure). `.mnemonic/state.sqlite` inside the vault holds FSRS state, review log, variation metadata, and LLM usage. A vault module scans, parses, injects block IDs, writes variation entries, and runs Git operations. The LLM client wraps the Anthropic SDK behind a Protocol with prompt caching, model tiering, and a budget guard. FastAPI + React stack retained; auth/User dropped (single-user).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy + SQLite, Alembic, `anthropic` SDK, `watchdog`, subprocess `git`, pytest, Vitest, Playwright.

**Reference spec:** `docs/superpowers/specs/2026-05-10-vault-storage-design.md`

---

## File Structure

**New backend modules:**
```
backend/src/mnemonic/
├── vault/                         NEW MODULE
│   ├── __init__.py
│   ├── note.py                    canonical-section parser
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── cloze.py
│   │   ├── highlight.py
│   │   └── callout.py
│   ├── injector.py                block-ID + variation-section writes
│   ├── deck.py                    folder→deck + _deck.md parser
│   ├── scanner.py                 walks vault, emits Cards
│   ├── repository.py              joins scan with SQLite state
│   ├── git_ops.py                 subprocess git wrapper
│   ├── watcher.py                 watchdog-based optional
│   └── session.py                 lifecycle: pre-flight → scan → review → commit → push
├── llm/
│   ├── client.py                  LLMClient Protocol + types
│   ├── backends/
│   │   ├── __init__.py
│   │   └── anthropic.py
│   ├── cache.py                   build cache_control blocks
│   ├── budget.py                  daily/monthly cost cap
│   ├── router.py                  model-tier picker
│   ├── batch.py                   batch-API submitter (offline)
│   ├── exceptions.py              extends mnemonic.exceptions.LLMError
│   ├── prompts/
│   │   └── variation/
│   │       ├── SKILL.md
│   │       ├── system.j2
│   │       ├── user.j2
│   │       └── strategies/{rephrase,specialize,generalize}.md
│   ├── variation/
│   │   ├── __init__.py
│   │   ├── strategy.py            strategy selector
│   │   ├── generator.py           renders prompts, calls client
│   │   └── writer.py              appends entries to note's ## Variations
│   └── dspy/
│       └── variation_optimizer.py (offline; stubbed in Phase 1)
└── db/
    ├── sqlite.py                  SQLite engine + session
    └── models/
        ├── scheduling_state.py    NEW
        ├── variation_meta.py      NEW (replaces variation_cache)
        ├── review_log.py          REWRITTEN for SQLite
        ├── llm_usage.py           REWRITTEN for SQLite
        └── training_example.py    REWRITTEN for SQLite
```

**Deletions:**
```
backend/src/mnemonic/db/models/{user,card,deck,card_type,variation_cache}.py
backend/src/mnemonic/db/repositories/{user,card,deck}.py
backend/src/mnemonic/services/auth.py
backend/src/mnemonic/api/routes/auth.py
backend/alembic/versions/0001_initial_schema_with_all_models.py
backend/alembic/versions/0002_seed_builtin_card_types.py
frontend/src/pages/{LoginPage,RegisterPage}.tsx
frontend/src/components/ProtectedRoute.tsx
frontend/src/hooks/useAuth.ts
frontend/src/stores/authStore.ts
```

**Config:**
- `~/.config/mnemonic/config.toml` (user-global)
- `<vault>/.mnemonic/config.toml` (vault-local; vault-local wins per-key)
- `<vault>/.gitignore` and `<vault>/.gitattributes` managed by Mnemonic

---

## Pre-flight: dependency updates

### Task 0: Update Python dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Edit pyproject.toml dependencies**

Replace the `dependencies` block. Remove `psycopg2-binary`, `python-jose`, `passlib`, `argon2-cffi`, `python-multipart`. Add `anthropic`, `watchdog`, `tomli` (Python 3.10 fallback; std-lib `tomllib` on 3.11+ but we support config writing → keep `tomli-w`), `jinja2`.

```toml
dependencies = [
    # Core framework
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic[email]>=2.5.0",
    "pydantic-settings>=2.1.0",

    # Database
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",

    # HTTP client
    "httpx>=0.25.0",

    # LLM
    "anthropic>=0.40.0",
    "dspy-ai>=2.0.0",

    # Vault
    "watchdog>=4.0.0",

    # Templating (LLM prompts)
    "jinja2>=3.1.0",

    # Config
    "tomli-w>=1.0.0",

    # Utilities
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "pypandoc>=1.11.0",
]
```

- [ ] **Step 2: Sync env**

Run: `cd backend && uv sync`
Expected: lockfile updates; new packages installed; removed packages uninstalled.

- [ ] **Step 3: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore: update deps for vault-backed storage (anthropic, watchdog, jinja2; drop psycopg/jose/passlib)"
```

---

## Wave 1: Foundations (config, exceptions, SQLite engine)

### Task 1: Extend exception hierarchy

**Files:**
- Modify: `backend/src/mnemonic/exceptions.py`
- Test: `backend/tests/unit/test_exceptions.py`

- [ ] **Step 1: Write failing tests for new exceptions**

Append to `backend/tests/unit/test_exceptions.py`:

```python
from mnemonic.exceptions import (
    LLMBudgetExceededError,
    GitDirtyWorkingTreeError,
    GitNonFastForwardError,
    GitPushRejectedError,
    VaultNotConfiguredError,
    MalformedNoteError,
    MalformedVariationSectionError,
    OrphanCardError,
)


def test_llm_budget_exceeded_carries_amounts():
    err = LLMBudgetExceededError(spent_millicents=2600, cap_millicents=2500, scope="daily")
    assert err.spent_millicents == 2600
    assert err.cap_millicents == 2500
    assert err.scope == "daily"
    assert "daily" in str(err)


def test_git_errors_subclass_mnemonic_error():
    from mnemonic.exceptions import MnemonicError
    assert issubclass(GitDirtyWorkingTreeError, MnemonicError)
    assert issubclass(GitNonFastForwardError, MnemonicError)
    assert issubclass(GitPushRejectedError, MnemonicError)


def test_vault_errors_subclass_mnemonic_error():
    from mnemonic.exceptions import MnemonicError
    assert issubclass(VaultNotConfiguredError, MnemonicError)
    assert issubclass(MalformedNoteError, MnemonicError)
    assert issubclass(MalformedVariationSectionError, MnemonicError)
    assert issubclass(OrphanCardError, MnemonicError)
```

- [ ] **Step 2: Run tests; verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_exceptions.py -v`
Expected: FAIL — `ImportError: cannot import name ...`

- [ ] **Step 3: Add exceptions to `exceptions.py`**

Append to `backend/src/mnemonic/exceptions.py`:

```python
# LLM additions
class LLMBudgetExceededError(LLMError):
    """LLM cost cap (daily or monthly) reached."""

    def __init__(self, spent_millicents: int, cap_millicents: int, scope: str) -> None:
        self.spent_millicents = spent_millicents
        self.cap_millicents = cap_millicents
        self.scope = scope
        super().__init__(
            f"LLM {scope} budget exceeded: spent "
            f"{spent_millicents / 1000:.2f} cents of {cap_millicents / 1000:.2f} cents. "
            f"Raise the cap in [llm.budget] in ~/.config/mnemonic/config.toml."
        )


# Git errors
class GitError(MnemonicError):
    """Base class for Git operation failures."""

    pass


class GitDirtyWorkingTreeError(GitError):
    """Vault has uncommitted changes; refuse to start a session."""

    pass


class GitNonFastForwardError(GitError):
    """Remote has commits that cannot fast-forward into local."""

    pass


class GitPushRejectedError(GitError):
    """Push rejected by remote (typically: concurrent push)."""

    pass


# Vault errors
class VaultError(MnemonicError):
    """Base class for vault-layer failures."""

    pass


class VaultNotConfiguredError(VaultError):
    """vault_path missing and no vault_remote available to clone."""

    pass


class MalformedNoteError(VaultError):
    """A card-note does not match the canonical structure."""

    pass


class MalformedVariationSectionError(VaultError):
    """## Variations section is missing the begin/end markers."""

    pass


class OrphanCardError(VaultError):
    """A SchedulingState row has no corresponding card-note."""

    pass
```

- [ ] **Step 4: Run tests; verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_exceptions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/exceptions.py backend/tests/unit/test_exceptions.py
git commit -m "feat(exceptions): add Git, Vault, LLM-budget exception classes"
```

---

### Task 2: Config loader (config.toml)

**Files:**
- Create: `backend/src/mnemonic/config.py` (rewrite existing)
- Create: `backend/tests/unit/test_config.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/test_config.py`:

```python
from pathlib import Path
import pytest
from mnemonic.config import Config, load_config
from mnemonic.exceptions import VaultNotConfiguredError


def test_load_user_global_only(tmp_path: Path):
    user_cfg = tmp_path / "config.toml"
    user_cfg.write_text(
        '[vault]\npath = "/tmp/v"\nremote = "git@x.com:u/v.git"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "ANTHROPIC_API_KEY"\nmodel_default = "claude-sonnet-4-6"\n'
        'model_rephrase = "claude-haiku-4-5"\nmodel_offline = "claude-opus-4-7"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    cfg = load_config(user_global_path=user_cfg)
    assert cfg.vault.path == Path("/tmp/v")
    assert cfg.vault.branch == "main"
    assert cfg.llm.model_default == "claude-sonnet-4-6"
    assert cfg.llm.budget.daily_cents == 25
    assert cfg.defaults.variation_frequency == 0.5


def test_vault_local_overrides_user_global(tmp_path: Path):
    user_cfg = tmp_path / "user.toml"
    user_cfg.write_text(
        '[vault]\npath = "' + str(tmp_path) + '"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "ANTHROPIC_API_KEY"\nmodel_default = "claude-sonnet-4-6"\n'
        'model_rephrase = "claude-haiku-4-5"\nmodel_offline = "claude-opus-4-7"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    vault_local_dir = tmp_path / ".mnemonic"
    vault_local_dir.mkdir()
    (vault_local_dir / "config.toml").write_text(
        '[defaults]\nvariation_frequency = 0.6\n'
    )
    cfg = load_config(user_global_path=user_cfg)
    assert cfg.defaults.variation_frequency == 0.6
    assert cfg.defaults.leech_threshold == 8  # not overridden


def test_missing_vault_path_raises(tmp_path: Path):
    user_cfg = tmp_path / "config.toml"
    user_cfg.write_text(
        '[llm]\napi_key_env = "ANTHROPIC_API_KEY"\nmodel_default = "claude-sonnet-4-6"\n'
        'model_rephrase = "claude-haiku-4-5"\nmodel_offline = "claude-opus-4-7"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    with pytest.raises(VaultNotConfiguredError):
        load_config(user_global_path=user_cfg)
```

- [ ] **Step 2: Run; verify failure**

Run: `cd backend && uv run pytest tests/unit/test_config.py -v`
Expected: FAIL — `ImportError` or attribute mismatch.

- [ ] **Step 3: Rewrite `config.py`**

Replace `backend/src/mnemonic/config.py`:

```python
"""Configuration loader for Mnemonic.

Loads from ~/.config/mnemonic/config.toml (user-global) overlaid by
<vault>/.mnemonic/config.toml (vault-local). Vault-local wins per-key.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from mnemonic.exceptions import VaultNotConfiguredError


@dataclass(frozen=True)
class VaultConfig:
    path: Path
    remote: str | None
    branch: str
    watch: bool


@dataclass(frozen=True)
class BudgetConfig:
    daily_cents: int
    monthly_cents: int


@dataclass(frozen=True)
class LLMConfig:
    api_key_env: str
    model_default: str
    model_rephrase: str
    model_offline: str
    budget: BudgetConfig


@dataclass(frozen=True)
class DefaultsConfig:
    variation_enabled: bool
    variation_frequency: float
    leech_threshold: int
    daily_review_limit: int
    daily_new_limit: int


@dataclass(frozen=True)
class Config:
    vault: VaultConfig
    llm: LLMConfig
    defaults: DefaultsConfig


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _user_global_default() -> Path:
    return Path.home() / ".config" / "mnemonic" / "config.toml"


def load_config(*, user_global_path: Path | None = None) -> Config:
    """Load merged config. Returns frozen Config dataclass.

    Raises:
        VaultNotConfiguredError: if vault.path is missing or empty after merge.
    """
    user_path = user_global_path or _user_global_default()
    if not user_path.exists():
        raise VaultNotConfiguredError(
            f"User config missing at {user_path}. "
            "Run `mnemonic init` or create the file manually with [vault], [llm], [defaults] sections."
        )
    user_data = tomllib.loads(user_path.read_text())

    vault_path_str = user_data.get("vault", {}).get("path", "")
    if not vault_path_str:
        raise VaultNotConfiguredError(
            "[vault] path is missing in config. "
            f"Set vault.path in {user_path}."
        )
    vault_path = Path(vault_path_str)

    vault_local_path = vault_path / ".mnemonic" / "config.toml"
    if vault_local_path.exists():
        vault_data = tomllib.loads(vault_local_path.read_text())
        merged = _deep_merge(user_data, vault_data)
    else:
        merged = user_data

    vault_section = merged["vault"]
    llm_section = merged["llm"]
    budget_section = llm_section["budget"]
    defaults_section = merged["defaults"]

    return Config(
        vault=VaultConfig(
            path=Path(vault_section["path"]),
            remote=vault_section.get("remote"),
            branch=vault_section.get("branch", "main"),
            watch=vault_section.get("watch", False),
        ),
        llm=LLMConfig(
            api_key_env=llm_section["api_key_env"],
            model_default=llm_section["model_default"],
            model_rephrase=llm_section["model_rephrase"],
            model_offline=llm_section["model_offline"],
            budget=BudgetConfig(
                daily_cents=budget_section["daily_cents"],
                monthly_cents=budget_section["monthly_cents"],
            ),
        ),
        defaults=DefaultsConfig(
            variation_enabled=defaults_section["variation_enabled"],
            variation_frequency=defaults_section["variation_frequency"],
            leech_threshold=defaults_section["leech_threshold"],
            daily_review_limit=defaults_section["daily_review_limit"],
            daily_new_limit=defaults_section["daily_new_limit"],
        ),
    )
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/config.py backend/tests/unit/test_config.py
git commit -m "feat(config): TOML-based config loader with vault-local override"
```

---

### Task 3: SQLite engine + base

**Files:**
- Create: `backend/src/mnemonic/db/sqlite.py`
- Modify: `backend/src/mnemonic/db/models/base.py` (only if currently Postgres-specific)
- Test: `backend/tests/unit/db/test_sqlite_engine.py`

- [ ] **Step 1: Inspect existing base**

Run: `cat backend/src/mnemonic/db/models/base.py`
Expected: see existing `Base` definition; confirm whether it imports from postgres dialect.

- [ ] **Step 2: Write failing test**

Create `backend/tests/unit/db/test_sqlite_engine.py`:

```python
from pathlib import Path
from mnemonic.db.sqlite import create_engine, session_scope


def test_engine_creates_file(tmp_path: Path):
    db_path = tmp_path / "state.sqlite"
    engine = create_engine(db_path)
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    assert db_path.exists()


def test_session_scope_commits(tmp_path: Path):
    from sqlalchemy import text
    db_path = tmp_path / "state.sqlite"
    engine = create_engine(db_path)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (k TEXT PRIMARY KEY, v TEXT)"))
    with session_scope(engine) as s:
        s.execute(text("INSERT INTO t VALUES ('a', 'b')"))
    with engine.connect() as conn:
        rows = list(conn.execute(text("SELECT * FROM t")))
    assert rows == [("a", "b")]
```

- [ ] **Step 3: Run; verify failure**

Run: `cd backend && uv run pytest tests/unit/db/test_sqlite_engine.py -v`
Expected: FAIL — `ImportError: mnemonic.db.sqlite`

- [ ] **Step 4: Implement `db/sqlite.py`**

Create `backend/src/mnemonic/db/sqlite.py`:

```python
"""SQLite engine factory and session helper for Mnemonic state."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine(db_path: Path) -> Engine:
    """Create a SQLite engine targeting the given path. Enables WAL + foreign keys."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = _create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )

    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 5: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/db/test_sqlite_engine.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/mnemonic/db/sqlite.py backend/tests/unit/db/test_sqlite_engine.py
git commit -m "feat(db): SQLite engine factory with WAL + foreign-keys pragmas"
```

---

## Wave 2: Note parsing and card extractors

### Task 4: Canonical note parser

**Files:**
- Create: `backend/src/mnemonic/vault/__init__.py` (empty)
- Create: `backend/src/mnemonic/vault/note.py`
- Create: `backend/tests/unit/vault/__init__.py` (empty)
- Create: `backend/tests/unit/vault/test_note.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/unit/vault/test_note.py`:

```python
import pytest
from mnemonic.vault.note import (
    parse_note,
    ParsedNote,
    BLOCK_ID_RE,
    VAR_BEGIN,
    VAR_END,
)
from mnemonic.exceptions import MalformedNoteError


def test_parses_full_canonical_note():
    text = """---
title: Nash equilibrium
tags: [game-theory]
---

## Card

A {{c1::Nash equilibrium}} is a strategy profile. ^card-7f3a

## Context

Mutual best responses.

## Variations

<!-- mnemonic:variations:begin -->
### 2026-04-12 (rating: 4)
**Q:** When is a profile a NE?
**A:** When no deviation improves any payoff.
<!-- mnemonic:variations:end -->
"""
    note = parse_note(text)
    assert isinstance(note, ParsedNote)
    assert note.frontmatter["title"] == "Nash equilibrium"
    assert "Nash equilibrium" in note.card_section
    assert note.block_id == "card-7f3a"
    assert "best responses" in note.context_section
    assert note.variations_section is not None
    assert "2026-04-12" in note.variations_section


def test_card_section_only_yields_no_block_id():
    text = """---
title: t
---

## Card

A ==Nash equilibrium== is a profile.
"""
    note = parse_note(text)
    assert note.block_id is None  # not yet injected


def test_missing_card_section_returns_non_card_note():
    text = """---
title: just a regular note
---

Some prose with no ## Card heading.
"""
    note = parse_note(text)
    assert note.is_card_note is False


def test_missing_title_raises():
    text = """---
tags: [x]
---

## Card

stuff. ^card-1234abcd
"""
    with pytest.raises(MalformedNoteError):
        parse_note(text)


def test_variations_section_without_markers_raises():
    text = """---
title: t
---

## Card

stuff. ^card-7f3a

## Variations

### 2026-04-12 (rating: 4)
no markers
"""
    with pytest.raises(MalformedNoteError):
        parse_note(text)
```

- [ ] **Step 2: Run; expect failure**

Run: `cd backend && uv run pytest tests/unit/vault/test_note.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement `vault/note.py`**

Create `backend/src/mnemonic/vault/__init__.py` (empty file).

Create `backend/src/mnemonic/vault/note.py`:

```python
"""Parser for the canonical Mnemonic note structure.

A card-note has:
  - YAML frontmatter (title required)
  - ## Card section (contains card markers + optional ^card-xyz block ID)
  - ## Context section (optional)
  - ## Variations section (optional; bounded by mnemonic markers)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from mnemonic.exceptions import MalformedNoteError

BLOCK_ID_RE = re.compile(r"\^(card-[0-9a-f]{8})\b")
VAR_BEGIN = "<!-- mnemonic:variations:begin -->"
VAR_END = "<!-- mnemonic:variations:end -->"

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(\S.*?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ParsedNote:
    frontmatter: dict[str, Any]
    card_section: str | None
    context_section: str | None
    variations_section: str | None
    block_id: str | None
    raw_text: str

    @property
    def is_card_note(self) -> bool:
        return self.card_section is not None


def parse_note(text: str) -> ParsedNote:
    """Parse a Mnemonic note. Raises MalformedNoteError on structural problems."""
    frontmatter, body = _split_frontmatter(text)

    sections = _split_h2_sections(body)
    card = sections.get("Card")
    context = sections.get("Context")
    variations = sections.get("Variations")

    if card is None:
        return ParsedNote(
            frontmatter=frontmatter,
            card_section=None,
            context_section=None,
            variations_section=None,
            block_id=None,
            raw_text=text,
        )

    if "title" not in frontmatter:
        raise MalformedNoteError(
            "Card-note missing required `title` field in frontmatter."
        )

    if variations is not None:
        if VAR_BEGIN not in variations or VAR_END not in variations:
            raise MalformedNoteError(
                "## Variations section is missing the mnemonic markers. "
                f"Expected `{VAR_BEGIN}` and `{VAR_END}`."
            )

    block_id_match = BLOCK_ID_RE.search(card)
    block_id = block_id_match.group(1) if block_id_match else None

    return ParsedNote(
        frontmatter=frontmatter,
        card_section=card,
        context_section=context,
        variations_section=variations,
        block_id=block_id,
        raw_text=text,
    )


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return ({}, text)
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise MalformedNoteError(f"Invalid YAML in frontmatter: {e}") from e
    if not isinstance(fm, dict):
        raise MalformedNoteError("Frontmatter must be a YAML mapping.")
    return (fm, text[m.end() :])


def _split_h2_sections(body: str) -> dict[str, str]:
    """Return a dict mapping each ## heading text to the body following it."""
    matches = list(_HEADING_RE.finditer(body))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[name] = body[start:end].strip("\n")
    return out
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_note.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/ backend/tests/unit/vault/
git commit -m "feat(vault): canonical note parser with frontmatter + section detection"
```

---

### Task 5: Cloze extractor

**Files:**
- Create: `backend/src/mnemonic/vault/extractors/__init__.py`
- Create: `backend/src/mnemonic/vault/extractors/cloze.py`
- Create: `backend/tests/unit/vault/test_extractors.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/vault/test_extractors.py`:

```python
import pytest
from mnemonic.vault.extractors.cloze import extract_cloze, ExtractedCard
from mnemonic.exceptions import InvalidCardSyntaxError


def test_single_cloze():
    text = "A {{c1::Nash equilibrium}} is a strategy profile."
    card = extract_cloze(text)
    assert isinstance(card, ExtractedCard)
    assert card.syntax == "cloze"
    assert "Nash equilibrium" in card.cloze_terms
    assert card.front.startswith("A [...]")
    assert card.back == text


def test_multiple_clozes_same_number_blank_together():
    text = "A {{c1::Nash equilibrium}} is {{c1::stable}}."
    card = extract_cloze(text)
    assert card.cloze_terms == ["Nash equilibrium", "stable"]
    assert card.front == "A [...] is [...]."


def test_multiple_clozes_different_numbers():
    # Per spec §4.2: different numbers still blank together
    text = "A {{c1::NE}} is {{c2::stable}}."
    card = extract_cloze(text)
    assert card.cloze_terms == ["NE", "stable"]
    assert card.front == "A [...] is [...]."


def test_no_cloze_raises():
    with pytest.raises(InvalidCardSyntaxError):
        extract_cloze("plain text with no markers")
```

- [ ] **Step 2: Run; expect failure**

Run: `cd backend && uv run pytest tests/unit/vault/test_extractors.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement cloze extractor**

Create `backend/src/mnemonic/vault/extractors/__init__.py`:

```python
"""Card-marker extractors. Each module exposes an `extract_*` function returning ExtractedCard."""

from mnemonic.vault.extractors.cloze import ExtractedCard, extract_cloze

__all__ = ["ExtractedCard", "extract_cloze"]
```

Create `backend/src/mnemonic/vault/extractors/cloze.py`:

```python
"""Cloze deletion extractor.

Recognises `{{cN::text}}` markers. All clozes (regardless of number) blank
together in the rendered front face — Mnemonic treats one note as one card
per spec §4.2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mnemonic.exceptions import InvalidCardSyntaxError

_CLOZE_RE = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")


@dataclass(frozen=True)
class ExtractedCard:
    syntax: str  # "cloze" | "highlight" | "callout"
    front: str
    back: str
    cloze_terms: list[str]


def extract_cloze(card_section_text: str) -> ExtractedCard:
    """Parse a `## Card` body containing cloze markers.

    Raises InvalidCardSyntaxError if no marker found.
    """
    matches = list(_CLOZE_RE.finditer(card_section_text))
    if not matches:
        raise InvalidCardSyntaxError(
            "Cloze extractor invoked but no {{cN::...}} markers found in card section."
        )

    terms: list[str] = []
    front_parts: list[str] = []
    last_end = 0
    for m in matches:
        front_parts.append(card_section_text[last_end : m.start()])
        front_parts.append("[...]")
        terms.append(m.group(2))
        last_end = m.end()
    front_parts.append(card_section_text[last_end:])
    front = "".join(front_parts).strip()

    back_parts: list[str] = []
    last_end = 0
    for m in matches:
        back_parts.append(card_section_text[last_end : m.start()])
        back_parts.append(m.group(2))
        last_end = m.end()
    back_parts.append(card_section_text[last_end:])
    back = "".join(back_parts).strip()

    return ExtractedCard(syntax="cloze", front=front, back=back, cloze_terms=terms)
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_extractors.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/extractors/ backend/tests/unit/vault/test_extractors.py
git commit -m "feat(vault): cloze extractor with multi-marker grouping"
```

---

### Task 6: Highlight cloze + callout extractors

**Files:**
- Create: `backend/src/mnemonic/vault/extractors/highlight.py`
- Create: `backend/src/mnemonic/vault/extractors/callout.py`
- Modify: `backend/src/mnemonic/vault/extractors/__init__.py`
- Modify: `backend/tests/unit/vault/test_extractors.py`

- [ ] **Step 1: Add failing tests for both extractors**

Append to `backend/tests/unit/vault/test_extractors.py`:

```python
from mnemonic.vault.extractors.highlight import extract_highlight
from mnemonic.vault.extractors.callout import extract_callout


def test_highlight_single():
    text = "A ==Nash equilibrium== is a profile."
    card = extract_highlight(text)
    assert card.syntax == "highlight"
    assert card.cloze_terms == ["Nash equilibrium"]
    assert "[...]" in card.front
    assert "Nash equilibrium" in card.back


def test_highlight_multiple_blank_together():
    text = "A ==NE== is ==stable==."
    card = extract_highlight(text)
    assert card.cloze_terms == ["NE", "stable"]
    assert card.front == "A [...] is [...]."


def test_highlight_no_markers_raises():
    with pytest.raises(InvalidCardSyntaxError):
        extract_highlight("plain text")


def test_callout_basic():
    text = "> [!card]\n> **Q:** Define NE.\n> **A:** A profile where..."
    card = extract_callout(text)
    assert card.syntax == "callout"
    assert "Define NE" in card.front
    assert "profile where" in card.back


def test_callout_multiline_answer():
    text = (
        "> [!card]\n"
        "> **Q:** State the minimax theorem.\n"
        "> **A:** For any 2-player zero-sum finite game,\n"
        "> max-min equals min-max."
    )
    card = extract_callout(text)
    assert "minimax theorem" in card.front
    assert "max-min equals min-max" in card.back


def test_callout_missing_q_or_a_raises():
    with pytest.raises(InvalidCardSyntaxError):
        extract_callout("> [!card]\n> only one line")
```

- [ ] **Step 2: Run; expect failure**

Run: `cd backend && uv run pytest tests/unit/vault/test_extractors.py -v`
Expected: import errors for new modules.

- [ ] **Step 3: Implement `highlight.py`**

Create `backend/src/mnemonic/vault/extractors/highlight.py`:

```python
"""Highlight-cloze extractor.

Recognises `==text==`. All highlights blank together (one note = one card per spec §4.2).
"""

from __future__ import annotations

import re

from mnemonic.exceptions import InvalidCardSyntaxError
from mnemonic.vault.extractors.cloze import ExtractedCard

_HL_RE = re.compile(r"==([^=]+)==")


def extract_highlight(card_section_text: str) -> ExtractedCard:
    matches = list(_HL_RE.finditer(card_section_text))
    if not matches:
        raise InvalidCardSyntaxError(
            "Highlight extractor invoked but no ==text== markers found."
        )

    terms = [m.group(1) for m in matches]

    front_parts: list[str] = []
    last_end = 0
    for m in matches:
        front_parts.append(card_section_text[last_end : m.start()])
        front_parts.append("[...]")
        last_end = m.end()
    front_parts.append(card_section_text[last_end:])

    back_parts: list[str] = []
    last_end = 0
    for m in matches:
        back_parts.append(card_section_text[last_end : m.start()])
        back_parts.append(m.group(1))
        last_end = m.end()
    back_parts.append(card_section_text[last_end:])

    return ExtractedCard(
        syntax="highlight",
        front="".join(front_parts).strip(),
        back="".join(back_parts).strip(),
        cloze_terms=terms,
    )
```

- [ ] **Step 4: Implement `callout.py`**

Create `backend/src/mnemonic/vault/extractors/callout.py`:

```python
"""Callout-block extractor.

Recognises Obsidian callouts of the form:

    > [!card]
    > **Q:** ...
    > **A:** ...
"""

from __future__ import annotations

import re

from mnemonic.exceptions import InvalidCardSyntaxError
from mnemonic.vault.extractors.cloze import ExtractedCard

_CALLOUT_OPEN = re.compile(r"^>\s*\[!card\]\s*$", re.MULTILINE)
_BLOCKQUOTE_LINE = re.compile(r"^>\s?(.*)$")


def extract_callout(card_section_text: str) -> ExtractedCard:
    """Parse a card-callout into Q/A."""
    if not _CALLOUT_OPEN.search(card_section_text):
        raise InvalidCardSyntaxError("Callout extractor invoked but no `> [!card]` block found.")

    lines = card_section_text.splitlines()
    inside = False
    body_lines: list[str] = []
    for line in lines:
        if _CALLOUT_OPEN.match(line):
            inside = True
            continue
        if inside:
            m = _BLOCKQUOTE_LINE.match(line)
            if not m:
                break
            body_lines.append(m.group(1))

    body = "\n".join(body_lines).strip()
    q_marker = "**Q:**"
    a_marker = "**A:**"
    if q_marker not in body or a_marker not in body:
        raise InvalidCardSyntaxError(
            "Callout block must contain both **Q:** and **A:** markers."
        )

    q_idx = body.index(q_marker) + len(q_marker)
    a_idx = body.index(a_marker)
    if a_idx < q_idx:
        raise InvalidCardSyntaxError("**A:** must follow **Q:** in a card callout.")

    front = body[q_idx:a_idx].strip()
    back = body[a_idx + len(a_marker) :].strip()

    if not front or not back:
        raise InvalidCardSyntaxError("Callout has empty Q or A.")

    return ExtractedCard(syntax="callout", front=front, back=back, cloze_terms=[])
```

- [ ] **Step 5: Update extractors `__init__.py`**

Replace `backend/src/mnemonic/vault/extractors/__init__.py`:

```python
from mnemonic.vault.extractors.callout import extract_callout
from mnemonic.vault.extractors.cloze import ExtractedCard, extract_cloze
from mnemonic.vault.extractors.highlight import extract_highlight

__all__ = ["ExtractedCard", "extract_cloze", "extract_highlight", "extract_callout"]
```

- [ ] **Step 6: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_extractors.py -v`
Expected: 10 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/mnemonic/vault/extractors/ backend/tests/unit/vault/test_extractors.py
git commit -m "feat(vault): highlight and callout extractors"
```

---

### Task 7: Extractor dispatcher (auto-detect syntax)

**Files:**
- Modify: `backend/src/mnemonic/vault/extractors/__init__.py`
- Modify: `backend/tests/unit/vault/test_extractors.py`

- [ ] **Step 1: Add failing test**

Append to `backend/tests/unit/vault/test_extractors.py`:

```python
from mnemonic.vault.extractors import extract_card


def test_dispatcher_picks_cloze():
    card = extract_card("A {{c1::NE}} is stable.")
    assert card.syntax == "cloze"


def test_dispatcher_picks_highlight():
    card = extract_card("A ==NE== is stable.")
    assert card.syntax == "highlight"


def test_dispatcher_picks_callout():
    card = extract_card("> [!card]\n> **Q:** q?\n> **A:** a.")
    assert card.syntax == "callout"


def test_dispatcher_mixed_syntax_raises():
    with pytest.raises(InvalidCardSyntaxError):
        extract_card("A {{c1::NE}} is ==stable==.")


def test_dispatcher_no_syntax_raises():
    with pytest.raises(InvalidCardSyntaxError):
        extract_card("plain text")
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/vault/test_extractors.py -v`
Expected: ImportError on `extract_card`.

- [ ] **Step 3: Implement dispatcher**

Replace `backend/src/mnemonic/vault/extractors/__init__.py`:

```python
"""Card-marker extractors with syntax auto-detection."""

from __future__ import annotations

import re

from mnemonic.exceptions import InvalidCardSyntaxError
from mnemonic.vault.extractors.callout import extract_callout
from mnemonic.vault.extractors.cloze import ExtractedCard, extract_cloze
from mnemonic.vault.extractors.highlight import extract_highlight

__all__ = ["ExtractedCard", "extract_card", "extract_cloze", "extract_highlight", "extract_callout"]

_CLOZE_HINT = re.compile(r"\{\{c\d+::")
_HIGHLIGHT_HINT = re.compile(r"==[^=]+==")
_CALLOUT_HINT = re.compile(r"^>\s*\[!card\]", re.MULTILINE)


def extract_card(card_section_text: str) -> ExtractedCard:
    """Detect which syntax is used and dispatch to the correct extractor.

    Raises InvalidCardSyntaxError if zero or more than one syntax is present.
    """
    has_cloze = bool(_CLOZE_HINT.search(card_section_text))
    has_hl = bool(_HIGHLIGHT_HINT.search(card_section_text))
    has_callout = bool(_CALLOUT_HINT.search(card_section_text))

    syntaxes = sum([has_cloze, has_hl, has_callout])
    if syntaxes == 0:
        raise InvalidCardSyntaxError(
            "No supported card syntax detected. Use {{cN::...}}, ==text==, or > [!card]."
        )
    if syntaxes > 1:
        present = [n for n, p in (("cloze", has_cloze), ("highlight", has_hl), ("callout", has_callout)) if p]
        raise InvalidCardSyntaxError(
            f"Mixed card syntaxes in one note: {present}. A note must use exactly one."
        )

    if has_cloze:
        return extract_cloze(card_section_text)
    if has_hl:
        return extract_highlight(card_section_text)
    return extract_callout(card_section_text)
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_extractors.py -v`
Expected: 15 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/extractors/__init__.py backend/tests/unit/vault/test_extractors.py
git commit -m "feat(vault): syntax auto-detection dispatcher for extractors"
```

---

## Wave 3: Vault writes (injector) and deck resolver

### Task 8: Atomic write helper + block-ID injector

**Files:**
- Create: `backend/src/mnemonic/vault/_atomic.py`
- Create: `backend/src/mnemonic/vault/injector.py`
- Create: `backend/tests/unit/vault/test_injector.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/vault/test_injector.py`:

```python
import re
from pathlib import Path
import pytest
from mnemonic.vault.injector import inject_block_id, ensure_variations_section, append_variation_entry
from mnemonic.vault.note import BLOCK_ID_RE
from mnemonic.exceptions import MalformedNoteError, MalformedVariationSectionError


def _read(p: Path) -> str:
    return p.read_text()


def test_inject_block_id_appends_to_card_paragraph(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA {{c1::NE}} is stable.\n\n## Context\n\nfoo\n"
    )
    cid = inject_block_id(note)
    text = _read(note)
    assert BLOCK_ID_RE.search(text)
    assert cid.startswith("card-")
    assert len(cid) == len("card-") + 8


def test_inject_block_id_idempotent_when_already_present(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA ==NE== is stable. ^card-aaaabbbb\n"
    )
    cid = inject_block_id(note)
    assert cid == "card-aaaabbbb"
    assert _read(note).count("^card-aaaabbbb") == 1


def test_inject_raises_when_no_card_section(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text("---\ntitle: t\n---\n\nno card here\n")
    with pytest.raises(MalformedNoteError):
        inject_block_id(note)


def test_ensure_variations_section_creates_when_absent(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA ==NE==. ^card-aaaabbbb\n"
    )
    ensure_variations_section(note)
    text = _read(note)
    assert "## Variations" in text
    assert "<!-- mnemonic:variations:begin -->" in text
    assert "<!-- mnemonic:variations:end -->" in text


def test_append_variation_entry_inserts_before_end_marker(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA ==NE==. ^card-aaaabbbb\n\n"
        "## Variations\n\n<!-- mnemonic:variations:begin -->\n<!-- mnemonic:variations:end -->\n"
    )
    append_variation_entry(
        note,
        date_str="2026-05-10",
        question="When is X?",
        answer="When Y.",
    )
    text = _read(note)
    assert "### 2026-05-10 (rating: pending)" in text
    assert text.index("### 2026-05-10") < text.index("<!-- mnemonic:variations:end -->")


def test_append_variation_entry_raises_if_markers_missing(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA. ^card-aaaabbbb\n\n## Variations\n\n### 2026-04-01\nfoo\n"
    )
    with pytest.raises(MalformedVariationSectionError):
        append_variation_entry(note, "2026-05-10", "q", "a")
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/vault/test_injector.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement atomic write helper**

Create `backend/src/mnemonic/vault/_atomic.py`:

```python
"""Atomic file write helper. Used everywhere Mnemonic touches the vault."""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
```

- [ ] **Step 4: Implement injector**

Create `backend/src/mnemonic/vault/injector.py`:

```python
"""Mnemonic-managed writes to vault notes.

Two operations:
  - inject_block_id(note_path) → str: append ^card-xyz at end of `## Card` if missing.
  - ensure_variations_section(note_path): add an empty ## Variations stub.
  - append_variation_entry(note_path, date, q, a): insert a pending entry before :end marker.
  - update_variation_rating(note_path, date, rating): change "(rating: pending)" → "(rating: N)".

All writes are atomic via _atomic.atomic_write_text.
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from mnemonic.exceptions import MalformedNoteError, MalformedVariationSectionError
from mnemonic.vault._atomic import atomic_write_text
from mnemonic.vault.note import BLOCK_ID_RE, VAR_BEGIN, VAR_END, parse_note


def _new_block_id() -> str:
    return f"card-{secrets.token_hex(4)}"


def inject_block_id(note_path: Path) -> str:
    """Append a block ID to the `## Card` section if missing. Returns the ID."""
    text = note_path.read_text()
    note = parse_note(text)
    if note.card_section is None:
        raise MalformedNoteError(
            f"Cannot inject block ID: {note_path} has no ## Card section."
        )
    if note.block_id is not None:
        return note.block_id

    card_section = note.card_section
    new_block_id = _new_block_id()
    # Append " ^<id>" to the end of the last non-blank line of the card section.
    lines = card_section.splitlines()
    last_nonblank = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip()), None)
    if last_nonblank is None:
        raise MalformedNoteError("## Card section is empty.")
    lines[last_nonblank] = lines[last_nonblank].rstrip() + f" ^{new_block_id}"
    new_card = "\n".join(lines)

    new_text = text.replace(card_section, new_card, 1)
    atomic_write_text(note_path, new_text)
    return new_block_id


def ensure_variations_section(note_path: Path) -> None:
    """Append an empty `## Variations` section with markers if not present."""
    text = note_path.read_text()
    note = parse_note(text)
    if note.variations_section is not None:
        if VAR_BEGIN not in note.variations_section or VAR_END not in note.variations_section:
            raise MalformedVariationSectionError(
                f"## Variations section in {note_path} is missing markers."
            )
        return
    new_block = (
        "\n## Variations\n\n"
        f"{VAR_BEGIN}\n"
        f"{VAR_END}\n"
    )
    new_text = text.rstrip() + "\n" + new_block
    atomic_write_text(note_path, new_text)


def append_variation_entry(
    note_path: Path, date_str: str, question: str, answer: str
) -> None:
    """Insert a pending variation entry before the :end marker."""
    text = note_path.read_text()
    if VAR_BEGIN not in text or VAR_END not in text:
        raise MalformedVariationSectionError(
            f"{note_path} has no ## Variations markers; call ensure_variations_section first."
        )
    entry = (
        f"### {date_str} (rating: pending)\n"
        f"**Q:** {question}\n"
        f"**A:** {answer}\n\n"
    )
    new_text = text.replace(VAR_END, entry + VAR_END, 1)
    atomic_write_text(note_path, new_text)


def update_variation_rating(note_path: Path, date_str: str, rating: int) -> None:
    """Change the most recent `(rating: pending)` entry for date_str to (rating: N)."""
    text = note_path.read_text()
    pat = re.compile(rf"### {re.escape(date_str)} \(rating: pending\)")
    new_text, count = pat.subn(f"### {date_str} (rating: {rating})", text, count=1)
    if count == 0:
        raise MalformedVariationSectionError(
            f"No pending entry found for {date_str} in {note_path}."
        )
    atomic_write_text(note_path, new_text)
```

- [ ] **Step 5: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_injector.py -v`
Expected: 6 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/mnemonic/vault/_atomic.py backend/src/mnemonic/vault/injector.py backend/tests/unit/vault/test_injector.py
git commit -m "feat(vault): atomic block-ID and variation-section writers"
```

---

### Task 9: Deck resolver (folder + _deck.md)

**Files:**
- Create: `backend/src/mnemonic/vault/deck.py`
- Create: `backend/tests/unit/vault/test_deck.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/vault/test_deck.py`:

```python
from pathlib import Path
from mnemonic.vault.deck import resolve_deck_for_note, parse_deck_config, DeckConfig


def test_parse_deck_config(tmp_path: Path):
    deck_md = tmp_path / "_deck.md"
    deck_md.write_text(
        "---\n"
        "deck_name: Game Theory\n"
        "variation_enabled: true\n"
        "variation_frequency: 0.6\n"
        "leech_threshold: 8\n"
        "daily_review_limit: 50\n"
        "daily_new_limit: 10\n"
        "---\n\nfree-form\n"
    )
    cfg = parse_deck_config(deck_md)
    assert cfg.deck_name == "Game Theory"
    assert cfg.variation_frequency == 0.6


def test_resolve_deck_uses_folder_path(tmp_path: Path):
    vault = tmp_path / "vault"
    folder = vault / "01_Projects" / "game-theory"
    folder.mkdir(parents=True)
    note = folder / "nash.qmd"
    note.write_text("---\ntitle: t\n---\n## Card\n\nA ==NE==. ^card-11112222\n")

    deck_path, cfg = resolve_deck_for_note(note, vault_root=vault)
    assert deck_path == folder
    assert cfg is None  # no _deck.md present


def test_resolve_deck_inherits_from_parent(tmp_path: Path):
    vault = tmp_path / "vault"
    parent = vault / "01_Projects"
    parent.mkdir(parents=True)
    (parent / "_deck.md").write_text(
        "---\ndeck_name: Projects\nvariation_enabled: true\nvariation_frequency: 0.5\n"
        "leech_threshold: 8\ndaily_review_limit: 50\ndaily_new_limit: 10\n---\n"
    )
    child = parent / "game-theory"
    child.mkdir()
    note = child / "nash.qmd"
    note.write_text("---\ntitle: t\n---\n## Card\n\nA ==NE==. ^card-11112222\n")

    deck_path, cfg = resolve_deck_for_note(note, vault_root=vault)
    assert deck_path == child
    assert cfg.deck_name == "Projects"  # inherited
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/vault/test_deck.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement deck resolver**

Create `backend/src/mnemonic/vault/deck.py`:

```python
"""Deck resolution: folder = deck. Optional `_deck.md` provides per-folder config."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from mnemonic.exceptions import MalformedNoteError

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class DeckConfig:
    deck_name: str
    variation_enabled: bool
    variation_frequency: float
    leech_threshold: int
    daily_review_limit: int
    daily_new_limit: int


def parse_deck_config(deck_md_path: Path) -> DeckConfig:
    """Parse a `_deck.md` file's frontmatter into a DeckConfig."""
    text = deck_md_path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise MalformedNoteError(f"{deck_md_path} has no YAML frontmatter.")
    fm = yaml.safe_load(m.group(1)) or {}
    required = (
        "deck_name",
        "variation_enabled",
        "variation_frequency",
        "leech_threshold",
        "daily_review_limit",
        "daily_new_limit",
    )
    missing = [k for k in required if k not in fm]
    if missing:
        raise MalformedNoteError(
            f"{deck_md_path} _deck.md missing required keys: {missing}."
        )
    return DeckConfig(
        deck_name=str(fm["deck_name"]),
        variation_enabled=bool(fm["variation_enabled"]),
        variation_frequency=float(fm["variation_frequency"]),
        leech_threshold=int(fm["leech_threshold"]),
        daily_review_limit=int(fm["daily_review_limit"]),
        daily_new_limit=int(fm["daily_new_limit"]),
    )


def resolve_deck_for_note(
    note_path: Path, *, vault_root: Path
) -> tuple[Path, DeckConfig | None]:
    """Return (deck_folder, deck_config_or_None_if_no_deck.md_in_chain).

    Walks upward from the note's folder until vault_root, returning the first
    `_deck.md` config found. Deck folder is always the note's immediate parent.
    """
    deck_folder = note_path.parent
    cur = deck_folder
    while True:
        candidate = cur / "_deck.md"
        if candidate.exists():
            return (deck_folder, parse_deck_config(candidate))
        if cur == vault_root or cur.parent == cur:
            return (deck_folder, None)
        cur = cur.parent
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_deck.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/deck.py backend/tests/unit/vault/test_deck.py
git commit -m "feat(vault): folder-based deck resolver with _deck.md inheritance"
```

---

### Task 10: Vault scanner (walks vault, emits Cards)

**Files:**
- Create: `backend/src/mnemonic/vault/scanner.py`
- Create: `backend/tests/unit/vault/test_scanner.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/vault/test_scanner.py`:

```python
from pathlib import Path
from mnemonic.vault.scanner import scan_vault, ScannedCard


def _make_note(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_scan_emits_one_card_per_card_note(tmp_path: Path):
    vault = tmp_path / "vault"
    _make_note(
        vault / "01_Projects" / "game-theory" / "nash.qmd",
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::NE}} is stable. ^card-11112222\n",
    )
    _make_note(
        vault / "01_Projects" / "game-theory" / "minimax.qmd",
        "---\ntitle: minimax\n---\n## Card\n\nA ==minimax==. ^card-33334444\n",
    )
    cards = list(scan_vault(vault))
    assert len(cards) == 2
    ids = {c.card_id for c in cards}
    assert ids == {"card-11112222", "card-33334444"}
    syntaxes = {c.syntax for c in cards}
    assert syntaxes == {"cloze", "highlight"}


def test_scan_skips_non_card_notes(tmp_path: Path):
    vault = tmp_path / "vault"
    _make_note(vault / "01_Projects" / "regular-note.md", "no card section here")
    cards = list(scan_vault(vault))
    assert cards == []


def test_scan_injects_block_ids_when_missing(tmp_path: Path):
    vault = tmp_path / "vault"
    note = vault / "01_Projects" / "no-id.qmd"
    _make_note(note, "---\ntitle: x\n---\n## Card\n\nA ==NE==.\n")
    cards = list(scan_vault(vault, inject_missing_ids=True))
    assert len(cards) == 1
    assert cards[0].card_id.startswith("card-")
    assert "^card-" in note.read_text()


def test_scan_skips_mnemonic_folder(tmp_path: Path):
    vault = tmp_path / "vault"
    _make_note(vault / ".mnemonic" / "should-not-scan.md", "## Card\n\nA ==X==.")
    cards = list(scan_vault(vault, inject_missing_ids=False))
    assert cards == []
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/vault/test_scanner.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement scanner**

Create `backend/src/mnemonic/vault/scanner.py`:

```python
"""Vault scanner.

Walks the vault, finds card-notes, extracts cards, optionally injects missing
block IDs. Emits ScannedCard objects (pure data — no SQLite involvement).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from mnemonic.exceptions import InvalidCardSyntaxError, MalformedNoteError
from mnemonic.vault.deck import DeckConfig, resolve_deck_for_note
from mnemonic.vault.extractors import ExtractedCard, extract_card
from mnemonic.vault.injector import inject_block_id
from mnemonic.vault.note import parse_note

NOTE_SUFFIXES = (".md", ".qmd")
SKIP_DIRS = {".mnemonic", ".obsidian", ".git", "_build", "node_modules"}


@dataclass(frozen=True)
class ScannedCard:
    card_id: str
    note_path: Path
    deck_folder: Path
    deck_config: DeckConfig | None
    syntax: str
    front: str
    back: str
    title: str
    frontmatter: dict


def _iter_notes(vault_root: Path) -> Iterator[Path]:
    for path in vault_root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix not in NOTE_SUFFIXES:
            continue
        rel = path.relative_to(vault_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name.startswith("_deck"):
            continue
        yield path


def scan_vault(
    vault_root: Path, *, inject_missing_ids: bool = True
) -> Iterator[ScannedCard]:
    """Walk vault and emit ScannedCard objects for every card-note."""
    for note_path in _iter_notes(vault_root):
        try:
            note = parse_note(note_path.read_text())
        except MalformedNoteError:
            # Surface but continue. Loud failures handled by session orchestrator.
            raise
        if not note.is_card_note:
            continue

        if note.block_id is None:
            if not inject_missing_ids:
                continue
            block_id = inject_block_id(note_path)
            note = parse_note(note_path.read_text())
        else:
            block_id = note.block_id

        try:
            extracted: ExtractedCard = extract_card(note.card_section or "")
        except InvalidCardSyntaxError:
            raise

        deck_folder, deck_cfg = resolve_deck_for_note(note_path, vault_root=vault_root)

        yield ScannedCard(
            card_id=block_id,
            note_path=note_path,
            deck_folder=deck_folder,
            deck_config=deck_cfg,
            syntax=extracted.syntax,
            front=extracted.front,
            back=extracted.back,
            title=str(note.frontmatter.get("title", "")),
            frontmatter=note.frontmatter,
        )
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_scanner.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/scanner.py backend/tests/unit/vault/test_scanner.py
git commit -m "feat(vault): scanner walks vault and emits ScannedCard objects"
```

---

## Wave 4: SQLite models & Alembic migration

### Task 11: New SQLite models

**Files:**
- Create: `backend/src/mnemonic/db/models/scheduling_state.py`
- Create: `backend/src/mnemonic/db/models/variation_meta.py`
- Modify: `backend/src/mnemonic/db/models/review_log.py` (rewrite for SQLite + remove user_id)
- Modify: `backend/src/mnemonic/db/models/llm_usage.py` (rewrite for SQLite)
- Modify: `backend/src/mnemonic/db/models/training_example.py` (rewrite for SQLite)
- Modify: `backend/src/mnemonic/db/models/__init__.py`
- Create: `backend/tests/unit/db/test_models_v2.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/db/test_models_v2.py`:

```python
from datetime import datetime
from pathlib import Path
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.db.models import Base, SchedulingState, ReviewLog, VariationMeta, LLMUsage, TrainingExample


def test_scheduling_state_round_trip(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(SchedulingState(
            card_id="card-aaaabbbb",
            state="new",
            stability=0.0,
            difficulty=5.0,
            reps=0,
            lapses=0,
            leech_score=0.0,
        ))
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.state == "new"
        assert row.stability == 0.0


def test_review_log_no_user_id(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(ReviewLog(
            id="r1",
            card_id="card-aaaabbbb",
            rating=3,
            response_time_ms=1200,
            review_time=datetime(2026, 5, 10, 12, 0, 0),
        ))
    with session_scope(engine) as s:
        row = s.get(ReviewLog, "r1")
        assert row.rating == 3
        assert not hasattr(row, "user_id")


def test_variation_meta_minimal(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(VariationMeta(
            id="v1",
            card_id="card-aaaabbbb",
            strategy="rephrase",
            model="claude-haiku-4-5",
            generated_at=datetime(2026, 5, 10),
            content_hash="abc",
            note_path="01_Projects/x.qmd",
        ))
    with session_scope(engine) as s:
        row = s.get(VariationMeta, "v1")
        assert row.strategy == "rephrase"
        assert row.shown_count == 0
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/db/test_models_v2.py -v`
Expected: ImportError (SchedulingState, VariationMeta) or wrong fields on existing models.

- [ ] **Step 3: Inspect existing Base**

Run: `cat backend/src/mnemonic/db/models/base.py`
Expected: see `Base = declarative_base()` or similar. If it imports from postgresql dialect, note and adjust.

- [ ] **Step 4: Rewrite Base for SQLite**

Replace `backend/src/mnemonic/db/models/base.py`:

```python
"""SQLAlchemy declarative base for Mnemonic SQLite models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for all SQLite-backed ORM models."""

    pass
```

- [ ] **Step 5: Create `scheduling_state.py`**

Create `backend/src/mnemonic/db/models/scheduling_state.py`:

```python
"""SchedulingState model: FSRS state per card-block-id."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class SchedulingState(Base):
    __tablename__ = "scheduling_state"

    card_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="new")
    stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leech_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    leech_notified: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    suspended: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    parent_card_id: Mapped[str | None] = mapped_column(String, nullable=True)
    orphan: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
```

- [ ] **Step 6: Create `variation_meta.py`**

Create `backend/src/mnemonic/db/models/variation_meta.py`:

```python
"""VariationMeta: metadata for an LLM-generated variation written to a note."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class VariationMeta(Base):
    __tablename__ = "variation_meta"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    shown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    note_path: Mapped[str] = mapped_column(String, nullable=False)
```

- [ ] **Step 7: Rewrite `review_log.py` for SQLite (no user_id)**

Replace `backend/src/mnemonic/db/models/review_log.py`:

```python
"""ReviewLog: append-only record of every card review."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class ReviewLog(Base):
    __tablename__ = "review_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    review_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    state_before: Mapped[str | None] = mapped_column(String, nullable=True)
    state_after: Mapped[str | None] = mapped_column(String, nullable=True)
    stability_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    variation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_helpful: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 8: Rewrite `llm_usage.py` and `training_example.py`**

Replace `backend/src/mnemonic/db/models/llm_usage.py`:

```python
"""LLMUsage: per-call telemetry for cost/cache tracking."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_millicents: Mapped[int] = mapped_column(Integer, nullable=False)
    card_id: Mapped[str | None] = mapped_column(String, nullable=True)
```

Replace `backend/src/mnemonic/db/models/training_example.py`:

```python
"""TrainingExample: labelled variation outputs used for DSPy optimisation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class TrainingExample(Base):
    __tablename__ = "training_example"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False)
    variation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    base_q: Mapped[str] = mapped_column(Text, nullable=False)
    base_a: Mapped[str] = mapped_column(Text, nullable=False)
    variation_q: Mapped[str] = mapped_column(Text, nullable=False)
    variation_a: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

- [ ] **Step 9: Update models `__init__.py`**

Replace `backend/src/mnemonic/db/models/__init__.py`:

```python
"""SQLite ORM models for Mnemonic application state."""

from mnemonic.db.models.base import Base
from mnemonic.db.models.llm_usage import LLMUsage
from mnemonic.db.models.review_log import ReviewLog
from mnemonic.db.models.scheduling_state import SchedulingState
from mnemonic.db.models.training_example import TrainingExample
from mnemonic.db.models.variation_meta import VariationMeta

__all__ = [
    "Base",
    "LLMUsage",
    "ReviewLog",
    "SchedulingState",
    "TrainingExample",
    "VariationMeta",
]
```

- [ ] **Step 10: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/db/test_models_v2.py -v`
Expected: 3 PASS.

- [ ] **Step 11: Commit**

```bash
git add backend/src/mnemonic/db/models/ backend/tests/unit/db/test_models_v2.py
git commit -m "feat(db): SQLite models (scheduling_state, variation_meta, review_log, llm_usage, training_example)"
```

---

### Task 12: Alembic migration targeting SQLite

**Files:**
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_sqlite_schema.py`

- [ ] **Step 1: Inspect current alembic env**

Run: `cat backend/alembic/env.py`
Expected: see how it loads target_metadata and the URL.

- [ ] **Step 2: Rewrite `alembic/env.py`**

Replace `backend/alembic/env.py`:

```python
"""Alembic env for Mnemonic SQLite state DB."""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from mnemonic.config import load_config
from mnemonic.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sqlite_url() -> str:
    cfg = load_config()
    db_path = cfg.vault.path / ".mnemonic" / "state.sqlite"
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    url = _sqlite_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config_section = config.get_section(config.config_ini_section) or {}
    config_section["sqlalchemy.url"] = _sqlite_url()
    connectable = engine_from_config(config_section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Create initial migration**

Create `backend/alembic/versions/0001_initial_sqlite_schema.py`:

```python
"""Initial SQLite schema for Mnemonic vault-backed storage.

Revision ID: 0001_initial_sqlite_schema
Revises:
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_sqlite_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduling_state",
        sa.Column("card_id", sa.String, primary_key=True),
        sa.Column("state", sa.String, nullable=False, server_default="new"),
        sa.Column("stability", sa.Float, nullable=False, server_default="0"),
        sa.Column("difficulty", sa.Float, nullable=False, server_default="5"),
        sa.Column("due", sa.DateTime, nullable=True),
        sa.Column("reps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("leech_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("leech_notified", sa.Integer, nullable=False, server_default="0"),
        sa.Column("suspended", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parent_card_id", sa.String, nullable=True),
        sa.Column("orphan", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_scheduling_due", "scheduling_state", ["due"])
    op.create_index("idx_scheduling_orphan", "scheduling_state", ["orphan"])
    op.create_index("idx_scheduling_suspended", "scheduling_state", ["suspended"])

    op.create_table(
        "review_log",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=False),
        sa.Column("review_time", sa.DateTime, nullable=False),
        sa.Column("state_before", sa.String, nullable=True),
        sa.Column("state_after", sa.String, nullable=True),
        sa.Column("stability_before", sa.Float, nullable=True),
        sa.Column("stability_after", sa.Float, nullable=True),
        sa.Column("difficulty_before", sa.Float, nullable=True),
        sa.Column("difficulty_after", sa.Float, nullable=True),
        sa.Column("variation_id", sa.String, nullable=True),
        sa.Column("variation_helpful", sa.Integer, nullable=True),
    )
    op.create_index("idx_review_card_time", "review_log", ["card_id", "review_time"])
    op.create_index("idx_review_time", "review_log", ["review_time"])

    op.create_table(
        "variation_meta",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("strategy", sa.String, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("generated_at", sa.DateTime, nullable=False),
        sa.Column("shown_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("helpful_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String, nullable=False),
        sa.Column("note_path", sa.String, nullable=False),
    )
    op.create_index("idx_variation_card_hash", "variation_meta", ["card_id", "content_hash"])
    op.create_index("idx_variation_card_time", "variation_meta", ["card_id", "generated_at"])

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("purpose", sa.String, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cache_read_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cache_creation_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_millicents", sa.Integer, nullable=False),
        sa.Column("card_id", sa.String, nullable=True),
    )
    op.create_index("idx_usage_timestamp", "llm_usage", ["timestamp"])
    op.create_index("idx_usage_card", "llm_usage", ["card_id"])

    op.create_table(
        "training_example",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("variation_id", sa.String, nullable=True),
        sa.Column("base_q", sa.Text, nullable=False),
        sa.Column("base_a", sa.Text, nullable=False),
        sa.Column("variation_q", sa.Text, nullable=False),
        sa.Column("variation_a", sa.Text, nullable=False),
        sa.Column("label", sa.Integer, nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("note_context", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_training_label", "training_example", ["label"])


def downgrade() -> None:
    op.drop_table("training_example")
    op.drop_table("llm_usage")
    op.drop_table("variation_meta")
    op.drop_table("review_log")
    op.drop_table("scheduling_state")
```

- [ ] **Step 4: Verify migration loads (smoke test)**

Note: a full run requires a configured vault. For now, smoke-test the import:

Run: `cd backend && uv run python -c "from alembic.config import Config; from alembic import command; print('alembic import ok')"`
Expected: prints "alembic import ok".

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/env.py backend/alembic/versions/0001_initial_sqlite_schema.py
git commit -m "feat(db): initial SQLite Alembic migration"
```

---

## Wave 5: Git operations and session lifecycle

### Task 13: Git ops module (subprocess-based)

**Files:**
- Create: `backend/src/mnemonic/vault/git_ops.py`
- Create: `backend/tests/integration/test_git_ops.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/integration/test_git_ops.py`:

```python
import subprocess
from pathlib import Path
import pytest
from mnemonic.vault import git_ops
from mnemonic.exceptions import GitDirtyWorkingTreeError, GitNonFastForwardError


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare", "--initial-branch=main"], bare)

    local = tmp_path / "local"
    local.mkdir()
    _run(["git", "init", "--initial-branch=main"], local)
    _run(["git", "config", "user.email", "t@t.t"], local)
    _run(["git", "config", "user.name", "t"], local)
    _run(["git", "remote", "add", "origin", str(bare)], local)
    (local / "x.md").write_text("hello")
    _run(["git", "add", "."], local)
    _run(["git", "commit", "-m", "init"], local)
    _run(["git", "push", "-u", "origin", "main"], local)
    return local


def test_working_tree_clean(repo: Path):
    assert git_ops.working_tree_clean(repo) is True
    (repo / "x.md").write_text("modified")
    assert git_ops.working_tree_clean(repo) is False


def test_commit_all_and_push(repo: Path):
    (repo / "new.md").write_text("new")
    sha = git_ops.commit_all(repo, "test commit")
    assert sha
    git_ops.push(repo)


def test_dirty_tree_raises_on_session_preflight(repo: Path):
    (repo / "x.md").write_text("dirty")
    with pytest.raises(GitDirtyWorkingTreeError):
        git_ops.assert_clean(repo)
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/integration/test_git_ops.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement git_ops**

Create `backend/src/mnemonic/vault/git_ops.py`:

```python
"""Subprocess-based Git operations. All raise domain exceptions on failure."""

from __future__ import annotations

import subprocess
from pathlib import Path

from mnemonic.exceptions import (
    GitDirtyWorkingTreeError,
    GitError,
    GitNonFastForwardError,
    GitPushRejectedError,
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_checked(cwd: Path, *args: str) -> str:
    result = _git(cwd, *args)
    if result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def clone(remote: str, dest: Path, branch: str = "main") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--branch", branch, remote, str(dest)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git clone {remote} failed: {result.stderr.strip()}")


def fetch(cwd: Path, remote: str = "origin") -> None:
    result = _git(cwd, "fetch", remote)
    if result.returncode != 0:
        raise GitError(f"git fetch failed: {result.stderr.strip()}")


def working_tree_clean(cwd: Path) -> bool:
    out = _git_checked(cwd, "status", "--porcelain")
    return out.strip() == ""


def assert_clean(cwd: Path) -> None:
    if not working_tree_clean(cwd):
        raise GitDirtyWorkingTreeError(
            f"Vault at {cwd} has uncommitted changes. "
            "Commit or stash them in Obsidian/CLI before starting a Mnemonic session."
        )


def is_fast_forward(cwd: Path, ref: str = "origin/main") -> bool:
    head = _git_checked(cwd, "rev-parse", "HEAD").strip()
    remote = _git_checked(cwd, "rev-parse", ref).strip()
    if head == remote:
        return True
    merge_base = _git_checked(cwd, "merge-base", head, remote).strip()
    return merge_base == head


def fast_forward_pull(cwd: Path, remote: str = "origin", branch: str = "main") -> None:
    if not is_fast_forward(cwd, f"{remote}/{branch}"):
        raise GitNonFastForwardError(
            f"Remote {remote}/{branch} has diverged from local. "
            "Reconcile manually in your editor or with `git pull --rebase`."
        )
    result = _git(cwd, "merge", "--ff-only", f"{remote}/{branch}")
    if result.returncode != 0:
        raise GitError(f"fast-forward merge failed: {result.stderr.strip()}")


def commit_all(cwd: Path, message: str) -> str:
    _git_checked(cwd, "add", "-A")
    status = _git_checked(cwd, "status", "--porcelain")
    if status.strip() == "":
        return ""
    result = _git(cwd, "commit", "-m", message)
    if result.returncode != 0:
        raise GitError(f"git commit failed: {result.stderr.strip()}")
    return _git_checked(cwd, "rev-parse", "HEAD").strip()


def push(cwd: Path, remote: str = "origin", branch: str = "main") -> None:
    result = _git(cwd, "push", remote, branch)
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "rejected" in stderr or "non-fast-forward" in stderr:
            raise GitPushRejectedError(
                f"Push rejected by {remote}/{branch}: remote has newer commits. "
                "Run a fresh Mnemonic session or `git pull` to reconcile."
            )
        raise GitError(f"git push failed: {result.stderr.strip()}")


def has_unpushed_commits(cwd: Path, remote: str = "origin", branch: str = "main") -> bool:
    out = _git_checked(cwd, "log", f"{remote}/{branch}..HEAD", "--oneline")
    return out.strip() != ""
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/integration/test_git_ops.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/git_ops.py backend/tests/integration/test_git_ops.py
git commit -m "feat(vault): subprocess-based git_ops with FF-only pull and dirty-tree refusal"
```

---

### Task 14: Vault repository (joins scan + SQLite state)

**Files:**
- Create: `backend/src/mnemonic/vault/repository.py`
- Create: `backend/tests/unit/vault/test_repository.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/vault/test_repository.py`:

```python
from pathlib import Path
from mnemonic.db.models import Base, SchedulingState
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\n==NE==. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def test_list_cards_joins_with_state(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    with session_scope(engine) as s:
        s.add(SchedulingState(card_id="card-aaaabbbb", state="review",
                              stability=4.0, difficulty=6.0, reps=5, lapses=0, leech_score=0.0))
    repo = VaultRepository(vault_root=vault, engine=engine)
    cards = repo.list_cards()
    assert len(cards) == 1
    assert cards[0].card_id == "card-aaaabbbb"
    assert cards[0].state == "review"
    assert cards[0].stability == 4.0


def test_list_cards_new_state_default(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    cards = repo.list_cards()
    assert len(cards) == 1
    assert cards[0].state == "new"
    assert cards[0].stability == 0.0


def test_list_decks(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    decks = repo.list_decks()
    assert len(decks) == 1
    assert decks[0].folder.name == "gt"
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/vault/test_repository.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement repository**

Create `backend/src/mnemonic/vault/repository.py`:

```python
"""Vault repository: presents Card/Deck objects to the rest of the app.

Combines the read-side scan with SQLite scheduling state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.db.models import SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.vault.deck import DeckConfig
from mnemonic.vault.scanner import ScannedCard, scan_vault


@dataclass(frozen=True)
class Card:
    card_id: str
    note_path: Path
    deck_folder: Path
    syntax: str
    front: str
    back: str
    title: str
    state: str
    stability: float
    difficulty: float
    due: datetime | None
    reps: int
    lapses: int
    leech_score: float
    suspended: bool


@dataclass(frozen=True)
class Deck:
    folder: Path
    name: str
    config: DeckConfig | None


class VaultRepository:
    def __init__(self, vault_root: Path, engine: Engine):
        self.vault_root = vault_root
        self.engine = engine

    def _scan(self) -> list[ScannedCard]:
        return list(scan_vault(self.vault_root, inject_missing_ids=True))

    def list_cards(self) -> list[Card]:
        scanned = self._scan()
        ids = [c.card_id for c in scanned]
        with session_scope(self.engine) as s:
            rows = (
                s.query(SchedulingState).filter(SchedulingState.card_id.in_(ids)).all()
                if ids else []
            )
            by_id = {r.card_id: r for r in rows}
        out: list[Card] = []
        for sc in scanned:
            row = by_id.get(sc.card_id)
            out.append(
                Card(
                    card_id=sc.card_id,
                    note_path=sc.note_path,
                    deck_folder=sc.deck_folder,
                    syntax=sc.syntax,
                    front=sc.front,
                    back=sc.back,
                    title=sc.title,
                    state=row.state if row else "new",
                    stability=row.stability if row else 0.0,
                    difficulty=row.difficulty if row else 5.0,
                    due=row.due if row else None,
                    reps=row.reps if row else 0,
                    lapses=row.lapses if row else 0,
                    leech_score=row.leech_score if row else 0.0,
                    suspended=bool(row.suspended) if row else False,
                )
            )
        return out

    def list_decks(self) -> list[Deck]:
        seen: dict[Path, Deck] = {}
        for sc in self._scan():
            if sc.deck_folder not in seen:
                name = sc.deck_config.deck_name if sc.deck_config else sc.deck_folder.name
                seen[sc.deck_folder] = Deck(folder=sc.deck_folder, name=name, config=sc.deck_config)
        return list(seen.values())

    def get_card(self, card_id: str) -> Card | None:
        for c in self.list_cards():
            if c.card_id == card_id:
                return c
        return None
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/vault/test_repository.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/repository.py backend/tests/unit/vault/test_repository.py
git commit -m "feat(vault): VaultRepository joins scan with SchedulingState"
```

---

## Wave 6: LLM client (Anthropic SDK + Protocol)

### Task 15: LLM client Protocol + types

**Files:**
- Create: `backend/src/mnemonic/llm/exceptions.py` (re-exports + module-local)
- Create: `backend/src/mnemonic/llm/client.py`
- Create: `backend/tests/unit/llm/__init__.py`
- Create: `backend/tests/unit/llm/test_client_types.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/llm/test_client_types.py`:

```python
from mnemonic.llm.client import Block, Message, Completion, Usage, LLMClient
from typing import Protocol


def test_block_with_cache_control():
    b = Block(text="hello", cache_control={"type": "ephemeral"})
    assert b.text == "hello"
    assert b.cache_control == {"type": "ephemeral"}


def test_block_without_cache_control():
    b = Block(text="hi")
    assert b.cache_control is None


def test_completion_carries_usage():
    c = Completion(text="ok", usage=Usage(input_tokens=10, output_tokens=5,
                                          cache_read_tokens=0, cache_creation_tokens=0,
                                          cost_millicents=15))
    assert c.text == "ok"
    assert c.usage.cost_millicents == 15


def test_llm_client_is_protocol():
    assert issubclass(LLMClient, Protocol) or hasattr(LLMClient, "_is_protocol")
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/llm/test_client_types.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement client types**

Create `backend/src/mnemonic/llm/__init__.py` (empty).

Create `backend/src/mnemonic/llm/client.py`:

```python
"""LLM client Protocol and shared types.

Backends implement this Protocol. Only one backend exists in Phase 1
(Anthropic). The Protocol exists so we can slot in alternatives later
without rewriting consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class Block:
    """A single content block. Optional cache_control marks a cache breakpoint."""

    text: str
    cache_control: dict[str, Any] | None = None


@dataclass(frozen=True)
class Message:
    role: str  # "user" | "assistant"
    blocks: list[Block]


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_millicents: int


@dataclass(frozen=True)
class Completion:
    text: str
    usage: Usage
    model: str


@dataclass(frozen=True)
class BatchRequest:
    custom_id: str
    system: list[Block]
    messages: list[Message]
    max_tokens: int
    stop_sequences: Sequence[str] = ()


@dataclass(frozen=True)
class BatchHandle:
    batch_id: str


class LLMClient(Protocol):
    def generate(
        self,
        *,
        system: list[Block],
        messages: list[Message],
        model: str,
        max_tokens: int,
        stop_sequences: Sequence[str] = (),
    ) -> Completion: ...

    def submit_batch(self, requests: Sequence[BatchRequest], *, model: str) -> BatchHandle: ...
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/llm/test_client_types.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/llm/__init__.py backend/src/mnemonic/llm/client.py backend/tests/unit/llm/
git commit -m "feat(llm): client Protocol with Block/Message/Completion/Usage types"
```

---

### Task 16: Cache helper + budget guard + router

**Files:**
- Create: `backend/src/mnemonic/llm/cache.py`
- Create: `backend/src/mnemonic/llm/budget.py`
- Create: `backend/src/mnemonic/llm/router.py`
- Create: `backend/tests/unit/llm/test_cache.py`
- Create: `backend/tests/unit/llm/test_budget.py`
- Create: `backend/tests/unit/llm/test_router.py`

- [ ] **Step 1: Failing tests for cache**

Create `backend/tests/unit/llm/test_cache.py`:

```python
from mnemonic.llm.cache import build_cached_system, EPHEMERAL_1H, EPHEMERAL_5M
from mnemonic.llm.client import Block


def test_three_cached_blocks():
    blocks = build_cached_system(
        skill_md="SKILL CONTENT",
        strategy_md="STRATEGY",
        note_context="CTX",
    )
    assert len(blocks) == 3
    assert blocks[0].text == "SKILL CONTENT"
    assert blocks[0].cache_control == EPHEMERAL_1H
    assert blocks[1].cache_control == EPHEMERAL_1H
    assert blocks[2].cache_control == EPHEMERAL_5M


def test_no_more_than_four_breakpoints():
    blocks = build_cached_system(skill_md="x", strategy_md="y", note_context="z")
    cached = [b for b in blocks if b.cache_control is not None]
    assert len(cached) <= 4
```

- [ ] **Step 2: Failing tests for budget**

Create `backend/tests/unit/llm/test_budget.py`:

```python
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from mnemonic.db.models import Base, LLMUsage
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.exceptions import LLMBudgetExceededError
from mnemonic.llm.budget import BudgetGuard


def _seed(engine, ts: datetime, cost: int):
    with session_scope(engine) as s:
        s.add(LLMUsage(
            id=f"u-{ts.isoformat()}", timestamp=ts, model="m", purpose="p",
            input_tokens=0, output_tokens=0, cost_millicents=cost,
        ))


def test_under_budget_allows(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    guard = BudgetGuard(engine=engine, daily_cents=25, monthly_cents=500)
    guard.assert_within_budget()  # no rows; passes


def test_over_daily_raises(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    _seed(engine, datetime.now(), 26_000)  # 26 cents = 26_000 millicents
    guard = BudgetGuard(engine=engine, daily_cents=25, monthly_cents=500)
    with pytest.raises(LLMBudgetExceededError) as ei:
        guard.assert_within_budget()
    assert ei.value.scope == "daily"


def test_over_monthly_raises(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    # Add usage on prior days totaling > monthly cap (but <= daily on any day)
    for i in range(1, 25):
        _seed(engine, datetime.now() - timedelta(days=i), 21_000)
    guard = BudgetGuard(engine=engine, daily_cents=25, monthly_cents=500)
    with pytest.raises(LLMBudgetExceededError) as ei:
        guard.assert_within_budget()
    assert ei.value.scope == "monthly"
```

- [ ] **Step 3: Failing tests for router**

Create `backend/tests/unit/llm/test_router.py`:

```python
from mnemonic.llm.router import pick_model


def test_rephrase_uses_haiku():
    assert pick_model(strategy="rephrase", recent_failures=0,
                      model_default="claude-sonnet-4-6",
                      model_rephrase="claude-haiku-4-5") == "claude-haiku-4-5"


def test_specialize_uses_default():
    assert pick_model(strategy="specialize", recent_failures=0,
                      model_default="claude-sonnet-4-6",
                      model_rephrase="claude-haiku-4-5") == "claude-sonnet-4-6"


def test_many_recent_failures_force_default():
    assert pick_model(strategy="rephrase", recent_failures=4,
                      model_default="claude-sonnet-4-6",
                      model_rephrase="claude-haiku-4-5") == "claude-sonnet-4-6"
```

- [ ] **Step 4: Implement cache.py**

Create `backend/src/mnemonic/llm/cache.py`:

```python
"""Build cache_control blocks for the variation prompt."""

from __future__ import annotations

from mnemonic.llm.client import Block

EPHEMERAL_1H = {"type": "ephemeral", "ttl": "1h"}
EPHEMERAL_5M = {"type": "ephemeral"}


def build_cached_system(*, skill_md: str, strategy_md: str, note_context: str) -> list[Block]:
    """Return system blocks ordered SKILL → strategy → context, each with cache_control."""
    return [
        Block(text=skill_md, cache_control=EPHEMERAL_1H),
        Block(text=strategy_md, cache_control=EPHEMERAL_1H),
        Block(text=note_context, cache_control=EPHEMERAL_5M),
    ]
```

- [ ] **Step 5: Implement budget.py**

Create `backend/src/mnemonic/llm/budget.py`:

```python
"""Daily/monthly LLM cost cap. Reads aggregates from LLMUsage rows."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine, func

from mnemonic.db.models import LLMUsage
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import LLMBudgetExceededError


class BudgetGuard:
    def __init__(self, *, engine: Engine, daily_cents: int, monthly_cents: int):
        self.engine = engine
        self.daily_millicents = daily_cents * 1000
        self.monthly_millicents = monthly_cents * 1000

    def _sum_since(self, since: datetime) -> int:
        with session_scope(self.engine) as s:
            total = s.query(func.coalesce(func.sum(LLMUsage.cost_millicents), 0)).filter(
                LLMUsage.timestamp >= since
            ).scalar()
            return int(total or 0)

    def assert_within_budget(self) -> None:
        now = datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = day_start - timedelta(days=30)

        daily_spent = self._sum_since(day_start)
        if daily_spent >= self.daily_millicents:
            raise LLMBudgetExceededError(
                spent_millicents=daily_spent,
                cap_millicents=self.daily_millicents,
                scope="daily",
            )

        monthly_spent = self._sum_since(month_start)
        if monthly_spent >= self.monthly_millicents:
            raise LLMBudgetExceededError(
                spent_millicents=monthly_spent,
                cap_millicents=self.monthly_millicents,
                scope="monthly",
            )
```

- [ ] **Step 6: Implement router.py**

Create `backend/src/mnemonic/llm/router.py`:

```python
"""Pick which model to use for a given strategy + FSRS context."""

from __future__ import annotations


def pick_model(
    *,
    strategy: str,
    recent_failures: int,
    model_default: str,
    model_rephrase: str,
) -> str:
    """Return the model string to use.

    Rules (per spec §6.3):
      - Strategy == "rephrase" → model_rephrase (Haiku-tier)
      - Otherwise → model_default (Sonnet-tier)
      - If recent_failures > 3 → force model_default regardless of strategy
    """
    if recent_failures > 3:
        return model_default
    if strategy == "rephrase":
        return model_rephrase
    return model_default
```

- [ ] **Step 7: Run all three test files; verify pass**

Run: `cd backend && uv run pytest tests/unit/llm/ -v`
Expected: 9 PASS (4 client types + 2 cache + 3 budget + 3 router; 12 total — count both subdirs).

- [ ] **Step 8: Commit**

```bash
git add backend/src/mnemonic/llm/{cache,budget,router}.py backend/tests/unit/llm/
git commit -m "feat(llm): cache builder, budget guard, model-tier router"
```

---

### Task 17: Anthropic backend

**Files:**
- Create: `backend/src/mnemonic/llm/backends/__init__.py` (empty)
- Create: `backend/src/mnemonic/llm/backends/anthropic.py`
- Create: `backend/tests/unit/llm/test_anthropic_backend.py`

- [ ] **Step 1: Failing test (with mocked SDK)**

Create `backend/tests/unit/llm/test_anthropic_backend.py`:

```python
import os
from unittest.mock import MagicMock, patch
import pytest
from mnemonic.llm.backends.anthropic import AnthropicBackend, PRICE_TABLE
from mnemonic.llm.client import Block, Message
from mnemonic.exceptions import LLMConfigError, LLMRateLimitError, LLMError


def _mock_message(input_tokens=100, output_tokens=50, cache_read=10, cache_creation=5):
    m = MagicMock()
    m.content = [MagicMock(text="result")]
    m.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_creation,
    )
    return m


def test_generate_success(monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_message()
    monkeypatch.setattr("mnemonic.llm.backends.anthropic._make_sdk_client", lambda key: fake_client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    backend = AnthropicBackend(api_key_env="ANTHROPIC_API_KEY")
    completion = backend.generate(
        system=[Block(text="sys")],
        messages=[Message(role="user", blocks=[Block(text="hi")])],
        model="claude-haiku-4-5",
        max_tokens=200,
    )
    assert completion.text == "result"
    assert completion.usage.input_tokens == 100
    assert completion.usage.cost_millicents > 0


def test_generate_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    backend = AnthropicBackend(api_key_env="ANTHROPIC_API_KEY")
    with pytest.raises(LLMConfigError):
        backend.generate(
            system=[Block(text="s")],
            messages=[Message(role="user", blocks=[Block(text="h")])],
            model="claude-haiku-4-5",
            max_tokens=10,
        )


def test_generate_rate_limit_translates(monkeypatch):
    import anthropic
    fake_client = MagicMock()
    err = anthropic.RateLimitError(message="rate", response=MagicMock(headers={"retry-after": "42"}), body=None)
    fake_client.messages.create.side_effect = err
    monkeypatch.setattr("mnemonic.llm.backends.anthropic._make_sdk_client", lambda key: fake_client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    backend = AnthropicBackend(api_key_env="ANTHROPIC_API_KEY")
    with pytest.raises(LLMRateLimitError) as ei:
        backend.generate(system=[Block(text="s")],
                         messages=[Message(role="user", blocks=[Block(text="h")])],
                         model="claude-haiku-4-5", max_tokens=10)
    assert ei.value.retry_after == 42


def test_price_table_has_required_models():
    for m in ("claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-7"):
        assert m in PRICE_TABLE
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/llm/test_anthropic_backend.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement Anthropic backend**

Create `backend/src/mnemonic/llm/backends/__init__.py` (empty file).

Create `backend/src/mnemonic/llm/backends/anthropic.py`:

```python
"""Anthropic SDK backend implementing LLMClient.

Translates Block/Message into the SDK shape, adds cache_control,
computes cost from a hardcoded price table, translates SDK exceptions
into Mnemonic's exception hierarchy.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

import anthropic

from mnemonic.exceptions import LLMConfigError, LLMError, LLMRateLimitError, LLMUnavailableError
from mnemonic.llm.client import Block, BatchHandle, BatchRequest, Completion, Message, Usage


# Prices in millicents per million tokens (1 cent = 1000 millicents).
# Update when Anthropic prices change.
PRICE_TABLE: dict[str, dict[str, int]] = {
    "claude-haiku-4-5":  {"input": 100,  "output": 500,  "cache_read": 10,  "cache_creation": 125},
    "claude-sonnet-4-6": {"input": 300,  "output": 1500, "cache_read": 30,  "cache_creation": 375},
    "claude-opus-4-7":   {"input": 1500, "output": 7500, "cache_read": 150, "cache_creation": 1875},
}


def _make_sdk_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def _to_sdk_blocks(blocks: list[Block]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in blocks:
        entry: dict[str, Any] = {"type": "text", "text": b.text}
        if b.cache_control is not None:
            entry["cache_control"] = b.cache_control
        out.append(entry)
    return out


def _compute_cost_millicents(model: str, usage: Any) -> int:
    if model not in PRICE_TABLE:
        raise LLMConfigError(
            f"Unknown model in price table: {model}. Add it to PRICE_TABLE in anthropic.py."
        )
    p = PRICE_TABLE[model]
    inp = getattr(usage, "input_tokens", 0)
    out = getattr(usage, "output_tokens", 0)
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    cc = getattr(usage, "cache_creation_input_tokens", 0) or 0
    total = (
        (inp - cr - cc) * p["input"]
        + cr * p["cache_read"]
        + cc * p["cache_creation"]
        + out * p["output"]
    ) // 1_000_000
    return max(0, int(total))


class AnthropicBackend:
    def __init__(self, *, api_key_env: str = "ANTHROPIC_API_KEY"):
        self.api_key_env = api_key_env

    def _client(self) -> anthropic.Anthropic:
        key = os.environ.get(self.api_key_env, "").strip()
        if not key:
            raise LLMConfigError(
                f"Anthropic API key missing. Set ${self.api_key_env} in your shell "
                "(e.g. in ~/.config/mnemonic/.env or your shell profile)."
            )
        return _make_sdk_client(key)

    def generate(
        self,
        *,
        system: list[Block],
        messages: list[Message],
        model: str,
        max_tokens: int,
        stop_sequences: Sequence[str] = (),
    ) -> Completion:
        client = self._client()
        sdk_messages = [
            {"role": m.role, "content": _to_sdk_blocks(m.blocks)} for m in messages
        ]
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_to_sdk_blocks(system),
                messages=sdk_messages,
                stop_sequences=list(stop_sequences),
            )
        except anthropic.AuthenticationError as e:
            raise LLMConfigError(
                "Anthropic authentication failed. Verify ${self.api_key_env} is correct."
            ) from e
        except anthropic.RateLimitError as e:
            retry = 30
            try:
                retry = int(e.response.headers.get("retry-after", 30))
            except Exception:
                pass
            raise LLMRateLimitError(
                f"Anthropic rate limit hit. Retry in {retry}s, or reduce variation_frequency.",
                retry_after=retry,
            ) from e
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"Anthropic API returned {e.status_code} for model {model}: {getattr(e, 'message', '')}"
            ) from e
        except anthropic.APIConnectionError as e:
            raise LLMUnavailableError(f"Cannot reach Anthropic API: {e}") from e

        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        usage_obj = response.usage
        cost = _compute_cost_millicents(model, usage_obj)
        return Completion(
            text=text,
            model=model,
            usage=Usage(
                input_tokens=getattr(usage_obj, "input_tokens", 0),
                output_tokens=getattr(usage_obj, "output_tokens", 0),
                cache_read_tokens=getattr(usage_obj, "cache_read_input_tokens", 0) or 0,
                cache_creation_tokens=getattr(usage_obj, "cache_creation_input_tokens", 0) or 0,
                cost_millicents=cost,
            ),
        )

    def submit_batch(self, requests: Sequence[BatchRequest], *, model: str) -> BatchHandle:
        client = self._client()
        sdk_requests = []
        for r in requests:
            sdk_requests.append(
                {
                    "custom_id": r.custom_id,
                    "params": {
                        "model": model,
                        "max_tokens": r.max_tokens,
                        "system": _to_sdk_blocks(r.system),
                        "messages": [{"role": m.role, "content": _to_sdk_blocks(m.blocks)} for m in r.messages],
                        "stop_sequences": list(r.stop_sequences),
                    },
                }
            )
        try:
            batch = client.messages.batches.create(requests=sdk_requests)
        except anthropic.APIStatusError as e:
            raise LLMError(f"Batch submit failed: {getattr(e, 'message', '')}") from e
        return BatchHandle(batch_id=batch.id)
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/llm/test_anthropic_backend.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/llm/backends/ backend/tests/unit/llm/test_anthropic_backend.py
git commit -m "feat(llm): Anthropic backend with cache_control and cost computation"
```

---

## Wave 7: Variation skill (SKILL.md + generator + writer)

### Task 18: SKILL.md and strategy templates

**Files:**
- Create: `backend/src/mnemonic/llm/prompts/__init__.py` (empty)
- Create: `backend/src/mnemonic/llm/prompts/variation/__init__.py` (empty)
- Create: `backend/src/mnemonic/llm/prompts/variation/SKILL.md`
- Create: `backend/src/mnemonic/llm/prompts/variation/strategies/rephrase.md`
- Create: `backend/src/mnemonic/llm/prompts/variation/strategies/specialize.md`
- Create: `backend/src/mnemonic/llm/prompts/variation/strategies/generalize.md`
- Create: `backend/src/mnemonic/llm/prompts/variation/system.j2`
- Create: `backend/src/mnemonic/llm/prompts/variation/user.j2`

- [ ] **Step 1: Create SKILL.md**

Create `backend/src/mnemonic/llm/prompts/variation/SKILL.md`:

```markdown
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
```

- [ ] **Step 2: Create strategy templates**

Create `backend/src/mnemonic/llm/prompts/variation/strategies/rephrase.md`:

```markdown
# Strategy: Rephrase

**Difficulty target:** identical to the base card.

**Goal:** Re-word the question to test the same concept with different
phrasing. The user must still derive the same canonical answer.

**Permitted moves:**
- Swap synonyms ("define" ↔ "state" ↔ "give").
- Change sentence structure (active ↔ passive; declarative ↔ interrogative).
- Re-order clauses.
- Substitute equivalent notation (set-builder ↔ enumerated).

**Forbidden moves:**
- Adding new prerequisite knowledge.
- Changing the scope (asking for more or less than the base card).
- Hinting at the answer in the question.
```

Create `backend/src/mnemonic/llm/prompts/variation/strategies/specialize.md`:

```markdown
# Strategy: Specialize

**Difficulty target:** slightly easier than base, or same — never harder.

**Goal:** Ask the user to apply the concept to a specific concrete instance.
The answer should still rely on the same underlying definition/theorem.

**Permitted moves:**
- Provide a worked example setup; ask for the answer.
- Plug specific numbers into a formula and ask for the result.
- Restate an abstract definition with a concrete object.

**Forbidden moves:**
- Asking for a derivation the user hasn't been shown.
- Introducing new concepts not in `## Context`.
```

Create `backend/src/mnemonic/llm/prompts/variation/strategies/generalize.md`:

```markdown
# Strategy: Generalize

**Difficulty target:** slightly harder than base.

**Goal:** Ask the user to apply the concept at a higher level of abstraction
or to a broader class than the base card directly covers.

**Permitted moves:**
- Drop a specifying assumption and ask what survives.
- Lift to a more general object (group → category, real-valued → ℝⁿ).
- Ask for a unifying principle behind the base card's specific case.

**Forbidden moves:**
- Going outside the `## Context` material.
- Asking for a proof the user hasn't seen.
```

- [ ] **Step 3: Create Jinja templates**

Create `backend/src/mnemonic/llm/prompts/variation/system.j2`:

```
{{ skill_md }}

---

{{ strategy_md }}

---

## Note context for this card

{{ note_context }}
```

Create `backend/src/mnemonic/llm/prompts/variation/user.j2`:

```
## Base card

{{ base_card_text }}

## Prior variations

{% if prior_variations %}
{% for v in prior_variations %}
- Q: {{ v.q }}
  A: {{ v.a }}
  (rating: {{ v.rating }})
{% endfor %}
{% else %}
(none yet)
{% endif %}

## FSRS state

- stability: {{ fsrs.stability }}
- reps: {{ fsrs.reps }}
- lapses: {{ fsrs.lapses }}
- recent ratings: {{ fsrs.recent_ratings }}

## Task

Apply the {{ strategy_name }} strategy. Produce one Q/A pair following the
output schema in the skill.
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/mnemonic/llm/prompts/
git commit -m "feat(llm): SKILL.md, three strategy templates, Jinja prompt templates"
```

---

### Task 19: Variation generator + strategy selector + writer

**Files:**
- Create: `backend/src/mnemonic/llm/variation/__init__.py`
- Create: `backend/src/mnemonic/llm/variation/strategy.py`
- Create: `backend/src/mnemonic/llm/variation/generator.py`
- Create: `backend/src/mnemonic/llm/variation/writer.py`
- Create: `backend/tests/unit/llm/test_variation.py`

- [ ] **Step 1: Failing tests**

Create `backend/tests/unit/llm/test_variation.py`:

```python
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from mnemonic.llm.client import Completion, Usage
from mnemonic.llm.variation.strategy import select_strategy
from mnemonic.llm.variation.generator import VariationGenerator, GeneratedVariation


def test_select_strategy_rephrase_for_leech():
    s = select_strategy(reps=10, lapses=4, recent_ratings=[1, 2, 1])
    assert s == "rephrase"


def test_select_strategy_generalize_when_easy():
    s = select_strategy(reps=20, lapses=0, recent_ratings=[4, 4, 4])
    assert s == "generalize"


def test_select_strategy_specialize_default():
    s = select_strategy(reps=2, lapses=0, recent_ratings=[3])
    assert s == "specialize"


def test_generator_parses_qa_from_response(tmp_path: Path):
    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: When is X?\nA: When Y.",
        model="claude-haiku-4-5",
        usage=Usage(input_tokens=100, output_tokens=20, cache_read_tokens=0,
                    cache_creation_tokens=0, cost_millicents=15),
    )
    gen = VariationGenerator(
        client=client,
        prompts_dir=Path("backend/src/mnemonic/llm/prompts/variation"),
    )
    out = gen.generate(
        strategy="rephrase",
        base_card_text="A {{c1::NE}} is stable. ^card-x",
        note_context="Mutual best responses.",
        prior_variations=[],
        fsrs={"stability": 4.0, "reps": 5, "lapses": 0, "recent_ratings": [3, 4]},
        model="claude-haiku-4-5",
    )
    assert isinstance(out, GeneratedVariation)
    assert out.question == "When is X?"
    assert out.answer == "When Y."
    assert out.cost_millicents == 15
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/llm/test_variation.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement strategy.py**

Create `backend/src/mnemonic/llm/variation/__init__.py` (empty).

Create `backend/src/mnemonic/llm/variation/strategy.py`:

```python
"""Strategy selector for variation generation."""

from __future__ import annotations


def select_strategy(*, reps: int, lapses: int, recent_ratings: list[int]) -> str:
    """Pick rephrase | specialize | generalize based on FSRS signal.

    Rules:
      - High lapses or recent failures → rephrase (keep difficulty steady;
        defeat memorised wording).
      - Many reps with consistently high ratings → generalize (push deeper).
      - Otherwise → specialize (concrete instance to anchor learning).
    """
    recent = recent_ratings[-3:] if recent_ratings else []
    avg_recent = sum(recent) / len(recent) if recent else 3
    if lapses >= 3 or avg_recent < 2.5:
        return "rephrase"
    if reps >= 10 and avg_recent >= 3.8:
        return "generalize"
    return "specialize"
```

- [ ] **Step 4: Implement generator.py**

Create `backend/src/mnemonic/llm/variation/generator.py`:

```python
"""Variation generator: renders prompt + calls LLM + parses Q/A."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from mnemonic.exceptions import LLMError
from mnemonic.llm.cache import build_cached_system
from mnemonic.llm.client import LLMClient, Message, Block


@dataclass(frozen=True)
class GeneratedVariation:
    strategy: str
    question: str
    answer: str
    model: str
    cost_millicents: int
    raw_response: str


class VariationGenerator:
    def __init__(self, *, client: LLMClient, prompts_dir: Path):
        self.client = client
        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(prompts_dir),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def _load_skill(self) -> str:
        return (self.prompts_dir / "SKILL.md").read_text()

    def _load_strategy(self, strategy: str) -> str:
        path = self.prompts_dir / "strategies" / f"{strategy}.md"
        if not path.exists():
            raise LLMError(f"Strategy template not found: {path}")
        return path.read_text()

    def generate(
        self,
        *,
        strategy: str,
        base_card_text: str,
        note_context: str,
        prior_variations: list[dict[str, Any]],
        fsrs: dict[str, Any],
        model: str,
    ) -> GeneratedVariation:
        skill_md = self._load_skill()
        strategy_md = self._load_strategy(strategy)
        system_blocks = build_cached_system(
            skill_md=skill_md, strategy_md=strategy_md, note_context=note_context
        )

        user_tpl = self.env.get_template("user.j2")
        user_text = user_tpl.render(
            base_card_text=base_card_text,
            prior_variations=prior_variations,
            fsrs=fsrs,
            strategy_name=strategy,
        )

        completion = self.client.generate(
            system=system_blocks,
            messages=[Message(role="user", blocks=[Block(text=user_text)])],
            model=model,
            max_tokens=400,
        )

        q, a = self._parse_qa(completion.text)
        return GeneratedVariation(
            strategy=strategy,
            question=q,
            answer=a,
            model=completion.model,
            cost_millicents=completion.usage.cost_millicents,
            raw_response=completion.text,
        )

    @staticmethod
    def _parse_qa(text: str) -> tuple[str, str]:
        lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()]
        q_line = next((l for l in lines if l.startswith("Q:")), None)
        a_line = next((l for l in lines if l.startswith("A:")), None)
        if q_line is None or a_line is None:
            raise LLMError(
                "LLM did not return parseable Q:/A: blocks. "
                f"Got: {text[:200]!r}"
            )
        return q_line[2:].strip(), a_line[2:].strip()
```

- [ ] **Step 5: Implement writer.py**

Create `backend/src/mnemonic/llm/variation/writer.py`:

```python
"""Variation writer: persists generated variation to the note and to SQLite metadata."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.db.models import VariationMeta
from mnemonic.db.sqlite import session_scope
from mnemonic.vault.injector import (
    append_variation_entry,
    ensure_variations_section,
    update_variation_rating,
)
from mnemonic.llm.variation.generator import GeneratedVariation


def persist_variation(
    *,
    engine: Engine,
    note_path: Path,
    card_id: str,
    variation: GeneratedVariation,
    vault_root: Path,
) -> str:
    """Append variation entry to note and write VariationMeta row.

    Returns the generated variation_id.
    """
    ensure_variations_section(note_path)
    date_str = datetime.now().strftime("%Y-%m-%d")
    append_variation_entry(
        note_path=note_path,
        date_str=date_str,
        question=variation.question,
        answer=variation.answer,
    )

    variation_id = uuid.uuid4().hex
    content_hash = hashlib.sha256(
        (variation.question + "\n" + variation.answer).encode()
    ).hexdigest()
    rel_path = str(note_path.relative_to(vault_root))

    with session_scope(engine) as s:
        s.add(VariationMeta(
            id=variation_id,
            card_id=card_id,
            strategy=variation.strategy,
            model=variation.model,
            generated_at=datetime.now(),
            shown_count=1,
            helpful_count=0,
            content_hash=content_hash,
            note_path=rel_path,
        ))
    return variation_id


def mark_variation_rated(
    *,
    note_path: Path,
    rating: int,
) -> None:
    """Update the most recent pending entry in the note from `pending` → `rating: N`."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    update_variation_rating(note_path=note_path, date_str=date_str, rating=rating)
```

- [ ] **Step 6: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/llm/test_variation.py -v`
Expected: 4 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/mnemonic/llm/variation/ backend/tests/unit/llm/test_variation.py
git commit -m "feat(llm): variation strategy selector + generator + writer"
```

---

## Wave 8: Session lifecycle and API/service rewiring

### Task 20: Session lifecycle (pre-flight → scan → commit → push)

**Files:**
- Create: `backend/src/mnemonic/vault/session.py`
- Create: `backend/tests/integration/test_session.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/integration/test_session.py`:

```python
import subprocess
from pathlib import Path
import pytest
from mnemonic.db.models import Base, ReviewLog
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.vault.session import VaultSession
from mnemonic.exceptions import GitDirtyWorkingTreeError


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare", "--initial-branch=main"], bare)
    local = tmp_path / "vault"
    local.mkdir()
    _run(["git", "init", "--initial-branch=main"], local)
    _run(["git", "config", "user.email", "t@t.t"], local)
    _run(["git", "config", "user.name", "t"], local)
    _run(["git", "remote", "add", "origin", str(bare)], local)
    (local / "01_Projects" / "gt").mkdir(parents=True)
    (local / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA ==NE==.\n"
    )
    (local / ".gitattributes").write_text(".mnemonic/state.sqlite binary -diff -merge\n")
    _run(["git", "add", "."], local)
    _run(["git", "commit", "-m", "init"], local)
    _run(["git", "push", "-u", "origin", "main"], local)
    return local


def test_session_completes_and_commits(repo: Path):
    engine = create_engine(repo / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    sess = VaultSession(vault_root=repo, engine=engine)
    sess.start()
    sess.end(n_reviews=1, n_variations=0)
    log = subprocess.check_output(["git", "log", "--oneline"], cwd=repo).decode()
    assert "mnemonic: review session" in log


def test_session_refuses_on_dirty_tree(repo: Path):
    (repo / "01_Projects" / "gt" / "extra.md").write_text("untracked")
    engine = create_engine(repo / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    sess = VaultSession(vault_root=repo, engine=engine)
    with pytest.raises(GitDirtyWorkingTreeError):
        sess.start()
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/integration/test_session.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement session.py**

Create `backend/src/mnemonic/vault/session.py`:

```python
"""Session lifecycle: pre-flight → scan → review → commit → push."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.exceptions import GitError, GitNonFastForwardError
from mnemonic.vault import git_ops

logger = logging.getLogger(__name__)


class VaultSession:
    def __init__(
        self,
        *,
        vault_root: Path,
        engine: Engine,
        remote: str = "origin",
        branch: str = "main",
    ):
        self.vault_root = vault_root
        self.engine = engine
        self.remote = remote
        self.branch = branch
        self.offline = False
        self._started = False

    def start(self) -> None:
        self._ensure_vault_metadata()
        git_ops.assert_clean(self.vault_root)
        try:
            git_ops.fetch(self.vault_root, self.remote)
        except GitError as e:
            logger.warning("git fetch failed (continuing offline): %s", e)
            self.offline = True
        if not self.offline:
            try:
                git_ops.fast_forward_pull(self.vault_root, self.remote, self.branch)
            except GitNonFastForwardError:
                raise
        self._started = True

    def end(self, *, n_reviews: int, n_variations: int) -> None:
        if not self._started:
            raise RuntimeError("Session must be started before being ended.")
        msg = (
            f"mnemonic: review session {date.today().isoformat()} "
            f"({n_reviews} reviews, {n_variations} variations)"
        )
        sha = git_ops.commit_all(self.vault_root, msg)
        if not sha:
            logger.info("No changes to commit; skipping push.")
            return
        if self.offline:
            logger.warning("Offline: local commit %s retained; will push next session.", sha)
            return
        try:
            git_ops.push(self.vault_root, self.remote, self.branch)
        except GitError as e:
            logger.warning("Push failed: %s. Local commit %s retained.", e, sha)

    def _ensure_vault_metadata(self) -> None:
        """Ensure .mnemonic/ exists and .gitignore/.gitattributes carry Mnemonic-managed lines."""
        (self.vault_root / ".mnemonic").mkdir(exist_ok=True)

        gi_path = self.vault_root / ".gitignore"
        gi_lines = [
            "# managed by mnemonic",
            ".mnemonic/state.sqlite-wal",
            ".mnemonic/state.sqlite-shm",
            ".mnemonic/cache/",
            ".mnemonic/scan.log",
            ".mnemonic/.lock",
        ]
        existing = gi_path.read_text() if gi_path.exists() else ""
        missing = [l for l in gi_lines if l not in existing]
        if missing:
            from mnemonic.vault._atomic import atomic_write_text
            atomic_write_text(gi_path, (existing.rstrip() + "\n" + "\n".join(missing) + "\n").lstrip("\n"))

        ga_path = self.vault_root / ".gitattributes"
        ga_line = ".mnemonic/state.sqlite binary -diff -merge"
        existing_ga = ga_path.read_text() if ga_path.exists() else ""
        if ga_line not in existing_ga:
            from mnemonic.vault._atomic import atomic_write_text
            atomic_write_text(ga_path, (existing_ga.rstrip() + "\n" + ga_line + "\n").lstrip("\n"))
```

- [ ] **Step 4: Run; verify pass**

Run: `cd backend && uv run pytest tests/integration/test_session.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/mnemonic/vault/session.py backend/tests/integration/test_session.py
git commit -m "feat(vault): session lifecycle with pre-flight + offline-resilient commit"
```

---

### Task 21: Rewire deck/card services to VaultRepository

**Files:**
- Modify: `backend/src/mnemonic/services/deck.py`
- Modify: `backend/src/mnemonic/services/card.py`
- Modify: `backend/src/mnemonic/api/deps.py`
- Modify: `backend/tests/unit/api/test_decks.py`
- Modify: `backend/tests/unit/api/test_cards.py`

- [ ] **Step 1: Inspect current service**

Run: `cat backend/src/mnemonic/services/deck.py backend/src/mnemonic/services/card.py backend/src/mnemonic/api/deps.py`

- [ ] **Step 2: Rewrite `services/deck.py`**

Replace contents:

```python
"""Deck service: thin façade over VaultRepository."""

from __future__ import annotations

from mnemonic.vault.repository import VaultRepository, Deck


class DeckService:
    def __init__(self, *, repo: VaultRepository):
        self.repo = repo

    def list(self) -> list[Deck]:
        return self.repo.list_decks()

    def get(self, folder_name: str) -> Deck | None:
        for d in self.repo.list_decks():
            if d.folder.name == folder_name:
                return d
        return None
```

- [ ] **Step 3: Rewrite `services/card.py`**

Replace contents:

```python
"""Card service: thin façade over VaultRepository."""

from __future__ import annotations

from mnemonic.vault.repository import VaultRepository, Card


class CardService:
    def __init__(self, *, repo: VaultRepository):
        self.repo = repo

    def list(self, *, deck_folder_name: str | None = None) -> list[Card]:
        cards = self.repo.list_cards()
        if deck_folder_name is None:
            return cards
        return [c for c in cards if c.deck_folder.name == deck_folder_name]

    def get(self, card_id: str) -> Card | None:
        return self.repo.get_card(card_id)
```

- [ ] **Step 4: Rewrite `api/deps.py`**

Replace contents:

```python
"""FastAPI dependency injection: VaultRepository + engine + services."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine

from mnemonic.config import Config, load_config
from mnemonic.db.sqlite import create_engine
from mnemonic.services.card import CardService
from mnemonic.services.deck import DeckService
from mnemonic.vault.repository import VaultRepository


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    cfg = get_config()
    return create_engine(cfg.vault.path / ".mnemonic" / "state.sqlite")


def get_repo() -> VaultRepository:
    cfg = get_config()
    return VaultRepository(vault_root=cfg.vault.path, engine=get_engine())


def get_deck_service() -> DeckService:
    return DeckService(repo=get_repo())


def get_card_service() -> CardService:
    return CardService(repo=get_repo())
```

- [ ] **Step 5: Update existing API tests to use new shape**

Replace `backend/tests/unit/api/test_decks.py` and `test_cards.py` minimal smoke tests (rewrite full coverage in Task 24):

```python
# test_decks.py
def test_imports_work():
    from mnemonic.services.deck import DeckService  # noqa: F401
    from mnemonic.api.routes.decks import router  # noqa: F401
```

```python
# test_cards.py
def test_imports_work():
    from mnemonic.services.card import CardService  # noqa: F401
    from mnemonic.api.routes.cards import router  # noqa: F401
```

(Full coverage will be re-added in Task 22 once routes are adapted.)

- [ ] **Step 6: Run; expect failures from routes still referencing old User/auth deps**

Run: `cd backend && uv run pytest tests/unit/api/ -v`
Expected: failures; routes need adapting next task.

- [ ] **Step 7: Commit (intermediate)**

```bash
git add backend/src/mnemonic/services/ backend/src/mnemonic/api/deps.py backend/tests/unit/api/
git commit -m "refactor(services): point deck/card services at VaultRepository"
```

---

### Task 22: Adapt routes; delete auth; add new routes

**Files:**
- Modify: `backend/src/mnemonic/api/routes/decks.py`
- Modify: `backend/src/mnemonic/api/routes/cards.py`
- Create: `backend/src/mnemonic/api/routes/usage.py`
- Create: `backend/src/mnemonic/api/routes/vault.py`
- Create: `backend/src/mnemonic/api/routes/config.py`
- Modify: `backend/src/mnemonic/api/routes/__init__.py`
- Modify: `backend/src/mnemonic/main.py`
- Delete: `backend/src/mnemonic/api/routes/auth.py`
- Delete: `backend/src/mnemonic/services/auth.py`

- [ ] **Step 1: Rewrite `routes/decks.py`**

```python
"""Deck endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mnemonic.api.deps import get_deck_service
from mnemonic.services.deck import DeckService

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("")
def list_decks(svc: DeckService = Depends(get_deck_service)):
    return [
        {
            "folder_name": d.folder.name,
            "name": d.name,
            "config": d.config.__dict__ if d.config else None,
        }
        for d in svc.list()
    ]


@router.get("/{folder_name}")
def get_deck(folder_name: str, svc: DeckService = Depends(get_deck_service)):
    d = svc.get(folder_name)
    if d is None:
        raise HTTPException(status_code=404, detail=f"Deck '{folder_name}' not found.")
    return {
        "folder_name": d.folder.name,
        "name": d.name,
        "config": d.config.__dict__ if d.config else None,
    }
```

- [ ] **Step 2: Rewrite `routes/cards.py`**

```python
"""Card endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from mnemonic.api.deps import get_card_service
from mnemonic.services.card import CardService

router = APIRouter(prefix="/cards", tags=["cards"])


def _serialize(card) -> dict:
    return {
        "card_id": card.card_id,
        "note_path": str(card.note_path),
        "deck_folder": card.deck_folder.name,
        "syntax": card.syntax,
        "front": card.front,
        "back": card.back,
        "title": card.title,
        "state": card.state,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "due": card.due.isoformat() if card.due else None,
        "reps": card.reps,
        "lapses": card.lapses,
        "leech_score": card.leech_score,
        "suspended": card.suspended,
    }


@router.get("")
def list_cards(deck: str | None = Query(None), svc: CardService = Depends(get_card_service)):
    return [_serialize(c) for c in svc.list(deck_folder_name=deck)]


@router.get("/{card_id}")
def get_card(card_id: str, svc: CardService = Depends(get_card_service)):
    c = svc.get(card_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found.")
    return _serialize(c)
```

- [ ] **Step 3: Create `routes/usage.py`**

```python
"""LLM usage telemetry endpoint (today's spend, monthly spend, cache hit rate)."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func

from mnemonic.api.deps import get_engine
from mnemonic.db.models import LLMUsage
from mnemonic.db.sqlite import session_scope

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
def usage_summary(engine=Depends(get_engine)):
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start - timedelta(days=30)
    with session_scope(engine) as s:
        daily = int(s.query(func.coalesce(func.sum(LLMUsage.cost_millicents), 0))
                    .filter(LLMUsage.timestamp >= day_start).scalar() or 0)
        monthly = int(s.query(func.coalesce(func.sum(LLMUsage.cost_millicents), 0))
                      .filter(LLMUsage.timestamp >= month_start).scalar() or 0)
        cache_read = int(s.query(func.coalesce(func.sum(LLMUsage.cache_read_tokens), 0))
                         .filter(LLMUsage.timestamp >= day_start).scalar() or 0)
        total_input = int(s.query(func.coalesce(func.sum(LLMUsage.input_tokens), 0))
                          .filter(LLMUsage.timestamp >= day_start).scalar() or 0)
    hit_rate = (cache_read / total_input) if total_input else 0.0
    return {
        "daily_cents": daily / 1000,
        "monthly_cents": monthly / 1000,
        "cache_hit_rate": round(hit_rate, 3),
    }
```

- [ ] **Step 4: Create `routes/vault.py`**

```python
"""Vault status endpoint."""

from __future__ import annotations

import subprocess

from fastapi import APIRouter, Depends

from mnemonic.api.deps import get_config

router = APIRouter(prefix="/vault", tags=["vault"])


def _git_out(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


@router.get("/status")
def vault_status(cfg=Depends(get_config)):
    cwd = cfg.vault.path
    head = _git_out(cwd, "rev-parse", "--short", "HEAD")
    dirty = _git_out(cwd, "status", "--porcelain") != ""
    unpushed = _git_out(cwd, "log", "origin/main..HEAD", "--oneline") != ""
    return {
        "vault_path": str(cwd),
        "head": head,
        "dirty": dirty,
        "has_unpushed_commits": unpushed,
        "branch": cfg.vault.branch,
    }
```

- [ ] **Step 5: Create `routes/config.py`**

```python
"""Config UI endpoint (read-only in Phase 1)."""

from fastapi import APIRouter, Depends

from mnemonic.api.deps import get_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_current_config(cfg=Depends(get_config)):
    return {
        "vault": {"path": str(cfg.vault.path), "branch": cfg.vault.branch, "watch": cfg.vault.watch},
        "llm": {
            "model_default": cfg.llm.model_default,
            "model_rephrase": cfg.llm.model_rephrase,
            "model_offline": cfg.llm.model_offline,
            "budget": {
                "daily_cents": cfg.llm.budget.daily_cents,
                "monthly_cents": cfg.llm.budget.monthly_cents,
            },
        },
        "defaults": cfg.defaults.__dict__,
    }
```

- [ ] **Step 6: Replace `routes/__init__.py`**

```python
"""Mount API routers."""

from fastapi import APIRouter

from mnemonic.api.routes.cards import router as cards_router
from mnemonic.api.routes.config import router as config_router
from mnemonic.api.routes.decks import router as decks_router
from mnemonic.api.routes.usage import router as usage_router
from mnemonic.api.routes.vault import router as vault_router

api_router = APIRouter(prefix="/api")
api_router.include_router(decks_router)
api_router.include_router(cards_router)
api_router.include_router(usage_router)
api_router.include_router(vault_router)
api_router.include_router(config_router)
```

- [ ] **Step 7: Update `main.py`**

Replace `backend/src/mnemonic/main.py`:

```python
"""Mnemonic FastAPI app entry point."""

from fastapi import FastAPI

from mnemonic.api.routes import api_router

app = FastAPI(title="Mnemonic", version="0.2.0")
app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Delete obsolete files**

```bash
rm backend/src/mnemonic/api/routes/auth.py
rm backend/src/mnemonic/services/auth.py
rm backend/tests/unit/api/test_auth.py 2>/dev/null || true
```

- [ ] **Step 9: Run; expect pass (smoke imports only)**

Run: `cd backend && uv run pytest tests/unit/api/ -v`
Expected: 2 PASS (both smoke import tests).

- [ ] **Step 10: Commit**

```bash
git add -A backend/src/mnemonic/api backend/src/mnemonic/main.py backend/src/mnemonic/services
git commit -m "refactor(api): adapt decks/cards routes, add usage/vault/config routes, delete auth"
```

---

### Task 23: Review service + endpoint

**Files:**
- Create: `backend/src/mnemonic/services/review.py`
- Create: `backend/src/mnemonic/api/routes/reviews.py`
- Modify: `backend/src/mnemonic/api/routes/__init__.py`
- Create: `backend/tests/unit/services/test_review_service.py`

- [ ] **Step 1: Failing test**

Create `backend/tests/unit/services/__init__.py` (empty) and `backend/tests/unit/services/test_review_service.py`:

```python
from datetime import datetime
from pathlib import Path
from mnemonic.db.models import Base, SchedulingState, ReviewLog
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.review import ReviewService
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA ==NE==. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def test_rate_new_card_creates_state_and_log(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    svc = ReviewService(repo=repo, engine=engine)
    svc.rate(card_id="card-aaaabbbb", rating=3, response_time_ms=1500)
    with session_scope(engine) as s:
        state = s.get(SchedulingState, "card-aaaabbbb")
        assert state is not None
        assert state.reps == 1
        logs = s.query(ReviewLog).filter_by(card_id="card-aaaabbbb").all()
        assert len(logs) == 1
        assert logs[0].rating == 3


def test_rate_failure_increments_lapses(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    svc = ReviewService(repo=repo, engine=engine)
    svc.rate(card_id="card-aaaabbbb", rating=3, response_time_ms=1000)
    svc.rate(card_id="card-aaaabbbb", rating=1, response_time_ms=1000)
    with session_scope(engine) as s:
        state = s.get(SchedulingState, "card-aaaabbbb")
        assert state.lapses == 1
```

- [ ] **Step 2: Run; expect fail**

Run: `cd backend && uv run pytest tests/unit/services/test_review_service.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement review service**

Create `backend/src/mnemonic/services/review.py`:

```python
"""Review service: persists a rating, updates FSRS state, appends ReviewLog."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Engine

from mnemonic.core.fsrs.scheduler import schedule_next  # uses existing FSRS module
from mnemonic.db.models import ReviewLog, SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import CardNotFoundError, InvalidRatingError
from mnemonic.vault.repository import VaultRepository


class ReviewService:
    def __init__(self, *, repo: VaultRepository, engine: Engine):
        self.repo = repo
        self.engine = engine

    def rate(
        self,
        *,
        card_id: str,
        rating: int,
        response_time_ms: int,
        variation_id: str | None = None,
        variation_helpful: int | None = None,
    ) -> None:
        if rating not in (1, 2, 3, 4):
            raise InvalidRatingError(f"Rating must be 1..4 (got {rating}).")
        card = self.repo.get_card(card_id)
        if card is None:
            raise CardNotFoundError(f"Card '{card_id}' not in vault.")

        with session_scope(self.engine) as s:
            state = s.get(SchedulingState, card_id)
            if state is None:
                state = SchedulingState(
                    card_id=card_id, state="new", stability=0.0,
                    difficulty=5.0, reps=0, lapses=0, leech_score=0.0,
                )
                s.add(state)
                s.flush()

            state_before = state.state
            stability_before = state.stability
            difficulty_before = state.difficulty

            new_state, new_stab, new_diff, next_due_days = schedule_next(
                current_state=state.state,
                stability=state.stability,
                difficulty=state.difficulty,
                rating=rating,
            )
            state.state = new_state
            state.stability = new_stab
            state.difficulty = new_diff
            state.reps += 1
            if rating == 1:
                state.lapses += 1
            state.due = datetime.now() + timedelta(days=next_due_days)
            state.updated_at = datetime.now()

            s.add(ReviewLog(
                id=uuid.uuid4().hex,
                card_id=card_id,
                rating=rating,
                response_time_ms=response_time_ms,
                review_time=datetime.now(),
                state_before=state_before,
                state_after=new_state,
                stability_before=stability_before,
                stability_after=new_stab,
                difficulty_before=difficulty_before,
                difficulty_after=new_diff,
                variation_id=variation_id,
                variation_helpful=variation_helpful,
            ))
```

Note: `schedule_next` is assumed to exist in `core/fsrs/scheduler.py`. If its signature differs in the current code, adapt this call site accordingly without changing the FSRS algorithm itself.

- [ ] **Step 4: Create review route**

Create `backend/src/mnemonic/api/routes/reviews.py`:

```python
"""Review endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mnemonic.api.deps import get_engine, get_repo
from mnemonic.exceptions import CardNotFoundError, InvalidRatingError
from mnemonic.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class RatePayload(BaseModel):
    card_id: str
    rating: int = Field(..., ge=1, le=4)
    response_time_ms: int = Field(..., ge=0)
    variation_id: str | None = None
    variation_helpful: int | None = None


@router.post("/rate")
def rate(
    payload: RatePayload,
    repo=Depends(get_repo),
    engine=Depends(get_engine),
):
    svc = ReviewService(repo=repo, engine=engine)
    try:
        svc.rate(
            card_id=payload.card_id,
            rating=payload.rating,
            response_time_ms=payload.response_time_ms,
            variation_id=payload.variation_id,
            variation_helpful=payload.variation_helpful,
        )
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidRatingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}
```

- [ ] **Step 5: Mount in routes `__init__.py`**

Append to the imports + includes in `backend/src/mnemonic/api/routes/__init__.py`:

```python
from mnemonic.api.routes.reviews import router as reviews_router

# (existing api_router setup)
api_router.include_router(reviews_router)
```

- [ ] **Step 6: Run; verify pass**

Run: `cd backend && uv run pytest tests/unit/services/test_review_service.py -v`
Expected: 2 PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/mnemonic/services/review.py backend/src/mnemonic/api/routes/reviews.py backend/src/mnemonic/api/routes/__init__.py backend/tests/unit/services/
git commit -m "feat(reviews): review service + /api/reviews/rate endpoint"
```

---

## Wave 9: Frontend changes

### Task 24: Frontend auth removal

**Files:**
- Delete: `frontend/src/pages/LoginPage.tsx`
- Delete: `frontend/src/pages/RegisterPage.tsx`
- Delete: `frontend/src/components/ProtectedRoute.tsx`
- Delete: `frontend/src/hooks/useAuth.ts`
- Delete: `frontend/src/stores/authStore.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/components/Navigation.tsx`
- Modify: `frontend/src/hooks/index.ts`
- Modify: `frontend/src/stores/index.ts`

- [ ] **Step 1: Delete auth files**

```bash
rm frontend/src/pages/LoginPage.tsx \
   frontend/src/pages/RegisterPage.tsx \
   frontend/src/components/ProtectedRoute.tsx \
   frontend/src/hooks/useAuth.ts \
   frontend/src/stores/authStore.ts
```

- [ ] **Step 2: Inspect current `App.tsx` and `api.ts`**

Run: `cat frontend/src/App.tsx frontend/src/services/api.ts`

- [ ] **Step 3: Rewrite `App.tsx`**

Replace `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AppLayout from "./layouts/AppLayout";
import DeckListPage from "./pages/DeckListPage";
import DeckDetailPage from "./pages/DeckDetailPage";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/decks" replace />} />
            <Route path="/decks" element={<DeckListPage />} />
            <Route path="/decks/:folder" element={<DeckDetailPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 4: Rewrite `services/api.ts`**

Replace `frontend/src/services/api.ts`:

```ts
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, `${response.status}: ${detail || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listDecks: () => request<any[]>("/decks"),
  getDeck: (folder: string) => request<any>(`/decks/${folder}`),
  listCards: (deck?: string) =>
    request<any[]>(`/cards${deck ? `?deck=${encodeURIComponent(deck)}` : ""}`),
  getCard: (id: string) => request<any>(`/cards/${id}`),
  rate: (payload: { card_id: string; rating: number; response_time_ms: number }) =>
    request<{ ok: true }>("/reviews/rate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  usage: () => request<any>("/usage"),
  vaultStatus: () => request<any>("/vault/status"),
  getConfig: () => request<any>("/config"),
};
```

- [ ] **Step 5: Update `Navigation.tsx`**

Remove any login/logout/user-aware UI. Keep "Decks" / "Settings" links.

Edit `frontend/src/components/Navigation.tsx` (replace login-related JSX with just the deck/settings nav). If the file has only auth nav now, replace with:

```tsx
import { NavLink } from "react-router-dom";

export default function Navigation() {
  return (
    <nav className="app-nav">
      <NavLink to="/decks">Decks</NavLink>
    </nav>
  );
}
```

- [ ] **Step 6: Update `hooks/index.ts` and `stores/index.ts`**

Remove `useAuth` and `authStore` exports if present.

- [ ] **Step 7: Run tests**

Run: `cd frontend && npm test -- --run`
Expected: tests pass (or fail only on tests of deleted files — delete those test files too).

- [ ] **Step 8: Commit**

```bash
git add -A frontend/src
git commit -m "refactor(frontend): remove auth flow (single-user vault model)"
```

---

### Task 25: Vault status banner + Usage page + Settings page (read-only)

**Files:**
- Create: `frontend/src/components/VaultStatusBanner.tsx`
- Create: `frontend/src/pages/UsagePage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Navigation.tsx`

- [ ] **Step 1: Create VaultStatusBanner**

Create `frontend/src/components/VaultStatusBanner.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

export default function VaultStatusBanner() {
  const { data, isError } = useQuery({
    queryKey: ["vault-status"],
    queryFn: api.vaultStatus,
    refetchInterval: 30_000,
  });
  if (isError) return <div role="alert">Vault status unavailable.</div>;
  if (!data) return null;
  const warn = data.dirty || data.has_unpushed_commits;
  return (
    <div className={`vault-status ${warn ? "vault-status--warn" : ""}`}>
      <span>Vault @ {data.head}</span>
      {data.dirty && <span> · uncommitted changes</span>}
      {data.has_unpushed_commits && <span> · unpushed commits</span>}
    </div>
  );
}
```

- [ ] **Step 2: Create UsagePage**

Create `frontend/src/pages/UsagePage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

export default function UsagePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["usage"],
    queryFn: api.usage,
  });
  if (isLoading) return <div>Loading usage…</div>;
  if (error) return <div role="alert">Failed to load usage: {String(error)}</div>;
  return (
    <section>
      <h1>LLM Usage</h1>
      <dl>
        <dt>Today</dt>
        <dd>${data.daily_cents.toFixed(3)}</dd>
        <dt>Last 30 days</dt>
        <dd>${data.monthly_cents.toFixed(2)}</dd>
        <dt>Cache hit rate (today)</dt>
        <dd>{(data.cache_hit_rate * 100).toFixed(1)}%</dd>
      </dl>
    </section>
  );
}
```

- [ ] **Step 3: Create SettingsPage**

Create `frontend/src/pages/SettingsPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

export default function SettingsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["config"], queryFn: api.getConfig });
  if (isLoading || !data) return <div>Loading…</div>;
  return (
    <section>
      <h1>Settings</h1>
      <h2>Vault</h2>
      <dl>
        <dt>Path</dt><dd>{data.vault.path}</dd>
        <dt>Branch</dt><dd>{data.vault.branch}</dd>
        <dt>Watch</dt><dd>{String(data.vault.watch)}</dd>
      </dl>
      <h2>LLM</h2>
      <dl>
        <dt>Default model</dt><dd>{data.llm.model_default}</dd>
        <dt>Rephrase model</dt><dd>{data.llm.model_rephrase}</dd>
        <dt>Daily cap (cents)</dt><dd>{data.llm.budget.daily_cents}</dd>
        <dt>Monthly cap (cents)</dt><dd>{data.llm.budget.monthly_cents}</dd>
      </dl>
      <p>To edit, modify <code>~/.config/mnemonic/config.toml</code> and restart the backend.</p>
    </section>
  );
}
```

- [ ] **Step 4: Mount banner + new pages**

Edit `frontend/src/layouts/AppLayout.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import Navigation from "../components/Navigation";
import VaultStatusBanner from "../components/VaultStatusBanner";

export default function AppLayout() {
  return (
    <div>
      <Navigation />
      <VaultStatusBanner />
      <main><Outlet /></main>
    </div>
  );
}
```

Add routes for the new pages in `frontend/src/App.tsx`:

```tsx
import UsagePage from "./pages/UsagePage";
import SettingsPage from "./pages/SettingsPage";
// inside <Routes>:
<Route path="/usage" element={<UsagePage />} />
<Route path="/settings" element={<SettingsPage />} />
```

Update `Navigation.tsx`:

```tsx
import { NavLink } from "react-router-dom";

export default function Navigation() {
  return (
    <nav className="app-nav">
      <NavLink to="/decks">Decks</NavLink>
      <NavLink to="/usage">Usage</NavLink>
      <NavLink to="/settings">Settings</NavLink>
    </nav>
  );
}
```

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npm test -- --run`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add -A frontend/src
git commit -m "feat(frontend): vault status banner + Usage page + read-only Settings page"
```

---

## Wave 10: Smoke test, cleanup, docs

### Task 26: End-to-end smoke test (fixture vault + mocked LLM)

**Files:**
- Create: `backend/tests/e2e/test_session_smoke.py`
- Create: `backend/tests/e2e/conftest.py`
- Create: `backend/tests/llm/golden/nash-equilibrium.qmd`

- [ ] **Step 1: Create the golden fixture note**

Create `backend/tests/llm/golden/nash-equilibrium.qmd`:

```markdown
---
title: Nash equilibrium
tags: [game-theory]
---

## Card

A {{c1::Nash equilibrium}} is a strategy profile in which {{c1::no player can improve}} by deviating unilaterally.

## Context

Mutual best responses. Nash (1950) proved existence for any finite game.
Compare with: dominant strategy equilibrium, correlated equilibrium.
```

- [ ] **Step 2: Create e2e conftest with a fixture vault Git repo**

Create `backend/tests/e2e/conftest.py`:

```python
import subprocess
from pathlib import Path
import pytest


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def fixture_vault(tmp_path: Path):
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "--initial-branch=main")

    vault = tmp_path / "vault"
    vault.mkdir()
    _git(vault, "init", "--initial-branch=main")
    _git(vault, "config", "user.email", "t@t.t")
    _git(vault, "config", "user.name", "t")
    _git(vault, "remote", "add", "origin", str(bare))

    folder = vault / "01_Projects" / "game-theory"
    folder.mkdir(parents=True)
    src = Path(__file__).parent.parent / "llm" / "golden" / "nash-equilibrium.qmd"
    (folder / "nash.qmd").write_text(src.read_text())

    (vault / ".gitattributes").write_text(".mnemonic/state.sqlite binary -diff -merge\n")
    _git(vault, "add", ".")
    _git(vault, "commit", "-m", "init")
    _git(vault, "push", "-u", "origin", "main")
    return vault
```

- [ ] **Step 3: Smoke test**

Create `backend/tests/e2e/test_session_smoke.py`:

```python
import subprocess
from pathlib import Path
from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.services.review import ReviewService
from mnemonic.vault.repository import VaultRepository
from mnemonic.vault.session import VaultSession


def test_full_session_cycle(fixture_vault: Path):
    engine = create_engine(fixture_vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    sess = VaultSession(vault_root=fixture_vault, engine=engine)
    sess.start()

    repo = VaultRepository(vault_root=fixture_vault, engine=engine)
    cards = repo.list_cards()
    assert len(cards) == 1
    card = cards[0]
    assert card.card_id.startswith("card-")  # ID injected during scan

    svc = ReviewService(repo=repo, engine=engine)
    svc.rate(card_id=card.card_id, rating=3, response_time_ms=1500)

    sess.end(n_reviews=1, n_variations=0)

    log = subprocess.check_output(
        ["git", "log", "--oneline"], cwd=fixture_vault
    ).decode()
    assert "mnemonic: review session" in log
    note_text = (fixture_vault / "01_Projects" / "game-theory" / "nash.qmd").read_text()
    assert "^card-" in note_text
```

- [ ] **Step 4: Run**

Run: `cd backend && uv run pytest tests/e2e/test_session_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/e2e backend/tests/llm/golden
git commit -m "test(e2e): full-session smoke against fixture vault repo"
```

---

### Task 27: Cleanup (delete old models, old Alembic, Postgres from docker-compose)

**Files:**
- Delete: `backend/src/mnemonic/db/models/{user,card,deck,card_type,variation_cache}.py`
- Delete: `backend/src/mnemonic/db/repositories/{user,card,deck}.py`
- Delete: `backend/alembic/versions/0001_initial_schema_with_all_models.py`
- Delete: `backend/alembic/versions/0002_seed_builtin_card_types.py`
- Delete: `backend/tests/unit/db/test_repositories.py`
- Modify: `backend/src/mnemonic/db/repositories/__init__.py`
- Modify: `infrastructure/docker-compose.dev.yml` (drop postgres)

- [ ] **Step 1: Verify no imports remain**

Run: `cd backend && uv run grep -rE "from mnemonic.db.models.(user|card|deck|card_type|variation_cache) import" src/ tests/`
Expected: empty.

Run: `cd backend && uv run grep -rE "from mnemonic.db.repositories.(user|card|deck) import" src/ tests/`
Expected: empty.

- [ ] **Step 2: Delete obsolete files**

```bash
rm backend/src/mnemonic/db/models/user.py
rm backend/src/mnemonic/db/models/card.py
rm backend/src/mnemonic/db/models/deck.py
rm backend/src/mnemonic/db/models/card_type.py
rm backend/src/mnemonic/db/models/variation_cache.py
rm backend/src/mnemonic/db/repositories/user.py
rm backend/src/mnemonic/db/repositories/card.py
rm backend/src/mnemonic/db/repositories/deck.py
rm backend/alembic/versions/0001_initial_schema_with_all_models.py
rm backend/alembic/versions/0002_seed_builtin_card_types.py
rm backend/tests/unit/db/test_repositories.py
```

- [ ] **Step 3: Update repositories `__init__.py` to keep only base if needed**

Open `backend/src/mnemonic/db/repositories/__init__.py`. If it imports the deleted modules, replace with just:

```python
"""Database repositories. Currently empty — VaultRepository in mnemonic.vault is the new façade."""
```

- [ ] **Step 4: Update docker-compose**

Inspect: `cat infrastructure/docker-compose.dev.yml`

Remove the `postgres` service block. Remove any `depends_on: [postgres]` from `backend`. Remove postgres-related env vars (`DATABASE_URL` for postgres). Keep redis (still listed as optional cache). Update the backend's volume mount to mount the vault path at `/vault` (the user can configure their own vault path; document that the container needs read+write to the vault).

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest -v`
Expected: all PASS. If any test still references deleted models, fix or delete that test.

- [ ] **Step 6: Coverage check**

Run: `cd backend && uv run pytest --cov=mnemonic --cov-report=term-missing`
Expected:
  - `mnemonic.core` ≥ 95%
  - `mnemonic.vault` ≥ 90%
  - `mnemonic.llm` ≥ 85%
  - overall ≥ 85%
If any gate is below threshold, add targeted unit tests before committing.

- [ ] **Step 7: Commit**

```bash
git add -A backend infrastructure
git commit -m "chore: delete old Postgres models/migrations; drop postgres from compose"
```

---

### Task 28: Update docs (README + ADR for the storage rewrite)

**Files:**
- Modify: `README.md`
- Create: `docs/source/adr/0001-vault-backed-storage.md`

- [ ] **Step 1: Update README**

Edit `README.md` to reflect:
- Storage is now an Obsidian vault Git repo + SQLite sidecar.
- No PostgreSQL setup needed.
- Quickstart: install deps, set `ANTHROPIC_API_KEY`, write `~/.config/mnemonic/config.toml`, run backend, open frontend.
- Removed sections about user registration/login.

(Keep this section concise — let the spec be the long-form reference. Show the minimal `config.toml` and the first-run flow.)

- [ ] **Step 2: Write ADR**

Create `docs/source/adr/0001-vault-backed-storage.md`:

```markdown
# ADR-0001: Vault-Backed Storage with SQLite Sidecar

**Status:** Accepted (2026-05-10)

## Context

Phase 1 used PostgreSQL for all state — cards, decks, scheduling, reviews,
variations. This locked card content into a database row that diverged from
how the user actually authors notes (in Obsidian/Quarto vaults).

## Decision

Cards are authored as Markdown notes following a per-card-dossier convention
in an Obsidian vault Git repo (initialised from `vault-cookiecutter`).
Application state lives in a SQLite sidecar (`.mnemonic/state.sqlite`)
inside the vault. The vault is the source of truth; Mnemonic clones,
pulls, commits, and pushes around each review session.

## Consequences

- The user authors and edits cards in any editor they like — Obsidian,
  Neovim, the desktop, the web — and Mnemonic picks up changes on the
  next session.
- State is portable: cloning the vault on a new machine recovers the full
  review history.
- Binary SQLite churn in Git is accepted (~18MB/year per spec §14).
- Single-active-device contract: concurrent sessions on different machines
  are unsupported (would cause binary merge conflicts).
- PostgreSQL is removed from the stack.

## Alternatives considered

- **Text-dumped state** (YAML + JSONL committed; SQLite as derived cache).
  Cleaner Git diffs, more complexity. Rejected for simplicity in Phase 1.
- **OpenRouter as LLM provider.** Rejected for direct Anthropic SDK to
  capture prompt caching + batch API natively. Provider Protocol leaves an
  escape hatch.

## See also

- Spec: `docs/superpowers/specs/2026-05-10-vault-storage-design.md`
- Plan: `docs/superpowers/plans/2026-05-10-vault-storage.md`
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/source/adr/0001-vault-backed-storage.md
git commit -m "docs: README + ADR for vault-backed storage"
```

---

## Done

At this point:
- `pytest` passes; coverage gates met
- `git log` in a fixture vault shows clean `mnemonic: review session …` commits
- Frontend renders Decks / Usage / Settings without an auth gate
- PostgreSQL is gone from the codebase
- The note convention is enforced by the parser; loud failures on any violation
- Prompt caching and the budget guard are active in the LLM path

Verify with a real end-to-end smoke run against your own vault (point
`config.toml` at it; `uv run uvicorn mnemonic.main:app --reload`; open the frontend;
review one card; confirm a commit appears in your vault's git log and the
`^card-xyz` block ID was injected into the note).

## Deferred to follow-on plans

The following spec items are intentionally out of scope for this plan and
should each get their own short plan when prioritised:

- **File watcher (spec §8.5).** `watchdog`-based inotify watcher for
  mid-session note edits. Phase 1 default is `watch = false`; session-start
  scan is sufficient.
- **`mnemonic init` CLI.** Convenience command that prompts for vault remote
  and writes `~/.config/mnemonic/config.toml`. For now, the user creates the
  config file manually (one-time).
- **`scripts/migrate_pg_to_vault.py`.** Optional one-shot to read the
  current Postgres state and emit canonical notes. Phase 1 is a clean
  cutover; only relevant if real data was loaded into PG.
- **Full LLM golden-set evaluation harness** (spec §7.2). Phase 1 ships one
  golden card + the smoke test in Task 26; expand to the full ~20 cards and
  all four judges when the SKILL.md prompts have iterated a few times.
- **DSPy prompt optimiser productionisation** (spec §3.2 bullet). Stub
  module exists; offline script comes later.
- **`compose` variation strategy** (spec §7.3). Phase 2.






