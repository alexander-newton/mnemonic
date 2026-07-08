"""FastAPI dependency injection: VaultRepository + engine + services."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine

from mnemonic.config import Config, load_config
from mnemonic.db.sqlite import create_engine
from mnemonic.services.card import CardService
from mnemonic.services.deck import DeckService
from mnemonic.services.reconciliation import ReconciliationService
from mnemonic.vault.repository import VaultRepository


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    cfg = get_config()
    return create_engine(cfg.vault.path / ".mnemonic" / "state.sqlite")


def get_repo() -> VaultRepository:
    cfg = get_config()
    return VaultRepository(vault_root=cfg.vault.path, engine=get_engine())


def get_deck_service() -> DeckService:
    return DeckService(repo=get_repo())


def get_card_service() -> CardService:
    return CardService(repo=get_repo())


def get_reconciliation_service() -> ReconciliationService:
    cfg = get_config()
    return ReconciliationService(vault_root=cfg.vault.path, engine=get_engine())
