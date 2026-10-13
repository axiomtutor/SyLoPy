"""A proof's hypotheses reach every rule that treats a constant as arbitrary,
and a promoted theorem carries every hypothesis its proof took for granted.

Two ways a proof can say something about a constant without that showing up
where a freshness check looks (see todos.txt, item 8):

  * a hypothesis stated *inside* the subproof that introduced the constant --
    a `(Premise)` line nested in a `Fresh Variable` subproof or in an
    existential-elimination subproof is a hypothesis of the whole proof, but
    `UniversalGeneralization` and `ExistentialElimination` only looked at what
    was visible before the subproof opened;
  * structure recorded on a declaration (`Let R be a reflexive relation on
    X`), which no line states and which the relation rules read.

Theorem promotion had the same blind spot from the other side: it kept only the
top-level `(Premise)` lines, so a theorem proved from a hypothesis stated in a
subproof, from a `(Declare)` line, from a witness line, or from relation
properties was promoted as if it had no hypotheses at all.

Every negative test here is refused for the reason it names -- the error's
label and wording are asserted -- and has a positive twin that differs only in
what the negative test is about, so a refusal cannot be an accident of
something else in the proof.
"""

import pytest

import importlib

from .support import assert_invalid, assert_valid, c, fl, mp, pl, pp, prop, v

dmc = importlib.import_module("SyLoPy.source.DiscreteMathCore")

P = prop("P")
Q = prop("Q")


def check(text, *, axioms=None):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries, axioms=axioms).check_detailed()


def refused(text, label, *needles, category=pl.CATEGORY_RULE_MISMATCH):
    ok, err = check(text)
    assert not ok, "the proof was accepted"
    assert err.category == category, str(err)
    assert err.label == label, str(err)
    for needle in needles:
        assert needle in err.detail, f"{needle!r} not in {err.detail!r}"


def accepted(text):
    ok, err = check(text)
    assert ok, str(err)


def promote(text, name="Theorem", **kwargs):
    entries, _ = pp.parse_proof_text(text)
    return pl.promote_theorem(name, pl.Proof(entries), **kwargs)


def premises_of(theorem):
    return [repr(premise) for premise in theorem.premises]


def results_of(text):
    return [(number, ok, message) for number, _expected, ok, message, _crashed in mp.run_multi_proof_file(text)]


def declares(*names, kind=pl.DeclarationKind.CLOSED_FORMULA):
    return [pl.Declaration(name, kind) for name in names]


# ---------------------------------------------------------------------------
# Universal generalization: the constant occurs in no hypothesis, wherever the
# hypothesis was stated.
# ---------------------------------------------------------------------------

def test_a_premise_stated_in_the_subproof_does_not_make_its_constant_arbitrary():
    # `forall c, In(c, X)` would follow from "this particular c is in X".
    refused("""
1. Let X be any set. (Declaration)
2. forall c, In(c, X). (Universal Generalization from subproof below)
begin subproof
 2.0. let c be arbitrary. (Fresh Variable)
 2.1. In(c, X). (Premise)
end subproof
""", "2", "occurs in a hypothesis", "In(c, X)")


def test_a_premise_stated_deeper_in_the_subproof_counts_too():
    refused("""
1. Let X be any set, P be a closed formula. (Declaration)
2. forall c, (P -> In(c, X)). (Universal Generalization from subproof below)
begin subproof
 2.0. let c be arbitrary. (Fresh Variable)
 2.1. P -> In(c, X). (Conditional Introduction from subproof below)
 begin subproof
  2.1.1. P. (Assumption for Conditional Introduction)
  2.1.2. In(c, X). (Premise)
 end subproof
end subproof
""", "2", "occurs in a hypothesis")


