"""Support for line-broken coordinated declaration clauses.

This module extends the core parser's line preparation and declaration-clause
splitters. A sentinel marks a physical line break that should separate
declaration clauses, without letting commas inside a descriptor (for example,
"reflexive, symmetric, transitive relation") be mistaken for clause separators.
"""

from __future__ import annotations

import re
from typing import Any, Callable

DECLARATION_LINE_BREAK = "\x00SYLOPY_DECLARATION_LINE_BREAK\x00"


def _is_declaration_logical_line(logical: Any) -> bool:
    """Return whether a logical line begins with a labeled Let declaration."""
    match = re.match(
        r"^\s*(?:[0-9]+(?:\.[A-Za-z0-9_]+)*)\.\s*(.*)$",
        logical.text.strip(),
    )
    return bool(
        match
        and re.match(r"^let\b", match.group(1).strip(), re.IGNORECASE)
    )


def _patched_prepare_surface_lines(legacy: Any) -> Callable[[str], tuple[list[Any], list[str]]]:
    """Build a line-preparation function that preserves declaration breaks."""

    def comment_preserving_newlines(match: re.Match[str]) -> str:
        """Blank out a comment while keeping the source's line structure."""
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    def prepare(text: str) -> tuple[list[Any], list[str]]:
        cleaned = re.sub(
            r"\(\*.*?\*\)",
            comment_preserving_newlines,
            text,
            flags=re.DOTALL,
        )
        raw_lines: list[str] = []
        physical_lines: list[tuple[int, str]] = []

        for line_number, line in enumerate(cleaned.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            raw_lines.append(line)
            if legacy._is_theory_directive(stripped):
                continue
            physical_lines.append((line_number, line))

        logical_lines: list[Any] = []
        for line_number, line in physical_lines:
            stripped = line.strip()
            starts_item = (
                legacy._LABELED_LINE_RE.match(stripped)
                or legacy._BEGIN_SUBPROOF_RE.match(stripped)
                or legacy._END_SUBPROOF_RE.match(stripped)
            )
            if starts_item or not logical_lines:
                logical_lines.append(
                    legacy._LogicalSourceLine(
                        line, line_number, line_number, line
                    )
                )
                continue

            previous = logical_lines[-1]
            previous_physical_line = previous.original_text.splitlines()[-1].strip()
            is_declaration_break = (
                _is_declaration_logical_line(previous)
                and previous_physical_line.endswith(",")
            )
            separator = (
                f" {DECLARATION_LINE_BREAK} "
                if is_declaration_break
                else " "
            )
            logical_lines[-1] = legacy._LogicalSourceLine(
                previous.text + separator + stripped,
                previous.start_line,
                line_number,
                previous.original_text + "\n" + line,
            )

        return logical_lines, raw_lines

    return prepare


def _patch_splitter(legacy: Any, name: str) -> Callable[[str], list[str]]:
    """Wrap a declaration splitter so it honors marked physical line breaks."""
    original: Callable[[str], list[str]] = getattr(legacy, name)

    def split(text: str) -> list[str]:
        if DECLARATION_LINE_BREAK not in text:
            return original(text)

        result: list[str] = []
        for chunk in text.split(DECLARATION_LINE_BREAK):
            chunk = chunk.strip()
            if chunk.endswith(","):
                chunk = chunk[:-1].rstrip()
            if chunk.lower().startswith("and "):
                chunk = chunk[4:].lstrip()
            if chunk:
                result.extend(original(chunk))
        return result

    return split


def install(legacy: Any) -> None:
    """Install the line-break-aware implementations on the parser module."""
    legacy._prepare_surface_lines = _patched_prepare_surface_lines(legacy)
    legacy.split_declaration_clauses = _patch_splitter(
        legacy, "split_declaration_clauses"
    )
    legacy._split_compound_declaration_items = _patch_splitter(
        legacy, "_split_compound_declaration_items"
    )
