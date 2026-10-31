"""J31 red-team tests for the formula stated by relation declarations.

The enforced fixture covers scope, binder selection, exact formula matching,
carrier membership, unrelated terms, derived relation facts, and plain binary
predicates. These tests pin the refusals and exercise the cases that are clearer
as direct parser/kernel checks: shadowing, sibling-label isolation, simultaneous
Mutatis mutandis changes, and theorem promotion.
"""

from functools import lru_cache
from pathlib import Path
import importlib

import pytest

from .support import fl, mp, pl, pp, tl

dm = importlib.import_module("SyLoPy.source.DiscreteMath")

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests" / "testDiscreteMath" / "red_team_relation_subset.txt"

BAD_REFERENCE = pl.CATEGORY_BAD_REFERENCE
RULE_MISMATCH = pl.CATEGORY_RULE_MISMATCH

# case -> (first refusing line, error category, reason-specific detail)
REFUSALS = {
    "1": (
        "3",
        BAD_REFERENCE,
        "cites ['2.5'], which is not defined or not in scope",
    ),
    "4": (
        "2",
        RULE_MISMATCH,
        "UniversalInstantiation' does not justify (∀v. (x(a, v)",
    ),
    "6": (
        "2",
        RULE_MISMATCH,
        "UniversalInstantiation' does not justify (∀y. (R(a, y) → (In(y, X) ∧ In(a, X)))",
    ),
    "8": (
        "2",
        RULE_MISMATCH,
        "UniversalInstantiation' does not justify (∀y. (S(a, y) → (In(a, X) ∧ In(y, X)))",
    ),
    "10": (
        "2",
        RULE_MISMATCH,
        "UniversalInstantiation' does not justify (∀y. (R(a, y) → (In(a, Y) ∧ In(y, Y)))",
    ),
    "12": (
        "3",
        RULE_MISMATCH,
        "UniversalModusPonens' does not justify (In(c, X) ∧ In(b, X))",
    ),
    "15": (
        "2",
        RULE_MISMATCH,
        "UniversalInstantiation' does not justify",
    ),
}

TWINS = {
    "1": "2",
    "4": "5",
    "6": "7",
    "8": "9",
    "10": "11",
    "12": "13",
    "15": "16",
}
VALID_CASES = ["2", "3", "5", "7", "9", "11", "13", "14", "16"]


@lru_cache(maxsize=None)
def _cases():
    parsed = mp.parse_multi_proof_file(FIXTURE.read_text(encoding="utf-8"))
    return {str(case.number): case for case in parsed}


def _check_case(number):
    case = _cases()[number]
    assert case.parse_error is None, case.parse_error
    proof = pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    return proof.check_detailed()


