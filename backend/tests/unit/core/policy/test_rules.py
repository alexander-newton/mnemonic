"""Tests for parsing policy.toml into rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from mnemonic.core.policy.rules import Rule, load_rules
from mnemonic.exceptions import PolicyError

_VALID = """
[[rule]]
per_day = 200
order = "due_first"

[[rule]]
scope = "new"
per_day = 20

[[rule]]
deck = "gt"
scope = "new"
per_day = 10
per_session = 5

[[rule]]
deck = "gt"
order = "interleave"
interleave_new_every = 5
"""


def _write(tmp_path: Path, body: str) -> Path:
    (tmp_path / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".mnemonic" / "policy.toml").write_text(body)
    return tmp_path


def test_missing_file_is_empty(tmp_path: Path):
    assert load_rules(tmp_path) == []


def test_parses_valid_rules_in_order(tmp_path: Path):
    rules = load_rules(_write(tmp_path, _VALID))
    assert len(rules) == 4
    assert rules[0] == Rule(
        deck=None,
        scope="all",
        per_day=200,
        per_session=None,
        order="due_first",
        interleave_new_every=None,
    )
    assert rules[2].deck == "gt" and rules[2].scope == "new"
    assert rules[2].per_day == 10 and rules[2].per_session == 5
    assert rules[3].order == "interleave" and rules[3].interleave_new_every == 5


def test_unknown_key_raises_with_index(tmp_path: Path):
    with pytest.raises(PolicyError, match="rule #0"):
        load_rules(_write(tmp_path, "[[rule]]\nper_dya = 5\n"))


def test_bad_scope_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="scope"):
        load_rules(_write(tmp_path, '[[rule]]\nscope = "everything"\n'))


def test_bad_order_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="order"):
        load_rules(_write(tmp_path, '[[rule]]\norder = "sideways"\n'))


def test_negative_limit_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="per_day"):
        load_rules(_write(tmp_path, "[[rule]]\nper_day = -3\n"))


def test_interleave_requires_positive_every(tmp_path: Path):
    with pytest.raises(PolicyError, match="interleave_new_every"):
        load_rules(_write(tmp_path, '[[rule]]\norder = "interleave"\n'))


def test_malformed_toml_raises(tmp_path: Path):
    with pytest.raises(PolicyError, match="valid TOML"):
        load_rules(_write(tmp_path, "this is = = not toml"))