def test_generalizing_over_a_constant_nothing_was_assumed_about_is_accepted():
    accepted("""
1. Let X be any set. (Declaration)
2. forall c, (In(c, X) -> In(c, X)). (Universal Generalization from subproof below)
begin subproof
 2.0. let c be arbitrary. (Fresh Variable)
 2.1. In(c, X) -> In(c, X). (Conditional Introduction from subproof below)
 begin subproof
  2.1.1. In(c, X). (Assumption for Conditional Introduction)
  2.1.2. In(c, X). (Reiteration from 2.1.1)
 end subproof
end subproof
""")


def test_a_premise_in_the_subproof_that_does_not_mention_the_constant_is_harmless():
    accepted("""
1. Let X be any set, K be a closed formula. (Declaration)
2. forall c, (In(c, X) -> In(c, X)). (Universal Generalization from subproof below)
begin subproof
 2.0. let c be arbitrary. (Fresh Variable)
 2.1. K. (Premise)
 2.2. In(c, X) -> In(c, X). (Conditional Introduction from subproof below)
 begin subproof
  2.2.1. In(c, X). (Assumption for Conditional Introduction)
  2.2.2. In(c, X). (Reiteration from 2.2.1)
 end subproof
end subproof
""")


# ---------------------------------------------------------------------------
# Structure recorded on a declaration is a hypothesis about the names it
# refers to, so a constant it names is not arbitrary.
# ---------------------------------------------------------------------------

def _generalize_over_a_set_with_a_relation_declared_on_it(carrier_of_the_relation):
    """`forall X, (In(a, X) -> Q)` for an arbitrary closed formula `Q`, proved
    by a Fresh Variable subproof for `X` that declares `R` asymmetric and
    reflexive on `carrier_of_the_relation`, then, assuming `In(a, X)`, gets
    `R(a, a)` and `not R(a, a)` from the two relation rules and explodes.
    Built by hand: the surface language only lets a relation be declared on a
    set that a `Let` introduced, never on the flag of a Fresh Variable."""
    a, X, R = c("a"), c("X"), "R"
    in_aX = fl.AtomicFormula("In", [a, X])
    r_aa = fl.AtomicFormula(R, [a, a])
    relation = pl.Declaration(
        R, pl.DeclarationKind.PREDICATE, arity=2,
        metadata=(("carrier", carrier_of_the_relation), ("properties", ("asymmetric", "reflexive"))))
    entries = [
        ("1", None, ("declare", [pl.Declaration("a", pl.DeclarationKind.OBJECT),
                                 pl.Declaration("Y", pl.DeclarationKind.OBJECT),
                                 pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA)])),
        ("2", fl.ForAll("X", fl.Implies(fl.AtomicFormula("In", [a, v("X")]), Q)), ("rule_below", pl.UniversalGeneralizationRule()), [
            ("2.0", fl.AtomicFormula("X", []), ("arbitrary",)),
            ("2.1", None, ("declare", [relation])),
            ("2.2", fl.Implies(in_aX, Q), ("rule_below", pl.ConditionalIntroductionRule()), [
                ("2.2.1", in_aX, ("assume",)),
                ("2.2.2", r_aa, ("rule", dmc.RelationReflexivityRule(), ["2.2.1"])),
                ("2.2.3", fl.Not(r_aa), ("rule", dmc.RelationAsymmetryRule(), ["2.2.2"])),
                ("2.2.4", Q, ("rule", pl.ExplosionRule(), ["2.2.2", "2.2.3"])),
            ]),
        ]),
    ]
    rules = pl.default_rules() + [dmc.RelationReflexivityRule(), dmc.RelationAsymmetryRule()]
    declarations = [pl.Declaration("In", pl.DeclarationKind.PREDICATE, arity=2)]
    return pl.Proof(entries, rules=rules, declarations=declarations).check_detailed()


def test_a_declared_relations_properties_make_its_carrier_non_arbitrary():
    # "R is asymmetric and reflexive on X" can only hold when X has no elements,
    # so it says something about X. Generalizing over X would prove that any
    # closed formula follows from `a` being in some set.
    ok, err = _generalize_over_a_set_with_a_relation_declared_on_it("X")
    assert not ok, "proved an arbitrary Q from `a is in X`, for every X"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.label == "2"
    assert "structure of a declaration" in err.detail


