"""Entry point script for PyInstaller.

PyInstaller freezes a script, not a console-script entry point, so it can't
target the installed ``armonik`` launcher directly. Do not rename this file to
``armonik.py``: PyInstaller puts the script's directory first on the analysis
path, which would shadow the installed ``armonik`` package.
"""

from armonik_cli.cli import cli

if __name__ == "__main__":
    # Release assets carry the version and platform in their filename, and click
    # derives the usage line from basename(sys.argv[0]) at runtime -- so without
    # an explicit prog_name every help screen would read
    # "Usage: armonik-0.5.0-linux-x86_64 ...".
    cli(prog_name="armonik")
