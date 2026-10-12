"""Adversarial audit of the proof-to-theorem promotion boundary.

These probes are deliberately test-only: Claude owns the kernel implementation.
Known gaps are marked expected-failure only after the specific behavior is
reproduced, so unrelated setup or validation failures remain ordinary failures.
"""

import pytest

from .support import pl, pp


def _checked_proof(text):
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries)
    ok, error = proof.check_detailed()
    assert ok, error
    return proof



def _replace_rule(entries, label, rule, references):
    """Inject a registered theorem rule after parsing an otherwise-valid line."""
    for index, entry in enumerate(entries):
        if (
            isinstance(entry, tuple)
            and len(entry) >= 3
            and entry[0] == label
            and entry[1] != "subproof"
        ):
            entries[index] = (
                entry[0],
                entry[1],
                ("rule", rule, references),
                *entry[3:],
            )
            return
    raise AssertionError(f"no ordinary proof line with label {label!r}")


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

    assert len(theorem.premises) == 1
    assert pl._ast_eq(theorem.premises[0], pp.parse_formula("P", set()))
    assert theorem.generalized_names == []
    assert pl._ast_eq(theorem.conclusion, pp.parse_formula("P -> P", set()))


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


def test_existence_witness_is_not_a_default_generalized_parameter():
    proof = _checked_proof(
        """1. Let a be any set. (Declaration)
2. Exists X, X = a. (Premise)
3. Let Y be such a set. (Existence from 2)
4. Y = a. (Reiteration from 3)
"""
    )

    theorem = pl.promote_theorem("Existence witness audit", proof)

    # This is a promotion-policy question, not a demonstrated soundness hole:
    # the witness formula is retained as a premise. Mark only the exact current
    # behavior for review rather than xfail-ing the whole test function.
    if theorem.generalized_names == ["a", "Y"]:
        pytest.xfail(
            "promotion currently lists the top-level Existence-from-line witness as generalized"
        )
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
    assert len(theorem.premises) == 1
    assert pl._ast_eq(theorem.premises[0], pp.parse_formula("a = a", set()))
    assert pl._ast_eq(theorem.conclusion, pp.parse_formula("a = a", set()))

    # The parser does not know a newly created TheoremRule by name. Parse a
    # known rule shape, then inject the registered theorem directly to test
    # promotion/validation independently of citation-name resolution.
    entries, _ = pp.parse_proof_text(
        """1. Let b be any object. (Declaration)
2. b = b. (Premise)
3. b = b. (Reiteration from 2)
"""
    )
    _replace_rule(entries, "3", theorem, ["2"])
    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert ok, error

    missing_premise_entries, _ = pp.parse_proof_text(
        """1. Let b be any object. (Declaration)
2. b = b. (Reflexivity)
"""
    )
    _replace_rule(missing_premise_entries, "2", theorem, [])
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
4. b = b. (Reiteration from 3)
"""
    )
    _replace_rule(entries, "4", theorem, ["3"])

    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    assert not ok
    assert error is not None
    assert error.label == "4"

def test_an_explicit_promotion_conclusion_must_have_been_derived():
    proof = _checked_proof(
        """1. Let a be any object. (Declaration)
2. a = a. (Reflexivity)
"""
    )

    # The proof derives only a = a. A safe promotion API rejects Q here.
    unproved_conclusion = pp.parse_formula("Q", set())
    try:
        theorem = pl.promote_theorem(
            "Unproved explicit conclusion audit",
            proof,
            conclusion=unproved_conclusion,
        )
    except ValueError:
        return

    entries, _ = pp.parse_proof_text(
        """1. Let Q be a closed formula. (Declaration)
2. Q. (Reiteration from 1)
"""
    )
    _replace_rule(entries, "2", theorem, [])
    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    if ok:
        pytest.xfail(
            "promote_theorem accepted an explicit conclusion absent from the proof"
        )
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH


def test_explicit_generalized_names_cannot_generalize_the_empty_set():
    proof = _checked_proof(
        """1. Let x be any object. (Declaration)
