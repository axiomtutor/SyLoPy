"""Verify the J27 informational examples that exercise later Mutatis mutandis stages."""

from pathlib import Path

from .support import mp

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests" / "setTheoryProofs" / "mutatis_mutandis_terms_symbols_examples.txt"


def test_mutatis_mutandis_terms_symbols_examples_all_pass():
    results = mp.run_multi_proof_file(FIXTURE.read_text(encoding="utf-8"))
    outcomes = [(number, expected_valid, ok, crashed, message)
                for number, expected_valid, ok, message, crashed in results]
    assert outcomes == [
        (str(number), True, True, False, message)
        for number in range(1, 7)
        for message in [next(
            result[3] for result in results if result[0] == str(number)
        )]
    ], [
        (number, message)
        for number, expected_valid, ok, message, crashed in results
        if not expected_valid or not ok or crashed
    ]
