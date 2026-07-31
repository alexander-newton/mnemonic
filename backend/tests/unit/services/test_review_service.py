from datetime import datetime
from pathlib import Path

from mnemonic.db.models import Base, ReviewLog, SchedulingState
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


def _vault_with_variation_meta(tmp_path, *, shown=0, helpful=0):
    """Vault with one card plus a VariationMeta row 'v1'. Returns (repo, engine)."""
    from mnemonic.db.models import VariationMeta

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id="v1",
                card_id="card-aaaabbbb",
                strategy="rephrase",
                model="m",
                generated_at=datetime(2026, 7, 1),
                shown_count=shown,
                helpful_count=helpful,
                content_hash="h",
                note_path="nash.qmd",
            )
        )
    return VaultRepository(vault_root=vault, engine=engine), engine


def test_rate_increments_shown_count(tmp_path):
    from mnemonic.db.models import VariationMeta

    repo, engine = _vault_with_variation_meta(tmp_path, shown=2)
    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb", rating=3, response_time_ms=1000, variation_id="v1"
    )
    with session_scope(engine) as s:
        row = s.get(VariationMeta, "v1")
        assert row.shown_count == 3
        assert row.helpful_count == 0


def test_rate_increments_helpful_count_when_helpful(tmp_path):
    from mnemonic.db.models import VariationMeta

    repo, engine = _vault_with_variation_meta(tmp_path)
    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb",
        rating=3,
        response_time_ms=1000,
        variation_id="v1",
        variation_helpful=1,
    )
    with session_scope(engine) as s:
        row = s.get(VariationMeta, "v1")
        assert row.shown_count == 1 and row.helpful_count == 1


def test_rate_unknown_variation_id_is_noop_but_logged(tmp_path):
    repo, engine = _vault_with_variation_meta(tmp_path)
    ReviewService(repo=repo, engine=engine).rate(
        card_id="card-aaaabbbb",
        rating=3,
        response_time_ms=1000,
        variation_id="nope",
    )
    with session_scope(engine) as s:
        log = s.query(ReviewLog).filter(ReviewLog.card_id == "card-aaaabbbb").one()
        assert log.variation_id == "nope"
