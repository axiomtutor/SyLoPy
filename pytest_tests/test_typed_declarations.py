"""Regression tests for typed object declarations.

These declarations state ordinary predicate formulas. They do not enable the
separate refinement type checker proposed in TYPE_SYSTEM_DESIGN.md.
"""

import pytest

import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.ProofParser as pp
from .support import numt


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



def test_number_theory_environment_owns_typed_declaration_recipes():
    # The number-theory environment must be self-contained. Callers using it
    # directly should not depend on default_theory_environment() to register
    # Int/Nat declaration behavior.
    for phrase, expected in [
        ("Let n be an integer.", "Int(n)"),
        ("Let n be a natural number.", "Nat(n)"),
    ]:
        entries, _ = pp.parse_proof_text(
            f"1. {phrase} (Declaration)\n",
            environment=numt.NUMBER_THEORY_ENVIRONMENT,
        )

        assert len(entries) == 1
        assert entries[0][2][0] == "premise"
        assert repr(entries[0][1]) == expected

        ok, err = pl.Proof(entries).check_detailed()
        assert ok, err

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


def test_promoted_theorem_preserves_typed_declaration_as_a_required_premise():
    source = """
1. Let n be an integer. (Declaration)
2. Int(n) -> Int(n). (Conditional Introduction from subproof below)
begin subproof
 2.1. Int(n). (Assumption)
 2.2. Int(n). (Reiteration from 1)
end subproof
"""
    entries, _ = pp.parse_proof_text(source)
    proof = pl.Proof(entries)
    ok, err = proof.check_detailed()
    assert ok, err

    theorem = pl.promote_theorem("Integer premise implication", proof)
    assert [repr(premise) for premise in theorem.premises] == ["Int(n)"]
    assert theorem.generalized_names == ["n"]
    assert repr(theorem.conclusion) == "(Int(n) → Int(n))"

    use_entries, _ = pp.parse_proof_text(
        "1. Let m be an integer. (Declaration)\n"
    )
    use_entries.append(
        (
            "2",
            pp.parse_formula("Int(m) -> Int(m)"),
            ("rule", theorem, ["1"]),
        )
    )
    use_ok, use_err = pl.Proof(
        use_entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert use_ok, use_err

    # The theorem's conclusion shape alone is insufficient: without an
    # Int(m) premise, it must not be usable merely because m is declared.
    bad_entries, _ = pp.parse_proof_text("""
1. Let m be any set. (Declaration)
2. Let P be a closed formula such that: P. (Premise)
""")
    bad_entries.append(
        (
            "3",
            pp.parse_formula("Int(m) -> Int(m)"),
            ("rule", theorem, ["2"]),
        )
    )
    bad_ok, bad_err = pl.Proof(
        bad_entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert not bad_ok
    assert bad_err is not None
    assert bad_err.label == "3"
    assert bad_err.category == pl.CATEGORY_RULE_MISMATCH
