"""Tests for the general `Set property` rule (`SetPropertyRule`), which uses
a set's membership-defining biconditional `forall u, (In(u, S) <-> P(u))`
together with an instance of one side to derive the matching instance of
the other, in all four positive/negated directions.

Focused rule tests (valid instance accepted, near miss rejected) come
first; the realistic proofs in tests/setTheoryProofs/pairing_theorems.txt
exercise the rule inside actual set-theoretic arguments.
"""

from pathlib import Path

import pytest

from .support import pl, fl, tl, mp, st, c, v


def _in(element, set_term):
    return st.membership_formula(element, set_term)


def _eq(left, right):
    return fl.Equals(left, right)


a, b, x, y, Y, Z = c("a"), c("b"), c("x"), c("y"), c("Y"), c("Z")


def _pair_characterization(set_term=Y, first=a, second=b):
    u = v("u")
    return fl.ForAll("u", fl.Iff(_in(u, set_term), fl.Or(_eq(u, first), _eq(u, second))))


RULE = st.SetPropertyRule()


# --------------------------------------------------------------------
# Accepted instances
# --------------------------------------------------------------------

def test_membership_yields_the_defining_property():
    char = _pair_characterization()
    assert RULE.applies([char, _in(x, Y)], fl.Or(_eq(x, a), _eq(x, b)))


def test_defining_property_yields_membership():
    char = _pair_characterization()
    assert RULE.applies([char, fl.Or(_eq(a, a), _eq(a, b))], _in(a, Y))


def test_nonmembership_yields_negated_property_and_back():
    char = _pair_characterization()
    prop = fl.Or(_eq(x, a), _eq(x, b))
    assert RULE.applies([char, fl.Not(_in(x, Y))], fl.Not(prop))
    assert RULE.applies([char, fl.Not(prop)], fl.Not(_in(x, Y)))


def test_citation_order_is_free():
    char = _pair_characterization()
    assert RULE.applies([_in(x, Y), char], fl.Or(_eq(x, a), _eq(x, b)))


def test_membership_atom_may_be_on_either_side_of_the_biconditional():
    u = v("u")
    flipped = fl.ForAll("u", fl.Iff(fl.Or(_eq(u, a), _eq(u, b)), _in(u, Y)))
    assert RULE.applies([flipped, _in(x, Y)], fl.Or(_eq(x, a), _eq(x, b)))


def test_works_for_a_union_style_property_with_a_nested_quantifier():
    u, w = v("u"), v("w")
    char = fl.ForAll("u", fl.Iff(_in(u, Y), fl.Exists("w", fl.And(_in(w, Z), _in(u, w)))))
    instance = fl.Exists("w", fl.And(_in(w, Z), _in(x, w)))
    assert RULE.applies([char, instance], _in(x, Y))
    assert RULE.applies([char, _in(x, Y)], instance)


def test_works_for_a_power_set_style_property():
    u = v("u")
    char = fl.ForAll("u", fl.Iff(_in(u, Y), st.subset_formula(u, Z)))
    assert RULE.applies([char, _in(x, Y)], st.subset_formula(x, Z))


# --------------------------------------------------------------------
# Near misses are rejected
# --------------------------------------------------------------------

def test_rejects_the_wrong_set():
    char = _pair_characterization()
    assert not RULE.applies([char, _in(x, Z)], fl.Or(_eq(x, a), _eq(x, b)))


def test_rejects_an_unrelated_property():
    char = _pair_characterization()
    assert not RULE.applies([char, _in(x, Y)], fl.Or(_eq(x, a), _eq(x, y)))
    assert not RULE.applies([char, _in(x, Y)], fl.Or(_eq(x, b), _eq(x, a)))


def test_rejects_an_instance_at_a_different_term_than_the_membership_atom():
    char = _pair_characterization()
    assert not RULE.applies([char, _in(x, Y)], fl.Or(_eq(y, a), _eq(y, b)))


def test_rejects_mismatched_negation():
    char = _pair_characterization()
    prop = fl.Or(_eq(x, a), _eq(x, b))
    assert not RULE.applies([char, fl.Not(_in(x, Y))], prop)
    assert not RULE.applies([char, _in(x, Y)], fl.Not(prop))
    assert not RULE.applies([char, fl.Not(prop)], _in(x, Y))