@lru_cache(maxsize=None)
def _runner_results():
    results = mp.run_multi_proof_file(
        FIXTURE.read_text(encoding="utf-8"),
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert results
    return {
        str(number): (expected_valid, ok, message, crashed)
        for number, expected_valid, ok, message, crashed in results
    }


def _check_text(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def _validated_proof(text):
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries)
    ok, error = proof.check_detailed()
    assert ok, error
    return proof


@pytest.mark.parametrize("number", sorted(REFUSALS, key=int))
def test_each_invalid_case_is_refused_at_its_pinned_line_for_its_reason(number):
    line, category, detail = REFUSALS[number]
    ok, error = _check_case(number)
    assert not ok, f"case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == line, error
    assert error.category == category, error
    assert detail in error.detail, error


@pytest.mark.parametrize("number", VALID_CASES)
def test_each_valid_case_is_accepted(number):
    case = _cases()[number]
    expected_valid, ok, message, crashed = _runner_results()[number]
    assert case.expected_valid and expected_valid, number
    assert not crashed, (number, message)
    assert ok, (number, message)
    if case.stated_conclusion is not None:
        assert mp.conclusion_is_derived(case.entries, case.stated_conclusion), number


@pytest.mark.parametrize("number", sorted(TWINS, key=int))
def test_each_invalid_case_has_a_valid_twin(number):
    cases = _cases()
    twin = TWINS[number]
    assert not cases[number].expected_valid
    assert cases[twin].expected_valid
    expected_valid, ok, message, crashed = _runner_results()[twin]
    assert expected_valid, twin
    assert not crashed, (twin, message)
    assert ok, (twin, message)


def test_the_pins_twins_and_valid_list_cover_all_sixteen_cases():
    cases = _cases()
    assert set(cases) == {str(number) for number in range(1, 17)}
    assert {
        number for number, case in cases.items() if not case.expected_valid
    } == set(REFUSALS)
    assert [number for number, case in cases.items() if case.expected_valid] == VALID_CASES
    assert set(TWINS) == set(REFUSALS)


def test_the_runner_agrees_with_every_fixture_expectation_without_rule_crashes():
    cases = _cases()
    results = _runner_results()
    assert set(results) == set(cases)
    for number, case in cases.items():
        expected_valid, ok, message, crashed = results[number]
        assert not crashed, (number, message)
        assert ok == expected_valid, (number, message)


@pytest.mark.parametrize(
    ("relation", "carrier"),
    [
        ("x", "X"),
        ("y", "X"),
        ("u", "X"),
        ("v", "X"),
        ("R", "x"),
        ("R", "y"),
        ("R", "u"),
        ("R", "v"),
    ],
)
def test_relation_subset_binders_skip_relation_and_carrier_names(relation, carrier):
    formula = dm.relation_subset_formula(relation, carrier)
    expected = [
        name for name in ("x", "y", "u", "v", "s", "t")
        if name not in (relation, carrier)
    ][:2]
    assert (formula.var, formula.body.var) == tuple(expected)
    assert relation not in expected and carrier not in expected



def test_a_relation_declaration_itself_does_not_escape_its_subproof():
    text = """1. Let X be any set, a, b be objects. (Declaration)
2. a = a -> a = a. (Conditional Introduction from subproof below)
begin subproof
 2.1. a = a. (Assumption for Conditional Introduction)
 2.2. Let R be a relation on X, R(a,b). (Declaration)
 2.3. a = a. (Reiteration from 2.1)
end subproof
3. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 2.2)
"""
    ok, error = _check_text(text)
    assert not ok
    assert isinstance(error, pl.ValidationError), error
    assert error.label == "3", error
    assert error.category == pl.CATEGORY_UNDECLARED_SYMBOL, error
    assert "predicate/formula symbol 'R' is used but has not been declared" in error.detail

def _sibling_scopes_proof(second_sibling_citation):
    return f"""1. Let X be any set, Y be any set, a, b be objects. (Declaration)
2. a = a -> a = a. (Conditional Introduction from subproof below)
begin subproof
 2.1. a = a. (Assumption for Conditional Introduction)
 2.2. Let R be a relation on X, R(a,b). (Declaration)
 2.3. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 2.2)
 2.4. In(a,X) and In(b,X). (Universal Modus Ponens from 2.3, 2.2)
 2.5. a = a. (Reiteration from 2.1)
end subproof
3. b = b -> b = b. (Conditional Introduction from subproof below)
begin subproof
 3.1. b = b. (Assumption for Conditional Introduction)
 3.2. Let R be a relation on Y, R(a,b). (Declaration)
 3.3. forall y, (R(a,y) -> (In(a,Y) and In(y,Y))). (Universal Instantiation from {second_sibling_citation})
 3.4. In(a,Y) and In(b,Y). (Universal Modus Ponens from 3.3, 3.2)
 3.5. b = b. (Reiteration from 3.1)
end subproof
"""


def test_a_sibling_cannot_cite_the_relation_declaration_in_another_sibling():
    bad = _sibling_scopes_proof("2.2")
    ok, error = _check_text(bad)
    assert not ok
    assert isinstance(error, pl.ValidationError), error
    assert error.label == "3.3", error
    assert error.category == BAD_REFERENCE, error
    assert "cites ['2.2'], which is not defined or not in scope" in error.detail

    good = _sibling_scopes_proof("3.2")
    ok, error = _check_text(good)
    assert ok, error


def _nested_relation_declaration(inner_name):
    return f"""1. Let X be any set, Y be any set, a, b be objects. (Declaration)
2. a = a -> a = a. (Conditional Introduction from subproof below)
begin subproof
 2.1. a = a. (Assumption for Conditional Introduction)
 2.2. Let R be a relation on X. (Declaration)
 2.3. b = b -> b = b. (Conditional Introduction from subproof below)
 begin subproof
  2.3.1. b = b. (Assumption for Conditional Introduction)
  2.3.2. Let {inner_name} be a relation on Y, {inner_name}(a,b). (Declaration)
  2.3.3. forall y, ({inner_name}(a,y) -> (In(a,Y) and In(y,Y))). (Universal Instantiation from 2.3.2)
  2.3.4. In(a,Y) and In(b,Y). (Universal Modus Ponens from 2.3.3, 2.3.2)
  2.3.5. b = b. (Reiteration from 2.3.1)
 end subproof
 2.4. a = a. (Reiteration from 2.1)
end subproof
"""


def test_a_nested_relation_cannot_shadow_an_ancestor_but_a_different_name_can():
    with pytest.raises(pp.ElaborationError, match=r"symbol 'R' is already declared"):
        pp.parse_proof_text(_nested_relation_declaration("R"))

    entries, _ = pp.parse_proof_text(_nested_relation_declaration("S"))
    ok, error = pl.Proof(entries).check_detailed()
    assert ok, error


def test_a_carrier_must_be_declared_before_the_relation_clause():
    invalid = "1. Let R be a relation on X, X be any set. (Declaration)\n"
    with pytest.raises(pp.ElaborationError, match="has not been declared yet"):
        pp.parse_proof_text(invalid)

    valid = "1. Let X be any set, R be a relation on X. (Declaration)\n"
    entries, _ = pp.parse_proof_text(valid)
    stated = entries[0][1]
    formulas = stated if isinstance(stated, list) else [stated]
    assert [repr(formula) for formula in formulas] == [
        "(∀x. (∀y. (R(x, y) → (In(x, X) ∧ In(y, X)))))"
    ]


def test_mutatis_mutandis_can_replace_the_relation_and_its_carrier_together():
    text = """Use discrete math.

1. Let X be any set, Y be any set, R be a relation on X, S be a relation on Y, a, b be objects, R(a,b), S(a,b). (Declaration)
2. R(a,b) -> (In(a,X) and In(b,X)). (Conditional Introduction from subproof below)
begin subproof
 2.1. R(a,b). (Assumption for Conditional Introduction)
 2.2. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 1)
 2.3. In(a,X) and In(b,X). (Universal Modus Ponens from 2.2, 2.1)
end subproof
3. S(a,b) -> (In(a,Y) and In(b,Y)). (Mutatis mutandis, 2)
"""
    ok, error = _check_text(text)
    assert ok, error


@pytest.mark.parametrize("uses_relation_rule", [False, True])
def test_a_relation_declaration_blocks_promotion_with_or_without_using_a_relation_rule(
    uses_relation_rule,
):
    if uses_relation_rule:
        text = """1. Let X be any set, R be a reflexive relation on X, a be an object, R(a,a). (Declaration)
2. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 1)
3. In(a,X) and In(a,X). (Universal Modus Ponens from 2, 1)
4. In(a,X). (Conjunction Elimination from 3)
5. R(a,a). (Relation Reflexivity from 4)
"""
    else:
        text = """1. Let X be any set, R be a relation on X, a, b be objects, R(a,b). (Declaration)
2. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 1)
3. In(a,X) and In(b,X). (Universal Modus Ponens from 2, 1)
"""
    proof = _validated_proof(text)
    with pytest.raises(
        ValueError,
        match=r"declaration of 'R' records carrier X",
    ):
        pl.promote_theorem("Relation subset derivation", proof)


def test_an_explicit_subset_premise_promotes_for_a_binary_predicate_but_not_another_predicate():
    title = "Binary predicate subset theorem"
    source = """1. Let X be any set, P be a binary predicate, a, b be objects, P(a,b). (Declaration)
2. forall x, forall y, (P(x,y) -> (In(x,X) and In(y,X))). (Premise)
3. forall y, (P(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 2)
4. In(a,X) and In(b,X). (Universal Modus Ponens from 3, 1)
"""
    proof = _validated_proof(source)
    theorem = pl.promote_theorem(title, proof)

    # The promoted schema is usable for its own fixed predicate symbol.
    assert theorem.applies(list(theorem.premises), theorem.conclusion)

    # Promotion generalizes top-level object names, not predicate symbols.
    s_fact = fl.AtomicFormula("S", [tl.ConstantTerm("a", "a"), tl.ConstantTerm("b", "b")])
    s_subset = dm.relation_subset_formula("S", "X")
    assert not theorem.applies([s_fact, s_subset], theorem.conclusion)
