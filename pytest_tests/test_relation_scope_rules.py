"""Relation-property rules read the declaration visible at the line they justify.

A relation declared inside a subproof carries its carrier and properties in
that subproof and in its descendants, and nowhere else, like every other
declaration (todos.txt, item 7). These tests pin that contract from both
sides: a local declaration is usable where it is visible, and a declaration
that is not visible -- a sibling's, one from a subproof that has closed --
never lends its properties to another relation that happens to share its name.

Every refusal checked here must come from the relation rule itself
(`CATEGORY_RULE_MISMATCH` at the line that cites it), not from a parse error or
an unrelated scope failure, so each one sits next to the acceptance that shows
the same line would have passed with the right declaration in scope.
"""

import importlib

import pytest

from .support import pp, pl

dmc = importlib.import_module("SyLoPy.source.DiscreteMathCore")


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def assert_refused_by(text, label, rule_name):
    ok, err = check(text)
    assert not ok, f"expected a refusal at line {label}"
    assert err is not None
    assert err.label == label, err
    assert err.category == pl.CATEGORY_RULE_MISMATCH, err
    assert f"'{rule_name}' does not justify" in err.detail, err


def article(word):
    return "an" if word[0] in "aeiou" else "a"


def in_subproof(*body):
    """`P -> P`, proved by a subproof whose lines 2.2, 2.3, ... are `body`.

    The root declares only the formula letter, so everything `body` declares
    is local to the subproof.
    """
    lines = [
        "1. Let P be a closed formula. (Declaration)",
        "2. P -> P. (Conditional Introduction from subproof below)",
        "begin subproof",
        " 2.1. P. (Assumption)",
    ]
    for number, line in enumerate(body, start=2):
        lines.append(f" 2.{number}. {line}")
    lines.append(f" 2.{len(body) + 2}. P. (Reiteration from 2.1)")
    lines.append("end subproof")
    return "\n".join(lines) + "\n"


# (property, members and premises the declaration line states, conclusion,
#  rule citation, the name the validator reports for the rule)
RULE_CASES = [
    ("reflexive", "a be in X", "R(a,a)",
     "Relation Reflexivity from 2.2", "RelationReflexivity"),
    ("irreflexive", "a be in X", "not R(a,a)",
     "Relation Irreflexivity from 2.2", "RelationIrreflexivity"),
    ("symmetric", "a, b be in X, R(a,b)", "R(b,a)",
     "Relation Symmetry from 2.2", "RelationSymmetry"),
    ("antisymmetric", "a, b be in X, R(a,b) and R(b,a)", "a = b",
     "Relation Antisymmetry from 2.2, 2.2", "RelationAntisymmetry"),
    ("asymmetric", "a, b be in X, R(a,b)", "not R(b,a)",
     "Relation Asymmetry from 2.2", "RelationAsymmetry"),
    ("transitive", "a, b, c be in X, R(a,b) and R(b,c)", "R(a,c)",
     "Relation Transitivity from 2.2, 2.2", "RelationTransitivity"),
    ("total", "a, b be in X", "R(a,b) or R(b,a)",
     "Relation Totality from 2.2, 2.2", "RelationTotality"),
]

# A property that none of the seven rules above rests on, whichever rule is
# being tried: declaring it must not license any of them.
DECOY_FOR = {
    "reflexive": "symmetric",
    "irreflexive": "reflexive",
    "symmetric": "reflexive",
    "antisymmetric": "symmetric",
    "asymmetric": "symmetric",
    "transitive": "symmetric",
    "total": "symmetric",
}


def local_relation_proof(property_word, members, conclusion, citation):
    return in_subproof(
        f"Let X be any set, R be {article(property_word)} {property_word} relation on X, "
        f"{members}. (Declaration)",
        f"{conclusion}. ({citation})",
    )


# --------------------------------------------------------------------
# A relation declared in a subproof is usable in that subproof.
# --------------------------------------------------------------------

