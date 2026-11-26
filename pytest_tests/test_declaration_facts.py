"""J46 tests: declarations state nonemptiness, family membership constraints,
and plural finite/infinite properties as ordinary formulas.
"""

from functools import lru_cache
from pathlib import Path

import pytest

from .support import fl, mp, pl, pp, st, tl

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests" / "testSetTheory" / "declaration_facts.txt"


def c(name):
    return tl.ConstantTerm(name, name)


def v(name):
    return tl.VariableTerm(name)


def nonempty_formula(name, bound="u"):
    return fl.Exists(bound, st.membership_formula(v(bound), c(name)))


def family_formula(family, carrier, bound="S"):
    member = st.membership_formula(v(bound), c(family))
    return fl.ForAll(bound, fl.Implies(member, st.subset_formula(v(bound), c(carrier))))


def facts_of(text, line=0):
    entries, _ = pp.parse_proof_text(text)
    value = entries[line][1]
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def assert_facts(text, expected, line=0):
    actual = facts_of(text, line)
    assert len(actual) == len(expected)
    assert all(pl._ast_eq(left, right) for left, right in zip(actual, expected)), [
        repr(formula) for formula in actual
    ]


# --------------------------------------------------------------------
# Each declaration states exactly the fact named by its descriptor.
# --------------------------------------------------------------------

def test_a_nonempty_set_declaration_states_an_existential_membership():
    assert_facts(
        "1. Let A be a nonempty set. (Declaration)\n",
        [nonempty_formula("A")],
    )


def test_each_name_in_a_plural_nonempty_declaration_gets_its_own_existential():
    assert_facts(
        "1. Let A, B be nonempty sets. (Declaration)\n",
        [nonempty_formula("A"), nonempty_formula("B")],
    )


def test_a_family_of_subsets_declaration_states_the_subset_condition():
    text = (
        "1. Let A be any set, F be a family of subsets of A. (Declaration)\n"
    )
    assert_facts(text, [family_formula("F", "A")])


def test_each_family_in_a_plural_clause_gets_its_own_subset_condition():
    text = (
        "1. Let A be any set, F, G be families of subsets of A. (Declaration)\n"
    )
    assert_facts(text, [family_formula("F", "A"), family_formula("G", "A")])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "1. Let A be a finite set. (Declaration)\n",
            [fl.AtomicFormula("Finite", [c("A")])],
        ),
        (
            "1. Let A be an infinite set. (Declaration)\n",
            [fl.AtomicFormula("Infinite", [c("A")])],
        ),
        (
            "1. Let A be a finite set of cardinality 3. (Declaration)\n",
            [
                fl.AtomicFormula("Finite", [c("A")]),
                fl.AtomicFormula("Cardinality", [c("A"), tl.ConstantTerm("3", 3)]),
            ],
        ),
    ],
)
def test_singular_finite_and_infinite_declarations_are_unchanged(text, expected):
    assert_facts(text, expected)


def test_plural_finite_declaration_states_finiteness_for_each_name():
    expected = [
        fl.AtomicFormula("Finite", [c("A")]),
        fl.AtomicFormula("Finite", [c("B")]),
    ]
    assert_facts("1. Let A, B be finite sets. (Declaration)\n", expected)
    assert_facts("1. Let A and B be finite sets. (Declaration)\n", expected)


def test_plural_infinite_declaration_states_infiniteness_for_each_name():
    assert_facts(
        "1. Let A, B be infinite sets. (Declaration)\n",
        [
            fl.AtomicFormula("Infinite", [c("A")]),
            fl.AtomicFormula("Infinite", [c("B")]),
        ],
    )


def test_plural_cardinality_declaration_states_both_facts_for_each_name():
    expected = [
        fl.AtomicFormula("Finite", [c("A")]),
        fl.AtomicFormula("Cardinality", [c("A"), tl.ConstantTerm("3", 3)]),
        fl.AtomicFormula("Finite", [c("B")]),
        fl.AtomicFormula("Cardinality", [c("B"), tl.ConstantTerm("3", 3)]),
    ]
    assert_facts(
        "1. Let A, B be finite sets of cardinality 3. (Declaration)\n",
        expected,
    )


def test_a_new_recipe_does_not_change_an_unrelated_set_declaration():
    assert facts_of("1. Let A be any set. (Declaration)\n") == []


