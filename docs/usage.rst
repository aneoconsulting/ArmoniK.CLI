Working with ArmoniK.CLI
========================

The ArmoniK CLI offers commands to interact with various ArmoniK objects. For detailed information about these commands, please refer to the :doc:`CLI Reference <./cli_reference>` or use the help command (``-h``) with the different command groups.

Global Options
-------------

All ArmoniK CLI commands support five global options: ``endpoint``, ``debug``, ``verbose``, ``output`` and ``config``. These options can be placed immediately after the ``armonik`` command (or the command group) to apply to all subsequent commands.

For example, if you have ArmoniK deployed with an endpoint ``170.10.10.122:5001``, you can create a session like this:

.. code-block:: console

    $ armonik session create --max-duration 00:01:00.00 --priority 1 --max-retries 1 --endpoint 170.10.10.122:5001

Or using the global option placement:

.. code-block:: console

    $ armonik -e 170.10.10.122:5001 session create --max-duration 00:01:00.00 --priority 1 --max-retries 1

The ``output`` option controls your preferred output format: ``json`` (default), ``table``, or ``yaml``. The ``debug`` flag enables detailed stacktraces on failure instead of the default concise error messages.

You can create useful aliases for different deployments:

.. code-block:: console

    $ alias armonikl="armonik -e 172.17.63.166:5001 --debug"

This allows you to simply use:

.. code-block:: console

    $ armonikl session list

Instead of the more verbose:

.. code-block:: console

    $ armonik session list -e 172.17.63.166:5001 --debug

Speaking of verbose, all warnings are logged to stderr by default. So you can still pipe your outputs and use them.
You can however pass in ``--verbose`` (or ``--no-verbose``) to output both info and warnings to stdout. 
Running with ``--debug`` enabled will also output the debug output to the standard output.

Note that all log messages are always logged into the ``armonik_cli.log`` file next to the config file in your user directory.

Configuration
------------

ArmoniK CLI uses a layered configuration system that makes it flexible and powerful. The configuration is loaded in the following order, with each layer overriding the previous one:

1. Local configuration file (typically located at ``~/.config/armonik_cli/config.yml``) or the default configuration if it doesn't exist.
2. Configuration file specified via ``-c/--config`` option (it's layered over the local one, so redefined fields are overwritten, while new ones are added onto the local config)
3. Command-line arguments and environment variables

The configuration is managed using a Pydantic model, which ensures type validation and provides descriptive errors when invalid values are provided.

Configuration Commands
~~~~~~~~~~~~~~~~~~~~~

The CLI includes several commands to view and manage your configuration:

Viewing Configuration
^^^^^^^^^^^^^^^^^^^^

To show your current configuration:

.. code-block:: console

    $ armonik config show

To list all available configuration fields with their types, default values, and descriptions:

.. code-block:: console

    $ armonik config list

Managing Configuration Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To get a specific configuration value:

.. code-block:: console

    $ armonik config get endpoint

To set a configuration value:

.. code-block:: console

    $ armonik config set endpoint 172.17.63.166:5001

Configuration File Format
~~~~~~~~~~~~~~~~~~~~~~~~

The configuration file uses YAML format. Here's an example:

.. code-block:: yaml

    endpoint: 172.17.63.166:5001
    debug: true
    output: table
    table_columns:
      - table: session_list
        columns:
          ID: SessionId
          Status: Status
      - table: task
        columns:
          ID: TaskId
          Status: Status
          Created: CreatedAt

Configuration Fields
~~~~~~~~~~~~~~~~~~~

The main configuration fields include:

- ``endpoint``: The ArmoniK gRPC endpoint to connect to
- ``certificate_authority``: Path to the certificate authority file
- ``client_certificate``: Path to the client certificate file
- ``client_key``: Path to the client key file
- ``debug``: Whether to print stack traces for internal errors
- ``output``: Default output format (``json``, ``yaml``, ``table``, or ``auto``)
- ``table_columns``: Custom column definitions for table outputs

Filters
-------

All list commands for ArmoniK objects (sessions, tasks, etc.) support filtering to query entities matching specific conditions.

For example, to get all tasks associated with a specific session:

.. code-block:: console

    $ armonik task list -e 170.10.10.122:5001 --filter "session_id='1085c427-89da-4104-aa32-bc6d3d84d2b2'"

To list all failed tasks within a specific session:

.. code-block:: console

    $ armonik task list -e 172.17.63.166:5001 --filter "session_id='1085c427-89da-4104-aa32-bc6d3d84d2b2' & status = error" 

Filters are a powerful tool for narrowing down your results. While we don't have a comprehensive list of all filterable attributes, you can look for attributes tagged with ``FilterDescriptors`` in the ArmoniK entities code.

Pagination and Sorting
---------------------

When using list commands, you can control the results with pagination and sorting options:

- ``--page`` and ``--page-size``: Control which subset of results to retrieve
- ``--sort-by``: Specify which attribute to sort by
- ``--sort-direction``: Control sort order (ascending or descending)

For example, to get the first 100 tasks ordered by creation time:

.. code-block:: console

    $ armonik task list -e 172.17.63.166:5001 --filter "session_id='1085c427-89da-4104-aa32-bc6d3d84d2b2'" --sort-by "created_at" --output table --page 1 --page-size 100

Output Formats
-------------

ArmoniK CLI supports four output formats:

- ``json``: Detailed JSON output
- ``yaml``: YAML formatted output
- ``table``: Human-readable tabular format
- ``auto``: Default format for each command (tables for list commands, YAML for get commands)

You can specify the output format using the ``-o/--output`` global option or through your configuration.

Customizing Table Columns
~~~~~~~~~~~~~~~~~~~~~~~~

You can customize which columns appear in table outputs by configuring ``table_columns`` in your configuration file. You can specify columns for specific commands:

.. code-block:: yaml

    table_columns:
      - table: session_list
        columns:
          ID: SessionId
          Status: Status
      - table: session_get
        columns:
          ID: SessionId
          Status: Status

Or for entire command groups:

.. code-block:: yaml

    table_columns:
      - table: session
        columns:
          ID: SessionId
          Status: Status

The left side of each column entry (``ID``, ``Status``) defines the display name, while the right side (``SessionId``, ``Status``) references the actual data field.