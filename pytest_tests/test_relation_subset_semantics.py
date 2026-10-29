"""A relation on X is a subset of X x X (owner decision, 2026-10-29; issue #136).

`Let R be a ... relation on X` declares R as a relation on X in the usual
sense, so R(a, b) can hold only for members of X. That settles which relation
rules have to be told about X:

* Symmetry, antisymmetry, asymmetry and transitivity start from facts
  R(a, b). Such a fact already puts a and b in X, so these rules read the
  declared property and nothing else: they apply whichever set the terms were
  declared in, and take no membership premise.
* Reflexivity, irreflexivity and totality produce an R-fact, or its denial,
  from membership. They cite that membership, and it must be membership in the
  declared carrier: R reflexive on X says nothing about the members of Y.

Every acceptance here is paired with a refusal by the same rule at the same
line, so the rule is shown to be reading something: for the first group, the
declaration (a relation without the property is refused); for the second, the
carrier (membership in another set is refused). Each refusal must come from the
relation rule itself (`CATEGORY_RULE_MISMATCH` at the line that cites it), not
from a parse error or an unrelated scope failure.
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


def relation_proof(property_word, members, conclusion, citation):
    """A relation R with the property on X, then one line justified by a rule.

    `members` is the rest of the declaration line: the terms, with the set they
    are declared in, and the R-facts they carry. Y is declared too, so a term
    can be a member of another set.
    """
    return (
        f"1. Let X be any set, Y be any set, R be {article(property_word)} {property_word} "
        f"relation on X, {members}. (Declaration)\n"
        f"2. {conclusion}. ({citation})\n"
    )


# --------------------------------------------------------------------
# Rules that start from an R-fact: the declared property is all they read.
# (property, terms and facts the declaration states, conclusion, citation,
#  the name the validator reports for the rule, a property that is not it)
# --------------------------------------------------------------------

FACT_RULES = [
    ("symmetric", "a, b be in {where}, R(a,b)", "R(b,a)",
     "Relation Symmetry from 1", "RelationSymmetry", "reflexive"),
    ("antisymmetric", "a, b be in {where}, R(a,b) and R(b,a)", "a = b",
     "Relation Antisymmetry from 1, 1", "RelationAntisymmetry", "symmetric"),
    ("asymmetric", "a, b be in {where}, R(a,b)", "not R(b,a)",
     "Relation Asymmetry from 1", "RelationAsymmetry", "symmetric"),
    ("transitive", "a, b, c be in {where}, R(a,b) and R(b,c)", "R(a,c)",
     "Relation Transitivity from 1, 1", "RelationTransitivity", "symmetric"),
]
FACT_IDS = [case[0] for case in FACT_RULES]


@pytest.mark.parametrize(
    ("property_word", "members", "conclusion", "citation", "rule_name", "decoy"),
    FACT_RULES, ids=FACT_IDS,
)
@pytest.mark.parametrize("where", ["X", "Y"], ids=["terms in the carrier", "terms in another set"])
def test_a_rule_that_starts_from_a_fact_needs_no_membership_in_the_carrier(
    property_word, members, conclusion, citation, rule_name, decoy, where
):
    members = members.format(where=where)
    ok, err = check(relation_proof(property_word, members, conclusion, citation))
    assert ok, err

    # The same line is refused when the relation is declared without the
    # property: the acceptance above is the declaration's, not a loose rule's.
    assert_refused_by(relation_proof(decoy, members, conclusion, citation), "2", rule_name)


@pytest.mark.parametrize(
    ("property_word", "members", "conclusion", "citation", "rule_name", "decoy"),
    FACT_RULES, ids=FACT_IDS,
)
def test_a_rule_that_starts_from_a_fact_needs_no_set_for_its_terms(
    property_word, members, conclusion, citation, rule_name, decoy
):
    # The terms are objects that no declaration puts in any set: R(a, b) is
    # all the rule is given about them.
    members = members.format(where="X").replace("be in X", "be objects")
    assert "objects" in members
    ok, err = check(relation_proof(property_word, members, conclusion, citation))
    assert ok, err
    assert_refused_by(relation_proof(decoy, members, conclusion, citation), "2", rule_name)


# --------------------------------------------------------------------
# Rules that start from membership: it must be membership in the carrier.
# --------------------------------------------------------------------

MEMBERSHIP_RULES = [
    ("reflexive", "a be in {where}", "R(a,a)",
     "Relation Reflexivity from 1", "RelationReflexivity"),
    ("irreflexive", "a be in {where}", "not R(a,a)",
     "Relation Irreflexivity from 1", "RelationIrreflexivity"),
    ("total", "a, b be in {where}", "R(a,b) or R(b,a)",
     "Relation Totality from 1, 1", "RelationTotality"),
]


@pytest.mark.parametrize(
    ("property_word", "members", "conclusion", "citation", "rule_name"),
    MEMBERSHIP_RULES, ids=[case[0] for case in MEMBERSHIP_RULES],
)
def test_a_rule_that_starts_from_membership_needs_membership_in_the_carrier(
    property_word, members, conclusion, citation, rule_name
):
    ok, err = check(relation_proof(property_word, members.format(where="X"), conclusion, citation))
    assert ok, err

    # Only the set the terms are declared in differs.
    assert_refused_by(
        relation_proof(property_word, members.format(where="Y"), conclusion, citation),
        "2", rule_name,
    )


# --------------------------------------------------------------------
# The two groups are the whole of the theory's relation rules.
# --------------------------------------------------------------------

def test_every_relation_rule_is_in_exactly_one_of_the_two_groups():
    in_fact_group = {case[4] for case in FACT_RULES}
    in_membership_group = {case[4] for case in MEMBERSHIP_RULES}
    declared = {rule.name for rule in dmc.DISCRETE_MATH_ENVIRONMENT.rules}
    assert in_fact_group.isdisjoint(in_membership_group)
    # A relation rule added later has to be put in one group, which means
    # deciding whether it reads the carrier.
    assert declared == in_fact_group | in_membership_group
