Working on ArmoniK.CLI
============================


Configuring ArmoniK.CLI for development
---------------------------------------------


Requirements
`````````````

The CLI requires Python version 3.8 or newer. In order to install the ArmoniK CLI in an isolated environment, you must have python3-venv installed on your machine.

.. code-block:: console 

    $ sudo apt update && sudo apt install python3-venv


Installation
`````````````

To install the CLI from source, first clone this repository.

.. code-block:: console 

    $ git clone git@github.com/aneoconsulting/ArmoniK.CLI.git


Navigate in the root directory

.. code-block:: console 

    $ cd ArmoniK.CLI


Create and activate the virtual environment

.. code-block:: console 

    $ python -m venv ./venv
    $ source ./venv/bin/activate


Perform an editable install of the ArmoniK.CLI

.. code-block:: console 

    $ pip install -e .


Running tests
`````````````

We use pytest for unit tests

.. code-block:: console 

    $ pytest tests/


To run the integration test you can just deploy ArmoniK locally and then run

.. code-block:: console

    $ pytest tests/integration.py 



Linting and formatting
``````````````````````

Install the development packages

.. code-block:: console 

    $ pip install '.[dev]'


Formatting 

.. code-block:: console 

    $ ruff format


Linting

.. code-block:: console 

    $ ruff check . 


Documentation
`````````````
Install the documentation packages 

.. code-block:: console 

    $ pip install '.[docs]'

Serving the documentation locally 

.. code-block:: console

    $ sphinx-autobuild docs docs/_build/html 

Building the documentation 

.. code-block:: console 

    $ cd docs
    $ make html

Using ArmoniK.CLI with a custom version of ArmoniK Python API
-------------------------------------------------------------------

ArmoniK.CLI makes use of a good chunk of the ArmoniK Python API which makes it especially potent 
when it comes to driving the development of said package. You can perform an editable install of the armonik package

.. code-block:: toml 

    dependencies = [
        "armonik @ file://local_armonik_repo_folder/ArmoniK.Api/packages/python"
    ]

where you can point to your local ArmoniK package.

Another option is to perform an editable install of said package in the CLI project environment.

Extension support
-----------------

Another way to contribute to ArmoniK.CLI is through extensions. 
Support for this feature is still in ongoing development but for functionality that doesn't feel core to 
the experience of ArmoniK.CLI extensions will be the prefered way moving forward.   