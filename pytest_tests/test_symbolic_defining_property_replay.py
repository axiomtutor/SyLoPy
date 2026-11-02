from pathlib import Path

from .support import mp, pl


PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests" / "testSetTheory" / "symbolic_defining_property_replay.txt"


def test_symbolic_defining_property_replay_fixture_outcomes():
    results = mp.run_multi_proof_file(FIXTURE.read_text(encoding="utf-8"))
    assert [
        (number, expected_valid, ok, crashed)
        for number, expected_valid, ok, _message, crashed in results
    ] == [
        ("1", True, True, False),
        ("2", False, False, False),
        ("3", True, True, False),
        ("4", False, False, False),
    ]


def test_symbolic_defining_property_replay_fixture_refusals_are_exact():
    results = mp.run_multi_proof_file(FIXTURE.read_text(encoding="utf-8"))
    by_number = {number: (expected_valid, ok, message, crashed)
                 for number, expected_valid, ok, message, crashed in results}

    _expected_valid, ok, message, crashed = by_number["2"]
    assert not ok and not crashed
    assert "line 3.2" in message
    assert "may not add a hypothesis" in message

    _expected_valid, ok, message, crashed = by_number["4"]
    assert not ok and not crashed
    assert "Line 8.3" in message
    assert "no visible counterpart" in message
