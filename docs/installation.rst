Installation
============

Requirements
------------

- Python 3.8+
- An ArmoniK deployment to run the commands against.

Install from source
-------------------

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


Install the CLI in the environment you just created.

.. code-block:: console

   $ pip install .


Install from PyPI
-----------------

Install ArmoniK CLI 

.. code-block:: console

   $ pip install armonik-cli


Connecting to Your ArmoniK Cluster
----------------------------------

There are several ways to specify connection details for your ArmoniK cluster:

1. Using the ``--endpoint`` option:

   .. code-block:: console
   
      $ armonik --endpoint <cluster-endpoint> cluster info

2. Using environment variables:

   .. code-block:: console
   
      $ export AK_ENDPOINT=<cluster-endpoint>
      $ armonik cluster info

3. Using a configuration file (see :ref:`configuration documentation <configuration>` for details).

When deploying ArmoniK from the official repository, you'll receive a pre-configured file. The deployment process will prompt you to run:

.. code-block:: console
   
   $ export AKCONFIG=<path-to-generated-config>

You can then either:

.. code-block:: console

   $ armonik -c <path-to-generated-config> cluster info 

Or export the variable as requested so the configuration is automatically loaded.

**Connection Notes:**

- For non-TLS connections: Use just the host and port (e.g., ``172.16.17.18:5001``)
- For TLS connections: Include the protocol and use additional TLS options as needed

   .. code-block:: console
   
      $ armonik --endpoint <endpoint> --certificate-authority <ca-file> --client-certificate <cert-file> --client-key <key-file> cluster info