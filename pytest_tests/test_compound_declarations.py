

from pathlib import Path

import pytest

from .support import pp, pl, fl, c


def test_compound_declaration_surface_ast_separates_declarations_and_premises():
    text = """
1. Let X be any set,
    R be a reflexive, antisymmetric, transitive relation on X,
    a, b, c be in X,
    and R(a,b) and R(b,c). (Declaration)
"""
    surface = pp.parse_surface_proof(text)
    line = surface.entries[0]
    statement = line.declaration_statement

    assert statement is not None
    assert [d.name for d in statement.clauses[0].declarations] == ["X"]
    relation = statement.clauses[1].declarations[0]
    assert relation.kind == pl.DeclarationKind.PREDICATE
    assert relation.attributes["carrier"] == "X"
    assert set(relation.attributes["properties"]) == {
        "reflexive", "antisymmetric", "transitive"
    }

    membership = statement.clauses[2]
    assert [d.name for d in membership.declarations] == ["a", "b", "c"]
    assert membership.membership_expression == "X"

    assert [clause.formula for clause in statement.clauses[3:]] == [
        "R(a,b)", "R(b,c)"
    ]


def test_compound_declaration_elaborates_to_existing_core_concepts():
    text = """
1. Let X be any set, R be a relation on X, a, b be in X, and R(a,b). (Declaration)
"""
    entries, _ = pp.parse_proof_text(text)
    assert len(entries) == 1
    label, formulas, justification = entries[0]
    assert label == "1"
    assert isinstance(formulas, list)
    assert [repr(phi) for phi in formulas] == [
        "In(a, X)", "In(b, X)", "R(a, b)"
    ]
    assert justification[0] == "premise"
    assert [d.name for d in justification[1]] == ["X", "R", "a", "b"]

    assert pl.Proof(entries).check()[0]


def test_grouped_object_declaration_does_not_split_at_name_commas():
    entries, _ = pp.parse_proof_text(
        "1. Let a, b, c be objects. (Declaration)\n"
    )
    declarations = entries[0][2][1]
    assert [(d.name, d.kind) for d in declarations] == [
        ("a", pl.DeclarationKind.OBJECT),
        ("b", pl.DeclarationKind.OBJECT),
        ("c", pl.DeclarationKind.OBJECT),
    ]


def test_membership_group_declares_each_object_and_adds_each_membership_premise():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, a, b, c be in X. (Declaration)\n"
    )
    assert [repr(phi) for phi in entries[0][1]] == [
        "In(a, X)", "In(b, X)", "In(c, X)"
    ]
    assert [d.name for d in entries[0][2][1]] == ["X", "a", "b", "c"]
    assert pl.Proof(entries).check()[0]


def test_compound_declaration_is_elaborated_left_to_right():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, R be a relation on X. (Declaration)\n"
    )
    assert entries[0][2][1][0].name == "X"
    assert entries[0][2][1][1].metadata[0] == ("carrier", "X")

    with pytest.raises(pp.ElaborationError, match="has not been declared yet"):
        pp.parse_proof_text(
            "1. Let R be a relation on X, X be any set. (Declaration)\n"
        )


def test_compound_declaration_can_chain_predicates_functions_and_objects():
    entries, _ = pp.parse_proof_text(
        "1. Let P be a unary predicate, f be a unary function, "
        "a be an object, and P(f(a)). (Declaration)\n"
    )
    declarations = entries[0][2][1]
    assert [(d.name, d.kind, d.arity) for d in declarations] == [
        ("P", pl.DeclarationKind.PREDICATE, 1),
        ("f", pl.DeclarationKind.FUNCTION, 1),
        ("a", pl.DeclarationKind.OBJECT, None),
    ]
    assert repr(entries[0][1]) == "P(f(a))"
    assert pl.Proof(entries).check()[0]


def test_compound_declaration_does_not_infer_undeclared_symbols_from_usage():
    entries, _ = pp.parse_proof_text("1. P(a). (Premise)\n")
    ok, err = pl.Proof(entries).check_detailed()
    assert not ok
    assert err.category == pl.CATEGORY_UNDECLARED_SYMBOL


def test_surface_parser_ignores_physical_line_breaks_inside_compound_declaration():
    one_line = (
        "1. Let X be any set, R be a relation on X, "
        "a, b be in X, and R(a,b). (Declaration)\n"
    )
    wrapped = (
        "1. Let X be any set, R be a relation on X,\n"
        "   a, b be in X, and R(a,b). (Declaration)\n"
    )
    one = pp.parse_surface_proof(one_line).entries[0].declaration_statement
    two = pp.parse_surface_proof(wrapped).entries[0].declaration_statement
    assert [(type(c).__name__, getattr(c, "membership_expression", None),
             [d.name for d in getattr(c, "declarations", [])],
             getattr(c, "formula", None))
            for c in one.clauses] == [
        (type(c).__name__, getattr(c, "membership_expression", None),
         [d.name for d in getattr(c, "declarations", [])],
         getattr(c, "formula", None))
        for c in two.clauses
    ]


def test_membership_declaration_accepts_are_in_wording():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, a, b be in X. (Declaration)\n"
    )
    assert [repr(phi) for phi in entries[0][1]] == ["In(a, X)", "In(b, X)"]
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, a, b are in X. (Declaration)\n"
    )
    assert [repr(phi) for phi in entries[0][1]] == ["In(a, X)", "In(b, X)"]

@pytest.mark.parametrize("text, expected", [
    (
        "1. Let X be any set, a be in X, and R(a,a), R(a,b). (Declaration)\n",
        ["In(a, X)", "R(a, a)", "R(a, b)"],
    ),
    (
        "1. Let X be any set, R be a relation on X, P(a), Q(b). (Declaration)\n",
        ["P(a)", "Q(b)"],
    ),
    (
        "1. Let X be any set, a, b be in X, P(a), Q(b). (Declaration)\n",
        ["In(a, X)", "In(b, X)", "P(a)", "Q(b)"],
    ),
])
def test_compound_declaration_supports_comma_coordinated_premises(text, expected):
    entries, _ = pp.parse_proof_text(text)
    assert [repr(phi) for phi in entries[0][1]] == expected
    assert pl.Proof(entries).check()[0]



