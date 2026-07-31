# Variation Generation (B2-Gen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Actually create LLM variations — a `mnemonic-generate` CLI over an orchestrator that targets cards with zero live variations, budget-guarded, skipping and reporting per-card failures.

**Architecture:** A new `services/variation_gen.py` selects targets (non-suspended, `variation_enabled` deck, no non-invalidated `VariationMeta`), assembles per-card inputs (raw card section + context by re-parsing the note, recent ratings, prior variations), and drives `select_strategy` → `pick_model` → `get_champion` → `VariationGenerator.generate` → `persist_variation`. A thin `cli/generate.py` wraps a testable `run_generate` seam.

**Tech Stack:** Python 3.11, SQLAlchemy, Jinja2, pytest, `uv`.

All commands run from `backend/`. Spec: `docs/superpowers/specs/2026-07-16-variation-generation-design.md`.

---

## File Structure

**Create:** `src/mnemonic/services/variation_gen.py` (targets + per-card pipeline + `run_generate`), `src/mnemonic/cli/generate.py` (argparse wrapper).
**Modify:** `src/mnemonic/llm/variation/generator.py` (`instruction_text` override), `src/mnemonic/llm/variation/writer.py` (`shown_count` 1 → 0), `pyproject.toml` (console script).
**Tests:** `tests/unit/llm/test_variation.py` (append), `tests/unit/llm/test_variation_persist.py` (append), `tests/unit/services/test_variation_gen.py` (new), `tests/integration/test_cli_generate.py` (new).

---

## Task 1: Two defect fixes (`shown_count`, `instruction_text`)

**Files:**
- Modify: `src/mnemonic/llm/variation/writer.py`, `src/mnemonic/llm/variation/generator.py`
- Test: `tests/unit/llm/test_variation_persist.py`, `tests/unit/llm/test_variation.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/llm/test_variation_persist.py` (this file already has an `engine` fixture, a `note_path` fixture, and a `_make_variation(**kwargs)` helper — reuse them; match the argument style of the existing `persist_variation` calls in that file):

```python
def test_new_variation_starts_unshown(engine, note_path, tmp_path):
    from mnemonic.db.models import VariationMeta
    from mnemonic.db.sqlite import session_scope
    from mnemonic.llm.variation.writer import persist_variation

    variation_id = persist_variation(
        engine=engine,
        note_path=note_path,
        card_id="card-aabbccdd",
        variation=_make_variation(),
        vault_root=note_path.parent,
        prompt_version_id="pv-1",
        base_q="bq",
        base_a="ba",
    )
    with session_scope(engine) as s:
        assert s.get(VariationMeta, variation_id).shown_count == 0
```

Note: `vault_root=note_path.parent` must make `note_path.relative_to(vault_root)` valid. If the file's existing tests pass a different `vault_root`, copy whatever they use.

Append to `tests/unit/llm/test_variation.py` (it already builds a `MagicMock` client returning a real `Completion`, and points `prompts_dir` at the real shipped prompts — reuse that setup):

```python
def test_instruction_text_overrides_the_on_disk_strategy():
    from unittest.mock import MagicMock
    from pathlib import Path

    from mnemonic.llm.client import Completion, Usage
    from mnemonic.llm.variation.generator import VariationGenerator

    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: When is X?\nA: When Y.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=100, output_tokens=20,
            cache_read_tokens=0, cache_creation_tokens=0, cost_millicents=15,
        ),
    )
    prompts_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    gen = VariationGenerator(client=client, prompts_dir=prompts_dir)

    gen.generate(
        strategy="rephrase",
        base_card_text="A ==term==.",
        note_context="ctx",
        prior_variations=[],
        fsrs={"stability": 1.0, "reps": 1, "lapses": 0, "recent_ratings": [3]},
        model="m",
        instruction_text="SENTINEL-INSTRUCTION-TEXT",
    )

    system_blocks = client.generate.call_args.kwargs["system"]
    joined = "\n".join(b.text for b in system_blocks)
    assert "SENTINEL-INSTRUCTION-TEXT" in joined


def test_without_instruction_text_the_disk_strategy_is_used():
    from unittest.mock import MagicMock
    from pathlib import Path

    from mnemonic.llm.client import Completion, Usage
    from mnemonic.llm.variation.generator import VariationGenerator

    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: When is X?\nA: When Y.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=100, output_tokens=20,
            cache_read_tokens=0, cache_creation_tokens=0, cost_millicents=15,
        ),
    )
    prompts_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    disk_text = (prompts_dir / "strategies" / "rephrase.md").read_text()
    gen = VariationGenerator(client=client, prompts_dir=prompts_dir)

    gen.generate(
        strategy="rephrase",
        base_card_text="A ==term==.",
        note_context="ctx",
        prior_variations=[],
        fsrs={"stability": 1.0, "reps": 1, "lapses": 0, "recent_ratings": [3]},
        model="m",
    )

    system_blocks = client.generate.call_args.kwargs["system"]
    joined = "\n".join(b.text for b in system_blocks)
    assert disk_text.strip()[:60] in joined
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/llm/test_variation_persist.py::test_new_variation_starts_unshown tests/unit/llm/test_variation.py::test_instruction_text_overrides_the_on_disk_strategy -v`
Expected: FAIL — first with `assert 1 == 0`; second with `TypeError: generate() got an unexpected keyword argument 'instruction_text'`.

