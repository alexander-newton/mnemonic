"""Card service: thin façade over VaultRepository."""

from __future__ import annotations

from mnemonic.vault.repository import VaultRepository, Card


class CardService:
    def __init__(self, *, repo: VaultRepository):
        self.repo = repo

    def list(self, *, deck_folder_name: str | None = None) -> list[Card]:
        cards = self.repo.list_cards()
        if deck_folder_name is None:
            return cards
        return [c for c in cards if c.deck_folder.name == deck_folder_name]

    def get(self, card_id: str) -> Card | None:
        return self.repo.get_card(card_id)
