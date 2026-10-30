"""`Let R be a relation on X` states that R is a subset of X x X.

A relation on X is a subset of X x X (owner decision, 2026-10-29; issue #136),
and a declaration states the facts it is sugar for, as an ordinary formula, the
way `a be in X` states `In(a, X)`. Relations here are predicates, so "R is a
subset of X x X" is

    forall x, forall y, (R(x, y) -> (In(x, X) and In(y, X)))

(`DiscreteMath.relation_subset_formula`). A proof then gets `In(a, X)` from
`R(a, b)` with the ordinary rules, whatever set `a` was declared in. These tests
pin the formula, where a declaration states it (every form of the declaration),
what it does not do, and the proofs it makes (tests/testDiscreteMath/
relation_subset.txt, each refusal for the reason its title names).
"""

import importlib
from functools import lru_cache
from pathlib import Path

import pytest

from .support import fl, mp, pl, pp, tl

dm = importlib.import_module("SyLoPy.source.DiscreteMath")

PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / "tests" / "testDiscreteMath" / "relation_subset.txt"

R_ON_X = "(∀x. (∀y. (R(x, y) → (In(x, X) ∧ In(y, X)))))"
S_ON_X = "(∀x. (∀y. (S(x, y) → (In(x, X) ∧ In(y, X)))))"


def facts_of(text, line=0):
    """The formulas a declaration line states, as printed."""
    entries, _ = pp.parse_proof_text(text)
    value = entries[line][1]
    if value is None:
        return []
    return [repr(phi) for phi in (value if isinstance(value, list) else [value])]


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


# --------------------------------------------------------------------
# The formula.
# --------------------------------------------------------------------

def test_the_formula_says_that_whatever_the_relation_relates_is_in_the_carrier():
    x, y = tl.VariableTerm("x"), tl.VariableTerm("y")
    carrier = tl.ConstantTerm("X", "X")
    expected = fl.ForAll("x", fl.ForAll("y", fl.Implies(
        fl.AtomicFormula("R", [x, y]),
        fl.And(fl.AtomicFormula("In", [x, carrier]), fl.AtomicFormula("In", [y, carrier])),
    )))
    built = dm.relation_subset_formula("R", "X")
    assert pl._ast_eq(built, expected)
    assert repr(built) == R_ON_X


@pytest.mark.parametrize(
    ("relation", "carrier", "bound"),
    [
        ("R", "X", ("x", "y")),
        ("x", "X", ("y", "u")),
        ("R", "x", ("y", "u")),
        ("R", "y", ("x", "u")),
        ("y", "x", ("u", "v")),
        ("x", "y", ("u", "v")),
    ],
)
def test_the_bound_variables_are_never_called_what_the_relation_or_its_carrier_is(
    relation, carrier, bound
):
    formula = dm.relation_subset_formula(relation, carrier)
    assert (formula.var, formula.body.var) == bound
    assert relation not in bound and carrier not in bound


def test_the_formula_is_not_written_over_the_names_it_is_about():
    # The relation and its carrier are named in the formula as constants of
    # their own, never as the bound variables.
    formula = dm.relation_subset_formula("x", "y")
    consequent = formula.body.body.consequent
    assert [type(arg).__name__ for arg in consequent.conjuncts[0].args] == ["VariableTerm", "ConstantTerm"]
    assert consequent.conjuncts[0].args[1].name == "y"
    assert formula.body.body.antecedent.predicate == "x"


# --------------------------------------------------------------------
# Where a declaration states it.
# --------------------------------------------------------------------

def test_a_relation_declaration_states_the_formula():
    assert facts_of("1. Let X be any set, R be a relation on X. (Declaration)\n") == [R_ON_X]


@pytest.mark.parametrize(
    "descriptor",
    ["a reflexive relation", "a symmetric and transitive relation", "an equivalence relation",
     "a partial order", "a strict partial order", "a total order", "a poset"],
)
def test_every_kind_of_relation_states_the_same_formula(descriptor):
    assert facts_of(f"1. Let X be any set, R be {descriptor} on X. (Declaration)\n") == [R_ON_X]


def test_each_relation_of_a_declaration_states_its_own_formula_in_order():
    assert facts_of("1. Let X be any set, R and S be equivalence relations on X. (Declaration)\n") == [
        R_ON_X, S_ON_X]


