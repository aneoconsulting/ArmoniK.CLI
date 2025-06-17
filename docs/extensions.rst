Getting started with ArmoniK.CLI extensions
=============================================

Assuming you've already created a Python project, you'll be using rich-click (or click).

So add this package to your project. We recommend not using exact versions as that might conflict with the CLI's requirements,
this is especially troubling since they're installed in the same environment and you risk breaking the main CLI.

The most important step is exposing an entrypoint. In your ``pyproject.toml``, add the following line:

.. code-block:: toml 
    [project.entry-points."armonik.cli.extensions"]
    hello = "armonik_cli_ext_hello.cli:hello_group"

- The ``armonik.cli.extensions`` is the entrypoint that the CLI loads extensions from. 
- ``hello`` will be used as the name of the extension. So in this case, the user will type ``hello`` to access the ``hello_group`` command group.
- ``hello`` is followed by the CommandGroup exposed by the extension. Note that the extension can also expose commands instead.

