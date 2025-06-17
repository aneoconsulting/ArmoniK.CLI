import pytest
import yaml
import os


from unittest.mock import patch
from pathlib import Path
from armonik_cli_core.configuration import CliConfig


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory for config files and set it as the app directory."""
    config_dir = tmp_path / "config.yml"
    CliConfig.default_path = config_dir
    return tmp_path


@pytest.fixture
def default_config_file(temp_config_dir):
    """Create a default config file with some base settings."""
    config_path = temp_config_dir / "config.yml"
    config_content = {"endpoint": "default-endpoint", "debug": False, "output": "table"}
    config_path.write_text(yaml.dump(config_content))
    return config_path


@pytest.fixture
def additional_config_file(tmp_path):
    """Create an additional config file with different settings."""
    config_path = tmp_path / "additional_config.yml"
    config_content = {"endpoint": "additional-endpoint", "debug": True, "output": "json"}
    config_path.write_text(yaml.dump(config_content))
    return config_path


@pytest.fixture
def mock_click_context():
    """Mock Click context for testing."""
    with patch("click.get_current_context") as mock_context:
        # Mock get_parameter_source
        mock_context.get_parameter_source.return_value = "default"
        yield mock_context


def test_default_config_loading(temp_config_dir):
    """Test that default configuration is loaded correctly."""
    config = CliConfig()
    assert not hasattr(config._config, "endpoint")
    assert config.debug is False
    assert config.output == "auto"


def test_config_file_override(default_config_file):
    """Test that config file values override defaults."""
    config = CliConfig()
    assert config.endpoint == "default-endpoint"
    assert config.debug is False
    assert config.output == "table"


def test_additional_config_override(default_config_file, additional_config_file):
    """Test that additional config file overrides default config."""

    base_config = CliConfig()
    additional_config = CliConfig.from_file(additional_config_file)
    final_config = base_config.layer(**additional_config.model_dump(exclude_unset=True))

    assert final_config.endpoint == "additional-endpoint"
    assert final_config.debug is True
    assert final_config.output == "json"


def test_environment_var_override(default_config_file, additional_config_file):
    """Test that environment variables override both config files."""
    with patch.dict(os.environ, {"AK_ENDPOINT": "env-endpoint"}):
        base_config = CliConfig()
        additional_config = CliConfig.from_file(additional_config_file)
        final_config = base_config.layer(**additional_config.model_dump(exclude_unset=True))
        final_config = final_config.layer(endpoint="env-endpoint")

        assert final_config.endpoint == "env-endpoint"
        assert final_config.debug is True
        assert final_config.output == "json"


def test_cli_option_override(default_config_file, additional_config_file):
    """Test that CLI options override everything else."""
    with patch.dict(os.environ, {"AK_ENDPOINT": "env-endpoint"}):
        base_config = CliConfig()
        additional_config = CliConfig.from_file(additional_config_file)
        final_config = base_config.layer(**additional_config.model_dump(exclude_unset=True))
        final_config = final_config.layer(endpoint="env-endpoint")
        final_config = final_config.layer(endpoint="cli-endpoint")

        assert final_config.endpoint == "cli-endpoint"
        assert final_config.debug is True
        assert final_config.output == "json"


def test_layering_order_complete():
    """Test the complete layering order with all possible sources."""
    with patch.dict(os.environ, {"AK_ENDPOINT": "env-endpoint"}):
        # Create configs with different values for each layer
        default_values = {"endpoint": "default-endpoint", "debug": False, "output": "table"}

        additional_values = {"endpoint": "additional-endpoint", "debug": True, "output": "json"}

        cli_values = {
            "endpoint": "cli-endpoint",
            "debug": False,  # Have to mock the get_parameter_source to properly test CLI layering
            "output": "yaml",
        }

        # Simulate the layering process
        base_config = CliConfig()
        base_config._config = base_config.ConfigModel.model_construct(**default_values)

        # Layer additional config
        final_config = base_config.layer(**additional_values)
        assert final_config.endpoint == "additional-endpoint"

        # Layer environment variables
        final_config = final_config.layer(endpoint="env-endpoint")
        assert final_config.endpoint == "env-endpoint"

        # Layer CLI options
        final_config = final_config.layer(**cli_values)

        # Verify final state reflects proper override order
        assert final_config.endpoint == "cli-endpoint"  # CLI option wins
        assert final_config.debug is False  # CLI option wins
        assert final_config.output == "yaml"  # CLI option wins


def test_validate_config():
    """Test that config validation works correctly."""
    config = CliConfig()

    # Test valid values
    config.set(endpoint="valid-endpoint", output="json", debug=True)
    config.validate_config()
    assert config.endpoint == "valid-endpoint"
    assert config.output == "json"

    # Test invalid output format
    with pytest.raises(Exception):  # Replace with specific exception
        config.set(output="invalid-format")
        config.validate_config()


def test_empty_additional_config(temp_config_dir, default_config_file):
    """Test behavior with empty additional config file."""
    empty_config = Path(default_config_file.parent / "empty.yml")
    empty_config.write_text("")
    loaded_empty_config = CliConfig.from_file(empty_config)
    assert loaded_empty_config._config.model_dump(exclude_unset=True) == {}
