"""ReviewLog repository for data access.

Provides data access operations for ReviewLog entities including card history,
user review statistics, and recent review queries for analytics.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from mnemonic.db.models.review_log import ReviewLog
from mnemonic.db.repositories.base import BaseRepository


class ReviewLogRepository(BaseRepository[ReviewLog]):
    """Repository for ReviewLog entities.

    Extends BaseRepository with ReviewLog-specific query methods.
    """

    def __init__(self) -> None:
        """Initialize ReviewLogRepository with ReviewLog model."""
        super().__init__(ReviewLog)

    def get_by_card(
        self,
        session: Session,
        card_id: uuid.UUID,
        limit: int = 100,
    ) -> list[ReviewLog]:
        """Get review history for a card.

        Args:
            session: SQLAlchemy session.
            card_id: ID of card to get review history for.
            limit: Maximum number of reviews to return (default 100).

        Returns:
            List of ReviewLog entities for the card, ordered by most recent first.
        """
        return (
            session.query(ReviewLog)
            .filter(ReviewLog.card_id == card_id)
            .order_by(ReviewLog.review_time.desc())
            .limit(limit)
            .all()
        )

    def get_by_user(
        self,
        session: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ReviewLog]:
        """Get review history for a user with pagination.

        Args:
            session: SQLAlchemy session.
            user_id: ID of user to get reviews for.
            skip: Number of reviews to skip (default 0).
            limit: Maximum number of reviews to return (default 100).

        Returns:
            List of ReviewLog entities for the user.
        """
        return (
            session.query(ReviewLog)
            .filter(ReviewLog.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_recent(
        self,
        session: Session,
        user_id: uuid.UUID,
        days: int = 7,
    ) -> list[ReviewLog]:
        """Get recent reviews for a user from the last N days.

        Args:
            session: SQLAlchemy session.
            user_id: ID of user to get recent reviews for.
            days: Number of days to look back (default 7).

        Returns:
            List of ReviewLog entities from the specified time period.
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        return (
            session.query(ReviewLog)
            .filter(
                and_(
                    ReviewLog.user_id == user_id,
                    ReviewLog.review_time >= cutoff_time,
                )
            )
            .all()
        )
