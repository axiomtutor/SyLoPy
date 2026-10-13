"""Adversarial audit of the proof-to-theorem promotion boundary.

These probes are deliberately test-only: Claude owns the kernel implementation.
Known gaps are marked expected-failure only after the specific behavior is
reproduced, so unrelated setup or validation failures remain ordinary failures.
"""

import pytest

from .support import c, pl, pp


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
    assert error.category in {pl.CATEGORY_RULE_MISMATCH, pl.CATEGORY_ARITY_MISMATCH}

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

@pytest.mark.parametrize(
    ("dependency_tag", "proof_argument"),
    [("Premise", "premises"), ("Axiom", "axioms")],
)
def test_promotion_does_not_drop_a_dependency_used_only_inside_a_subproof(
    dependency_tag, proof_argument
):
    q = pp.parse_formula("Q", set())
    entries, _ = pp.parse_proof_text(
        f"""1. Let P, Q be closed formulas. (Declaration)
2. P -> Q. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption for Conditional Introduction)
 2.2. Q. ({dependency_tag})
end subproof
"""
    )
    source = pl.Proof(entries, **{proof_argument: [q]})
    ok, error = source.check_detailed()
    assert ok, error

    try:
        theorem = pl.promote_theorem("Nested dependency audit", source)
    except ValueError:
        # Refusing to promote a proof with a non-root dependency is safe.
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
            f"promotion dropped a nested {dependency_tag} dependency and made P -> Q a zero-premise theorem"
        )
    assert error is not None
    assert error.label == "2"
    assert error.category in {pl.CATEGORY_RULE_MISMATCH, pl.CATEGORY_ARITY_MISMATCH}

def test_promotion_does_not_drop_relation_property_declaration_dependencies():
    source = _checked_proof(
        """1. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
"""
    )
    try:
        theorem = pl.promote_theorem("Relation metadata dependency audit", source)
    except ValueError:
        # Current promotion cannot express a dependency on per-proof relation
        # metadata as a formula premise; refusing this promotion is safe.
        return

    target_entries, _ = pp.parse_proof_text(
        """1. Let X be any set, R be a symmetric relation on X, b be in X. (Declaration)
2. R(b,b). (Reiteration from 1)
"""
    )
    _replace_rule(target_entries, "2", theorem, ["1"])
    ok, error = pl.Proof(
        target_entries, rules=pl.default_rules() + [theorem]
    ).check_detailed()

    if ok:
        pytest.xfail(
            "promotion forgot that R was declared reflexive and reused R(a,a) under only symmetry"
        )
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH

def test_promotion_requires_the_same_parameterized_induction_rule():
    """A theorem requiring Nat induction must not accept Int induction instead."""
    declarations = [
        pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Int", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
        pl.Declaration("ZeroInt", pl.DeclarationKind.OBJECT),
        pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
        pl.Declaration("SuccInt", pl.DeclarationKind.FUNCTION, arity=1),
    ]
    base = pp.parse_formula("P(Zero)", set())
    step = pp.parse_formula("forall n, ((Nat(n) and P(n)) -> P(Succ(n)))", set())
    conclusion = pp.parse_formula("forall x, (Nat(x) -> P(x))", set())

    nat_induction = pl.InductionRule("Nat", c("Zero"), "Succ")
    source_entries = [
        ("1", None, ("declare", declarations)),
        ("2", base, ("premise",)),
        ("3", step, ("premise",)),
        ("4", conclusion, ("rule", nat_induction, ["2", "3"])),
    ]
    source = pl.Proof(source_entries, rules=pl.default_rules() + [nat_induction])
    ok, error = source.check_detailed()
    assert ok, error

    theorem = pl.promote_theorem("Nat induction audit", source)
    assert len(theorem.required_rules) == 1
    assert isinstance(theorem.required_rules[0], pl.InductionRule)
    assert theorem.required_rules[0].type_predicate == "Nat"
    assert theorem.required_rules[0].zero_term == c("Zero")
    assert theorem.required_rules[0].succ_symbol == "Succ"

    # The target proof has the same premises but a different theory rule. It
    # has no Nat induction rule. A class-only requirement check may nevertheless
    # let the theorem through because both schema instances share a Python type.
    int_induction = pl.InductionRule("Int", c("ZeroInt"), "SuccInt")
    target_entries = [
        ("1", None, ("declare", declarations)),
        ("2", base, ("premise",)),
        ("3", step, ("premise",)),
        ("4", conclusion, ("rule", theorem, ["2", "3"])),
    ]
    ok, error = pl.Proof(
        target_entries, rules=pl.default_rules() + [theorem, int_induction]
    ).check_detailed()

    if ok:
        pytest.xfail(
            "a theorem proved using Nat induction was accepted where only Int "
            "induction is registered; the required-rule check may ignore "
            "parameter differences between instances of InductionRule"
        )
    assert error is not None
    assert error.label == "4"
    assert error.category == pl.CATEGORY_RULE_MISMATCH


def test_promotion_does_not_drop_a_custom_inference_rule_dependency():
    q = pp.parse_formula("Q", set())

    class UnconditionalQRule(pl.InferenceRule):
        """An environment-supplied rule used to probe promotion dependencies."""

        name = "Unconditional Q audit rule"
        premise_arity = 0

        def applies(self, candidates, phi):
            return not candidates and pl._ast_eq(phi, q)

    custom_rule = UnconditionalQRule()
    entries, _ = pp.parse_proof_text(
        """1. Let Q be a closed formula. (Declaration)
2. Q. (Reiteration from 1)
"""
    )
    _replace_rule(entries, "2", custom_rule, [])
    source = pl.Proof(entries, rules=pl.default_rules() + [custom_rule])
    ok, error = source.check_detailed()
    assert ok, error

    try:
        theorem = pl.promote_theorem("Custom inference dependency audit", source)
    except ValueError:
        # Refusing promotion when the proof depends on a rule that the
        # promoted theorem cannot carry forward is safe.
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
            "promotion discarded the source proof's custom inference rule and "
            "made its conclusion available without that rule"
        )
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH

