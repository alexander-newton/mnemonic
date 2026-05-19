"""Variation generator: renders prompt + calls LLM + parses Q/A."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from mnemonic.exceptions import LLMError
from mnemonic.llm.cache import build_cached_system
from mnemonic.llm.client import LLMClient, Message, Block


@dataclass(frozen=True)
class GeneratedVariation:
    """A variation produced by the LLM for a single card review."""

    strategy: str
    question: str
    answer: str
    model: str
    cost_millicents: int
    raw_response: str


class VariationGenerator:
    """Renders a variation prompt, calls the LLM, and parses the Q/A response.

    Args:
        client: An LLMClient implementation (Anthropic backend in Phase 1).
        prompts_dir: Path to the directory containing SKILL.md, strategies/, and user.j2.
    """

    def __init__(self, *, client: LLMClient, prompts_dir: Path) -> None:
        self.client = client
        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(prompts_dir),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def _load_skill(self) -> str:
        """Load the SKILL.md file from the prompts directory.

        Returns:
            The content of SKILL.md as a string.

        Raises:
            FileNotFoundError: If SKILL.md is missing from prompts_dir.
        """
        return (self.prompts_dir / "SKILL.md").read_text()

    def _load_strategy(self, strategy: str) -> str:
        """Load a strategy markdown file by name.

        Args:
            strategy: One of "rephrase", "specialize", or "generalize".

        Returns:
            The content of the strategy file as a string.

        Raises:
            LLMError: If the strategy template file does not exist.
        """
        path = self.prompts_dir / "strategies" / f"{strategy}.md"
        if not path.exists():
            raise LLMError(f"Strategy template not found: {path}")
        return path.read_text()

    def generate(
        self,
        *,
        strategy: str,
        base_card_text: str,
        note_context: str,
        prior_variations: list[dict[str, Any]],
        fsrs: dict[str, Any],
        model: str,
    ) -> GeneratedVariation:
        """Generate a variation for the given card using the specified strategy.

        Args:
            strategy: One of "rephrase", "specialize", or "generalize".
            base_card_text: The raw card content (Markdown with cloze markers).
            note_context: The card's ## Context section from its vault note.
            prior_variations: List of prior variation dicts with keys q, a, rating.
            fsrs: Dict with keys stability, reps, lapses, recent_ratings.
            model: The model identifier to use for generation.

        Returns:
            A GeneratedVariation with parsed question and answer.

        Raises:
            LLMError: If the strategy template is missing or the LLM response
                cannot be parsed into Q:/A: blocks.
        """
        skill_md = self._load_skill()
        strategy_md = self._load_strategy(strategy)
        system_blocks = build_cached_system(
            skill_md=skill_md, strategy_md=strategy_md, note_context=note_context
        )

        user_tpl = self.env.get_template("user.j2")
        user_text = user_tpl.render(
            base_card_text=base_card_text,
            prior_variations=prior_variations,
            fsrs=fsrs,
            strategy_name=strategy,
        )

        completion = self.client.generate(
            system=system_blocks,
            messages=[Message(role="user", blocks=[Block(text=user_text)])],
            model=model,
            max_tokens=400,
        )

        q, a = self._parse_qa(completion.text)
        return GeneratedVariation(
            strategy=strategy,
            question=q,
            answer=a,
            model=completion.model,
            cost_millicents=completion.usage.cost_millicents,
            raw_response=completion.text,
        )

    @staticmethod
    def _parse_qa(text: str) -> tuple[str, str]:
        """Extract Q: and A: lines from LLM response text.

        Args:
            text: Raw LLM response string.

        Returns:
            A tuple of (question, answer) strings.

        Raises:
            LLMError: If the response does not contain parseable Q:/A: lines.
        """
        lines = [line.rstrip() for line in text.strip().splitlines() if line.strip()]
        q_line = next((line for line in lines if line.startswith("Q:")), None)
        a_line = next((line for line in lines if line.startswith("A:")), None)
        if q_line is None or a_line is None:
            raise LLMError(
                "LLM did not return parseable Q:/A: blocks. "
                f"Got: {text[:200]!r}"
            )
        return q_line[2:].strip(), a_line[2:].strip()