def test_a_relation_declared_on_another_set_gives_the_proof_nothing_to_generalize_from():
    # On `Y` the declaration says nothing about `X`: the relation rules do not
    # apply to `R(a, a)` from `In(a, X)`, so the conditional is never proved, and
    # the refusal is for that line, not for the generalization.
    ok, err = _generalize_over_a_set_with_a_relation_declared_on_it("Y")
    assert not ok
    assert err.label == "2.2.2"


def test_a_relation_declared_on_an_unrelated_set_does_not_block_generalization():
    accepted("""
1. Let Y be any set. (Declaration)
2. Let R be a reflexive relation on Y. (Declaration)
3. forall X, X = X. (Universal Generalization from subproof below)
begin subproof
 3.0. let X be arbitrary. (Fresh Variable)
 3.1. X = X. (Reflexivity)
end subproof
""")


# ---------------------------------------------------------------------------
# Existential elimination: the witness occurs in no hypothesis either.
# ---------------------------------------------------------------------------

def test_a_premise_about_the_witness_stated_in_the_subproof_blocks_elimination():
    # Premises `exists x, P(x)` and `R(m)` do not give `exists x, (P(x) and R(x))`.
    refused("""
1. Let P, R be predicates such that: exists x, P(x). (Premise)
2. Let m be an object. (Declare)
3. exists x, (P(x) and R(x)). (Existential Elimination from 1, subproof below)
begin subproof
 3.1. P(m). (Assumption for Existential Elimination)
 3.2. R(m). (Premise)
 3.3. P(m) and R(m). (Conjunction Introduction from 3.1, 3.2)
 3.4. exists x, (P(x) and R(x)). (Existential Introduction from 3.3)
end subproof
""", "3", "occurs in a hypothesis", "R(m)")


def test_a_witness_that_a_typed_declaration_already_describes_is_not_fresh():
    # `Let m be an integer` states Int(m); the witness of `exists x, P(x)` need
    # not be an integer, so `exists x, (P(x) and Int(x))` does not follow.
    refused("""
1. Let P be a predicate such that: exists x, P(x). (Premise)
2. Let m be an integer. (Declaration)
3. exists x, (P(x) and Int(x)). (Existential Elimination from 1, subproof below)
begin subproof
 3.1. P(m). (Assumption for Existential Elimination)
 3.2. P(m) and Int(m). (Conjunction Introduction from 3.1, 2)
 3.3. exists x, (P(x) and Int(x)). (Existential Introduction from 3.2)
end subproof
""", "3", "occurs in a hypothesis", "Int(m)")


def test_a_witness_reused_under_an_enclosing_assumption_about_it_is_refused():
    # Premises `exists x, P(x)` and `exists y, R(y)` do not give
    # `exists z, (P(z) and R(z))`; reusing the witness `c` inside the first
    # elimination does, unless the second elimination notices that the
    # enclosing subproof assumed `P(c)`. That assumption is two blocks out, so
    # it is not among the lines visible before the second subproof opened.
    refused("""
1. Let P, R be predicates such that: exists x, P(x). exists y, R(y). (Premise)
2. Let c be an object. (Declare)
3. Let K be a closed formula. (Declare)
4. K -> exists z, (P(z) and R(z)). (Existential Elimination from 1, subproof below)
begin subproof
 4.1. P(c). (Assumption for Existential Elimination)
 4.2. K -> exists z, (P(z) and R(z)). (Conditional Introduction from subproof below)
 begin subproof
  4.2.1. K. (Assumption for Conditional Introduction)
  4.2.2. exists z, (P(z) and R(z)). (Existential Elimination from 1, subproof below)
  begin subproof
   4.2.2.1. R(c). (Assumption for Existential Elimination)
   4.2.2.2. P(c) and R(c). (Conjunction Introduction from 4.1, 4.2.2.1)
   4.2.2.3. exists z, (P(z) and R(z)). (Existential Introduction from 4.2.2.2)
  end subproof
 end subproof
end subproof
""", "4.2.2", "occurs in a hypothesis", "P(c)")


