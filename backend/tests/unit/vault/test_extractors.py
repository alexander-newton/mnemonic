import pytest
from mnemonic.vault.extractors.cloze import extract_cloze, ExtractedCard
from mnemonic.vault.extractors.highlight import extract_highlight
from mnemonic.vault.extractors.callout import extract_callout
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


def test_dispatcher_picks_cloze():
    from mnemonic.vault.extractors import extract_card

    card = extract_card("A {{c1::NE}} is stable.")
    assert card.syntax == "cloze"


def test_dispatcher_picks_highlight():
    from mnemonic.vault.extractors import extract_card

    card = extract_card("A ==NE== is stable.")
    assert card.syntax == "highlight"


def test_dispatcher_picks_callout():
    from mnemonic.vault.extractors import extract_card

    card = extract_card("> [!card]\n> **Q:** q?\n> **A:** a.")
    assert card.syntax == "callout"


def test_dispatcher_mixed_syntax_raises():
    from mnemonic.vault.extractors import extract_card

    with pytest.raises(InvalidCardSyntaxError):
        extract_card("A {{c1::NE}} is ==stable==.")


def test_dispatcher_no_syntax_raises():
    from mnemonic.vault.extractors import extract_card

    with pytest.raises(InvalidCardSyntaxError):
        extract_card("plain text")
