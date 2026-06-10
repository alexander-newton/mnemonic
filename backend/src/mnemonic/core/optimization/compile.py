"""Compile a challenger prompt version for a strategy using DSPy."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import dspy
from dspy.teleprompt import BootstrapFewShot
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.dspy_lm import harvest_usage
from mnemonic.core.optimization.examples import build_trainset, split_examples
from mnemonic.core.optimization.metric import is_valid_variation, reward_metric
from mnemonic.core.optimization.registry import get_champion
from mnemonic.core.optimization.signatures import VariationModule, make_variation_signature
from mnemonic.db.models import LLMUsage, PromptVersion
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import OptimizationError


def _next_version_no(session: Session, strategy: str) -> int:
    current = session.execute(
        select(func.max(PromptVersion.version_no)).where(PromptVersion.strategy == strategy)
    ).scalar_one_or_none()
    return (current or 0) + 1


def _run_validity_gate(
    program: VariationModule, val: list[dspy.Example], min_pass_rate: float
) -> None:
    """Raise OptimizationError if too few val predictions are valid."""
    if not val:  # pragma: no cover - defensive; callers pass a non-empty split
        return
    valid = 0
    for example in val:
        pred = program(**example.inputs())
        if is_valid_variation(
            base_q=example.base_q,
            base_a=example.base_a,
            question=getattr(pred, "question", "") or "",
            answer=getattr(pred, "answer", "") or "",
        ):
            valid += 1
    pass_rate = valid / len(val)
    if pass_rate < min_pass_rate:
        raise OptimizationError(
            f"Compiled challenger failed the validity gate: {valid}/{len(val)} "
            f"valid ({pass_rate:.0%} < {min_pass_rate:.0%}). Not storing it."
        )


def compile_challenger(
    engine: Engine,
    *,
    strategy: str,
    config: OptimizationConfig,
    lm: dspy.BaseLM,
    now: datetime,
) -> PromptVersion:
    """Compile and persist a challenger prompt version for a strategy.

    Args:
        engine: SQLAlchemy engine for the state DB.
        strategy: Strategy to optimize (must have a champion).
        config: Optimization config.
        lm: A configured DSPy LM (real OpenRouter LM in production; DummyLM in
            tests). Used for bootstrapping and the validity gate.
        now: Timestamp for the new row and the usage record.

    Returns:
        The newly written challenger PromptVersion.

    Raises:
        OptimizationError: If the optimizer name is unsupported or the compiled
            program fails the validity gate.
        InsufficientDataError: If the trainset is too small.
    """
    if config.optimizer != "bootstrap":
        raise OptimizationError(
            f"Unsupported optimizer '{config.optimizer}'. Phase 2 implements " "only 'bootstrap'."
        )

    dspy.configure(lm=lm)

    with session_scope(engine) as session:
        champion = get_champion(session, strategy)
        champion_id = champion.id
        instruction = champion.instruction_text
        examples = build_trainset(session, strategy=strategy, config=config)
        version_no = _next_version_no(session, strategy)

    train, val = split_examples(examples, val_fraction=config.val_fraction, seed=config.split_seed)

    student = VariationModule(make_variation_signature(instruction))
    optimizer = BootstrapFewShot(
        metric=reward_metric,
        metric_threshold=0.0,
        max_bootstrapped_demos=config.max_bootstrapped_demos,
        max_labeled_demos=config.max_labeled_demos,
    )
    compiled = optimizer.compile(student, trainset=train)

    # Always run the validity gate on a non-empty split: fall back to the train
    # set if the validation split floored to empty (small trainset + low
    # val_fraction) so the safety gate is never silently skipped.
    validity_error: OptimizationError | None = None
    try:
        _run_validity_gate(compiled, val or train, config.validity_min_pass_rate)
    except OptimizationError as exc:
        validity_error = exc

    # Record spend FIRST so cost is never dropped, even when the gate rejects the
    # challenger (NO SILENT FAILURES on cost accounting). harvest_usage runs after
    # the gate so it also captures the gate's own LM calls.
    totals = harvest_usage(lm.history)
    with session_scope(engine) as session:
        session.add(
            LLMUsage(
                id=uuid.uuid4().hex,
                timestamp=now,
                model=getattr(lm, "model", "unknown"),
                purpose=f"optimize:{strategy}",
                input_tokens=totals.input_tokens,
                output_tokens=totals.output_tokens,
                cache_read_tokens=0,
                cache_creation_tokens=0,
                cost_millicents=totals.cost_millicents,
                card_id=None,
            )
        )

    if validity_error is not None:
        raise validity_error

    demos_state = compiled.predict.dump_state().get("demos", [])
    challenger = PromptVersion(
        id=uuid.uuid4().hex,
        strategy=strategy,
        version_no=version_no,
        instruction_text=compiled.predict.signature.instructions,
        demos=json.dumps(demos_state),
        status="challenger",
        parent_version_id=champion_id,
        compiled_from_n_examples=len(examples),
        created_at=now,
    )
    with session_scope(engine) as session:
        session.add(challenger)
    return challenger