def test_a_witness_that_a_relation_declaration_names_is_not_fresh():
    refused("""
1. Let P be a predicate such that: exists x, P(x). (Premise)
2. Let m be an object. (Declare)
3. Let R be a relation on m. (Declaration)
4. exists x, P(x). (Existential Elimination from 1, subproof below)
begin subproof
 4.1. P(m). (Assumption for Existential Elimination)
 4.2. exists x, P(x). (Existential Introduction from 4.1)
end subproof
""", "4", "structure of a declaration")


def test_a_relation_declared_on_another_set_does_not_make_the_witness_non_fresh():
    accepted("""
1. Let P be a predicate such that: exists x, P(x). (Premise)
2. Let m be an object. (Declare)
3. Let Y be any set. (Declaration)
4. Let R be a relation on Y. (Declaration)
5. exists x, P(x). (Existential Elimination from 1, subproof below)
begin subproof
 5.1. P(m). (Assumption for Existential Elimination)
 5.2. exists x, P(x). (Existential Introduction from 5.1)
end subproof
""")


def test_existential_elimination_with_a_fresh_witness_is_accepted():
    accepted("""
1. Let P be a predicate such that: exists x, P(x). (Premise)
2. Let m be an object. (Declare)
3. exists x, P(x). (Existential Elimination from 1, subproof below)
begin subproof
 3.1. P(m). (Assumption for Existential Elimination)
 3.2. exists x, P(x). (Existential Introduction from 3.1)
end subproof
""")


def test_a_premise_in_the_elimination_subproof_that_does_not_mention_the_witness_is_harmless():
    accepted("""
1. Let P be a predicate such that: exists x, P(x). (Premise)
2. Let m be an object. (Declare)
3. Let K be a closed formula. (Declare)
4. exists x, P(x). (Existential Elimination from 1, subproof below)
begin subproof
 4.1. P(m). (Assumption for Existential Elimination)
 4.2. K. (Premise)
 4.3. exists x, P(x). (Existential Introduction from 4.1)
end subproof
""")


# ---------------------------------------------------------------------------
# Promotion carries every hypothesis, at any depth.
# ---------------------------------------------------------------------------

NESTED_PREMISE_THEOREM = """
1. Let A, Q be closed formulas. (Declaration)
2. A -> Q. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption for Conditional Introduction)
 2.2. Q. (Premise)
end subproof
"""


def test_a_premise_stated_in_a_subproof_is_a_premise_of_the_promoted_theorem():
    assert premises_of(promote(NESTED_PREMISE_THEOREM)) == [repr(Q)]


def test_a_theorem_proved_from_a_nested_premise_is_not_citable_without_it():
    theorem = promote(NESTED_PREMISE_THEOREM)
    use = [
        ("1", None, ("declare", declares("A", "Q"))),
        ("2", fl.Implies(prop("A"), Q), ("rule", theorem, [])),
    ]
    assert_invalid(use, pl.CATEGORY_ARITY_MISMATCH, label="2", rules=pl.default_rules() + [theorem])


def test_a_theorem_proved_from_a_nested_premise_is_citable_with_it():
    theorem = promote(NESTED_PREMISE_THEOREM)
    use = [
        ("1", None, ("declare", declares("A"))),
        ("2", Q, ("premise", declares("Q"))),
        ("3", fl.Implies(prop("A"), Q), ("rule", theorem, ["2"])),
    ]
    assert_valid(use, rules=pl.default_rules() + [theorem])


def test_the_text_exploit_that_used_a_nested_premise_no_longer_works():
    first, second = results_of("""
# 1: Anything follows
## Proof that
### A -> Q
1. Let A, Q be closed formulas. (Declaration)
2. A -> Q. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption for Conditional Introduction)
 2.2. Q. (Premise)
end subproof

# 2
## Proof that
### A -> Q again
1. Let A, Q be closed formulas. (Declaration)
2. A -> Q. (Anything follows)
""")
    assert first[:2] == ("1", True)
    assert second[:2] == ("2", False)
    assert "requires exactly 1 candidate premise" in second[2]


