# Card Integrity & Change Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect when a card's core content changes (trivial vs material vs structural), auto-invalidate reversible derived artefacts (variations, training examples), surface (never auto-apply) FSRS resets, and detect orphaned references and duplicates — all during the existing vault scan.

**Architecture:** Pure, I/O-free decision logic in `core/integrity/` (hashing, classify, orphans, duplicates), called by one stateful orchestrator `services/reconciliation.py` that reads stored hashes, applies verdicts, and returns a `ReconciliationReport`. New nullable columns on three models plus a `core_change_log` audit table, added via one additive Alembic migration.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0 (`Mapped`/`mapped_column`), Alembic, pytest, `uv`. Hashing via `hashlib.sha256`. Spec: `docs/superpowers/specs/2026-06-11-card-integrity-hashing-design.md`.

All commands run from `backend/`. Run tests with `uv run pytest`.

---

## File Structure

**Create (pure logic):**
- `src/mnemonic/core/integrity/__init__.py` — package marker
- `src/mnemonic/core/integrity/hashing.py` — `normalize_core`, `compute_core_hash`, `compute_normalized_hash`, `cloze_signature`
- `src/mnemonic/core/integrity/classify.py` — `StoredHashes`, `CurrentHashes`, `ChangeVerdict`, `classify_change`
- `src/mnemonic/core/integrity/orphans.py` — `DanglingRefs`, `find_dangling_refs`
- `src/mnemonic/core/integrity/duplicates.py` — `DuplicateGroup`, `find_duplicates`

**Create (orchestration + model + migration):**
- `src/mnemonic/services/reconciliation.py` — `ReconciliationService`, `ReconciliationReport`
- `src/mnemonic/db/models/core_change_log.py` — `CoreChangeLog`
- `alembic/versions/card_integrity_0003_core_hashes.py` — migration

**Modify:**
- `src/mnemonic/exceptions.py` — add `IntegrityError`
- `src/mnemonic/db/models/scheduling_state.py` — add 5 columns
- `src/mnemonic/db/models/variation_meta.py` — add `invalidated_at`
- `src/mnemonic/db/models/training_example.py` — add `invalidated_at`
- `src/mnemonic/db/models/__init__.py` — export `CoreChangeLog`
- `src/mnemonic/core/optimization/examples.py` — exclude invalidated training examples

**Create (tests):**
- `tests/unit/core/integrity/__init__.py`
- `tests/unit/core/integrity/test_hashing.py`
- `tests/unit/core/integrity/test_classify.py`
- `tests/unit/core/integrity/test_orphans.py`
- `tests/unit/core/integrity/test_duplicates.py`
- `tests/unit/db/test_core_change_log.py`
- `tests/integration/test_reconciliation.py`

---

## Task 1: `IntegrityError` exception

**Files:**
- Modify: `src/mnemonic/exceptions.py`
- Test: `tests/unit/test_exceptions.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_exceptions.py`:

```python
def test_integrity_error_is_mnemonic_error():
    from mnemonic.exceptions import IntegrityError, MnemonicError

    err = IntegrityError("empty core body")
    assert isinstance(err, MnemonicError)
    assert str(err) == "empty core body"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_exceptions.py::test_integrity_error_is_mnemonic_error -v`
Expected: FAIL with `ImportError: cannot import name 'IntegrityError'`

- [ ] **Step 3: Add the exception**

In `src/mnemonic/exceptions.py`, after the `ValidationError` block (the `InvalidCardSyntaxError` class), insert:

```python
# Integrity errors
class IntegrityError(MnemonicError):
    """Card content integrity check failed (e.g. an un-hashable empty core)."""

    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_exceptions.py::test_integrity_error_is_mnemonic_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/exceptions.py tests/unit/test_exceptions.py
git commit -m "feat(integrity): add IntegrityError exception"
```

---

## Task 2: `hashing.py` — pure hash functions

**Files:**
- Create: `src/mnemonic/core/integrity/__init__.py`
- Create: `src/mnemonic/core/integrity/hashing.py`
- Create: `tests/unit/core/integrity/__init__.py`
- Create: `tests/unit/core/integrity/test_hashing.py`

- [ ] **Step 1: Create package markers**

Create `src/mnemonic/core/integrity/__init__.py` with:

```python
"""Pure, I/O-free card-integrity logic: hashing, change classification, orphans, duplicates."""
```

Create `tests/unit/core/integrity/__init__.py` as an empty file:

```python
```

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/core/integrity/test_hashing.py`:

```python
"""Tests for pure card-core hashing."""

from __future__ import annotations

import pytest

from mnemonic.core.integrity.hashing import (
    cloze_signature,
    compute_core_hash,
    compute_normalized_hash,
    normalize_core,
)
from mnemonic.exceptions import IntegrityError

_BODY = "What is a Nash equilibrium? ^card-aaaabbbb"


def test_block_id_excluded_from_raw_hash():
    with_id = "Define NE. ^card-aaaabbbb"
    without_id = "Define NE."
    assert compute_core_hash(with_id) == compute_core_hash(without_id)


def test_raw_hash_changes_with_content():
    assert compute_core_hash("Define NE.") != compute_core_hash("Define dominance.")


def test_normalize_folds_case_and_whitespace():
    assert normalize_core("Define   NE.") == normalize_core("define ne.")


def test_normalized_hash_ignores_trivial_formatting():
    assert compute_normalized_hash("Define  NE.") == compute_normalized_hash("define ne.")


def test_normalize_is_idempotent():
    once = normalize_core(_BODY)
    assert normalize_core(once) == once


