"""Utilities for safe console output across Windows code pages.

safe_print: drop or replace characters that can't be encoded in the active stdout
             encoding while preserving Arabic characters and ASCII.

Design goals:
- Keep dependency‑free (used early during startup scripts).
- Fail silent if printing still impossible.
- Allow optional prefix/suffix injection in future.
"""
from __future__ import annotations
import sys
from typing import Any

_ARABIC_RANGE = ('\u0600', '\u06FF')

def _filter_text(txt: str) -> str:
    lo, hi = _ARABIC_RANGE
    return ''.join(
        ch for ch in txt
        if (ord(ch) < 128) or ch.isalnum() or ch.isspace() or (lo <= ch <= hi)
    )

def safe_print(*args: Any, **kwargs: Any) -> None:  # pragma: no cover (I/O wrapper)
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        cleaned = []
        for a in args:
            try:
                s = str(a)
            except Exception:
                s = repr(a)
            cleaned.append(_filter_text(s))
        try:
            print(*cleaned, **kwargs)
        except Exception:
            # Complete silence if still failing (e.g. closed stdout)
            pass

__all__ = ["safe_print"]
