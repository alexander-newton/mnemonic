"""Parse <vault>/.mnemonic/policy.toml into an ordered list of Rule objects."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from mnemonic.exceptions import PolicyError

_SCOPES = ("all", "new", "due")
_ORDERS = ("due_first", "new_first", "interleave", "shuffle")
_ALLOWED_KEYS = {
    "deck",
    "scope",
    "per_day",
    "per_session",
    "order",
    "interleave_new_every",
    "minutes_per_day",
    "minutes_per_session",
}


@dataclass(frozen=True)
class Rule:
    """One rule from policy.toml. None fields mean 'do not touch this key'."""

    deck: str | None
    scope: Literal["all", "new", "due"]
    per_day: int | None
    per_session: int | None
    order: Literal["due_first", "new_first", "interleave", "shuffle"] | None
    interleave_new_every: int | None
    minutes_per_day: int | None = None
    minutes_per_session: int | None = None


def load_rules(vault_root: Path) -> list[Rule]:
    """Parse the vault's policy.toml. Missing file → []. Malformed → PolicyError."""
    path = vault_root / ".mnemonic" / "policy.toml"
    if not path.exists():
        return []
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"policy.toml is not valid TOML: {exc}") from exc
    raw = data.get("rule", [])
    if not isinstance(raw, list):
        raise PolicyError("policy.toml: [[rule]] must be an array of tables.")
    return [_parse_rule(i, r) for i, r in enumerate(raw)]


def _parse_rule(index: int, raw: dict) -> Rule:
    unknown = set(raw) - _ALLOWED_KEYS
    if unknown:
        raise PolicyError(f"policy.toml rule #{index}: unknown key(s) {sorted(unknown)}.")
    scope = raw.get("scope", "all")
    if scope not in _SCOPES:
        raise PolicyError(
            f"policy.toml rule #{index}: scope must be one of {_SCOPES}, got '{scope}'."
        )
    order = raw.get("order")
    if order is not None and order not in _ORDERS:
        raise PolicyError(
            f"policy.toml rule #{index}: order must be one of {_ORDERS}, got '{order}'."
        )
    per_day = _non_negative(index, "per_day", raw.get("per_day"))
    per_session = _non_negative(index, "per_session", raw.get("per_session"))
    ine = _non_negative(index, "interleave_new_every", raw.get("interleave_new_every"))
    if ine is not None and ine < 1:
        raise PolicyError(
            f"policy.toml rule #{index}: interleave_new_every must be >= 1, got {ine}."
        )
    if order == "interleave" and ine is None:
        raise PolicyError(
            f"policy.toml rule #{index}: order='interleave' requires interleave_new_every."
        )
    minutes_per_day = _non_negative(index, "minutes_per_day", raw.get("minutes_per_day"))
    minutes_per_session = _non_negative(
        index, "minutes_per_session", raw.get("minutes_per_session")
    )
    if (minutes_per_day is not None or minutes_per_session is not None) and scope != "all":
        raise PolicyError(
            f"policy.toml rule #{index}: minutes_per_day/minutes_per_session are only "
            f"allowed on scope='all', not '{scope}'."
        )
    return Rule(
        deck=raw.get("deck"),
        scope=scope,
        per_day=per_day,
        per_session=per_session,
        order=order,
        interleave_new_every=ine,
        minutes_per_day=minutes_per_day,
        minutes_per_session=minutes_per_session,
    )


def _non_negative(index: int, key: str, value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PolicyError(
            f"policy.toml rule #{index}: {key} must be a non-negative integer, got {value!r}."
        )
    return value
