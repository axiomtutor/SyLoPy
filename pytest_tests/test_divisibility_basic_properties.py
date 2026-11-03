"""Run the basic divisibility identity proofs against the real checker."""

from pathlib import Path

from .support import mp


def test_basic_divisibility_identity_proofs_all_pass():
    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "testNumberTheory"
        / "divisibility_basic_properties.txt"
    )
    results = mp.run_multi_proof_file(fixture.read_text(encoding="utf-8"))

    assert [result[0] for result in results] == ["1", "2", "3", "4"]
    failures = {
        number: (expected, ok, message, crashed)
        for number, expected, ok, message, crashed in results
        if not expected or not ok or crashed
    }
    assert not failures, failures