def test_a_declare_line_that_states_a_formula_is_a_premise_of_the_promoted_theorem():
    theorem = promote("""
1. P and Q. (Declare)
2. Q. (Conjunction Elimination from 1)
""")
    assert premises_of(theorem) == [repr(fl.And(P, Q))]


def test_the_text_exploit_that_used_a_declare_line_no_longer_works():
    first, second = results_of("""
# 1: Declared fact
## Proof that
### Q
1. P and Q. (Declare)
2. Q. (Conjunction Elimination from 1)

# 2
## Proof that
### Q for any closed formula Q
1. Let Q be a closed formula. (Declaration)
2. Q. (Declared fact)
""")
    assert first[:2] == ("1", True)
    assert second[:2] == ("2", False)
    assert "requires exactly 1 candidate premise" in second[2]


class _Witness(pl.InferenceRule):
    """Says yes to anything: stands in for a rule that names a witness and
    states what it satisfies (the direct Pairing witness)."""
    name = "Witness"
    premise_arity = 0

    def applies(self, candidates, phi):
        return True


def test_a_witness_line_a_rule_makes_is_a_premise_of_the_promoted_theorem():
    # Line 2 chooses an object `w` and says it is in `a`; nothing derives that.
    entries = [
        ("1", None, ("declare", [pl.Declaration("a", pl.DeclarationKind.OBJECT)])),
        ("2", fl.AtomicFormula("In", [c("w"), c("a")]),
         ("rule", _Witness(), [], [pl.Declaration("w", pl.DeclarationKind.OBJECT)])),
    ]
    proof = pl.Proof(entries, rules=pl.default_rules() + [_Witness()],
                     declarations=[pl.Declaration("In", pl.DeclarationKind.PREDICATE, arity=2)])
    theorem = pl.promote_theorem("A witness exists", proof)
    assert premises_of(theorem) == ["In(w, a)"]


