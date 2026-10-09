"""Tests for how set-theory phrases and citations are read.

Everything here is sugar: each phrase desugars to ordinary formulas the kernel
already knows, so the expectations are written in plain logic and compared with
the parsed phrase up to the *names of bound variables* (``pl._alpha_eq``).

Covered, in order: citation syntax (``Rule, 3, 3.2.1``, ranges, planned rule
names), declarations with "and" between the names, phrases inside larger
formulas ("Q(w) and w is h, i, j, or k"), set-builder notation, ``contains
exactly``, infix ``subset``, natural-language existentials, alpha-equivalence,
and the stated-conclusion check that uses it.
"""

import importlib
from pathlib import Path

import pytest

from .support import pl, fl, tl, pp, mp, st, c, v, atom

pj = importlib.import_module("SyLoPy.source.ProofJustification")


def core(text, bound=()):
    """A formula written in plain logic, with no sugar."""
    return pp.parse_formula(text, set(bound))


def surface(text, bound=()):
    """A formula as the proof parser reads it (sugar and all)."""
    return pp.parse_formula(text, set(bound))


def alpha(left, right):
    return pl._alpha_eq(left, right)


def reads_as(text, plain):
    """Does the surface `text` mean the plain-logic formula `plain`?"""
    actual, expected = surface(text), core(plain)
    assert alpha(actual, expected), f"{text!r}\n  parsed:   {actual!r}\n  expected: {expected!r}"


def is_refused(text):
    with pytest.raises(ValueError):
        surface(text)


# --------------------------------------------------------------------
# Citations: "Rule, 3, 3.2.1", ranges, planned rule names
# --------------------------------------------------------------------

def _cite(text):
    return pj.parse_justification(text)


def test_comma_citation_names_the_rule_and_then_the_lines():
    kind, rule, refs = _cite("Modus Ponens, 2, 3")
    assert kind == "rule"
    assert isinstance(rule, pl.ModusPonensRule)
    assert refs == ["2", "3"]


def test_comma_and_from_citations_mean_the_same():
    assert _cite("Modus Ponens, 2, 3")[2] == _cite("Modus Ponens from 2, 3")[2]
    assert type(_cite("Modus Ponens, 2, 3")[1]) is type(_cite("Modus Ponens from 2, 3")[1])


def test_dotted_labels_are_kept_whole():
    assert _cite("Universal Instantiation, 3, 3.2.1")[2] == ["3", "3.2.1"]


def test_a_range_citation_gives_its_two_endpoints():
    kind, rule, refs = _cite("Mutatis mutandis, 3.1 to 3.2")
    assert (kind, rule.name, refs) == ("rule", "MutatisMutandis", ["3.1", "3.2"])


def test_ranges_mix_with_single_labels():
    assert _cite("Mutatis mutandis, 1 to 2, 5")[2] == ["1", "2", "5"]
    assert _cite("Mutatis mutandis, 1 to 2 and 5")[2] == ["1", "2", "5"]


@pytest.mark.parametrize("text,name", [
    ("WLOG, 3.2.2", "WLOG"),
    ("Without loss of generality, 3.2.2", "WLOG"),
    ("Mutatis mutandis, 3.1 to 3.2", "MutatisMutandis"),
    ("Axiom of pairing", "PairingAxiom"),
    ("Axiom of union", "UnionAxiom"),
])
def test_planned_rule_names_resolve_to_named_placeholders(text, name):
    kind, rule, _refs = _cite(text)
    assert kind == "rule"
    assert isinstance(rule, pl.NamedRulePlaceholder)
    assert rule.name == name


def test_uniqueness_is_a_real_rule_cited_either_way():
    for text in ("Uniqueness, 2, 3", "Uniqueness from 2, 3"):
        kind, rule, refs = _cite(text)
        assert (kind, refs) == ("rule", ["2", "3"])
        assert isinstance(rule, pl.UniquenessRule)


