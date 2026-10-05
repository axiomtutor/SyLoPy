"""Tests for the set-theory surface syntax used by the ZFC axiom fixtures:
`{a, b}` enumeration sugar, "x is a or b", the `subseteq` token, and the
"a and b are sets" multi-subject declaration.

All four are sugar: each desugars to formulas the kernel already knows, so
these tests pin down the exact desugared shape and then run small proofs
end to end.
"""

import pytest

from .support import pl, fl, tl, pp, mp, st, c, v


def _parse(text, bound=()):
    return st.parse_set_formula(text, set(bound))


def same(left, right):
    """Structural formula/term equality, the way the kernel compares ASTs."""
    return pl._ast_eq(left, right)


def _equals(name_left, name_right):
    return fl.Equals(c(name_left), c(name_right))


# --------------------------------------------------------------------
# {a, b} enumeration
# --------------------------------------------------------------------

def test_set_equals_enumeration_means_exactly_these_members():
    expected = fl.ForAll("u", fl.Iff(
        st.membership_formula(v("u"), c("Y")),
        fl.Or(fl.Equals(v("u"), c("a")), fl.Equals(v("u"), c("b"))),
    ))
    assert same(_parse("Y = {a, b}"), expected)
    assert same(_parse("{a, b} = Y"), expected)


def test_single_and_triple_enumerations():
    single = _parse("Y = {a}")
    assert same(single.body.right, fl.Equals(v("u"), c("a")))
    triple = _parse("Y = {a, b, c}")
    assert len(triple.body.right.disjuncts) == 3


def test_enumeration_bound_variable_avoids_names_in_use():
    # `u` is already a name in the formula, so the generated variable
    # must not capture it.
    formula = _parse("u = {a, b}")
    assert formula.var != "u"


def test_membership_in_enumeration_is_a_disjunction_of_equalities():
    either = fl.Or(_equals("x", "a"), _equals("x", "b"))
    assert same(_parse("x is in {a, b}"), either)
    assert same(_parse("x is not in {a, b}"), fl.Not(either))


@pytest.mark.parametrize("text", ["{a, b}", "f({a, b}) = Y", "x is in {a, , b}", "x is in {}"])
def test_enumeration_is_not_accepted_as_a_free_standing_term(text):
    assert _parse(text) is None


# --------------------------------------------------------------------
# "x is a or b"
# --------------------------------------------------------------------

def test_x_is_a_or_b_is_a_disjunction_of_equalities():
    assert same(_parse("x is a or b"), fl.Or(_equals("x", "a"), _equals("x", "b")))
    assert same(
        _parse("x is a, b, or c"),
        fl.Or(_equals("x", "a"), _equals("x", "b"), _equals("x", "c")),
    )


def test_x_is_a_or_b_agrees_with_membership_in_the_enumeration():
    assert same(_parse("x is a or b"), _parse("x is in {a, b}"))


def test_x_is_ordinary_english_or_is_not_misread():
    # Only variable-like names count as alternatives.
    assert _parse("n is even or odd") is None
    assert _parse("x is a or the empty set") is None


# --------------------------------------------------------------------
# subseteq
# --------------------------------------------------------------------

def test_subseteq_means_the_same_as_is_a_subset_of():
    assert same(_parse("X subseteq Y"), _parse("X is a subset of Y"))
    assert same(_parse("X subseteq Y"), st.subset_formula(c("X"), c("Y")))


# --------------------------------------------------------------------
# "a and b are sets"
# --------------------------------------------------------------------

def test_a_and_b_are_sets_declares_both():
    entries, _ = pp.parse_proof_text("1. a and b are sets. (Declaration)\n")
    (_label, _formula, (tag, declarations)), = entries
    assert tag == "declare"
    assert [(d.name, d.kind, d.type_name) for d in declarations] == [
        ("a", "object", "sets"),
        ("b", "object", "sets"),
    ]


def test_comma_form_declares_the_same_names():
    entries, _ = pp.parse_proof_text("1. Let a, b be sets. (Declaration)\n")
    (_label, _formula, (tag, declarations)), = entries
    assert tag == "declare"
    assert [d.name for d in declarations] == ["a", "b"]


# --------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------

def _run(text):
    results = mp.run_multi_proof_file(
        text,
        axioms=st.SET_THEORY_ENVIRONMENT.axioms,
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules,
    )
    return [(number, ok) for number, _expected, ok, _msg, _crashed in results]


def test_proof_using_enumeration_membership_and_subseteq():
    text = """
# 1: Membership in a pair
## Proof that
### If x is in {a, b} then x = a or x = b.

1. a, b and x are sets. (Declaration)
2. x is in {a, b}. (Premise)
3. x = a or x = b. (Reiteration from 2)
"""
    assert _run(text) == [("1", True)]


def test_x_is_a_or_b_works_as_a_premise_and_as_a_derived_line():
    # As a premise the generic grammar used to split the line at its "or"
    # before the set-theory parser saw it ("Unrecognized formula syntax:
    # 'x is a'"); premises now go through the theory line parsers first.
    text = """
# 1: Alternatives as a premise
## Proof that
### If x is a or b then x = a or x = b.

1. a, b and x are sets. (Declaration)
2. x is a or b. (Premise)
3. x = a or x = b. (Reiteration from 2)
4. x is a or b. (Reiteration from 3)
"""
    assert _run(text) == [("1", True)]


def test_x_is_a_or_b_premise_is_not_the_wrong_disjunction():
    text = """
# 1: Wrong conclusion
## Invalid proof.
### Alternatives do not give a different pair.

1. a, b, c and x are sets. (Declaration)
2. x is a or b. (Premise)
3. x = a or x = c. (Reiteration from 2)
"""
    results = mp.run_multi_proof_file(
        text,
        axioms=st.SET_THEORY_ENVIRONMENT.axioms,
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules,
    )
    assert [ok for _n, _expected, ok, _msg, _crashed in results] == [False]


def test_subseteq_drives_a_subset_proof():
    text = """
# 1: Subset is reflexive, written with subseteq
## Proof that
### then X subseteq X.

1. Let X be any set. (Declaration)
2. X subseteq X. (Subset proof below)
 2.1. Let a in X. (Assumption for subset proof)
 2.2. a is in X. (Reiteration from 2.1)
"""
    assert _run(text) == [("1", True)]
