import logging
from click import get_app_dir
from rich.logging import RichHandler
from rich.console import Console
from pathlib import Path


def get_logger(name: str, debug: bool = False, verbose: bool = False) -> logging.Logger:
    """
    A logger for ArmoniK CLI that logs to both console and file.

    - Logs warnings and above to stderr by default
    - When verbose=True, logs info and above to stdout
    - Always logs everything to a file in the app directory
    """
    log_file_path = Path(get_app_dir("armonik_cli")) / f"{name}.log"
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    verbose = verbose

    for handler in logger.handlers:
        logger.removeHandler(handler)

    # TODO: Colors (Colorama ?)
    console_formatter = logging.Formatter("%(message)s")
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler = RichHandler(console=Console(stderr=not verbose))
    console_handler.setFormatter(console_formatter)
    if debug:
        console_handler.setLevel(logging.DEBUG)
    elif verbose:
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    return logger
