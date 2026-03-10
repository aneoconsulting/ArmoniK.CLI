"""
config_v2.py — New layerconfig-based configuration.

This module provides:
  - CliConfigSchema: the @layer_obj schema (the source of truth)
  - CliConfig: compatibility wrapper that bridges CliConfigSchema to the
    interface the current decorators/commands expect

Once all commands are migrated, the wrapper can be removed and commands
can use CliConfigSchema directly.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from click import get_app_dir
from layer import layer_obj, field, require, one_of, path_exists, solidify, solidify_env

# ──────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────

@layer_obj
class CliConfigSchema:
    # Cluster connection  (only validated when a command needs it)
    endpoint: str = field(str, cluster=[require])
    certificate_authority: str = field(str, cluster=[path_exists], default=None)
    client_certificate: str = field(str, cluster=[path_exists], default=None)
    client_key: str = field(str, cluster=[path_exists], default=None)

    # Common options (always validated)
    output: str = field(str, one_of("json", "yaml", "table", "auto"), default="auto")
    debug: bool = field(bool, default=False)
    verbose: bool = field(bool, default=False)


# ──────────────────────────────────────────────
# Compatibility wrapper
# ──────────────────────────────────────────────

class CliConfig:
    """
    Drop-in replacement for the current CliConfig.

    Wraps CliConfigSchema and exposes the same attribute access, .get(),
    .set(), .layer(), and .validate_config() that the current codebase uses.

    TODO: Once all commands use the `requires=[...]` pattern and build_config(),
    this wrapper can be deleted. Commands will receive CliConfigSchema directly.
    """

    default_path = Path(get_app_dir("armonik_cli")) / "config.yml"

    def __init__(self, schema: Optional[CliConfigSchema] = None):
        if schema is not None:
            self._schema = schema
        else:
            self._schema = CliConfigSchema()
            self.default_path.parent.mkdir(parents=True, exist_ok=True)
            if self.default_path.exists():
                file_data = yaml.safe_load(self.default_path.read_text()) or {}
                file_layer = solidify(file_data, CliConfigSchema, source="default-config")
                self._schema.layer(file_layer)

    # --- Attribute proxy (config.endpoint, config.debug, etc.) ---

    def __getattr__(self, name: str):
        if name.startswith("_") or name in ("default_path",):
            raise AttributeError(name)
        return getattr(self._schema, name)

    # --- Current interface methods (for backward compat) ---

    def get(self, field_name: str) -> Any:
        return getattr(self._schema, field_name, None)

    def set(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if k in self._schema._field_defs:
                setattr(self._schema, k, v)
                self._schema._sources[k] = "set()"
        # Validate only the fields we just set
        self._schema.validate(["*"], fields=list(kwargs.keys())).raise_if_invalid()
        self._write_to_file()

    def layer(self, **kwargs) -> "CliConfig":
        """Returns a new CliConfig with kwargs layered on top. Non-mutating."""
        new_schema = self._schema.copy()
        overlay = solidify(kwargs, CliConfigSchema, source="layer()")
        new_schema.layer(overlay)
        return CliConfig(schema=new_schema)

    def validate_config(self) -> None:
        """Validate all categories. Raises on failure."""
        self._schema.validate(["*"]).raise_if_invalid()

    def _write_to_file(self) -> None:
        with open(self.default_path, "w") as f:
            yaml.dump(self._schema.to_dict(), f, sort_keys=False)

    # --- TODO: table_columns support ---
    # The current CliConfig stores table_columns as a list of TableColumnsDescriptor
    # objects. This is display logic, not configuration, and should move out of the
    # config object entirely. For now we provide a stub.

    _default_table_columns = {
        "session": {"ID": "SessionId", "Status": "Status", "CreatedAt": "CreatedAt"},
        "result": {"Name": "Name", "ID": "ResultId", "Status": "Status", "CreatedAt": "CreatedAt"},
        "partition": {"ID": "Id", "PodReserved": "PodReserved", "PodMax": "PodMax"},
        "task": {"ID": "Id", "Status": "Status", "CreatedAt": "CreatedAt"},
    }

    def get_table_columns(
        self, command_group: str, command: str
    ) -> Optional[List[Tuple[str, str]]]:
        key = f"{command_group}_{command}"
        cols = self._default_table_columns.get(key) or self._default_table_columns.get(command_group)
        if cols:
            return list(cols.items())
        return None

    def __repr__(self) -> str:
        return f"CliConfig({self._schema.to_dict()})"


# ──────────────────────────────────────────────
# Config builder (replaces inject_config)
# ──────────────────────────────────────────────

def build_config(
    cli_kwargs: Dict[str, Any],
    additional_config_path: Optional[str] = None,
    requires: Optional[List[str]] = None,
) -> CliConfig:
    """
    Build a fully-layered config with proper precedence:
      defaults → default file → additional file → env vars → CLI args

    Args:
        cli_kwargs: Dict of CLI arguments (only explicitly-passed ones).
        additional_config_path: Path to an additional config file (--config flag).
        requires: Validation categories to check. None = common only. [] = none.
    """
    schema = CliConfigSchema()

    # Layer 1: Default config file
    default_path = CliConfig.default_path
    if default_path.exists():
        file_data = yaml.safe_load(default_path.read_text()) or {}
        schema.layer(solidify(file_data, CliConfigSchema, source="default-config"))

    # Layer 2: Additional config file (--config flag)
    if additional_config_path:
        extra_data = yaml.safe_load(Path(additional_config_path).read_text()) or {}
        schema.layer(solidify(extra_data, CliConfigSchema, source=additional_config_path))

    # Layer 3: Environment variables
    schema.layer(solidify_env("AK", CliConfigSchema))

    # Layer 4: CLI arguments (highest priority)
    # Filter out None values — these are unset Click options
    explicit_kwargs = {k: v for k, v in cli_kwargs.items() if v is not None}
    if explicit_kwargs:
        schema.layer(solidify(explicit_kwargs, CliConfigSchema, source="cli"))
    schema.resolve()
    # Validate
    if requires is None:
        schema.validate(["common"]).raise_if_invalid()
    elif len(requires) > 0:
        schema.validate(requires).raise_if_invalid()
    # else: requires=[] means no validation

    return CliConfig(schema=schema)
