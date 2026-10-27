"""What it means for a rule to be "the same rule": `same_configuration`.

`test_parameterized_rule_registration.py` is the acceptance suite for the
rule-registration soundness fix -- a proof's rule list is a list of rule
*configurations*, not of Python classes. This file pins what that suite leaves
to the implementation:

* the comparison itself, rule type by rule type;
* that the *registered* rule decides, so a cited rule cannot vouch for itself
  by overriding the comparison;
* that the same comparison is used wherever a rule list is read or merged (a
  theorem's requirements, `Proof.__init__`, promotion);
* the Pairing rule the elaborator configures for a direct witness line: it is
  registered, it is matched by its witness, and a theorem proved through it
  does not ask its citer for a rule named after a witness of the *other*
  proof.
"""

import pytest

from .support import c, pl, pp, st
from SyLoPy.source.ProofElaboration import ElaboratedEntries

SET_THEORY = st.SET_THEORY_ENVIRONMENT


def _induction(type_predicate="Nat", zero="Zero", successor="Succ"):
    return pl.InductionRule(type_predicate, c(zero), successor)


def _replace_rule(entries, label, rule, references):
    """Swap the justification of an otherwise-valid line for `rule`."""
    for index, entry in enumerate(entries):
        if (
            isinstance(entry, tuple)
            and len(entry) >= 3
            and entry[0] == label
            and entry[1] != "subproof"
        ):
            entries[index] = (entry[0], entry[1], ("rule", rule, references), *entry[3:])
            return
    raise AssertionError(f"no line {label}")


def _proof_allowing_only(entries, rules):
    """`entries` as a proof whose rule list is the standard rules plus `rules`
    -- without the rules the elaborated entries would add themselves -- but
    with the declarations and axioms of their theory."""
    return pl.Proof(
        ElaboratedEntries(
            entries,
            required_axioms=entries.required_axioms,
            required_declarations=entries.required_declarations,
        ),
        rules=pl.default_rules() + list(rules),
    )


# --------------------------------------------------------------------------
# The comparison itself
# --------------------------------------------------------------------------


def test_a_plain_rule_is_only_ever_its_own_class():
    class Subclass(pl.ReiterationRule):
        pass

    assert pl.ReiterationRule().same_configuration(pl.ReiterationRule())
    assert not pl.ReiterationRule().same_configuration(Subclass())
    assert not Subclass().same_configuration(pl.ReiterationRule())
    assert not pl.ReiterationRule().same_configuration(pl.ConditionalIntroductionRule())


def test_induction_is_the_same_configuration_only_with_equal_parameters():
    nat = _induction()

    class Subclass(pl.InductionRule):
        pass

    assert nat.same_configuration(_induction())
    assert not nat.same_configuration(_induction(type_predicate="Int"))
    assert not nat.same_configuration(_induction(zero="ZeroInt"))
    assert not nat.same_configuration(_induction(successor="SuccInt"))
    # Equal parameters do not make a subclass (which may override `applies`)
    # the same rule.
    assert not nat.same_configuration(Subclass("Nat", c("Zero"), "Succ"))
    assert not nat.same_configuration(pl.ReiterationRule())


def test_pairing_is_the_same_configuration_only_for_the_same_witness():
    generic = st.PairingAxiomRule()
    y = st.PairingAxiomRule(witness_name="Y")

    assert generic.same_configuration(st.PairingAxiomRule())
    assert y.same_configuration(st.PairingAxiomRule(witness_name="Y"))
    assert not generic.same_configuration(y)
    assert not y.same_configuration(generic)
    assert not y.same_configuration(st.PairingAxiomRule(witness_name="W"))


def test_a_theorem_is_authorized_by_being_the_registered_object():
    """A `TheoremRule` is trusted because a proof was promoted into it, so a
    second object with the same words is not thereby registered."""
    q = pp.parse_formula("Q", set())
    theorem = pl.TheoremRule("Q is true", [], q, [])
    twin = pl.TheoremRule("Q is true", [], q, [])

    assert theorem.same_configuration(theorem)
    assert not theorem.same_configuration(twin)


# --------------------------------------------------------------------------
# The registered rule decides
# --------------------------------------------------------------------------


