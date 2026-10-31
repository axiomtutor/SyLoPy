"""A theory can close its axiom list (owner decision, 2026-10-30).

An `(Axiom)` line states a formula that the proof was given as an axiom. What
"given" means depends on the list the proof is checked against:

* A proof with no list at all -- no axioms, and no theory that has any -- takes
  any formula as an axiom. That is the bare proof, and it stays.
* A proof with a list may state only what the list holds. A non-empty list
  closes itself; no flag is needed for it.
* A theory whose axioms are all cited by name has no formula to put in the
  list, and must not fall back on the first case because the list is empty.
  `TheoryEnvironment.axioms_closed` says that the empty list is a list.

Set theory is the first such theory. Its four axioms (Pairing, Union, Power
Set, Infinity) are cited by name -- `Axiom of pairing` and so on -- and are no
longer also cited by restating them with `(Axiom)`. Closing the list is what
makes that retirement sound: emptying `SET_AXIOMS` alone would have turned
`(Axiom)` into "any formula" in every set-theory proof.

A refused `(Axiom)` line says which rules of the proof justify the formula
outright, so that someone who restates an axiom is told what to cite.

Every acceptance below is paired with the refusal of the same line in the
sibling case, so that a check that stopped reading the list would show.
"""

import importlib
import re
from pathlib import Path

import pytest

from SyLoPy.source.ProofElaboration import ElaboratedEntries, TheoryEnvironment

from .support import fl, mp, pl, pp, st, tl

nt_theory = importlib.import_module("SyLoPy.source.NumberTheory")


# --------------------------------------------------------------------
# A small theory to close and open
# --------------------------------------------------------------------

OBJECT = pl.Declaration("someObject", pl.DeclarationKind.OBJECT)
PREDICATES = [pl.Declaration(name, pl.DeclarationKind.PREDICATE, arity=1) for name in ("Listed", "Unlisted")]
SOME = tl.ConstantTerm("someObject", "someObject")
LISTED = fl.AtomicFormula("Listed", [SOME])
UNLISTED = fl.AtomicFormula("Unlisted", [SOME])
LISTED_AXIOM = "1. Listed(someObject). (Axiom)\n"
UNLISTED_AXIOM = "1. Unlisted(someObject). (Axiom)\n"


def theory(**fields):
    return TheoryEnvironment(name="closed axiom list fixture", declarations=[OBJECT, *PREDICATES], **fields)


def check(text, environment, **arguments):
    return pp.check_proof_text(text, environment=environment, **arguments)


def assert_refused_as_unregistered(result, label="1"):
    ok, err = result
    assert not ok
    assert err is not None
    assert err.label == label, err
    assert err.category == pl.CATEGORY_UNREGISTERED_FORMULA, err
    return err.detail


class AcceptsOne(pl.InferenceRule):
    """A rule with nothing to cite that justifies one formula, and says so."""

    premise_arity = 0

    def __init__(self, name, formula, citation=None):
        self.name = name
        self.formula = formula
        self.citation = citation

    def applies(self, candidates, phi):
        return not candidates and pl._ast_eq(phi, self.formula)

    def same_configuration(self, other):
        return isinstance(other, AcceptsOne) and other.name == self.name and pl._ast_eq(other.formula, self.formula)


class NeedsContext(AcceptsOne):
    """A rule that answers only through `applies_in_context`, as the rules that
    read the proof around them do (`Uniqueness`, the relation rules)."""

    def applies(self, candidates, phi):
        return False

    def applies_in_context(self, candidates, phi, context):
        return not candidates and pl._ast_eq(phi, self.formula)


class CannotAnswer(AcceptsOne):
    def applies(self, candidates, phi):
        raise RuntimeError("this rule cannot say")


# --------------------------------------------------------------------
# What an (Axiom) line may state
# --------------------------------------------------------------------