def test_the_formula_comes_where_the_relation_is_declared_among_the_other_facts():
    text = "1. Let X be any set, a, b be in X, R be a relation on X, R(a,b). (Declaration)\n"
    assert facts_of(text) == ["In(a, X)", "In(b, X)", R_ON_X, "R(a, b)"]


def test_a_relation_declared_on_a_line_after_its_carrier_states_it_too():
    text = ("1. Let X be any set. (Declaration)\n"
            "2. Let R be a relation on X, a be in X. (Declaration)\n")
    assert facts_of(text, 0) == []
    assert facts_of(text, 1) == [R_ON_X, "In(a, X)"]


def test_a_relation_declared_after_a_premise_clause_of_its_line_states_it_too():
    # The premise clause ends the run of declaration clauses that `X` is in, so
    # the carrier was declared before the run `R` is in, not beside it.
    text = "1. Let X be any set, a be in X, and a = a, R be a relation on X. (Declaration)\n"
    assert facts_of(text) == ["In(a, X)", "a = a", R_ON_X]


def test_a_relation_declared_in_a_subproof_states_it_there():
    text = """
1. Let X be any set. (Declaration)
2. A -> A. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption)
 2.2. Let R be a relation on X, a, b be objects, R(a,b). (Declaration)
 2.3. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 2.2)
 2.4. In(a,X) and In(b,X). (Universal Modus Ponens from 2.3, 2.2)
 2.5. A. (Reiteration from 2.1)
end subproof
"""
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries, declarations=[pl.Declaration("A", pl.DeclarationKind.PREDICATE, arity=0)])
    ok, err = proof.check_detailed()
    assert ok, err


def test_a_carrier_that_is_not_declared_is_still_reported_when_the_relation_is_declared():
    with pytest.raises(pp.ElaborationError, match="has not been declared yet"):
        pp.parse_proof_text("1. Let R be a relation on X. (Declaration)\n")
    with pytest.raises(pp.ElaborationError, match="has not been declared yet"):
        pp.parse_proof_text("1. Let R be a relation on X, X be any set. (Declaration)\n")


@pytest.mark.parametrize(
    ("text", "facts"),
    [
        ("1. Let P be a binary predicate. (Declaration)\n", []),
        ("1. Let P be a unary predicate. (Declaration)\n", []),
        ("1. Let X be any set, a, b be objects. (Declaration)\n", []),
        ("1. Let X be any set, a, b be in X. (Declaration)\n", ["In(a, X)", "In(b, X)"]),
    ],
)
def test_a_declaration_that_is_not_a_relation_states_no_such_formula(text, facts):
    assert facts_of(text) == facts


@pytest.mark.parametrize(
    "text",
    [
        "1. Let X be any set, R be a reflexive and transitive relation on X. (Declaration)\n",
        "1. Let X be any set. (Declaration)\n2. Let R be a reflexive and transitive relation on X. (Declaration)\n",
    ],
)
def test_the_relation_still_carries_its_carrier_and_properties_for_the_rules(text):
    entries, _ = pp.parse_proof_text(text)
    (declaration,) = [d for entry in entries if isinstance(entry[2], tuple)
                      for d in entry[2][1] if d.name == "R"]
    assert declaration.kind == pl.DeclarationKind.PREDICATE
    assert declaration.arity == 2
    metadata = dict(declaration.metadata)
    assert metadata["carrier"] == "X"
    assert set(metadata["properties"]) == {"reflexive", "transitive"}


# --------------------------------------------------------------------
# The recipe reads the scope through the clause.
# --------------------------------------------------------------------

def clause(text="a relation on X", names=("R",), is_declared=None):
    return pp.DeclarationClause(list(names), is_tuple=False, descriptor=text, is_declared=is_declared)


def test_a_clause_has_no_scope_unless_it_is_given_one():
    assert clause().is_declared is None
    assert clause(is_declared=lambda name: True).is_declared("X") is True


def test_the_recipe_declines_a_relation_whose_carrier_is_declared_nowhere():
    recipe = dm.RELATION_DECLARATION_RECIPE
    assert recipe.try_match([clause()], 0) is None
    assert recipe.try_match([clause(is_declared=lambda name: name == "Y")], 0) is None


def test_the_recipe_takes_a_relation_whose_carrier_is_declared_in_scope():
    consumed, declarations, formulas, rules = dm.RELATION_DECLARATION_RECIPE.try_match(
        [clause(is_declared=lambda name: name == "X")], 0)
    assert consumed == 1 and rules == []
    assert [d.name for d in declarations] == ["R"]
    assert [repr(phi) for phi in formulas] == [R_ON_X]


