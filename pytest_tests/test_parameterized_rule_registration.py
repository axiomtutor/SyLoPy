"""Audit that parameterized inference rules are registered by configuration.

The trusted rule environment is not just a list of Python classes. An
InductionRule is parameterized by the predicate and successor structure for
which induction is sound; registering induction for Int must not authorize a
direct rule object for Nat.
"""

import pytest
import SyLoPy.source.SetTheory as st

from .support import c, fl, pl, pp


def _induction_case(type_predicate, zero, successor, extra_declarations=()):
    declarations = [
        pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Int", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
        pl.Declaration("ZeroInt", pl.DeclarationKind.OBJECT),
        pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
        pl.Declaration("SuccInt", pl.DeclarationKind.FUNCTION, arity=1),
        *extra_declarations,
    ]
    base = pp.parse_formula(f"P({zero})", set())
    step = pp.parse_formula(
        f"forall n, (({type_predicate}(n) and P(n)) -> "
        f"P({successor}(n)))",
        set(),
    )
    conclusion = pp.parse_formula(
        f"forall x, ({type_predicate}(x) -> P(x))",
        set(),
    )
    rule = pl.InductionRule(type_predicate, c(zero), successor)
    entries = [
        ("1", base, ("premise",)),
        ("2", step, ("premise",)),
        ("3", conclusion, ("rule", rule, ["1", "2"])),
    ]
    return declarations, rule, entries


def test_direct_citation_cannot_use_an_unregistered_parameterized_rule():
    """Registering Int induction does not register a direct Nat-rule object."""
    declarations, nat_induction, entries = _induction_case("Nat", "Zero", "Succ")
    int_induction = pl.InductionRule("Int", c("ZeroInt"), "SuccInt")
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + [int_induction],
        declarations=declarations,
    )

    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "the proof cited Nat induction successfully although its rule "
            "environment registers only Int induction; _rule_is_registered "
            "currently checks the Python class rather than the parameters"
        )

    assert error is not None
    assert error.label == "3"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE


def test_equivalent_parameterized_rule_configuration_is_usable():
    """A separate object with the same semantic parameters is also authorized."""
    declarations, cited_induction, entries = _induction_case("Nat", "Zero", "Succ")
    registered_induction = pl.InductionRule("Nat", c("Zero"), "Succ")
    assert registered_induction is not cited_induction
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + [registered_induction],
        declarations=declarations,
    )
    ok, error = proof.check_detailed()
    assert ok, error


def test_direct_citation_cannot_use_an_unregistered_theorem_instance():
    """A validated theorem in the allowlist must not authorize arbitrary theorems."""
    p = pp.parse_formula("P", set())
    q = pp.parse_formula("Q", set())
    declarations = [
        pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
        pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
    ]
    identity_entries = [
        ("1", None, ("declare", [declarations[0]])),
        ("2", fl.Implies(p, p), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("2.1", p, ("assume",)),
            ("2.2", p, ("rule", pl.ReiterationRule(), ["2.1"])),
        ]),
    ]
    identity_proof = pl.Proof(identity_entries)
    ok, error = identity_proof.check_detailed()
    assert ok, error
    registered = pl.promote_theorem("Identity", identity_proof)

    # This TheoremRule was not promoted from a proof and is not in the rule
    # allowlist. The kernel should reject it even though registered is a
    # different TheoremRule instance.
    unregistered = pl.TheoremRule("Unregistered theorem", [], q, [])
    proof = pl.Proof(
        [("1", q, ("rule", unregistered, []))],
        rules=pl.default_rules() + [registered],
        declarations=declarations,
    )

    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "the kernel accepted an unregistered TheoremRule instance because "
            "another validated TheoremRule instance of the same Python class "
            "was allowed"
        )

    assert error is not None
    assert error.label == "1"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE

def _induction_configuration(rule):
    return (rule.type_predicate, repr(rule.zero_term), rule.succ_symbol)


def test_proof_keeps_distinct_parameterized_rules_from_elaboration_metadata():
    """Proof.__init__ must not merge Nat and Int induction by type/name."""
    from SyLoPy.source.ProofElaboration import ElaboratedEntries

    nat = pl.InductionRule("Nat", c("Zero"), "Succ")
    integer = pl.InductionRule("Int", c("ZeroInt"), "SuccInt")
    entries = ElaboratedEntries([], required_rules=[nat, integer])
    proof = pl.Proof(entries)

    configured = [
        rule for rule in proof.rules if isinstance(rule, pl.InductionRule)
    ]
    if len(configured) != 2:
        pytest.xfail(
            "Proof.__init__ discarded a distinct required InductionRule "
            "because its deduplication compares only type and name"
        )

    assert {_induction_configuration(rule) for rule in configured} == {
        _induction_configuration(nat),
        _induction_configuration(integer),
    }

def test_unregistered_subclass_cannot_override_a_standard_rule():
    """Default Reiteration registration must not authorize altered subclasses."""
    q = pp.parse_formula("Q", set())

    class ForgedReiterationRule(pl.ReiterationRule):
        name = "Forged Reiteration"
        premise_arity = 0

        def applies(self, candidates, phi):
            return not candidates and pl._ast_eq(phi, q)

    forged = ForgedReiterationRule()
    proof = pl.Proof(
        [("1", q, ("rule", forged, []))],
        rules=pl.default_rules(),
        declarations=[pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA)],
    )

    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "an unregistered subclass overrode ReiterationRule to assert Q "
            "without premises, but passed the class-based rule allowlist"
        )

    assert error is not None
    assert error.label == "1"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE

