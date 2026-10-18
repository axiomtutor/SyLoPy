"""Run the number-theory closure/composition proof batch."""

from pathlib import Path

from .support import mp


def test_integer_closure_composition_proofs_all_pass():
    fixture = Path(__file__).resolve().parents[1] / "tests" / "testNumberTheory" / "integer_closure_compositions.txt"
    results = mp.run_multi_proof_file(fixture.read_text(encoding="utf-8"))
    actual = [(number, ok) for number, _expected, ok, _message, crashed in results]
    failures = [
        (number, message)
        for number, _expected, ok, message, crashed in results
        if not ok or crashed
    ]
    assert actual == [(str(n), True) for n in range(1, 8)], failures
    assert not any(crashed for _number, _expected, _ok, _message, crashed in results), failures