@pytest.mark.parametrize(("fields", "text", "accepted"), [
    ({}, UNLISTED_AXIOM, True),
    ({}, LISTED_AXIOM, True),
    ({"axioms": [LISTED]}, LISTED_AXIOM, True),
    ({"axioms": [LISTED]}, UNLISTED_AXIOM, False),
    ({"axioms_closed": True}, LISTED_AXIOM, False),
    ({"axioms_closed": True}, UNLISTED_AXIOM, False),
    ({"axioms": [LISTED], "axioms_closed": True}, LISTED_AXIOM, True),
    ({"axioms": [LISTED], "axioms_closed": True}, UNLISTED_AXIOM, False),
], ids=[
    "no list, not closed: any formula (a bare proof) / unlisted",
    "no list, not closed: any formula (a bare proof) / listed",
    "a list closes itself: what it lists",
    "a list closes itself: what it does not",
    "the empty list, closed: nothing / what another theory lists",
    "the empty list, closed: nothing / anything else",
    "a list that is closed too: what it lists",
    "a list that is closed too: what it does not",
])
def test_what_an_axiom_line_may_state(fields, text, accepted):
    ok, err = check(text, theory(**fields))
    assert ok is accepted, err
    if not accepted:
        detail = assert_refused_as_unregistered((ok, err))
        assert detail == "asserted as an axiom, but does not match any declared axioms"


def test_a_closed_theory_still_takes_a_premise_the_proof_was_not_given():
    # Only the axiom list closes. A proof given no premises takes any formula
    # as one, as it always did.
    ok, err = check("1. Unlisted(someObject). (Premise)\n", theory(axioms_closed=True))
    assert ok, err


@pytest.mark.parametrize("fields", [{}, {"axioms_closed": True}], ids=["open", "closed"])
def test_a_premise_the_proof_was_given_a_list_of_is_refused_the_same_way(fields):
    result = check("1. Unlisted(someObject). (Premise)\n", theory(**fields), premises=[LISTED])
    assert assert_refused_as_unregistered(result) == "asserted as a premise, but does not match any declared premises"


# --------------------------------------------------------------------
# The flag reaches the validator by every route
# --------------------------------------------------------------------

@pytest.mark.parametrize(("first", "second", "closed"), [
    (True, False, True), (False, True, True), (True, True, True), (False, False, False),
], ids=["closed + open", "open + closed", "closed + closed", "open + open"])
def test_a_combination_of_theories_is_closed_when_any_theory_is(first, second, closed):
    combined = theory(axioms_closed=first).extended(theory(axioms_closed=second))
    assert combined.axioms_closed is closed
    ok, err = check(UNLISTED_AXIOM, combined)
    assert ok is (not closed), err


def test_extending_with_several_theories_is_closed_when_the_last_one_is():
    combined = theory().extended(theory(), theory(axioms_closed=True))
    assert combined.axioms_closed is True
    assert not check(UNLISTED_AXIOM, combined)[0]


def test_extending_does_not_change_the_theories_it_combines():
    closed, other = theory(axioms_closed=True), theory()
    closed.extended(other)
    assert closed.axioms_closed is True
    assert other.axioms_closed is False


def test_a_theory_is_not_closed_unless_it_says_so():
    assert TheoryEnvironment().axioms_closed is False
    assert theory().axioms_closed is False


def test_elaborated_entries_carry_what_the_theory_said():
    closed, _ = pp.parse_proof_text(UNLISTED_AXIOM, theory(axioms_closed=True))
    opened, _ = pp.parse_proof_text(UNLISTED_AXIOM, theory())
    assert closed.axioms_closed is True
    assert opened.axioms_closed is False
    assert ElaboratedEntries([]).axioms_closed is False
    assert ElaboratedEntries([], axioms_closed=True).axioms_closed is True


def test_a_selected_theory_keeps_its_flag_when_base_syntax_is_added_to_it():
    # `parse_proof_text` adds the base line elaborators to a theory it was
    # given, by copying it; the copy must still be closed.
    entries, _ = pp.parse_proof_text(UNLISTED_AXIOM, st.SET_THEORY_ENVIRONMENT)
    assert entries.axioms_closed is True