def test_set_property_with_citations_is_the_general_rule():
    # Bare "Set property" is the empty-set rule; citing lines selects the general one.
    assert _cite("Set property, 3, 3.2.1")[1].name == "SetProperty"
    assert _cite("Set property from 3, 3.2.1")[1].name == "SetProperty"
    kind, rule, refs = _cite("Set property")
    assert (rule.name, refs) == ("EmptySetProperty", [])


def test_an_unknown_rule_with_citations_is_an_error_not_a_mangled_placeholder():
    with pytest.raises(ValueError, match="Unknown inference rule"):
        _cite("Frobnicate, 2, 3")


def test_a_bare_unknown_name_is_kept_for_theorem_lookup():
    kind, rule, refs = _cite("The empty set subset theorem")
    assert isinstance(rule, pl.NamedRulePlaceholder)
    assert (rule.name, refs) == ("The empty set subset theorem", [])


# --------------------------------------------------------------------
# Declarations with "and" between the names
# --------------------------------------------------------------------

def _declaration(text):
    entries, _ = pp.parse_proof_text(text)
    (_label, formula, (tag, declarations)), = entries
    return tag, [d.name for d in declarations], formula


@pytest.mark.parametrize("line,names", [
    ("Let X and Y be sets.", ["X", "Y"]),
    ("Let X, Y and Z be sets.", ["X", "Y", "Z"]),
    ("Let X, Y, and Z be any sets.", ["X", "Y", "Z"]),
    ("X and Y are sets.", ["X", "Y"]),
])
def test_and_between_names_declares_all_of_them(line, names):
    tag, declared, formula = _declaration(f"1. {line} (Declaration)\n")
    assert (tag, declared, formula) == ("declare", names, None)


def test_the_same_holds_when_the_line_is_cited_as_a_premise():
    tag, declared, _ = _declaration("1. Let X and Y be sets. (Premise)\n")
    assert declared == ["X", "Y"]


def test_a_declaration_can_still_carry_a_condition():
    for line in ("Let X and Y be sets such that X subseteq Y.", "Let X and Y be sets and X subseteq Y."):
        tag, declared, formula = _declaration(f"1. {line} (Declaration)\n")
        assert declared == ["X", "Y"]
        assert alpha(formula, st.subset_formula(c("X"), c("Y")))


def test_and_still_separates_declaration_clauses():
    entries, _ = pp.parse_proof_text("1. Let X be a set and Y be a set. (Declaration)\n")
    (_label, _formula, (_tag, declarations)), = entries
    assert [d.name for d in declarations] == ["X", "Y"]


# --------------------------------------------------------------------
# Braces are brackets for the connective grammar
# --------------------------------------------------------------------

def test_split_top_level_does_not_cut_inside_braces():
    parts = pp.split_top_level("Y = {u in X: P(u) and Q(u)} and Z = {a}", " and ")
    assert [p.strip() for p in parts] == ["Y = {u in X: P(u) and Q(u)}", "Z = {a}"]


def test_a_conjunction_of_two_displays():
    reads_as(
        "Y = {u in X: P(u) and Q(u)} and Z = {a}",
        "(forall u, (In(u, Y) iff (In(u, X) and (P(u) and Q(u))))) and (forall u, (In(u, Z) iff u = a))",
    )


# --------------------------------------------------------------------
# Phrases inside larger formulas
# --------------------------------------------------------------------

@pytest.mark.parametrize("text,plain", [
    ("if x is a or b then P(x)", "(x = a or x = b) -> P(x)"),
    ("x is a or b iff R(x)", "(x = a or x = b) iff R(x)"),
    ("not (x is a or b)", "not (x = a or x = b)"),
    ("not x is a or b", "not (x = a or x = b)"),
    ("Q(w) and w is h, i, j, or k", "Q(w) and (w = h or w = i or w = j or w = k)"),
    ("x is a or b and Q(x)", "(x = a or x = b) and Q(x)"),
    ("P(a) or x is a or b", "P(a) or (x = a or x = b)"),
    ("Q(x) and x is in {a, b}", "Q(x) and (x = a or x = b)"),
])
def test_alternatives_and_enumerations_keep_together_inside_larger_formulas(text, plain):
    reads_as(text, plain)


