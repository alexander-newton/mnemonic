Mnemonic Documentation
======================

Adaptive spaced repetition system with LLM-powered question variations.
Cards live as Markdown notes in a Git-backed Obsidian/Quarto vault; review
state lives in a SQLite sidecar inside that vault.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user-guide/index
   developer/index
   api/index
   adr/index

Quick Start
-----------

1. Install ``uv`` and run ``uv sync`` in ``backend/``.
2. Export ``ANTHROPIC_API_KEY`` in your shell.
3. Create ``~/.config/mnemonic/config.toml`` pointing at a vault path
   (and optional remote). See ``backend/README.md`` for the schema.
4. Run the backend: ``uv run uvicorn mnemonic.main:app --reload``.
5. Run the frontend: ``cd frontend && npm install && npm run dev``.
6. Open ``http://localhost:5173`` and start reviewing.

Each review session pulls the vault, scans for cards, lets you review, then
commits and pushes the resulting state back.

Features
--------

- FSRS-5 scheduling algorithm.
- Cards extracted from `.md`/`.qmd` notes via cloze (``{{cN::...}}``),
  highlight (``==text==``), or callout (``> [!card]``) syntax.
- Stable card identity via Obsidian-native ``^card-xyz`` block IDs (injected
  on first scan).
- LLM-powered variation generation (Anthropic SDK direct, with prompt
  caching, model tiering, and a daily/monthly budget guard).
- Per-card variation history written back to the note's
  ``## Variations`` section so the LLM sees its prior phrasings.

Design references
-----------------

- Specification: ``docs/superpowers/specs/2026-05-10-vault-storage-design.md``
- Implementation plan: ``docs/superpowers/plans/2026-05-10-vault-storage.md``
- ADR-0001: :doc:`adr/0001-vault-backed-storage`

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
