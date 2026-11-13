"""Tests for the definitions of the set operations: the definition facility on set theory.

`Union`, `Intersection` and `PowerSet` are declared function symbols, and a
declaration gives a symbol no meaning. Three definitions give them theirs, each by
one defining sentence that says which objects are members of the set it names:

    u in Union(S, T)         iff  u in S or u in T
    u in Intersection(S, T)  iff  u in S and u in T
    u in PowerSet(S)         iff  forall w, (w in u -> w in S)

A definition adds no axiom. It first shows that there is a set with exactly those
members -- the intersection by Separation, the power set by the Power Set axiom, the
union by a proof from Pairing and Union -- and only then names it. A proof cites it
"(Definition of union)", "(Definition of intersection)", "(Definition of power set)",
for the sentence about any terms, with or without leading foralls, with the
biconditional either way round, and for nothing else.

`test_definitions.py` tests the facility itself, on a toy theory. These tests are
about what is particular to set theory: the three definitions, their evidence, the
sentences each rule accepts and refuses (the builders below write each sentence for
the terms a test chooses, without the module's own helpers, so that a test says
exactly which sentence it means), and the symbols that stay without one. The proofs
that use the definitions are in tests/testSetTheory/set_operation_definitions.txt,
which `test_the_definition_fixture_behaves_as_it_says` runs.
"""

from pathlib import Path
from typing import Callable, NamedTuple

import pytest

from SyLoPy.source import Definitions as df
from SyLoPy.source import validate_all_proofs as validator
from SyLoPy.source.ProofElaboration import TheoryEnvironment

from .support import atom, c, fl, fn, mp, pl, pp, st, v


def _in(element, set_term):
    return atom("In", element, set_term)


def _union(u, s, t):
    return fl.Iff(_in(u, fn("Union", s, t)), fl.Or(_in(u, s), _in(u, t)))


def _intersection(u, s, t):
    return fl.Iff(_in(u, fn("Intersection", s, t)), fl.And(_in(u, s), _in(u, t)))


def _power_set(u, s, w="w"):
    member = v(w)
    return fl.Iff(_in(u, fn("PowerSet", s)), fl.ForAll(w, fl.Implies(_in(member, u), _in(member, s))))


class Operation(NamedTuple):
    key: str
    definition: df.Definition
    build: Callable[..., fl.Formula]
    arity: int          # how many terms the sentence is about
    title: str


OPERATIONS = [
    Operation("union", st.UNION_DEFINITION, _union, 3, "Definition of union"),
    Operation("intersection", st.INTERSECTION_DEFINITION, _intersection, 3, "Definition of intersection"),
    Operation("power set", st.POWER_SET_DEFINITION, _power_set, 2, "Definition of power set"),
]
BY_KEY = {operation.key: operation for operation in OPERATIONS}
KEYS = list(BY_KEY)


def rule_of(operation: Operation, environment: TheoryEnvironment = st.SET_THEORY_ENVIRONMENT):
    return next(r for r in environment.rules
                if isinstance(r, df.DefinitionRule) and r.definition is operation.definition)


# Terms the sentences may be about: none of them mentions a variable that a
# sentence's own quantifier binds (w), so none is captured.
SET_A, SET_B, SET_C = c("A"), c("B"), c("C")
TERMS = {
    "a declared object": SET_A,
    "a variable": v("x"),
    "a function term": fn("f", c("a"), v("y")),
    "a set operation": fn("Union", SET_A, fn("PowerSet", SET_B)),
    "the empty set": st.EMPTY_SET,
}
SOME_PREMISE = fl.Equals(c("a"), c("b"))


def _canonical(operation):
    """The sentence for `x` and declared sets: the instance a proof cites."""
    if operation.key == "power set":
        return operation.build(v("x"), SET_A)
    return operation.build(v("x"), SET_A, SET_B)


def _closed(operation, names):
    """The sentence about the variables `names`, with a `forall` for each, outermost first."""
    formula = operation.build(*[v(name) for name in names])
    for name in reversed(names):
        formula = fl.ForAll(name, formula)
    return formula


def _variable_names(operation):
    return [f"x{i}" for i in range(operation.arity)]


# --------------------------------------------------------------------
# The three definitions
# --------------------------------------------------------------------

def test_set_theory_defines_the_union_the_intersection_and_the_power_set():
    assert [(d.title, d.symbol, d.kind, d.arity, d.type_name) for d in st.SET_DEFINITIONS] == [
        ("Definition of union", "Union", pl.DeclarationKind.FUNCTION, 2, "set operation"),
        ("Definition of intersection", "Intersection", pl.DeclarationKind.FUNCTION, 2, "set operation"),
        ("Definition of power set", "PowerSet", pl.DeclarationKind.FUNCTION, 1, "set operation"),
    ]


