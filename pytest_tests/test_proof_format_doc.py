"""Keep the examples in docs/PROOF_FILE_FORMAT.md synchronized with the checker."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .support import mp, pl
from SyLoPy.source import ProofJustification as pj


_DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "PROOF_FILE_FORMAT.md"
_MARKER_RE = re.compile(r"<!--\s*proof-format-test:\s*([a-z-]+)\s*-->")
_PROOF_LINE_RE = re.compile(
    r"^\s*\d+(?:\.[A-Za-z0-9_]+)*\.\s+.*\.\s+\((?P<justification>[^()]*)\)\s*$"
)
_GENERIC_JUSTIFICATION_RE = re.compile(
    r"(?:some\s+)?rule\s+from\s+.+", re.IGNORECASE
)


def _document_fences():
    """Return Markdown code fences and their optional immediately preceding test marker."""
    lines = _DOC_PATH.read_text(encoding="utf-8").splitlines()
    fences = []
    index = 0

    while index < len(lines):
        if not lines[index].startswith("```"):
            index += 1
            continue

        opening = index
        closing = next(
            (j for j in range(opening + 1, len(lines)) if lines[j].startswith("```")),
            None,
        )
        assert closing is not None, f"{_DOC_PATH.name}:{opening + 1}: unclosed code fence"

        marker = None
        if opening:
            match = _MARKER_RE.fullmatch(lines[opening - 1].strip())
            if match:
                marker = match.group(1)

        fences.append({
            "opening_line": opening + 1,
            "language": lines[opening][3:].strip(),
            "body": "\n".join(lines[opening + 1:closing]),
            "marker": marker,
        })
        index = closing + 1

    # Markers must be known and immediately precede a code fence. This avoids
    # a typo silently turning off execution of a documented example.
    for index, line in enumerate(lines):
        if "proof-format-test:" not in line:
            continue
        match = _MARKER_RE.fullmatch(line.strip())
        assert match, f"{_DOC_PATH.name}:{index + 1}: malformed proof-format-test marker"
        assert match.group(1) == "valid-proof", (
            f"{_DOC_PATH.name}:{index + 1}: unknown marker {match.group(1)!r}"
        )
        assert index + 1 < len(lines) and lines[index + 1].startswith("```"), (
            f"{_DOC_PATH.name}:{index + 1}: marker must immediately precede a code fence"
        )

    return fences


def test_marked_complete_proof_examples_validate():
    fences = _document_fences()
    runnable = [fence for fence in fences if fence["marker"] == "valid-proof"]
    assert runnable, "mark complete proof examples with <!-- proof-format-test: valid-proof -->"

    for fence in runnable:
        results = mp.run_multi_proof_file(
            fence["body"],
            axioms=mp.BARE_PROOF_AXIOMS,
            rules=mp.BARE_PROOF_RULES,
            declarations=mp.BARE_PROOF_DECLARATIONS,
        )
        assert results, f"no proof cases parsed from documentation fence at line {fence['opening_line']}"
        for number, expected_valid, ok, message, rule_crashed in results:
            assert expected_valid, (
                f"documentation fence at line {fence['opening_line']} unexpectedly marks "
                f"proof #{number} invalid"
            )
            assert not rule_crashed, (
                f"documentation proof #{number} crashed a rule: {message}"
            )
            assert ok, (
                f"documentation proof #{number} at line {fence['opening_line']} failed: {message}"
            )


def test_justifications_in_non_runnable_fences_resolve():
    """Check concrete justification phrases in snippets that are not full proofs."""
    checked = []
    unresolved = []

    for fence in _document_fences():
        if fence["marker"] == "valid-proof":
            # The proof validator above checks every justification in this fence.
            continue

        for offset, line in enumerate(fence["body"].splitlines()):
            match = _PROOF_LINE_RE.match(line)
            if not match:
                continue

            justification = match.group("justification").strip()
            normalized = " ".join(justification.lower().split())
            # These are metasyntactic placeholders in templates, not actual rule names.
            if normalized == "rule" or normalized == "justification":
                continue
            if _GENERIC_JUSTIFICATION_RE.fullmatch(normalized):
                continue

            checked.append((fence["opening_line"] + offset + 1, justification))
            try:
                parsed = pj.parse_justification(justification)
            except Exception as exc:
                unresolved.append(
                    f"line {fence['opening_line'] + offset + 1}: "
                    f"{justification!r} did not parse ({type(exc).__name__}: {exc})"
                )
                continue

            if parsed and parsed[0] in {"rule", "rule_below", "rule_hybrid"}:
                rule = parsed[1]
                if isinstance(rule, pl.NamedRulePlaceholder):
                    unresolved.append(
                        f"line {fence['opening_line'] + offset + 1}: "
                        f"{justification!r} resolves only to unknown placeholder "
                        f"{getattr(rule, 'name', rule)!r}"
                    )

    assert len(checked) >= 10, (
        f"expected to check concrete justification examples, but found only {len(checked)}"
    )
    assert not unresolved, "Unresolved documentation justifications:\n" + "\n".join(unresolved)
