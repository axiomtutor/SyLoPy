"""Extensionality, foundation and choice are cited for one sentence each.

`(Axiom of extensionality)`, `(Axiom of foundation)` (also `Axiom of regularity`)
and `(Axiom of choice)` used to check the *shape* of the cited line, not the
axiom. Foundation took a universal over an implication whose antecedent is an
atom or a negation and whose consequent is an existential; choice took any
universal over an implication that contains an existential; extensionality took
the right shape for any choice of variable names, so that a member variable that
shadows one of the two sets passed. A line cited with them could therefore state
a false sentence:

    forall x, (Finite(EmptySet) -> exists y, not (y = y))

was accepted as either axiom, and with the proved `Finite(EmptySet)` it gave
`exists y, not (y = y)`. Meanwhile the textbook form of foundation, which has
`exists y, In(y, x)` as its antecedent, was refused.

Each rule now justifies one sentence, up to the names of its bound variables
(`ProofLogic._alpha_eq`), and nothing else. This module checks that in four ways:

* the sentences parse to the formulas the rules compare with, and the formulas
  say what the axioms say (checked against independent Python predicates in
  every structure with up to three elements, where `In` is any relation);
* what the rules accept: the sentences, their renamings, the two orders of
  extensionality's biconditional, foundation's "not the empty set" form;
* what they refuse: the sentences the shapes used to let through, shadowed
  variables, the other axioms' sentences, a cited premise, one edit of an axiom
  (every one-edit change of each axiom, and sampled assignments of colliding
  names to its binders), where any sentence a rule takes must hold in every
  small structure in which the axiom holds;
* the same cases as proofs, in `tests/testSetTheory/zfc_axioms_exact.txt`.
"""

import itertools
import random
import re
from functools import lru_cache
from pathlib import Path

import pytest

from .support import fl, mp, pl, pp, st, tl

V = tl.VariableTerm

# --------------------------------------------------------------------
# The sentences, as a proof writes them (a quantifier in a parenthesized part
# must itself be parenthesized, or it reaches over the arrow)
# --------------------------------------------------------------------

EXT = "forall x, forall y, ((forall z, (In(z, x) iff In(z, y))) -> x = y)"
EXT_SWAPPED = "forall x, forall y, ((forall z, (In(z, y) iff In(z, x))) -> x = y)"
FOUND = (
    "forall x, ((exists y, In(y, x)) -> "
    "exists y, (In(y, x) and not (exists z, (In(z, y) and In(z, x)))))"
)
FOUND_NONEMPTY = (
    "forall x, (not (x = EmptySet) -> "
    "exists y, (In(y, x) and not (exists z, (In(z, y) and In(z, x)))))"
)
CHOICE = (
    "forall X, (((forall A, (In(A, X) -> exists a, In(a, A))) and "
    "(forall A, forall B, ((In(A, X) and In(B, X) and not (A = B)) -> "
    "not (exists c, (In(c, A) and In(c, B)))))) -> "
    "exists C, forall A, (In(A, X) -> exists a, "
    "(In(a, A) and In(a, C) and forall b, ((In(b, A) and In(b, C)) -> b = a))))"
)

EXTENSIONALITY_CITATION = "Axiom of extensionality"
FOUNDATION_CITATION = "Axiom of foundation"
REGULARITY_CITATION = "Axiom of regularity"
CHOICE_CITATION = "Axiom of choice"

# The sentences the old shape checks took for these axioms. They are not axioms:
# the first is false whenever a proof has `Finite(EmptySet)`, which it has.
FALSE_SENTENCE = "forall x, (Finite(EmptySet) -> exists y, not (y = y))"
NOTHING_HAS_A_MEMBER = "forall x, (In(x, x) -> exists y, (In(y, x) and not (y = y)))"
# `y` is the member variable and also the second set: the antecedent says that
# something is a member of y exactly when it is a member of itself.
EXT_MEMBER_SHADOWS_Y = "forall x, forall y, ((forall y, (In(y, x) iff In(y, y))) -> x = y)"
EXT_MEMBER_SHADOWS_X = "forall x, forall y, ((forall x, (In(x, x) iff In(x, y))) -> x = y)"
# The disjointness clause dropped: three two-element sets {1,2}, {2,3}, {1,3}
# have no set that meets each in exactly one element.
CHOICE_WITHOUT_DISJOINTNESS = (
    "forall X, ((forall A, (In(A, X) -> exists a, In(a, A))) -> "
    "exists C, forall A, (In(A, X) -> exists a, "
    "(In(a, A) and In(a, C) and forall b, ((In(b, A) and In(b, C)) -> b = a))))"
)


