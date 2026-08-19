

from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def test_relation_properties_are_attached_to_declarations():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, R be a reflexive, antisymmetric, transitive relation on X. (Declaration)\n"
    )
    decls = entries[0][2][1]
    relation = next(d for d in decls if d.name == "R")
    assert relation.kind == pl.DeclarationKind.PREDICATE
    assert relation.arity == 2
    assert dict(relation.metadata)["carrier"] == "X"
    assert set(dict(relation.metadata)["properties"]) == {"reflexive", "antisymmetric", "transitive"}


def test_relation_reflexivity_requires_membership_in_the_carrier():
    ok, err = check("""
1. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
""")
    assert ok, err

    ok, err = check("""
1. Let X be any set, Y be any set, R be a reflexive relation on X, a be in Y. (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
""")
    assert not ok


def test_relation_symmetry_and_transitivity_are_declaration_sensitive():
    ok, err = check("""
1. Let X be any set, R be a symmetric, transitive relation on X, a, b, c be in X, and R(a,b) and R(b,c). (Declaration)
2. R(b,a). (Relation Symmetry from 1)
3. R(a,c). (Relation Transitivity from 1, 1)
""")
    assert ok, err

    ok, err = check("""
1. Let X be any set, R be a transitive relation on X, S be a relation on X, a, b, c be in X, and S(a,b) and S(b,c). (Declaration)
2. S(a,c). (Relation Transitivity from 1, 1)
""")
    assert not ok


def test_antisymmetry_and_irreflexivity():
    ok, err = check("""
1. Let X be any set, R be an antisymmetric relation on X, a, b be in X, and R(a,b) and R(b,a). (Declaration)
2. a = b. (Relation Antisymmetry from 1, 1)
""")
    assert ok, err

    ok, err = check("""
1. Let X be any set, R be an irreflexive relation on X, a be in X. (Declaration)
2. not R(a,a). (Relation Irreflexivity from 1)
""")
    assert ok, err


def test_standard_relation_descriptors_expand_to_properties():
    for descriptor, expected in [
        ("equivalence relation", {"reflexive", "symmetric", "transitive"}),
        ("partial order", {"reflexive", "antisymmetric", "transitive"}),
        ("strict partial order", {"irreflexive", "transitive"}),
        ("total order", {"reflexive", "antisymmetric", "transitive", "total"}),
    ]:
        entries, _ = pp.parse_proof_text(
            f"1. Let X be any set, R be a {descriptor} on X. (Declaration)\n"
        )
        relation = next(d for d in entries[0][2][1] if d.name == "R")
        assert set(dict(relation.metadata)["properties"]) == expected