def test_normalize_reduces_cloze_markers_to_inner_text():
    assert normalize_core("the {{c1::mitochondria}} is the powerhouse") == normalize_core(
        "the mitochondria is the powerhouse"
    )


def test_normalize_nfc_equivalence():
    composed = "café"        # é as one code point
    decomposed = "café"     # e + combining acute
    assert normalize_core(composed) == normalize_core(decomposed)


def test_empty_core_raises_on_raw_hash():
    with pytest.raises(IntegrityError):
        compute_core_hash("   ^card-aaaabbbb  ")


def test_empty_core_raises_on_normalized_hash():
    with pytest.raises(IntegrityError):
        compute_normalized_hash("  ")


def test_cloze_signature_none_when_no_cloze():
    assert cloze_signature("plain ==highlight== card") is None


def test_cloze_signature_stable_under_reordering_in_text():
    a = "{{c1::alpha}} then {{c2::beta}}"
    b = "{{c2::beta}} first {{c1::alpha}}"
    assert cloze_signature(a) == cloze_signature(b)


def test_cloze_signature_changes_when_number_changes():
    assert cloze_signature("{{c1::alpha}}") != cloze_signature("{{c2::alpha}}")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/integrity/test_hashing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.integrity.hashing'`

- [ ] **Step 4: Implement `hashing.py`**

Create `src/mnemonic/core/integrity/hashing.py`:

```python
"""Pure hashing of a card's core (`## Card`) body.

Three signals are derived from one body string:
- raw hash: SHA-256 of the verbatim body (block-ID token excluded) — any change at all.
- normalized hash: SHA-256 of a case/whitespace-folded, de-clozed body — material change.
- cloze signature: hash of the set of (number, answer) cloze pairs — structural change.

Normalization is deliberately conservative (case + whitespace only, no punctuation
stripping) because punctuation is meaningful in math/code cards.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from mnemonic.exceptions import IntegrityError

_BLOCK_ID_RE = re.compile(r"\^card-[0-9a-z]+")
_CLOZE_RE = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_block_id(card_body: str) -> str:
    """Remove the ``^card-xxxx`` block-ID token so identity does not affect content hashes."""
    return _BLOCK_ID_RE.sub("", card_body)


def _require_core(card_body: str) -> str:
    """Return the block-ID-stripped, trimmed body, or raise if it is empty."""
    stripped = _strip_block_id(card_body).strip()
    if not stripped:
        raise IntegrityError("Card core body is empty — cannot hash. The note may be malformed.")
    return stripped


def normalize_core(card_body: str) -> str:
    """Case/whitespace-fold a card body and reduce cloze markers to their answer text."""
    nfc = unicodedata.normalize("NFC", _strip_block_id(card_body))
    declozed = _CLOZE_RE.sub(lambda m: m.group(2), nfc)
    folded = declozed.casefold()
    return _WHITESPACE_RE.sub(" ", folded).strip()


def compute_core_hash(card_body: str) -> str:
    """SHA-256 of the verbatim body (block-ID excluded). Raises IntegrityError if empty."""
    return hashlib.sha256(_require_core(card_body).encode("utf-8")).hexdigest()


def compute_normalized_hash(card_body: str) -> str:
    """SHA-256 of the normalized body. Raises IntegrityError if the core is empty."""
    _require_core(card_body)
    return hashlib.sha256(normalize_core(card_body).encode("utf-8")).hexdigest()


def cloze_signature(card_body: str) -> str | None:
    """Hash of the canonical, sorted set of ``(number, answer)`` cloze pairs.

    Returns None when the body contains no cloze markers.
    """
    pairs = _CLOZE_RE.findall(_strip_block_id(card_body))
    if not pairs:
        return None
    canon = "\n".join(f"{num}::{text.strip()}" for num, text in sorted(pairs))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/integrity/test_hashing.py -v`
Expected: PASS (12 passed)

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/core/integrity/__init__.py src/mnemonic/core/integrity/hashing.py tests/unit/core/integrity/__init__.py tests/unit/core/integrity/test_hashing.py
git commit -m "feat(integrity): pure core hashing (raw, normalized, cloze signature)"
```

---

## Task 3: `classify.py` — change classification

**Files:**
- Create: `src/mnemonic/core/integrity/classify.py`
- Create: `tests/unit/core/integrity/test_classify.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/core/integrity/test_classify.py`:

```python
"""Tests for the change-classification decision table."""

from __future__ import annotations

from mnemonic.core.integrity.classify import (
    CurrentHashes,
    StoredHashes,
    classify_change,
)


def _stored(h="h1", n="n1", c="c1"):
    return StoredHashes(core_hash=h, core_hash_normalized=n, cloze_signature=c)


def _current(h="h1", n="n1", c="c1"):
    return CurrentHashes(core_hash=h, core_hash_normalized=n, cloze_signature=c)


def test_new_when_stored_is_none():
    assert classify_change(None, _current()).kind == "new"


def test_new_when_stored_core_hash_is_none():
    assert classify_change(_stored(h=None), _current()).kind == "new"


def test_unchanged_when_all_equal():
    assert classify_change(_stored(), _current()).kind == "unchanged"


def test_trivial_when_only_raw_differs():
    stored = _stored(h="old")
    current = _current(h="new")  # normalized + cloze unchanged
    assert classify_change(stored, current).kind == "trivial"


def test_material_when_normalized_differs():
    stored = _stored(h="old", n="oldnorm")
    current = _current(h="new", n="newnorm")  # cloze unchanged
    assert classify_change(stored, current).kind == "material"


def test_cloze_structure_when_cloze_signature_differs():
    stored = _stored(h="old", c="oldcloze")
    current = _current(h="new", c="newcloze")
    assert classify_change(stored, current).kind == "cloze_structure"


def test_cloze_structure_takes_precedence_over_material():
    # both normalized and cloze changed -> structural wins
    stored = _stored(h="old", n="oldnorm", c="oldcloze")
    current = _current(h="new", n="newnorm", c="newcloze")
    assert classify_change(stored, current).kind == "cloze_structure"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/integrity/test_classify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.integrity.classify'`

