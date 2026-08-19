from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def test_line_broken_declaration_clauses_are_distinct():
    text = """
1. Let X be any set,
   R be a reflexive, antisymmetric, transitive relation on X,
   a, b be in X,
   R(a,b) and R(b,a). (Declaration)
2. a = b. (Relation Antisymmetry from 1, 1)
"""
    ok, err = check(text)
    assert ok, err

    entries, _ = pp.parse_proof_text(text)
    declarations = entries[0][2][1]
    by_name = {d.name: d for d in declarations}
    assert set(by_name) == {"X", "R", "a", "b"}
    assert by_name["R"].arity == 2
    assert set(dict(by_name["R"].metadata)["properties"]) == {
        "reflexive",
        "antisymmetric",
        "transitive",
    }


def test_line_break_prevents_descriptor_commas_from_being_clause_boundaries():
    entries, _ = pp.parse_proof_text(
        """
1. Let X be any set,
   R be a reflexive, symmetric, transitive relation on X. (Declaration)
"""
    )
    declarations = entries[0][2][1]
    relation = next(d for d in declarations if d.name == "R")
    assert set(dict(relation.metadata)["properties"]) == {
        "reflexive",
        "symmetric",
        "transitive",
    }


def test_same_line_declaration_syntax_remains_supported():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, R be a reflexive, symmetric relation on X, a be in X. (Declaration)\n"
    )
    declarations = entries[0][2][1]
    assert {d.name for d in declarations} == {"X", "R", "a"}
