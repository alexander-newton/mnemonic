"""Tests for resolving the policy cascade into an EffectivePolicy."""

from __future__ import annotations

from mnemonic.core.policy.resolve import EffectivePolicy, Limits, SeedLimits, resolve_policy
from mnemonic.core.policy.rules import Rule


def _rule(**kw):
    base = {
        "deck": None,
        "scope": "all",
        "per_day": None,
        "per_session": None,
        "order": None,
        "interleave_new_every": None,
        "minutes_per_day": None,
        "minutes_per_session": None,
    }
    base.update(kw)
    return Rule(**base)


SEED = SeedLimits(new_per_day=20, due_per_day=200)


def test_seed_only_defaults():
    eff = resolve_policy(seed=SEED, rules=[], deck="gt")
    assert eff == EffectivePolicy(
        all=Limits(None, None),
        new=Limits(20, None),
        due=Limits(200, None),
        order="due_first",
        interleave_new_every=None,
    )


def test_scopes_resolve_independently():
    rules = [_rule(scope="new", per_day=10), _rule(scope="due", per_session=50)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.new == Limits(10, None)
    assert eff.due == Limits(200, 50)


def test_later_rule_overrides_earlier_key_by_key():
    rules = [_rule(scope="new", per_day=10, per_session=5), _rule(scope="new", per_day=8)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.new == Limits(8, 5)  # per_day overridden, per_session preserved


def test_deck_scoped_rule_only_applies_to_that_deck():
    rules = [_rule(deck="gt", scope="new", per_day=3)]
    assert resolve_policy(seed=SEED, rules=rules, deck="gt").new.per_day == 3
    assert resolve_policy(seed=SEED, rules=rules, deck="econ").new.per_day == 20


def test_order_and_interleave_applied():
    rules = [_rule(order="interleave", interleave_new_every=4)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.order == "interleave" and eff.interleave_new_every == 4


def test_time_keys_unset_are_none():
    eff = resolve_policy(seed=SEED, rules=[], deck="gt")
    assert eff.minutes_per_day is None and eff.minutes_per_session is None


def test_time_keys_resolve_top_level():
    rules = [_rule(minutes_per_day=40, minutes_per_session=25)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.minutes_per_day == 40 and eff.minutes_per_session == 25


def test_later_time_rule_overrides_earlier():
    rules = [_rule(minutes_per_day=40), _rule(minutes_per_day=10)]
    eff = resolve_policy(seed=SEED, rules=rules, deck="gt")
    assert eff.minutes_per_day == 10
