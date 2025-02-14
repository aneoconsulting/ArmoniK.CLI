from typing import Literal, Optional
from pathlib import Path

from click import get_app_dir
from pydantic import BaseModel, Field
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str


class CliConfig:
    class ConfigModel(BaseModel):
        endpoint: Optional[str] = Field(
            default=None, description="String - ArmoniK gRPC endpoint to connect to."
        )
        debug: bool = Field(
            default=False,
            description="Boolean - Whether to print the stack trace of internal errors.",
        )
        output: Literal["json", "yaml", "table", "auto"] = Field(
            default="auto",
            description="'json', 'yaml', 'table', or 'auto' - Commands output format.",
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "ConfigModel":
        """
        Loads the config from the given file and merges with default values.
        """
        with open(config_path, "r") as f:
            file_config = parse_yaml_raw_as(cls.ConfigModel, f.read())
        # Merge with defaults by unpacking only the set fields over the default model
        return cls.ConfigModel(**file_config.model_dump(exclude_unset=True))

    def __init__(self):
        self.default_path = Path(get_app_dir("armonik_cli")) / "config.yml"
        self.default_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.default_path.exists():
            self._config = self.ConfigModel()
            self._write_to_file()
        else:
            self._config = self.from_file(self.default_path)

    def __repr__(self) -> str:
        return f"CliConfig({self._config!r})"

    def __getattr__(self, name: str):
        """
        Delegates attribute access to the underlying _config.
        This allows direct usage like `config.endpoint` or `config.debug`.
        """
        if hasattr(self._config, name):
            return getattr(self._config, name)
        # If it's not on the ConfigModel, raise the usual AttributeError
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _write_to_file(self):
        """Helper method to write the current config to disk."""
        with open(self.default_path, "w") as f:
            f.write(to_yaml_str(self._config))

    def get(self, field: str):
        """
        Returns the value of the given field in the config, or None if it doesn't exist.
        """
        return getattr(self._config, field, None)

    def set(self, **kwargs):
        """
        Updates the configuration fields with the passed kwargs.
        Then writes them back to disk.
        Example usage: config.set(endpoint="http://example.com", debug=True)
        """
        self._config = self._config.copy(update=kwargs)
        self._write_to_file()