def check_line(text, citation):
    return pp.check_proof_text(f"1. {text}. ({citation})\n")


def accepted(text, citation):
    ok, err = check_line(text, citation)
    return ok


def renamed(text, mapping):
    """`text` with each whole-word name in `mapping` replaced at once."""
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, mapping)) + r")\b")
    return pattern.sub(lambda match: mapping[match.group(1)], text)


# --------------------------------------------------------------------
# Small structures: elements 0..n-1, and `(a, b) in member` reads `a ∈ b`
# --------------------------------------------------------------------

SIZES = (1, 2, 3)


def structures():
    """Every structure with up to three elements, one for each isomorphism class
    (2 + 10 + 104 of them): what a formula says does not depend on the names of
    the elements."""
    seen = set()
    for n in SIZES:
        pairs = [(a, b) for a in range(n) for b in range(n)]
        for bits in itertools.product((False, True), repeat=len(pairs)):
            member = frozenset(pair for pair, bit in zip(pairs, bits) if bit)
            form = min(
                tuple(sorted((order[a], order[b]) for a, b in member))
                for order in itertools.permutations(range(n))
            )
            if (n, form) not in seen:
                seen.add((n, form))
                yield n, member


def members_of(n, member, s):
    return [a for a in range(n) if (a, s) in member]


# The axioms, written directly as statements about the relation, not through
# the formulas.

def extensional(n, member):
    return all(x == y or members_of(n, member, x) != members_of(n, member, y)
               for x in range(n) for y in range(n))


def regular(n, member):
    for x in range(n):
        inside = set(members_of(n, member, x))
        if inside and not any(not (set(members_of(n, member, y)) & inside) for y in inside):
            return False
    return True


def choice_instances(n, member):
    """For every X: is X a set of nonempty, pairwise disjoint sets, and does a
    set meet each of them in exactly one element?"""
    for X in range(n):
        family = members_of(n, member, X)
        eligible = (
            all(members_of(n, member, A) for A in family)
            and all(not (set(members_of(n, member, A)) & set(members_of(n, member, B)))
                    for A in family for B in family if A != B)
        )
        selector = any(
            all(len(set(members_of(n, member, A)) & set(members_of(n, member, C))) == 1 for A in family)
            for C in range(n)
        )
        yield eligible, selector


def has_selectors(n, member):
    return all(selector for eligible, selector in choice_instances(n, member) if eligible)


def holds(formula, n, member, empty=None, env=None):
    """Truth of a formula over `In`, `=` and `EmptySet` in the structure."""
    env = env or {}

    def value(term):
        if isinstance(term, tl.VariableTerm):
            return env[term.name]
        assert isinstance(term, tl.ConstantTerm) and term.name == "EmptySet", term
        return empty

    def go(f, bound):
        if isinstance(f, fl.AtomicFormula):
            assert f.predicate == "In" and len(f.args) == 2, f
            return (value_in(f.args[0], bound), value_in(f.args[1], bound)) in member
        if isinstance(f, fl.Equals):
            return value_in(f.left, bound) == value_in(f.right, bound)
        if isinstance(f, fl.Not):
            return not go(f.sub, bound)
        if isinstance(f, fl.And):
            return all(go(c, bound) for c in f.conjuncts)
        if isinstance(f, fl.Or):
            return any(go(d, bound) for d in f.disjuncts)
        if isinstance(f, fl.Implies):
            return (not go(f.antecedent, bound)) or go(f.consequent, bound)
        if isinstance(f, fl.Iff):
            return go(f.left, bound) == go(f.right, bound)
        if isinstance(f, fl.ForAll):
            return all(go(f.body, {**bound, f.var: e}) for e in range(n))
        if isinstance(f, fl.Exists):
            return any(go(f.body, {**bound, f.var: e}) for e in range(n))
        raise AssertionError(f"unexpected formula {f!r}")

    def value_in(term, bound):
        if isinstance(term, tl.VariableTerm):
            return bound[term.name]
        return value(term)

    return go(formula, dict(env))


def closed(formula):
    """The universal closure: a one-edit change may leave a variable free."""
    for name in sorted(fl.free_variables(formula), reverse=True):
        formula = fl.ForAll(name, formula)
    return formula


@lru_cache(maxsize=None)
def models(axiom):
    """The (structure, EmptySet) pairs in which an axiom, and what it needs, holds.

    `extensionality` and `choice` stand alone. `foundation` is read together
    with extensionality and an `EmptySet` that has no member, which is what
    `EmptySetPropertyRule` gives it: the `not (x = EmptySet)` form is the same
    axiom only given those two.
    """
    found = []
    for n, member in structures():
        if axiom == "extensionality":
            if extensional(n, member):
                found.append((n, member, None))
        elif axiom == "choice":
            if has_selectors(n, member):
                found.append((n, member, None))
        else:
            assert axiom == "foundation"
            if regular(n, member) and extensional(n, member):
                found += [(n, member, e) for e in range(n) if not members_of(n, member, e)]
    return tuple(found)


