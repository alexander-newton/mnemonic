from mnemonic.llm.cache import EPHEMERAL_1H, EPHEMERAL_5M, build_cached_system


def test_three_cached_blocks():
    blocks = build_cached_system(
        skill_md="SKILL CONTENT",
        strategy_md="STRATEGY",
        note_context="CTX",
    )
    assert len(blocks) == 3
    assert blocks[0].text == "SKILL CONTENT"
    assert blocks[0].cache_control == EPHEMERAL_1H
    assert blocks[1].cache_control == EPHEMERAL_1H
    assert blocks[2].cache_control == EPHEMERAL_5M


def test_no_more_than_four_breakpoints():
    blocks = build_cached_system(skill_md="x", strategy_md="y", note_context="z")
    cached = [b for b in blocks if b.cache_control is not None]
    assert len(cached) <= 4