def hand_built_entries(**flags):
    return ElaboratedEntries([("1", UNLISTED, ("axiom",))], **flags)


def test_a_proof_reads_the_flag_of_its_entries():
    closed = pl.Proof(hand_built_entries(axioms_closed=True), declarations=[OBJECT, *PREDICATES])
    assert closed.axioms_closed is True
    assert assert_refused_as_unregistered(closed.check_detailed())

    opened = pl.Proof(hand_built_entries(), declarations=[OBJECT, *PREDICATES])
    assert opened.axioms_closed is False
    ok, err = opened.check_detailed()
    assert ok, err

    plain = pl.Proof([("1", UNLISTED, ("axiom",))], declarations=[OBJECT, *PREDICATES])
    assert plain.axioms_closed is False
    assert plain.check_detailed()[0]


def test_a_proof_with_axioms_is_closed_whatever_its_entries_say():
    proof = pl.Proof(hand_built_entries(), axioms=[LISTED], declarations=[OBJECT, *PREDICATES])
    assert proof.axioms_closed is True
    assert assert_refused_as_unregistered(proof.check_detailed())


def test_a_proof_whose_theory_lists_axioms_is_closed_though_the_theory_did_not_say_so():
    # The axioms come from the environment, not from the caller, and are
    # merged into the proof's list: the list the proof is closed by.
    entries, _ = pp.parse_proof_text(UNLISTED_AXIOM, theory(axioms=[LISTED]))
    assert entries.axioms_closed is False
    assert pl.Proof(entries).axioms_closed is True


def test_the_validator_takes_the_flag_directly():
    entries = [("1", UNLISTED, ("axiom",))]
    declarations = [OBJECT, *PREDICATES]
    closed = pl.ProofValidator(pl.default_rules(), None, [], declarations=declarations, axioms_closed=True)
    ok, err, _ = closed.validate(entries)
    assert not ok and err.category == pl.CATEGORY_UNREGISTERED_FORMULA

    opened = pl.ProofValidator(pl.default_rules(), None, [], declarations=declarations)
    ok, err, _ = opened.validate(entries)
    assert ok, err

    # A validator that was given a list is closed without being told so: it
    # refuses what the list does not hold, and records what it does as a theory
    # axiom the proof used.
    listed = pl.ProofValidator(pl.default_rules(), None, [LISTED], declarations=declarations)
    ok, err, _ = listed.validate(entries)
    assert not ok and err.category == pl.CATEGORY_UNREGISTERED_FORMULA
    ok, err, _ = listed.validate([("1", LISTED, ("axiom",))])
    assert ok, err
    assert same_formulas(listed.used_axioms, [LISTED]) and listed.own_givens == []

    # A validator built with no list at all, closed, refuses rather than failing.
    absent = pl.ProofValidator(pl.default_rules(), None, None, declarations=declarations, axioms_closed=True)
    ok, err, _ = absent.validate(entries)
    assert not ok and err.category == pl.CATEGORY_UNREGISTERED_FORMULA


# --------------------------------------------------------------------
# What a proof is recorded to have assumed or used
# --------------------------------------------------------------------

def validator_of(text, environment):
    entries, _ = pp.parse_proof_text(text, environment)
    validator, ok, err = pl.Proof(entries)._validate()
    return validator, ok, err


def same_formulas(formulas, expected):
    return len(formulas) == len(expected) and all(pl._ast_eq(a, b) for a, b in zip(formulas, expected))


def test_an_axiom_of_a_list_is_recorded_as_used_not_as_assumed():
    validator, ok, err = validator_of(LISTED_AXIOM, theory(axioms=[LISTED]))
    assert ok, err
    assert same_formulas(validator.used_axioms, [LISTED])
    assert validator.own_givens == []