- [ ] **Step 3: Fix `shown_count`** — In `src/mnemonic/llm/variation/writer.py`, inside the `VariationMeta(...)` construction, change:

```python
                shown_count=1,
```
to:
```python
                shown_count=0,
```

- [ ] **Step 4: Add the `instruction_text` override** — In `src/mnemonic/llm/variation/generator.py`:

Add the parameter to `generate`'s signature, after `model: str,`:
```python
        model: str,
        instruction_text: str | None = None,
```

Add this line to the `generate` docstring's Args section (after the `model:` entry):
```
            instruction_text: Optional strategy prompt text to use instead of reading
                ``strategies/<strategy>.md`` from disk (e.g. a compiled champion).
```

Replace the line that loads the strategy:
```python
        strategy_md = self._load_strategy(strategy)
```
with:
```python
        strategy_md = (
            instruction_text if instruction_text is not None else self._load_strategy(strategy)
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/llm -q`
Expected: PASS (all llm tests, including the 3 new).

- [ ] **Step 6: Commit**

```bash
git add src/mnemonic/llm/variation/writer.py src/mnemonic/llm/variation/generator.py tests/unit/llm/test_variation_persist.py tests/unit/llm/test_variation.py
git commit -m "fix(variation): variations start unshown; generate() accepts instruction_text override"
```

---

## Task 2: Target selection

**Files:**
- Create: `src/mnemonic/services/variation_gen.py`
- Test: `tests/unit/services/test_variation_gen.py`

- [ ] **Step 1: Write the failing tests** — Create `tests/unit/services/test_variation_gen.py`:

```python
"""Tests for variation-generation target selection and the run loop."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import Base, TrainingExample, VariationMeta
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.variation_gen import select_targets
from mnemonic.vault.repository import VaultRepository

WHEN = datetime(2026, 7, 1, 12, 0, 0)


def _deck_md(enabled: bool = True) -> str:
    return (
        f"---\ndeck_name: GT\nvariation_enabled: {str(enabled).lower()}\n"
        "variation_frequency: 1.0\nleech_threshold: 8\n"
        "daily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )


def _card_note(n: int) -> str:
    return f"---\ntitle: n{n}\n---\n## Card\n\nA {{{{c1::term{n}}}}}. ^card-n{n}\n"


def _setup(tmp_path: Path, *, enabled: bool = True, n_cards: int = 3):
    vault = tmp_path / "vault"
    deck = vault / "01_Projects" / "gt"
    deck.mkdir(parents=True)
    (deck / "_deck.md").write_text(_deck_md(enabled))
    for i in range(n_cards):
        (deck / f"n{i}.qmd").write_text(_card_note(i))
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return VaultRepository(vault_root=vault, engine=engine), engine


def _add_variation(engine, card_id: str, vid: str, *, invalidated=None):
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id=vid, card_id=card_id, strategy="rephrase", model="m", generated_at=WHEN,
                shown_count=0, helpful_count=0, content_hash="h", note_path="n.qmd",
                invalidated_at=invalidated,
            )
        )
        s.add(
            TrainingExample(
                id=f"te-{vid}", card_id=card_id, variation_id=vid, base_q="bq", base_a="ba",
                variation_q="vq", variation_a="va", label=0, created_at=WHEN,
            )
        )


def test_targets_are_cards_without_live_variations(tmp_path: Path):
    repo, engine = _setup(tmp_path)
    _add_variation(engine, "card-n0", "v0")          # n0 already covered

    targets = select_targets(repo, engine, deck=None, limit=10)

    assert [t.card.card_id for t in targets] == ["card-n1", "card-n2"]


def test_invalidated_variations_do_not_count_as_coverage(tmp_path: Path):
    repo, engine = _setup(tmp_path, n_cards=1)
    _add_variation(engine, "card-n0", "v0", invalidated=WHEN)

    targets = select_targets(repo, engine, deck=None, limit=10)

    assert [t.card.card_id for t in targets] == ["card-n0"]


def test_disabled_deck_yields_no_targets(tmp_path: Path):
    repo, engine = _setup(tmp_path, enabled=False)
    assert select_targets(repo, engine, deck=None, limit=10) == []


def test_limit_caps_targets(tmp_path: Path):
    repo, engine = _setup(tmp_path, n_cards=5)
    assert len(select_targets(repo, engine, deck=None, limit=2)) == 2


def test_deck_filter(tmp_path: Path):
    repo, engine = _setup(tmp_path)
    assert select_targets(repo, engine, deck="gt", limit=10) != []
    assert select_targets(repo, engine, deck="other", limit=10) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_variation_gen.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.services.variation_gen'`