- [ ] **Step 3: Implement `classify.py`**

Create `src/mnemonic/core/integrity/classify.py`:

```python
"""Classify a core edit as new / unchanged / trivial / material / cloze_structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChangeKind = Literal["new", "unchanged", "trivial", "material", "cloze_structure"]


@dataclass(frozen=True)
class StoredHashes:
    """Hashes previously persisted on a card's SchedulingState row (may be None)."""

    core_hash: str | None
    core_hash_normalized: str | None
    cloze_signature: str | None


@dataclass(frozen=True)
class CurrentHashes:
    """Hashes freshly computed from the scanned card body."""

    core_hash: str
    core_hash_normalized: str
    cloze_signature: str | None


@dataclass(frozen=True)
class ChangeVerdict:
    """The classified outcome of comparing stored vs current hashes."""

    kind: ChangeKind


def classify_change(stored: StoredHashes | None, current: CurrentHashes) -> ChangeVerdict:
    """Apply the first-match-wins decision table from the design spec.

    Args:
        stored: Previously persisted hashes, or None for a first-seen card.
        current: Freshly computed hashes for the scanned body.

    Returns:
        A ChangeVerdict whose ``kind`` drives the reconciliation action matrix.
    """
    if stored is None or stored.core_hash is None:
        return ChangeVerdict("new")

    raw_same = stored.core_hash == current.core_hash
    norm_same = stored.core_hash_normalized == current.core_hash_normalized
    cloze_same = stored.cloze_signature == current.cloze_signature

    if raw_same and norm_same and cloze_same:
        return ChangeVerdict("unchanged")
    if norm_same and cloze_same:
        return ChangeVerdict("trivial")
    if not cloze_same:
        return ChangeVerdict("cloze_structure")
    return ChangeVerdict("material")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/integrity/test_classify.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/integrity/classify.py tests/unit/core/integrity/test_classify.py
git commit -m "feat(integrity): classify core edits (trivial/material/cloze_structure)"
```

---

## Task 4: `orphans.py` — dangling-reference detection

**Files:**
- Create: `src/mnemonic/core/integrity/orphans.py`
- Create: `tests/unit/core/integrity/test_orphans.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/core/integrity/test_orphans.py`:

```python
"""Tests for dangling-reference detection."""

from __future__ import annotations

from mnemonic.core.integrity.orphans import find_dangling_refs


def test_no_dangling_when_all_refs_live():
    live = {"a", "b"}
    refs = find_dangling_refs(
        live_card_ids=live,
        review_card_ids={"a", "b"},
        variation_card_ids={"a"},
        parent_links={"b": "a"},
    )
    assert refs.review_logs == []
    assert refs.variations == []
    assert refs.parents == []


def test_dangling_review_log():
    refs = find_dangling_refs(
        live_card_ids={"a"},
        review_card_ids={"a", "gone"},
        variation_card_ids=set(),
        parent_links={},
    )
    assert refs.review_logs == ["gone"]


def test_dangling_variation():
    refs = find_dangling_refs(
        live_card_ids={"a"},
        review_card_ids=set(),
        variation_card_ids={"gone"},
        parent_links={},
    )
    assert refs.variations == ["gone"]


def test_dangling_parent_link_reports_child():
    # child "c" points at a parent that no longer exists
    refs = find_dangling_refs(
        live_card_ids={"c"},
        review_card_ids=set(),
        variation_card_ids=set(),
        parent_links={"c": "deadparent"},
    )
    assert refs.parents == ["c"]


def test_results_are_sorted_and_deduped():
    refs = find_dangling_refs(
        live_card_ids=set(),
        review_card_ids={"z", "a", "a"},
        variation_card_ids=set(),
        parent_links={},
    )
    assert refs.review_logs == ["a", "z"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/integrity/test_orphans.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.integrity.orphans'`

- [ ] **Step 3: Implement `orphans.py`**

Create `src/mnemonic/core/integrity/orphans.py`:

```python
"""Detect references that point at cards no longer present in the vault."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DanglingRefs:
    """Buckets of references whose target card is no longer live.

    Attributes:
        review_logs: card_ids referenced by review logs but absent from the vault.
        variations: card_ids with variation metadata but absent from the vault.
        parents: child card_ids whose ``parent_card_id`` is absent from the vault.
    """

    review_logs: list[str]
    variations: list[str]
    parents: list[str]


def find_dangling_refs(
    live_card_ids: set[str],
    review_card_ids: Iterable[str],
    variation_card_ids: Iterable[str],
    parent_links: Mapping[str, str | None],
) -> DanglingRefs:
    """Compute the three dangling-reference buckets.

    Args:
        live_card_ids: card_ids present in the current vault scan.
        review_card_ids: card_ids referenced by ReviewLog rows.
        variation_card_ids: card_ids referenced by VariationMeta rows.
        parent_links: mapping of child card_id -> its parent_card_id.

    Returns:
        A DanglingRefs with each bucket sorted and de-duplicated.
    """
    review = sorted({cid for cid in review_card_ids if cid not in live_card_ids})
    variations = sorted({cid for cid in variation_card_ids if cid not in live_card_ids})
    parents = sorted(
        {child for child, parent in parent_links.items() if parent and parent not in live_card_ids}
    )
    return DanglingRefs(review_logs=review, variations=variations, parents=parents)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/integrity/test_orphans.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/integrity/orphans.py tests/unit/core/integrity/test_orphans.py
git commit -m "feat(integrity): detect dangling review/variation/parent references"
```