def test_the_recipe_takes_a_relation_whose_carrier_an_earlier_clause_declares():
    earlier = pp.DeclarationClause(["X"], is_tuple=False, descriptor="any set")
    consumed, declarations, formulas, rules = dm.RELATION_DECLARATION_RECIPE.try_match(
        [earlier, clause()], 1)
    assert [d.name for d in declarations] == ["R"]
    assert [repr(phi) for phi in formulas] == [R_ON_X]


def test_the_recipe_states_a_formula_for_each_name_of_its_clause():
    _, declarations, formulas, _ = dm.RELATION_DECLARATION_RECIPE.try_match(
        [clause(names=("R", "S"), is_declared=lambda name: True)], 0)
    assert [d.name for d in declarations] == ["R", "S"]
    assert [repr(phi) for phi in formulas] == [R_ON_X, S_ON_X]


# --------------------------------------------------------------------
# What the formula makes provable.
# --------------------------------------------------------------------

@lru_cache(maxsize=None)
def _cases():
    parsed = mp.parse_multi_proof_file(FIXTURES.read_text(encoding="utf-8"))
    return {str(case.number): case for case in parsed}


def _check_case(number):
    case = _cases()[number]
    assert case.parse_error is None, case.parse_error
    return pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    ).check_detailed()


BAD_REFERENCE = pl.CATEGORY_BAD_REFERENCE
RULE_MISMATCH = pl.CATEGORY_RULE_MISMATCH

# case -> (line, category, what the refusal says)
REFUSALS = {
    "3": ("5", RULE_MISMATCH, "'RelationReflexivity' does not justify R(a, a) from the cited line(s) ['4']"),
    "4": ("2", RULE_MISMATCH, "'UniversalInstantiation' does not justify "
                              "(∀y. (R(a, y) → (In(a, Y) ∧ In(y, Y)))) from the cited line(s) ['1']"),
    "5": ("3", RULE_MISMATCH, "'UniversalModusPonens' does not justify (In(c, X) ∧ In(b, X)) "
                              "from the cited line(s) ['2', '1']"),
    "10": ("3", BAD_REFERENCE, "and no visible line says (∀x. (∀y. (S(x, y) → (In(x, X) ∧ In(y, X)))))"),
}
TWINS = {"3": "2", "4": "1", "5": "1", "10": "9"}
VALID = ["1", "2", "6", "7", "8", "9"]


@pytest.mark.parametrize("number", sorted(REFUSALS, key=int))
def test_each_invalid_case_is_refused_at_its_line_for_the_reason_its_title_names(number):
    line, category, detail = REFUSALS[number]
    ok, error = _check_case(number)
    assert not ok, f"case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == line, error
    assert error.category == category, error
    assert detail in error.detail, error


@pytest.mark.parametrize("number", VALID)
def test_each_valid_case_is_accepted(number):
    ok, error = _check_case(number)
    assert ok, error


@pytest.mark.parametrize("number", sorted(TWINS, key=int))
def test_each_invalid_case_has_a_valid_twin(number):
    assert not _cases()[number].expected_valid
    assert _cases()[TWINS[number]].expected_valid
    ok, error = _check_case(TWINS[number])
    assert ok, error


def test_the_pins_and_the_valid_list_cover_every_case_of_the_file():
    cases = _cases()
    assert {n for n, case in cases.items() if not case.expected_valid} == set(REFUSALS)
    assert [n for n, case in cases.items() if case.expected_valid] == VALID


def test_the_runner_agrees_with_every_expectation_of_the_file():
    results = mp.run_multi_proof_file(
        FIXTURES.read_text(encoding="utf-8"),
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert {str(number) for number, *_ in results} == set(_cases())
    for number, expected_valid, ok, message, crashed in results:
        assert not crashed, (number, message)
        assert ok == expected_valid, (number, message)


def test_a_binary_predicate_that_is_not_a_relation_on_a_set_puts_nothing_in_any_set():
    # The fact belongs to `relation on X` and to nothing else: a binary
    # predicate P relates what it relates, in whatever sets those are declared.
    ok, error = check(
        "1. Let X be any set, P be a binary predicate, a, b be objects, P(a,b). (Declaration)\n"
        "2. forall y, (P(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 1)\n")
    assert not ok
    assert error.label == "2" and error.category == RULE_MISMATCH, error