def test_each_definition_is_the_sentence_that_says_which_objects_are_members():
    assert [d.sentence() for d in st.SET_DEFINITIONS] == [
        "In(u, Union(A, B)) iff (In(u, A) or In(u, B))",
        "In(u, Intersection(A, B)) iff (In(u, A) and In(u, B))",
        "In(u, PowerSet(A)) iff forall w, (In(w, u) -> In(w, A))",
    ]
    assert [d.variables for d in st.SET_DEFINITIONS] == [("u", "A", "B"), ("u", "A", "B"), ("u", "A")]


def test_each_definition_shows_that_there_is_a_set_with_exactly_those_members():
    assert [df.show(d.existence.statement) for d in st.SET_DEFINITIONS] == [
        "exists Y, forall u, (In(u, Y) iff (In(u, A) or In(u, B)))",
        "exists Y, forall u, (In(u, Y) iff (In(u, A) and In(u, B)))",
        "exists Y, forall u, (In(u, Y) iff forall w, (In(w, u) -> In(w, A)))",
    ]
    assert [d.parameters for d in st.SET_DEFINITIONS] == [("A", "B"), ("A", "B"), ("A",)]


def test_the_evidence_for_each_definition_is_an_axiom_or_a_proof_from_the_axioms():
    union, intersection, power_set = (d.existence.evidence for d in st.SET_DEFINITIONS)
    assert isinstance(union, df.ByProof) and union.text == st.UNION_EXISTENCE_PROOF
    assert isinstance(intersection, df.ByRule) and isinstance(intersection.rule, st.SeparationSchemaRule)
    assert isinstance(power_set, df.ByRule) and isinstance(power_set.rule, st.PowerSetAxiomRule)


@pytest.mark.parametrize("key", KEYS)
def test_the_evidence_for_each_definition_holds_in_set_theory(key):
    assert rule_of(BY_KEY[key]).evidence_problem() is None


def test_the_evidence_for_the_union_is_the_proof_that_the_union_of_two_sets_exists():
    """Proof 2 of tests/setTheoryProofs/set_operation_foundations.txt, which a
    test of its own runs, is the proof the definition of the union is built on."""
    project = Path(__file__).resolve().parents[1]
    text = (project / "tests" / "setTheoryProofs" / "set_operation_foundations.txt").read_text()
    [case] = [case for case in validator.parse_multi_proof_file(text) if case.number == "2"]
    assert [line for line in case.raw_lines if line.strip()] == \
        [line for line in st.UNION_EXISTENCE_PROOF.splitlines() if line.strip()]


def test_a_definition_is_refused_in_a_theory_without_the_axiom_that_is_its_evidence():
    """The evidence must be in the theory: an axiom the theory does not have shows nothing."""
    bare = TheoryEnvironment(name="bare", declarations=st.SET_THEORY_ENVIRONMENT.declarations)
    assert df.DefinitionRule(st.INTERSECTION_DEFINITION, bare).evidence_problem() == \
        "Separation is not a rule of the theory"
    assert df.DefinitionRule(st.POWER_SET_DEFINITION, bare).evidence_problem() == \
        "PowerSetAxiom is not a rule of the theory"
    union = df.DefinitionRule(st.UNION_DEFINITION, bare).evidence_problem()
    assert union.startswith("the proof of existence is not a valid proof:")
    assert "no rule named 'PairingAxiom' is registered" in union


def test_a_theory_that_extends_set_theory_has_the_definitions():
    text = (
        "Use discrete math.\n\n"
        "# 1\n## Proof that\n"
        "1. Let A, B be any set. (Declaration)\n"
        "2. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)\n"
    )
    assert [(number, ok) for number, _expected, ok, _message, _crashed in mp.run_multi_proof_file(text)] == [("1", True)]