---

## Task 5: `duplicates.py` — duplicate detection

**Files:**
- Create: `src/mnemonic/core/integrity/duplicates.py`
- Create: `tests/unit/core/integrity/test_duplicates.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/core/integrity/test_duplicates.py`:

```python
"""Tests for normalized-hash duplicate detection."""

from __future__ import annotations

from mnemonic.core.integrity.duplicates import find_duplicates


def test_no_duplicates_when_all_unique():
    assert find_duplicates({"a": "h1", "b": "h2"}) == []


def test_pair_duplicate_grouped():
    groups = find_duplicates({"a": "h1", "b": "h1", "c": "h2"})
    assert len(groups) == 1
    assert groups[0].normalized_hash == "h1"
    assert groups[0].card_ids == ["a", "b"]


def test_triple_duplicate_grouped():
    groups = find_duplicates({"x": "h", "y": "h", "z": "h"})
    assert len(groups) == 1
    assert groups[0].card_ids == ["x", "y", "z"]


def test_card_ids_sorted_within_group():
    groups = find_duplicates({"b": "h", "a": "h"})
    assert groups[0].card_ids == ["a", "b"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/core/integrity/test_duplicates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.core.integrity.duplicates'`

- [ ] **Step 3: Implement `duplicates.py`**

Create `src/mnemonic/core/integrity/duplicates.py`:

```python
"""Detect cards that share an identical normalized core (duplicate candidates)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DuplicateGroup:
    """A set of cards sharing one normalized core hash.

    Attributes:
        normalized_hash: The shared normalized hash.
        card_ids: The card_ids in the group, sorted.
    """

    normalized_hash: str
    card_ids: list[str]


def find_duplicates(normalized_by_card: Mapping[str, str]) -> list[DuplicateGroup]:
    """Group card_ids by normalized hash, returning only groups with 2+ members.

    Args:
        normalized_by_card: mapping of card_id -> normalized core hash.

    Returns:
        Duplicate groups, ordered by normalized hash, each with sorted card_ids.
        Surfaced as candidates for the user to judge — never auto-merged.
    """
    by_hash: dict[str, list[str]] = {}
    for card_id, normalized in normalized_by_card.items():
        by_hash.setdefault(normalized, []).append(card_id)
    return [
        DuplicateGroup(normalized_hash=h, card_ids=sorted(ids))
        for h, ids in sorted(by_hash.items())
        if len(ids) > 1
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/core/integrity/test_duplicates.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/integrity/duplicates.py tests/unit/core/integrity/test_duplicates.py
git commit -m "feat(integrity): detect duplicate cards by normalized core hash"
```

---

## Task 6: Model changes + `CoreChangeLog` table

**Files:**
- Modify: `src/mnemonic/db/models/scheduling_state.py`
- Modify: `src/mnemonic/db/models/variation_meta.py`
- Modify: `src/mnemonic/db/models/training_example.py`
- Create: `src/mnemonic/db/models/core_change_log.py`
- Modify: `src/mnemonic/db/models/__init__.py`
- Create: `tests/unit/db/test_core_change_log.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/db/test_core_change_log.py`:

```python
"""Round-trip tests for integrity columns and the CoreChangeLog table."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import (
    Base,
    CoreChangeLog,
    SchedulingState,
    TrainingExample,
    VariationMeta,
)
from mnemonic.db.sqlite import create_engine, session_scope


def test_scheduling_state_integrity_columns(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            SchedulingState(
                card_id="card-aaaabbbb",
                core_hash="raw",
                core_hash_normalized="norm",
                cloze_signature="cl",
                core_changed=True,
                core_changed_at=datetime(2026, 6, 11, 9, 0, 0),
            )
        )
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.core_hash == "raw"
        assert row.core_hash_normalized == "norm"
        assert row.cloze_signature == "cl"
        assert bool(row.core_changed) is True


def test_scheduling_state_integrity_columns_default_none(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(SchedulingState(card_id="card-ccccdddd"))
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-ccccdddd")
        assert row.core_hash is None
        assert bool(row.core_changed) is False


def test_variation_and_training_invalidated_at(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    when = datetime(2026, 6, 11, 9, 0, 0)
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id="v1",
                card_id="card-aaaabbbb",
                strategy="rephrase",
                model="m",
                generated_at=when,
                content_hash="ch",
                note_path="p.qmd",
                invalidated_at=when,
            )
        )
        s.add(
            TrainingExample(
                id="te1",
                card_id="card-aaaabbbb",
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=1,
                created_at=when,
                invalidated_at=when,
            )
        )
    with session_scope(engine) as s:
        assert s.get(VariationMeta, "v1").invalidated_at == when
        assert s.get(TrainingExample, "te1").invalidated_at == when


def test_core_change_log_round_trip(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    when = datetime(2026, 6, 11, 9, 0, 0)
    with session_scope(engine) as s:
        s.add(
            CoreChangeLog(
                id="log1",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="old",
                new_hash="new",
                old_normalized="oldn",
                new_normalized="newn",
                detected_at=when,
            )
        )
    with session_scope(engine) as s:
        row = s.get(CoreChangeLog, "log1")
        assert row.change_kind == "material"
        assert row.old_hash == "old"
        assert row.new_hash == "new"
        assert row.detected_at == when
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_core_change_log.py -v`
Expected: FAIL with `ImportError: cannot import name 'CoreChangeLog'`