@pytest.mark.parametrize(
    ("property_word", "members", "conclusion", "citation", "rule_name"),
    RULE_CASES,
    ids=[case[0] for case in RULE_CASES],
)
def test_a_relation_declared_in_a_subproof_uses_its_own_property_there(
    property_word, members, conclusion, citation, rule_name
):
    ok, err = check(local_relation_proof(property_word, members, conclusion, citation))
    assert ok, err

    # The same line with a relation that lacks the property is refused by the
    # rule: it is the declaration in scope that decides, not the mere presence
    # of some local relation named R.
    decoy = DECOY_FOR[property_word]
    assert_refused_by(
        local_relation_proof(decoy, members, conclusion, citation), "2.3", rule_name
    )


@pytest.mark.parametrize(
    ("property_word", "conclusion", "citation", "rule_name"),
    [
        ("reflexive", "R(a,a)", "Relation Reflexivity from 2.2", "RelationReflexivity"),
        ("irreflexive", "not R(a,a)", "Relation Irreflexivity from 2.2", "RelationIrreflexivity"),
    ],
)
def test_a_local_relation_is_restricted_to_its_declared_carrier(
    property_word, conclusion, citation, rule_name
):
    right = in_subproof(
        f"Let X be any set, Y be any set, R be {article(property_word)} {property_word} "
        f"relation on X, a be in X. (Declaration)",
        f"{conclusion}. ({citation})",
    )
    ok, err = check(right)
    assert ok, err

    wrong = right.replace("a be in X.", "a be in Y.")
    assert wrong != right
    assert_refused_by(wrong, "2.3", rule_name)


def test_a_local_totality_is_restricted_to_its_declared_carrier():
    right = in_subproof(
        "Let X be any set, Y be any set, R be a total relation on X, a, b be in X. (Declaration)",
        "R(a,b) or R(b,a). (Relation Totality from 2.2, 2.2)",
    )
    ok, err = check(right)
    assert ok, err

    wrong = right.replace("a, b be in X.", "a, b be in Y.")
    assert wrong != right
    assert_refused_by(wrong, "2.3", "RelationTotality")


# --------------------------------------------------------------------
# Visible in descendants; not outside, and not in a sibling.
# --------------------------------------------------------------------

def test_a_relation_declared_in_a_subproof_is_visible_in_its_nested_subproofs():
    text = """
1. Let P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)
 2.3. P -> P. (Conditional Introduction from subproof below)
 begin subproof
  2.3.1. P. (Assumption)
  2.3.2. P -> P. (Conditional Introduction from subproof below)
  begin subproof
   2.3.2.1. P. (Assumption)
   2.3.2.2. R(a,a). (Relation Reflexivity from 2.2)
   2.3.2.3. P. (Reiteration from 2.3.2.1)
  end subproof
  2.3.3. P. (Reiteration from 2.3.1)
 end subproof
 2.4. P. (Reiteration from 2.1)
end subproof
"""
    ok, err = check(text)
    assert ok, err


def test_a_relation_declared_in_a_nested_subproof_is_not_the_enclosing_ones():
    # The enclosing subproof's R is symmetric; the nested subproof's R is a
    # different, reflexive relation. The rule at 2.3.2 may use the nested
    # one's reflexivity, and the rule at 2.5 -- back in the enclosing
    # subproof, where only the symmetric R is visible -- may not.
    template = """
1. Let P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let X be any set, a be in X. (Declaration)
 2.3. P -> P. (Conditional Introduction from subproof below)
 begin subproof
  2.3.1. P. (Assumption)
  2.3.2. Let R be a reflexive relation on X. (Declaration)
  2.3.3. R(a,a). (Relation Reflexivity from 2.2)
  2.3.4. P. (Reiteration from 2.3.1)
 end subproof
 2.4. Let R be a symmetric relation on X. (Declaration)
 2.5. {conclusion}. ({citation})
 2.6. P. (Reiteration from 2.1)
end subproof
"""
    # `R` is declared again at 2.4 only after the nested subproof has closed,
    # which is what lets the name be reused at all.
    refused = template.format(conclusion="R(a,a)", citation="Relation Reflexivity from 2.2")
    assert_refused_by(refused, "2.5", "RelationReflexivity")

    # Without the reflexivity attempt the same proof is accepted.
    accepted = template.format(conclusion="P -> P", citation="Reiteration from 2.3")
    ok, err = check(accepted)
    assert ok, err


