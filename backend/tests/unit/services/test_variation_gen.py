"""Tests for variation-generation target selection and the run loop."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import Base, TrainingExample, VariationMeta
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.variation_gen import select_targets
from mnemonic.vault.repository import VaultRepository

WHEN = datetime(2026, 7, 1, 12, 0, 0)


def _deck_md(enabled: bool = True) -> str:
    return (
        f"---\ndeck_name: GT\nvariation_enabled: {str(enabled).lower()}\n"
        "variation_frequency: 1.0\nleech_threshold: 8\n"
        "daily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )


def _card_note(n: int) -> str:
    # Use valid hex block IDs; inject_block_id generates card-XXXXXXXX format
    block_id = f"{n:08x}"
    return f"---\ntitle: n{n}\n---\n## Card\n\nA {{{{c1::term{n}}}}}. ^card-{block_id}\n"


def _setup(tmp_path: Path, *, enabled: bool = True, n_cards: int = 3):
    vault = tmp_path / "vault"
    deck = vault / "01_Projects" / "gt"
    deck.mkdir(parents=True)
    (deck / "_deck.md").write_text(_deck_md(enabled))
    for i in range(n_cards):
        (deck / f"n{i}.qmd").write_text(_card_note(i))
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return VaultRepository(vault_root=vault, engine=engine), engine


def _add_variation(engine, card_id: str, vid: str, *, invalidated=None):
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id=vid,
                card_id=card_id,
                strategy="rephrase",
                model="m",
                generated_at=WHEN,
                shown_count=0,
                helpful_count=0,
                content_hash="h",
                note_path="n.qmd",
                invalidated_at=invalidated,
            )
        )
        s.add(
            TrainingExample(
                id=f"te-{vid}",
                card_id=card_id,
                variation_id=vid,
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=0,
                created_at=WHEN,
            )
        )


def test_targets_are_cards_without_live_variations(tmp_path: Path):
    repo, engine = _setup(tmp_path)
    _add_variation(engine, "card-00000000", "v0")  # n0 already covered

    targets = select_targets(repo, engine, deck=None, limit=10)

    assert [t.card.card_id for t in targets] == ["card-00000001", "card-00000002"]


def test_invalidated_variations_do_not_count_as_coverage(tmp_path: Path):
    repo, engine = _setup(tmp_path, n_cards=1)
    _add_variation(engine, "card-00000000", "v0", invalidated=WHEN)

    targets = select_targets(repo, engine, deck=None, limit=10)

    assert [t.card.card_id for t in targets] == ["card-00000000"]


def test_disabled_deck_yields_no_targets(tmp_path: Path):
    repo, engine = _setup(tmp_path, enabled=False)
    assert select_targets(repo, engine, deck=None, limit=10) == []


def test_limit_caps_targets(tmp_path: Path):
    repo, engine = _setup(tmp_path, n_cards=5)
    assert len(select_targets(repo, engine, deck=None, limit=2)) == 2


def test_deck_filter(tmp_path: Path):
    repo, engine = _setup(tmp_path)
    assert select_targets(repo, engine, deck="gt", limit=10) != []
    assert select_targets(repo, engine, deck="other", limit=10) == []


def test_note_inputs_returns_raw_card_section_and_context(tmp_path: Path):
    from mnemonic.services.variation_gen import note_inputs

    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n## Card\n\nA {{c1::term}}. ^card-n0\n\n"
        "## Context\n\nSome context here.\n"
    )

    card_section, context = note_inputs(note)

    assert "{{c1::term}}" in card_section  # raw markers, NOT build_faces output
    assert "Some context here." in context


def test_note_inputs_context_is_empty_when_absent(tmp_path: Path):
    from mnemonic.services.variation_gen import note_inputs

    note = tmp_path / "n.qmd"
    note.write_text("---\ntitle: t\n---\n## Card\n\nA {{c1::term}}. ^card-n0\n")

    _, context = note_inputs(note)

    assert context == ""


def test_recent_ratings_newest_first_and_capped(tmp_path: Path):
    from mnemonic.db.models import ReviewLog
    from mnemonic.services.variation_gen import recent_ratings

    _, engine = _setup(tmp_path, n_cards=1)
    with session_scope(engine) as s:
        for i, rating in enumerate([1, 2, 3, 4, 1, 2]):
            s.add(
                ReviewLog(
                    id=f"r{i}",
                    card_id="card-00000000",
                    rating=rating,
                    response_time_ms=100,
                    review_time=datetime(2026, 7, 1, 12, i, 0),
                )
            )

    got = recent_ratings(engine, "card-00000000", n=3)

    assert got == [2, 1, 4]  # newest first, capped at 3


def test_prior_variations_excludes_invalidated(tmp_path: Path):
    from mnemonic.services.variation_gen import prior_variations

    _, engine = _setup(tmp_path, n_cards=1)
    _add_variation(engine, "card-00000000", "v-live")
    _add_variation(engine, "card-00000000", "v-dead", invalidated=WHEN)

    got = prior_variations(engine, "card-00000000")

    assert len(got) == 1
    assert set(got[0]) == {"q", "a", "rating"}
    assert got[0]["q"] == "vq"


def _stub_generator():
    """A VariationGenerator whose client returns a canned Completion."""
    from unittest.mock import MagicMock

    from mnemonic.llm.client import Completion, Usage
    from mnemonic.llm.variation.generator import VariationGenerator

    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: Rephrased?\nA: Yes.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=10,
            output_tokens=5,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_millicents=7,
        ),
    )
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    return VariationGenerator(client=client, prompts_dir=prompts_dir), client


def test_generate_for_card_persists_everything(tmp_path: Path):
    from mnemonic.core.optimization.registry import ensure_champion_versions
    from mnemonic.db.models import LLMUsage, TrainingExample, VariationMeta
    from mnemonic.services.variation_gen import generate_for_card, select_targets

    repo, engine = _setup(tmp_path, n_cards=1)
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    with session_scope(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=WHEN)
    generator, client = _stub_generator()
    target = select_targets(repo, engine, deck=None, limit=1)[0]

    variation_id = generate_for_card(
        target,
        engine=engine,
        generator=generator,
        vault_root=repo.vault_root,
        model_default="m-default",
        model_rephrase="m-rephrase",
    )

    assert client.generate.called
    with session_scope(engine) as s:
        meta = s.get(VariationMeta, variation_id)
        assert meta is not None
        assert meta.card_id == "card-00000000"
        assert meta.arm == "champion"
        assert meta.prompt_version_id is not None
        assert meta.shown_count == 0
        assert (
            s.query(TrainingExample).filter(TrainingExample.variation_id == variation_id).count()
            == 1
        )
        assert s.query(LLMUsage).count() == 1
    assert "### " in target.card.note_path.read_text()  # note entry appended


def _seed_champions(engine):
    from mnemonic.core.optimization.registry import ensure_champion_versions

    prompts_dir = (
        Path(__file__).resolve().parents[3] / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    with session_scope(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=WHEN)


def test_run_generate_happy_path(tmp_path: Path):
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, _ = _stub_generator()

    report = run_generate(
        repo=repo,
        engine=engine,
        generator=generator,
        deck=None,
        limit=10,
        model_default="d",
        model_rephrase="r",
        daily_cents=1000,
        monthly_cents=10000,
    )

    assert len(report.generated) == 2
    assert report.skipped == []
    assert report.budget_stopped is False


def test_run_generate_skips_a_failing_card_and_continues(tmp_path: Path):
    from mnemonic.exceptions import LLMError
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, client = _stub_generator()
    ok = client.generate.return_value
    client.generate.side_effect = [LLMError("bad response"), ok]

    report = run_generate(
        repo=repo,
        engine=engine,
        generator=generator,
        deck=None,
        limit=10,
        model_default="d",
        model_rephrase="r",
        daily_cents=1000,
        monthly_cents=10000,
    )

    assert len(report.generated) == 1
    assert len(report.skipped) == 1
    assert "bad response" in report.skipped[0][1]
    assert report.budget_stopped is False


def test_run_generate_stops_when_budget_exhausted(tmp_path: Path):
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, client = _stub_generator()

    report = run_generate(
        repo=repo,
        engine=engine,
        generator=generator,
        deck=None,
        limit=10,
        model_default="d",
        model_rephrase="r",
        daily_cents=0,
        monthly_cents=0,
    )

    assert report.generated == []
    assert report.budget_stopped is True
    assert client.generate.call_count == 0


def test_run_generate_dry_run_makes_no_calls(tmp_path: Path):
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, client = _stub_generator()

    report = run_generate(
        repo=repo,
        engine=engine,
        generator=generator,
        deck=None,
        limit=10,
        model_default="d",
        model_rephrase="r",
        daily_cents=1000,
        monthly_cents=10000,
        dry_run=True,
    )

    assert client.generate.call_count == 0
    assert report.generated == []
    assert len(report.targets) == 2