def counterexample(sentence, axiom):
    """A structure in which the axiom holds and the sentence does not, or None."""
    sentence = closed(sentence)
    for n, member, empty in models(axiom):
        if not holds(sentence, n, member, empty):
            return n, member, empty
    return None


# --------------------------------------------------------------------
# The sentences parse to the formulas, and the formulas say what the axioms say
# --------------------------------------------------------------------

@pytest.mark.parametrize(("text", "constant", "formula"), [
    (EXT, st.EXTENSIONALITY_TEXT, st.EXTENSIONALITY_AXIOM),
    (EXT_SWAPPED, None, st._EXTENSIONALITY_AXIOM_SWAPPED),
    (FOUND, st.FOUNDATION_TEXT, st.FOUNDATION_AXIOM),
    (FOUND_NONEMPTY, st.FOUNDATION_TEXT_NONEMPTY, st._FOUNDATION_AXIOM_NONEMPTY),
    (CHOICE, st.CHOICE_TEXT, st.CHOICE_AXIOM),
], ids=["extensionality", "extensionality swapped", "foundation", "foundation, not the empty set", "choice"])
def test_the_sentence_parses_to_the_formula_the_rule_compares_with(text, constant, formula):
    assert pl._ast_eq(pp.parse_formula(text), formula)
    if constant is not None:
        assert constant == text


def test_the_extensionality_formula_says_that_sets_with_the_same_members_are_equal():
    for n, member in structures():
        assert holds(st.EXTENSIONALITY_AXIOM, n, member) is extensional(n, member), (n, sorted(member))
        assert holds(st._EXTENSIONALITY_AXIOM_SWAPPED, n, member) is extensional(n, member), (n, sorted(member))


def test_the_foundation_formula_says_that_a_set_with_a_member_has_a_member_sharing_none_with_it():
    outcomes = set()
    for n, member in structures():
        outcomes.add(regular(n, member))
        assert holds(st.FOUNDATION_AXIOM, n, member) is regular(n, member), (n, sorted(member))
    assert outcomes == {True, False}


def test_foundation_in_terms_of_the_empty_set_is_the_same_axiom_given_extensionality():
    both = set()
    for n, member in structures():
        for empty in (e for e in range(n) if not members_of(n, member, e)):
            nonempty = holds(st._FOUNDATION_AXIOM_NONEMPTY, n, member, empty)
            # It implies the axiom whatever the structure: a set with a member is not EmptySet.
            assert not nonempty or regular(n, member), (n, sorted(member), empty)
            if extensional(n, member):
                assert nonempty is regular(n, member), (n, sorted(member), empty)
                both.add(nonempty)
    assert both == {True, False}


def test_the_choice_formula_says_that_a_family_of_nonempty_disjoint_sets_has_a_selector():
    seen = set()
    for n, member in structures():
        assert holds(st.CHOICE_AXIOM, n, member) is has_selectors(n, member), (n, sorted(member))
        seen.update(choice_instances(n, member))
    # Non-vacuous: a family that qualifies and has a selector, one that qualifies
    # and has none, and one that does not qualify.
    assert seen == {(True, True), (True, False), (False, True), (False, False)}


def test_the_disjointness_clause_of_choice_is_needed():
    # Points 0, 1, 2; the pairs 3 = {0, 1}, 4 = {1, 2}, 5 = {0, 2}; the family
    # 6 = {3, 4, 5}. Every pair meets every other, and no set meets all three
    # in exactly one element (one point of {0, 1, 2} misses a pair, two meet
    # one twice). The axiom holds here, because the family is not disjoint; the
    # sentence without the clause does not.
    n = 7
    member = frozenset({(0, 3), (1, 3), (1, 4), (2, 4), (0, 5), (2, 5), (3, 6), (4, 6), (5, 6)})
    assert holds(closed(st.CHOICE_AXIOM), n, member)
    assert not holds(closed(pp.parse_formula(CHOICE_WITHOUT_DISJOINTNESS)), n, member)


# --------------------------------------------------------------------
# What the rules accept
# --------------------------------------------------------------------

