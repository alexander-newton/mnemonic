"""The brand-new FSRS defaults, single source of truth."""

from __future__ import annotations

import dataclasses

import pytest

from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS


def test_new_card_defaults_values():
    assert NEW_CARD_DEFAULTS.state == "new"
    assert NEW_CARD_DEFAULTS.stability == 0.0
    assert NEW_CARD_DEFAULTS.difficulty == 5.0
    assert NEW_CARD_DEFAULTS.due is None
    assert NEW_CARD_DEFAULTS.reps == 0
    assert NEW_CARD_DEFAULTS.lapses == 0


def test_new_card_defaults_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        NEW_CARD_DEFAULTS.stability = 9.9  # type: ignore[misc]
