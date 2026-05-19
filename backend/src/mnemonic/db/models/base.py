"""Base model configuration for SQLAlchemy.

This module provides the declarative base for all SQLAlchemy models
and common mixins for timestamps.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