def test_an_axiom_of_a_bare_proof_is_recorded_as_assumed_not_as_used():
    # With no list there is no theory axiom to have used: the line is something
    # this proof assumed, like a premise, and a theorem built from it carries it.
    validator, ok, err = validator_of(UNLISTED_AXIOM, theory())
    assert ok, err
    assert validator.used_axioms == []
    assert same_formulas(validator.own_givens, [UNLISTED])


# --------------------------------------------------------------------
# A refusal points to the rule that justifies the formula
# --------------------------------------------------------------------

POINTER = "; cite it by name instead: "


def refusal(environment, text=UNLISTED_AXIOM, **arguments):
    return assert_refused_as_unregistered(check(text, environment, **arguments))


def test_a_refused_axiom_is_pointed_to_the_rule_that_justifies_it():
    detail = refusal(theory(axioms_closed=True, rules=[AcceptsOne("FixtureRule", UNLISTED)]))
    assert detail == "asserted as an axiom, but does not match any declared axioms" + POINTER + "(FixtureRule)"


def test_the_pointer_says_the_citation_when_the_rule_has_one():
    detail = refusal(theory(axioms_closed=True, rules=[AcceptsOne("FixtureRule", UNLISTED, citation="Fixture axiom")]))
    assert detail.endswith(POINTER + "(Fixture axiom)")
    assert "FixtureRule" not in detail


def test_the_pointer_names_every_rule_that_justifies_the_formula_in_order():
    rules = [AcceptsOne("First", UNLISTED), AcceptsOne("Other", LISTED), AcceptsOne("Second", UNLISTED, citation="Second one")]
    detail = refusal(theory(axioms_closed=True, rules=rules))
    assert detail.endswith(POINTER + "(First) or (Second one)")


def test_the_pointer_names_a_citation_once():
    rules = [AcceptsOne("Twin", UNLISTED, citation="Same words"), AcceptsOne("Other twin", UNLISTED, citation="Same words")]
    detail = refusal(theory(axioms_closed=True, rules=rules))
    assert detail.endswith(POINTER + "(Same words)")


def test_there_is_no_pointer_when_no_rule_justifies_the_formula():
    detail = refusal(theory(axioms_closed=True, rules=[AcceptsOne("OtherFormula", LISTED)]))
    assert POINTER not in detail
    assert detail == "asserted as an axiom, but does not match any declared axioms"


def test_the_pointer_is_also_given_when_the_list_is_not_empty():
    detail = refusal(theory(axioms=[LISTED], rules=[AcceptsOne("FixtureRule", UNLISTED)]))
    assert detail.endswith(POINTER + "(FixtureRule)")


def test_an_axiom_that_is_listed_is_not_pointed_anywhere():
    ok, err = check(LISTED_AXIOM, theory(axioms=[LISTED], rules=[AcceptsOne("FixtureRule", LISTED)]))
    assert ok, err


def test_a_premise_is_not_pointed_to_a_rule():
    detail = refusal(theory(rules=[AcceptsOne("FixtureRule", UNLISTED)]),
                     "1. Unlisted(someObject). (Premise)\n", premises=[LISTED])
    assert POINTER not in detail


def test_the_pointer_asks_a_rule_the_way_a_citation_does_with_the_context_of_the_line():
    detail = refusal(theory(axioms_closed=True, rules=[NeedsContext("ReadsTheProof", UNLISTED)]))
    assert detail.endswith(POINTER + "(ReadsTheProof)")


def test_a_rule_that_cannot_answer_does_not_break_the_refusal():
    rules = [CannotAnswer("Broken", UNLISTED), AcceptsOne("FixtureRule", UNLISTED)]
    detail = refusal(theory(axioms_closed=True, rules=rules))
    assert detail.endswith(POINTER + "(FixtureRule)")


def test_asking_which_rules_justify_a_formula_uses_none_of_them():
    # The line was refused, so no rule was used for it: a theorem built from
    # the proof must not require a rule that was only asked about.
    entries, _ = pp.parse_proof_text(UNLISTED_AXIOM, theory(axioms_closed=True, rules=[AcceptsOne("FixtureRule", UNLISTED)]))
    validator, ok, err = pl.Proof(entries)._validate()
    assert not ok
    assert validator.used_rules == []


