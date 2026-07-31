from pathlib import Path
from unittest.mock import MagicMock

from mnemonic.llm.client import Completion, Usage
from mnemonic.llm.variation.generator import GeneratedVariation, VariationGenerator
from mnemonic.llm.variation.strategy import select_strategy


def test_select_strategy_rephrase_for_leech():
    s = select_strategy(reps=10, lapses=4, recent_ratings=[1, 2, 1])
    assert s == "rephrase"


def test_select_strategy_generalize_when_easy():
    s = select_strategy(reps=20, lapses=0, recent_ratings=[4, 4, 4])
    assert s == "generalize"


def test_select_strategy_specialize_default():
    s = select_strategy(reps=2, lapses=0, recent_ratings=[3])
    assert s == "specialize"


def test_generator_parses_qa_from_response():
    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: When is X?\nA: When Y.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=100,
            output_tokens=20,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_millicents=15,
        ),
    )
    # Use the real prompts directory shipped in the repo
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "src" / "mnemonic" / "llm" / "prompts" / "variation"
    )
    gen = VariationGenerator(client=client, prompts_dir=prompts_dir)
    out = gen.generate(
        strategy="rephrase",
        base_card_text="A {{c1::NE}} is stable. ^card-x",
        note_context="Mutual best responses.",
        prior_variations=[],
        fsrs={"stability": 4.0, "reps": 5, "lapses": 0, "recent_ratings": [3, 4]},
        model="claude-haiku-4-5",
    )
    assert isinstance(out, GeneratedVariation)
    assert out.question == "When is X?"
    assert out.answer == "When Y."
    assert out.cost_millicents == 15


def test_instruction_text_overrides_the_on_disk_strategy():
    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: When is X?\nA: When Y.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=100,
            output_tokens=20,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_millicents=15,
        ),
    )
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "src" / "mnemonic" / "llm" / "prompts" / "variation"
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
    client = MagicMock()
    client.generate.return_value = Completion(
        text="Q: When is X?\nA: When Y.",
        model="claude-haiku-4-5",
        usage=Usage(
            input_tokens=100,
            output_tokens=20,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_millicents=15,
        ),
    )
    prompts_dir = (
        Path(__file__).resolve().parents[3] / "src" / "mnemonic" / "llm" / "prompts" / "variation"
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
