"""Regression tests for direct named-witness Pairing citations."""
import pytest

from .support import fl, mp, pp, st, tl


PAIRING_PROOF = """1. Let a, b be any set. (Declaration)
2. There is a set Y = {a, b}. (Axiom of pairing)
3. a = a. (Reflexivity)
4. a = a or a = b. (Disjunction Introduction from 3)
5. In(a, Y). (Set property from 2, 4)
6. b = b. (Reflexivity)
7. b = a or b = b. (Disjunction Introduction from 6)
8. In(b, Y). (Set property from 2, 7)
"""


def test_direct_pairing_citation_names_the_witness_and_states_its_property():
    entries, _ = pp.parse_proof_text(PAIRING_PROOF)
    label, formula, justification = entries[1]

    assert label == "2"
    assert isinstance(formula, fl.ForAll)
    assert justification[0] == "rule"
    assert justification[1].name == "PairingAxiom"
    assert justification[2] == []
    assert [(d.name, d.kind) for d in justification[3]] == [
        ("Y", st.pl.DeclarationKind.OBJECT)
    ]

    match = st.match_membership_characterization(formula)
    assert match is not None
    _, set_term, property_formula = match
    assert set_term == tl.ConstantTerm("Y", "Y")
    assert property_formula == fl.Or(
        fl.Equals(tl.VariableTerm("u"), tl.ConstantTerm("a", "a")),
        fl.Equals(tl.VariableTerm("u"), tl.ConstantTerm("b", "b")),
    )


def test_direct_pairing_citation_checks_end_to_end():
    ok, error = pp.check_proof_text(PAIRING_PROOF)
    assert ok, error


def test_direct_pairing_rejects_a_third_generator():
    text = """1. Let a, b, c be any set. (Declaration)
2. There is a set Y = {a, b, c}. (Axiom of pairing)
"""
    with pytest.raises(st.ElaborationError, match="exactly two terms"):
        pp.parse_proof_text(text)


def test_direct_pairing_rejects_a_self_referential_generator():
    text = """1. Let a, b be any set. (Declaration)
2. There is a set Y = {Y, b}. (Axiom of pairing)
"""
    with pytest.raises(st.ElaborationError, match="exactly two terms"):
        pp.parse_proof_text(text)


def test_direct_pairing_rejects_a_reused_witness_name():
    text = """1. Let a, b, Y be any set. (Declaration)
2. There is a set Y = {a, b}. (Axiom of pairing)
"""
    with pytest.raises(pp.ElaborationError, match="already declared"):
        pp.parse_proof_text(text)


def test_direct_pairing_witness_respects_subproof_scope():
    inside = """1. Let a, b be any set. (Declaration)
2. If a = a then a = a. (Conditional Introduction from subproof below)
begin subproof
  2.1. a = a. (Assumption)
  2.2. There is a set Y = {a, b}. (Axiom of pairing)
  2.3. a = a. (Reiteration from 2.1)
end subproof
"""
    ok, error = pp.check_proof_text(inside)
    assert ok, error

    outside = inside + "3. Y = Y. (Reflexivity)\n"
    ok, error = pp.check_proof_text(outside)
    assert not ok
    assert "Y" in str(error)
