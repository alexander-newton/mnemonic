"""Database repository layer.

Repositories provide the data access abstraction layer for the application,
implementing the Repository pattern with consistent error handling and
pagination support.

Note: CardRepository, DeckRepository, and UserRepository were removed in the
vault-backed storage refactor. VaultRepository (in mnemonic.vault) is the
new storage facade for card/deck data.
"""

from mnemonic.db.repositories.base import BaseRepository
from mnemonic.db.repositories.review_log import ReviewLogRepository

__all__ = [
    "BaseRepository",
    "ReviewLogRepository",
]