- [ ] **Step 3: Add columns to `SchedulingState`**

In `src/mnemonic/db/models/scheduling_state.py`, add `Boolean` to the sqlalchemy import line and add the new columns after the `orphan` column:

Change the import line:

```python
from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
```

After the `orphan: Mapped[bool] = ...` line, insert:

```python
    core_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    core_hash_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    cloze_signature: Mapped[str | None] = mapped_column(String, nullable=True)
    core_changed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    core_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4: Add `invalidated_at` to `VariationMeta`**

In `src/mnemonic/db/models/variation_meta.py`, after the `arm: Mapped[str] = ...` line, insert:

```python
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 5: Add `invalidated_at` to `TrainingExample`**

In `src/mnemonic/db/models/training_example.py`, after the `created_at: Mapped[datetime] = ...` line, insert:

```python
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 6: Create the `CoreChangeLog` model**

Create `src/mnemonic/db/models/core_change_log.py`:

```python
"""CoreChangeLog: append-only audit of core-hash transitions per card."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class CoreChangeLog(Base):
    __tablename__ = "core_change_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_kind: Mapped[str] = mapped_column(String, nullable=False)
    old_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    new_hash: Mapped[str] = mapped_column(String, nullable=False)
    old_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    new_normalized: Mapped[str] = mapped_column(String, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

- [ ] **Step 7: Export `CoreChangeLog`**

Replace the body of `src/mnemonic/db/models/__init__.py` with:

```python
"""SQLite ORM models for Mnemonic application state."""

from mnemonic.db.models.base import Base
from mnemonic.db.models.core_change_log import CoreChangeLog
from mnemonic.db.models.llm_usage import LLMUsage
from mnemonic.db.models.prompt_version import PromptVersion
from mnemonic.db.models.review_log import ReviewLog
from mnemonic.db.models.scheduling_state import SchedulingState
from mnemonic.db.models.training_example import TrainingExample
from mnemonic.db.models.variation_meta import VariationMeta

__all__ = [
    "Base",
    "CoreChangeLog",
    "LLMUsage",
    "PromptVersion",
    "ReviewLog",
    "SchedulingState",
    "TrainingExample",
    "VariationMeta",
]
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_core_change_log.py -v`
Expected: PASS (4 passed)

- [ ] **Step 9: Run the existing model tests to confirm no regressions**

Run: `uv run pytest tests/unit/db/ -v`
Expected: PASS (all existing db tests still pass)

- [ ] **Step 10: Commit**

```bash
git add src/mnemonic/db/models/ tests/unit/db/test_core_change_log.py
git commit -m "feat(integrity): add integrity columns and core_change_log model"
```

---

## Task 7: Alembic migration

**Files:**
- Create: `alembic/versions/card_integrity_0003_core_hashes.py`

- [ ] **Step 1: Write the migration**

Create `alembic/versions/card_integrity_0003_core_hashes.py`:

```python
"""Card integrity: core-hash columns, invalidated_at columns, core_change_log table.