def test_alternatives_under_a_quantifier():
    reads_as("forall x, Q(x) and x is a or b", "forall x, (Q(x) and (x = a or x = b))")


@pytest.mark.parametrize("text", [
    "n is even or odd",
    "Q(n) and n is even or odd",
    "if n is even or odd then P(n)",
])
def test_ordinary_english_is_still_not_read_as_alternatives(text):
    is_refused(text)


def test_contains_exactly_inside_a_conjunction():
    reads_as(
        "Q(V) and V contains exactly g, h, i and j",
        "Q(V) and (forall u, (In(u, V) iff (u = g or u = h or u = i or u = j)))",
    )


def test_contains_exactly_list_ends_at_a_conjunct_with_arguments():
    reads_as(
        "Q(S) and S contains exactly a and b and P(S)",
        "Q(S) and (forall u, (In(u, S) iff (u = a or u = b))) and P(S)",
    )


# --------------------------------------------------------------------
# Set-builder notation
# --------------------------------------------------------------------

@pytest.mark.parametrize("text,plain", [
    ("Y = {u in X: P(u)}", "forall u, (In(u, Y) iff (In(u, X) and P(u)))"),
    ("{u in X: P(u)} = Y", "forall u, (In(u, Y) iff (In(u, X) and P(u)))"),
    ("Y = {y: P(y)}", "forall y, (In(y, Y) iff P(y))"),
    ("Y = {F(x): x in X}", "forall v, (In(v, Y) iff exists x, (In(x, X) and v = F(x)))"),
    ("Y = {F(x): x in X and R(x)}", "forall v, (In(v, Y) iff exists x, (In(x, X) and R(x) and v = F(x)))"),
    ("Y = {F(x): x in X, y in Z}",
     "forall v, (In(v, Y) iff exists x, exists y, (In(x, X) and In(y, Z) and v = F(x)))"),
    ("z is in {u in X: P(u)}", "In(z, X) and P(z)"),
    ("z is not in {u in X: P(u)}", "not (In(z, X) and P(z))"),
    ("z is in {y: P(y)}", "P(z)"),
    ("if Y = {u in X: P(u)} then Q(Y)", "(forall u, (In(u, Y) iff (In(u, X) and P(u)))) -> Q(Y)"),
])
def test_set_builder_means_a_membership_condition(text, plain):
    reads_as(text, plain)


def test_a_builder_does_not_capture_a_name_the_element_uses():
    # The set is called u, and the builder's own variable is u too: the
    # generated element variable must not be u.
    formula = surface("u = {u in X: P(u)}")
    assert alpha(formula, core("forall v, (In(v, u) iff (In(v, X) and P(v)))"))


def test_an_element_may_not_use_a_name_the_builder_binds_inside():
    with pytest.raises(ValueError, match="bound inside"):
        surface("w is in {u in X: exists w, Q(u, w)}")


@pytest.mark.parametrize("text", [
    "Y = {u in X P(u)}",     # no colon
    "Y = {u in X:}",         # no property
    "Y = {: P(u)}",          # nothing before the colon
    "Y = {a, b",             # unbalanced
    "Y = {}",                # empty
    "P({u in X: Q(u)})",     # not a term
])
def test_malformed_displays_are_refused(text):
    is_refused(text)


# --------------------------------------------------------------------
# Subset spellings
# --------------------------------------------------------------------

@pytest.mark.parametrize("text", ["X subset Y", "X is a subset of Y", "X subseteq Y"])
def test_every_subset_spelling_is_the_non_strict_relation(text):
    assert alpha(surface(text), st.subset_formula(c("X"), c("Y")))