- [ ] **Step 3: Implement selection** — Create `src/mnemonic/services/variation_gen.py`:

```python
"""Variation generation: pick target cards and drive the generate → persist pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from mnemonic.db.models import VariationMeta
from mnemonic.db.sqlite import session_scope
from mnemonic.vault.repository import Card, VaultRepository


@dataclass(frozen=True)
class GenerationTarget:
    """A card selected for variation generation."""

    card: Card
    deck_folder: str


def _covered_card_ids(engine: Engine, card_ids: list[str]) -> set[str]:
    """card_ids that already have at least one non-invalidated variation."""
    if not card_ids:
        return set()
    with session_scope(engine) as s:
        rows = (
            s.query(VariationMeta.card_id)
            .filter(
                VariationMeta.card_id.in_(card_ids),
                VariationMeta.invalidated_at.is_(None),
            )
            .distinct()
            .all()
        )
    return {row[0] for row in rows}


def select_targets(
    repo: VaultRepository, engine: Engine, *, deck: str | None, limit: int
) -> list[GenerationTarget]:
    """Cards eligible for generation: enabled deck, not suspended, no live variation.

    Args:
        repo: Vault repository (source of truth for which cards exist).
        engine: SQLAlchemy engine for the state DB.
        deck: Optional deck-folder name filter.
        limit: Maximum number of targets to return.

    Returns:
        Up to ``limit`` targets, ordered by card_id for deterministic runs.
    """
    decks = {d.folder.name: d for d in repo.list_decks()}
    eligible: list[Card] = []
    for card in repo.list_cards():
        folder = card.deck_folder.name
        if deck is not None and folder != deck:
            continue
        if card.suspended:
            continue
        cfg = decks[folder].config if folder in decks else None
        if cfg is None or not cfg.variation_enabled:
            continue
        eligible.append(card)

    covered = _covered_card_ids(engine, [c.card_id for c in eligible])
    chosen = sorted(
        (c for c in eligible if c.card_id not in covered), key=lambda c: c.card_id
    )
    return [
        GenerationTarget(card=c, deck_folder=c.deck_folder.name) for c in chosen[:limit]
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_variation_gen.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/variation_gen.py tests/unit/services/test_variation_gen.py
git commit -m "feat(variation-gen): select cards lacking live variations"
```

---

## Task 3: Per-card input accessors

**Files:**
- Modify: `src/mnemonic/services/variation_gen.py`
- Test: `tests/unit/services/test_variation_gen.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/services/test_variation_gen.py`:

```python
def test_note_inputs_returns_raw_card_section_and_context(tmp_path: Path):
    from mnemonic.services.variation_gen import note_inputs

    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n## Card\n\nA {{c1::term}}. ^card-n0\n\n"
        "## Context\n\nSome context here.\n"
    )

    card_section, context = note_inputs(note)

    assert "{{c1::term}}" in card_section   # raw markers, NOT build_faces output
    assert "Some context here." in context


def test_note_inputs_context_is_empty_when_absent(tmp_path: Path):
    from mnemonic.services.variation_gen import note_inputs

    note = tmp_path / "n.qmd"
    note.write_text("---\ntitle: t\n---\n## Card\n\nA {{c1::term}}. ^card-n0\n")

    _, context = note_inputs(note)

    assert context == ""


def test_recent_ratings_newest_first_and_capped(tmp_path: Path):
    from mnemonic.db.models import ReviewLog
    from mnemonic.services.variation_gen import recent_ratings

    _, engine = _setup(tmp_path, n_cards=1)
    with session_scope(engine) as s:
        for i, rating in enumerate([1, 2, 3, 4, 1, 2]):
            s.add(
                ReviewLog(
                    id=f"r{i}", card_id="card-n0", rating=rating, response_time_ms=100,
                    review_time=datetime(2026, 7, 1, 12, i, 0),
                )
            )

    got = recent_ratings(engine, "card-n0", n=3)

    assert got == [2, 1, 4]   # newest first, capped at 3


def test_prior_variations_excludes_invalidated(tmp_path: Path):
    from mnemonic.services.variation_gen import prior_variations

    _, engine = _setup(tmp_path, n_cards=1)
    _add_variation(engine, "card-n0", "v-live")
    _add_variation(engine, "card-n0", "v-dead", invalidated=WHEN)

    got = prior_variations(engine, "card-n0")

    assert len(got) == 1
    assert set(got[0]) == {"q", "a", "rating"}
    assert got[0]["q"] == "vq"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_variation_gen.py::test_note_inputs_returns_raw_card_section_and_context -v`
Expected: FAIL with `ImportError: cannot import name 'note_inputs'`

- [ ] **Step 3: Implement the accessors** — In `src/mnemonic/services/variation_gen.py`:

Extend the imports at the top:
```python
from pathlib import Path
from typing import Any

from mnemonic.db.models import ReviewLog, TrainingExample, VariationMeta
from mnemonic.vault.note import parse_note
```
(Replace the existing `from mnemonic.db.models import VariationMeta` line with the three-model version, and add the `Path`, `Any`, and `parse_note` imports.)

Append these three functions to the module:
```python
def note_inputs(note_path: Path) -> tuple[str, str]:
    """Return (raw ``## Card`` section, ``## Context`` section) for a note.

    The card section keeps its cloze markers — the prompt needs the raw form, not the
    display faces produced by ``build_faces``.
    """
    note = parse_note(note_path.read_text())
    return (note.card_section or ""), (note.context_section or "")


def recent_ratings(engine: Engine, card_id: str, *, n: int = 5) -> list[int]:
    """The card's most recent review ratings, newest first, capped at ``n``."""
    with session_scope(engine) as s:
        rows = (
            s.query(ReviewLog.rating)
            .filter(ReviewLog.card_id == card_id)
            .order_by(ReviewLog.review_time.desc())
            .limit(n)
            .all()
        )
    return [row[0] for row in rows]


def prior_variations(engine: Engine, card_id: str) -> list[dict[str, Any]]:
    """Existing live variations for a card as ``{q, a, rating}`` dicts."""
    with session_scope(engine) as s:
        rows = (
            s.query(
                TrainingExample.variation_q,
                TrainingExample.variation_a,
                TrainingExample.rating,
            )
            .join(VariationMeta, VariationMeta.id == TrainingExample.variation_id)
            .filter(
                VariationMeta.card_id == card_id,
                VariationMeta.invalidated_at.is_(None),
            )
            .all()
        )
    return [{"q": q, "a": a, "rating": rating} for q, a, rating in rows]
```

Note the `recent_ratings` signature uses a keyword-only `n`; the test calls it as `recent_ratings(engine, "card-n0", n=3)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_variation_gen.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/variation_gen.py tests/unit/services/test_variation_gen.py
git commit -m "feat(variation-gen): note/rating/prior-variation input accessors"
```

---

## Task 4: `generate_for_card`

**Files:**
- Modify: `src/mnemonic/services/variation_gen.py`
- Test: `tests/unit/services/test_variation_gen.py`

- [ ] **Step 1: Write the failing test** — Append to `tests/unit/services/test_variation_gen.py`:

