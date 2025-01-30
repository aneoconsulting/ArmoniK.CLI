ArmoniK.CLI Core
======================

This is arguably one of the main components you'll interact with when working on ArmoniK.CLI.

We'll give an overview of the various custom decorators, parameter types, objects, and convenience functions that are provided.

Serialization of ArmoniK types
------------------------------

When working with ArmoniK you'll be dealing with many of its objects or entity types (Task, Session, etc.). 
To assist with that, ArmoniK.CLI's core module provides a function :code:`serialize`. This function converts 
not just ArmoniK objects but also general Python objects into a JSON-serializable structure. This allows you to, for example,
pass in a list of Tasks to get back a list of serialized tasks.

.. note::
   There are certain requirements/limitations you must handle yourself:
   
   * Dictionary keys must be strings or the :code:`serialize` function will raise :code:`ArmoniKCLIError`.
   * Complex or custom Python objects that do not reduce easily to JSON primitives (strings, numbers, booleans, lists, dictionaries) may require additional handling.

For more information about usage, we recommend you look at the :code:`serialize` function's documentation in the 
:doc:`CLI Reference <./cli_reference>` or review the unit tests for the serializer.

Cross-Platform Input Handling
-----------------------------

In addition to serialization tools, ArmoniK.CLI provides a small helper utility for reading single key presses 
in a cross-platform way. This is especially useful for interactive CLI scenarios, menu navigation, or prompting 
the user for a quick key press without requiring the Enter key. This is used for instance in the :mod:`watch` commands

The core function is called :code:`get_key`, implemented differently for Windows and non-Windows systems:

- **Windows**: Uses the :mod:`msvcrt` module to read a single character. Special sequences (like arrow keys) 
  are detected by reading two consecutive characters.
- **Non-Windows (Unix-like)**: Uses :mod:`termios`, :mod:`tty`, and :mod:`select` to read from stdin in a 
  non-blocking (or blocking) manner.

Usage
^^^^^

Here are a few examples of how to use :code:`get_key`:

.. code-block:: python

   # Example 1: Blocking call on any platform
   print("Press any key...")
   key = get_key(blocking=True)
   print(f"You pressed: {key}")

   # Example 2: Non-blocking call (Windows only example)
   # On non-Windows, you can still pass blocking=False, but remember to handle the timeouts.
   key = get_key(blocking=False, timeout=0.5)
   if key:
       print(f"You pressed: {key}")
   else:
       print("No key pressed within 0.5 seconds")

   # Example 3: Handling Ctrl+C gracefully
   try:
       key = get_key(blocking=True, catch=True)
       if key == "\x03":
           print("Detected Ctrl+C!")
   except KeyboardInterrupt:
       # If catch=False, a normal KeyboardInterrupt could occur
       print("KeyboardInterrupt raised!")

When a recognized special key (like an arrow key) is pressed, :code:`get_key` will return strings such as 
:code:`"UP"`, :code:`"DOWN"`, :code:`"LEFT"`, :code:`"RIGHT"`, or :code:`"ESCAPE"` in the case of an Escape press. 
Otherwise, it attempts to return the literal character pressed.

.. note::
   * Windows uses :mod:`msvcrt` to determine if a key was pressed (:code:`msvcrt.kbhit()`) and then reads 
     with :code:`msvcrt.getch()`.
   * On Unix-like systems, raw mode is used temporarily to capture the keys without requiring the Enter key. 
     The :mod:`select` call is used for optional timeouts.
   * This is meant as a simple utility, it exists because Rich's LiveDisplay doesn't work well with other libraries like (curses, pynput, etc.); 
     for more complex needs where Rich's LiveDisplay isn't present you may consider more specialized libraries.

----

That covers the core utilities around serialization and cross-platform input handling in ArmoniK.CLI. 
For additional usage examples, advanced patterns, or potential edge cases, refer to the unit tests or to the 
:doc:`CLI Reference <./cli_reference>`.
