"""User repository for data access.

Provides data access operations for User entities with email-based lookups
and user creation with validation.
"""

from typing import Any

from sqlalchemy.orm import Session

from mnemonic.db.models.user import User
from mnemonic.db.repositories.base import BaseRepository
from mnemonic.exceptions import NotFoundError


class UserRepository(BaseRepository[User]):
    """Repository for User entities.

    Extends BaseRepository with User-specific query methods.
    """

    def __init__(self) -> None:
        """Initialize UserRepository with User model."""
        super().__init__(User)

    def get_by_email(self, session: Session, email: str) -> User:
        """Get user by email address.

        Args:
            session: SQLAlchemy session.
            email: Email address to look up.

        Returns:
            The User entity.

        Raises:
            NotFoundError: If user with email is not found.
        """
        user = session.query(User).filter(User.email == email).first()
        if user is None:
            raise NotFoundError(f"User with email '{email}' not found")
        return user

    def exists_by_email(self, session: Session, email: str) -> bool:
        """Check if user with email exists.

        Args:
            session: SQLAlchemy session.
            email: Email address to check.

        Returns:
            True if user exists, False otherwise.
        """
        user = session.query(User).filter(User.email == email).first()
        return user is not None

    def create_user(
        self,
        session: Session,
        email: str,
        password_hash: str,
        **kwargs: Any,
    ) -> User:
        """Create a new user with email and password hash.

        Args:
            session: SQLAlchemy session.
            email: User's email address.
            password_hash: Hashed password.
            **kwargs: Additional keyword arguments (fsrs_params, settings, etc.).

        Returns:
            The newly created User entity.
        """
        return self.create(
            session,
            email=email,
            password_hash=password_hash,
            **kwargs,
        )
