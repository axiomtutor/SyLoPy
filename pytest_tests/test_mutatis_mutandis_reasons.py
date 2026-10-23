"""Pin each refused use of Mutatis mutandis to its line, its category and its reason.

`tests/testProofs/mutatis_mutandis.txt` and
`tests/testSetTheory/mutatis_mutandis_sets.txt` give every refused use a valid
sibling that differs from it in the one point the refused case names. The pins
check the line the refusal is reported at, its category, and what it says, so
that a proof that fails for some other reason (a parse error, a scope error, a
rule that does not apply) cannot pass for the refusal it was written to show.
Every refusal is reported at the Mutatis mutandis line itself, whichever line of
the repeated argument it concerns.
"""

from pathlib import Path

import pytest

from .support import mp, pl

PROJECT = Path(__file__).resolve().parents[1]
GENERIC = PROJECT / "tests" / "testProofs" / "mutatis_mutandis.txt"
SETS = PROJECT / "tests" / "testSetTheory" / "mutatis_mutandis_sets.txt"

BAD_REFERENCE = pl.CATEGORY_BAD_REFERENCE
RULE_MISMATCH = pl.CATEGORY_RULE_MISMATCH
ARITY_MISMATCH = pl.CATEGORY_ARITY_MISMATCH

# case number -> (line, category, what the refusal says, a reason it must also give or None).
# With no reason the detail must be exactly what is written; with one, the
# detail must start with what is written and contain the reason.
GENERIC_REFUSALS = {
    "2": ("7", BAD_REFERENCE,
          "Mutatis mutandis cannot start from line 3: it says (P(a) → Q(a)), and no visible line says "
          "(P(b) → Q(b)), which is what it says with a by b", None),
    "3": ("7", BAD_REFERENCE,
          "Mutatis mutandis cannot repeat line 6 with a by b: line 6.3 cites line 4, which says "
          "(Q(a) → R(a)), and no visible line says (Q(b) → R(b))", None),
    "5": ("7", BAD_REFERENCE,
          "Mutatis mutandis cannot repeat line 6 with a by b and b by a: line 6 cites line 5, which says "
          "R(a, b), and no visible line says R(b, a)", None),
    "7": ("4", BAD_REFERENCE,
          "Mutatis mutandis cannot repeat line 3 with a by b: line 3 cites line 2, which says P(a), and "
          "no visible line says P(b)", None),
    "11": ("5", BAD_REFERENCE,
           "Mutatis mutandis cites ['4.2'], which is not defined or not in scope at this point in the proof",
           None),
    "12": ("4", RULE_MISMATCH,
           "Mutatis mutandis repeats an argument, and line 2 is not a line that a rule derived from other "
           "lines", None),
    "13": ("5", RULE_MISMATCH,
           "P(b) is not line 4, Q(a), with names replaced: only names may change, but Q(a) would have to "
           "become P(b)", None),
    "14": ("5", RULE_MISMATCH, "nothing to change: Q(a) says what line 4 says", None),
    "16": ("5", RULE_MISMATCH,
           "T(b, c) is not line 4, T(a, a), with names replaced: a would have to be replaced by both b "
           "and c", None),
    "17": ("5", ARITY_MISMATCH,
           "Mutatis mutandis cites the line whose argument it repeats, or a range 'A to B' that ends at "
           "it; it was given ['2', '4', '3']", None),
    "18": ("5", BAD_REFERENCE,
           "Mutatis mutandis cites ['9'], which is not defined or not in scope at this point in the proof",
           None),
    "20": ("6", RULE_MISMATCH,
           "Mutatis mutandis cannot repeat line 4 with a by w: 'ExistentialElimination' does not justify "
           "Q(w) from the cited line(s) ['1'] and attached subproofs",
           "the witness w occurs in the conclusion"),
    "22": ("4", BAD_REFERENCE,
           "Mutatis mutandis cannot start from line 2: it says (P(a) → Q(a)); (Q(a) → R(a)); "
           "(P(b) → Q(b)), and no visible line says (P(b) → Q(b)); (Q(b) → R(b)); (P(b) → Q(b)), which "
           "is what it says with a by b", None),
    "24": ("6", RULE_MISMATCH,
           "Mutatis mutandis cannot repeat line 4 with a by w: Line 4.2, in the repeated argument: "
           "'ExistentialElimination' does not justify Q(w) from the cited line(s) ['1'] and attached "
           "subproofs", "the witness w occurs in the conclusion"),
    "26": ("3", RULE_MISMATCH,
           "Mutatis mutandis cannot repeat the argument of line 2: line 2.2 is part of it, and it is a "
           "premise (so is a witness named with 'Existence from'); a repeated argument may not add a "
           "hypothesis", None),
    "27": ("8", BAD_REFERENCE,
           "Mutatis mutandis cites the range '7 to 3' backwards: line 7 comes after line 3", None),
    "28": ("3", RULE_MISMATCH,
           "Mutatis mutandis cannot repeat line 2: it is a WLOG step, which has no argument of its own to "
           "repeat (an argument that contains a WLOG step can be repeated)", None),
    "30": ("7", BAD_REFERENCE,
           "Mutatis mutandis cannot repeat line 6 with a by c: line 6 cites line 3, which says P(a), and "
           "no visible line says P(c)", None),
}

