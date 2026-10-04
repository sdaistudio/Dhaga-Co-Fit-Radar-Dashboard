import config

KEYS = ["ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"]


def _clear(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER", "auto")
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)


def test_no_key_is_offline(monkeypatch):
    _clear(monkeypatch)
    assert config.resolve_provider() == "offline"


def test_openrouter_key_selects_openrouter(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert config.resolve_provider() == "openrouter"


def test_anthropic_key_wins_over_openrouter(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert config.resolve_provider() == "anthropic"


def test_openrouter_has_models_and_prices():
    assert all(config.MODELS["openrouter"].values())
    assert all(p > 0 for pair in config.PRICES["openrouter"].values() for p in pair)
