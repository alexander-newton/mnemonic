"""Collapse the policy cascade into one EffectivePolicy for a deck.

Precedence weakest -> strongest: built-in defaults, config [defaults] / _deck.md (both
folded into the SeedLimits the caller passes), then policy.toml rules in file order
(later matching rules override earlier ones, key by key).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from mnemonic.core.policy.rules import Rule


@dataclass(frozen=True)
class Limits:
    """Per-scope limits. None means unlimited."""

    per_day: int | None = None
    per_session: int | None = None


@dataclass(frozen=True)
class EffectivePolicy:
    """The fully-resolved policy for one deck."""

    all: Limits
    new: Limits
    due: Limits
    order: str
    interleave_new_every: int | None


@dataclass(frozen=True)
class SeedLimits:
    """The new/due per-day limits seeded from config [defaults] or the deck's _deck.md."""

    new_per_day: int | None
    due_per_day: int | None


def resolve_policy(*, seed: SeedLimits, rules: list[Rule], deck: str) -> EffectivePolicy:
    """Apply the ordered rules on top of the seed for a given deck."""
    eff = EffectivePolicy(
        all=Limits(),
        new=Limits(per_day=seed.new_per_day),
        due=Limits(per_day=seed.due_per_day),
        order="due_first",
        interleave_new_every=None,
    )
    for rule in rules:
        if rule.deck is not None and rule.deck != deck:
            continue
        eff = _apply(eff, rule)
    return eff


def _apply(eff: EffectivePolicy, rule: Rule) -> EffectivePolicy:
    slot: Limits = getattr(eff, rule.scope)
    new_slot = Limits(
        per_day=rule.per_day if rule.per_day is not None else slot.per_day,
        per_session=rule.per_session if rule.per_session is not None else slot.per_session,
    )
    order = rule.order if rule.order is not None else eff.order
    ine = (
        rule.interleave_new_every
        if rule.interleave_new_every is not None
        else eff.interleave_new_every
    )
    if rule.scope == "all":
        return replace(eff, all=new_slot, order=order, interleave_new_every=ine)
    elif rule.scope == "new":
        return replace(eff, new=new_slot, order=order, interleave_new_every=ine)
    else:  # rule.scope == "due"
        return replace(eff, due=new_slot, order=order, interleave_new_every=ine)