```python
def _stub_generator():
    """A VariationGenerator whose client returns a canned Completion."""
    from unittest.mock import MagicMock

    from mnemonic.llm.client import Completion, Usage
    from mnemonic.llm.variation.generator import VariationGenerator

    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: Rephrased?\nA: Yes.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=10, output_tokens=5,
            cache_read_tokens=0, cache_creation_tokens=0, cost_millicents=7,
        ),
    )
    prompts_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    return VariationGenerator(client=client, prompts_dir=prompts_dir), client


def test_generate_for_card_persists_everything(tmp_path: Path):
    from mnemonic.core.optimization.registry import ensure_champion_versions
    from mnemonic.db.models import LLMUsage, TrainingExample, VariationMeta
    from mnemonic.services.variation_gen import generate_for_card, select_targets

    repo, engine = _setup(tmp_path, n_cards=1)
    prompts_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    with session_scope(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=WHEN)
    generator, client = _stub_generator()
    target = select_targets(repo, engine, deck=None, limit=1)[0]

    variation_id = generate_for_card(
        target,
        engine=engine,
        generator=generator,
        vault_root=repo.vault_root,
        model_default="m-default",
        model_rephrase="m-rephrase",
    )

    assert client.generate.called
    with session_scope(engine) as s:
        meta = s.get(VariationMeta, variation_id)
        assert meta is not None
        assert meta.card_id == "card-n0"
        assert meta.arm == "champion"
        assert meta.prompt_version_id is not None
        assert meta.shown_count == 0
        assert s.query(TrainingExample).filter(
            TrainingExample.variation_id == variation_id
        ).count() == 1
        assert s.query(LLMUsage).count() == 1
    assert "### " in target.card.note_path.read_text()   # note entry appended
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/services/test_variation_gen.py::test_generate_for_card_persists_everything -v`
Expected: FAIL with `ImportError: cannot import name 'generate_for_card'`

- [ ] **Step 3: Implement `generate_for_card`** — In `src/mnemonic/services/variation_gen.py`:

Extend the imports:
```python
from mnemonic.core.optimization.registry import get_champion
from mnemonic.core.review.faces import build_faces
from mnemonic.llm.router import pick_model
from mnemonic.llm.variation.generator import VariationGenerator
from mnemonic.llm.variation.strategy import select_strategy
from mnemonic.llm.variation.writer import persist_variation
```

Append this function:
```python
def generate_for_card(
    target: GenerationTarget,
    *,
    engine: Engine,
    generator: VariationGenerator,
    vault_root: Path,
    model_default: str,
    model_rephrase: str,
) -> str:
    """Generate and persist one variation for a card. Returns the new variation_id.

    Raises:
        LLMError: If generation fails or the response cannot be parsed.
        OptimizationError: If the strategy has no champion PromptVersion.
        MalformedNoteError: If the note cannot be parsed.
    """
    card = target.card
    card_section, context = note_inputs(card.note_path)
    ratings = recent_ratings(engine, card.card_id)
    strategy = select_strategy(reps=card.reps, lapses=card.lapses, recent_ratings=ratings)
    model = pick_model(
        strategy=strategy,
        recent_failures=sum(1 for r in ratings if r == 1),
        model_default=model_default,
        model_rephrase=model_rephrase,
    )
    with session_scope(engine) as s:
        champion = get_champion(s, strategy)
        prompt_version_id = champion.id
        instruction_text = champion.instruction_text
    variation = generator.generate(
        strategy=strategy,
        base_card_text=card_section,
        note_context=context,
        prior_variations=prior_variations(engine, card.card_id),
        fsrs={
            "stability": card.stability,
            "reps": card.reps,
            "lapses": card.lapses,
            "recent_ratings": ratings,
        },
        model=model,
        instruction_text=instruction_text,
    )
    faces = build_faces(syntax=card.syntax, front=card.front, back=card.back)
    return persist_variation(
        engine=engine,
        note_path=card.note_path,
        card_id=card.card_id,
        variation=variation,
        vault_root=vault_root,
        prompt_version_id=prompt_version_id,
        arm="champion",
        base_q=faces.front,
        base_a=faces.answer,
        note_context=context or None,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_variation_gen.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/variation_gen.py tests/unit/services/test_variation_gen.py
git commit -m "feat(variation-gen): generate_for_card assembles strategy, champion prompt, persist"
```

---

## Task 5: `run_generate` loop

**Files:**
- Modify: `src/mnemonic/services/variation_gen.py`
- Test: `tests/unit/services/test_variation_gen.py`

- [ ] **Step 1: Write the failing tests** — Append to `tests/unit/services/test_variation_gen.py`:

