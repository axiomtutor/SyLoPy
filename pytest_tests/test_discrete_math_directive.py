
import pytest

from .support import pp, pl


def test_discrete_math_directive_is_accepted_before_proofs():
    text = """
Use discrete math.

# 1
## Proof that
### a reflexive relation relates every member to itself
1. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
"""
    entries, _ = pp.parse_proof_text(text)
    ok, err = pl.Proof(entries).check_detailed()
    assert ok, err


def test_discrete_mathematics_alias_is_accepted():
    text = """
Use discrete mathematics.
1. Let X be any set, R be a symmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. R(b,a). (Relation Symmetry from 1)
"""
    entries, _ = pp.parse_proof_text(text)
    assert pl.Proof(entries).check()[0]


def test_unknown_use_directive_is_rejected():
    with pytest.raises(pp.ElaborationError, match="unknown theory directive"):
        pp.parse_proof_text("Use algebra.\n1. A. (Premise)\n")


def test_irreflexivity_requires_membership_in_declared_carrier():
    text = """
1. Let X be any set, Y be any set, R be an irreflexive relation on X, a be in Y. (Declaration)
2. not R(a,a). (Relation Irreflexivity from 1)
"""
    entries, _ = pp.parse_proof_text(text)
    ok, err = pl.Proof(entries).check_detailed()
    assert not ok


