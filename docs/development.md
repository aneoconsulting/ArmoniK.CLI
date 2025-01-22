# Installing ArmoniK.Admin.CLI for development :

### Requirements

The CLI requires Python version 3.8 or newer. In order to install the ArmoniK CLI in an isolated environment, you must have python3-venv installed on your machine.

```bash
sudo apt update && sudo apt install python3-venv
```

### Installation

To install the CLI from source, first clone this repository.

```bash
git clone git@github.com/aneoconsulting/ArmoniK.Admin.CLI.git
```

Navigate in the root directory

```bash
cd ArmoniK.Admin.CLI
```

Create and activate the virtual environment

```bash
python -m venv ./venv
source ./venv/bin/activate
```

Perform an editable install of the ArmoniK.Admin.CLI

```bash
pip install -e .
```

### Running tests

We use pytest for unit tests

```bash
pytest tests/
```

### Linting and formatting

Install the development packages

```bash
pip install '.[dev]'
```

Formatting 
```bash
ruff format
```

Linting
```bash
ruff check . 
```

### Documentation

Install the documentation packages

```bash
pip install '.[docs]'
```

Serving the documentation locally 
```bash
mkdocs serve
```

Publishing the documentation to github pages
```bash
mkdocs gh-deploy
```