@pytest.mark.parametrize(("text", "citation"), [
    (EXT, EXTENSIONALITY_CITATION),
    (EXT_SWAPPED, EXTENSIONALITY_CITATION),
    (FOUND, FOUNDATION_CITATION),
    (FOUND, REGULARITY_CITATION),
    (FOUND_NONEMPTY, FOUNDATION_CITATION),
    (FOUND_NONEMPTY, REGULARITY_CITATION),
    (CHOICE, CHOICE_CITATION),
], ids=["extensionality", "extensionality, biconditional swapped", "foundation", "regularity", "foundation, not the empty set",
        "regularity, not the empty set", "choice"])
def test_each_axiom_is_accepted_as_written(text, citation):
    ok, err = check_line(text, citation)
    assert ok, err


@pytest.mark.parametrize(("text", "citation", "mapping"), [
    (EXT, EXTENSIONALITY_CITATION, {"x": "P", "y": "Q", "z": "r"}),
    (EXT, EXTENSIONALITY_CITATION, {"x": "y", "y": "z", "z": "x"}),
    (FOUND, FOUNDATION_CITATION, {"x": "S", "y": "m", "z": "w"}),
    (FOUND, FOUNDATION_CITATION, {"x": "y", "y": "x"}),
    (FOUND_NONEMPTY, FOUNDATION_CITATION, {"x": "S", "y": "m", "z": "w"}),
    (CHOICE, CHOICE_CITATION, {"X": "F", "A": "M", "B": "N", "a": "p", "b": "q", "c": "r", "C": "T"}),
    (CHOICE, CHOICE_CITATION, {"X": "A", "A": "X", "a": "b", "b": "a"}),
], ids=["extensionality, new names", "extensionality, names rotated", "foundation, new names",
        "foundation, x and y exchanged", "foundation (empty set form), new names", "choice, new names",
        "choice, names exchanged"])
def test_the_names_of_bound_variables_do_not_matter(text, citation, mapping):
    renamed_text = renamed(text, mapping)
    assert renamed_text != text
    ok, err = check_line(renamed_text, citation)
    assert ok, err


def test_the_two_members_of_foundation_may_have_different_names():
    # `exists y` appears twice, in separate scopes.
    text = ("forall x, ((exists y, In(y, x)) -> "
            "exists w, (In(w, x) and not (exists z, (In(z, w) and In(z, x)))))")
    ok, err = check_line(text, FOUNDATION_CITATION)
    assert ok, err


def test_the_two_selector_quantifiers_of_choice_may_have_different_names():
    text = (
        "forall X, (((forall A, (In(A, X) -> exists a, In(a, A))) and "
        "(forall M, forall N, ((In(M, X) and In(N, X) and not (M = N)) -> "
        "not (exists c, (In(c, M) and In(c, N)))))) -> "
        "exists C, forall P, (In(P, X) -> exists q, "
        "(In(q, P) and In(q, C) and forall b, ((In(b, P) and In(b, C)) -> b = q))))"
    )
    ok, err = check_line(text, CHOICE_CITATION)
    assert ok, err


def test_a_proof_can_use_the_axiom_it_cites():
    ok, err = pp.check_proof_text(
        "1. Let X, Y be any sets. (Declaration)\n"
        "2. forall z, (In(z, X) iff In(z, Y)). (Premise)\n"
        f"3. {EXT}. ({EXTENSIONALITY_CITATION})\n"
        "4. forall y, ((forall z, (In(z, X) iff In(z, y))) -> X = y). (Universal Instantiation from 3)\n"
        "5. (forall z, (In(z, X) iff In(z, Y))) -> X = Y. (Universal Instantiation from 4)\n"
        "6. X = Y. (Modus Ponens from 2, 5)\n"
    )
    assert ok, err


# --------------------------------------------------------------------
# What they refuse
# --------------------------------------------------------------------

@pytest.mark.parametrize(("text", "citation"), [
    (FALSE_SENTENCE, FOUNDATION_CITATION),
    (FALSE_SENTENCE, REGULARITY_CITATION),
    (FALSE_SENTENCE, CHOICE_CITATION),
    (NOTHING_HAS_A_MEMBER, FOUNDATION_CITATION),
    (NOTHING_HAS_A_MEMBER, CHOICE_CITATION),
    (EXT_MEMBER_SHADOWS_Y, EXTENSIONALITY_CITATION),
    (EXT_MEMBER_SHADOWS_X, EXTENSIONALITY_CITATION),
    (CHOICE_WITHOUT_DISJOINTNESS, CHOICE_CITATION),
], ids=["false sentence as foundation", "false sentence as regularity", "false sentence as choice",
        "nothing has a member, as foundation", "nothing has a member, as choice",
        "extensionality, member variable is y", "extensionality, member variable is x",
        "choice without disjointness"])
