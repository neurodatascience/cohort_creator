from __future__ import annotations

import os
from pathlib import Path

import pytest

# needs the 'update' extra
pytest.importorskip("datalad")
pytest.importorskip("mne")

from bids_inventory._update import CONFIG_ENV_VAR, config, config_path, get_auth  # noqa: E402


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config.cache_clear()
    yield
    config.cache_clear()


def test_default_config_has_no_local_paths():
    """The packaged config must not contain paths of a given machine."""
    assert config()["local_paths"]["openneuro"]["OpenNeuroDatasets"] is None
    assert config()["auth"]["token_file"] is None


def test_config_path_not_set():
    with pytest.raises(ValueError, match="'local_paths.openneuro.OpenNeuroDatasets' is not set"):
        config_path("local_paths", "openneuro", "OpenNeuroDatasets")


def test_user_config(tmp_path, monkeypatch):
    user_config = tmp_path / "config.yml"
    user_config.write_text("local_paths:\n    openneuro:\n        OpenNeuroDatasets: ~/openneuro\n")
    monkeypatch.setenv(CONFIG_ENV_VAR, str(user_config))

    assert config_path("local_paths", "openneuro", "OpenNeuroDatasets") == Path.home() / "openneuro"
    # keys not in the user file keep their default
    assert config()["local_paths"]["datalad"] == {
        "OpenNeuroDatasets": None,
        "OpenNeuroDerivatives": None,
    }


def test_get_auth(tmp_path, monkeypatch):
    assert get_auth() is None

    token_file = tmp_path / "token.txt"
    token_file.write_text("from_file\n")
    user_config = tmp_path / "config.yml"
    user_config.write_text(f"auth:\n    token_file: {token_file}\n")
    monkeypatch.setenv(CONFIG_ENV_VAR, str(user_config))
    config.cache_clear()
    assert get_auth() == ("bids-inventory", "from_file")

    # the environment variable takes precedence
    monkeypatch.setenv("GITHUB_TOKEN", "from_env")
    assert get_auth() == ("bids-inventory", "from_env")


def test_cli_config_not_found(tmp_path):
    from bids_inventory._cli import cli

    with pytest.raises(SystemExit):
        cli(["bids_inventory", "update", "--config", str(tmp_path / "missing.yml")])
    assert CONFIG_ENV_VAR not in os.environ
