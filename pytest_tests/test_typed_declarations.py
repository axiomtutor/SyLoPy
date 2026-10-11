"""Regression tests for typed object declarations.

These declarations state ordinary predicate formulas. They do not enable the
separate refinement type checker proposed in TYPE_SYSTEM_DESIGN.md.
"""

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.ProofParser as pp
import SyLoPy.source.TermLogic as tl


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
        assert len(entries) == 2
        assert [repr(entry[1]) for entry in entries] == [
            f"{predicate}(a)", f"{predicate}(b)"
        ]
        assert pl.Proof(entries).check()[0]
