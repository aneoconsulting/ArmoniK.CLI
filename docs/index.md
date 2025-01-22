# ArmoniK Admin CLI.

This repository is part of the [ArmoniK](https://github.com/aneoconsulting/ArmoniK) project. It provides a command-line tool to monitor and manage ArmoniK clusters.

## Installation

### Requirements

The CLI requires Python version 3.8 or newer. In order to install the ArmoniK CLI in an isolated environment, you must have python3-venv installed on your machine.

```bash
sudo apt update && sudo apt install python3-venv
```

### Install from source

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

Install the CLI in the environment you just created.

```bash
pip install .
```

## Contributing

Contributions are always welcome!

See [CONTRIBUTING](CONTRIBUTING.md) for ways to get started.