# ADR-0001: Vault-Backed Storage with SQLite Sidecar

**Status:** Accepted (2026-05-19)

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

The Anthropic SDK replaces OpenRouter, enabling native prompt caching and
batch API support for cost-efficient LLM variation generation.

## Consequences

**Positive:**
- The user authors and edits cards in any editor they like — Obsidian,
  Neovim, the desktop, the web — and Mnemonic picks up changes on the
  next session.
- State is portable: cloning the vault on a new machine recovers the full
  review history.
- Prompt caching reduces LLM costs by 10x on re-reviewed cards.
- Batch API enables overnight bulk variation generation.
- No authentication burden: vault is a local folder (Git-backed).

**Trade-offs:**
- Binary SQLite churn in Git is accepted (~18MB/year per spec).
- Single-active-device contract: concurrent sessions on different machines
  are unsupported (would cause binary merge conflicts).
- PostgreSQL, Redis, and Docker are removed from Phase 1.

## Alternatives considered

- **Text-dumped state** (YAML + JSONL committed; SQLite as derived cache).
  Cleaner Git diffs, more complexity in Phase 1. Deferred to Phase 2.
- **OpenRouter as LLM provider.** Rejected for direct Anthropic SDK to
  capture prompt caching + batch API natively. Provider Protocol leaves an
  escape hatch for future flexibility.

## See also

- Spec: `docs/superpowers/specs/2026-05-10-vault-storage-design.md`
- Plan: `docs/superpowers/plans/2026-05-10-vault-storage.md`
- Quick Start: `README.md`