```python
def _seed_champions(engine):
    from mnemonic.core.optimization.registry import ensure_champion_versions

    prompts_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    with session_scope(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=WHEN)


def test_run_generate_happy_path(tmp_path: Path):
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, _ = _stub_generator()

    report = run_generate(
        repo=repo, engine=engine, generator=generator, deck=None, limit=10,
        model_default="d", model_rephrase="r", daily_cents=1000, monthly_cents=10000,
    )

    assert len(report.generated) == 2
    assert report.skipped == []
    assert report.budget_stopped is False


def test_run_generate_skips_a_failing_card_and_continues(tmp_path: Path):
    from mnemonic.exceptions import LLMError
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, client = _stub_generator()
    ok = client.generate.return_value
    client.generate.side_effect = [LLMError("bad response"), ok]

    report = run_generate(
        repo=repo, engine=engine, generator=generator, deck=None, limit=10,
        model_default="d", model_rephrase="r", daily_cents=1000, monthly_cents=10000,
    )

    assert len(report.generated) == 1
    assert len(report.skipped) == 1
    assert "bad response" in report.skipped[0][1]
    assert report.budget_stopped is False


def test_run_generate_stops_when_budget_exhausted(tmp_path: Path):
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, client = _stub_generator()

    report = run_generate(
        repo=repo, engine=engine, generator=generator, deck=None, limit=10,
        model_default="d", model_rephrase="r", daily_cents=0, monthly_cents=0,
    )

    assert report.generated == []
    assert report.budget_stopped is True
    assert client.generate.call_count == 0


def test_run_generate_dry_run_makes_no_calls(tmp_path: Path):
    from mnemonic.services.variation_gen import run_generate

    repo, engine = _setup(tmp_path, n_cards=2)
    _seed_champions(engine)
    generator, client = _stub_generator()

    report = run_generate(
        repo=repo, engine=engine, generator=generator, deck=None, limit=10,
        model_default="d", model_rephrase="r", daily_cents=1000, monthly_cents=10000,
        dry_run=True,
    )

    assert client.generate.call_count == 0
    assert report.generated == []
    assert len(report.targets) == 2
```

Note: a `daily_cents=0` budget makes `assert_within_budget()` raise immediately (spent `0 >= cap 0`), which is how the budget-stop path is exercised without spending anything.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_variation_gen.py::test_run_generate_happy_path -v`
Expected: FAIL with `ImportError: cannot import name 'run_generate'`

- [ ] **Step 3: Implement `run_generate`** — In `src/mnemonic/services/variation_gen.py`:

Extend the imports:
```python
from mnemonic.exceptions import (
    LLMBudgetExceededError,
    LLMError,
    MalformedNoteError,
    OptimizationError,
)
from mnemonic.llm.budget import BudgetGuard
```

Append the report dataclass and the loop:
```python
@dataclass(frozen=True)
class GenerationReport:
    """Outcome of one generation run."""

    generated: list[str]
    skipped: list[tuple[str, str]]
    budget_stopped: bool
    targets: list[str]


def run_generate(
    *,
    repo: VaultRepository,
    engine: Engine,
    generator: VariationGenerator,
    deck: str | None,
    limit: int,
    model_default: str,
    model_rephrase: str,
    daily_cents: int,
    monthly_cents: int,
    dry_run: bool = False,
) -> GenerationReport:
    """Generate variations for eligible cards.

    Budget exhaustion stops the run; a per-card failure is recorded and skipped.
    """
    targets = select_targets(repo, engine, deck=deck, limit=limit)
    target_ids = [t.card.card_id for t in targets]
    if dry_run:
        return GenerationReport(
            generated=[], skipped=[], budget_stopped=False, targets=target_ids
        )

    guard = BudgetGuard(
        engine=engine, daily_cents=daily_cents, monthly_cents=monthly_cents
    )
    generated: list[str] = []
    skipped: list[tuple[str, str]] = []
    for target in targets:
        try:
            guard.assert_within_budget()
        except LLMBudgetExceededError:
            return GenerationReport(
                generated=generated,
                skipped=skipped,
                budget_stopped=True,
                targets=target_ids,
            )
        try:
            generated.append(
                generate_for_card(
                    target,
                    engine=engine,
                    generator=generator,
                    vault_root=repo.vault_root,
                    model_default=model_default,
                    model_rephrase=model_rephrase,
                )
            )
        except (LLMError, MalformedNoteError, OptimizationError, ValueError) as exc:
            skipped.append((target.card.card_id, f"{type(exc).__name__}: {exc}"))
    return GenerationReport(
        generated=generated, skipped=skipped, budget_stopped=False, targets=target_ids
    )
```

Note `LLMBudgetExceededError` is a subclass of `LLMError`, so its `except` clause must come first — it does, being a separate `try` around the guard.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_variation_gen.py -v`
Expected: PASS (14 passed)

