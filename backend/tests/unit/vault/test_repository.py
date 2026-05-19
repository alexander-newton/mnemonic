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
