"""A promoted theorem is a theorem of the theory its proof was written in.

`promote_theorem` turns a checked proof into a rule later proofs may cite. The
rule has to carry everything the proof stood on, or citing it would be a way to
use something the citing proof never had (see todos.txt, item 8):

  * the *conclusion* must be something the proof derived, not a formula the
    caller names;
  * the *generalized names* must be objects the proof declared as "any",
    not the vocabulary it merely mentioned (`EmptySet`);
  * the axioms the proof cited and the rules it used beyond the standard
    logical ones are *requirements*: the theorem is only citable in a proof that
    lists those axioms and allows those rules. A proof written for one caller's
    axiom, or by one caller's rule, must not make that axiom or rule available
    to every proof.

Every refusal here is asserted by label, category and wording, and has a twin
that differs only in what the refusal is about.
"""

import re

import pytest

from .support import c, fl, mp, pl, pp, prop

P = prop("P")
Q = prop("Q")
OBJECT = pl.DeclarationKind.OBJECT


def declares(*names, kind=pl.DeclarationKind.CLOSED_FORMULA):
    return [pl.Declaration(name, kind) for name in names]


def parse(text):
    return pp.parse_formula(text, set())


def theorem_from(text, name="Theorem", **kwargs):
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries)
    ok, err = proof.check_detailed()
    assert ok, str(err)
    return pl.promote_theorem(name, proof, **kwargs)


def cite_in(entries, label, theorem, references=()):
    """Replace line `label` of parsed `entries` with a citation of `theorem`
    (the parser cannot name a theorem it was not told about)."""
    for index, entry in enumerate(entries):
        if isinstance(entry, tuple) and entry[0] == label and entry[1] != "subproof":
            entries[index] = (entry[0], entry[1], ("rule", theorem, list(references)), *entry[3:])
            return entries
    raise AssertionError(f"no line {label!r}")


def check_citation(entries, theorem, **proof_kwargs):
    proof_kwargs.setdefault("rules", pl.default_rules() + [theorem])
    return pl.Proof(entries, **proof_kwargs).check_detailed()


def assert_refused(result, label, *needles):
    ok, err = result
    assert not ok, "the citation was accepted"
    assert err.category == pl.CATEGORY_RULE_MISMATCH, str(err)
    assert err.label == label, str(err)
    for needle in needles:
        assert needle in err.detail, f"{needle!r} not in {err.detail!r}"


def assert_accepted(result):
    ok, err = result
    assert ok, str(err)


# ---------------------------------------------------------------------------
# The conclusion has to be something the proof derived.
# ---------------------------------------------------------------------------

TWO_CONSEQUENCES = """
1. Let P, Q be closed formulas such that: P. Q. (Premise)
2. P and Q. (Conjunction Introduction from 1, 1)
3. P or Q. (Disjunction Introduction from 1)
"""


def test_the_conclusion_defaults_to_the_last_formula_the_proof_derived():
    assert repr(theorem_from(TWO_CONSEQUENCES).conclusion) == repr(parse("P or Q"))


def test_an_explicit_conclusion_may_be_any_formula_the_proof_derived():
    theorem = theorem_from(TWO_CONSEQUENCES, conclusion=parse("P and Q"))
    assert repr(theorem.conclusion) == repr(parse("P and Q"))


def test_an_explicit_conclusion_the_proof_never_derived_is_refused():
    never = parse("Q or P")
    with pytest.raises(ValueError, match=re.escape(f"cannot promote {never!r} as the theorem's conclusion") +
                                         ".*never derived it at the top level"):
        theorem_from(TWO_CONSEQUENCES, conclusion=never)


def test_the_refusal_says_what_the_proof_did_derive():
    with pytest.raises(ValueError) as raised:
        theorem_from(TWO_CONSEQUENCES, conclusion=parse("Q"))
    assert "it derived " + repr(parse("P and Q")) in str(raised.value)
    assert repr(parse("P or Q")) in str(raised.value)


def test_a_premise_is_not_a_conclusion_the_proof_derived():
    with pytest.raises(ValueError, match="never derived it"):
        theorem_from(TWO_CONSEQUENCES, conclusion=parse("P"))


