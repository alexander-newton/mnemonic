"""Deck service: thin façade over VaultRepository."""

from __future__ import annotations

from mnemonic.vault.repository import VaultRepository, Deck


class DeckService:
    def __init__(self, *, repo: VaultRepository):
        self.repo = repo

    def list(self) -> list[Deck]:
        return self.repo.list_decks()

    def get(self, folder_name: str) -> Deck | None:
        for d in self.repo.list_decks():
            if d.folder.name == folder_name:
                return d
        return None