def test_a_sentence_that_is_no_axiom_is_refused(text, citation):
    ok, err = check_line(text, citation)
    assert not ok
    assert err.label == "1"
    assert err.category == pl.CATEGORY_RULE_MISMATCH, err
    assert "is cited for exactly this sentence, up to the names of its bound variables" in str(err)


def test_the_false_sentence_cannot_be_used_to_derive_a_contradiction():
    # On the shape checks this proof was accepted, and ended at `exists y, not (y = y)`.
    for citation in (FOUNDATION_CITATION, CHOICE_CITATION):
        ok, err = pp.check_proof_text(
            f"1. {FALSE_SENTENCE}. ({citation})\n"
            "2. Finite(EmptySet). (Empty set finite)\n"
            "3. Finite(EmptySet) -> exists y, not (y = y). (Universal Instantiation from 1)\n"
            "4. exists y, not (y = y). (Modus Ponens from 2, 3)\n"
        )
        assert not ok
        assert err.label == "1", err
        assert err.category == pl.CATEGORY_RULE_MISMATCH, err


@pytest.mark.parametrize(("text", "citation"), [
    # a bound variable that another quantifier binds again changes what the sentence says
    (FOUND.replace("exists z, (In(z, y) and In(z, x))", "exists y, (In(y, y) and In(y, x))"), FOUNDATION_CITATION),
    (FOUND_NONEMPTY.replace("exists z, (In(z, y) and In(z, x))", "exists x, (In(x, y) and In(x, x))"), FOUNDATION_CITATION),
    (CHOICE.replace("exists c, (In(c, A) and In(c, B))", "exists A, (In(A, A) and In(A, B))"), CHOICE_CITATION),
    (CHOICE.replace("forall b, ((In(b, A) and In(b, C)) -> b = a)", "forall a, ((In(a, A) and In(a, C)) -> a = a)"), CHOICE_CITATION),
])
def test_a_bound_variable_that_is_bound_again_is_refused(text, citation):
    assert text not in {FOUND, FOUND_NONEMPTY, CHOICE}
    assert not accepted(text, citation)


@pytest.mark.parametrize(("text", "own"), [
    (EXT, EXTENSIONALITY_CITATION),
    (FOUND, FOUNDATION_CITATION),
    (FOUND_NONEMPTY, FOUNDATION_CITATION),
    (CHOICE, CHOICE_CITATION),
], ids=["extensionality", "foundation", "foundation, not the empty set", "choice"])
def test_an_axiom_is_not_accepted_under_the_name_of_another(text, own):
    others = {EXTENSIONALITY_CITATION, FOUNDATION_CITATION, CHOICE_CITATION} - {own}
    assert accepted(text, own)
    for other in others:
        assert not accepted(text, other), other


def test_the_generic_axiom_citation_is_refused_for_all_of_them_and_points_to_the_name_only_for_the_axioms():
    pointer = "; cite it by name instead: "
    for text, name in [(EXT, "(Axiom of extensionality)"), (FOUND, "(Axiom of foundation)"),
                       (FOUND_NONEMPTY, "(Axiom of foundation)"), (CHOICE, "(Axiom of choice)")]:
        ok, err = pp.check_proof_text(f"1. {text}. (Axiom)\n")
        assert not ok
        assert err.category == pl.CATEGORY_UNREGISTERED_FORMULA, err
        assert str(err).endswith(pointer + name), err
    # The shape checks pointed a person who restated a false sentence at them.
    for text in (FALSE_SENTENCE, NOTHING_HAS_A_MEMBER, EXT_MEMBER_SHADOWS_Y):
        ok, err = pp.check_proof_text(f"1. {text}. (Axiom)\n")
        assert not ok
        assert err.category == pl.CATEGORY_UNREGISTERED_FORMULA, err
        assert pointer not in str(err), err


def test_a_cited_line_is_refused_before_and_inside_the_rule():
    ok, err = pp.check_proof_text(f"1. In(EmptySet, EmptySet). (Premise)\n2. {EXT}. ({EXTENSIONALITY_CITATION}, 1)\n")
    assert not ok
    assert err.category == pl.CATEGORY_ARITY_MISMATCH, err
    # The rule says so itself, for a caller that does not go through the arity check.
    some_line = pp.parse_formula("In(EmptySet, EmptySet)")
    for rule, axiom in [(st.ExtensionalityAxiomRule(), st.EXTENSIONALITY_AXIOM),
                        (st.FoundationAxiomRule(), st.FOUNDATION_AXIOM),
                        (st.ChoiceAxiomRule(), st.CHOICE_AXIOM)]:
        assert rule.applies([], axiom)
        assert not rule.applies([some_line], axiom)
        assert "takes no cited premises" in rule.explain_in_context([some_line], axiom, None)
        assert "is cited for exactly this sentence" in rule.explain_in_context([], some_line, None)