2. x is not in the empty set. (Set property)
"""
    )

    try:
        theorem = pl.promote_theorem(
            "No element belongs to any set audit",
            proof,
            generalized_names=["x", "EmptySet"],
        )
    except ValueError:
        return

    entries, _ = pp.parse_proof_text(
        """1. Let y be any object. (Declaration)
2. Let Y be any set. (Declaration)
3. y is not in Y. (Reiteration from 1)
"""
    )
    _replace_rule(entries, "3", theorem, [])
    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    if ok:
        pytest.xfail(
            "generalized_names override turned EmptySet's property into a universal set rule"
        )
    assert error is not None
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH


def test_promotion_cannot_export_a_direct_pairing_witness_as_a_free_constant():
    proof = _checked_proof(
        """1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. There is a set Y = {a, b}. (Axiom of Pairing)
4. a = a. (Reflexivity)
5. a = a or a = b. (Disjunction Introduction from 4)
6. a is in Y. (Set property from 3, 5)
"""
    )
    try:
        theorem = pl.promote_theorem("Pairing membership audit", proof)
    except ValueError:
        # Refusing to promote this proof is a safe response to its witness
        # assumption; the proof itself was already checked above.
        return

    entries, _ = pp.parse_proof_text(
        """1. Let c be any object. (Declaration)
2. Let Y be any set. (Declaration)
3. c is in Y. (Reiteration from 1)
"""
    )
    _replace_rule(entries, "3", theorem, [])
    ok, error = pl.Proof(
        entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()
    if ok:
        pytest.xfail(
            "promotion dropped the direct Pairing witness's defining property"
        )
    assert error is not None
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH

def test_promotion_does_not_erase_a_custom_axiom_dependency():
    q = pp.parse_formula("Q", set())
    source_entries, _ = pp.parse_proof_text(
        """1. Let Q be a closed formula. (Declaration)
2. Q. (Axiom)
3. Q. (Reiteration from 2)
"""
    )
    # The proof is valid only under the caller-supplied axiom Q.
    source = pl.Proof(source_entries, axioms=[q])
    ok, error = source.check_detailed()
    assert ok, error

    try:
        theorem = pl.promote_theorem("Custom axiom dependency audit", source)
    except ValueError:
        # Rejecting promotion when a source axiom dependency cannot be carried
        # forward is safe; the source proof itself was checked above.
        return

    target_entries, _ = pp.parse_proof_text(
        """1. Let Q be a closed formula. (Declaration)
2. Q. (Reiteration from 1)
"""
    )
    _replace_rule(target_entries, "2", theorem, [])
    ok, error = pl.Proof(
        target_entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()

    if ok:
        pytest.xfail(
            "promotion discarded the custom axiom Q and exported Q as a zero-premise theorem"
        )
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH

def test_promotion_does_not_drop_a_premise_used_only_inside_a_subproof():
    q = pp.parse_formula("Q", set())
    entries, _ = pp.parse_proof_text(
        """1. Let P, Q be closed formulas. (Declaration)
2. P -> Q. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption for Conditional Introduction)
 2.2. Q. (Premise)
end subproof
"""
    )
    source = pl.Proof(entries, premises=[q])
    ok, error = source.check_detailed()
    assert ok, error

    try:
        theorem = pl.promote_theorem("Nested premise dependency audit", source)
    except ValueError:
        # Refusing to promote a proof with a non-root premise dependency is safe.
        return

    target_entries, _ = pp.parse_proof_text(
        """1. Let P, Q be closed formulas. (Declaration)
2. P -> Q. (Reiteration from 1)
"""
    )
    _replace_rule(target_entries, "2", theorem, [])
    ok, error = pl.Proof(
        target_entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()

    if ok:
        pytest.xfail(
            "promotion dropped Q from a nested Premise line and made P -> Q a zero-premise theorem"
        )
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH

