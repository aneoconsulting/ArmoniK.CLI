import pytest
import yaml
from unittest.mock import patch

from armonik_cli.core.config import CliConfig


@pytest.fixture
def mock_app_dir(tmp_path):
    """
    Pytest fixture that mocks click.get_app_dir to return a temp directory.
    This ensures each test runs with a fresh config location.
    """
    with patch("armonik_cli.core.config.get_app_dir", return_value=str(tmp_path)):
        yield tmp_path


def test_config_file_creation_if_missing(mock_app_dir):
    """
    Tests that if no config file exists, CliConfig creates one with default values.
    """
    config = CliConfig()
    config_file = mock_app_dir / "config.yml"

    # Check that the file is created
    assert config_file.exists(), "Expected config.yml to be created if it didn't exist."

    # Check the default values in memory
    assert config.endpoint is None
    assert config.debug is False
    assert config.output == "auto"

    # Check the default values on disk
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    assert data["endpoint"] is None
    assert data["debug"] is False
    assert data["output"] == "auto"


def test_partial_config_file_merge(mock_app_dir):
    """
    Tests that if a config file exists with some fields, the missing fields
    are merged in with default values.
    """
    config_file = mock_app_dir / "config.yml"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write a partial config to disk
    partial_data = {"endpoint": "http://example.com"}
    with open(config_file, "w") as f:
        yaml.safe_dump(partial_data, f)

    # Initialize CliConfig, which should merge missing defaults
    config = CliConfig()

    # 'endpoint' should come from file
    assert config.endpoint == "http://example.com"
    # 'debug' and 'output' should be defaults
    assert config.debug is False
    assert config.output == "auto"


def test_getattr_raises_for_invalid_field(mock_app_dir):
    """
    Tests that accessing an invalid attribute via dot notation
    raises AttributeError.
    """
    config = CliConfig()
    with pytest.raises(AttributeError):
        _ = config.some_invalid_field
