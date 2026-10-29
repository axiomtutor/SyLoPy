"""J26 red-team tests for Mutatis mutandis stages 2 and 3.

The fixture checks that the alignment is a uniform simultaneous substitution,
that formula structure and symbol arity remain fixed, and that all transformed
outside citations have visible counterparts. Invalid examples are pinned to
the first refusing line and a reason-specific fragment; each has a valid twin.
"""

from pathlib import Path
from functools import lru_cache

import pytest

from .support import mp, pl

PROJECT = Path(__file__).resolve().parents[1]
GENERIC = PROJECT / "tests" / "testProofs" / "red_team_mutatis_mutandis_terms_symbols.txt"
RELATIONS = PROJECT / "tests" / "testDiscreteMath" / "red_team_mutatis_mutandis_relations.txt"
SETS = PROJECT / "tests" / "testSetTheory" / "red_team_mutatis_mutandis_sets.txt"

BAD_REFERENCE = pl.CATEGORY_BAD_REFERENCE
RULE_MISMATCH = pl.CATEGORY_RULE_MISMATCH

# case -> (line, category, reason-specific part of the refusal)
REFUSALS = {
    "1": ("3", BAD_REFERENCE, "no visible line says R(f(a))"),
    "7": ("3", RULE_MISMATCH, "same number of arguments"),
    "9": ("5", RULE_MISMATCH, "P would have to be replaced by both P and Q"),
    "11": ("5", RULE_MISMATCH, "only names and symbols may change"),
    "13": ("3", RULE_MISMATCH, "only names and symbols may change"),
    "15": ("3", RULE_MISMATCH, "only names and symbols may change"),
    "17": ("3", RULE_MISMATCH, "same number of arguments"),
    "19": ("5", BAD_REFERENCE, "S(b)"),
    "25": ("5", RULE_MISMATCH, "f would have to be replaced by both g and h"),
    "32": ("3", RULE_MISMATCH, "only names and symbols may change"),
}

# Each refused case -> the valid control that repairs its named condition.
SIBLINGS = {
    "1": "2",
    "7": "8",
    "9": "10",
    "11": "12",
    "13": "14",
    "15": "16",
    "17": "18",
    "19": "20",
    "25": "26",
    "32": "33",
}

VALID_CASES = [
    "2", "3", "4", "5", "6", "8", "10", "12", "14", "16", "18",
    "20", "21", "22", "23", "24", "26", "27", "28", "29", "30", "31", "33", "34",
]


@lru_cache(maxsize=None)
def _cases(path=GENERIC):
    parsed = mp.parse_multi_proof_file(path.read_text(encoding="utf-8"))
    return {str(case.number): case for case in parsed}


def _check(case):
    assert case.parse_error is None, case.parse_error
    proof = pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    return proof.check_detailed()


