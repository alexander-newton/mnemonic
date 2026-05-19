"""Build cache_control blocks for the variation prompt."""

from __future__ import annotations

from mnemonic.llm.client import Block

EPHEMERAL_1H = {"type": "ephemeral", "ttl": "1h"}
EPHEMERAL_5M = {"type": "ephemeral"}


def build_cached_system(*, skill_md: str, strategy_md: str, note_context: str) -> list[Block]:
    """Return system blocks ordered SKILL → strategy → context, each with cache_control.

    Args:
        skill_md: Skill markdown content (strategy definitions)
        strategy_md: Strategy markdown content (variation strategy)
        note_context: Note context content (card notes)

    Returns:
        List of three Block objects with appropriate cache_control settings.
    """
    return [
        Block(text=skill_md, cache_control=EPHEMERAL_1H),
        Block(text=strategy_md, cache_control=EPHEMERAL_1H),
        Block(text=note_context, cache_control=EPHEMERAL_5M),
    ]