def test_the_explanation_gives_the_sentence_to_cite():
    for rule, texts in [(st.ExtensionalityAxiomRule(), [EXT]), (st.FoundationAxiomRule(), [FOUND, FOUND_NONEMPTY]),
                        (st.ChoiceAxiomRule(), [CHOICE])]:
        explanation = rule.explain_in_context([], pp.parse_formula(FALSE_SENTENCE), None)
        assert explanation.startswith(f"{rule.citation} is cited for exactly this sentence")
        for text in texts:
            assert text in explanation


def test_the_format_reference_lists_the_sentences_the_rules_accept():
    reference = (Path(__file__).resolve().parents[1] / "docs" / "PROOF_FILE_FORMAT.md").read_text(encoding="utf-8")
    for text in (EXT, FOUND, CHOICE):
        assert f"`{text}`" in reference, text
    assert "not (x = EmptySet)" in reference
    for citation in (EXTENSIONALITY_CITATION, FOUNDATION_CITATION, REGULARITY_CITATION, CHOICE_CITATION):
        assert f"({citation})" in reference, citation


# --------------------------------------------------------------------
# One edit of an axiom is never taken for it
# --------------------------------------------------------------------

def one_edit(node, names, with_empty_set):
    """The formulas that differ from `node` by one change at `node` itself."""
    terms = [V(name) for name in names] + ([st.EMPTY_SET] if with_empty_set else [])
    out = [fl.Not(node)]
    if isinstance(node, fl.AtomicFormula):
        first, second = node.args
        out.append(fl.AtomicFormula(node.predicate, [second, first]))
        for term in terms:
            out.append(fl.AtomicFormula(node.predicate, [term, second]))
            out.append(fl.AtomicFormula(node.predicate, [first, term]))
    elif isinstance(node, fl.Equals):
        out.append(fl.Equals(node.right, node.left))
        for term in terms:
            out.append(fl.Equals(term, node.right))
            out.append(fl.Equals(node.left, term))
    elif isinstance(node, fl.Not):
        out.append(node.sub)
    elif isinstance(node, (fl.And, fl.Or)):
        parts = node.conjuncts if isinstance(node, fl.And) else node.disjuncts
        out.append((fl.Or if isinstance(node, fl.And) else fl.And)(*parts))
        for i, part in enumerate(parts):
            out.append(part)
            if len(parts) > 2:
                out.append(type(node)(*parts[:i], *parts[i + 1:]))
    elif isinstance(node, fl.Implies):
        a, c = node.antecedent, node.consequent
        out += [fl.Iff(a, c), fl.Implies(c, a), fl.And(a, c), fl.Or(a, c), fl.Implies(fl.Not(a), c), a, c]
    elif isinstance(node, fl.Iff):
        left, right = node.left, node.right
        out += [fl.Implies(left, right), fl.Implies(right, left), fl.And(left, right), left, right]
    elif isinstance(node, (fl.ForAll, fl.Exists)):
        out.append((fl.Exists if isinstance(node, fl.ForAll) else fl.ForAll)(node.var, node.body))
        out.append(node.body)
        # Only the binder gets the new name: its uses are now bound by another
        # quantifier, or free.
        out += [type(node)(name, node.body) for name in names if name != node.var]
    return out


def edits(node, names, with_empty_set):
    yield from one_edit(node, names, with_empty_set)
    if isinstance(node, fl.Not):
        for e in edits(node.sub, names, with_empty_set):
            yield fl.Not(e)
    elif isinstance(node, (fl.And, fl.Or)):
        parts = node.conjuncts if isinstance(node, fl.And) else node.disjuncts
        for i, part in enumerate(parts):
            for e in edits(part, names, with_empty_set):
                yield type(node)(*parts[:i], e, *parts[i + 1:])
    elif isinstance(node, fl.Implies):
        for e in edits(node.antecedent, names, with_empty_set):
            yield fl.Implies(e, node.consequent)
        for e in edits(node.consequent, names, with_empty_set):
            yield fl.Implies(node.antecedent, e)
    elif isinstance(node, fl.Iff):
        for e in edits(node.left, names, with_empty_set):
            yield fl.Iff(e, node.right)
        for e in edits(node.right, names, with_empty_set):
            yield fl.Iff(node.left, e)
    elif isinstance(node, (fl.ForAll, fl.Exists)):
        for e in edits(node.body, names, with_empty_set):
            yield type(node)(node.var, e)