def test_rejects_property_that_is_itself_negated_when_negation_is_dropped():
    # P(u) = not Q(u): from not-Q(t) one gets In(t, S), never not In(t, S).
    u = v("u")
    Q = lambda t: fl.AtomicFormula("Q", [t])
    char = fl.ForAll("u", fl.Iff(_in(u, Y), fl.Not(Q(u))))
    assert RULE.applies([char, fl.Not(Q(x))], _in(x, Y))
    assert not RULE.applies([char, fl.Not(Q(x))], fl.Not(_in(x, Y)))


def test_rejects_a_characterization_that_is_not_a_membership_biconditional():
    u = v("u")
    one_way = fl.ForAll("u", fl.Implies(_in(u, Y), fl.Or(_eq(u, a), _eq(u, b))))
    assert not RULE.applies([one_way, _in(x, Y)], fl.Or(_eq(x, a), _eq(x, b)))

    not_membership = fl.ForAll("u", fl.Iff(fl.AtomicFormula("P", [u]), fl.AtomicFormula("Q", [u])))
    assert not RULE.applies([not_membership, fl.AtomicFormula("P", [x])], fl.AtomicFormula("Q", [x]))


def test_rejects_when_the_bound_variable_is_not_the_membership_element():
    u, w = v("u"), v("w")
    wrong_var = fl.ForAll("u", fl.Iff(_in(w, Y), fl.Or(_eq(u, a), _eq(u, b))))
    assert not RULE.applies([wrong_var, _in(x, Y)], fl.Or(_eq(x, a), _eq(x, b)))


def test_rejects_a_set_term_that_mentions_the_bound_variable():
    u = v("u")
    self_referential = fl.ForAll("u", fl.Iff(_in(u, u), fl.Or(_eq(u, a), _eq(u, b))))
    assert st.match_membership_characterization(self_referential) is None
    assert not RULE.applies([self_referential, _in(x, x)], fl.Or(_eq(x, a), _eq(x, b)))


def test_rejects_wrong_citation_count_and_non_formula_candidates():
    char = _pair_characterization()
    assert not RULE.applies([char], _in(x, Y))
    assert not RULE.applies([char, _in(x, Y), _in(x, Y)], fl.Or(_eq(x, a), _eq(x, b)))
    assert not RULE.applies([], _in(x, Y))


def test_property_not_mentioning_the_bound_variable_still_requires_exact_agreement():
    u = v("u")
    constant_prop = fl.AtomicFormula("R", [a])
    char = fl.ForAll("u", fl.Iff(_in(u, Y), constant_prop))
    assert RULE.applies([char, _in(x, Y)], constant_prop)
    assert not RULE.applies([char, _in(x, Y)], fl.AtomicFormula("R", [b]))


# --------------------------------------------------------------------
# Environment wiring and citation syntax
# --------------------------------------------------------------------

def test_set_property_rule_is_registered_alongside_the_empty_set_rule():
    names = {rule.name for rule in st.SET_THEORY_ENVIRONMENT.rules}
    assert {"EmptySetProperty", "SetProperty"} <= names


def test_bare_set_property_citation_is_still_the_empty_set_rule():
    kind, rule, refs = _justification("Set property")
    assert (kind, refs) == ("rule", [])
    assert rule.name == "EmptySetProperty"


@pytest.mark.parametrize("text", ["Set property from 2, 4", "Set property, 2, 4", "(Set property, 2, 4)"])
def test_set_property_citation_forms_resolve_to_the_general_rule(text):
    kind, rule, refs = _justification(text)
    assert kind == "rule"
    assert rule.name == "SetProperty"
    assert refs == ["2", "4"]


def _justification(text):
    import SyLoPy.source.ProofJustification as pj
    return pj.parse_justification(text.strip("()"))


# --------------------------------------------------------------------
# Realistic proofs
# --------------------------------------------------------------------

def _pairing_text() -> str:
    project = Path(__file__).resolve().parents[1]
    return (project / "tests" / "setTheoryProofs" / "pairing_theorems.txt").read_text()


def test_pairing_theorems_fixture_all_pass():
    results = mp.run_multi_proof_file(_pairing_text())
    assert [(number, ok) for number, _expected, ok, _msg, _crashed in results] == [
        ("1", True), ("2", True), ("3", True), ("4", True),
    ]


def test_a_wrong_instance_inside_a_real_proof_is_rejected():
    broken = _pairing_text().split("# 2:")[0].replace(
        "5. In(a, Y). (Set property from 2, 4)",
        "5. In(b, Y). (Set property from 2, 4)",
    )
    results = mp.run_multi_proof_file(broken)
    assert [(number, ok) for number, _expected, ok, _msg, _crashed in results] == [("1", False)]
