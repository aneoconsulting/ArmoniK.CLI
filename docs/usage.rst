Working with ArmoniK.CLI
==============================

the ArmoniK CLI offers commands to work with the different ArmoniK objects, for more information about how to use these specific 
commands please refer to the :doc:`CLI Reference <./cli_reference>` or use the help command for the command groups
of the different ArmoniK entities. `-h` is your best friend !

Global Options
--------------

For instance, assuming you have ArmoniK deployed with an endpoint `170.10.10.122:5001` you can create a session 
by running 

.. code-block:: console 

    $ armonik session create --max-duration 00:01:00.00 --priority 1  --max-retries 1 --endpoint 170.10.10.122:5001

All ArmoniK CLI without exception take the options: `endpoint`, `debug` and `output`. As such, they've been made global options. 
This allows you to write something like : 

.. code-block:: console 

    $ armonik session -e 170.10.10.122:5001 create --max-duration 00:01:00.00 --priority 1  --max-retries 1

The `output` option lets you control the desired format for your output. It's `json` by default but you can also choose `table` or `yaml` 
depending on your preference. While the `debug` flag lets you get a stacktrace of the execution on failure (it's omitted by default and replaced with a more concise error message).


Filters
-------

All of the list commands for the various ArmoniK objects (sessions, tasks, etc.) have a common filter option that allows you to, as the name suggests, query for entities that 
satisfy a specific condition. 

For instance, say we want to get all of the tasks associated with a specific session 

.. code-block:: console 

    $ armonik task list -e 170.10.10.122:5001 --filter "session_id='1085c427-89da-4104-aa32-bc6d3d84d2b2'" --output table   

or if we want to list all of the tasks within a specific session that have error'd out we can do 

.. code-block:: console 

    $ armonik task list -e 172.17.63.166:5001 --filter "session_id='1085c427-89da-4104-aa32-bc6d3d84d2b2' & status = error" --output table  

Filters are a very powerful tool when put to good use. Although we don't have a full list of all of the ArmoniK entities' attributes 
that you can filter with, you can go through the ArmoniK entities yourself and look through the attributes that are tagged
with FilterDescriptors. Those are generally safe to use. You can also find out more about the different operations that filters support 
by looking through the unit tests for filters. Hopefully this won't be the case when this section gets expanded in the future. 


Pages and Sorting
-----------------

Whenever you run a list command, the CLI automatically retrieves all of the entities. You can specify a specific page, as well as a page size 
by passing in the `--page` and `--page-size` arguments. 

Another thing you can do is sort your results in either ascending or descending order. You can pick the attribute to sort with using the `--sort-by` 
option, and the order using the `--sort-direction`. 

For instance, making use of all of these options we can get the first 100 tasks to have been created.

.. code-block:: console 

    $ armonik task list -e 172.17.63.166:5001 --filter "session_id='1085c427-89da-4104-aa32-bc6d3d84d2b2'" --sort-by "created_at" --output table --page 1  