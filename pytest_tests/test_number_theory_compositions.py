"""Run the number-theory closure/composition proof batch."""

from pathlib import Path

from .support import mp


def test_integer_closure_composition_proofs_all_pass():
    fixture_dir = Path(__file__).resolve().parents[1] / "tests" / "testNumberTheory"
    paths = sorted(fixture_dir.glob("integer_closure_*.txt"))
    assert len(paths) == 9
    failures = {}
    for path in paths:
        results = mp.run_multi_proof_file(path.read_text(encoding="utf-8"))
        assert len(results) == 1, f"{path.name}: expected exactly one proof, got {results}"
        number, expected, ok, message, crashed = results[0]
        if not expected or not ok or crashed:
            failures[path.name] = (number, expected, ok, message, crashed)
    assert not failures, failures