# refused case -> the valid case that differs from it in the point the refusal names
GENERIC_SIBLINGS = {
    "2": "1", "3": "1", "5": "4", "7": "6", "11": "10", "12": "6", "13": "6", "14": "6",
    "16": "15", "17": "6", "18": "6", "20": "19", "22": "21", "24": "23", "26": "25",
    "27": "1", "28": "29", "30": "29",
}

GENERIC_VALID = ["1", "4", "6", "8", "9", "10", "15", "19", "21", "23", "25", "29"]

SETS_REFUSALS = {
    "3": ("6", BAD_REFERENCE,
          "Mutatis mutandis cannot start from line 3: it says (∀u. (In(u, X) ↔ (u = a ∨ u = b))), and no "
          "visible line says (∀u. (In(u, Y) ↔ (u = a ∨ u = b))), which is what it says with X by Y and "
          "Y by X", None),
}
SETS_SIBLINGS = {"3": "2"}
SETS_VALID = ["1", "2"]


def _cases(path):
    cases = mp.parse_multi_proof_file(path.read_text(encoding="utf-8"))
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


def _assert_refused_as_pinned(path, number, pins):
    line, category, detail, reason = pins[number]
    ok, error = _check(_cases(path)[number])
    assert not ok, f"invalid case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == line, error
    assert error.category == category, error
    if reason is None:
        assert error.detail == detail, error
    else:
        assert error.detail.startswith(detail), error
        assert reason in error.detail, error


@pytest.mark.parametrize("number", sorted(GENERIC_REFUSALS, key=int))
def test_each_refused_generic_case_is_refused_at_its_line_for_its_reason(number):
    _assert_refused_as_pinned(GENERIC, number, GENERIC_REFUSALS)


@pytest.mark.parametrize("number", sorted(SETS_REFUSALS, key=int))
def test_each_refused_set_theory_case_is_refused_at_its_line_for_its_reason(number):
    _assert_refused_as_pinned(SETS, number, SETS_REFUSALS)


def test_the_pins_cover_every_case_the_fixtures_declare_invalid():
    for path, pins in ((GENERIC, GENERIC_REFUSALS), (SETS, SETS_REFUSALS)):
        declared_invalid = {number for number, case in _cases(path).items() if not case.expected_valid}
        assert declared_invalid == set(pins), path.name


def test_the_valid_lists_cover_every_case_the_fixtures_declare_valid():
    for path, valid in ((GENERIC, GENERIC_VALID), (SETS, SETS_VALID)):
        declared_valid = [number for number, case in _cases(path).items() if case.expected_valid]
        assert declared_valid == valid, path.name


@pytest.mark.parametrize("number", GENERIC_VALID)
def test_each_valid_generic_case_is_accepted_and_derives_its_stated_conclusion(number):
    case = _cases(GENERIC)[number]
    ok, error = _check(case)
    assert ok, error
    assert case.stated_conclusion is not None
    assert mp.conclusion_is_derived(case.entries, case.stated_conclusion)


@pytest.mark.parametrize("number", SETS_VALID)
def test_each_valid_set_theory_case_is_accepted_and_derives_its_stated_conclusion(number):
    case = _cases(SETS)[number]
    ok, error = _check(case)
    assert ok, error
    assert case.stated_conclusion is not None
    assert mp.conclusion_is_derived(case.entries, case.stated_conclusion)


@pytest.mark.parametrize("twin", sorted(GENERIC_SIBLINGS, key=int))
def test_each_refused_generic_case_has_a_valid_sibling(twin):
    cases = _cases(GENERIC)
    control = GENERIC_SIBLINGS[twin]
    assert not cases[twin].expected_valid, f"case {twin} must remain declared invalid"
    assert cases[control].expected_valid, f"sibling case {control} must be declared valid"
    ok, error = _check(cases[control])
    assert ok, f"sibling case {control} of case {twin} was refused: {error}"


@pytest.mark.parametrize("twin", sorted(SETS_SIBLINGS, key=int))
def test_each_refused_set_theory_case_has_a_valid_sibling(twin):
    cases = _cases(SETS)
    control = SETS_SIBLINGS[twin]
    assert not cases[twin].expected_valid
    assert cases[control].expected_valid
    ok, error = _check(cases[control])
    assert ok, error


def test_the_runner_agrees_with_the_pins_on_both_fixtures():
    for path in (GENERIC, SETS):
        results = mp.run_multi_proof_file(
            path.read_text(encoding="utf-8"),
            axioms=mp.BARE_PROOF_AXIOMS,
            rules=mp.BARE_PROOF_RULES,
            declarations=mp.BARE_PROOF_DECLARATIONS,
        )
        assert results
        for number, expected_valid, ok, message, crashed in results:
            assert not crashed, (path.name, number, message)
            assert ok == expected_valid, (path.name, number, message)


def test_the_unique_pairing_fixture_with_mutatis_mutandis_is_the_proof_the_zfc_file_states():
    """The enforced copy and the informational ZFC proof repeat the same inclusion."""
    zfc = (PROJECT / "tests" / "setTheoryProofs" / "zfc_remaining_axioms.txt").read_text(encoding="utf-8")
    assert " 5.3. Y subseteq X. (Mutatis mutandis, 5.1 to 5.2)" in zfc
    enforced = SETS.read_text(encoding="utf-8")
    assert " 5.3. Y subseteq X. (Mutatis mutandis, 5.1 to 5.2)" in enforced