def one_edit_mutants(axiom, with_empty_set):
    names = sorted(fl.bound_variable_names(axiom))
    seen = {repr(axiom)}
    mutants = []
    for mutant in edits(axiom, names, with_empty_set):
        key = repr(mutant)
        if key not in seen:
            seen.add(key)
            mutants.append(mutant)
    return mutants


RULES = {
    "extensionality": (st.ExtensionalityAxiomRule, st.EXTENSIONALITY_AXIOM),
    "foundation": (st.FoundationAxiomRule, st.FOUNDATION_AXIOM),
    "foundation, empty set form": (st.FoundationAxiomRule, st._FOUNDATION_AXIOM_NONEMPTY),
    "choice": (st.ChoiceAxiomRule, st.CHOICE_AXIOM),
}
# The model of each rule's axiom: what must hold for a sentence to follow from it.
MODEL = {"extensionality": "extensionality", "foundation": "foundation",
         "foundation, empty set form": "foundation", "choice": "choice"}


@pytest.mark.parametrize("label", RULES)
def test_no_one_edit_change_of_an_axiom_is_taken_for_it_unless_it_still_follows_from_it(label):
    rule_class, axiom = RULES[label]
    rule = rule_class()
    mutants = one_edit_mutants(axiom, with_empty_set=MODEL[label] == "foundation")
    wrong = {repr(m) for m in mutants if counterexample(m, MODEL[label]) is not None}
    # The check must be able to see: most edits change what the sentence says.
    assert len(mutants) >= 40, len(mutants)
    assert len(wrong) >= len(mutants) // 2, (len(wrong), len(mutants))
    taken = [m for m in mutants if rule.applies([], m)]
    assert not [m for m in taken if repr(m) in wrong], \
        f"taken for the axiom, but false where it holds: {[m for m in taken if repr(m) in wrong][:3]}"


@pytest.mark.parametrize("label", RULES)
def test_every_renaming_of_one_bound_variable_is_taken_for_the_axiom(label):
    rule_class, axiom = RULES[label]
    rule = rule_class()
    fresh = iter("pqrstuvwklmn")

    def rename_free(node, old, new):
        if isinstance(node, tl.VariableTerm):
            return V(new) if node.name == old else node
        if isinstance(node, tl.ConstantTerm):
            return node
        if isinstance(node, fl.AtomicFormula):
            return fl.AtomicFormula(node.predicate, [rename_free(a, old, new) for a in node.args])
        if isinstance(node, fl.Equals):
            return fl.Equals(rename_free(node.left, old, new), rename_free(node.right, old, new))
        if isinstance(node, fl.Not):
            return fl.Not(rename_free(node.sub, old, new))
        if isinstance(node, (fl.And, fl.Or)):
            parts = node.conjuncts if isinstance(node, fl.And) else node.disjuncts
            return type(node)(*[rename_free(p, old, new) for p in parts])
        if isinstance(node, fl.Implies):
            return fl.Implies(rename_free(node.antecedent, old, new), rename_free(node.consequent, old, new))
        if isinstance(node, fl.Iff):
            return fl.Iff(rename_free(node.left, old, new), rename_free(node.right, old, new))
        if node.var == old:
            return node
        return type(node)(node.var, rename_free(node.body, old, new))

    def rename_binders(node):
        """Every formula got by giving one quantifier a name that occurs nowhere."""
        if isinstance(node, (fl.ForAll, fl.Exists)):
            new = next(fresh)
            yield type(node)(new, rename_free(node.body, node.var, new))
            for inner in rename_binders(node.body):
                yield type(node)(node.var, inner)
        elif isinstance(node, fl.Not):
            for inner in rename_binders(node.sub):
                yield fl.Not(inner)
        elif isinstance(node, (fl.And, fl.Or)):
            parts = node.conjuncts if isinstance(node, fl.And) else node.disjuncts
            for i, part in enumerate(parts):
                for inner in rename_binders(part):
                    yield type(node)(*parts[:i], inner, *parts[i + 1:])
        elif isinstance(node, fl.Implies):
            for inner in rename_binders(node.antecedent):
                yield fl.Implies(inner, node.consequent)
            for inner in rename_binders(node.consequent):
                yield fl.Implies(node.antecedent, inner)
        elif isinstance(node, fl.Iff):
            for inner in rename_binders(node.left):
                yield fl.Iff(inner, node.right)
            for inner in rename_binders(node.right):
                yield fl.Iff(node.left, inner)

    renamings = list(rename_binders(axiom))
    assert len(renamings) >= 3
    for renaming in renamings:
        assert repr(renaming) != repr(axiom)
        assert rule.applies([], renaming), renaming


# --------------------------------------------------------------------
# Colliding names for the binders
# --------------------------------------------------------------------