Revision ID: card_integrity_0003
Revises: prompt_opt_0002
Create Date: 2026-06-11
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "card_integrity_0003"
down_revision = "prompt_opt_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduling_state", sa.Column("core_hash", sa.String, nullable=True))
    op.add_column("scheduling_state", sa.Column("core_hash_normalized", sa.String, nullable=True))
    op.add_column("scheduling_state", sa.Column("cloze_signature", sa.String, nullable=True))
    op.add_column(
        "scheduling_state",
        sa.Column("core_changed", sa.Boolean, nullable=False, server_default="0"),
    )
    op.add_column("scheduling_state", sa.Column("core_changed_at", sa.DateTime, nullable=True))

    op.add_column("variation_meta", sa.Column("invalidated_at", sa.DateTime, nullable=True))
    op.add_column("training_example", sa.Column("invalidated_at", sa.DateTime, nullable=True))

    op.create_table(
        "core_change_log",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("card_id", sa.String, nullable=False),
        sa.Column("change_kind", sa.String, nullable=False),
        sa.Column("old_hash", sa.String, nullable=True),
        sa.Column("new_hash", sa.String, nullable=False),
        sa.Column("old_normalized", sa.String, nullable=True),
        sa.Column("new_normalized", sa.String, nullable=False),
        sa.Column("detected_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_core_change_log_card", "core_change_log", ["card_id"])


def downgrade() -> None:
    op.drop_index("idx_core_change_log_card", table_name="core_change_log")
    op.drop_table("core_change_log")
    with op.batch_alter_table("training_example") as batch:
        batch.drop_column("invalidated_at")
    with op.batch_alter_table("variation_meta") as batch:
        batch.drop_column("invalidated_at")
    with op.batch_alter_table("scheduling_state") as batch:
        batch.drop_column("core_changed_at")
        batch.drop_column("core_changed")
        batch.drop_column("cloze_signature")
        batch.drop_column("core_hash_normalized")
        batch.drop_column("core_hash")
```

- [ ] **Step 2: Verify the migration applies cleanly**

Run:

```bash
uv run alembic upgrade head
```

Expected: output ends with `Running upgrade prompt_opt_0002 -> card_integrity_0003`, no errors.

- [ ] **Step 3: Verify the downgrade is reversible**

Run:

```bash
uv run alembic downgrade -1 && uv run alembic upgrade head
```

Expected: downgrade removes the revision, upgrade re-applies it, no errors.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/card_integrity_0003_core_hashes.py
git commit -m "feat(integrity): alembic migration for core-hash and invalidation columns"
```

---

## Task 8: `ReconciliationService` orchestrator

**Files:**
- Create: `src/mnemonic/services/reconciliation.py`
- Create: `tests/integration/test_reconciliation.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_reconciliation.py`:

```python
"""Integration tests for the reconciliation pass over a real vault + SQLite."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import (
    Base,
    CoreChangeLog,
    ReviewLog,
    SchedulingState,
    TrainingExample,
    VariationMeta,
)
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.reconciliation import ReconciliationService


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    return vault


def _write_card(vault: Path, name: str, body: str) -> Path:
    path = vault / "01_Projects" / "gt" / f"{name}.qmd"
    path.write_text(f"---\ntitle: {name}\n---\n## Card\n\n{body}\n")
    return path


def _engine(vault: Path):
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return engine


def test_first_scan_classifies_new_and_stores_hashes(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "nash", "What is a {{c1::Nash equilibrium}}?")
    engine = _engine(vault)

    report = ReconciliationService(vault, engine).run()

    assert report.counts["new"] == 1
    with session_scope(engine) as s:
        rows = s.query(SchedulingState).all()
        assert len(rows) == 1
        assert rows[0].core_hash is not None
        assert rows[0].cloze_signature is not None
        assert bool(rows[0].core_changed) is False
        logs = s.query(CoreChangeLog).all()
        assert len(logs) == 1 and logs[0].change_kind == "new"


def test_rescan_with_no_edit_is_unchanged(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "nash", "What is a Nash equilibrium?")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()

    report = ReconciliationService(vault, engine).run()

    assert report.counts["unchanged"] == 1
    with session_scope(engine) as s:
        assert s.query(CoreChangeLog).count() == 1  # no new audit row on rescan


def test_trivial_edit_does_not_flag_or_invalidate(tmp_path: Path):
    vault = _vault(tmp_path)
    path = _write_card(vault, "nash", "What is a Nash equilibrium?")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()
    card_id = _only_card_id(engine)
    _seed_variation(engine, card_id)

    # whitespace-only edit (block ID is preserved by the scanner)
    path.write_text(path.read_text().replace("What is a", "What  is   a"))
    report = ReconciliationService(vault, engine).run()

    assert report.counts["trivial"] == 1
    with session_scope(engine) as s:
        assert bool(s.get(SchedulingState, card_id).core_changed) is False
        assert s.query(VariationMeta).one().invalidated_at is None


def test_material_edit_flags_and_invalidates(tmp_path: Path):
    vault = _vault(tmp_path)
    path = _write_card(vault, "nash", "What is a Nash equilibrium?")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()
    card_id = _only_card_id(engine)
    _seed_variation(engine, card_id)
    _seed_training(engine, card_id)
    _set_fsrs(engine, card_id, stability=42.0, reps=9)

    path.write_text(path.read_text().replace("Nash equilibrium", "dominant strategy"))
    report = ReconciliationService(vault, engine).run()

    assert report.counts["material"] == 1
    with session_scope(engine) as s:
        row = s.get(SchedulingState, card_id)
        assert bool(row.core_changed) is True
        assert row.core_changed_at is not None
        assert row.stability == 42.0 and row.reps == 9  # FSRS untouched
        assert s.query(VariationMeta).one().invalidated_at is not None
        assert s.query(TrainingExample).one().invalidated_at is not None
        kinds = {log.change_kind for log in s.query(CoreChangeLog).all()}
        assert "material" in kinds


def test_dangling_parent_marks_child_orphan(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "child", "A child card.")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()
    card_id = _only_card_id(engine)
    with session_scope(engine) as s:
        s.get(SchedulingState, card_id).parent_card_id = "card-deadparent"

    report = ReconciliationService(vault, engine).run()

    assert report.dangling.parents == [card_id]
    with session_scope(engine) as s:
        assert bool(s.get(SchedulingState, card_id).orphan) is True


def test_duplicate_cards_detected(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "a", "The capital of France is Paris.")
    _write_card(vault, "b", "the capital of france is paris.")
    engine = _engine(vault)

    report = ReconciliationService(vault, engine).run()

    assert len(report.duplicates) == 1
    assert len(report.duplicates[0].card_ids) == 2


# --- helpers ---


def _only_card_id(engine) -> str:
    with session_scope(engine) as s:
        return s.query(SchedulingState).one().card_id


def _set_fsrs(engine, card_id: str, *, stability: float, reps: int) -> None:
    with session_scope(engine) as s:
        row = s.get(SchedulingState, card_id)
        row.stability = stability
        row.reps = reps


def _seed_variation(engine, card_id: str) -> None:
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id=f"var-{card_id}",
                card_id=card_id,
                strategy="rephrase",
                model="m",
                generated_at=datetime(2026, 6, 1),
                content_hash="ch",
                note_path="p.qmd",
            )
        )


def _seed_training(engine, card_id: str) -> None:
    with session_scope(engine) as s:
        s.add(
            TrainingExample(
                id=f"te-{card_id}",
                card_id=card_id,
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=1,
                created_at=datetime(2026, 6, 1),
            )
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_reconciliation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.services.reconciliation'`

- [ ] **Step 3: Implement `reconciliation.py`**

Create `src/mnemonic/services/reconciliation.py`:

```python
"""Reconciliation pass: detect core changes, orphans, and duplicates during a scan.

This is the single stateful caller of the pure ``core/integrity`` functions. It reads
stored hashes, classifies each card's change, applies the action matrix from the design
spec (auto-invalidate reversible artefacts; flag — never reset — FSRS), and returns a
structured report. Runs inside one transaction: any per-card IntegrityError aborts the
whole pass loudly with no partial commit.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mnemonic.core.integrity.classify import (
    ChangeVerdict,
    CurrentHashes,
    StoredHashes,
    classify_change,
)
from mnemonic.core.integrity.duplicates import DuplicateGroup, find_duplicates
from mnemonic.core.integrity.hashing import (
    cloze_signature,
    compute_core_hash,
    compute_normalized_hash,
)
from mnemonic.core.integrity.orphans import DanglingRefs, find_dangling_refs
from mnemonic.db.models import (
    CoreChangeLog,
    ReviewLog,
    SchedulingState,
    TrainingExample,
    VariationMeta,
)
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import IntegrityError
from mnemonic.vault.scanner import ScannedCard, scan_vault

_KINDS = ("new", "unchanged", "trivial", "material", "cloze_structure")
_FLAGGED = ("material", "cloze_structure")


@dataclass
class ReconciliationReport:
    """Outcome of one reconciliation pass.

    Attributes:
        counts: number of cards per change kind.
        dangling: dangling review/variation/parent references.
        duplicates: groups of cards sharing a normalized core hash.
    """

    counts: dict[str, int]
    dangling: DanglingRefs
    duplicates: list[DuplicateGroup]


class ReconciliationService:
    """Run the change/orphan/duplicate detection pass over a vault + SQLite engine."""

    def __init__(self, vault_root: Path, engine: Engine) -> None:
        self.vault_root = vault_root
        self.engine = engine

    def run(self) -> ReconciliationReport:
        """Scan the vault, reconcile every card, and detect orphans and duplicates."""
        scanned = list(scan_vault(self.vault_root, inject_missing_ids=True))
        live_ids = {sc.card_id for sc in scanned}
        counts = dict.fromkeys(_KINDS, 0)
        normalized_by_card: dict[str, str] = {}
        now = datetime.now()
        with session_scope(self.engine) as session:
            for sc in scanned:
                current = self._hash_card(sc)
                normalized_by_card[sc.card_id] = current.core_hash_normalized
                verdict = self._reconcile_card(session, sc, current, now)
                counts[verdict.kind] += 1
            dangling = self._check_orphans(session, live_ids, now)
        duplicates = find_duplicates(normalized_by_card)
        return ReconciliationReport(counts=counts, dangling=dangling, duplicates=duplicates)

    def _hash_card(self, sc: ScannedCard) -> CurrentHashes:
        """Compute all three hashes for a scanned card, re-raising empties with context."""
        try:
            return CurrentHashes(
                core_hash=compute_core_hash(sc.back),
                core_hash_normalized=compute_normalized_hash(sc.back),
                cloze_signature=cloze_signature(sc.back),
            )
        except IntegrityError as exc:
            raise IntegrityError(
                f"Card {sc.card_id} in {sc.note_path} has an empty core body — "
                "cannot hash. The note may be malformed."
            ) from exc

    def _reconcile_card(
        self, session: Session, sc: ScannedCard, current: CurrentHashes, now: datetime
    ) -> ChangeVerdict:
        """Classify one card and apply the resulting action matrix."""
        row = session.get(SchedulingState, sc.card_id)
        stored = (
            StoredHashes(row.core_hash, row.core_hash_normalized, row.cloze_signature)
            if row is not None
            else None
        )
        verdict = classify_change(stored, current)
        self._apply_verdict(session, sc, row, current, verdict, now)
        return verdict

    def _apply_verdict(
        self,
        session: Session,
        sc: ScannedCard,
        row: SchedulingState | None,
        current: CurrentHashes,
        verdict: ChangeVerdict,
        now: datetime,
    ) -> None:
        """Write hashes, set flags, invalidate derived artefacts, and log the change."""
        if verdict.kind == "unchanged":
            return
        old_hash = row.core_hash if row is not None else None
        old_norm = row.core_hash_normalized if row is not None else None
        if row is None:
            row = SchedulingState(card_id=sc.card_id)
            session.add(row)
        row.core_hash = current.core_hash
        row.core_hash_normalized = current.core_hash_normalized
        row.cloze_signature = current.cloze_signature
        if verdict.kind in _FLAGGED:
            row.core_changed = True
            row.core_changed_at = now
            self._invalidate_derived(session, sc.card_id, now)
        self._log_change(session, sc.card_id, old_hash, old_norm, current, verdict, now)

    @staticmethod
    def _invalidate_derived(session: Session, card_id: str, now: datetime) -> None:
        """Mark all still-active variations and training examples for this card stale."""
        session.query(VariationMeta).filter(
            VariationMeta.card_id == card_id,
            VariationMeta.invalidated_at.is_(None),
        ).update({VariationMeta.invalidated_at: now})
        session.query(TrainingExample).filter(
            TrainingExample.card_id == card_id,
            TrainingExample.invalidated_at.is_(None),
        ).update({TrainingExample.invalidated_at: now})

    @staticmethod
    def _log_change(
        session: Session,
        card_id: str,
        old_hash: str | None,
        old_norm: str | None,
        current: CurrentHashes,
        verdict: ChangeVerdict,
        now: datetime,
    ) -> None:
        """Append one CoreChangeLog audit row."""
        session.add(
            CoreChangeLog(
                id=uuid.uuid4().hex,
                card_id=card_id,
                change_kind=verdict.kind,
                old_hash=old_hash,
                new_hash=current.core_hash,
                old_normalized=old_norm,
                new_normalized=current.core_hash_normalized,
                detected_at=now,
            )
        )

    def _check_orphans(self, session: Session, live_ids: set[str], now: datetime) -> DanglingRefs:
        """Find and apply dangling-reference consequences."""
        review_ids = {r[0] for r in session.execute(select(ReviewLog.card_id)).all()}
        variation_ids = {r[0] for r in session.execute(select(VariationMeta.card_id)).all()}
        parent_links = {
            r[0]: r[1]
            for r in session.execute(
                select(SchedulingState.card_id, SchedulingState.parent_card_id).where(
                    SchedulingState.parent_card_id.is_not(None)
                )
            ).all()
        }
        dangling = find_dangling_refs(live_ids, review_ids, variation_ids, parent_links)
        self._apply_orphans(session, dangling, now)
        return dangling

    @staticmethod
    def _apply_orphans(session: Session, dangling: DanglingRefs, now: datetime) -> None:
        """Flag orphaned children and invalidate orphaned variations. Review logs untouched."""
        for child_id in dangling.parents:
            row = session.get(SchedulingState, child_id)
            if row is not None:
                row.orphan = True
        for card_id in dangling.variations:
            session.query(VariationMeta).filter(
                VariationMeta.card_id == card_id,
                VariationMeta.invalidated_at.is_(None),
            ).update({VariationMeta.invalidated_at: now})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_reconciliation.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/reconciliation.py tests/integration/test_reconciliation.py
git commit -m "feat(integrity): reconciliation service wiring detection to state"
```

---

## Task 9: Exclude invalidated training examples from the trainset

**Files:**
- Modify: `src/mnemonic/core/optimization/examples.py:43-45`
- Test: `tests/unit/test_examples.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_examples.py` (the `_engine`, `_champion`, `_example` helpers already exist in this file):

```python
def test_build_trainset_excludes_invalidated():
    from datetime import datetime as _dt

    engine = _engine()
    with Session(engine) as s:
        _champion(s, "rephrase", "pv-r")
        _example(s, 0, "pv-r", finalized=True, reward=0.5)
        _example(s, 1, "pv-r", finalized=True, reward=0.5)
        s.commit()
        # invalidate one example
        from mnemonic.db.models import TrainingExample

        s.get(TrainingExample, "te1").invalidated_at = _dt(2026, 6, 11)
        s.commit()
        cfg = OptimizationConfig(min_examples_to_compile=1)
        train = build_trainset(s, strategy="rephrase", config=cfg)
        assert len(train) == 1  # invalidated row excluded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_examples.py::test_build_trainset_excludes_invalidated -v`
Expected: FAIL with `assert 2 == 1` (the invalidated row is still included)

- [ ] **Step 3: Add the exclusion filter**

In `src/mnemonic/core/optimization/examples.py`, in the `build_trainset` query `.where(...)` clause, add a third condition. Change:

```python
            .where(
                PromptVersion.strategy == strategy,
                TrainingExample.finalized.is_(True),
                TrainingExample.reward.is_not(None),
            )
```

to:

```python
            .where(
                PromptVersion.strategy == strategy,
                TrainingExample.finalized.is_(True),
                TrainingExample.reward.is_not(None),
                TrainingExample.invalidated_at.is_(None),
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_examples.py -v`
Expected: PASS (all tests in the file, including the new one)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/core/optimization/examples.py tests/unit/test_examples.py
git commit -m "feat(integrity): exclude invalidated training examples from trainset"
```

---

## Task 10: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole backend test suite**

Run: `uv run pytest`
Expected: PASS, no regressions.

- [ ] **Step 2: Lint and type-check**

Run:

```bash
uv run ruff check src tests
uv run black --check src tests
uv run mypy src
```

Expected: all clean. Fix any issues, then re-run.

- [ ] **Step 3: Confirm coverage on the new core module**

Run: `uv run pytest --cov=mnemonic.core.integrity --cov-report=term-missing tests/unit/core/integrity/`
Expected: `core/integrity` at or above 95%.

- [ ] **Step 4: Final commit (only if lint/type fixes were made)**

```bash
git add -A
git commit -m "chore(integrity): lint and type-check fixes"
```

---

## Notes for the implementer

- **New behaviour:** reconciliation now creates a `SchedulingState` row for every scanned card (to hold its hashes). Previously rows were created lazily. The defaults match what `VaultRepository.list_cards` assumed for missing rows, so this is safe.
- **No-silent-failures:** an empty core body raises `IntegrityError` inside one transaction, aborting the whole pass with the offending `card_id` and note path — no partial commit. Dangling `ReviewLog` rows are reported, never deleted.
- **FSRS is never reset here.** Material/structural changes only set `core_changed` + `core_changed_at`; the keep/soft-reset/full-reset UI panel that consumes that flag is future work, out of scope for this plan.
- **Variation read-path:** invalidated variations have `invalidated_at` set; a future review/display path should filter on `invalidated_at IS NULL`. Only the training-set builder is wired in this plan (Task 9), since it is the one existing consumer.