def _self_approving(parent, conclusion, premise_arity):
    """A subclass of `parent` that proves `conclusion` and also claims to be
    whatever configuration it is compared with."""

    class Forged(parent):
        name = f"Forged {parent.name}"

        def applies(self, candidates, phi):
            return len(candidates) == premise_arity and pl._ast_eq(phi, conclusion)

        def same_configuration(self, other):
            return True

    Forged.premise_arity = premise_arity
    return Forged()


def _plain_citation(p, q):
    forged = _self_approving(pl.ReiterationRule, q, 0)
    return forged, [("1", q, ("rule", forged, []))], "1"


def _rule_below_citation(p, q):
    forged = _self_approving(pl.ConditionalIntroductionRule, q, 1)
    return forged, [("1", q, ("rule_below", forged), [("1.1", p, ("assume",))])], "1"


def _hybrid_citation(p, q):
    forged = _self_approving(pl.ConjunctionEliminationRule, q, 2)
    return forged, [
        ("1", p, ("premise",)),
        ("2", q, ("rule_hybrid", forged, ["1"]), [[("2.1", p, ("assume",))]]),
    ], "2"


@pytest.mark.parametrize(
    "citation",
    [_plain_citation, _rule_below_citation, _hybrid_citation],
    ids=["rule", "rule_below", "rule_hybrid"],
)
def test_a_cited_rule_cannot_vouch_for_itself(citation):
    """A subclass that overrides `same_configuration` to say yes is still not
    registered: the comparison is made by the registered rule, with the cited
    one as its argument."""
    p = pp.parse_formula("P", set())
    q = pp.parse_formula("Q", set())
    forged, entries, label = citation(p, q)
    proof = pl.Proof(
        entries,
        rules=pl.default_rules(),
        declarations=[
            pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
            pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
        ],
    )
    ok, error = proof.check_detailed()
    assert not ok
    assert error.label == label
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE

    # The same proof is fine when the forged rule really is registered -- the
    # rejection above is about registration, nothing else.
    registered = pl.Proof(
        entries,
        rules=pl.default_rules() + [forged],
        declarations=[
            pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
            pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
        ],
    )
    ok, error = registered.check_detailed()
    assert ok, error


def test_a_theorem_requirement_cannot_vouch_for_itself_either():
    """The requirements of a cited theorem are checked the same way (`allows_rule`)."""
    q = pp.parse_formula("Q", set())
    declarations = [pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA)]
    forged = _self_approving(pl.ReiterationRule, q, 0)
    source = pl.Proof(
        [("1", q, ("rule", forged, []))],
        rules=pl.default_rules() + [forged],
        declarations=declarations,
    )
    ok, error = source.check_detailed()
    assert ok, error
    theorem = pl.promote_theorem("Needs a forged rule", source, generalized_names=[])

    caller = pl.Proof(
        [("1", q, ("rule", theorem, []))],
        rules=pl.default_rules() + [theorem],
        declarations=declarations,
    )
    ok, error = caller.check_detailed()
    assert not ok
    assert error.label == "1"
    assert error.category == pl.CATEGORY_RULE_MISMATCH


def test_the_rule_context_allows_a_configuration_not_a_class():
    nat, integer = _induction(), _induction("Int", "ZeroInt", "SuccInt")
    context = pl.RuleContext(rules=[integer])

    assert context.allows_rule(_induction("Int", "ZeroInt", "SuccInt"))
    assert not context.allows_rule(nat)
    assert not pl.RuleContext().allows_rule(nat)


# --------------------------------------------------------------------------
# One equivalence, wherever rule lists are merged
# --------------------------------------------------------------------------


def _nat_induction_world():
    declarations = [
        pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
        pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
    ]
    base = pp.parse_formula("P(Zero)", set())
    step = pp.parse_formula("forall n, ((Nat(n) and P(n)) -> P(Succ(n)))", set())
    result = pp.parse_formula("forall x, (Nat(x) -> P(x))", set())
    return declarations, base, step, result