def _in(a, b):
    return st.membership_formula(V(a), V(b))


def build_extensionality(x, y, z):
    return fl.ForAll(x, fl.ForAll(y, fl.Implies(
        fl.ForAll(z, fl.Iff(_in(z, x), _in(z, y))), fl.Equals(V(x), V(y)))))


def build_foundation(x, y1, y2, z):
    return fl.ForAll(x, fl.Implies(
        fl.Exists(y1, _in(y1, x)),
        fl.Exists(y2, fl.And(_in(y2, x), fl.Not(fl.Exists(z, fl.And(_in(z, y2), _in(z, x))))))))


def build_choice(X, A1, a1, A2, B, c, C, A3, a2, b):
    return fl.ForAll(X, fl.Implies(
        fl.And(
            fl.ForAll(A1, fl.Implies(_in(A1, X), fl.Exists(a1, _in(a1, A1)))),
            fl.ForAll(A2, fl.ForAll(B, fl.Implies(
                fl.And(_in(A2, X), _in(B, X), fl.Not(fl.Equals(V(A2), V(B)))),
                fl.Not(fl.Exists(c, fl.And(_in(c, A2), _in(c, B)))))))),
        fl.Exists(C, fl.ForAll(A3, fl.Implies(
            _in(A3, X),
            fl.Exists(a2, fl.And(_in(a2, A3), _in(a2, C), fl.ForAll(b, fl.Implies(
                fl.And(_in(b, A3), _in(b, C)), fl.Equals(V(b), V(a2)))))))))))


NAME_POOL = ["x", "y", "z", "w"]
FUZZ = {
    "extensionality": (build_extensionality, st.ExtensionalityAxiomRule, 3, ("x", "y", "z")),
    "foundation": (build_foundation, st.FoundationAxiomRule, 4, ("x", "y", "y", "z")),
    "choice": (build_choice, st.ChoiceAxiomRule, 10, ("X", "A", "a", "A", "B", "c", "C", "A", "a", "b")),
}


@pytest.mark.parametrize("label", FUZZ)
def test_names_given_to_the_binders_that_collide_do_not_make_the_axiom_out_of_something_else(label):
    build, rule_class, slots, canonical = FUZZ[label]
    rule = rule_class()
    assert pl._alpha_eq(build(*canonical), RULES[label][1])
    if slots <= 4:
        assignments = list(itertools.product(NAME_POOL, repeat=slots))
    else:
        generator = random.Random(2026)
        pool = ["X", "A", "B", "a", "b", "c", "C"]
        assignments = [tuple(generator.choice(pool) for _ in range(slots)) for _ in range(1000)]
        assignments += [canonical]
    taken = refused = refused_and_wrong = 0
    for names in assignments:
        sentence = build(*names)
        if rule.applies([], sentence):
            taken += 1
            assert counterexample(sentence, MODEL[label]) is None, \
                f"taken for the axiom, but false where it holds: {sentence}"
        else:
            refused += 1
            # Look at the first few hundred refusals: most of them say something else.
            if refused <= 300:
                refused_and_wrong += counterexample(sentence, MODEL[label]) is not None
    assert taken >= 1
    assert refused_and_wrong >= min(refused, 300) // 4, (refused_and_wrong, min(refused, 300))


# --------------------------------------------------------------------
# The same cases as proofs
# --------------------------------------------------------------------

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "testSetTheory" / "zfc_axioms_exact.txt"


def test_the_fixture_proves_with_each_axiom_and_refuses_what_only_looked_like_it():
    results = mp.run_multi_proof_file(FIXTURE.read_text())
    behaved = {number: (expected, ok, crashed) for number, expected, ok, _message, crashed in results}
    valid = {"1", "2", "3", "5", "6", "7", "8", "10", "12"}
    invalid = {"4", "9", "11", "13", "14", "15", "16"}
    assert set(behaved) == valid | invalid
    for number in valid:
        assert behaved[number] == (True, True, False), number
    for number in invalid:
        assert behaved[number] == (False, False, False), number
    messages = {number: message for number, _expected, _ok, message, _crashed in results}
    for number in ("4", "9", "11", "13", "14"):
        assert "is cited for exactly this sentence, up to the names of its bound variables" in messages[number], number
    # Restating an axiom with `(Axiom)` is refused and pointed at the name (and at the
    # theorem that case 8 proved and named `Choice`); a false sentence is not pointed anywhere.
    assert messages["15"].startswith("Line 1: asserted as an axiom, but does not match any declared axioms")
    assert "; cite it by name instead: " in messages["15"] and "(Axiom of choice)" in messages["15"], messages["15"]
    assert "cite it by name instead" not in messages["16"], messages["16"]