def test_the_pointer_names_a_built_in_rule_by_its_name():
    # A rule that sets no `citation` is pointed to by its name, which is how
    # the built-in rules are cited (`Reflexivity`).
    detail = refusal(theory(axioms_closed=True), "1. someObject = someObject. (Axiom)\n")
    assert detail.endswith(POINTER + "(Reflexivity)")


def test_the_pointer_comes_from_the_proof_rules_not_from_all_rules():
    # A rule the theory does not register is not one this proof may cite.
    detail = refusal(theory(axioms_closed=True))
    assert POINTER not in detail


# --------------------------------------------------------------------
# Set theory: the four axioms are cited by name
# --------------------------------------------------------------------

PAIRING = "forall a, forall b, exists Y, forall u, (In(u, Y) iff (u = a or u = b))"
UNION = "forall X, exists Y, forall u, (In(u, Y) iff (exists v, (In(v, X) and In(u, v))))"
POWER_SET = "forall X, exists Y, forall u, (In(u, Y) iff (forall v, (In(v, u) -> In(v, X))))"
INFINITY = ("exists X, (In(EmptySet, X) and forall y, (In(y, X) -> exists S, "
            "((forall u, (In(u, S) iff (In(u, y) or u = y))) and In(S, X))))")

SET_AXIOMS_BY_NAME = [
    (PAIRING, "Axiom of pairing", "PairingAxiom"),
    (UNION, "Axiom of union", "UnionAxiom"),
    (POWER_SET, "Axiom of power set", "PowerSetAxiom"),
    (INFINITY, "Axiom of infinity", "InfinityAxiom"),
]
AXIOM_IDS = ["pairing", "union", "power set", "infinity"]

# Every theory a set-theory proof may be checked in: set theory alone, the
# default (which also has number theory's axioms to list), and number theory's.
ENVIRONMENTS = {
    "set theory": lambda: st.SET_THEORY_ENVIRONMENT,
    "default": pp.default_theory_environment,
    "number theory": lambda: nt_theory.NUMBER_THEORY_ENVIRONMENT,
}


@pytest.fixture(params=sorted(ENVIRONMENTS))
def environment(request):
    return ENVIRONMENTS[request.param]()


@pytest.mark.parametrize(("formula", "citation", "rule_name"), SET_AXIOMS_BY_NAME, ids=AXIOM_IDS)
def test_a_set_axiom_is_cited_by_name(environment, formula, citation, rule_name):
    ok, err = check(f"1. {formula}. ({citation})\n", environment)
    assert ok, err


@pytest.mark.parametrize(("formula", "citation", "rule_name"), SET_AXIOMS_BY_NAME, ids=AXIOM_IDS)
def test_a_set_axiom_is_no_longer_cited_by_restating_it_with_axiom(environment, formula, citation, rule_name):
    detail = assert_refused_as_unregistered(check(f"1. {formula}. (Axiom)\n", environment))
    assert detail == ("asserted as an axiom, but does not match any declared axioms"
                      + POINTER + f"({citation})")


@pytest.mark.parametrize(("formula", "citation", "rule_name"), SET_AXIOMS_BY_NAME, ids=AXIOM_IDS)
def test_the_citation_a_refusal_gives_is_one_that_works(environment, formula, citation, rule_name):
    detail = assert_refused_as_unregistered(check(f"1. {formula}. (Axiom)\n", environment))
    given = re.search(r"cite it by name instead: \((.+)\)$", detail).group(1)
    ok, err = check(f"1. {formula}. ({given})\n", environment)
    assert ok, err


