# ArmoniK CLI

<div align="center">

<!-- TODO: Fix documentation link to point to the ReadTheDocs page (again). -->
[![Latest Release](https://img.shields.io/github/v/release/aneoconsulting/ArmoniK.CLI)](https://github.com/aneoconsulting/ArmoniK.CLI/releases)
[![License](https://img.shields.io/github/license/aneoconsulting/ArmoniK.CLI?label=License&color=blue)](https://github.com/aneoconsulting/ArmoniK.CLI/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://armonikadmincli.readthedocs.io/en/latest/)

Command-line interface for monitoring and managing [ArmoniK](https://github.com/aneoconsulting/ArmoniK) clusters.

<!-- TODO: Fix documentation link to point to the ReadTheDocs page (again). -->
[Documentation](https://armonikadmincli.readthedocs.io/en/latest/) •
[Getting Started](#getting-started) •
[Contributing](#contributing)

</div>

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [Recommended Installation (pipx)](#recommended-installation-pipx)
  - [Alternative Installation Methods](#alternative-installation-methods)
  - [Development Installation](#development-installation)
- [Getting Started](#getting-started)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

The ArmoniK CLI is a tool that provides commands to monitor and manage computations in ArmoniK clusters. It serves as a powerful alternative to the ArmoniK Admin GUI, offering the same core functionality through a terminal interface.

The CLI enables users to:
- Manage results, sessions and partitions.
- Monitor task execution.
- Query task results and metadata.

A key advantage of the CLI is its ability to support automation through scripts and scheduled jobs. This makes it ideal for DevOps workflows, automated testing, and continuous integration/deployment pipelines where GUI interaction is not practical.

## Installation

### Recommended Installation (pipx)

We recommend using [pipx](https://pypa.github.io/pipx/) to install the CLI in an isolated environment:

```bash
pipx install armonik-cli
```

You can check the installation by running:

```bash
armonik --version
```

### Alternative Installation Methods

Alternatively, you can install the CLI using pip or from source.

#### Using pip

```bash
pip install armonik-cli
```

You can check the installation by running:

```bash
armonik --version
```

#### From source

```bash
git clone https://github.com/aneoconsulting/ArmoniK.CLI.git
cd ArmoniK.CLI
pip install -e .
```

You can check the installation by running:

```bash
armonik --version
```

### Development Installation

If you want to contribute to the project, follow the steps for installing from source and add the `[dev,tests]` extra:

```bash
pip install -e .[dev,tests]
```

You can check the installation by running:

```bash
armonik --version
```

## Getting Started

To use the CLI with an ArmoniK cluster, you must provide the CLI with the cluster credentials. The most simple way to do this is to use the `--endpoint` option:

```bash
armonik --endpoint <cluster-endpoint> cluster info
```

There exists additional options to connect to clusters that use TLS. In addition, to simplify the usage of the CLI, you can set the default values for the `--endpoint` and the others connection options using a configuration file.

You don't need to specify the endpoint if you exported the AKCONFIG variable when prompted to when deploying an ArmoniK cluster, because that environment variable points to a pre-filled configuration.

To list available commands and options, you can use the `--help` or `-h` option:

```bash
armonik --help
```

To learn more about the CLI, please refer to the documentation.

## Documentation

<!-- TODO: Fix documentation link to point to the ReadTheDocs page. -->
The full documentation is available on [ReadTheDocs](https://armonikadmincli.readthedocs.io/en/latest/). Otherwise, you can build and view the documentation locally by running:

```bash
pip install -e .[docs]
sphinx-autobuild docs _build/html
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for more information.

## License

This project is licensed under the [Apache 2.0 License](LICENSE).