def test_a_closed_subproofs_relation_does_not_license_a_later_one_of_the_same_name():
    # R is reflexive inside the subproof (accepted at 2.3) and merely
    # symmetric at the root afterwards, where reflexivity must be refused.
    # A table of declarations keyed by name, shared across scopes, gets one of
    # the two lines wrong whichever way it resolves the clash.
    template = """
1. Let X be any set, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a reflexive relation on X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 1)
 2.4. P. (Reiteration from 2.1)
end subproof
3. Let R be a symmetric relation on X. (Declaration)
4. {conclusion}. ({citation})
"""
    refused = template.format(conclusion="R(a,a)", citation="Relation Reflexivity from 1")
    assert_refused_by(refused, "4", "RelationReflexivity")

    accepted = template.format(conclusion="P -> P", citation="Reiteration from 2")
    ok, err = check(accepted)
    assert ok, err


SIBLINGS = """
1. Let X be any set, a, b be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be {first} relation on X. (Declaration)
 2.3. {first_line}
 2.4. P. (Reiteration from 2.1)
end subproof
3. P -> P. (Conditional Introduction from subproof below)
begin subproof
 3.1. P. (Assumption)
 3.2. Let R be {second} relation on X. (Declaration)
 3.3. {second_line}
 3.4. P. (Reiteration from 3.1)
end subproof
"""

REFLEXIVITY = "R(a,a). (Relation Reflexivity from 1)"
SYMMETRY_OF_NOTHING = "P. (Reiteration from {p})"


def siblings(first, first_line, second, second_line):
    return SIBLINGS.format(first=first, first_line=first_line,
                           second=second, second_line=second_line)


def test_siblings_may_each_declare_their_own_relation_and_use_its_properties():
    ok, err = check(siblings(
        "a reflexive", REFLEXIVITY,
        "a symmetric", "P. (Reiteration from 3.1)",
    ))
    assert ok, err

    ok, err = check(siblings(
        "a symmetric", "P. (Reiteration from 2.1)",
        "a reflexive", REFLEXIVITY,
    ))
    assert ok, err


def test_a_later_sibling_does_not_inherit_the_property_an_earlier_one_declared():
    assert_refused_by(
        siblings("a reflexive", REFLEXIVITY, "a symmetric", REFLEXIVITY),
        "3.3", "RelationReflexivity",
    )


def test_an_earlier_sibling_does_not_borrow_the_property_a_later_one_declares():
    assert_refused_by(
        siblings("a symmetric", REFLEXIVITY, "a reflexive", REFLEXIVITY),
        "2.3", "RelationReflexivity",
    )


# --------------------------------------------------------------------
# The other ways a subproof can be opened.
# --------------------------------------------------------------------

def test_a_relation_declared_in_a_proof_by_cases_branch_stays_in_that_branch():
    template = """
1. Let A, B, C be closed formulas such that: A or B. if A then C. B -> C. (Premise)
2. C. (Proof by Cases from 1, subproofs below)
begin subproof
 2.1. A. (Case)
 2.2. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 2.2)
 2.4. C. (Modus Ponens from 1, 2.1)
end subproof
begin subproof
 2.1. B. (Case)
 2.2. Let X be any set, R be a {second} relation on X, a be in X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 2.2)
 2.4. C. (Modus Ponens from 1, 2.1)
end subproof
"""
    ok, err = check(template.format(second="reflexive"))
    assert ok, err

    # The second branch's R is its own: the first branch's reflexivity is not
    # carried over to it.
    ok, err = check(template.format(second="symmetric"))
    assert not ok
    assert err.label == "2.3"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert "'RelationReflexivity' does not justify" in err.detail


