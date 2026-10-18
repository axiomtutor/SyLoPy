"""Regression tests for the set-operation foundation proof fixtures."""

from pathlib import Path

from .support import mp


def _fixture_text(filename: str) -> str:
    project = Path(__file__).resolve().parents[1]
    return (project / "tests" / "setTheoryProofs" / filename).read_text()


def _assert_fixture_passes(filename: str, expected_numbers: range) -> None:
    results = mp.run_multi_proof_file(_fixture_text(filename))
    expected = [(str(number), True) for number in expected_numbers]
    actual = [(number, ok) for number, _expected, ok, _message, _crashed in results]
    failures = [
        (number, message)
        for number, _expected, ok, message, crashed in results
        if not ok or crashed
    ]
    assert actual == expected, f"{filename} unexpected proof results: {failures}"


def test_set_operation_foundations_fixture_all_pass() -> None:
    _assert_fixture_passes("set_operation_foundations.txt", range(1, 6))


def test_set_operation_properties_fixture_all_pass() -> None:
    _assert_fixture_passes("set_operation_properties.txt", range(1, 6))