def test_subset_inside_a_conjunction():
    reads_as(
        "if X subseteq Y and Y subseteq X then X = Y",
        "((forall v, (In(v, X) -> In(v, Y))) and (forall v, (In(v, Y) -> In(v, X)))) -> X = Y",
    )


# --------------------------------------------------------------------
# Bounded quantifiers
# --------------------------------------------------------------------

@pytest.mark.parametrize("text,plain", [
    ("forall a in X, P(a)", "forall a, (In(a, X) -> P(a))"),
    ("for all a in X, P(a)", "forall a, (In(a, X) -> P(a))"),
    ("for all a in X we have P(a)", "forall a, (In(a, X) -> P(a))"),
    ("exists a in X, P(a)", "exists a, (In(a, X) and P(a))"),
    ("there exists a in X such that P(a)", "exists a, (In(a, X) and P(a))"),
])
def test_bounded_quantifiers_desugar_to_membership_restricted_quantifiers(text, plain):
    reads_as(text, plain)


def test_bounded_quantifier_body_can_contain_connectives():
    reads_as(
        "forall a in X, P(a) and Q(a)",
        "forall a, (In(a, X) -> (P(a) and Q(a)))",
    )


def test_bounded_quantifier_can_appear_after_a_connective():
    reads_as(
        "P and forall a in X, Q(a) and R(a)",
        "P and (forall a, (In(a, X) -> (Q(a) and R(a))))",
    )


@pytest.mark.parametrize("text", [
    "forall a in X",
    "exists a in X",
    "forall a in X,",
    "exists a in X such that",
])
def test_malformed_bounded_quantifiers_are_refused(text):
    is_refused(text)

# --------------------------------------------------------------------
# Natural-language existentials
# --------------------------------------------------------------------

@pytest.mark.parametrize("text,plain", [
    ("there exists x such that P(x)", "exists x, P(x)"),
    ("there exists a set Y such that P(Y)", "exists Y, P(Y)"),
    ("there exists a set Y such that P(Y) and Q(Y)", "exists Y, (P(Y) and Q(Y))"),
    ("there exists a set Y, forall u, In(u, Y)", "exists Y, forall u, In(u, Y)"),
    ("there exists a set Y that contains exactly a and b",
     "exists Y, forall u, (In(u, Y) iff (u = a or u = b))"),
    ("there is a set Y = {a, b}", "exists Y, forall u, (In(u, Y) iff (u = a or u = b))"),
    ("there exists a set Y such that Y = {a, b}", "exists Y, forall u, (In(u, Y) iff (u = a or u = b))"),
    ("there exists x such that there exists y such that R(x, y)", "exists x, exists y, R(x, y)"),
    ("there exists an integer n such that P(n)", "exists n, (Int(n) and P(n))"),
])
def test_existential_phrases_desugar_to_ordinary_quantifiers(text, plain):
    reads_as(text, plain)


def test_the_word_set_adds_no_condition():
    assert alpha(surface("there exists a set Y such that P(Y)"), surface("there exists Y such that P(Y)"))


@pytest.mark.parametrize("text", [
    "there exists a unique set Y such that P(Y)",
    "there exists exactly one set Y such that P(Y)",
    "there exists a unique Y such that P(Y)",
])
def test_unique_existence_is_written_out_in_ordinary_logic(text):
    reads_as(text, "exists Y, (P(Y) and forall Z, (P(Z) -> Z = Y))")


def test_the_competitor_variable_avoids_names_in_the_condition():
    # X occurs in the condition, so it cannot be the competitor variable; if it
    # were, the free X would be captured and the meaning would change.
    formula = surface("there exists a unique set Y such that R(Y, X)")
    assert alpha(formula, core("exists Y, (R(Y, X) and forall Z, (R(Z, X) -> Z = Y))"))
    assert not alpha(formula, core("exists Y, (R(Y, X) and forall X, (R(X, X) -> X = Y))"))