- [ ] **Step 5: Commit**

```bash
git add src/mnemonic/services/variation_gen.py tests/unit/services/test_variation_gen.py
git commit -m "feat(variation-gen): run loop with per-card budget check and skip-and-report"
```

---

## Task 6: `mnemonic-generate` CLI + verification

**Files:**
- Create: `src/mnemonic/cli/generate.py`
- Modify: `pyproject.toml`
- Test: `tests/integration/test_cli_generate.py`

- [ ] **Step 1: Write the failing test** — Create `tests/integration/test_cli_generate.py`:

```python
"""Integration test for the mnemonic-generate CLI."""

from __future__ import annotations

import types
from pathlib import Path

from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.services.variation_gen import GenerationReport


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    deck = vault / "01_Projects" / "gt"
    deck.mkdir(parents=True)
    (deck / "_deck.md").write_text(
        "---\ndeck_name: GT\nvariation_enabled: true\nvariation_frequency: 1.0\n"
        "leech_threshold: 8\ndaily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )
    (deck / "n0.qmd").write_text(
        "---\ntitle: n0\n---\n## Card\n\nA {{c1::term}}. ^card-n0\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault


def _config(vault: Path):
    return types.SimpleNamespace(
        vault=types.SimpleNamespace(path=vault),
        llm=types.SimpleNamespace(
            api_key_env="OPENROUTER_API_KEY",
            api_base="https://openrouter.ai/api",
            model_default="d",
            model_rephrase="r",
            budget=types.SimpleNamespace(daily_cents=100, monthly_cents=1000),
        ),
    )


def test_main_dry_run_returns_zero(tmp_path, monkeypatch, capsys):
    from mnemonic.cli import generate as gen_cli

    vault = _vault(tmp_path)
    monkeypatch.setattr(gen_cli, "load_config", lambda: _config(vault))

    exit_code = gen_cli.main(["--dry-run"])

    assert exit_code == 0
    assert "card-n0" in capsys.readouterr().out


def test_main_returns_one_when_cards_were_skipped(tmp_path, monkeypatch, capsys):
    from mnemonic.cli import generate as gen_cli

    vault = _vault(tmp_path)
    monkeypatch.setattr(gen_cli, "load_config", lambda: _config(vault))
    monkeypatch.setattr(
        gen_cli,
        "run_generate",
        lambda **kwargs: GenerationReport(
            generated=[], skipped=[("card-n0", "LLMError: boom")],
            budget_stopped=False, targets=["card-n0"],
        ),
    )

    exit_code = gen_cli.main([])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "skipped 1" in out
    assert "card-n0" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_cli_generate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mnemonic.cli.generate'`

- [ ] **Step 3: Allow a `None` generator for dry runs** — In `src/mnemonic/services/variation_gen.py`, change `run_generate`'s parameter annotation:

```python
    generator: VariationGenerator | None,
```

and add this guard immediately AFTER the `if dry_run:` early-return block and BEFORE the `guard = BudgetGuard(...)` line:

```python
    if generator is None:
        raise ValueError("A VariationGenerator is required unless dry_run=True.")
```

This lets the CLI skip constructing a client (and needing an API key) on `--dry-run`, while still failing loudly if a real run somehow gets no generator.

- [ ] **Step 4: Implement the CLI** — Create `src/mnemonic/cli/generate.py`:

