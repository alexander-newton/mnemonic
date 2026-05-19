"""Vault repository: presents Card/Deck objects to the rest of the app.

Combines the read-side scan with SQLite scheduling state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.db.models import SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.vault.deck import DeckConfig
from mnemonic.vault.scanner import ScannedCard, scan_vault


@dataclass(frozen=True)
class Card:
    card_id: str
    note_path: Path
    deck_folder: Path
    syntax: str
    front: str
    back: str
    title: str
    state: str
    stability: float
    difficulty: float
    due: datetime | None
    reps: int
    lapses: int
    leech_score: float
    suspended: bool


@dataclass(frozen=True)
class Deck:
    folder: Path
    name: str
    config: DeckConfig | None


class VaultRepository:
    def __init__(self, vault_root: Path, engine: Engine):
        self.vault_root = vault_root
        self.engine = engine

    def _scan(self) -> list[ScannedCard]:
        return list(scan_vault(self.vault_root, inject_missing_ids=True))

    def list_cards(self) -> list[Card]:
        scanned = self._scan()
        ids = [c.card_id for c in scanned]
        with session_scope(self.engine) as s:
            rows = (
                s.query(SchedulingState).filter(SchedulingState.card_id.in_(ids)).all()
                if ids else []
            )
            by_id = {r.card_id: r for r in rows}
        out: list[Card] = []
        for sc in scanned:
            row = by_id.get(sc.card_id)
            out.append(
                Card(
                    card_id=sc.card_id,
                    note_path=sc.note_path,
                    deck_folder=sc.deck_folder,
                    syntax=sc.syntax,
                    front=sc.front,
                    back=sc.back,
                    title=sc.title,
                    state=row.state if row else "new",
                    stability=row.stability if row else 0.0,
                    difficulty=row.difficulty if row else 5.0,
                    due=row.due if row else None,
                    reps=row.reps if row else 0,
                    lapses=row.lapses if row else 0,
                    leech_score=row.leech_score if row else 0.0,
                    suspended=bool(row.suspended) if row else False,
                )
            )
        return out

    def list_decks(self) -> list[Deck]:
        seen: dict[Path, Deck] = {}
        for sc in self._scan():
            if sc.deck_folder not in seen:
                name = sc.deck_config.deck_name if sc.deck_config else sc.deck_folder.name
                seen[sc.deck_folder] = Deck(folder=sc.deck_folder, name=name, config=sc.deck_config)
        return list(seen.values())

    def get_card(self, card_id: str) -> Card | None:
        for c in self.list_cards():
            if c.card_id == card_id:
                return c
        return None