def test_unique_set_with_a_label_and_a_condition():
    # The braces only label the witness; the condition after "that" constrains it.
    reads_as(
        "there exists a unique set {a, b} that contains exactly a and b",
        "exists V, ((forall u, (In(u, V) iff (u = a or u = b))) and "
        "forall W, ((forall u, (In(u, W) iff (u = a or u = b))) -> W = V))",
    )


def test_unique_enumeration_equality_form():
    reads_as(
        "there exists a unique set Y = {a, b}",
        "exists Y, ((forall u, (In(u, Y) iff (u = a or u = b))) and "
        "forall W, ((forall u, (In(u, W) iff (u = a or u = b))) -> W = Y))",
    )


def test_existentials_inside_larger_formulas():
    reads_as("if there exists a set Y such that P(Y) then Q", "(exists Y, P(Y)) -> Q")
    reads_as("not there exists a set Y such that P(Y)", "not (exists Y, P(Y))")
    reads_as("if A then there exists a set Y such that P(Y) and Q(Y)", "A -> (exists Y, (P(Y) and Q(Y)))")


def test_an_existential_after_and_takes_the_rest_of_the_formula():
    # Like an existential at the start of a string, it extends to the right.
    reads_as("P(a) and there exists x such that Q(x) and R(x)", "P(a) and (exists x, (Q(x) and R(x)))")
    reads_as(
        "P and there exists a unique set {c, d} that contains exactly c and d",
        "P and (exists V, ((forall u, (In(u, V) iff (u = c or u = d))) and "
        "forall W, ((forall u, (In(u, W) iff (u = c or u = d))) -> W = V)))",
    )


def test_an_existential_before_then_stops_at_then():
    reads_as(
        "if there exists a unique set {c, d} that contains exactly c and d then P(c, d)",
        "(exists V, ((forall u, (In(u, V) iff (u = c or u = d))) and "
        "forall W, ((forall u, (In(u, W) iff (u = c or u = d))) -> W = V))) -> P(c, d)",
    )


def test_symbolic_quantifiers_keep_their_old_scope():
    # Unchanged: after "and", a symbolic `exists x, BODY` ends at the next connective.
    reads_as("P(a) and exists x, Q(x) and R(x)", "P(a) and (exists x, Q(x)) and R(x)")


@pytest.mark.parametrize("text", [
    "there exists a natural number n such that P(n)",   # two-word kind: no such predicate
    "there exists a unique set Y",                       # no condition
    "there exists a unique set Y such that",             # empty condition
    "there exists a set such that P",                    # no variable
])
def test_unreadable_existentials_are_refused_with_the_supported_forms(text):
    with pytest.raises(ValueError):
        surface(text)


def test_the_refusal_lists_the_supported_forms():
    with pytest.raises(ValueError, match="Supported:"):
        surface("there exists a unique set Y")


def test_an_unknown_kind_word_is_named_in_the_error():
    with pytest.raises(ValueError, match="'prime'"):
        surface("there exists a prime p such that P(p)")


def test_the_bare_article_still_works_as_a_variable_name():
    # "a" is also a perfectly good variable name.
    reads_as("there exists a such that P(a)", "exists a, P(a)")
    reads_as("there exists a, b such that R(a, b)", "exists a, exists b, R(a, b)")


# --------------------------------------------------------------------
# Alpha-equivalence
# --------------------------------------------------------------------

def test_alpha_eq_ignores_the_names_of_bound_variables():
    assert alpha(core("forall x, P(x)"), core("forall y, P(y)"))
    assert alpha(core("exists x, forall y, R(x, y)"), core("exists a1, forall b1, R(a1, b1)"))
    assert alpha(core("forall x, forall x, P(x)"), core("forall y, forall z, P(z)"))


