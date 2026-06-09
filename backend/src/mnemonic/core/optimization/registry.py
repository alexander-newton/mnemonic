"""Champion prompt-version seeding and lookup."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemonic.db.models import PromptVersion
from mnemonic.exceptions import OptimizationError

DEFAULT_STRATEGIES = ("rephrase", "specialize", "generalize")


def ensure_champion_versions(
    session: Session,
    *,
    prompts_dir: Path,
    now: datetime,
    strategies: tuple[str, ...] = DEFAULT_STRATEGIES,
) -> list[PromptVersion]:
    """Seed a version_no=0 champion for each strategy that has none yet.

    Idempotent: strategies that already have any PromptVersion row are skipped.

    Args:
        session: Active SQLAlchemy session.
        prompts_dir: Directory containing ``strategies/<name>.md`` seed files.
        now: Timestamp to stamp on created rows.
        strategies: Strategy names to seed.

    Returns:
        The list of newly created PromptVersion rows (empty if all existed).

    Raises:
        OptimizationError: If a strategy's seed markdown file is missing.
    """
    created: list[PromptVersion] = []
    for strategy in strategies:
        existing = session.execute(
            select(PromptVersion).where(PromptVersion.strategy == strategy).limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            continue

        seed_path = prompts_dir / "strategies" / f"{strategy}.md"
        if not seed_path.exists():
            raise OptimizationError(
                f"Cannot seed champion for strategy '{strategy}': "
                f"seed file not found at {seed_path}."
            )

        version = PromptVersion(
            id=uuid.uuid4().hex,
            strategy=strategy,
            version_no=0,
            instruction_text=seed_path.read_text(),
            demos="[]",
            status="champion",
            parent_version_id=None,
            compiled_from_n_examples=None,
            created_at=now,
        )
        session.add(version)
        created.append(version)
    return created


def get_champion(session: Session, strategy: str) -> PromptVersion:
    """Return the current champion PromptVersion for a strategy.

    Args:
        session: Active SQLAlchemy session.
        strategy: Strategy name.

    Returns:
        The champion PromptVersion.

    Raises:
        OptimizationError: If no champion exists for the strategy.
    """
    champion = session.execute(
        select(PromptVersion).where(
            PromptVersion.strategy == strategy,
            PromptVersion.status == "champion",
        )
    ).scalar_one_or_none()
    if champion is None:
        raise OptimizationError(
            f"No champion prompt version for strategy '{strategy}'. "
            "Run the labeling job once to seed champions from the on-disk prompts."
        )
    return champion
