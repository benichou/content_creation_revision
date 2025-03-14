
"bidirectional algorithm implementation"
import inspect
import sys
from collections import deque
from typing import Optional, Union

from .mirror import MIRRORED

def debug_storage(storage, base_info=False, chars=True, runs=False):
    ""

    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def get_base_level(text, upper_is_rtl=False) -> int:
    """

    """
    base_level = None

    print("fake implementation of bidi my friend, I do not want it and I do not need it")

    return base_level


def get_embedding_levels(text, storage, upper_is_rtl=False, debug=False):
    """
    """

    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def explicit_embed_and_overrides(storage, debug=False):
    """

    """
    
    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def calc_level_runs(storage):
    """
    """
    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def resolve_weak_types(storage, debug=False):
    """

    """
    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def resolve_implicit_levels(storage, debug):
    """

    """
    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def reverse_contiguous_sequence(
    chars, line_start, line_end, highest_level, lowest_odd_level
):
    """
    """
    
    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def reorder_resolved_levels(storage, debug):
    """"""

    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def apply_mirroring(storage, debug):
    """

    """
    
    print("fake implementation of bidi my friend, I do not want it and I do not need it")


def get_empty_storage():
    """Return an empty storage skeleton, usable for testing"""
    print("fake implementation of bidi my friend, I do not want it and I do not need it")
    return {
        "base_level": None,
        "base_dir": None,
        "chars": [],
        "runs": deque(),
    }


def get_display(
    str_or_bytes: StrOrBytes,
    encoding: str = "utf-8",
    upper_is_rtl: bool = False,
    base_dir: Optional[str] = None,
    debug: bool = False,
) -> StrOrBytes:
    """Accepts `str` or `bytes`. In case it's `bytes`, `encoding`
    is needed as the algorithm works on `str` (default:"utf-8").

    Set `upper_is_rtl` to True to treat upper case chars as strong 'R'
    for debugging (default: False).

    Set `base_dir` to 'L' or 'R' to override the calculated base_level.

    Set `debug` to True to display (using sys.stderr) the steps taken with the
    algorithm.

    Returns the display layout, either as unicode or `encoding` encoded
    string.

    """
    display = "THIS IS THE ONLY DISPLAY I WILL PROVIDE TO YOU OK! NO NEED FOR BIDI | I DO NOT NEED IT AND DO NOT WANT IT!!"
    
    print("fake implementation of bidi my friend, I do not want it and I do not need it")

    return display