def test_alpha_eq_still_tells_different_formulas_apart():
    assert not alpha(core("forall x, P(x, c)"), core("forall x, P(x, d)"))             # free names differ
    assert not alpha(core("forall x, exists y, R(x, y)"), core("forall x, exists y, R(y, x)"))  # binders swapped
    assert not alpha(core("forall x, forall x, P(x)"), core("forall y, forall z, P(y)"))        # shadowing
    assert not alpha(core("forall x, P(x)"), core("exists x, P(x)"))
    assert not alpha(core("A and B"), core("B and A"))
    assert not alpha(core("A and B"), core("A and B and C"))


def test_alpha_eq_distinguishes_a_free_name_from_a_bound_one():
    assert not alpha(core("forall x, P(x, y)"), core("forall y, P(y, y)"))
    assert not alpha(core("forall y, P(y, y)"), core("forall x, P(x, y)"))


def test_alpha_eq_agrees_with_ast_eq_when_nothing_is_bound():
    for text in ("A", "P(a, f(b))", "a = f(b)", "A -> (B or C)", "not A", "A iff B"):
        formula = core(text)
        assert alpha(formula, core(text)) and pl._ast_eq(formula, core(text))


def test_alpha_eq_handles_terms_and_function_applications():
    assert alpha(core("forall x, P(f(x, g(x)))"), core("forall z, P(f(z, g(z)))"))
    assert not alpha(core("forall x, P(f(x, g(x)))"), core("forall z, P(f(z, g(c)))"))


# --------------------------------------------------------------------
# The stated-conclusion check compares up to bound-variable names
# --------------------------------------------------------------------

def test_conclusion_is_derived_up_to_bound_variable_names():
    derived = core("exists Y, forall z, (In(z, Y) iff z = a)")
    entries = [("1", derived, ("rule", pl.ReiterationRule(), ["0"]))]
    assert mp.conclusion_is_derived(entries, core("exists S, forall u, (In(u, S) iff u = a)"))
    assert not mp.conclusion_is_derived(entries, core("exists S, forall u, (In(u, S) iff u = b)"))


def test_a_proof_may_state_its_conclusion_with_other_bound_names():
    text = """
# 1: Existential introduction, conclusion stated with another bound name
## Proof that
### If a is in X
### then there exists a set Y such that a is in Y.

1. Let a, X be any set. (Declaration)
2. In(a, X). (Premise)
3. Exists Z, In(a, Z). (Existential Introduction from 2)
"""
    (case,) = mp.parse_multi_proof_file(text)
    assert case.stated_conclusion is not None, "the header's conclusion must parse, or nothing is being checked"
    results = mp.run_multi_proof_file(
        text, axioms=st.SET_THEORY_ENVIRONMENT.axioms,
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules,
    )
    assert [(n, ok) for n, _expected, ok, _msg, _crashed in results] == [("1", True)]


def test_a_different_stated_conclusion_is_still_reported():
    text = """
# 1: Wrong conclusion
## Proof that
### If a is in X
### then there exists a set Y such that Y is in a.

1. Let a, X be any set. (Declaration)
2. In(a, X). (Premise)
3. Exists Z, In(a, Z). (Existential Introduction from 2)
"""
    result = mp.run_multi_proof_file(
        text, axioms=st.SET_THEORY_ENVIRONMENT.axioms,
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules,
    )[0]
    assert result[2] is False
    assert "never derived" in result[3]


def test_unique_pairing_fixture_states_what_its_last_line_derives():
    # The fixture is ahead of the rules it needs, but its *header* must already
    # parse, and must say what the proof's last line says (up to renaming).
    project = Path(__file__).resolve().parents[1]
    text = (project / "tests" / "setTheoryProofs" / "zfc_remaining_axioms.txt").read_text()
    cases = [case for case in mp.parse_multi_proof_file(text) if (case.title or "").startswith("Unique pairing")]
    if not cases:
        pytest.skip("the Unique pairing proof is no longer in this fixture")
    (case,) = cases
    assert case.stated_conclusion is not None
    assert mp.conclusion_is_derived(case.entries, case.stated_conclusion)