def test_proof_merges_required_rules_by_configuration():
    nat_a, nat_b = _induction(), _induction()
    integer = _induction("Int", "ZeroInt", "SuccInt")

    # Equal configurations collapse into one rule; distinct ones all stay.
    proof = pl.Proof(ElaboratedEntries([], required_rules=[nat_a, nat_b, integer]))
    configured = [r for r in proof.rules if isinstance(r, pl.InductionRule)]
    assert len(configured) == 2
    assert any(r.same_configuration(nat_a) for r in configured)
    assert any(r.same_configuration(integer) for r in configured)

    # A rule the caller configured already counts: its twin is not added again.
    proof = pl.Proof(
        ElaboratedEntries([], required_rules=[nat_b]),
        rules=pl.default_rules() + [nat_a],
    )
    assert [r for r in proof.rules if isinstance(r, pl.InductionRule)] == [nat_a]


def test_promotion_records_one_requirement_for_equivalent_rule_instances():
    declarations, base, step, result = _nat_induction_world()
    first, second = _induction(), _induction()
    proof = pl.Proof(
        [
            ("1", base, ("premise",)),
            ("2", step, ("premise",)),
            ("3", result, ("rule", first, ["1", "2"])),
            ("4", result, ("rule", second, ["1", "2"])),
        ],
        rules=pl.default_rules() + [first, second],
        declarations=declarations,
    )
    ok, error = proof.check_detailed()
    assert ok, error

    theorem = pl.promote_theorem("Nat induction, twice", proof)
    assert len(theorem.required_rules) == 1
    assert theorem.required_rules[0].same_configuration(first)


def test_promotion_records_each_distinct_rule_configuration():
    """Nat induction and Int induction share a Python class and a name; a
    theorem that used both needs both."""
    declarations = [
        pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Int", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
        pl.Declaration("ZeroInt", pl.DeclarationKind.OBJECT),
        pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
        pl.Declaration("SuccInt", pl.DeclarationKind.FUNCTION, arity=1),
    ]
    nat, integer = _induction(), _induction("Int", "ZeroInt", "SuccInt")
    nat_base = pp.parse_formula("P(Zero)", set())
    nat_step = pp.parse_formula("forall n, ((Nat(n) and P(n)) -> P(Succ(n)))", set())
    nat_result = pp.parse_formula("forall x, (Nat(x) -> P(x))", set())
    int_base = pp.parse_formula("P(ZeroInt)", set())
    int_step = pp.parse_formula("forall n, ((Int(n) and P(n)) -> P(SuccInt(n)))", set())
    int_result = pp.parse_formula("forall x, (Int(x) -> P(x))", set())
    proof = pl.Proof(
        [
            ("1", nat_base, ("premise",)),
            ("2", nat_step, ("premise",)),
            ("3", nat_result, ("rule", nat, ["1", "2"])),
            ("4", int_base, ("premise",)),
            ("5", int_step, ("premise",)),
            ("6", int_result, ("rule", integer, ["4", "5"])),
        ],
        rules=pl.default_rules() + [nat, integer],
        declarations=declarations,
    )
    ok, error = proof.check_detailed()
    assert ok, error

    theorem = pl.promote_theorem("Nat and Int induction", proof)
    required = [r for r in theorem.required_rules if isinstance(r, pl.InductionRule)]
    assert len(required) == 2
    assert any(r.same_configuration(nat) for r in required)
    assert any(r.same_configuration(integer) for r in required)


def test_a_theorem_requirement_is_met_by_an_equivalent_rule_instance():
    declarations, base, step, result = _nat_induction_world()
    used = _induction()
    source = pl.Proof(
        [
            ("1", base, ("premise",)),
            ("2", step, ("premise",)),
            ("3", result, ("rule", used, ["1", "2"])),
        ],
        rules=pl.default_rules() + [used],
        declarations=declarations,
    )
    ok, error = source.check_detailed()
    assert ok, error
    theorem = pl.promote_theorem("Nat induction", source)

    separately_built = _induction()
    assert separately_built is not used
    citer = pl.Proof(
        [
            ("1", base, ("premise",)),
            ("2", step, ("premise",)),
            ("3", result, ("rule", theorem, ["1", "2"])),
        ],
        rules=pl.default_rules() + [theorem, separately_built],
        declarations=declarations,
    )
    ok, error = citer.check_detailed()
    assert ok, error


