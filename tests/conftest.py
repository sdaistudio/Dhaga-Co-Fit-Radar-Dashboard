import pytest
import config


@pytest.fixture(autouse=True)
def _ignore_dotenv_limits(monkeypatch):
    """config.py reads the developer's .env at import. Tests must not depend on it."""
    monkeypatch.setattr(config, "MAX_COMMENTS", 0)
