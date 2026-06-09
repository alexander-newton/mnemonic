"""Integration tests for the labeling job."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.fsrs.algorithm import calculate_retrievability
from mnemonic.core.optimization.labeling import run_labeling_job
from mnemonic.db.models import (
    Base,
    ReviewLog,
    SchedulingState,
    TrainingExample,
)


def _engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def _unlabeled_example(variation_id: str = "v1", card_id: str = "c1") -> TrainingExample:
    return TrainingExample(
        id="te-" + variation_id,
        card_id=card_id,
        variation_id=variation_id,
        prompt_version_id="pv1",
        base_q="q",
        base_a="a",
        variation_q="vq",
        variation_a="va",
        label=0,
        reward=None,
        maturity=0,
        finalized=False,
        rating=None,
        note_context=None,
        created_at=datetime(2026, 6, 1),
    )


def _review(card_id, variation_id, when, rating, stability_before):
    return ReviewLog(
        id=f"r-{when.isoformat()}",
        card_id=card_id,
        rating=rating,
        response_time_ms=1000,
        review_time=when,
        state_before="review",
        state_after="review",
        stability_before=stability_before,
        stability_after=stability_before,
        difficulty_before=5.0,
        difficulty_after=5.0,
        variation_id=variation_id,
        variation_helpful=None,
    )


def test_labels_example_after_next_review_lands():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        s.add(_review("c1", None, t0 + timedelta(days=5), rating=3, stability_before=10.0))
        s.commit()

        report = run_labeling_job(engine, OptimizationConfig())

        te = s.get(TrainingExample, "te-v1")
        assert te.reward is not None
        assert te.maturity == 1
        assert te.finalized is False
        assert report.labeled == 1


def test_example_without_anchor_review_stays_pending():
    engine = _engine()
    with Session(engine) as s:
        s.add(_unlabeled_example())  # no ReviewLog with variation_id="v1"
        s.commit()

        report = run_labeling_job(engine, OptimizationConfig())

        te = s.get(TrainingExample, "te-v1")
        assert te.reward is None
        assert te.maturity == 0
        assert te.finalized is False
        assert report.pending == 1


def test_same_day_cram_review_is_excluded():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        s.add(_review("c1", None, t0 + timedelta(hours=2), rating=1, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig(min_interval_hours=20.0))

        te = s.get(TrainingExample, "te-v1")
        assert te.maturity == 0
        assert te.reward is None


def test_finalizes_when_window_full_and_sets_demo_label():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        for days in (30, 60, 90):
            s.add(_review("c1", None, t0 + timedelta(days=days), rating=3, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig(demo_margin_delta=0.1))

        te = s.get(TrainingExample, "te-v1")
        assert te.maturity == 3
        assert te.finalized is True
        assert te.reward > 0.1
        assert te.label == 1


def test_suspended_card_finalizes_immature_example():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        s.add(_review("c1", None, t0 + timedelta(days=5), rating=3, stability_before=10.0))
        s.add(SchedulingState(card_id="c1", suspended=1))
        s.commit()

        run_labeling_job(engine, OptimizationConfig())

        te = s.get(TrainingExample, "te-v1")
        assert te.maturity == 1
        assert te.finalized is True


def test_job_is_idempotent_on_finalized_examples():
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        for days in (30, 60, 90):
            s.add(_review("c1", None, t0 + timedelta(days=days), rating=3, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig())
        second = run_labeling_job(engine, OptimizationConfig())
        assert second.labeled == 0
        assert second.finalized_skipped == 1


def test_cram_skip_then_eligible_measures_elapsed_from_actual_previous_review():
    # anchor at t0; a crammed review 10h later (excluded from the window but it
    # really happened and advances the clock); then an eligible review 5 days
    # after the cram. The eligible review's elapsed_days must be measured from
    # the cram (5.0 days), NOT from the anchor (~5.42 days), because its
    # stability_before reflects the crammed review's update.
    engine = _engine()
    t0 = datetime(2026, 6, 1, 9, 0)
    cram_time = t0 + timedelta(hours=10)
    eligible_time = cram_time + timedelta(days=5)
    with Session(engine) as s:
        s.add(_unlabeled_example())
        s.add(_review("c1", "v1", t0, rating=3, stability_before=10.0))
        s.add(_review("c1", None, cram_time, rating=3, stability_before=10.0))
        s.add(_review("c1", None, eligible_time, rating=3, stability_before=10.0))
        s.commit()

        run_labeling_job(engine, OptimizationConfig(min_interval_hours=20.0))

        te = s.get(TrainingExample, "te-v1")
        # Only the eligible review contributes (cram excluded).
        assert te.maturity == 1
        expected_r = calculate_retrievability(stability=10.0, elapsed_days=5.0)
        expected_reward = 1.0 - expected_r
        assert math.isclose(te.reward, expected_reward, rel_tol=1e-9)
