API Reference
=============

The Mnemonic API is a single-user, locally-hosted FastAPI service.
There is no authentication: the user is the operator.

Interactive documentation is generated at runtime by FastAPI:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Endpoints
---------

All routes are mounted under ``/api`` (except ``/health``).

Decks
~~~~~

- ``GET /api/decks`` — list all decks discovered in the vault.
- ``GET /api/decks/{folder_name}`` — get one deck by its folder basename;
  404 if not found.

A "deck" is a folder containing at least one card-note. The ``config``
field returns the parsed ``_deck.md`` frontmatter if present (else null).

Cards
~~~~~

- ``GET /api/cards[?deck=<folder_name>]`` — list cards, optionally
  filtered to one deck.
- ``GET /api/cards/{card_id}`` — single card by block-ID
  (``card-xxxxxxxx``).

Each card returned joins the on-disk note (front, back, syntax,
note_path, title) with the SQLite scheduling row (state, stability,
difficulty, due, reps, lapses, leech_score, suspended). Cards without
a SQLite row default to ``state="new"``.

Reviews
~~~~~~~

- ``POST /api/reviews/rate`` — rate a card. Body:

  .. code-block:: json

     {
       "card_id": "card-7f3a1234",
       "rating": 3,
       "response_time_ms": 1500,
       "variation_id": null,
       "variation_helpful": null
     }

  ``rating`` is 1–4 (FSRS). The service updates the SchedulingState row,
  appends a ReviewLog entry, and recomputes the due date.

Usage
~~~~~

- ``GET /api/usage`` — today/30-day spend in cents plus cache hit rate.
  Powers the cost panel in the frontend.

Vault Status
~~~~~~~~~~~~

- ``GET /api/vault/status`` — current commit SHA, dirty flag, unpushed
  commit flag, configured branch. Returns 503 if the vault path doesn't
  exist or Git fails.

Config
~~~~~~

- ``GET /api/config`` — current effective configuration (vault, LLM,
  defaults). Read-only in Phase 1; edit
  ``~/.config/mnemonic/config.toml`` to change settings.

Health
~~~~~~

- ``GET /health`` — liveness probe; always ``{"status": "ok"}``.

Error Responses
---------------

Domain exceptions are translated by route handlers:

- ``CardNotFoundError`` → ``404`` with ``detail`` carrying the missing id.
- ``InvalidRatingError`` → ``400``.
- ``GitError`` (and subclasses) → ``503`` with the underlying message.
- ``LLMConfigError`` / ``LLMRateLimitError`` / ``LLMBudgetExceededError``
  bubble through to surface in the frontend banner when the variation
  generator runs.

No silent fallbacks: per Principle #1 in ``CLAUDE.md``, every error path
carries enough context for the operator to act.
