"""Base repository with common CRUD operations.

Provides the foundation for all repository implementations with standard
data access patterns for creating, reading, updating, and deleting entities.
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from mnemonic.exceptions import NotFoundError

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations.

    All repositories should inherit from this class to ensure consistent
    error handling and data access patterns.
    """

    def __init__(self, model: type[T]) -> None:
        """Initialize repository with a SQLAlchemy model class.

        Args:
            model: The SQLAlchemy model class this repository manages.
        """
        self.model = model

    def get(self, session: Session, entity_id: uuid.UUID) -> T:
        """Get entity by ID.

        Args:
            session: SQLAlchemy session.
            entity_id: ID of entity to retrieve.

        Returns:
            The entity instance.

        Raises:
            NotFoundError: If entity is not found.
        """
        entity = session.query(self.model).filter(self.model.id == entity_id).first()  # type: ignore[attr-defined]
        if entity is None:
            raise NotFoundError(f"{self.model.__name__} with id {entity_id} not found")
        return entity

    def get_all(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """Get all entities with pagination.

        Args:
            session: SQLAlchemy session.
            skip: Number of entities to skip (default 0).
            limit: Maximum number of entities to return (default 100).

        Returns:
            List of entities.
        """
        return session.query(self.model).offset(skip).limit(limit).all()

    def create(self, session: Session, **kwargs: Any) -> T:
        """Create a new entity.

        Args:
            session: SQLAlchemy session.
            **kwargs: Keyword arguments to pass to model constructor.

        Returns:
            The newly created entity instance.
        """
        entity = self.model(**kwargs)
        session.add(entity)
        session.commit()
        return entity

    def update(
        self,
        session: Session,
        entity_id: uuid.UUID,
        **kwargs: Any,
    ) -> T:
        """Update an existing entity.

        Args:
            session: SQLAlchemy session.
            entity_id: ID of entity to update.
            **kwargs: Keyword arguments with new values.

        Returns:
            The updated entity instance.

        Raises:
            NotFoundError: If entity is not found.
        """
        entity = self.get(session, entity_id)
        for key, value in kwargs.items():
            setattr(entity, key, value)
        session.commit()
        return entity

    def delete(self, session: Session, entity_id: uuid.UUID) -> None:
        """Delete an entity.

        Args:
            session: SQLAlchemy session.
            entity_id: ID of entity to delete.

        Raises:
            NotFoundError: If entity is not found.
        """
        entity = self.get(session, entity_id)
        session.delete(entity)
        session.commit()
