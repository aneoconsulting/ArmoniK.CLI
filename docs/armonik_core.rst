ArmoniK.CLI Core
======================

This is arguable one of the main things you'll be interacting with when working on ArmoniK.CLI.

We'll give an overview of the various custom decorators, parameter types and objects that are provided. 


Serialization of ArmoniK types
------------------------------

When working with ArmoniK you'll be dealing with a lot of its objects/entity types (Task, Session, etc.). 
To assist with that, ArmoniK.CLI's core module provides a function :code:`serialize`. Said function converts 
not just ArmoniK objects but also general Python objects into a JSON-serializable structure. This allows you to, for example
pass in a list of Tasks to get a list of serialized tasks. There are however certain requirements/limitations that 
you must handle yourself. Dict keys must be strings or else the serialize function will fail with an :code:`ArmoniKCLIError`.

For more information about usage, we recommend you look at said function's documentation at :doc:`CLI Reference <./cli_reference>` or 
at the unit tests for the serializer. 