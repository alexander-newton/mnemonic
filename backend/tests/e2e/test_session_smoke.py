import subprocess
from pathlib import Path
from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.services.review import ReviewService
from mnemonic.vault.repository import VaultRepository
from mnemonic.vault.session import VaultSession


def test_full_session_cycle(fixture_vault: Path):
    engine = create_engine(fixture_vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    sess = VaultSession(vault_root=fixture_vault, engine=engine)
    sess.start()

    repo = VaultRepository(vault_root=fixture_vault, engine=engine)
    cards = repo.list_cards()
    assert len(cards) == 1
    card = cards[0]
    assert card.card_id.startswith("card-")  # ID injected during scan

    svc = ReviewService(repo=repo, engine=engine)
    svc.rate(card_id=card.card_id, rating=3, response_time_ms=1500)

    sess.end(n_reviews=1, n_variations=0)

    log = subprocess.check_output(
        ["git", "log", "--oneline"], cwd=fixture_vault
    ).decode()
    assert "mnemonic: review session" in log
    note_text = (fixture_vault / "01_Projects" / "game-theory" / "nash.qmd").read_text()
    assert "^card-" in note_text