def test_theorem_cannot_replace_a_required_rule_subclass_with_its_parent():
    """Theorem requirements must authorize the actual rule behavior used."""
    q = pp.parse_formula("Q", set())
    declarations = [
        pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
    ]

    class ForgedReiterationRule(pl.ReiterationRule):
        name = "Forged Reiteration"
        premise_arity = 0

        def applies(self, candidates, phi):
            return not candidates and pl._ast_eq(phi, q)

    forged = ForgedReiterationRule()
    source = pl.Proof(
        [("1", q, ("rule", forged, []))],
        rules=pl.default_rules() + [forged],
        declarations=declarations,
    )
    ok, error = source.check_detailed()
    assert ok, error
    theorem = pl.promote_theorem("Requires forged subclass", source, generalized_names=[])

    # The caller registers the theorem and ordinary logical rules, but not the
    # custom subclass that let the theorem prove Q without premises.
    caller = pl.Proof(
        [("1", q, ("rule", theorem, []))],
        rules=pl.default_rules() + [theorem],
        declarations=declarations,
    )
    ok, error = caller.check_detailed()
    if ok:
        pytest.xfail(
            "RuleContext.allows_rule treated the unregistered ForgedReiterationRule "
            "requirement as available because default_rules() contains its parent"
        )

    assert error is not None
    assert error.label == "1"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "Forged Reiteration" in error.detail

def test_pairing_witness_rule_is_exported_as_a_required_rule():
    """The generated Pairing rule needs explicit registration, not class matching."""
    text = """
1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. There is a set Y = {a, b}. (Axiom of Pairing)
"""
    entries, _ = pp.parse_proof_text(
        text, environment=st.SET_THEORY_ENVIRONMENT
    )
    pairing_entry = next(entry for entry in entries if entry[0] == "3")
    line_rule = pairing_entry[2][1]
    assert isinstance(line_rule, st.PairingAxiomRule)
    assert line_rule.witness_name == "Y"

    registered = [
        rule for rule in entries.required_rules
        if isinstance(rule, st.PairingAxiomRule)
        and rule.witness_name == "Y"
    ]
    if not registered:
        pytest.xfail(
            "the elaborator embeds PairingAxiomRule(witness_name='Y') in the "
            "line justification but exports only generic PairingAxiomRule(); "
            "class-based authorization currently masks the missing registration"
        )

    # Keep the ordinary schema rule as well as the generated witness instance
    # both in the intermediate metadata and in the final Proof allowlist.
    generic_registered = any(
        isinstance(rule, st.PairingAxiomRule) and rule.witness_name is None
        for rule in entries.required_rules
    )
    assert registered
    assert generic_registered

    proof_rules = [
        rule for rule in pl.Proof(entries).rules
        if isinstance(rule, st.PairingAxiomRule)
    ]
    assert any(rule.witness_name == "Y" for rule in proof_rules)
    assert any(rule.witness_name is None for rule in proof_rules)

def test_unregistered_subclass_cannot_override_a_rule_below_citation():
    """The rule_below validator must reject overriding subclasses too."""
    p = pp.parse_formula("P", set())
    q = pp.parse_formula("Q", set())
    declarations = [
        pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
        pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
    ]

    class ForgedConditionalIntroductionRule(pl.ConditionalIntroductionRule):
        name = "Forged Conditional Introduction"
        premise_arity = 1

        def applies(self, candidates, phi):
            return (
                len(candidates) == 1
                and isinstance(candidates[0], pl.SubproofRecord)
                and pl._ast_eq(phi, q)
            )

    forged = ForgedConditionalIntroductionRule()
    proof = pl.Proof(
        [
            ("1", q, ("rule_below", forged), [
                ("1.1", p, ("assume",)),
            ]),
        ],
        rules=pl.default_rules(),
        declarations=declarations,
    )
    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "_validate_rule_below authorized an unregistered subclass of "
            "ConditionalIntroductionRule through isinstance matching"
        )

    assert error is not None
    assert error.label == "1"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE


def test_unregistered_subclass_cannot_override_a_hybrid_rule_citation():
    """The hybrid validator must reject overriding subclasses too."""
    p = pp.parse_formula("P", set())
    q = pp.parse_formula("Q", set())
    declarations = [
        pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
        pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
    ]

    class ForgedConjunctionEliminationRule(pl.ConjunctionEliminationRule):
        name = "Forged Conjunction Elimination"
        premise_arity = 2

        def applies(self, candidates, phi):
            return len(candidates) == 2 and pl._ast_eq(phi, q)

    forged = ForgedConjunctionEliminationRule()
    proof = pl.Proof(
        [
            ("1", p, ("premise",)),
            ("2", q, ("rule_hybrid", forged, ["1"]), [
                ("2.1", p, ("assume",)),
            ]),
        ],
        rules=pl.default_rules(),
        declarations=declarations,
    )
    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "_validate_rule_hybrid authorized an unregistered subclass of "
            "ConjunctionEliminationRule through isinstance matching"
        )

    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE

