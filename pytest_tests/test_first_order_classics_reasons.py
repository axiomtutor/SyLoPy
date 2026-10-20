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
    "14": ("6.2", "ExistentialElimination", "the witness w occurs in a hypothesis in force"),
    "15": ("3.2", "ExistentialElimination", "the witness b occurs in the conclusion"),
    "16": ("6", "ModusPonens", "does not justify P(a)"),
    "17": ("3", "UniversalInstantiation", "does not justify"),
    "18": ("4", "ExistentialIntroduction", "does not justify"),
    "34": ("2.1.5", "ModusPonens", "does not justify P(c)"),
    "35": ("2", "ModusTollens", "does not justify"),
    "36": ("2", "UniversalInstantiation", "does not justify"),
    "37": ("2", "UniversalInstantiation", "does not justify"),
    "38": ("2", "UniversalInstantiation", "does not justify"),
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
    line, rule, detail = _EXPECTED_REFUSALS[number]
    error = _case_error(number)
    assert error.label == line, error
    assert error.category == pl.CATEGORY_RULE_MISMATCH, error
    assert f"'{rule}' does not justify" in error.detail, error
    assert detail in error.detail, error
