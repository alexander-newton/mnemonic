"""The labeling job: turn shown variations into rewarded TrainingExamples."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.fsrs.algorithm import calculate_retrievability
from mnemonic.core.optimization.reward import (
    RewardConfig,
    SubsequentReview,
    compute_reward,
)
from mnemonic.db.models import ReviewLog, SchedulingState, TrainingExample
from mnemonic.db.sqlite import session_scope

# A review rating >= 2 counts as a successful recall (1 = "again"/lapse).
MIN_SUCCESS_RATING = 2


@dataclass(frozen=True)
class LabelingReport:
    """Summary of one labeling run.

    Attributes:
        labeled: Examples that received or updated a reward this run.
        pending: Examples left unlabeled (no anchor / no usable reviews yet).
        finalized_skipped: Already-finalized examples that were not revisited.
    """

    labeled: int = 0
    pending: int = 0
    finalized_skipped: int = 0


def _to_reward_config(config: OptimizationConfig) -> RewardConfig:
    return RewardConfig(
        gamma=config.reward_decay_gamma,
        window_k=config.reward_window_k,
    )


def _subsequent_reviews(
    session: Session,
    *,
    card_id: str,
    anchor_time: datetime,
    config: OptimizationConfig,
) -> list[SubsequentReview]:
    """Build the FSRS-adjusted subsequent-review list for a card.

    ``elapsed_days`` and the same-session-cram gap are both measured from the
    card's actual immediately-preceding review (which set the current
    ``stability_before``), so the clock advances on every review even when the
    review itself is excluded from the reward window.
    """
    rows = (
        session.execute(
            select(ReviewLog)
            .where(ReviewLog.card_id == card_id, ReviewLog.review_time > anchor_time)
            .order_by(ReviewLog.review_time.asc())
        )
        .scalars()
        .all()
    )

    result: list[SubsequentReview] = []
    last_review_time = anchor_time
    for row in rows:
        gap_hours = (row.review_time - last_review_time).total_seconds() / 3600.0
        elapsed_days = (row.review_time - last_review_time).total_seconds() / 86400.0
        is_cram = gap_hours < config.min_interval_hours
        stability_before: float | None = row.stability_before
        stability_usable = stability_before is not None and stability_before > 0
        if not is_cram and stability_usable and stability_before is not None:
            r_pred = calculate_retrievability(stability=stability_before, elapsed_days=elapsed_days)
            result.append(
                SubsequentReview(
                    success=row.rating >= MIN_SUCCESS_RATING,
                    predicted_retrievability=r_pred,
                )
            )
        last_review_time = row.review_time
    return result


def run_labeling_job(engine: Engine, config: OptimizationConfig) -> LabelingReport:
    """Label all non-finalized TrainingExamples whose reviews have landed.

    Idempotent: finalized examples are never revisited; non-finalized ones are
    re-evaluated each run as more reviews accrue.

    Args:
        engine: SQLAlchemy engine for the state database.
        config: Optimization configuration (reward window parameters).

    Returns:
        A LabelingReport summarizing the run.
    """
    reward_config = _to_reward_config(config)
    labeled = pending = finalized_skipped = 0

    with session_scope(engine) as session:
        examples = (
            session.execute(
                select(TrainingExample).where(TrainingExample.variation_id.is_not(None))
            )
            .scalars()
            .all()
        )

        for example in examples:
            if example.finalized:
                finalized_skipped += 1
                continue

            anchor = session.execute(
                select(ReviewLog)
                .where(ReviewLog.variation_id == example.variation_id)
                .order_by(ReviewLog.review_time.asc())
                .limit(1)
            ).scalar_one_or_none()
            if anchor is None:
                pending += 1
                continue

            scheduling = session.get(SchedulingState, example.card_id)
            card_retired = bool(scheduling and scheduling.suspended)

            reviews = _subsequent_reviews(
                session,
                card_id=example.card_id,
                anchor_time=anchor.review_time,
                config=config,
            )
            result = compute_reward(reviews, reward_config, card_retired=card_retired)

            if result.reward is None and not result.finalized:
                pending += 1
                continue

            example.reward = result.reward
            example.maturity = result.maturity
            example.finalized = result.finalized
            example.label = int(
                result.reward is not None and result.reward > config.demo_margin_delta
            )
            labeled += 1

    return LabelingReport(labeled=labeled, pending=pending, finalized_skipped=finalized_skipped)
