import yaml
import grpc

import rich_click as click

from typing import Any, Callable, Dict, List, Literal, Optional, Tuple
from pathlib import Path
from .options import GlobalOption

from armonik.common.channel import create_channel

from click import get_app_dir
from pydantic import BaseModel, Field
from pydantic_yaml import to_yaml_str


def CliField(
    *args,
    cli_option: Optional[Callable[..., Any]] = None,
    cli_option_group: Optional[str] = "Common",
    **kwargs,
) -> Any:
    """Enhanced Pydantic Field with CLI metadata using Field.metadata.

    A decorator that extends Pydantic's Field to include CLI-specific metadata.

    Args:
        *args: Variable length argument list to be passed to Pydantic's Field.
        cli_option (Callable[..., Any], optional): Function to handle CLI option processing. Defaults to None.
        cli_option_group (str, optional): Group name for the CLI option. Defaults to "Common".
        **kwargs: Arbitrary keyword arguments to be passed to Pydantic's Field.

    Returns:
        FieldInfo: A Pydantic FieldInfo object with additional CLI metadata.

    Example:
        ```python
        class Config(BaseModel):
            value: str = CliField(cli_option=click.option("--value"), cli_option_group="Advanced")
        ```
    """

    # Create standard FieldInfo object
    field_info = Field(*args, **kwargs)

    # Append custom CLI metadata
    field_info.metadata.append({"cli_option_group": cli_option_group, "cli_option": cli_option})

    return field_info


class TableColumnsDescriptor(BaseModel):
    table: str = Field(
        description="Name of the command group (session, etc.) and optionally command (session_list) to apply this rule to."
    )
    columns: Dict[str, str] = Field(
        description="Dictionary of column names and their descriptions."
    )