@lru_cache(maxsize=None)
def _runner_results(path=GENERIC):
    results = mp.run_multi_proof_file(
        path.read_text(encoding="utf-8"),
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert results
    return {
        str(number): (expected_valid, ok, message, crashed)
        for number, expected_valid, ok, message, crashed in results
    }


@pytest.mark.parametrize("number", sorted(REFUSALS, key=int))
def test_each_invalid_case_is_refused_at_the_expected_line_for_its_reason(number):
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


def test_valid_case_list_covers_every_case_declared_valid():
    cases = _cases()
    declared_valid = [number for number, case in cases.items() if case.expected_valid]
    assert declared_valid == VALID_CASES


@pytest.mark.parametrize("number", VALID_CASES)
def test_each_valid_case_is_accepted_and_derives_its_stated_conclusion(number):
    cases = _cases()
    case = cases[number]
    expected_valid, ok, message, crashed = _runner_results()[number]
    assert expected_valid, number
    assert not crashed, (number, message)
    assert ok, (number, message)
    assert case.stated_conclusion is not None
    assert mp.conclusion_is_derived(case.entries, case.stated_conclusion), number


@pytest.mark.parametrize("number,control", sorted(SIBLINGS.items(), key=lambda item: int(item[0])))
def test_each_invalid_case_has_a_valid_twin(number, control):
    cases = _cases()
    assert not cases[number].expected_valid
    assert cases[control].expected_valid
    expected_valid, ok, message, crashed = _runner_results()[control]
    assert expected_valid, control
    assert not crashed, (control, message)
    assert ok, (control, message)


def test_runner_agrees_with_all_case_expectations_including_the_promoted_theorem():
    # The final case cites a theorem promoted from case 30, so use the multi-proof
    # runner rather than checking that case in isolation.
    cases = _cases()
    results = _runner_results()
    assert set(results) == set(cases)
    for number, case in cases.items():
        expected_valid, ok, message, crashed = results[number]
        assert not crashed, (number, message)
        assert ok == expected_valid, (number, message)


# Theory-specific J26 red-team cases: each invalid case has one valid twin.
RELATION_REFUSALS = {
    "1": ("4", RULE_MISMATCH, "RelationTransitivity"),
    "3": ("4", RULE_MISMATCH, "RelationReflexivity"),
}
RELATION_SIBLINGS = {"1": "2", "3": "4"}
RELATION_VALID = ["2", "4", "5"]

SET_REFUSALS = {
    "2": ("11", RULE_MISMATCH, "PairingAxiom"),
    "3": ("12", RULE_MISMATCH, "UnionAxiom"),
    "4": ("13", RULE_MISMATCH, "PowerSetAxiom"),
    "5": ("14", RULE_MISMATCH, "Separation"),
}
SET_SIBLINGS = {"2": "1", "3": "1", "4": "1", "5": "1"}
SET_VALID = ["1"]


@pytest.mark.parametrize(
    "path,number,pins",
    [
        (RELATIONS, number, RELATION_REFUSALS)
        for number in sorted(RELATION_REFUSALS, key=int)
    ] + [
        (SETS, number, SET_REFUSALS)
        for number in sorted(SET_REFUSALS, key=int)
    ],
)
def test_each_invalid_theory_specific_case_is_refused_at_its_line_for_its_reason(path, number, pins):
    line, category, reason = pins[number]
    ok, error = _check(_cases(path)[number])
    assert not ok, f"{path.name} case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == line, error
    assert error.category == category, error
    assert reason in error.detail, error


@pytest.mark.parametrize(
    "path,expected_invalid,expected_valid",
    [
        (RELATIONS, set(RELATION_REFUSALS), RELATION_VALID),
        (SETS, set(SET_REFUSALS), SET_VALID),
    ],
)
def test_theory_specific_pins_and_valid_lists_cover_every_case(path, expected_invalid, expected_valid):
    cases = _cases(path)
    assert {number for number, case in cases.items() if not case.expected_valid} == expected_invalid
    assert [number for number, case in cases.items() if case.expected_valid] == expected_valid


@pytest.mark.parametrize(
    "path,number",
    [(RELATIONS, number) for number in RELATION_VALID]
    + [(SETS, number) for number in SET_VALID],
)
def test_each_valid_theory_specific_case_is_accepted_and_derives_its_conclusion(path, number):
    case = _cases(path)[number]
    expected_valid, ok, message, crashed = _runner_results(path)[number]
    assert expected_valid, (path.name, number)
    assert not crashed, (path.name, number, message)
    assert ok, (path.name, number, message)
    assert case.stated_conclusion is not None
    assert mp.conclusion_is_derived(case.entries, case.stated_conclusion), (path.name, number)


@pytest.mark.xfail(
    strict=True,
    reason="Finding b: RelationAntisymmetry ignores the declared carrier; owner Claude must fix the kernel rule.",
)
def test_relation_antisymmetry_replay_respects_declared_carrier():
    ok, error = _check(_cases(RELATIONS)["5"])
    assert not ok, error
    assert isinstance(error, pl.ValidationError), error
    assert error.label == "3", error
    assert error.category == RULE_MISMATCH, error
    assert "RelationAntisymmetry" in error.detail, error


@pytest.mark.parametrize(
    "path,number,siblings",
    [
        (RELATIONS, number, RELATION_SIBLINGS)
        for number in sorted(RELATION_SIBLINGS, key=int)
    ] + [
        (SETS, number, SET_SIBLINGS)
        for number in sorted(SET_SIBLINGS, key=int)
    ],
)
def test_each_invalid_theory_specific_case_has_a_valid_twin(path, number, siblings):
    cases = _cases(path)
    control = siblings[number]
    assert not cases[number].expected_valid
    assert cases[control].expected_valid
    expected_valid, ok, message, crashed = _runner_results(path)[control]
    assert expected_valid, (path.name, control)
    assert not crashed, (path.name, control, message)
    assert ok, (path.name, control, message)
