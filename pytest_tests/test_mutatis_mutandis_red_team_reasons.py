"""Red-team tests for Mutatis mutandis, stage 1."""

from pathlib import Path

import pytest

from .support import mp, pl

PROJECT = Path(__file__).resolve().parents[1]
RED_TEAM = PROJECT / "tests" / "testProofs" / "red_team_mutatis_mutandis.txt"

BAD_REFERENCE = pl.CATEGORY_BAD_REFERENCE
RULE_MISMATCH = pl.CATEGORY_RULE_MISMATCH

# case -> (line, category, distinctive part of the expected refusal)
# Cases 4, 17 and 20 were refused in stage 1 because the replacement itself was
# not allowed. Stages 2 and 3 allow it, so they are refused because the facts
# that the repeated argument cites about the new symbols or term are not stated.
REFUSALS = {
    "2": ("3", BAD_REFERENCE, "no visible line says b = a"),
    "4": ("3", BAD_REFERENCE, "no visible line says R(g(b), b)"),
    "6": ("3", RULE_MISMATCH, "only a term without variables can replace a name"),
    "8": ("4", RULE_MISMATCH, "a repeated argument may not add a hypothesis"),
    "10": ("5", BAD_REFERENCE, "no visible line says a = d"),
    "12": ("5", RULE_MISMATCH, "only names and symbols may change"),
    "17": ("3", BAD_REFERENCE, "no visible line says (∀x. (Q(x) → P(x)))"),
    "20": ("3", BAD_REFERENCE, "no visible line says R(f(b))"),
}

VALID = ["1", "3", "5", "7", "9", "11", "13", "14", "15", "16", "18", "19", "21", "22", "23"]
SIBLINGS = {
    "2": "1",
    "4": "21",
    "6": "5",
    "8": "7",
    "10": "9",
    "12": "11",
    "17": "23",
    "20": "22",
}


def _cases():
    cases = mp.parse_multi_proof_file(RED_TEAM.read_text(encoding="utf-8"))
    return {case.number: case for case in cases}


def _check(case):
    assert case.parse_error is None, case.parse_error
    proof = pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    return proof.check_detailed()


@pytest.mark.parametrize("number", sorted(REFUSALS, key=int))
def test_each_invalid_case_is_refused_for_its_named_reason(number):
    line, category, reason = REFUSALS[number]
    ok, error = _check(_cases()[number])
    assert not ok, f"invalid case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == line, error
    assert error.category == category, error
    assert reason in error.detail, error


def test_pins_cover_every_case_declared_invalid():
    cases = _cases()
    declared_invalid = {number for number, case in cases.items() if not case.expected_valid}
    assert declared_invalid == set(REFUSALS)


def test_valid_cases_are_accepted_and_derive_their_stated_conclusions():
    cases = _cases()
    for number in VALID:
        case = cases[number]
        ok, error = _check(case)
        assert ok, (number, error)
        assert case.stated_conclusion is not None
        assert mp.conclusion_is_derived(case.entries, case.stated_conclusion), number


@pytest.mark.parametrize("number,control", sorted(SIBLINGS.items(), key=lambda item: int(item[0])))
def test_each_invalid_case_has_a_valid_twin(number, control):
    cases = _cases()
    assert not cases[number].expected_valid
    assert cases[control].expected_valid
    ok, error = _check(cases[control])
    assert ok, (control, error)


def test_fixture_runner_agrees_with_the_case_expectations():
    results = mp.run_multi_proof_file(
        RED_TEAM.read_text(encoding="utf-8"),
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert results
    for number, expected_valid, ok, message, crashed in results:
        assert not crashed, (number, message)
        assert ok == expected_valid, (number, message)


@pytest.mark.xfail(strict=True, reason="issue #122")
def test_same_line_mutatis_range_is_rejected():
    """A range A to B must not have an empty argument when A == B."""
    ok, error = _check(_cases()["18"])
    assert not ok, error