```python
"""`mnemonic-generate`: generate LLM variations for cards that have none."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from mnemonic.config import load_config
from mnemonic.core.optimization.registry import ensure_champion_versions
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.llm.backends.openrouter import OpenRouterBackend
from mnemonic.llm.variation.generator import VariationGenerator
from mnemonic.services.variation_gen import GenerationReport, run_generate
from mnemonic.vault.repository import VaultRepository

_DEFAULT_LIMIT = 20


def _default_prompts_dir() -> Path:
    from mnemonic.llm.prompts import variation as variation_pkg

    return Path(variation_pkg.__file__).parent


def _format_summary(report: GenerationReport, *, dry_run: bool) -> str:
    """Render a one-glance summary of a generation run."""
    if dry_run:
        listed = "\n".join(f"  {cid}" for cid in report.targets)
        return f"dry run: {len(report.targets)} target(s)\n{listed}".rstrip()
    lines = [
        f"generated {len(report.generated)}, skipped {len(report.skipped)}, "
        f"budget stopped: {'yes' if report.budget_stopped else 'no'}"
    ]
    if report.skipped:
        lines.append("")
        lines.append("skipped:")
        lines.extend(f"  {cid}  {reason}" for cid, reason in report.skipped)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-generate",
        description="Generate LLM variations for cards that have none.",
    )
    parser.add_argument("--deck", default=None, help="Limit to one deck folder name.")
    parser.add_argument(
        "--limit", type=int, default=_DEFAULT_LIMIT, help="Maximum cards to generate for."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List targets without calling the LLM."
    )
    args = parser.parse_args(argv)

    config = load_config()
    engine = create_engine(config.vault.path / ".mnemonic" / "state.sqlite")
    prompts_dir = _default_prompts_dir()
    with session_scope(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=datetime.now())

    generator = (
        None
        if args.dry_run
        else VariationGenerator(
            client=OpenRouterBackend(
                api_key_env=config.llm.api_key_env, base_url=config.llm.api_base
            ),
            prompts_dir=prompts_dir,
        )
    )
    report = run_generate(
        repo=VaultRepository(vault_root=config.vault.path, engine=engine),
        engine=engine,
        generator=generator,
        deck=args.deck,
        limit=args.limit,
        model_default=config.llm.model_default,
        model_rephrase=config.llm.model_rephrase,
        daily_cents=config.llm.budget.daily_cents,
        monthly_cents=config.llm.budget.monthly_cents,
        dry_run=args.dry_run,
    )
    print(_format_summary(report, dry_run=args.dry_run))
    return 1 if (report.skipped or report.budget_stopped) else 0
```

Note: on `--dry-run` the generator is `None` and never constructed, so no API key is required — Step 3 made that safe.

- [ ] **Step 5: Register the console script** — In `pyproject.toml`, add to `[project.scripts]`:

```toml
mnemonic-generate = "mnemonic.cli.generate:main"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_cli_generate.py tests/unit/services/test_variation_gen.py -q`
Expected: PASS (all CLI + service tests).

- [ ] **Step 7: Full verification**

Run (from `backend/`):
```bash
uv run pytest -q
uv run ruff check src/mnemonic/services/variation_gen.py src/mnemonic/cli/generate.py src/mnemonic/llm/variation
uv run black --check src/mnemonic/services/variation_gen.py src/mnemonic/cli/generate.py src/mnemonic/llm/variation
uv run mypy src/mnemonic/services/variation_gen.py src/mnemonic/cli/generate.py
uv run pytest --cov=mnemonic.services.variation_gen --cov-report=term-missing tests/unit/services/test_variation_gen.py -q
```
Expected: pytest passes except the 3 known pre-existing `tests/test_setup.py` failures; ruff clean (ignore the pyproject deprecation warning); black clean; mypy clean; `variation_gen` coverage ≥ 85%.

- [ ] **Step 8: Verify the console script resolves**

Run: `uv run mnemonic-generate --help`
Expected: prints the usage block with `--deck`, `--limit`, `--dry-run`.

- [ ] **Step 9: Commit**

```bash
git add src/mnemonic/cli/generate.py src/mnemonic/services/variation_gen.py pyproject.toml tests/integration/test_cli_generate.py
git commit -m "feat(cli): mnemonic-generate command for variation generation"
```

---

## Notes for the implementer

- **This is the first feature that spends real money.** Nothing in the test suite makes a network call — every test stubs the client with a `MagicMock` returning a canned `Completion`. Keep it that way.
- **`--dry-run` must construct no client** and require no API key; it is the safe way to preview a run.
- **Budget is checked before every card**, not once per run — `assert_within_budget()` is a pre-flight check with no per-call decrement, so re-checking each iteration is what stops a long batch overrunning the cap.
- **`base_card_text` is the raw `## Card` section** (cloze markers intact) from `note_inputs`, NOT `build_faces` output. `build_faces` supplies only `base_q`/`base_a` for the training record. Keeping these distinct matters — the prompt needs to see the markers.
- **Two defects fixed in Task 1** because this feature depends on them: variations were born `shown_count=1` (skewing B2-Display's least-shown-first rotation), and the generator ignored `PromptVersion.instruction_text` (so compiled challengers were never used despite being recorded).
- **Known pre-existing hazards, deliberately not addressed** (see spec): `persist_variation` writes the note before the DB rows, so a DB failure can orphan a note entry; and an LLM call that succeeds but fails before persist costs money never recorded in `LLMUsage`.
- **Pre-existing failures to expect:** backend `tests/test_setup.py` (redis/jose/passlib not installed).