def test_a_relation_declared_inside_a_fresh_variable_subproof_is_usable_there():
    text = """
1. forall c, (c = c and c = c). (Universal Generalization from subproof below)
begin subproof
 1.0. let c be arbitrary. (Fresh Variable)
 1.1. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)
 1.2. R(a,a). (Relation Reflexivity from 1.1)
 1.3. c = c. (Reflexivity)
 1.4. c = c and c = c. (Conjunction Introduction from 1.3, 1.3)
end subproof
"""
    ok, err = check(text)
    assert ok, err


def test_a_root_relation_is_usable_inside_every_kind_of_subproof():
    text = """
1. Let X be any set, R be a reflexive relation on X, a be in X, A, B, C be closed formulas. (Declaration)
2. A -> A. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption)
 2.2. R(a,a). (Relation Reflexivity from 1)
 2.3. A. (Reiteration from 2.1)
end subproof
3. forall c, (c = c and c = c). (Universal Generalization from subproof below)
begin subproof
 3.0. let c be arbitrary. (Fresh Variable)
 3.1. R(a,a). (Relation Reflexivity from 1)
 3.2. c = c. (Reflexivity)
 3.3. c = c and c = c. (Conjunction Introduction from 3.2, 3.2)
end subproof
"""
    ok, err = check(text)
    assert ok, err


def test_a_subproof_cannot_redeclare_a_relation_of_an_enclosing_scope():
    # The kernel forbids shadowing along an enclosing chain; a nested
    # declaration of `R` is therefore not a way to give R new properties.
    text = """
1. Let X be any set, R be a symmetric relation on X, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a reflexive relation on X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 1)
 2.4. P. (Reiteration from 2.1)
end subproof
"""
    with pytest.raises(pp.ElaborationError, match="already declared"):
        pp.parse_proof_text(text)


# --------------------------------------------------------------------
# The mechanism: the rules hold no table, the context holds the scope.
# --------------------------------------------------------------------

def test_the_rule_context_answers_with_the_declaration_in_scope():
    root = pl.DeclarationScope()
    reflexive = pl.Declaration(
        "R", pl.DeclarationKind.PREDICATE, arity=2,
        metadata=(("carrier", "X"), ("properties", ("reflexive",))),
    )
    root.declare(reflexive)
    child = root.child()

    assert pl.RuleContext(declarations=root).declaration("R") is reflexive
    assert pl.RuleContext(declarations=child).declaration("R") is reflexive

    other = pl.Declaration("S", pl.DeclarationKind.PREDICATE, arity=2)
    child.declare(other)
    assert pl.RuleContext(declarations=child).declaration("S") is other
    assert pl.RuleContext(declarations=root).declaration("S") is None


def test_the_rule_context_outside_a_proof_has_no_declarations():
    assert pl.RuleContext().declaration("R") is None


@pytest.mark.parametrize(
    "rule",
    [
        dmc.RelationReflexivityRule, dmc.RelationIrreflexivityRule,
        dmc.RelationSymmetryRule, dmc.RelationAntisymmetryRule,
        dmc.RelationAsymmetryRule, dmc.RelationTransitivityRule,
        dmc.RelationTotalityRule,
    ],
)
def test_a_relation_rule_asked_outside_a_proof_finds_no_declared_property(rule):
    # Called directly, with no proof around it, there is no scope to read a
    # relation's properties from, so the rule has to say no -- it must not
    # fall back to anything remembered from an earlier proof.
    x = pl.tl.ConstantTerm("a", "a")
    y = pl.tl.ConstantTerm("b", "b")
    member = pl.fl.AtomicFormula("In", [x, pl.tl.ConstantTerm("X", "X")])
    atom = pl.fl.AtomicFormula("R", [x, x])
    flipped = pl.fl.AtomicFormula("R", [y, x])
    pair = pl.fl.AtomicFormula("R", [x, y])
    rule = rule()
    assert not rule.applies([member], atom)
    assert not rule.applies([member], pl.fl.Not(atom))
    assert not rule.applies([pair], flipped)
    assert not rule.applies([pair], pl.fl.Not(flipped))
    assert not rule.applies([pair, flipped], pl.fl.Equals(x, y))
    assert not rule.applies([pair, flipped], pair)
    assert not rule.applies([member, member], pl.fl.Or([pair, flipped]))


