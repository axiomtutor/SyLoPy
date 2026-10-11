"""Regression tests for declaration-sensitive relation inference rules.

These tests exercise successful applications and rejection boundaries through
the public proof-text interface. Negative cases assert that the intended
inference line is rejected, so a parser or unrelated earlier failure cannot
satisfy the test.
"""

from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def assert_rejected_at_rule(text, label="2"):
    ok, err = check(text)
    assert not ok
    assert err is not None
    assert err.label == label, err


def test_asymmetry_rule_accepts_declared_asymmetry():
    ok, err = check("""
1. Let X be any set, R be an asymmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. not R(b,a). (Relation Asymmetry from 1)
""")
    assert ok, err


def test_asymmetry_rule_rejects_relation_without_asymmetry_property():
    assert_rejected_at_rule("""
1. Let X be any set, R be a symmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. not R(b,a). (Relation Asymmetry from 1)
""")


def test_totality_rule_accepts_both_disjunct_orders():
    for conclusion in ("R(a,b) or R(b,a)", "R(b,a) or R(a,b)"):
        ok, err = check(f"""
1. Let X be any set, R be a total relation on X, a, b be in X. (Declaration)
2. {conclusion}. (Relation Totality from 1, 1)
""")
        assert ok, (conclusion, err)


def test_totality_rule_rejects_relation_without_totality_property():
    assert_rejected_at_rule("""
1. Let X be any set, R be a transitive relation on X, a, b be in X. (Declaration)
2. R(a,b) or R(b,a). (Relation Totality from 1, 1)
""")


def test_symmetry_rejects_a_relation_without_the_symmetric_property():
    assert_rejected_at_rule("""
1. Let X be any set, R be a transitive relation on X, a, b be in X, and R(a,b). (Declaration)
2. R(b,a). (Relation Symmetry from 1)
""")


def test_symmetry_cannot_be_transferred_to_a_different_relation():
    assert_rejected_at_rule("""
1. Let X be any set, R be a symmetric relation on X, S be a relation on X, a, b be in X, and R(a,b). (Declaration)
2. S(b,a). (Relation Symmetry from 1)
""")


def test_antisymmetry_rejects_a_relation_without_the_property():
    assert_rejected_at_rule("""
1. Let X be any set, R be a symmetric relation on X, a, b be in X, and R(a,b) and R(b,a). (Declaration)
2. a = b. (Relation Antisymmetry from 1, 1)
""")


def test_antisymmetry_requires_the_two_relation_atoms_to_reverse_each_other():
    assert_rejected_at_rule("""
1. Let X be any set, R be an antisymmetric relation on X, a, b, c be in X, and R(a,b) and R(b,c). (Declaration)
2. a = c. (Relation Antisymmetry from 1, 1)
""")


def test_transitivity_rejects_a_chain_with_mismatched_middle_terms():
    assert_rejected_at_rule("""
1. Let X be any set, R be a transitive relation on X, a, b, c, d be in X, and R(a,b) and R(c,d). (Declaration)
2. R(a,d). (Relation Transitivity from 1, 1)
""")


def test_transitivity_cannot_be_transferred_to_a_different_relation():
    assert_rejected_at_rule("""
1. Let X be any set, R be a transitive relation on X, S be a relation on X, a, b, c be in X, and R(a,b) and S(b,c). (Declaration)
2. R(a,c). (Relation Transitivity from 1, 1)
""")

def test_irreflexivity_is_restricted_to_the_declared_carrier():
    ok, err = check("""
1. Let X be any set, R be an irreflexive relation on X, a be in X. (Declaration)
2. not R(a,a). (Relation Irreflexivity from 1)
""")
    assert ok, err

    assert_rejected_at_rule("""
1. Let X be any set, Y be any set, R be an irreflexive relation on X, a be in Y. (Declaration)
2. not R(a,a). (Relation Irreflexivity from 1)
""")

def test_reflexivity_requires_the_declared_reflexive_property():
    assert_rejected_at_rule("""
1. Let X be any set, R be a symmetric relation on X, a be in X. (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
""")


def test_irreflexivity_requires_the_declared_irreflexive_property():
    assert_rejected_at_rule("""
1. Let X be any set, R be a transitive relation on X, a be in X. (Declaration)
2. not R(a,a). (Relation Irreflexivity from 1)
""")


def test_antisymmetry_does_not_combine_different_relations():
    assert_rejected_at_rule("""
1. Let X be any set, R be an antisymmetric relation on X, S be an antisymmetric relation on X, a, b be in X, and R(a,b) and S(b,a). (Declaration)
2. a = b. (Relation Antisymmetry from 1, 1)
""")