class CliConfig:
    default_path = Path(get_app_dir("armonik_cli")) / "config.yml"

    class ConfigModel(BaseModel):
        endpoint: Optional[str] = CliField(
            description="ArmoniK gRPC endpoint to connect to.",
            cli_option_group="ClusterConnection",
            cli_option=click.option(
                "-e",
                "--endpoint",
                type=str,
                help="Endpoint of the cluster to connect to.",
                metavar="ENDPOINT",
                envvar="AK_ENDPOINT",
                cls=GlobalOption,
            ),
        )

        certificate_authority: Optional[Path] = CliField(
            description="Path to the certificate authority file.",
            cli_option_group="ClusterConnection",
            default=None,
            cli_option=click.option(
                "--certificate-authority",
                type=click.Path(exists=True, dir_okay=False),
                help="Path to the certificate authority file.",
                required=False,
                metavar="CA_FILE",
                cls=GlobalOption,
            ),
        )

        client_certificate: Optional[Path] = CliField(
            description="Path to the client certificate file.",
            cli_option_group="ClusterConnection",
            default=None,
            cli_option=click.option(
                "--client-certificate",
                type=click.Path(exists=True, dir_okay=False),
                help="Path to the client certificate file.",
                required=False,
                metavar="CERT_FILE",
                cls=GlobalOption,
            ),
        )

        client_key: Optional[Path] = CliField(
            description="Path to the client key file.",
            cli_option_group="ClusterConnection",
            default=None,
            cli_option=click.option(
                "--client-key",
                type=click.Path(exists=True, dir_okay=False),
                required=False,
                help="Path to the client key file.",
                metavar="KEY_FILE",
                cls=GlobalOption,
            ),
        )

        debug: bool = CliField(
            default=False,
            description="Whether to print the stack trace of internal errors.",
            cli_option_group="Common",
            cli_option=click.option(
                "--debug/--no-debug",
                is_flag=True,
                default=False,
                help="Print debug logs and internal errors.",
                show_default=True,
                envvar="AK_DEBUG",
                cls=GlobalOption,
            ),
        )

        verbose: bool = CliField(
            default=False,
            description="Whether or not to log info.",
            cli_option_group="Common",
            cli_option=click.option(
                "--verbose/--no-verbose",
                is_flag=True,
                default=False,
                help="Whether or not to log info.",
                show_default=True,
                envvar="AK_VERBOSE",
                cls=GlobalOption,
            ),
        )

        output: Literal["json", "yaml", "table", "auto"] = CliField(
            default="auto",
            description="Commands output format.",
            cli_option_group="Common",
            cli_option=click.option(
                "-o",
                "--output",
                type=click.Choice(["yaml", "json", "table", "auto"], case_sensitive=False),
                default="auto",
                show_default=True,
                help="Commands output format.",
                metavar="FORMAT",
                envvar="AK_OUTPUT",
                cls=GlobalOption,
            ),
        )
        table_columns: List[TableColumnsDescriptor] = Field(
            default=[
                TableColumnsDescriptor(
                    table="session",
                    columns={"ID": "SessionId", "Status": "Status", "CreatedAt": "CreatedAt"},
                ),
                TableColumnsDescriptor(
                    table="result",
                    columns={
                        "Name": "Name",
                        "ID": "ResultId",
                        "Status": "Status",
                        "CreatedAt": "CreatedAt",
                    },
                ),
                TableColumnsDescriptor(
                    table="partition",
                    columns={"ID": "Id", "PodReserved": "PodReserved", "PodMax": "PodMax"},
                ),
                TableColumnsDescriptor(
                    table="task",
                    columns={"ID": "Id", "Status": "Status", "CreatedAt": "CreatedAt"},
                ),
            ],
            description="List of table columns to be used in the output.",
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "CliConfig":
        """
        Loads the configuration from a YAML file and merges it with default values.
        Args:
            config_path (Path): Path to the YAML configuration file.
        Returns:
            CliConfig: A new configuration instance with merged values.
        Notes:
            - If the config file doesn't exist, an empty configuration will be created
            - Only fields present in the YAML file will override default values
            - The loaded configuration is not validated against the model schema
        Example:
            >>> config = CliConfig.from_file(Path("config.yaml"))
        """

        try:
            with open(config_path, "r") as f:
                # If the file is empty then raw_data is set to {}
                raw_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            # If file doesn't exist, just build empty dict
            raw_data = {}

        # Merge with defaults by unpacking only the set fields over the default model
        unvalidated_model = cls.ConfigModel.model_construct(**raw_data)
        new_config_instance = cls()
        new_config_instance._config = unvalidated_model
        return new_config_instance

    @classmethod
    def from_dict(cls, config_dict: dict) -> "CliConfig":
        """
        Loads the configuration from a dictionary and merges with default values.
        Args:
            config_dict (dict): Dictionary containing configuration key-value pairs
        Returns:
            CliConfig: A new instance of CliConfig with the loaded configuration
        Example:
            >>> config = CliConfig.from_dict({"host": "localhost", "port": 8080})
        """

        unvalidated_model = cls.ConfigModel.model_construct(**config_dict)
        new_config_instance = cls()
        new_config_instance._config = unvalidated_model
        return new_config_instance

    def __init__(self):
        """
        If a config model is provided, we store it directly.
        Otherwise, we create a new unvalidated model (with defaults),
        then optionally load from the default file if it exists.
        """
        self._config = self.ConfigModel.model_construct()
        self.default_path.parent.mkdir(parents=True, exist_ok=True)

        if self.default_path.exists():
            # Merge file contents into the unvalidated model
            file_config = yaml.safe_load(self.default_path.read_text()) or {}
            for k, v in file_config.items():
                setattr(self._config, k, v)
        else:
            # If no file, just write defaults
            self._write_to_file()

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
        """
        Helper method to write the current config to disk.

        This method writes the current configuration to the default configuration file path
        without validating it. The configuration is written in YAML format.

        Raises:
            IOError: If there is an error writing to the file.
        """
        with open(self.default_path, "w") as f:
            f.write(to_yaml_str(self._config))

    def get_table_columns(
        self, command_group: str, command: str
    ) -> Optional[List[Tuple[str, str]]]:
        """
        Get the table columns for a given command group/command.
        """
        for table_columns in self.table_columns:
            if table_columns.table == f"{command_group}_{command}":
                return list(table_columns.columns.items())
            elif table_columns.table == f"{command_group}":
                return list(table_columns.columns.items())
        return None

    def get(self, field: str):
        """
        Returns the value of the given field in the config, or None if it doesn't exist.
        """
        return getattr(self._config, field, None)

    def set(self, **kwargs):
        """
        Updates the configuration fields with the passed kwargs and writes them back to disk.

        Args:
            **kwargs: Arbitrary keyword arguments used to update configuration fields.

        Example:
            >>> config.set(endpoint="http://example.com", debug=True)

        Note:
            - The configuration is validated before updating
            - Changes are immediately written to disk after updating

        Raises:
            ValidationError: If the updated configuration is invalid
        """
        self._config = self._config.model_copy(update=kwargs)
        self.validate_config()
        self._write_to_file()

    def layer(self, **kwargs) -> "CliConfig":
        """
        Return a new CliConfig object that merges `kwargs` on top of the current data
        """
        merged_dict = dict(self._config.__dict__)
        for key, value in kwargs.items():
            if key in self.ConfigModel.model_fields.keys():
                merged_dict[key] = value

        new_model = self.ConfigModel.model_construct(**merged_dict)
        final_cli_conf = CliConfig()
        final_cli_conf._config = new_model
        return final_cli_conf

    def validate_config(self):
        """
        Manually trigger Pydantic validation on the final data.
        This overwrites self._config with a fully validated model instance.
        """
        validated_model = self.ConfigModel.model_validate(self._config.__dict__)
        self._config = validated_model


def create_grpc_channel(config: CliConfig) -> grpc.Channel:
    """
    Create a gRPC channel based on the configuration.
    """
    cleaner_endpoint = config.endpoint
    if cleaner_endpoint.startswith("http://"):
        cleaner_endpoint = cleaner_endpoint[7:]
    if cleaner_endpoint.endswith("/"):
        cleaner_endpoint = cleaner_endpoint[:-1]
    if config.certificate_authority:
        # Create grpc channel with tls
        channel = create_channel(
            cleaner_endpoint,
            options=(("grpc.ssl_target_name_override", "armonik.local"),),
            certificate_authority=config.certificate_authority,
            client_certificate=config.client_certificate,
            client_key=config.client_key,
        )
    else:
        # Create insecure grpc channel
        channel = grpc.insecure_channel(cleaner_endpoint)
    return channel
