"""Check the surface parser against the parser oracle, ``parse_oracle/*.txt``.

An oracle file is a list of blank-line-separated blocks::

    id: enum-eq-two-nested
    context: nested
    surface: if Y = {a, b} then a is in Y
    expect: (forall u, (In(u, Y) iff (u = a or u = b))) -> In(a, Y)
    why: Why this is the right reading.

``context: line`` means the phrase is a whole proof line; ``nested`` means it
sits inside a larger formula (so the generic connective grammar sees it too).
``expect`` is written in plain logic with no sugar, so it is read with the core
grammar and compared with the parsed surface up to the *names of bound
variables*: free names and the order of conjuncts and disjuncts must agree.
``expect: REJECT`` means the surface must be refused with an error.

The oracle was written from the intended readings, independently of the
implementation. When a case fails, either the parser is wrong or the oracle
misread the intent: read ``why`` and decide which, and fix that side.

Set ``SYLOPY_ORACLE_DIR`` to check a directory of oracle files other than
``<repo>/parse_oracle`` (for example a branch checked out elsewhere). With no
oracle files present, every case is skipped.
"""

import os
from pathlib import Path

import pytest

from .support import pl, pp

_REQUIRED_KEYS = ("id", "context", "surface", "expect")


def oracle_directory() -> Path:
    override = os.environ.get("SYLOPY_ORACLE_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "parse_oracle"


def load_cases(path: Path):
    """The cases of one oracle file, in order, as dicts of their fields."""
    cases, current = [], {}
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if not line.strip():
            if current:
                cases.append(current)
                current = {}
            continue
        if line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")  # only the first colon: surfaces contain colons
        current[key.strip()] = value.strip()
    if current:
        cases.append(current)
    for case in cases:
        missing = [key for key in _REQUIRED_KEYS if key not in case]
        assert not missing, f"{path.name}: case {case.get('id', case)!r} lacks {missing}"
        assert case["context"] in ("line", "nested"), f"{path.name}: {case['id']}: bad context {case['context']!r}"
    return cases


def all_cases():
    directory = oracle_directory()
    cases = []
    if directory.is_dir():
        for path in sorted(directory.glob("*.txt")):
            cases.extend(load_cases(path))
    return cases


CASES = all_cases()


def _line_parse(surface: str):
    """Parse as a whole proof line: theory line parsers first, then the grammar."""
    return pp._ElaborationContext(pp.default_theory_environment()).parse_core_formula(surface)


def _nested_parse(surface: str):
    return pp.parse_formula(surface)


def _parsers_for(case):
    # A line-context phrase is parsed as a line. A nested one must also work as
    # a line (every formula is a legal line) and through the plain grammar.
    return (_line_parse,) if case["context"] == "line" else (_nested_parse, _line_parse)


def test_oracle_ids_are_unique():
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_surface_parser_agrees_with_oracle(case):
    surface, expect = case["surface"], case["expect"]
    if expect == "REJECT":
        for parse in _parsers_for(case):
            with pytest.raises(Exception):
                parse(surface)
        return
    expected = pp.parse_formula(expect)
    for parse in _parsers_for(case):
        actual = parse(surface)
        assert pl._alpha_eq(actual, expected), (
            f"{case['id']} ({parse.__name__}): {surface!r}\n"
            f"  parsed  : {actual!r}\n"
            f"  expected: {expected!r}\n"
            f"  why     : {case.get('why', '')}"
        )
