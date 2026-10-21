"""Pin the first-order logic fallacies to the rule and side condition that reject them."""

from pathlib import Path

import pytest

import SyLoPy.source.validate_all_proofs as mp
from .support import pl

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "testProofs" / "first_order_classics.txt"

# The first five cases are the supplied, already-verified invalid twins.
# The later cases are the textbook fallacies added by J16. The line and
# rule pins ensure that parse errors or unrelated scope errors cannot pass.
_EXPECTED_REFUSALS = {
    "14": (
        "6.2", "ExistentialElimination",
        "'ExistentialElimination' does not justify (∃x. (P(x) ∧ Q(x))) from the cited line(s) ['4'] and attached subproofs",
        "the witness w occurs in P(w), which was visible before the subproof opened; the witness w occurs in a hypothesis in force, P(w), so what the subproof derived may depend on it",
    ),
    "15": (
        "3.2", "ExistentialElimination",
        "'ExistentialElimination' does not justify R(c, b) from the cited line(s) ['3.1'] and attached subproofs",
        "the witness b occurs in the conclusion",
    ),
    "16": (
        "6", "ModusPonens",
        "'ModusPonens' does not justify P(a) from the cited line(s) ['5', '4']", None,
    ),
    "17": (
        "3", "UniversalInstantiation",
        "'UniversalInstantiation' does not justify (∃y. ¬y = y) from the cited line(s) ['2']", None,
    ),
    "18": (
        "4", "ExistentialIntroduction",
        "'ExistentialIntroduction' does not justify (∃x. R(x, x)) from the cited line(s) ['3']", None,
    ),
    "34": (
        "2.1.5", "ModusPonens",
        "'ModusPonens' does not justify P(c) from the cited line(s) ['2.1.4', '2.1.3']", None,
    ),
    "35": (
        "3", "ModusTollens",
        "'ModusTollens' does not justify ¬Q(a) from the cited line(s) ['2', '1']", None,
    ),
    "36": (
        "2", "UniversalInstantiation",
        "'UniversalInstantiation' does not justify ((∀x. P(x)) ∨ (∀x. Q(x))) from the cited line(s) ['1']", None,
    ),
    "37": (
        "2", "UniversalInstantiation",
        "'UniversalInstantiation' does not justify (∀x. P(x)) from the cited line(s) ['1']", None,
    ),
}


def _case_error(number):
    cases = mp.parse_multi_proof_file(FIXTURE.read_text(encoding="utf-8"))
    case = next(case for case in cases if case.number == number)
    assert case.parse_error is None, case.parse_error
    proof = pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    ok, error = proof.check_detailed()
    assert not ok, f"invalid case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    return error


@pytest.mark.parametrize("number", sorted(_EXPECTED_REFUSALS, key=int))
def test_each_invalid_twin_is_refused_for_its_named_reason(number):
    line, rule, prefix, reason = _EXPECTED_REFUSALS[number]
    error = _case_error(number)
    assert error.label == line, error
    assert error.category == pl.CATEGORY_RULE_MISMATCH, error
    assert f"'{rule}' does not justify" in error.detail, error
    assert error.detail.startswith(prefix), error
    if reason is not None:
        assert reason in error.detail, error

def test_wrong_rule_citation_twins_have_valid_sibling_controls():
    text = FIXTURE.read_text(encoding="utf-8")
    results = mp.run_multi_proof_file(
        text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    by_number = {number: (expected, ok, message, crashed)
                 for number, expected, ok, message, crashed in results}
    cases = {case.number: case for case in mp.parse_multi_proof_file(text)}
    for control, invalid_twin in (("42", "36"), ("43", "37")):
        assert cases[control].stated_conclusion is not None, (
            f"valid control case {control} has no parsed stated conclusion"
        )
        assert cases[invalid_twin].stated_conclusion is not None, (
            f"invalid case {invalid_twin} has no parsed stated conclusion"
        )
        assert cases[control].expected_valid, (
            f"control case {control} must be declared valid"
        )
        assert not cases[invalid_twin].expected_valid, (
            f"case {invalid_twin} must remain declared invalid"
        )
        expected, ok, message, crashed = by_number[control]
        assert expected, f"control case {control} must be declared valid"
        assert not crashed, f"control case {control} crashed: {message}"
        assert ok, f"valid control case {control} was rejected: {message}"
