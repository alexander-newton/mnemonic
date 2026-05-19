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