# --------------------------------------------------------------------
# What each rule accepts
# --------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_its_sentence_as_a_single_instance(key):
    operation = BY_KEY[key]
    assert rule_of(operation).applies([], _canonical(operation))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_its_sentence_with_a_forall_in_front_of_it(key):
    """The form `Set property` reads: `forall u, (u in Union(S, T) iff ...)`."""
    operation = BY_KEY[key]
    assert rule_of(operation).applies([], fl.ForAll("x", _canonical(operation)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_its_sentence_closed_over_all_its_variables_in_any_order(key):
    import itertools
    operation = BY_KEY[key]
    rule = rule_of(operation)
    names = _variable_names(operation)
    for order in itertools.permutations(names):
        assert rule.applies([], _closed(operation, list(order)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_a_forall_over_a_variable_the_sentence_does_not_mention(key):
    operation = BY_KEY[key]
    assert rule_of(operation).applies([], fl.ForAll("z", _canonical(operation)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_the_biconditional_either_way_round(key):
    operation = BY_KEY[key]
    sentence = _canonical(operation)
    assert rule_of(operation).applies([], fl.Iff(sentence.right, sentence.left))
    assert rule_of(operation).applies([], fl.ForAll("x", fl.Iff(sentence.right, sentence.left)))


@pytest.mark.parametrize("term_name", list(TERMS))
@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_any_terms_in_place_of_the_variables_of_its_sentence(key, term_name):
    operation = BY_KEY[key]
    term = TERMS[term_name]
    terms = [term, SET_A, SET_B][:operation.arity]
    assert rule_of(operation).applies([], operation.build(*terms))
    terms = [SET_A, term, SET_B][:operation.arity]
    assert rule_of(operation).applies([], operation.build(*terms))


def test_the_power_set_rule_accepts_any_name_for_the_variable_of_the_subset_clause():
    rule = rule_of(BY_KEY["power set"])
    for name in ("w", "z", "member", "x_1"):
        assert rule.applies([], _power_set(v("x"), SET_A, name))


def test_the_power_set_rule_accepts_what_the_subset_syntax_builds():
    """`u subseteq S` is the sentence the definition gives for membership in the power set."""
    rule = rule_of(BY_KEY["power set"])
    line = fl.Iff(_in(v("x"), fn("PowerSet", SET_A)), st.subset_formula(v("x"), SET_A))
    assert rule.applies([], line)


def test_a_constant_spelled_like_a_bound_variable_is_not_captured():
    """The constant `w` is not the variable `w` the sentence's quantifier binds."""
    rule = rule_of(BY_KEY["power set"])
    assert rule.applies([], _power_set(c("w"), SET_A))
    assert rule.applies([], _power_set(v("x"), c("w")))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_takes_no_cited_lines(key):
    operation = BY_KEY[key]
    rule = rule_of(operation)
    assert rule.premise_arity == 0
    assert not rule.applies([SOME_PREMISE], _canonical(operation))
    assert rule.explain_in_context([SOME_PREMISE], _canonical(operation), None) == \
        f"{operation.title} takes no cited lines."


# --------------------------------------------------------------------
# What each rule refuses
# --------------------------------------------------------------------

def test_each_rule_accepts_only_the_sentence_of_its_own_operation():
    for operation in OPERATIONS:
        for other in OPERATIONS:
            if operation is other:
                continue
            assert not rule_of(operation).applies([], _canonical(other)), (operation.key, other.key)


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_refuses_the_sentence_where_it_is_not_the_whole_line(key):
    operation = BY_KEY[key]
    rule = rule_of(operation)
    sentence = _canonical(operation)
    for line in (
        fl.And(sentence, SOME_PREMISE),
        fl.And(SOME_PREMISE, sentence),
        fl.Or(sentence, SOME_PREMISE),
        fl.Implies(SOME_PREMISE, sentence),
        fl.Not(sentence),
        fl.Exists("x", sentence),
    ):
        assert not rule.applies([], line), line


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_refuses_one_direction_of_its_sentence(key):
    operation = BY_KEY[key]
    sentence = _canonical(operation)
    rule = rule_of(operation)
    assert not rule.applies([], fl.Implies(sentence.left, sentence.right))
    assert not rule.applies([], fl.Implies(sentence.right, sentence.left))
    assert not rule.applies([], fl.ForAll("x", fl.Implies(sentence.left, sentence.right)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_refuses_things_that_are_not_formulas_of_its_shape(key):
    rule = rule_of(BY_KEY[key])
    for line in (atom("P"), _in(v("x"), SET_A), fl.Equals(c("a"), c("b")), fl.And(atom("P"), atom("Q"))):
        assert not rule.applies([], line)


def _union_near_misses():
    x, a, b = v("x"), SET_A, SET_B
    return {
        "and in place of or": fl.Iff(_in(x, fn("Union", a, b)), fl.And(_in(x, a), _in(x, b))),
        "the first set twice": fl.Iff(_in(x, fn("Union", a, b)), fl.Or(_in(x, a), _in(x, a))),
        "the second set twice": fl.Iff(_in(x, fn("Union", a, b)), fl.Or(_in(x, b), _in(x, b))),
        "the disjuncts in the other order": fl.Iff(_in(x, fn("Union", a, b)), fl.Or(_in(x, b), _in(x, a))),
        "another set in the disjunction": fl.Iff(_in(x, fn("Union", a, b)), fl.Or(_in(x, a), _in(x, SET_C))),
        "another element on each side":
            fl.Iff(_in(x, fn("Union", a, b)), fl.Or(_in(v("y"), a), _in(v("y"), b))),
        "the sets of the union the other way round": fl.Iff(_in(x, fn("Union", b, a)), fl.Or(_in(x, a), _in(x, b))),
        "a negated disjunct": fl.Iff(_in(x, fn("Union", a, b)), fl.Or(fl.Not(_in(x, a)), _in(x, b))),
        "the intersection on the left": fl.Iff(_in(x, fn("Intersection", a, b)), fl.Or(_in(x, a), _in(x, b))),
        "a subset relation in place of the disjunction": fl.Iff(_in(x, fn("Union", a, b)), st.subset_formula(x, a)),
    }


def _intersection_near_misses():
    x, a, b = v("x"), SET_A, SET_B
    return {
        "or in place of and": fl.Iff(_in(x, fn("Intersection", a, b)), fl.Or(_in(x, a), _in(x, b))),
        "the first set twice": fl.Iff(_in(x, fn("Intersection", a, b)), fl.And(_in(x, a), _in(x, a))),
        "the conjuncts in the other order": fl.Iff(_in(x, fn("Intersection", a, b)), fl.And(_in(x, b), _in(x, a))),
        "another set in the conjunction":
            fl.Iff(_in(x, fn("Intersection", a, b)), fl.And(_in(x, a), _in(x, SET_C))),
        "another element on each side":
            fl.Iff(_in(x, fn("Intersection", a, b)), fl.And(_in(v("y"), a), _in(v("y"), b))),
        "the sets of the intersection the other way round":
            fl.Iff(_in(x, fn("Intersection", b, a)), fl.And(_in(x, a), _in(x, b))),
        "a negated conjunct": fl.Iff(_in(x, fn("Intersection", a, b)), fl.And(_in(x, a), fl.Not(_in(x, b)))),
        "the union on the left": fl.Iff(_in(x, fn("Union", a, b)), fl.And(_in(x, a), _in(x, b))),
    }


def _power_set_near_misses():
    x, a, b, w = v("x"), SET_A, SET_B, v("w")
    power = _in(x, fn("PowerSet", a))
    return {
        "the members of the set": fl.Iff(power, _in(x, a)),
        "the supersets of the set": fl.Iff(power, fl.ForAll("w", fl.Implies(_in(w, a), _in(w, x)))),
        "the subsets of another set": fl.Iff(power, fl.ForAll("w", fl.Implies(_in(w, x), _in(w, b)))),
        "an existential in place of the universal":
            fl.Iff(power, fl.Exists("w", fl.Implies(_in(w, x), _in(w, a)))),
        "a conjunction in place of the implication":
            fl.Iff(power, fl.ForAll("w", fl.And(_in(w, x), _in(w, a)))),
        "the set a member of the other, not the members": fl.Iff(power, fl.ForAll("w", fl.Implies(_in(w, x), _in(x, a)))),
        "the power set of another set": fl.Iff(_in(x, fn("PowerSet", b)),
                                               fl.ForAll("w", fl.Implies(_in(w, x), _in(w, a)))),
        "the union on the left": fl.Iff(_in(x, fn("Union", a, b)),
                                        fl.ForAll("w", fl.Implies(_in(w, x), _in(w, a)))),
    }


NEAR_MISSES = {
    "union": _union_near_misses(),
    "intersection": _intersection_near_misses(),
    "power set": _power_set_near_misses(),
}


@pytest.mark.parametrize("key,description", [
    (key, description) for key, misses in NEAR_MISSES.items() for description in misses
])
def test_a_rule_refuses_a_sentence_close_to_its_own(key, description):
    operation = BY_KEY[key]
    phi = NEAR_MISSES[key][description]
    assert not rule_of(operation).applies([], phi)
    assert operation.definition.instance_problem(phi) is not None


def test_the_near_misses_are_about_the_rule_that_refuses_them():
    """A near miss is refused for being close to the sentence and not equal to it:
    each one is a sentence the other two rules do not accept either, and the
    sentence it is close to is accepted."""
    for key, misses in NEAR_MISSES.items():
        operation = BY_KEY[key]
        assert rule_of(operation).applies([], _canonical(operation))
        for description, phi in misses.items():
            for other in OPERATIONS:
                assert not rule_of(other).applies([], phi), (key, description, other.key)


# A term that mentions a variable the sentence's quantifier binds would be
# captured by it, and the line would say something else.

POWER_SET_CAPTURED = {
    "the element is the bound variable": lambda: _power_set(v("w"), SET_A),
    "the set is the bound variable": lambda: _power_set(v("x"), v("w")),
    "the element mentions the bound variable": lambda: _power_set(fn("f", v("w")), SET_A),
    "the set mentions the bound variable": lambda: _power_set(v("x"), fn("Union", SET_A, v("w"))),
}


@pytest.mark.parametrize("description", list(POWER_SET_CAPTURED))
def test_the_power_set_rule_refuses_a_term_the_subset_clause_would_capture(description):
    phi = POWER_SET_CAPTURED[description]()
    operation = BY_KEY["power set"]
    assert not rule_of(operation).applies([], phi)
    message = operation.definition.instance_problem(phi)
    assert "the other side must be forall w_1," in message, message


def test_the_power_set_rule_accepts_the_same_sentence_with_the_variable_renamed():
    rule = rule_of(BY_KEY["power set"])
    assert rule.applies([], _power_set(v("w"), SET_A, "w_1"))
    assert rule.applies([], _power_set(v("x"), v("w"), "u"))
    assert rule.applies([], _power_set(fn("f", v("w")), SET_A, "anything_else"))


def test_the_power_set_rule_refuses_the_sentence_with_the_variable_clashing_both_ways():
    # forall w, (In(w, PowerSet(w)) iff forall w, ...): the element and the set are both w.
    phi = _power_set(v("w"), v("w"))
    assert not rule_of(BY_KEY["power set"]).applies([], phi)


def test_a_refused_citation_says_what_it_is_cited_for():
    union = BY_KEY["union"]
    phi = _union_near_misses()["and in place of or"]
    assert union.definition.instance_problem(phi) == (
        "Definition of union is cited for the sentence In(u, Union(A, B)) iff (In(u, A) or In(u, B)), "
        "for any terms in place of u, A, B, with or without leading `forall`s and with the biconditional "
        "in either order; here for In(x, Union(A, B)) the other side must be (In(x, A) or In(x, B)).")


# --------------------------------------------------------------------
# What a theory has: the symbols, the rules, the titles
# --------------------------------------------------------------------

def test_each_definition_is_registered_in_set_theory_once():
    registered = [r for r in st.SET_THEORY_ENVIRONMENT.rules if isinstance(r, df.DefinitionRule)]
    assert [r.definition for r in registered] == st.SET_DEFINITIONS
    assert st.SET_DEFINITION_RULES == registered
    assert st.SET_THEORY_ENVIRONMENT.citable_titles == [d.title for d in st.SET_DEFINITIONS]


def test_a_registered_rule_asks_the_theory_it_is_in():
    for rule in st.SET_DEFINITION_RULES:
        assert rule.theory() is st.SET_THEORY_ENVIRONMENT


def test_the_symbols_of_the_operations_are_declared_by_their_definitions():
    declared = {d.name: d for d in st.SET_THEORY_ENVIRONMENT.declarations}
    for definition in st.SET_DEFINITIONS:
        assert declared[definition.symbol].kind == pl.DeclarationKind.FUNCTION
        assert declared[definition.symbol].arity == definition.arity
        assert declared[definition.symbol].type_name == "set operation"
    assert [d.name for d in st.SET_THEORY_ENVIRONMENT.declarations].count("Union") == 1


def test_the_product_and_the_ordered_pair_are_declared_and_have_no_definition_yet():
    declared = {d.name: d for d in st.SET_THEORY_ENVIRONMENT.declarations}
    for symbol in ("CartesianProduct", "Pair"):
        assert declared[symbol].kind == pl.DeclarationKind.FUNCTION and declared[symbol].arity == 2
    assert {d.symbol for d in st.SET_DEFINITIONS} == {"Union", "Intersection", "PowerSet"}
    assert [r.name for r in st.SET_THEORY_ENVIRONMENT.rules if isinstance(r, df.DefinitionRule)] == \
        ["Definition of union", "Definition of intersection", "Definition of power set"]


@pytest.mark.parametrize("title,line", [
    ("Definition of Cartesian product",
     "forall p, (In(p, CartesianProduct(A, B)) iff (exists a, (In(a, A) and exists b, (In(b, B) and p = Pair(a, b)))))"),
    ("Definition of ordered pair", "Pair(a, b) = Pair(c, d) iff (a = c and b = d)"),
])
def test_no_proof_can_cite_a_definition_of_the_product_or_the_pair(title, line):
    message = _refusal("1. Let A, B be any set, and a, b, c, d be any object. (Declaration)\n"
                       f"2. {line}. ({title})\n")
    assert message is not None
    assert message.startswith(f"Line 2: no rule named '{title}' is registered for this proof")


# --------------------------------------------------------------------
# A proof cites a definition
# --------------------------------------------------------------------

def _check(text):
    entries = pp.parse_proof_text(text)[0]
    return pl.Proof(entries).check_detailed()


def _refusal(body):
    """The message a one-proof file made of `body` is refused with, or None if it
    is accepted."""
    [(_number, _expected, ok, message, crashed)] = mp.run_multi_proof_file(
        "# 1\n## Proof that\n" + body)
    assert not crashed
    return None if ok else str(message)


DECLARATIONS = "1. Let A, B be any set, and x be any object. (Declaration)\n"


@pytest.mark.parametrize("line,title", [
    ("forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B)))", "Definition of union"),
    ("In(x, Union(A, B)) iff (In(x, A) or In(x, B))", "Definition of union"),
    ("(In(x, A) or In(x, B)) iff In(x, Union(A, B))", "Definition of union"),
    ("forall u, (In(u, Intersection(A, B)) iff (In(u, A) and In(u, B)))", "Definition of intersection"),
    ("In(x, Intersection(A, B)) iff (In(x, A) and In(x, B))", "Definition of intersection"),
    ("forall u, (In(u, PowerSet(A)) iff u subseteq A)", "Definition of power set"),
    ("forall u, (In(u, PowerSet(A)) iff (forall z, (In(z, u) -> In(z, A))))", "Definition of power set"),
    ("In(x, PowerSet(Union(A, B))) iff (forall z, (In(z, x) -> In(z, Union(A, B))))", "Definition of power set"),
])
def test_a_proof_cites_each_definition_in_the_forms_it_is_written(line, title):
    ok, error = _check(f"{DECLARATIONS}2. {line}. ({title})\n")
    assert ok, error


@pytest.mark.parametrize("title", ["definition of union", "Definition-of-union", "DEFINITION OF  UNION",
                                   "Definition Of Union"])
def test_a_definition_is_cited_by_its_title_however_the_title_is_spelled(title):
    ok, error = _check(f"{DECLARATIONS}2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). ({title})\n")
    assert ok, error


def test_a_proof_cites_a_definition_for_a_term_of_the_proof():
    ok, error = _check(
        f"{DECLARATIONS}2. In(Union(A, B), Union(Union(A, B), EmptySet)) iff "
        "(In(Union(A, B), Union(A, B)) or In(Union(A, B), EmptySet)). (Definition of union)\n")
    assert ok, error


@pytest.mark.parametrize("line,title,statement", [
    ("In(x, Union(A, B)) iff (In(x, A) and In(x, B))", "Definition of union",
     "(In(x, A) or In(x, B))"),
    ("In(x, Intersection(A, B)) iff (In(x, A) or In(x, B))", "Definition of intersection",
     "(In(x, A) and In(x, B))"),
    ("In(x, PowerSet(A)) iff In(x, A)", "Definition of power set",
     "forall w, (In(w, x) -> In(w, A))"),
])
def test_a_refused_citation_names_the_definition_and_says_what_it_is_cited_for(line, title, statement):
    message = _refusal(f"{DECLARATIONS}2. {line}. ({title})\n")
    assert message is not None
    assert message.startswith(f"Line 2: '{title}' does not justify")
    assert f"{title} is cited for the sentence" in message
    assert f"the other side must be {statement}." in message


@pytest.mark.parametrize("line,title", [
    ("forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B)))", "Definition of union"),
    ("forall u, (In(u, Intersection(A, B)) iff (In(u, A) and In(u, B)))", "Definition of intersection"),
    ("forall u, (In(u, PowerSet(A)) iff u subseteq A)", "Definition of power set"),
])
def test_a_definition_cited_with_a_line_is_refused(line, title):
    message = _refusal(f"{DECLARATIONS}2. {line}. ({title})\n3. {line}. ({title} from 2)\n")
    assert message == f"Line 3: '{title}' requires at most 0 cited line label(s), but 1 were given (['2'])"


def test_a_captured_variable_is_refused_with_the_reason():
    message = _refusal(
        "1. Let A be any set. (Declaration)\n"
        "2. forall w, (In(w, PowerSet(A)) iff (forall w, (In(w, w) -> In(w, A)))). (Definition of power set)\n")
    assert message is not None
    assert "Definition of power set is cited for the sentence" in message
    assert "here for In(w, PowerSet(A)) the other side must be forall w_1, (In(w_1, w) -> In(w_1, A))." in message


def test_the_definition_makes_the_union_of_a_declared_term_usable_by_set_property():
    """The characterization form is what `Set property` reads: from it and a
    member of A, the line says the member is in the union."""
    ok, err = _check(
        "1. Let A, B be any set, and x be any object. (Declaration)\n"
        "2. In(x, A). (Premise)\n"
        "3. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)\n"
        "4. In(x, A) or In(x, B). (Disjunction Introduction from 2)\n"
        "5. In(x, Union(A, B)). (Set property from 3, 4)\n"
    )
    assert ok, err


def test_a_member_of_a_union_is_not_a_member_without_the_definition():
    """Without the definition the symbol means nothing: that x is in A or in B does
    not make it a member of Union(A, B), since no cited line says what the members
    of Union(A, B) are."""
    message = _refusal(
        "1. Let A, B be any set, and x be any object. (Declaration)\n"
        "2. In(x, A). (Premise)\n"
        "3. In(x, A) or In(x, B). (Disjunction Introduction from 2)\n"
        "4. In(x, Union(A, B)). (Set property from 3, 2)\n"
    )
    assert message == ("Line 4: 'SetProperty' does not justify In(x, Union(A, B)) from the cited line(s) "
                       "['3', '2']: a cited line must characterize membership in a fixed set by a universal "
                       "biconditional")


def test_a_membership_in_a_union_is_a_membership_and_not_yet_a_disjunction():
    """`x is in A union B` is the atom `In(x, Union(A, B))`: that x is in A or in B
    is not said by the phrase but derived from the definition (proof 9 of the fixture)."""
    entries = pp.parse_proof_text(f"{DECLARATIONS}2. x is in A union B. (Premise)\n")[0]
    phi = entries[1][1]
    assert isinstance(phi, fl.AtomicFormula)
    assert pl._ast_eq(phi, _in(c("x"), fn("Union", c("A"), c("B"))))
    message = _refusal(f"{DECLARATIONS}2. x is in A union B. (Premise)\n"
                       "3. x is in A or x is in B. (Set property from 2)\n")
    assert message is not None and message.startswith("Line 3: 'SetProperty'")


# --------------------------------------------------------------------
# A set is named by a property its members have
# --------------------------------------------------------------------

def _plus(*definitions):
    """Set theory with `definitions` added: a theory built on this one."""
    holder = {}
    environment = st.SET_THEORY_ENVIRONMENT.extended(TheoryEnvironment(
        name="set theory plus",
        rules=df.definition_rules(definitions, lambda: holder["environment"]),
        declarations=df.definition_declarations(definitions),
        citable_titles=df.definition_titles(definitions),
    ))
    holder["environment"] = environment
    return environment


def _evidence_problem(definition):
    environment = _plus(definition)
    rule = next(r for r in environment.rules if isinstance(r, df.DefinitionRule) and r.definition is definition)
    return rule.evidence_problem()


_U, _SA, _SB = v("u"), v("A"), v("B")


def test_a_set_definition_says_which_objects_are_members_and_that_there_is_such_a_set():
    common = st.set_definition("Definition of common part", "Common", ("A", "B"),
                               fl.And(_in(_U, _SA), _in(_U, _SB)), df.ByRule(st.SeparationSchemaRule()))
    assert common.sentence() == "In(u, Common(A, B)) iff (In(u, A) and In(u, B))"
    assert df.show(common.existence.statement) == "exists Y, forall u, (In(u, Y) iff (In(u, A) and In(u, B)))"
    assert (common.symbol, common.kind, common.arity, common.type_name) == \
        ("Common", pl.DeclarationKind.FUNCTION, 2, "set operation")
    assert common.variables == ("u", "A", "B")
    assert common.parameters == ("A", "B")


def test_a_set_may_be_defined_by_a_property_that_a_set_bounds():
    common = st.set_definition("Definition of common part", "Common", ("A", "B"),
                               fl.And(_in(_U, _SA), _in(_U, _SB)), df.ByRule(st.SeparationSchemaRule()))
    assert _evidence_problem(common) is None
    environment = _plus(common)
    entries = pp.parse_proof_text(
        f"{DECLARATIONS}2. In(x, Common(A, B)) iff (In(x, A) and In(x, B)). (Definition of common part)\n",
        environment)[0]
    assert pl.Proof(entries).check_detailed()[0]


@pytest.mark.parametrize("name,property_,parameters", [
    ("the objects that are not members of A", fl.Not(_in(_U, _SA)), ("A",)),
    ("the objects that are not members of themselves", fl.Not(_in(_U, _U)), ()),
    ("all objects", fl.Equals(_U, _U), ()),
    ("the objects that are members of A or are not", fl.Or(_in(_U, _SA), fl.Not(_in(_U, _SA))), ("A",)),
])
def test_a_set_may_not_be_defined_by_a_property_that_no_set_bounds(name, property_, parameters):
    """Nothing says there is a set of the objects that are not members of A, or of
    all objects, or of those that are not members of themselves (Russell's): so a
    definition that names one fails its evidence, and cannot be cited."""
    definition = st.set_definition("Definition of that set", "That", parameters, property_,
                                   df.ByRule(st.SeparationSchemaRule()))
    problem = _evidence_problem(definition)
    assert problem is not None and problem.startswith("Separation does not accept exists Y, forall u, ")


def test_a_property_that_no_set_bounds_can_be_defined_as_a_property():
    """The same property is fine as a predicate: `Outside(x, A)` says that x is not a member of A."""
    outside = df.Definition(
        title="Definition of outside", symbol="Outside", variables=("x", "A"),
        definiendum=atom("Outside", v("x"), v("A")), definiens=fl.Not(_in(v("x"), v("A"))))
    entries = pp.parse_proof_text(
        f"{DECLARATIONS}2. Outside(x, A) iff not In(x, A). (Definition of outside)\n", _plus(outside))[0]
    assert pl.Proof(entries).check_detailed()[0]


def test_the_name_of_the_set_in_a_definitions_claim_is_not_one_the_property_uses():
    in_element = st.set_definition("Definition of Y element", "WithY", ("A",), _in(v("Y"), _SA),
                                   df.ByRule(st.SeparationSchemaRule()), element="Y")
    assert df.show(in_element.existence.statement) == "exists Y_1, forall Y, (In(Y, Y_1) iff In(Y, A))"
    in_parameter = st.set_definition("Definition of Y parameter", "WithY2", ("Y",), _in(_U, v("Y")),
                                     df.ByRule(st.SeparationSchemaRule()))
    assert df.show(in_parameter.existence.statement) == "exists Y_1, forall u, (In(u, Y_1) iff In(u, Y))"


def test_a_set_definition_is_a_definition_the_facility_checks():
    with pytest.raises(df.DefinitionError, match="the definiens uses Common, which it is defining"):
        st.set_definition("Definition of common part", "Common", ("A",), _in(_U, fn("Common", _SA)),
                          df.ByRule(st.SeparationSchemaRule()))
    with pytest.raises(df.DefinitionError, match="the definiens has B free"):
        st.set_definition("Definition of common part", "Common", ("A",), _in(_U, _SB),
                          df.ByRule(st.SeparationSchemaRule()))


# --------------------------------------------------------------------
# The symbols of the definitions cannot be declared again
# --------------------------------------------------------------------
#
# A definition is cited for a sentence about the symbol `Union` (or `Intersection`,
# ...) that set theory declares. A proof that could declare a function of its own
# under that name and cite the definition for it would be asserting the
# definition of the union of an arbitrary function. So a declaration under the
# name of one of the symbols, or of `In`, is refused, in every form a declaration
# takes and wherever it is written.

SYMBOLS_OF_THE_DEFINITIONS = [
    ("Union", "function"),
    ("Intersection", "function"),
    ("PowerSet", "function"),
    ("CartesianProduct", "function"),
    ("Pair", "function"),
    ("In", "predicate"),
]

DECLARATION_FORMS = {
    "a function": "1. Let A be any set, and {symbol} be a function. (Declaration)\n",
    "a typed function": (
        "1. Let A, P be any set. (Declaration)\n"
        "2. Let {symbol}: A -> P be a unary function. (Declaration)\n"
    ),
    "an object": "1. Let A be any set, and {symbol} be any object. (Declaration)\n",
    "a set": "1. Let A be any set, and {symbol} be any set. (Declaration)\n",
    "a predicate": "1. Let A be any set, and {symbol} be a predicate. (Declaration)\n",
    "a relation": "1. Let A be any set, and {symbol} be a relation on A. (Declaration)\n",
    "an arbitrary object": (
        "1. Let A be any set. (Declaration)\n"
        "2. forall {symbol}, {symbol} = {symbol}. (Universal Generalization from subproof below)\n"
        "begin subproof\n"
        " 2.0. let {symbol} be arbitrary. (Arbitrary)\n"
        " 2.1. {symbol} = {symbol}. (Reflexivity)\n"
        "end subproof\n"
    ),
}


@pytest.mark.parametrize("form", list(DECLARATION_FORMS))
@pytest.mark.parametrize("symbol,kind", SYMBOLS_OF_THE_DEFINITIONS)
def test_a_proof_cannot_declare_a_symbol_the_definitions_are_about(symbol, kind, form):
    message = _refusal(DECLARATION_FORMS[form].format(symbol=symbol))
    assert message is not None, f"a proof declared {symbol} as {form}"
    assert f"symbol '{symbol}' is already declared as {kind}" in message


@pytest.mark.parametrize("symbol,title,line", [
    ("union", "Definition of union", "In(x, union(A, B)) iff (In(x, A) or In(x, B))"),
    ("intersection", "Definition of intersection", "In(x, intersection(A, B)) iff (In(x, A) and In(x, B))"),
])
def test_a_function_declared_in_lower_case_is_another_symbol_and_gets_no_definition(symbol, title, line):
    """`union` is not `Union`: it is the proof's own function, of which nothing is
    said, and the definition of the union is not about it."""
    message = _refusal(
        f"1. Let {symbol} be a function, and A, B be any set, and x be any object. (Declaration)\n"
        f"2. {line}. ({title})\n"
    )
    assert message is not None
    assert f"'{title}' does not justify" in message
    assert "here neither side of the biconditional is a use of" in message


# --------------------------------------------------------------------
# The proof fixture
# --------------------------------------------------------------------

REFUSED_FOR = {
    "10": "'Definition of union' does not justify",
    "11": "'Definition of union' does not justify",
    "12": "'Definition of union' does not justify",
    "13": "'Definition of union' does not justify",
    "14": "'Definition of union' does not justify",
    "15": "'Definition of union' requires at most 0 cited line label(s), but 1 were given",
    "16": "'Definition of union' does not justify",
    "17": "function 'Union' expects arity 2, but is used with 3 argument(s)",
    "18": "'Definition of power set' does not justify",
    "19": "'Definition of power set' does not justify",
    "20": "'Definition of power set' does not justify",
    "21": "'Definition of power set' does not justify",
    "22": "'SetProperty' requires exactly 2 candidate premise(s)",
}


def test_the_definition_fixture_behaves_as_it_says():
    project = Path(__file__).resolve().parents[1]
    results = validator.check_file(project / "tests" / "testSetTheory" / "set_operation_definitions.txt")
    assert [result.proof_id for result in results] == [str(number) for number in range(1, 23)]
    assert all(result.passed for result in results), [result for result in results if not result.passed]
    valid = [result for result in results if result.expected_valid]
    refused = [result for result in results if not result.expected_valid]
    assert [result.proof_id for result in valid] == [str(number) for number in range(1, 10)]
    assert [result.proof_id for result in refused] == list(REFUSED_FOR)
    for result in refused:
        # Each invalid proof is refused for the reason it says, and not for some other
        # one (a parse error, an undeclared name).
        assert REFUSED_FOR[result.proof_id] in result.message, result
