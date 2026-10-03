"""Regression coverage for tests/setTheoryProofs/basic_theorems.txt, the
growing corpus of basic axiomatic-set-theory theorems (subset reflexivity
and transitivity, uniqueness of the empty set, and more to come). Each
proof in that file is independent (its own declarations, no citations of
the others), so this just confirms the whole file still validates and each
proof's stated "### then ..." conclusion is the thing actually derived.
"""

from pathlib import Path

from .support import mp


def _proof_text() -> str:
    project = Path(__file__).resolve().parents[1]
    return (project / "tests" / "setTheoryProofs" / "basic_theorems.txt").read_text()


def test_basic_theorems_fixture_all_pass():
    results = mp.run_multi_proof_file(_proof_text())
    assert [(number, ok) for number, _expected, ok, _msg, _crashed in results] == [
        ("1", True), ("2", True), ("3", True),
    ]


def test_basic_theorems_have_titles_matching_their_content():
    cases = mp.parse_multi_proof_file(_proof_text())
    assert [case.number for case in cases] == ["1", "2", "3"]
    # Each stated "### then ..." conclusion must itself parse as a formula
    # and be the thing the proof actually derives at the top level --
    # run_multi_proof_file's own check (exercised above) already enforces
    # this; here we just confirm none of the three silently fell back to
    # "unparseable, skip the cross-check" (see _stated_conclusion_from).
    for case in cases:
        assert case.stated_conclusion is not None, f"proof {case.number}'s 'then' line didn't parse"