CONDITIONAL_IDENTITY = """
1. Let P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption for Conditional Introduction)
 2.2. P. (Reiteration from 2.1)
end subproof
"""


def test_a_formula_derived_only_inside_a_subproof_is_not_a_conclusion():
    # `P` is derived at 2.2, but only under the assumption `P`.
    with pytest.raises(ValueError, match="never derived it at the top level"):
        theorem_from(CONDITIONAL_IDENTITY, conclusion=parse("P"))
    assert repr(theorem_from(CONDITIONAL_IDENTITY, conclusion=parse("P -> P")).conclusion) == repr(parse("P -> P"))


def test_a_proof_that_derives_nothing_has_no_conclusion_to_promote():
    with pytest.raises(ValueError, match="derives nothing at the top level"):
        theorem_from("""
1. Let P be a closed formula such that: P. (Premise)
""")


# ---------------------------------------------------------------------------
# Only objects the proof declared as "any" can be generalized.
# ---------------------------------------------------------------------------

TWO_OBJECTS = """
1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. a = a. (Reflexivity)
"""


def test_generalized_names_default_to_every_declared_object():
    assert theorem_from(TWO_OBJECTS).generalized_names == ["a", "b"]


def test_generalized_names_may_be_some_of_the_declared_objects_or_none():
    assert theorem_from(TWO_OBJECTS, generalized_names=["a"]).generalized_names == ["a"]
    assert theorem_from(TWO_OBJECTS, generalized_names=[]).generalized_names == []


def test_a_name_listed_twice_is_generalized_once():
    assert theorem_from(TWO_OBJECTS, generalized_names=["b", "b", "a"]).generalized_names == ["b", "a"]


NO_ELEMENT = """
1. Let x be any object. (Declaration)
2. x is not in the empty set. (Set property)
"""


def test_fixed_vocabulary_cannot_be_generalized():
    with pytest.raises(ValueError, match=r"cannot generalize over 'EmptySet'.*\(here: 'x'\)"):
        theorem_from(NO_ELEMENT, generalized_names=["x", "EmptySet"])


def test_an_object_declared_inside_a_subproof_cannot_be_generalized():
    text = """
1. Let a be any object. (Declaration)
2. Let P be a closed formula. (Declaration)
3. P -> a = a. (Conditional Introduction from subproof below)
begin subproof
 3.1. P. (Assumption for Conditional Introduction)
 3.2. Let Y be any object. (Declaration)
 3.3. a = a. (Reflexivity)
end subproof
"""
    with pytest.raises(ValueError, match="cannot generalize over 'Y'"):
        theorem_from(text, generalized_names=["a", "Y"])
    assert theorem_from(text, generalized_names=["a"]).generalized_names == ["a"]


def test_a_name_the_proof_never_declared_cannot_be_generalized():
    with pytest.raises(ValueError, match="cannot generalize over 'z'"):
        theorem_from(TWO_OBJECTS, generalized_names=["a", "z"])


def test_every_foreign_name_is_reported():
    with pytest.raises(ValueError, match="cannot generalize over 'EmptySet', 'z'"):
        theorem_from(NO_ELEMENT, generalized_names=["EmptySet", "x", "z"])


def test_what_was_not_generalized_stays_fixed_when_the_theorem_is_cited():
    theorem = theorem_from(NO_ELEMENT, generalized_names=["x"])

    about_another_object, _ = pp.parse_proof_text("""
1. Let y be any object. (Declaration)
2. y is not in the empty set. (Reiteration from 1)
""")
    assert_accepted(check_citation(cite_in(about_another_object, "2", theorem), theorem))

    about_another_set, _ = pp.parse_proof_text("""
1. Let y be any object. (Declaration)
2. Let Y be any set. (Declaration)
3. y is not in Y. (Reiteration from 1)
""")
    assert_refused(check_citation(cite_in(about_another_set, "3", theorem), theorem), "3")


# ---------------------------------------------------------------------------
# Axioms the proof cited are requirements of the theorem.
# ---------------------------------------------------------------------------

