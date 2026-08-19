"""Support for line-broken coordinated declaration clauses.

A declaration may be written as one logical proof line while putting each
coordinated clause on its own physical line, for example::

    1. Let X be any set,
       R be a reflexive, antisymmetric, transitive relation on X,
       a, b be in X,
       R(a,b) and R(b,c). (Declaration)

The ordinary parser historically joined continuation lines before parsing,
which meant that commas had to be interpreted heuristically.  This module
retains the physical line boundary internally so a comma followed by a line
break is an explicit declaration-clause boundary.  The marker never appears
in source spans or raw source lines.
"""

from __future__ import annotations

from typing import List


DECLARATION_LINE_BREAK = "\x00SYLOPY_DECLARATION_LINE_BREAK\x00"


def _is_declaration_logical_line(logical) -> bool:
    """Return whether a logical line is a ``Let`` declaration line."""
    import re

    text = logical.text.strip()
    match = re.match(r"^\s*(?:[0-9]+(?:\.[A-Za-z0-9_]+)*)\.\s*(.*)$", text)
    if not match:
        return False
    remainder = match.group(1).strip()
    return bool(re.match(r"^let\b", remainder, re.IGNORECASE))


def _patched_prepare_surface_lines(legacy):
    """Return a version of the legacy physical-line preparer that records
    declaration continuation boundaries without changing source text.
    """
    import re

    def comment_preserving_newlines(match: re.Match) -> str:
        return "".join("\n" if ch == "\n" else " " for ch in match.group(0))

    def prepare(text: str):
        cleaned = re.sub(r"\(\*.*?\*\)", comment_preserving_newlines, text, flags=re.S)
        raw_lines: List[str] = []
        physical = []
        for line_number, line in enumerate(cleaned.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            raw_lines.append(line)
            if legacy._is_theory_directive(stripped):
                continue
            physical.append((line_number, line))

        logical = []
        for line_number, line in physical:
            stripped = line.strip()
            starts_item = (
                legacy._LABELED_LINE_RE.match(stripped)
                or legacy._BEGIN_SUBPROOF_RE.match(stripped)
                or legacy._END_SUBPROOF_RE.match(stripped)
            )
            if starts_item or not logical:
                logical.append(
                    legacy._LogicalSourceLine(line, line_number, line_number, line)
                )
                continue

            previous = logical[-1]
            previous_physical = previous.original_text.splitlines()[-1].strip()
            declaration_break = (
                _is_declaration_logical_line(previous)
                and previous_physical.endswith(",")
            )
            separator = (
                f" {DECLARATION_LINE_BREAK} "
                if declaration_break
                else " "
            )
            logical[-1] = legacy._LogicalSourceLine(
                previous.text + separator + stripped,
                previous.start_line,
                line_number,
                previous.original_text + "\n" + line,
            )
        return logical, raw_lines

    return prepare


def _patch_splitter(legacy, name: str):
    """Make a legacy declaration splitter treat the explicit marker as a
    hard clause boundary while retaining all of its existing heuristics for
    ordinary same-line syntax.
    """
    original = getattr(legacy, name)

    def split(s: str):
        if DECLARATION_LINE_BREAK not in s:
            return original(s)
        chunks = s.split(DECLARATION_LINE_BREAK)
        result = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk.endswith(","):
                chunk = chunk[:-1].rstrip()
            if chunk:
                result.extend(original(chunk))
        return result

    return split


def install(legacy) -> None:
    """Install line-break-aware declaration parsing into ``ProofParserLegacy``."""
    legacy._prepare_surface_lines = _patched_prepare_surface_lines(legacy)
    legacy.split_declaration_clauses = _patch_splitter(
        legacy, "split_declaration_clauses"
    )
    legacy._split_compound_declaration_items = _patch_splitter(
        legacy, "_split_compound_declaration_items"
    )
