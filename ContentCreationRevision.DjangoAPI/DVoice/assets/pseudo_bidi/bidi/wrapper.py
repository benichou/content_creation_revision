"""Provides the fake wrpper for the Rust based implementation."""

from typing import Optional, Union

# from .bidi import get_base_level_inner, get_display_inner

StrOrBytes = Union[str, bytes]

def get_display(
    str_or_bytes: StrOrBytes,
    encoding: str = "utf-8",
    base_dir: Optional[str] = None,
    debug: bool = False,
) -> StrOrBytes:
    """
    """
    print("WE DO NOT INTEND TO USE BIDI AND ARE ACTUALLY CALLING A FAKE ALIAS OF BIDI | I REPEAT WE ARE NOT USING BIDI AND ARE NOT COVERED BY ITS GPL TERMS")
    if isinstance(str_or_bytes, bytes):
        text = str_or_bytes.decode(encoding)
        was_decoded = True
    else:
        text = str_or_bytes
        was_decoded = False

    display = "FAKE DISPLAY FOR DVOICE IMPLEMENTATION"

    if was_decoded:
        display = display.encode(encoding)

    return display


def get_base_level(text: str) -> int:
    """Returns the base unicode level of the 1st paragraph in `text`.

    Return value of 0 means LTR, while 1 means RTL.
    """
    return 0 # FOR FAKE IMPLEMENTATION OF BIDI
