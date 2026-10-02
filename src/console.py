"""Console output helpers.

Chinese Windows consoles default to GBK, where printing emoji or box-drawing
characters raises UnicodeEncodeError and kills the process. Correctness never
depends on such decoration, so this is a belt-and-braces net: any character the
active code page can't encode degrades to '?' instead of crashing.
"""

from __future__ import annotations

import sys


def enable_safe_output() -> None:
    """Make stdout/stderr never raise on un-encodable characters."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
