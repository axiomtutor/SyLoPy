"""Pin the intended failures of the equivalence-class proofs."""

from pathlib import Path

import pytest

import SyLoPy.source.validate_all_proofs as mp
from .support import pl

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "testDiscreteMath" / "equivalence_classes.txt"


def _case(number):
    text = FIXTURE.read_text(encoding="utf-8")
    matches = [case for case in mp.parse_multi_proof_file(text) if case.number == number]
    assert len(matches) == 1, (number, [case.number for case in mp.parse_multi_proof_file(text)])
    return text, matches[0]


def test_all_equivalence_class_proofs_match_their_declared_validity():
    text = FIXTURE.read_text(encoding="utf-8")
    results = mp.run_multi_proof_file(
        text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert [number for number, *_ in results] == [str(n) for n in range(1, 10)]
    assert [ok for _number, expected, ok, _message, crashed in results
            if expected and not crashed] == [True] * 6
    for number, expected, ok, message, crashed in results:
        assert not crashed, f"case {number} raised in a rule: {message}"
        assert expected == ok, f"case {number}: {message}"


@pytest.mark.parametrize(
    "number,expected_line,expected_rule,detail",
    [
        ("7", "3", "RelationSymmetry", "does not justify"),
        ("8", "7.6", "RelationTransitivity", "does not justify"),
        ("9", "7.8", "SetProperty", "does not justify"),
    ],
)
def test_invalid_twins_are_rejected_by_the_target_rule(number, expected_line, expected_rule, detail):
    _text, case = _case(number)
    assert case.parse_error is None, case.parse_error
    proof = pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    ok, error = proof.check_detailed()
    assert not ok, f"invalid equivalence-class case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == expected_line, error
    assert error.category == pl.CATEGORY_RULE_MISMATCH, error
    assert f"'{expected_rule}' does not justify" in error.detail, error
    assert detail in error.detail, error