# --------------------------------------------------------------------------
# The Pairing rule a direct witness line configures
# --------------------------------------------------------------------------

TWO_WITNESSES = """1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let c be any object. (Declaration)
4. Let d be any object. (Declaration)
5. There is a set Y = {a, b}. (Axiom of Pairing)
6. There is a set W = {c, d}. (Axiom of Pairing)
"""


def _witness_names(rules):
    return sorted(
        (rule.witness_name or "")
        for rule in rules
        if isinstance(rule, st.PairingAxiomRule)
    )


def test_every_direct_witness_line_registers_its_own_rule():
    entries, _ = pp.parse_proof_text(TWO_WITNESSES, environment=SET_THEORY)
    assert _witness_names(entries.required_rules) == ["", "W", "Y"]

    proof = pl.Proof(entries)
    assert _witness_names(proof.rules) == ["", "W", "Y"]
    ok, error = proof.check_detailed()
    assert ok, error


def test_a_witness_rule_authorizes_only_its_own_witness():
    """The Pairing rule for a witness `Z` is not registered by registering the
    generic rule and the rule for `Y`; a line that cites it is refused even
    though, with the rule registered, it is a perfectly good line."""
    entries, _ = pp.parse_proof_text(
        """1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. There is a set Z = {a, b}. (Axiom of Pairing)
""",
        environment=SET_THEORY,
    )
    generic, y, z = (
        st.PairingAxiomRule(),
        st.PairingAxiomRule(witness_name="Y"),
        st.PairingAxiomRule(witness_name="Z"),
    )

    ok, error = _proof_allowing_only(entries, [generic, y]).check_detailed()
    assert not ok
    assert error.label == "3"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE

    ok, error = _proof_allowing_only(entries, [generic, y, z]).check_detailed()
    assert ok, error


PAIRING_SOURCE = """1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. There is a set Y = {a, b}. (Axiom of Pairing)
4. a = a. (Reflexivity)
5. a = a or a = b. (Disjunction Introduction from 4)
6. a is in Y. (Set property from 3, 5)
7. b = b. (Reflexivity)
8. b = a or b = b. (Disjunction Introduction from 7)
9. b is in Y. (Set property from 3, 8)
10. a is in Y and b is in Y. (Conjunction Introduction from 6, 9)
"""

PAIRING_TARGET = """1. Let c be any object. (Declaration)
2. Let d be any object. (Declaration)
3. Let Y be any set. (Declaration)
4. forall u, (In(u, Y) <-> (u = c or u = d)). (Premise)
5. In(c, Y) and In(d, Y). (Reiteration from 4)
"""


def test_a_theorem_proved_through_a_witness_line_asks_for_the_pairing_rule():
    """The witness is a name local to the proof that chose it: the theorem
    carries what the line said as a premise, and asks its citer for the
    Pairing rule -- not for a rule configured with the *source* proof's `Y`,
    which no other proof has. (It still asks for the Pairing rule.)"""
    entries, _ = pp.parse_proof_text(PAIRING_SOURCE, environment=SET_THEORY)
    source = pl.Proof(entries)
    ok, error = source.check_detailed()
    assert ok, error
    theorem = pl.promote_theorem("Pairing contains both", source)

    pairing = [r for r in theorem.required_rules if isinstance(r, st.PairingAxiomRule)]
    assert [r.witness_name for r in pairing] == [None]

    target, _ = pp.parse_proof_text(PAIRING_TARGET, environment=SET_THEORY)
    _replace_rule(target, "5", theorem, ["4"])

    # A proof of set theory has the Pairing rule, and may cite the theorem.
    ok, error = pl.Proof(target, rules=pl.default_rules() + [theorem]).check_detailed()
    assert ok, error

    # A proof that does not have it may not. (The same line and the same
    # theory, but without the rules the set-theory environment would add.)
    ok, error = _proof_allowing_only(
        target, [st.SetPropertyRule(), theorem]
    ).check_detailed()
    assert not ok
    assert error.label == "5"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "PairingAxiom" in error.detail
