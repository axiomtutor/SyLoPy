"""Regression tests for the relation rules not covered by the original suite.

These tests exercise both successful applications and declaration-sensitive
rejections. They intentionally use only the public proof-text interface.
"""

from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def test_asymmetry_rule_accepts_declared_asymmetry():
    ok, err = check("""
1. Let X be any set, R be an asymmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. not R(b,a). (Relation Asymmetry from 1)
""")
    assert ok, err


def test_asymmetry_rule_rejects_relation_without_asymmetry_property():
    ok, _ = check("""
1. Let X be any set, R be a symmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. not R(b,a). (Relation Asymmetry from 1)
""")
    assert not ok


def test_totality_rule_accepts_both_disjunct_orders():
    for conclusion in ("R(a,b) or R(b,a)", "R(b,a) or R(a,b)"):
        ok, err = check(f"""
1. Let X be any set, R be a total relation on X, a, b be in X. (Declaration)
2. {conclusion}. (Relation Totality from 1, 1)
""")
        assert ok, (conclusion, err)


def test_totality_rule_rejects_relation_without_totality_property():
    ok, _ = check("""
1. Let X be any set, R be a transitive relation on X, a, b be in X. (Declaration)
2. R(a,b) or R(b,a). (Relation Totality from 1, 1)
""")
    assert not ok