def test_the_relation_rules_are_part_of_the_discrete_math_environment():
    names = [type(rule).__name__ for rule in dmc.DISCRETE_MATH_ENVIRONMENT.rules]
    assert sorted(names) == sorted([
        "RelationReflexivityRule", "RelationIrreflexivityRule",
        "RelationSymmetryRule", "RelationAntisymmetryRule",
        "RelationAsymmetryRule", "RelationTransitivityRule",
        "RelationTotalityRule",
    ])


def test_elaboration_does_not_build_relation_rules_per_proof():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, R be a reflexive relation on X, a be in X. (Declaration)\n"
        "2. R(a,a). (Relation Reflexivity from 1)\n"
    )
    reflexivity = [rule for rule in entries.required_rules
                   if isinstance(rule, dmc.RelationReflexivityRule)]
    assert len(reflexivity) == 1
    assert not hasattr(reflexivity[0], "relation_properties")


# --------------------------------------------------------------------
# What a relation rule accepts as "the declaration of R".
# --------------------------------------------------------------------

def _reflexivity_with(declaration):
    scope = pl.DeclarationScope()
    scope.declare(declaration)
    a = pl.tl.ConstantTerm("a", "a")
    member = pl.fl.AtomicFormula("In", [a, pl.tl.ConstantTerm("X", "X")])
    atom = pl.fl.AtomicFormula("R", [a, a])
    context = pl.RuleContext(declarations=scope)
    return dmc.RelationReflexivityRule().applies_in_context([member], atom, context)


_REFLEXIVE_ON_X = (("carrier", "X"), ("properties", ("reflexive",)))


def test_a_relation_rule_reads_the_carrier_and_properties_from_the_declaration():
    kind = pl.DeclarationKind
    assert _reflexivity_with(pl.Declaration("R", kind.PREDICATE, arity=2, metadata=_REFLEXIVE_ON_X))


@pytest.mark.parametrize(
    "declaration",
    [
        pl.Declaration("R", pl.DeclarationKind.FUNCTION, arity=2, metadata=_REFLEXIVE_ON_X),
        pl.Declaration("R", pl.DeclarationKind.OBJECT, metadata=_REFLEXIVE_ON_X),
        pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=1, metadata=_REFLEXIVE_ON_X),
        pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=None, metadata=_REFLEXIVE_ON_X),
        pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=2),
        pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=2,
                       metadata=(("carrier", "X"), ("properties", ("symmetric",)))),
        pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=2,
                       metadata=(("carrier", "Y"), ("properties", ("reflexive",)))),
        pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=2,
                       metadata=(("properties", ("reflexive",)),)),
    ],
    ids=["function", "object", "unary", "no-arity", "no-metadata",
         "other-property", "other-carrier", "no-carrier"],
)
def test_a_relation_rule_needs_a_binary_predicate_with_the_property_and_the_carrier(declaration):
    assert not _reflexivity_with(declaration)


def test_a_relation_rule_ignores_metadata_entries_that_are_not_key_value_pairs():
    declaration = pl.Declaration(
        "R", pl.DeclarationKind.PREDICATE, arity=2,
        metadata=("stray", ("carrier", "X", "extra"), *_REFLEXIVE_ON_X),
    )
    assert _reflexivity_with(declaration)


def test_a_relation_declared_in_a_subproof_is_undeclared_after_it_closes():
    # Visibility, as the kernel's own symbol check sees it: after the subproof
    # the relation is not just without properties, it is not there at all.
    ok, err = check("""
1. Let X be any set, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a reflexive relation on X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 1)
 2.4. P. (Reiteration from 2.1)
end subproof
3. R(a,a). (Premise)
""")
    assert not ok
    assert err.label == "3"
    assert err.category == pl.CATEGORY_UNDECLARED_SYMBOL