def test_new_facts_are_added_at_their_clause_position():
    text = (
        "1. Let A, B be sets, C be a nonempty set, "
        "D be a finite set. (Declaration)\n"
    )
    actual = facts_of(text)
    expected = [
        nonempty_formula("C"),
        fl.AtomicFormula("Finite", [c("D")]),
    ]
    assert len(actual) == len(expected)
    assert all(pl._ast_eq(left, right) for left, right in zip(actual, expected))


# --------------------------------------------------------------------
# The enforced proofs: a fact can be used, but not enlarged or reassigned.
# --------------------------------------------------------------------

@lru_cache(maxsize=None)
def _cases():
    return {str(case.number): case for case in mp.parse_multi_proof_file(
        FIXTURE.read_text(encoding="utf-8")
    )}


def _check_case(number):
    case = _cases()[number]
    assert case.parse_error is None, case.parse_error
    return pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    ).check_detailed()


def test_declaration_facts_fixture_has_grounded_conclusions_and_expected_results():
    source = FIXTURE.read_text(encoding="utf-8")
    cases = mp.parse_multi_proof_file(source)

    assert [case.number for case in cases] == [str(number) for number in range(1, 10)]
    assert all(case.stated_conclusion is not None for case in cases)
    assert all(case.parse_error is None for case in cases)

    results = mp.run_multi_proof_file(
        source,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert [result[0] for result in results] == [case.number for case in cases]
    assert all(result[1] == result[2] and not result[4] for result in results), [
        result for result in results if result[1] != result[2] or result[4]
    ]


@pytest.mark.parametrize("number", ["1", "2", "3", "4", "5"])
def test_each_positive_declaration_facts_proof_is_accepted(number):
    ok, error = _check_case(number)
    assert ok, error


@pytest.mark.parametrize("number", ["6", "7", "8", "9"])
def test_each_negative_declaration_facts_proof_is_refused(number):
    ok, error = _check_case(number)
    assert not ok, f"invalid case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == "2", error
    if number == "7":
        assert error.category == pl.CATEGORY_BAD_REFERENCE, error
    else:
        assert error.category == pl.CATEGORY_RULE_MISMATCH, error
        assert "does not justify" in error.detail, error


def test_nonempty_declaration_does_not_transfer_to_another_set():
    entries, _raw = pp.parse_proof_text(
        "1. Let A be a nonempty set, B be a set. (Declaration)\n"
        "2. exists u, In(u, B). (Reiteration from 1)\n"
    )
    ok, error = pl.Proof(entries).check_detailed()
    assert not ok
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH



def test_family_carrier_must_be_declared_before_the_family():
    with pytest.raises(pp.ElaborationError, match="has not been declared yet"):
        pp.parse_proof_text(
            "1. Let F be a family of subsets of A. (Declaration)\n"
        )
    with pytest.raises(pp.ElaborationError, match="has not been declared yet"):
        pp.parse_proof_text(
            "1. Let F be a family of subsets of A, A be any set. (Declaration)\n"
        )


def test_a_family_declared_after_its_carrier_can_use_that_carrier():
    assert_facts(
        "1. Let A be any set. (Declaration)\n"
        "2. Let F be a family of subsets of A. (Declaration)\n",
        [family_formula("F", "A")],
        line=1,
    )


def test_the_other_issue_171_descriptors_remain_unimplemented():
    typed_entries, _ = pp.parse_proof_text(
        "1. Let A, B be sets, f: A -> B be a unary function. (Declaration)\n"
    )
    typed_declarations = {d.name: d for d in typed_entries[0][2][1]}
    function = typed_declarations["f"]
    assert function.kind == pl.DeclarationKind.FUNCTION
    assert function.arity == 1
    assert dict(function.metadata)["domain"] == "A"
    assert dict(function.metadata)["codomain"] == "B"
    assert typed_entries[0][1] is None

    other_entries, _ = pp.parse_proof_text(
        "1. Let A be a set, P be a partition of A, F be a set of sets. (Declaration)\n"
    )
    assert other_entries[0][1] is None
    other_declarations = {d.name: d for d in other_entries[0][2][1]}
    for name in ("P", "F"):
        declaration = other_declarations[name]
        assert declaration.kind == pl.DeclarationKind.OBJECT
        assert not declaration.metadata
