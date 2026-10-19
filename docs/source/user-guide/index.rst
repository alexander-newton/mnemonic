User Guide
==========

This guide covers day-to-day use of Mnemonic. For developer setup, see the
:doc:`Developer Documentation <../developer/index>`.

Getting Started
---------------

Mnemonic does not store cards in its own database. It reads them from your
**vault** — a Git repository containing Markdown notes organised in folders.
Each subfolder of the vault that contains at least one card-note becomes a
**deck**.

On first run, Mnemonic clones the vault (if you've configured a remote),
walks every note, and identifies the ones that look like card-notes. The
first time it sees an un-marked card-note, it injects a stable
``^card-xyz`` identifier so subsequent edits don't lose review history.

Card-Note Convention
--------------------

Every card-note follows the same canonical structure:

.. code-block:: markdown

   ---
   title: Nash equilibrium
   tags: [game-theory]
   ---

   ## Card

   A {{c1::Nash equilibrium}} is a strategy profile in which
   {{c1::no player can improve}} by deviating unilaterally. ^card-7f3a

   ## Context

   Mutual best responses. Nash (1950) proved existence for any finite game.
   Compare with dominant strategy equilibrium, correlated equilibrium.

   ## Variations

   <!-- mnemonic:variations:begin -->
   ### 2026-04-12 (rating: 4)
   **Q:** When is a strategy profile a Nash equilibrium?
   **A:** When no unilateral deviation improves any player's payoff.
   <!-- mnemonic:variations:end -->

- The frontmatter must contain at least ``title``.
- ``## Card`` uses exactly one of the three supported syntaxes (cloze,
  highlight, or callout — not mixed). All markers in the section are
  revealed together at review time; the note is one FSRS-scheduled unit.
- Cloze answers may contain balanced braces, so LaTeX works inside them
  (``{{c1::\dfrac{a}{2}}}``, ``{{c2::\mathbb{R}^2}}``). A marker closes at the
  first ``}}`` outside any brace group; ``\{`` and ``\}`` count as literal braces.
- ``## Context`` is user-authored, free-form, and fed to the LLM verbatim
  when generating variations.
- ``## Variations`` is managed by Mnemonic between the
  ``<!-- mnemonic:variations:begin/end -->`` markers. The LLM sees prior
  variations next time, defeating "I memorised the wording of this card".

Decks and Per-Deck Config
-------------------------

A deck is just a folder. To give one a custom name or override defaults
(variation frequency, leech threshold, daily limits), drop a ``_deck.md``
file in the folder:

.. code-block:: markdown

   ---
   deck_name: Game Theory
   variation_enabled: true
   variation_frequency: 0.6
   leech_threshold: 8
   daily_review_limit: 50
   daily_new_limit: 10
   ---

   # Free-form description for humans; not parsed.

Folders without a ``_deck.md`` inherit from the nearest ancestor's
``_deck.md``, or from the user-global config.

Review Sessions
---------------

Pressing **Start review** in the frontend triggers, in order:

1. Pre-flight checks against the vault Git repo: refuse to start if the
   working tree is dirty, refuse if the remote has commits that don't
   fast-forward into local. Network failure is tolerated and the session
   continues offline.
2. A scan to extract due cards.
3. The interactive review loop. LLM-generated variations may appear
   instead of the base card; you rate them on the standard 1–4 FSRS scale.
4. A commit of all changes (block-ID injections, variation log entries,
   ``state.sqlite``) with message
   ``mnemonic: review session YYYY-MM-DD (N reviews, M variations)``.
5. A push to the remote.

Settings and Usage
------------------

- **Settings** page is read-only in Phase 1. Edit
  ``~/.config/mnemonic/config.toml`` and restart the backend to change
  models, budget caps, or default deck behaviour.
- **Usage** page reports today's cost, last-30-days cost, and cache hit
  rate. Sustained cache hit rate below ~80 % across a session probably
  means a SKILL or strategy file is changing too often.

Troubleshooting
---------------

- *Vault status banner shows "uncommitted changes"*: Someone (you, or
  another editor) has touched the vault outside Mnemonic since the last
  session. Commit or stash in your editor before starting a session.
- *Vault status banner shows "unpushed commits"*: The last session
  committed locally but couldn't push (likely offline). The next session
  will retry.
- *Malformed note error*: The scanner now skips bad notes rather than
  crashing. Check ``<vault>/.mnemonic/scan.log`` for the offending path.

For deeper detail on note structure and trade-offs, read the spec at
``docs/superpowers/specs/2026-05-10-vault-storage-design.md``.
