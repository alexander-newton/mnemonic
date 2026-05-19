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
