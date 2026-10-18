"""Check order/relation proofs and reject their invalid twins at the named inference."""

from pathlib import Path

from .support import mp


_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "testDiscreteMath"
_VALID = _FIXTURE_DIR / "order_relation_proofs.txt"
_INVALID = _FIXTURE_DIR / "invalid_order_relation_proofs.txt"


def _run(path: Path):
    return mp.run_multi_proof_file(path.read_text(encoding="utf-8"))


def test_order_and_relation_theorems_all_prove():
    results = _run(_VALID)
    assert [(number, ok) for number, _expected, ok, _message, crashed in results
            if not crashed] == [(str(n), True) for n in range(1, 11)]
    assert not [r for r in results if r[4]], results


def test_each_invalid_twin_fails_at_its_intended_rule():
    expected = {
        "1": ("6", "RelationAntisymmetry"),
        "2": ("6", "RelationAntisymmetry"),
        "3": ("3.3", "RelationSymmetry"),
        "4": ("5", "RelationTransitivity"),
        "5": ("4", "RelationAntisymmetry"),
        "6": ("4", "RelationAsymmetry"),
        "7": ("2", "RelationReflexivity"),
        "8": ("3", "RelationAsymmetry"),
        "9": ("3", "RelationIrreflexivity"),
        "10": ("7", "RelationTransitivity"),
    }
    results = _run(_INVALID)
    assert [number for number, *_rest in results] == [str(n) for n in range(1, 11)]
    for number, expected_valid, ok, message, crashed in results:
        label, rule = expected[number]
        assert not crashed, f"case {number} crashed: {message}"
        assert not expected_valid, f"case {number} was not marked invalid"
        assert not ok, f"case {number} was accepted"
        assert message, f"case {number} failed without a message"
        assert f"Line {label}" in message, f"case {number} failed at the wrong line: {message}"
        assert rule.lower() in message.lower(), f"case {number} did not name {rule}: {message}"
