
from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def test_relation_asymmetry_requires_the_asymmetry_property():
    ok, err = check("""
1. Let X be any set, R be an asymmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. not R(b,a). (Relation Asymmetry from 1)
""")
    assert ok, err

    ok, err = check("""
1. Let X be any set, R be a transitive relation on X, a, b be in X, and R(a,b). (Declaration)
2. not R(b,a). (Relation Asymmetry from 1)
""")
    assert not ok


def test_totality_applies_to_members_of_the_declared_carrier():
    ok, err = check("""
1. Let X be any set, R be a total relation on X, a, b be in X. (Declaration)
2. R(a,b) or R(b,a). (Relation Totality from 1, 1)
""")
    assert ok, err


def test_totality_does_not_apply_to_members_of_another_carrier():
    ok, err = check("""
1. Let X be any set, Y be any set, R be a total relation on X, a, b be in Y. (Declaration)
2. R(a,b) or R(b,a). (Relation Totality from 1, 1)
""")
    assert not ok


def test_totality_requires_the_total_property():
    ok, err = check("""
1. Let X be any set, R be a symmetric relation on X, a, b be in X. (Declaration)
2. R(a,b) or R(b,a). (Relation Totality from 1, 1)
""")
    assert not ok
