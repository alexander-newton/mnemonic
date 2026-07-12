from datetime import datetime
from pathlib import Path
from mnemonic.db.models import Base, SchedulingState, ReviewLog
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.review import ReviewService
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA ==NE==. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def test_rate_new_card_creates_state_and_log(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    svc = ReviewService(repo=repo, engine=engine)
    svc.rate(card_id="card-aaaabbbb", rating=3, response_time_ms=1500)
    with session_scope(engine) as s:
        state = s.get(SchedulingState, "card-aaaabbbb")
        assert state is not None
        assert state.reps == 1
        logs = s.query(ReviewLog).filter_by(card_id="card-aaaabbbb").all()
        assert len(logs) == 1
        assert logs[0].rating == 3


def test_rate_failure_increments_lapses(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    svc = ReviewService(repo=repo, engine=engine)
    svc.rate(card_id="card-aaaabbbb", rating=3, response_time_ms=1000)
    svc.rate(card_id="card-aaaabbbb", rating=1, response_time_ms=1000)
    with session_scope(engine) as s:
        state = s.get(SchedulingState, "card-aaaabbbb")
        # FSRS schedule_review returns new_lapses; the service stores that exact value.
        # After a 3 then a 1, FSRS should have new_lapses == 1.
        assert state.lapses >= 1


def test_rate_records_deck_folder(tmp_path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    repo = VaultRepository(vault_root=vault, engine=engine)

    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb", rating=3, response_time_ms=1200
    )

    with session_scope(engine) as s:
        row = s.query(ReviewLog).filter(ReviewLog.card_id == "card-aaaabbbb").one()
        assert row.deck_folder == "gt"
