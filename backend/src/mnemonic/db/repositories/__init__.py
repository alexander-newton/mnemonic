"""Database repository layer.

Repositories provide the data access abstraction layer for the application,
implementing the Repository pattern with consistent error handling and
pagination support.
"""

from mnemonic.db.repositories.base import BaseRepository
from mnemonic.db.repositories.card import CardRepository
from mnemonic.db.repositories.deck import DeckRepository
from mnemonic.db.repositories.review_log import ReviewLogRepository
from mnemonic.db.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "CardRepository",
    "DeckRepository",
    "ReviewLogRepository",
    "UserRepository",
]
