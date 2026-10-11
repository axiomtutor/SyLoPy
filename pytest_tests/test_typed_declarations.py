"""Regression tests for typed object declarations.

These declarations state ordinary predicate formulas. They do not enable the
separate refinement type checker proposed in TYPE_SYSTEM_DESIGN.md.
"""

import pytest

import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.ProofParser as pp


def _declaration_formula(text):
    entries, _ = pp.parse_proof_text(text)
    assert len(entries) == 1
    return entries[0][1], entries


def test_integer_declaration_states_int_predicate():
    formula, entries = _declaration_formula(
        "1. Let n be an integer. (Declaration)\n"
    )
    assert repr(formula) == "Int(n)"
    assert pl.Proof(entries).check()[0]


def test_natural_number_declaration_states_nat_predicate():
    formula, entries = _declaration_formula(
        "1. Let n be a natural number. (Declaration)\n"
    )
    assert repr(formula) == "Nat(n)"
    assert pl.Proof(entries).check()[0]


def test_plural_typed_declarations_state_predicate_for_each_object():
    for phrase, predicate in [
        ("Let a and b be integers.", "Int"),
        ("Let a and b be natural numbers.", "Nat"),
    ]:
        entries, _ = pp.parse_proof_text(f"1. {phrase} (Declaration)\n")
        assert len(entries) == 1
        assert [repr(formula) for formula in entries[0][1]] == [
            f"{predicate}(a)", f"{predicate}(b)"
        ]
        assert pl.Proof(entries).check()[0]


def test_typed_declaration_formula_can_be_cited_later():
    entries, _ = pp.parse_proof_text("""
1. Let n be an integer. (Declaration)
2. Int(n). (Reiteration from 1)
""")
    ok, err = pl.Proof(entries).check_detailed()
    assert ok, err


def test_typed_declaration_formula_is_citable_inside_its_subproof():
    entries, _ = pp.parse_proof_text("""
1. Let P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let n be an integer. (Declaration)
 2.3. Int(n). (Reiteration from 2.2)
 2.4. P. (Reiteration from 2.1)
end subproof
""")
    ok, err = pl.Proof(entries).check_detailed()
    assert ok, err


def test_typed_declaration_does_not_declare_its_constant_after_scope_closes():
    text = """
1. Let P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let n be an integer. (Declaration)
 2.3. Int(n). (Reiteration from 2.2)
 2.4. P. (Reiteration from 2.1)
end subproof
3. Int(n). (Premise)
"""
    entries, _ = pp.parse_proof_text(text)
    ok, err = pl.Proof(entries).check_detailed()

    assert not ok
    assert err is not None
    assert err.label == "3"
    assert err.category == pl.CATEGORY_UNDECLARED_SYMBOL
    assert "constant 'n' is used but has not been declared" in err.detail


def test_comma_grouped_and_tuple_target_typed_declarations_type_each_name():
    # Both syntactic groupings declare each named object individually; the
    # parenthesized form is a tuple-shaped declaration target, not one object.
    for phrase in (
        "Let a, b be integers.",
        "Let (a, b) be an integer.",
    ):
        entries, _ = pp.parse_proof_text(f"1. {phrase} (Declaration)\n")
        assert len(entries) == 1
        assert [repr(formula) for formula in entries[0][1]] == [
            "Int(a)", "Int(b)"
        ]
        ok, err = pl.Proof(entries).check_detailed()
        assert ok, err
