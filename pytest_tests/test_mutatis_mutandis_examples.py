"""Verify the informational Mutatis mutandis examples in CI."""

from pathlib import Path

from .support import mp

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests" / "setTheoryProofs" / "mutatis_mutandis_examples.txt"


def test_mutatis_mutandis_examples_all_pass():
    results = mp.run_multi_proof_file(FIXTURE.read_text(encoding="utf-8"))
    outcomes = [(number, ok) for number, _expected, ok, _message, _crashed in results]
    assert outcomes == [(str(number), True) for number in range(1, 7)], [
        (number, message) for number, _expected, ok, message, crashed in results
        if not ok or crashed
    ]
