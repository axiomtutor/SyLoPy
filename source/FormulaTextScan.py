"""Shared lexical scans for embedded formula phrases.

The one-argument phrase_spans(text) extension API is intentionally kept
unchanged. Built-in finders reuse this context-local scan without requiring
third-party finders to accept additional parameters.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import re
from typing import Iterator, Tuple


_TOP_LEVEL_THEN_RE = re.compile(r"\s+then\s+", re.I)


@dataclass(frozen=True)
class FormulaTextScan:
    """Bracket depth at each character and positions of top-level then."""

    bracket_depths: Tuple[int, ...]
    top_level_then_positions: Tuple[int, ...]


def _build_formula_text_scan(text: str) -> FormulaTextScan:
    """Build both shared indexes in one pass over the formula text."""
    depths = []
    depth = 0
    for character in text:
        depths.append(depth)
        if character in "({":
            depth += 1
        elif character in ")}":
            # Preserve the parser's established behavior for unmatched closers.
            depth = max(0, depth - 1)

    top_level_then_positions = tuple(
        match.start()
        for match in _TOP_LEVEL_THEN_RE.finditer(text)
        if depths[match.start()] == 0
    )
    return FormulaTextScan(tuple(depths), top_level_then_positions)


_ACTIVE_SCAN = ContextVar("sy_lopy_active_formula_text_scan", default=None)


@contextmanager
def share_formula_text_scan(text: str) -> Iterator[None]:
    """Share a lazily built scan among phrase finders for exactly this text."""
    state = [text, None]
    token = _ACTIVE_SCAN.set(state)
    try:
        yield
    finally:
        _ACTIVE_SCAN.reset(token)


def formula_text_scan(text: str) -> FormulaTextScan:
    """Return the active scan for this text, or build an independent scan."""
    state = _ACTIVE_SCAN.get()
    if state is not None and state[0] == text:
        if state[1] is None:
            state[1] = _build_formula_text_scan(text)
        return state[1]
    return _build_formula_text_scan(text)