def proof_from_axiom(axiom, axioms):
    """`1. declare Q`, `2. Q (Axiom)`, `3. Q or Q` -- checked against `axioms`."""
    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", axiom, ("axiom",)),
        ("3", fl.Or(axiom, axiom), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    return pl.Proof(entries, axioms=axioms)


def a_use_of(theorem):
    """A proof that states the theorem's conclusion by citing it, with no
    premises, and nothing else."""
    return [
        ("1", None, ("declare", declares("Q"))),
        ("2", fl.Or(Q, Q), ("rule", theorem, [])),
    ]


def test_a_theorem_remembers_the_axioms_its_proof_cited():
    theorem = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))
    assert [repr(axiom) for axiom in theorem.required_axioms] == [repr(Q)]
    assert theorem.premises == []


def test_a_proof_that_cited_no_axiom_and_no_theory_rule_requires_nothing():
    entries = [
        ("1", None, ("declare", declares("P"))),
        ("2", fl.Implies(P, P), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("2.1", P, ("assume",)),
            ("2.2", P, ("rule", pl.ReiterationRule(), ["2.1"])),
        ]),
    ]
    theorem = pl.promote_theorem("Identity", pl.Proof(entries))
    assert theorem.required_axioms == []
    assert theorem.required_rules == []


def test_a_proof_that_lists_the_axiom_may_cite_the_theorem():
    theorem = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))
    assert_accepted(check_citation(a_use_of(theorem), theorem, axioms=[Q]))


def test_a_proof_that_lacks_the_axiom_may_not_cite_the_theorem():
    theorem = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))
    assert_refused(
        check_citation(a_use_of(theorem), theorem, axioms=[P]), "2",
        "the theorem 'From an axiom' was proved using the axiom Q", "does not have",
    )


def test_a_proof_with_no_axiom_list_does_not_have_every_axiom():
    # The validator accepts any formula as an `(Axiom)` line of a proof that
    # was given no axioms; a theorem that rests on one still needs it named.
    theorem = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))
    assert_refused(check_citation(a_use_of(theorem), theorem), "2", "the axiom Q")


def test_the_theorem_applies_nowhere_without_a_proof_around_it():
    theorem = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))
    assert not theorem.applies([], fl.Or(Q, Q))
    assert theorem.applies_in_context([], fl.Or(Q, Q), pl.RuleContext(axioms=[Q], rules=[theorem]))


def test_an_axiom_cited_inside_a_subproof_is_still_a_requirement():
    entries = [
        ("1", None, ("declare", declares("P", "Q"))),
        ("2", fl.Implies(P, Q), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("2.1", P, ("assume",)),
            ("2.2", Q, ("axiom",)),
        ]),
    ]
    theorem = pl.promote_theorem("From a nested axiom", pl.Proof(entries, axioms=[Q]))
    assert [repr(axiom) for axiom in theorem.required_axioms] == [repr(Q)]


