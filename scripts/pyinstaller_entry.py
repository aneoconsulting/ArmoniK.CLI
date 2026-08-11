"""Entry point script for PyInstaller.

PyInstaller freezes a script, not a console-script entry point, so it can't
target the installed ``armonik`` launcher directly. Do not rename this file to
``armonik.py``: PyInstaller puts the script's directory first on the analysis
path, which would shadow the installed ``armonik`` package.
"""

from armonik_cli.cli import cli

if __name__ == "__main__":
    cli()