def test_a_proof_with_no_axiom_list_takes_its_axiom_lines_as_hypotheses():
    # With no axiom list the validator accepts any formula as an axiom, so an
    # `(Axiom)` line is only something the proof assumed. (Built by hand: parsed
    # text always arrives with the axioms of the theories it uses.)
    entries = [
        ("1", None, ("declare", declares("P"))),
        ("2", P, ("axiom",)),
        ("3", fl.Or(P, P), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    theorem = pl.promote_theorem("From an assumed axiom", pl.Proof(entries))
    assert premises_of(theorem) == [repr(P)]


def test_an_axiom_of_the_theory_is_not_carried_as_a_premise():
    entries = [
        ("1", None, ("declare", declares("P"))),
        ("2", P, ("axiom",)),
        ("3", fl.Or(P, P), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    theorem = pl.promote_theorem("From the axiom", pl.Proof(entries, axioms=[P]))
    assert theorem.premises == []


def test_a_premise_stated_at_the_top_level_is_still_a_premise():
    theorem = promote("""
1. Let P, Q be closed formulas such that: P. Q. (Premise)
2. P and Q. (Conjunction Introduction from 1, 1)
""")
    assert premises_of(theorem) == [repr(P), repr(Q)]


def test_a_hypothesis_stated_twice_is_one_premise_of_the_promoted_theorem():
    theorem = promote("""
1. Let P be a closed formula such that: P. (Premise)
2. (P or P) -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P or P. (Assumption for Conditional Introduction)
 2.2. P. (Premise)
end subproof
""")
    assert premises_of(theorem) == [repr(P)]


def test_objects_declared_to_be_in_a_set_state_their_membership_as_premises():
    theorem = promote("""
1. Let X be any set, a be in X. (Declaration)
2. In(a, X) or In(a, X). (Disjunction Introduction from 1)
""")
    assert premises_of(theorem) == ["In(a, X)"]
    assert theorem.generalized_names == ["X", "a"]


# ---------------------------------------------------------------------------
# Promotion refuses what it cannot carry: relation properties live in the
# declaration, not in a formula.
# ---------------------------------------------------------------------------

SYMMETRY_PROOF = """
1. Let X be any set, R be a symmetric relation on X. (Declaration)
2. forall a, forall b, (R(a,b) -> R(b,a)). (Universal Generalization from subproof below)
begin subproof
 2.0. let a be arbitrary. (Fresh Variable)
 2.1. forall b, (R(a,b) -> R(b,a)). (Universal Generalization from subproof below)
 begin subproof
  2.1.0. let b be arbitrary. (Fresh Variable)
  2.1.1. R(a,b) -> R(b,a). (Conditional Introduction from subproof below)
  begin subproof
   2.1.1.1. R(a,b). (Assumption for Conditional Introduction)
   2.1.1.2. R(b,a). (Relation Symmetry from 2.1.1.1)
  end subproof
 end subproof
end subproof
"""

PLAIN_RELATION_CLAIMS_SYMMETRY = """
1. Let X be any set, R be a relation on X. (Declaration)
2. forall a, forall b, (R(a,b) -> R(b,a)). (Symmetric relations reverse every pair)
"""


def test_a_theorem_that_relied_on_relation_properties_is_not_promoted():
    entries, _ = pp.parse_proof_text(SYMMETRY_PROOF)
    proof = pl.Proof(entries)
    assert proof.check()[0], "the proof itself is fine; only promoting it is refused"
    with pytest.raises(ValueError, match=r"'R'.*symmetric"):
        pl.promote_theorem("Symmetric relations reverse every pair", proof)


def test_the_text_exploit_that_proved_a_plain_relation_symmetric_no_longer_works(capsys):
    first, second = results_of(f"""
# 1: Symmetric relations reverse every pair
## Proof that
### R(a,b) -> R(b,a) for all a, b
{SYMMETRY_PROOF}
# 2
## Proof that
### a relation with no declared properties reverses every pair
{PLAIN_RELATION_CLAIMS_SYMMETRY}
""")
    assert first[:2] == ("1", True)
    assert second[:2] == ("2", False)
    assert "no rule named 'Symmetric relations reverse every pair'" in second[2]
    assert "was not promoted" in capsys.readouterr().out


def test_a_theorem_about_a_predicate_whose_property_is_a_premise_is_promoted():
    # The workaround the refusal points to: declare a plain binary predicate and
    # state the property as a formula, which the theorem then carries.
    theorem = promote("""
1. Let X be any set, R be a binary predicate such that: forall a, forall b, (R(a,b) -> R(b,a)). (Declaration)
2. Let u, v be in X. (Declaration)
3. R(u,v) -> R(v,u). (Conditional Introduction from subproof below)
begin subproof
 3.1. R(u,v). (Assumption for Conditional Introduction)
 3.2. forall b, (R(u,b) -> R(b,u)). (Universal Instantiation from 1)
 3.3. R(u,v) -> R(v,u). (Universal Instantiation from 3.2)
 3.4. R(v,u). (Modus Ponens from 3.1, 3.3)
end subproof
""")
    assert premises_of(theorem)[0].startswith("(∀a. (∀b.")


def test_a_relation_declared_without_properties_still_refuses_promotion_by_default():
    # Its carrier is structure a rule reads (the relation rules check it), so
    # promotion refuses rather than guess that nothing depends on it.
    entries, _ = pp.parse_proof_text("""
1. Let X be any set, R be a relation on X. (Declaration)
2. Let a be in X. (Declaration)
3. In(a, X) or In(a, X). (Disjunction Introduction from 2)
""")
    with pytest.raises(ValueError, match=r"'R'"):
        pl.promote_theorem("About a plain relation", pl.Proof(entries))
