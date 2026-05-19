Developer Documentation
=======================

.. toctree::
   :maxdepth: 2

   migrations

Setup
-----

See ``backend/README.md`` for installation and configuration. The short
version:

.. code-block:: bash

   cd backend
   uv sync
   uv run uvicorn mnemonic.main:app --reload

For the frontend:

.. code-block:: bash

   cd frontend
   npm install
   npm run dev

Both expect ``~/.config/mnemonic/config.toml`` to exist and point at a
vault path.

Architecture Overview
---------------------

- ``backend/src/mnemonic/vault/`` — The vault layer. Scans notes, parses
  the canonical structure, extracts cards via three syntaxes, manages
  block-ID injection and variation-log writes, runs Git operations,
  orchestrates the session lifecycle. ``repository.py`` is the public
  façade that joins on-disk scan results with SQLite scheduling state.
- ``backend/src/mnemonic/llm/`` — LLM client behind a ``Protocol`` so the
  backend is swappable. ``backends/anthropic.py`` is the only concrete
  implementation in Phase 1. ``cache.py`` builds cache-controlled prompt
  blocks; ``budget.py`` halts requests when the daily/monthly cap is hit;
  ``router.py`` picks model tier; ``variation/`` renders prompts, parses
  ``Q:``/``A:`` output, and writes the result back to the note.
- ``backend/src/mnemonic/db/`` — SQLite engine + ORM models. Five tables:
  scheduling state, review log, variation metadata, LLM usage, training
  example. Alembic migrations under ``backend/alembic/``.
- ``backend/src/mnemonic/services/`` — Application services (deck, card,
  review). All take ``VaultRepository`` (and the engine for review) by
  dependency injection.
- ``backend/src/mnemonic/api/`` — FastAPI routes. Single-user; no auth.
- ``backend/src/mnemonic/core/fsrs/`` — Pure FSRS-5 algorithm. Untouched
  by the vault rewrite.

API Design
----------

All errors raise a typed subclass of ``mnemonic.exceptions.MnemonicError``
carrying an actionable message — never a generic exception or a silent
fallback. Routes translate domain exceptions into appropriate HTTP status
codes (``CardNotFoundError`` → 404, ``InvalidRatingError`` → 400,
``GitError`` → 503).

Configuration is loaded once at startup via
``mnemonic.config.load_config()``: user-global TOML overlaid by a
vault-local TOML. The vault-local file is committed in the vault repo so
per-vault overrides travel with the data.

Testing
-------

- ``backend/tests/unit/`` — fast, no I/O beyond ``tmp_path``.
- ``backend/tests/integration/`` — exercises real Git via ``subprocess``
  (bare + local temp repos).
- ``backend/tests/e2e/`` — full session-lifecycle smoke against a fixture
  vault repo.

Run the full suite with ``cd backend && uv run pytest``. Coverage targets
per ``CLAUDE.md``: ``core/`` ≥ 95 %, ``vault/`` ≥ 90 %, ``llm/`` ≥ 85 %,
overall ≥ 85 %.

See :doc:`migrations` for working with Alembic and the SQLite sidecar.
