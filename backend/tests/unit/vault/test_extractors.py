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
