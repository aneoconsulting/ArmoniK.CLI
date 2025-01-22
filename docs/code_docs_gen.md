::: armonik_cli.cli

# Core

## Exceptions

::: armonik_cli.core.filters.SemanticError

::: armonik_cli.exceptions.ArmoniKCLIError

::: armonik_cli.exceptions.InternalError

::: armonik_cli.exceptions.InternalArmoniKError

::: armonik_cli.exceptions.NotFoundError


## Decorators 

The error handler decorator is supposed to serve as the object where all errors that happen during command execution are routed to. It helps make said errors more presentable.

::: armonik_cli.core.decorators.error_handler

Base command is a decorator that's used for all the commands in the ArmoniK CLI, it includes the error handler.

::: armonik_cli.core.decorators.base_command

## Options

We've created some custom options that simplify the task of writing certain commands. 

::: armonik_cli.core.options.MutuallyExclusiveOption


## Filters

The following classes are used for a custom Click parameter type that allows you to filter ArmoniK's objects based on specific conditions. 

::: armonik_cli.core.filters.FilterParser

::: armonik_cli.core.filters.FilterTransformer