def test_the_same_axiom_cited_twice_is_required_once():
    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("axiom",)),
        ("3", Q, ("axiom",)),
        ("4", fl.Or(Q, Q), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    theorem = pl.promote_theorem("Twice", pl.Proof(entries, axioms=[Q]))
    assert len(theorem.required_axioms) == 1


def test_the_validator_lists_each_axiom_the_proof_cited_once():
    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("axiom",)),
        ("3", Q, ("axiom",)),
        ("4", fl.Or(Q, Q), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    validator, ok, err = pl.Proof(entries, axioms=[Q])._validate()
    assert ok, str(err)
    assert [repr(axiom) for axiom in validator.used_axioms] == [repr(Q)]


def test_an_axiom_cited_directly_and_required_by_a_cited_theorem_is_required_once():
    first = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))
    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("axiom",)),
        ("3", fl.Or(Q, Q), ("rule", first, [])),
        ("4", fl.Or(Q, Q), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    second = pl.promote_theorem(
        "Both ways", pl.Proof(entries, axioms=[Q], rules=pl.default_rules() + [first]))
    assert [repr(axiom) for axiom in second.required_axioms] == [repr(Q)]


def test_an_axiom_that_a_theorem_it_cited_required_is_required_too():
    first = pl.promote_theorem("From an axiom", proof_from_axiom(Q, [Q]))

    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", fl.Or(Q, Q), ("rule", first, [])),
        ("3", fl.Or(fl.Or(Q, Q), fl.Or(Q, Q)),
         ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    second = pl.promote_theorem(
        "From a theorem from an axiom",
        pl.Proof(entries, axioms=[Q], rules=pl.default_rules() + [first]),
    )
    assert [repr(axiom) for axiom in second.required_axioms] == [repr(Q)]
    assert second.required_rules == []

    use = [
        ("1", None, ("declare", declares("Q"))),
        ("2", fl.Or(fl.Or(Q, Q), fl.Or(Q, Q)), ("rule", second, [])),
    ]
    assert_refused(check_citation(use, second, axioms=[P]), "2", "the axiom Q")
    assert_accepted(check_citation(use, second, axioms=[Q]))


def test_a_theorem_from_an_axiom_cannot_generalize_over_a_constant_the_axiom_mentions():
    # The axiom is about `a`; a theorem about *any* `a` that needed it would
    # be citable for objects the axiom says nothing about.
    declarations = [pl.Declaration("a", OBJECT), pl.Declaration("A", pl.DeclarationKind.PREDICATE, arity=1)]
    atom = fl.AtomicFormula("A", [c("a")])
    entries = [
        ("1", None, ("declare", [pl.Declaration("a", OBJECT)])),
        ("2", atom, ("axiom",)),
        ("3", fl.Or(atom, atom), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    proof = pl.Proof(entries, axioms=[atom], declarations=[declarations[1]])
    with pytest.raises(ValueError, match=r"cannot generalize over 'a': the theorem requires the axiom A\(a\)"):
        pl.promote_theorem("About a", proof)

    theorem = pl.promote_theorem("About a", proof, generalized_names=[])
    assert theorem.generalized_names == []
    assert [repr(axiom) for axiom in theorem.required_axioms] == ["A(a)"]


def test_an_axiom_that_mentions_no_generalized_constant_does_not_block_generalizing():
    entries = [
        ("1", None, ("declare", [pl.Declaration("a", OBJECT)])),
        ("2", Q, ("axiom",)),
        ("3", fl.Or(Q, Q), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    proof = pl.Proof(entries, axioms=[Q], declarations=declares("Q"))
    assert pl.promote_theorem("Q", proof).generalized_names == ["a"]


# ---------------------------------------------------------------------------
# Rules beyond the standard logical ones are requirements of the theorem.
# ---------------------------------------------------------------------------

class _UnconditionalQ(pl.InferenceRule):
    """A rule a caller supplied: it says Q from nothing."""
    name = "Unconditional Q"
    premise_arity = 0

    def applies(self, candidates, phi):
        return not candidates and pl._ast_eq(phi, Q)


def proof_by_unconditional_q():
    rule = _UnconditionalQ()
    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("rule", rule, [])),
    ]
    return pl.Proof(entries, rules=pl.default_rules() + [rule])


def a_use_of_q(theorem):
    return [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("rule", theorem, [])),
    ]


def test_a_theorem_remembers_the_nonstandard_rules_its_proof_used():
    theorem = pl.promote_theorem("Q outright", proof_by_unconditional_q())
    assert [rule.name for rule in theorem.required_rules] == ["Unconditional Q"]
    assert theorem.premises == []


def test_a_proof_that_allows_the_rule_may_cite_the_theorem():
    theorem = pl.promote_theorem("Q outright", proof_by_unconditional_q())
    assert_accepted(check_citation(
        a_use_of_q(theorem), theorem,
        rules=pl.default_rules() + [theorem, _UnconditionalQ()],
    ))


def test_a_proof_that_does_not_allow_the_rule_may_not_cite_the_theorem():
    theorem = pl.promote_theorem("Q outright", proof_by_unconditional_q())
    assert_refused(
        check_citation(a_use_of_q(theorem), theorem), "2",
        "the theorem 'Q outright' was proved using the rule 'Unconditional Q'", "does not have",
    )


def test_a_theorem_may_need_a_rule_and_an_axiom_at_once():
    rule = _UnconditionalQ()
    entries = [
        ("1", None, ("declare", declares("P", "Q"))),
        ("2", P, ("axiom",)),
        ("3", Q, ("rule", rule, [])),
        ("4", fl.And(P, Q), ("rule", pl.ConjunctionIntroductionRule(), ["2", "3"])),
    ]
    theorem = pl.promote_theorem(
        "Both", pl.Proof(entries, axioms=[P], rules=pl.default_rules() + [rule]))
    assert [r.name for r in theorem.required_rules] == ["Unconditional Q"]
    assert [repr(a) for a in theorem.required_axioms] == [repr(P)]

    use = [
        ("1", None, ("declare", declares("P", "Q"))),
        ("2", fl.And(P, Q), ("rule", theorem, [])),
    ]
    detail = check_citation(use, theorem)[1].detail
    assert "the rule 'Unconditional Q' and the axiom P" in detail


def test_a_rule_used_only_inside_a_subproof_is_still_a_requirement():
    rule = _UnconditionalQ()
    entries = [
        ("1", None, ("declare", declares("P", "Q"))),
        ("2", fl.Implies(P, Q), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("2.1", P, ("assume",)),
            ("2.2", Q, ("rule", rule, [])),
        ]),
    ]
    theorem = pl.promote_theorem("Nested", pl.Proof(entries, rules=pl.default_rules() + [rule]))
    assert [r.name for r in theorem.required_rules] == ["Unconditional Q"]


def test_a_rule_used_by_a_rule_below_subproof_is_a_requirement():
    class _FromSubproof(pl.InferenceRule):
        name = "From a subproof"
        premise_arity = 1

        def applies(self, candidates, phi):
            return len(candidates) == 1 and isinstance(candidates[0], pl.SubproofRecord) and pl._ast_eq(phi, Q)

    rule = _FromSubproof()
    entries = [
        ("1", None, ("declare", declares("P", "Q"))),
        ("2", Q, ("rule_below", rule), [
            ("2.1", P, ("assume",)),
            ("2.2", P, ("rule", pl.ReiterationRule(), ["2.1"])),
        ]),
    ]
    theorem = pl.promote_theorem("Via subproof", pl.Proof(entries, rules=pl.default_rules() + [rule]))
    assert [r.name for r in theorem.required_rules] == ["From a subproof"]


def test_the_standard_logical_rules_are_never_requirements():
    entries = [
        ("1", None, ("declare", declares("P", "Q"))),
        ("2", fl.Implies(P, P), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("2.1", P, ("assume",)),
            ("2.2", P, ("rule", pl.ReiterationRule(), ["2.1"])),
        ]),
    ]
    theorem = pl.promote_theorem("Identity", pl.Proof(entries))
    assert theorem.required_rules == []

    # ... so a proof restricted to its own few rules can still cite it.
    use = [
        ("1", None, ("declare", declares("P"))),
        ("2", fl.Implies(P, P), ("rule", theorem, [])),
    ]
    assert_accepted(pl.Proof(use, rules=[theorem]).check_detailed())


def test_a_rule_a_theorem_it_cited_required_is_required_too_and_the_theorem_is_not():
    first = pl.promote_theorem("Q outright", proof_by_unconditional_q())
    rule = _UnconditionalQ()

    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("rule", first, [])),
        ("3", fl.Or(Q, Q), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    second = pl.promote_theorem(
        "Q or Q",
        pl.Proof(entries, rules=pl.default_rules() + [first, rule]),
    )
    assert [r.name for r in second.required_rules] == ["Unconditional Q"]

    use = [
        ("1", None, ("declare", declares("Q"))),
        ("2", fl.Or(Q, Q), ("rule", second, [])),
    ]
    assert_refused(check_citation(use, second), "2", "the rule 'Unconditional Q'")
    # `first` is not needed where the rule is: the second theorem stands alone.
    assert_accepted(check_citation(use, second, rules=pl.default_rules() + [second, rule]))


def test_a_rule_needed_directly_and_through_a_cited_theorem_is_required_once():
    first = pl.promote_theorem("Q outright", proof_by_unconditional_q())
    rule = _UnconditionalQ()
    entries = [
        ("1", None, ("declare", declares("Q"))),
        ("2", Q, ("rule", first, [])),
        ("3", Q, ("rule", rule, [])),
        ("4", fl.Or(Q, Q), ("rule", pl.DisjunctionIntroductionRule(), ["2"])),
    ]
    second = pl.promote_theorem(
        "Both ways", pl.Proof(entries, rules=pl.default_rules() + [first, rule]))
    assert [r.name for r in second.required_rules] == ["Unconditional Q"]


def test_a_requirement_is_matched_by_rule_type_like_every_citation():
    # `allows_rule` is the validator's own test for a citation.
    context = pl.RuleContext(rules=[_UnconditionalQ()])
    assert context.allows_rule(_UnconditionalQ())
    assert not context.allows_rule(pl.ReiterationRule())
    assert not pl.RuleContext().allows_rule(_UnconditionalQ())


def test_a_context_lists_the_axioms_it_was_given_and_no_others():
    context = pl.RuleContext(axioms=[Q])
    assert context.lists_axiom(Q)
    assert not context.lists_axiom(P)
    assert not pl.RuleContext().lists_axiom(Q)


# ---------------------------------------------------------------------------
# Theories supply the requirements of the proofs written in them.
# ---------------------------------------------------------------------------

def test_a_theorem_proved_from_a_theorys_axioms_is_citable_in_the_same_theory():
    results = mp.run_multi_proof_file("""
# 1: Zero is an integer
## Proof that
### then Int(Zero).

1. Nat(Zero). (Axiom)
2. forall x, (Nat(x) -> Int(x)). (Axiom)
3. Nat(Zero) -> Int(Zero). (Universal Instantiation from 2)
4. Int(Zero). (Modus Ponens from 1, 3)

# 2: Zero is an integer, cited
## Proof that
### then Int(Zero).

1. Int(Zero). (Zero is an integer)
""")
    assert [(number, ok) for number, _expected, ok, _message, _crashed in results] == [("1", True), ("2", True)]


def test_a_theorem_proved_from_a_theorys_axioms_records_them():
    theorem = theorem_from("""
1. Nat(Zero). (Axiom)
2. forall x, (Nat(x) -> Int(x)). (Axiom)
3. Nat(Zero) -> Int(Zero). (Universal Instantiation from 2)
4. Int(Zero). (Modus Ponens from 1, 3)
""")
    assert [repr(axiom) for axiom in theorem.required_axioms] == ["Nat(Zero)", "(∀x. (Nat(x) → Int(x)))"]
    assert theorem.premises == []


def test_a_theorem_proved_with_a_theorys_rule_records_it_and_is_citable_where_the_rule_is():
    theorem = theorem_from("""
1. Let x be any object. (Declaration)
2. x is not in the empty set. (Set property)
""")
    assert [type(rule).__name__ for rule in theorem.required_rules] == ["EmptySetPropertyRule"]

    entries, _ = pp.parse_proof_text("""
1. Let y be any object. (Declaration)
2. y is not in the empty set. (Reiteration from 1)
""")
    # The parsed proof brings the set theory rules with it ...
    assert_accepted(check_citation(cite_in(entries, "2", theorem), theorem))

    # ... a proof assembled without them does not have the rule.
    by_hand = [
        ("1", None, ("declare", [pl.Declaration("y", OBJECT)])),
        ("2", fl.Not(fl.AtomicFormula("In", [c("y"), c("EmptySet")])), ("rule", theorem, [])),
    ]
    assert_refused(
        check_citation(by_hand, theorem, declarations=[
            pl.Declaration("In", pl.DeclarationKind.PREDICATE, arity=2),
            pl.Declaration("EmptySet", pl.DeclarationKind.OBJECT),
        ]),
        "2", "the rule 'EmptySetProperty'",
    )
