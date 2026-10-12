"""Adversarial audit of the proof-to-theorem promotion boundary.

These probes are deliberately test-only: Claude owns the kernel implementation.
The strict xfail records the one known promotion-policy gap and will force the
marker to be removed when the implementation is corrected.
"""

import pytest

from .support import pl, pp


def _checked_proof(text):
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries)
    ok, error = proof.check_detailed()
    assert ok, error
    return proof


def test_promotion_keeps_top_level_premises_but_not_nested_assumptions():
    proof = _checked_proof(
        """1. Let P be a closed formula. (Declaration)
2. P. (Premise)
3. P -> P. (Conditional Introduction from subproof below)
begin subproof
 3.1. P. (Assumption for Conditional Introduction)
 3.2. P. (Reiteration from 3.1)
end subproof
"""
    )

    theorem = pl.promote_theorem("Conditional identity audit", proof)

    assert theorem.premises == [pp.parse_formula("P", set())]
    assert theorem.generalized_names == []
    assert theorem.conclusion == pp.parse_formula("P -> P", set())


def test_promotion_generalizes_only_top_level_object_declarations():
    proof = _checked_proof(
        """1. Let a be any object. (Declaration)
2. Let P be a closed formula. (Declaration)
3. P -> a = a. (Conditional Introduction from subproof below)
begin subproof
 3.1. P. (Assumption for Conditional Introduction)
 3.2. Let Y be any object. (Declaration)
 3.3. a = a. (Reflexivity)
end subproof
"""
    )

    theorem = pl.promote_theorem("Nested declaration audit", proof)

    assert theorem.generalized_names == ["a"]


def test_fresh_variable_subproof_flag_is_not_a_generalized_parameter():
    proof = _checked_proof(
        """1. forall x, x = x. (Universal Generalization from subproof below)
begin subproof
 1.1. let x be arbitrary. (Fresh Variable)
 1.2. x = x. (Reflexivity)
end subproof
"""
    )

    theorem = pl.promote_theorem("Universal identity audit", proof)

    assert theorem.generalized_names == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "promotion must not generalize an Existence-from-line witness; "
        "kernel-side promotion policy is pending"
    ),
)
def test_existence_witness_is_not_a_default_generalized_parameter():
    proof = _checked_proof(
        """1. Let a be any set. (Declaration)
2. Exists X, X = a. (Premise)
3. Let Y be such a set. (Existence from 2)
4. Y = a. (Reiteration from 3)
"""
    )

    theorem = pl.promote_theorem("Existence witness audit", proof)

    # Y is a witness constrained by an existential premise, not an arbitrary
    # top-level parameter. Only the independently declared a is generalized.
    assert theorem.generalized_names == ["a"]


def test_root_assumptions_cannot_be_promoted_as_theorems():
    entries, _ = pp.parse_proof_text(
        """1. Let P be a closed formula. (Declaration)
2. P. (Assumption)
3. P. (Reiteration from 2)
"""
    )
    proof = pl.Proof(entries)

    ok, error = proof.check_detailed()
    assert not ok
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_WRONG_POSITION

    with pytest.raises(ValueError, match="does not validate"):
        pl.promote_theorem("Undischarged assumption audit", proof)


def test_promoted_premise_is_substituted_and_must_be_supplied():
    source = _checked_proof(
        """1. Let a be any object. (Declaration)
2. a = a. (Premise)
3. a = a. (Reiteration from 2)
"""
    )
    theorem = pl.promote_theorem("Identity transport audit", source)

    assert theorem.generalized_names == ["a"]
    assert theorem.premises == [pp.parse_formula("a = a", set())]
    assert theorem.conclusion == pp.parse_formula("a = a", set())

    # Validate with the promoted theorem registered for this citation.
    entries, _ = pp.parse_proof_text(
        """1. Let b be any object. (Declaration)
2. b = b. (Premise)
3. b = b. (Identity transport audit from 2)
"""
    )
    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert ok, error

    missing_premise_entries, _ = pp.parse_proof_text(
        """1. Let b be any object. (Declaration)
2. b = b. (Identity transport audit)
"""
    )
    ok, error = pl.Proof(
        missing_premise_entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert not ok
    assert error is not None
    assert error.label == "2"


def test_promoted_premise_rejects_a_different_instance():
    source = _checked_proof(
        """1. Let a be any object. (Declaration)
2. a = a. (Premise)
3. a = a. (Reiteration from 2)
"""
    )
    theorem = pl.promote_theorem("Identity transport mismatch audit", source)
    entries, _ = pp.parse_proof_text(
        """1. Let b be any object. (Declaration)
2. Let c be any object. (Declaration)
3. b = c. (Premise)
4. b = b. (Identity transport mismatch audit from 3)
"""
    )

    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert not ok
    assert error is not None
    assert error.label == "4"
