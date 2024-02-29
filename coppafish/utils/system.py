import os
import shutil
import psutil
import checksumdir
import numpy as np
from pathlib import PurePath
from typing import Tuple


def get_software_version() -> str:
    """
    Get coppafish's version tag written in _version.py

    Returns:
        str: software version.
    """
    with open(PurePath(os.path.dirname(os.path.realpath(__file__))).parent.joinpath("_version.py"), "r") as f:
        version_tag = f.read().split('"')[1]
    return version_tag


def get_software_hash() -> str:
    """
    Get a checksum hash from the coppafish directory (i.e. all the source code).

    Returns:
        str: hash.
    """
    # Exclude any python cache files (.pyc)
    result = checksumdir.dirhash(
        PurePath(os.path.dirname(os.path.realpath(__file__))).parent, excluded_extensions=["pyc"], ignore_hidden=True
    )
    return result


def get_available_memory() -> float:
    """
    Get system's available memory at the time of calling this function.

    Returns:
        float: available memory in GB.
    """
    return psutil.virtual_memory().available / 1e9


def get_core_count() -> int:
    """
    Get the number of threads available for multiprocessing tasks on the system.

    Returns:
        int: number of available threads.
    """
    n_threads = psutil.cpu_count(logical=True)
    if n_threads is None:
        n_threads = 1
    else:
        n_threads -= 2
    n_threads = np.clip(n_threads, 1, 999, dtype=int)

    return int(n_threads)


def current_terminal_size_xy(x_offset: int = 0, y_offset: int = 0) -> Tuple[int, int]:
    """
    Get the current terminal size in x and y direction, clamped at >= 1 in both directions. Falls back to a default of
    `(80, 20)` if cannot be found.

    Args:
        x_offset (int, optional): add this value to the terminal size in x. Default: 0.
        y_offset (int, optional): add this value to the terminal size in y. Default: 0.

    Returns:
        - (int): number of terminal columns.
        - (int): number of terminal rows.
    """
    terminal_size = tuple(shutil.get_terminal_size((80, 20)))
    return (
        int(np.clip(terminal_size[0] + x_offset, a_min=1, a_max=None)),
        int(np.clip(terminal_size[1] + y_offset, a_min=1, a_max=None)),
    )
