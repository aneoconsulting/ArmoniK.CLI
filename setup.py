# WARNING: This setup.py script is only for customizing the local version scheme with setuptools-scm.
# All other project configuration must be provided in pyproject.toml. Use this script cautiously and
# refer to the documentation for more details: https://setuptools-scm.readthedocs.io/en/latest/customizing/.
# For more details on the use of setup.py and its deprecated features, please refer to:
# https://packaging.python.org/en/latest/discussions/setup-py-deprecated/

from os import environ
from setuptools import setup
from setuptools_scm import ScmVersion


def get_local_schema(version: ScmVersion) -> str:
    """
    Generate a custom local version scheme for setuptools-scm.

    Generates a local version string based on environment variables. If RELEASE is unset,
    appends .dev<run_id> for development builds; otherwise, returns an empty string. The
    value of <run_id> is retrieved from the GITHUB_RUN_ID environment variable if it exists,
    otherwise the default value used is 0.

    Args:
        version: The ScmVersion object passed by setuptools-scm.

    Returns:
        The custom local version string.
    """
    run_id = environ.get("GITHUB_RUN_ID", "0")
    event_name = environ.get("GITHUB_EVENT_NAME", "")
    if event_name == "release":
        return ""
    return f".dev{run_id}"


setup(
    use_scm_version={
        "version_scheme": "post-release",
        "local_scheme": get_local_schema,
        "version_file": "src/armonik_cli/_version.py",
    }
)