@pytest.mark.parametrize(("formula", "citation", "rule_name"), SET_AXIOMS_BY_NAME, ids=AXIOM_IDS)
def test_each_rule_of_a_set_axiom_has_the_citation_a_proof_uses(formula, citation, rule_name):
    rule = next(rule for rule in st.SET_THEORY_ENVIRONMENT.rules if rule.name == rule_name)
    assert rule.citation == citation


@pytest.mark.parametrize("formula", [
    "forall x, not In(x, EmptySet)",
    "exists x, In(x, EmptySet)",
    "forall x, forall y, (In(x, y) -> not In(y, x))",
    "EmptySet = EmptySet",
], ids=["a true statement that is no axiom", "a false statement", "regularity, which the theory does not have", "an equation"])
def test_a_set_theory_proof_does_not_take_any_formula_as_an_axiom(environment, formula):
    detail = assert_refused_as_unregistered(check(f"1. {formula}. (Axiom)\n", environment))
    assert "asserted as an axiom" in detail


def test_set_theory_lists_no_axiom_and_closes_the_list():
    assert st.SET_THEORY_ENVIRONMENT.axioms == []
    assert st.SET_THEORY_ENVIRONMENT.axioms_closed is True
    assert pp.default_theory_environment().axioms_closed is True
    # The four formulas are still there: they are what the named rules accept.
    assert len(st.SET_AXIOMS) == 4


INT_AXIOM = "1. forall x, forall y, ((Int(x) and Int(y)) -> Int(Plus(x, y))). (Axiom)\n"


@pytest.mark.parametrize("name", ["default", "number theory"])
def test_the_axioms_of_number_theory_are_still_cited_with_axiom(name):
    # Closing set theory's list does not touch number theory's, nor how it is cited.
    ok, err = check(INT_AXIOM, ENVIRONMENTS[name]())
    assert ok, err


def test_set_axioms_cited_by_name_are_recorded_as_rules_not_as_axioms():
    text = "".join(f"{number}. {formula}. ({citation})\n"
                   for number, (formula, citation, _) in enumerate(SET_AXIOMS_BY_NAME, 1))
    validator, ok, err = validator_of(text, st.SET_THEORY_ENVIRONMENT)
    assert ok, err
    assert validator.used_axioms == []
    assert validator.own_givens == []
    used = {type(rule).__name__ for rule in validator.used_rules}
    assert {"PairingAxiomRule", "UnionAxiomRule", "PowerSetAxiomRule", "InfinityAxiomRule"} <= used


def test_a_proof_in_the_base_logic_alone_still_takes_any_formula_as_an_axiom():
    # No list and no theory to close it: the unchanged case.
    entries, _ = pp.parse_proof_text("1. Let a be an object. (Declaration)\n2. a = a. (Axiom)\n", TheoryEnvironment())
    ok, err = pl.Proof(entries).check_detailed()
    assert ok, err


# --------------------------------------------------------------------
# The fixture
# --------------------------------------------------------------------

def test_the_fixture_cites_each_axiom_by_name_and_refuses_the_retired_citation():
    path = Path(__file__).resolve().parents[1] / "tests" / "testSetTheory" / "axioms_cited_by_name.txt"
    results = mp.run_multi_proof_file(path.read_text())

    behaved = {number: (expected, ok, crashed) for number, expected, ok, _message, crashed in results}
    assert behaved == {
        "1": (True, True, False), "2": (False, False, False),
        "3": (True, True, False), "4": (False, False, False),
        "5": (True, True, False), "6": (False, False, False),
        "7": (True, True, False), "8": (False, False, False),
        "9": (False, False, False),
    }

    messages = {number: message for number, _expected, _ok, message, _crashed in results}
    for number, citation in [("2", "Axiom of pairing"), ("4", "Axiom of union"),
                             ("6", "Axiom of power set"), ("8", "Axiom of infinity")]:
        assert messages[number].startswith("Line 1: asserted as an axiom, but does not match any declared axioms"), number
        assert f"({citation})" in messages[number], number
    # The formula of case 9 is no axiom and no rule justifies it: nothing to point to.
    assert POINTER not in messages["9"]
