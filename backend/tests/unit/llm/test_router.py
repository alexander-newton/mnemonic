from mnemonic.llm.router import pick_model


def test_rephrase_uses_haiku():
    assert pick_model(strategy="rephrase", recent_failures=0,
                      model_default="claude-sonnet-4-6",
                      model_rephrase="claude-haiku-4-5") == "claude-haiku-4-5"


def test_specialize_uses_default():
    assert pick_model(strategy="specialize", recent_failures=0,
                      model_default="claude-sonnet-4-6",
                      model_rephrase="claude-haiku-4-5") == "claude-sonnet-4-6"


def test_many_recent_failures_force_default():
    assert pick_model(strategy="rephrase", recent_failures=4,
                      model_default="claude-sonnet-4-6",
                      model_rephrase="claude-haiku-4-5") == "claude-sonnet-4-6"
