"""Tests for the definition rules of the declared set operations.

`Union`, `Intersection`, `PowerSet`, `CartesianProduct` and `Pair` are declared
function symbols, and a declaration gives a symbol no meaning. Five zero-premise
rules give them theirs, each by one defining sentence, cited "(Definition of
union)", "(Definition of intersection)", "(Definition of power set)",
"(Definition of Cartesian product)" and "(Definition of ordered pair)":

    u in Union(S, T)              iff  u in S or u in T
    u in Intersection(S, T)       iff  u in S and u in T
    u in PowerSet(S)              iff  forall w, (w in u -> w in S)
    p in CartesianProduct(S, T)   iff  exists a, (a in S and exists b, (b in T and p = Pair(a, b)))
    Pair(a, b) = Pair(c, d)       iff  a = c and b = d

A rule accepts its sentence for any terms, with or without leading `forall`s, with
the biconditional either way round, and nothing else. Where the sentence has
quantifiers of its own (the power set and the product) a term must not mention a
variable they bind, or the quantifier would capture it and the line would say
something else.

The builders below write each sentence for the terms a test chooses, without the
rules' own helpers, so a test can say exactly which sentence it means. The
proofs that use the rules are in tests/testSetTheory/set_operation_definitions.txt,
which `test_the_definition_fixture_behaves_as_it_says` runs.
"""

import itertools
from pathlib import Path
from typing import Callable, NamedTuple

import pytest

from SyLoPy.source import ProofJustification as pj
from SyLoPy.source import validate_all_proofs as validator

from .support import fl, fn, mp, pl, pp, prop, st, c, v


def _in(element, set_term):
    return st.membership_formula(element, set_term)


def _union(u, s, t):
    return fl.Iff(_in(u, fn("Union", s, t)), fl.Or(_in(u, s), _in(u, t)))


def _intersection(u, s, t):
    return fl.Iff(_in(u, fn("Intersection", s, t)), fl.And(_in(u, s), _in(u, t)))


def _power_set(u, s, w="w"):
    member = v(w)
    return fl.Iff(_in(u, fn("PowerSet", s)),
                  fl.ForAll(w, fl.Implies(_in(member, u), _in(member, s))))


def _product(p, s, t, a="a", b="b"):
    first, second = v(a), v(b)
    return fl.Iff(_in(p, fn("CartesianProduct", s, t)),
                  fl.Exists(a, fl.And(_in(first, s), fl.Exists(b, fl.And(
                      _in(second, t), fl.Equals(p, fn("Pair", first, second)))))))


def _ordered_pair(a, b, x, y):
    return fl.Iff(fl.Equals(fn("Pair", a, b), fn("Pair", x, y)),
                  fl.And(fl.Equals(a, x), fl.Equals(b, y)))


class Definition(NamedTuple):
    key: str
    rule: pl.InferenceRule
    build: Callable[..., fl.Formula]
    arity: int  # how many terms the sentence is about
    citation: str


UNION = st.UnionDefinitionRule()
INTERSECTION = st.IntersectionDefinitionRule()
POWER_SET = st.PowerSetDefinitionRule()
PRODUCT = st.CartesianProductDefinitionRule()
ORDERED_PAIR = st.OrderedPairDefinitionRule()

DEFINITIONS = [
    Definition("union", UNION, _union, 3, "Definition of union"),
    Definition("intersection", INTERSECTION, _intersection, 3, "Definition of intersection"),
    Definition("power set", POWER_SET, _power_set, 2, "Definition of power set"),
    Definition("Cartesian product", PRODUCT, _product, 3, "Definition of Cartesian product"),
    Definition("ordered pair", ORDERED_PAIR, _ordered_pair, 4, "Definition of ordered pair"),
]
BY_KEY = {definition.key: definition for definition in DEFINITIONS}
KEYS = [definition.key for definition in DEFINITIONS]

# Terms the sentences may be about: none of them mentions a variable that a
# sentence's own quantifiers bind (w, a, b), so none is captured.
SET_A, SET_B, SET_C = c("A"), c("B"), c("C")
TERMS = {
    "a declared object": SET_A,
    "a variable": v("x"),
    "a function term": fn("f", c("a"), v("y")),
    "a set operation": fn("Union", SET_A, fn("PowerSet", SET_B)),
    "the empty set": st.EMPTY_SET,
}
SOME_PREMISE = fl.Equals(c("a"), c("b"))


def _canonical(definition):
    """The sentence for `x` and declared sets: the instance a proof cites."""
    if definition.key == "ordered pair":
        return definition.build(c("a"), c("b"), c("c"), c("d"))
    if definition.key == "power set":
        return definition.build(v("x"), SET_A)
    return definition.build(v("x"), SET_A, SET_B)


def _closed(definition, names):
    """The sentence about the variables `names`, with a `forall` for each,
    outermost first."""
    formula = definition.build(*[v(name) for name in names])
    for name in reversed(names):
        formula = fl.ForAll(name, formula)
    return formula


def _variable_names(definition):
    return [f"x{i}" for i in range(definition.arity)]


# --------------------------------------------------------------------
# What each rule accepts
# --------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_its_sentence_as_a_single_instance(key):
    definition = BY_KEY[key]
    assert definition.rule.applies([], _canonical(definition))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_its_sentence_with_a_forall_in_front_of_it(key):
    """The form `Set property` reads: `forall u, (u in Union(S, T) iff ...)`,
    with the first variable of the sentence (the element, or the first
    component) quantified and the rest terms."""
    definition = BY_KEY[key]
    names = _variable_names(definition)
    terms = [v(names[0])] + [c(f"K{i}") for i in range(1, definition.arity)]
    assert definition.rule.applies([], fl.ForAll(names[0], definition.build(*terms)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_its_sentence_closed_over_all_its_variables_in_any_order(key):
    definition = BY_KEY[key]
    names = _variable_names(definition)
    for order in itertools.permutations(names):
        assert definition.rule.applies([], _closed(definition, list(order))), order


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_a_forall_over_a_variable_the_sentence_does_not_mention(key):
    definition = BY_KEY[key]
    assert definition.rule.applies([], fl.ForAll("zz", _canonical(definition)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_the_biconditional_either_way_round(key):
    definition = BY_KEY[key]
    sentence = _canonical(definition)
    flipped = fl.Iff(sentence.right, sentence.left)
    assert definition.rule.applies([], flipped)
    assert definition.rule.applies([], fl.ForAll("x", flipped))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_accepts_any_terms_in_place_of_the_variables_of_its_sentence(key):
    definition = BY_KEY[key]
    for terms in itertools.product(TERMS.values(), repeat=definition.arity):
        assert definition.rule.applies([], definition.build(*terms)), [repr(t) for t in terms]


def test_the_power_set_rule_accepts_any_name_for_the_variable_of_the_subset_clause():
    for name in ("w", "z", "member", "__subset_element"):
        assert POWER_SET.applies([], _power_set(v("x"), SET_A, w=name)), name


def test_the_product_rule_accepts_any_names_for_its_two_bound_variables():
    for first, second in [("a", "b"), ("b", "a"), ("s", "t"), ("p0", "p1")]:
        assert PRODUCT.applies([], _product(v("x"), SET_A, SET_B, a=first, b=second)), (first, second)


def test_the_power_set_rule_accepts_what_the_subset_syntax_builds():
    sentence = fl.Iff(_in(v("u"), fn("PowerSet", SET_A)), st.subset_formula(v("u"), SET_A))
    assert POWER_SET.applies([], fl.ForAll("u", sentence))


def test_a_constant_spelled_like_a_bound_variable_is_not_captured():
    """Only a variable a quantifier binds is captured; a constant of the same
    spelling is another term."""
    assert POWER_SET.applies([], _power_set(c("w"), c("w"), w="w"))
    assert PRODUCT.applies([], _product(c("a"), c("a"), c("b"), a="a", b="b"))
    assert PRODUCT.applies([], _product(c("b"), c("b"), c("a"), a="a", b="b"))


# --------------------------------------------------------------------
# What they refuse
# --------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_a_rule_takes_no_cited_lines(key):
    definition = BY_KEY[key]
    sentence = _canonical(definition)
    assert not definition.rule.applies([SOME_PREMISE], sentence)
    assert not definition.rule.applies([sentence], sentence)


def test_each_rule_accepts_only_the_sentence_of_its_own_operation():
    for definition in DEFINITIONS:
        for other in DEFINITIONS:
            sentence = _canonical(other)
            assert definition.rule.applies([], sentence) == (definition is other), (definition.key, other.key)
            closed = _closed(other, _variable_names(other))
            assert definition.rule.applies([], closed) == (definition is other), (definition.key, other.key)


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_refuses_the_sentence_where_it_is_not_the_whole_line(key):
    """Only leading `forall`s are set aside; the sentence under anything else
    is another sentence."""
    definition = BY_KEY[key]
    sentence = _canonical(definition)
    other = fl.Equals(c("a"), c("b"))
    misses = {
        "under exists": fl.Exists("x", sentence),
        "under not": fl.Not(sentence),
        "as a conclusion": fl.Implies(other, sentence),
        "as a premise": fl.Implies(sentence, other),
        "as a conjunct": fl.And(sentence, other),
        "as a disjunct": fl.Or(sentence, other),
        "under exists under forall": fl.ForAll("x", fl.Exists("y", sentence)),
        "after a forall that follows a conjunction": fl.And(other, fl.ForAll("x", sentence)),
    }
    for description, formula in misses.items():
        assert not definition.rule.applies([], formula), description


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_refuses_one_direction_of_its_sentence(key):
    definition = BY_KEY[key]
    sentence = _canonical(definition)
    assert not definition.rule.applies([], fl.Implies(sentence.left, sentence.right))
    assert not definition.rule.applies([], fl.Implies(sentence.right, sentence.left))
    assert not definition.rule.applies([], fl.ForAll("x", fl.Implies(sentence.left, sentence.right)))


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_refuses_things_that_are_not_formulas_of_its_shape(key):
    rule = BY_KEY[key].rule
    assert not rule.applies([], fl.Equals(c("a"), c("b")))
    assert not rule.applies([], prop("P"))
    assert not rule.applies([], fl.Iff(prop("P"), prop("Q")))
    assert not rule.applies([], fl.ForAll("x", prop("P")))
    assert not rule.applies([], _in(c("a"), SET_A))


def _union_near_misses():
    x, y = v("x"), v("y")
    a, b, k = SET_A, SET_B, SET_C
    union = fn("Union", a, b)
    return {
        "and for or": fl.Iff(_in(x, union), fl.And(_in(x, a), _in(x, b))),
        "about another element on the right": fl.Iff(_in(x, union), fl.Or(_in(y, a), _in(y, b))),
        "the first set twice": fl.Iff(_in(x, union), fl.Or(_in(x, a), _in(x, a))),
        "the second set twice": fl.Iff(_in(x, union), fl.Or(_in(x, b), _in(x, b))),
        "the sets in the other order": fl.Iff(_in(x, union), fl.Or(_in(x, b), _in(x, a))),
        "a third disjunct": fl.Iff(_in(x, union), fl.Or(_in(x, a), _in(x, b), _in(x, k))),
        "a negated disjunct": fl.Iff(_in(x, union), fl.Or(fl.Not(_in(x, a)), _in(x, b))),
        "a single disjunct": fl.Iff(_in(x, union), _in(x, a)),
        "the other union": fl.Iff(_in(x, fn("Union", a, k)), fl.Or(_in(x, a), _in(x, b))),
        "about the union's own members": fl.Iff(_in(a, union), fl.Or(_in(x, a), _in(x, b))),
        "membership in a set, not the union": fl.Iff(_in(x, a), fl.Or(_in(x, a), _in(x, b))),
        "membership the other way round": fl.Iff(_in(union, x), fl.Or(_in(x, a), _in(x, b))),
        "a union of three sets": fl.Iff(_in(x, fn("Union", a, b, k)), fl.Or(_in(x, a), _in(x, b))),
        "a union of one set": fl.Iff(_in(x, fn("Union", a)), fl.Or(_in(x, a), _in(x, b))),
        "a constant named Union": fl.Iff(_in(x, c("Union")), fl.Or(_in(x, a), _in(x, b))),
        "another function": fl.Iff(_in(x, fn("Join", a, b)), fl.Or(_in(x, a), _in(x, b))),
        "an equation, not a membership": fl.Iff(fl.Equals(x, union), fl.Or(_in(x, a), _in(x, b))),
        "two unions": fl.Iff(_in(x, union), _in(x, fn("Union", b, a))),
    }


def _intersection_near_misses():
    x, y = v("x"), v("y")
    a, b, k = SET_A, SET_B, SET_C
    meet = fn("Intersection", a, b)
    return {
        "or for and": fl.Iff(_in(x, meet), fl.Or(_in(x, a), _in(x, b))),
        "about another element on the right": fl.Iff(_in(x, meet), fl.And(_in(y, a), _in(y, b))),
        "the first set twice": fl.Iff(_in(x, meet), fl.And(_in(x, a), _in(x, a))),
        "the sets in the other order": fl.Iff(_in(x, meet), fl.And(_in(x, b), _in(x, a))),
        "a third conjunct": fl.Iff(_in(x, meet), fl.And(_in(x, a), _in(x, b), _in(x, k))),
        "a negated conjunct": fl.Iff(_in(x, meet), fl.And(_in(x, a), fl.Not(_in(x, b)))),
        "a single conjunct": fl.Iff(_in(x, meet), _in(x, a)),
        "the union, as a name": fl.Iff(_in(x, fn("Union", a, b)), fl.And(_in(x, a), _in(x, b))),
        "an intersection of three sets": fl.Iff(_in(x, fn("Intersection", a, b, k)), fl.And(_in(x, a), _in(x, b))),
    }


def _power_set_near_misses():
    x, z = v("x"), v("z")
    a, b = SET_A, SET_B
    power = fn("PowerSet", a)
    member = fl.Implies(_in(z, x), _in(z, a))
    return {
        "membership, not subset": fl.Iff(_in(x, power), _in(x, a)),
        "the subset clause the wrong way round": fl.Iff(_in(x, power), fl.ForAll("z", fl.Implies(_in(z, a), _in(z, x)))),
        "a subset of another set": fl.Iff(_in(x, power), fl.ForAll("z", fl.Implies(_in(z, x), _in(z, b)))),
        "the power set of another set": fl.Iff(_in(x, fn("PowerSet", b)), fl.ForAll("z", member)),
        "the clause about the power set itself": fl.Iff(_in(x, power), fl.ForAll("z", fl.Implies(_in(z, power), _in(z, a)))),
        "exists for forall": fl.Iff(_in(x, power), fl.Exists("z", member)),
        "and for implies": fl.Iff(_in(x, power), fl.ForAll("z", fl.And(_in(z, x), _in(z, a)))),
        "iff for implies": fl.Iff(_in(x, power), fl.ForAll("z", fl.Iff(_in(z, x), _in(z, a)))),
        "a clause about a free variable": fl.Iff(_in(x, power), fl.Implies(_in(z, x), _in(z, a))),
        "a member of the subset, not the set": fl.Iff(_in(x, power), fl.ForAll("z", fl.Implies(_in(z, x), _in(x, a)))),
        "a power set of two sets": fl.Iff(_in(x, fn("PowerSet", a, b)), fl.ForAll("z", member)),
        "a doubly bounded clause": fl.Iff(_in(x, power), fl.ForAll("z", fl.ForAll("y", fl.Implies(_in(z, x), _in(z, a))))),
    }


def _product_near_misses():
    p = v("p")
    a, b = SET_A, SET_B
    first, second = v("s"), v("t")
    product = fn("CartesianProduct", a, b)
    pair = fn("Pair", first, second)
    inner = fl.And(_in(second, b), fl.Equals(p, pair))

    def clause(first_set=a, inner_formula=inner, outer=fl.Exists):
        """`outer s, (s in first_set and exists t, inner_formula)`"""
        return outer("s", fl.And(_in(first, first_set), fl.Exists("t", inner_formula)))

    return {
        "the components in the wrong sets": fl.Iff(_in(p, product), clause(first_set=b, inner_formula=fl.And(_in(second, a), fl.Equals(p, pair)))),
        "the pair of the components in the other order": fl.Iff(_in(p, product), clause(
            inner_formula=fl.And(_in(second, b), fl.Equals(p, fn("Pair", second, first))))),
        "the pair not tied to the element": fl.Iff(_in(p, product), clause(
            inner_formula=fl.And(_in(second, b), fl.Equals(pair, fn("Pair", second, first))))),
        "forall for exists on the first component": fl.Iff(_in(p, product), clause(outer=fl.ForAll)),
        "forall for exists on the second component": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a), fl.ForAll("t", inner)))),
        "implies for and on the first component": fl.Iff(_in(p, product), fl.Exists("s", fl.Implies(_in(first, a), fl.Exists("t", inner)))),
        "implies for and on the second component": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a), fl.Exists("t", fl.Implies(_in(second, b), fl.Equals(p, pair)))))),
        "one quantifier for both components": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a), _in(first, b), fl.Equals(p, fn("Pair", first, first))))),
        "a flat conjunction under two quantifiers": fl.Iff(_in(p, product), fl.Exists("s", fl.Exists("t", fl.And(_in(first, a), _in(second, b), fl.Equals(p, pair))))),
        "the pair an unordered set": fl.Iff(_in(p, product), clause(inner_formula=fl.And(_in(second, b), fl.Equals(p, fn("Union", first, second))))),
        "the product of other sets": fl.Iff(_in(p, fn("CartesianProduct", b, a)), clause()),
        "a product of one set": fl.Iff(_in(p, fn("CartesianProduct", a)), clause()),
        "no second membership": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a), fl.Exists("t", fl.Equals(p, pair))))),
        "no first membership": fl.Iff(_in(p, product), fl.Exists("s", fl.And(fl.Exists("t", inner), _in(first, a)))),
        "a conjunct too many": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a), fl.Exists("t", inner), _in(first, b)))),
        "a conjunction of one": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a)))),
        "a conjunction of none": fl.Iff(_in(p, product), fl.Exists("s", fl.And())),
        "a free component": fl.Iff(_in(p, product), fl.Exists("s", fl.And(_in(first, a), fl.Exists("t", fl.And(_in(second, b), fl.Equals(p, fn("Pair", first, v("u")))))))),
    }


def _ordered_pair_near_misses():
    a, b, x, y = c("a"), c("b"), c("x"), c("y")
    equal = fl.Equals(fn("Pair", a, b), fn("Pair", x, y))
    return {
        "components crossed": fl.Iff(equal, fl.And(fl.Equals(a, y), fl.Equals(b, x))),
        "only the first components": fl.Iff(equal, fl.Equals(a, x)),
        "only the second components": fl.Iff(equal, fl.Equals(b, y)),
        "or for and": fl.Iff(equal, fl.Or(fl.Equals(a, x), fl.Equals(b, y))),
        "the components in the other order": fl.Iff(equal, fl.And(fl.Equals(b, y), fl.Equals(a, x))),
        "the equations the other way round": fl.Iff(equal, fl.And(fl.Equals(x, a), fl.Equals(y, b))),
        "a component equal to itself": fl.Iff(equal, fl.And(fl.Equals(a, a), fl.Equals(b, y))),
        "the first pair on both sides": fl.Iff(fl.Equals(fn("Pair", a, b), fn("Pair", a, b)), fl.And(fl.Equals(a, x), fl.Equals(b, y))),
        "a third equation": fl.Iff(equal, fl.And(fl.Equals(a, x), fl.Equals(b, y), fl.Equals(a, b))),
        "a pair equal to a non-pair": fl.Iff(fl.Equals(fn("Pair", a, b), x), fl.And(fl.Equals(a, x), fl.Equals(b, y))),
        "the unordered pair": fl.Iff(fl.Equals(fn("Union", a, b), fn("Union", x, y)), fl.And(fl.Equals(a, x), fl.Equals(b, y))),
        "a triple": fl.Iff(fl.Equals(fn("Pair", a, b, x), fn("Pair", x, y, a)), fl.And(fl.Equals(a, x), fl.Equals(b, y))),
        "a single": fl.Iff(fl.Equals(fn("Pair", a), fn("Pair", x)), fl.And(fl.Equals(a, x), fl.Equals(b, y))),
        "an inequation": fl.Iff(fl.Not(equal), fl.And(fl.Equals(a, x), fl.Equals(b, y))),
    }


NEAR_MISSES = {
    "union": _union_near_misses(),
    "intersection": _intersection_near_misses(),
    "power set": _power_set_near_misses(),
    "Cartesian product": _product_near_misses(),
    "ordered pair": _ordered_pair_near_misses(),
}


@pytest.mark.parametrize("key,description", [
    (key, description) for key, misses in NEAR_MISSES.items() for description in misses
])
def test_a_rule_refuses_a_sentence_close_to_its_own(key, description):
    formula = NEAR_MISSES[key][description]
    assert not BY_KEY[key].rule.applies([], formula)
    assert not BY_KEY[key].rule.applies([], fl.ForAll("x", formula))


def test_the_near_misses_are_about_the_rule_that_refuses_them():
    """Guard the tables: each near miss is refused by every rule, and not only
    because it was filed under the wrong one."""
    for key, misses in NEAR_MISSES.items():
        for description, formula in misses.items():
            for definition in DEFINITIONS:
                assert not definition.rule.applies([], formula), (key, description, definition.key)


# --------------------------------------------------------------------
# Variable capture: the power set and the Cartesian product
# --------------------------------------------------------------------

POWER_SET_CAPTURED = {
    "the element is the clause's variable": (v("w"), SET_A),
    "the set is the clause's variable": (v("u"), v("w")),
    "an element that mentions the clause's variable": (fn("f", v("w")), SET_A),
    "a set that mentions the clause's variable": (v("u"), fn("g", c("a"), v("w"))),
    "both mention it": (fn("f", v("w")), fn("g", v("w"))),
}


@pytest.mark.parametrize("description", list(POWER_SET_CAPTURED))
def test_the_power_set_rule_refuses_a_term_the_subset_clause_would_capture(description):
    element, set_term = POWER_SET_CAPTURED[description]
    assert not POWER_SET.applies([], _power_set(element, set_term, w="w"))
    # Written with the clause's variable renamed, the same terms are not captured.
    assert POWER_SET.applies([], _power_set(element, set_term, w="z"))


PRODUCT_CAPTURED = {
    "the element is the first bound variable": (v("a"), SET_A, SET_B),
    "the element is the second bound variable": (v("b"), SET_A, SET_B),
    "the first set is the first bound variable": (v("p"), v("a"), SET_B),
    "the first set is the second bound variable": (v("p"), v("b"), SET_B),
    "the second set is the first bound variable": (v("p"), SET_A, v("a")),
    "the second set is the second bound variable": (v("p"), SET_A, v("b")),
    "an element that mentions a bound variable": (fn("f", v("a")), SET_A, SET_B),
    "a set that mentions a bound variable": (v("p"), fn("g", c("c"), v("b")), SET_B),
}


@pytest.mark.parametrize("description", list(PRODUCT_CAPTURED))
def test_the_product_rule_refuses_a_term_its_quantifiers_would_capture(description):
    element, first, second = PRODUCT_CAPTURED[description]
    assert not PRODUCT.applies([], _product(element, first, second, a="a", b="b"))
    # Written with the bound variables renamed, the same terms are not captured.
    assert PRODUCT.applies([], _product(element, first, second, a="m", b="n"))


def test_the_product_rule_refuses_a_term_captured_by_either_quantifier_alone():
    """The second set is under both quantifiers and the first only under the
    outer one, but a name that is bound at all is refused wherever it occurs."""
    assert not PRODUCT.applies([], _product(v("p"), v("n"), SET_B, a="m", b="n"))
    assert not PRODUCT.applies([], _product(v("p"), v("m"), SET_B, a="m", b="n"))
    assert not PRODUCT.applies([], _product(v("p"), SET_A, v("n"), a="m", b="n"))
    assert not PRODUCT.applies([], _product(v("n"), SET_A, SET_B, a="m", b="n"))


def test_the_product_rule_refuses_the_same_name_for_both_bound_variables():
    """The inner quantifier would shadow the outer one, and the sentence would
    say that the element is a pair (a, a) with a in the second set."""
    assert not PRODUCT.applies([], _product(v("p"), SET_A, SET_B, a="a", b="a"))
    assert not PRODUCT.applies([], _product(v("p"), SET_A, SET_B, a="m", b="m"))


# --------------------------------------------------------------------
# Registration and citation
# --------------------------------------------------------------------

def test_each_rule_is_registered_in_set_theory_once():
    names = [rule.name for rule in st.SET_THEORY_ENVIRONMENT.rules]
    for definition in DEFINITIONS:
        assert names.count(definition.rule.name) == 1, definition.rule.name


def test_the_rules_take_no_cited_lines_by_their_declared_arity():
    for definition in DEFINITIONS:
        assert definition.rule.premise_arity == 0, definition.key


def test_the_rule_names_and_citations_are_distinct():
    assert len({definition.rule.name for definition in DEFINITIONS}) == len(DEFINITIONS)
    assert len({definition.rule.citation for definition in DEFINITIONS}) == len(DEFINITIONS)
    assert [definition.rule.citation for definition in DEFINITIONS] == [definition.citation for definition in DEFINITIONS]


@pytest.mark.parametrize("citation,rule_name", [
    ("Definition of union", "UnionDefinition"),
    ("union definition", "UnionDefinition"),
    ("DEFINITION OF UNION", "UnionDefinition"),
    ("Definition of intersection", "IntersectionDefinition"),
    ("Intersection definition", "IntersectionDefinition"),
    ("Definition of power set", "PowerSetDefinition"),
    ("Power set definition", "PowerSetDefinition"),
    ("Definition of Cartesian product", "CartesianProductDefinition"),
    ("Definition of cartesian product", "CartesianProductDefinition"),
    ("Cartesian product definition", "CartesianProductDefinition"),
    ("Definition of ordered pair", "OrderedPairDefinition"),
    ("Ordered pair definition", "OrderedPairDefinition"),
    ("Ordered pair equality", "OrderedPairDefinition"),
])
def test_each_spelling_cites_its_rule(citation, rule_name):
    kind, placeholder, refs = pj.parse_justification(citation)
    assert (kind, placeholder.name, refs) == ("rule", rule_name, [])


def test_a_rule_is_cited_by_the_citation_it_declares():
    for definition in DEFINITIONS:
        kind, placeholder, _ = pj.parse_justification(definition.rule.citation)
        assert (kind, placeholder.name) == ("rule", definition.rule.name)


# --------------------------------------------------------------------
# Cited from proof text
# --------------------------------------------------------------------

def _check(text):
    entries = pp.parse_proof_text(text)[0]
    return pl.Proof(entries).check_detailed()


DECLARATIONS = "1. Let A, B be any set, and x, p, a, b, c, d be any object. (Declaration)\n"


@pytest.mark.parametrize("line,citation", [
    ("forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B)))", "Definition of union"),
    ("x is in A union B iff (x is in A or x is in B)", "Definition of union"),
    ("(x is in A or x is in B) iff x is in A union B", "Union definition"),
    ("forall u, (In(u, Intersection(A, B)) iff (In(u, A) and In(u, B)))", "Definition of intersection"),
    ("x is in A intersection B iff (x is in A and x is in B)", "Intersection definition"),
    ("forall u, (In(u, PowerSet(A)) iff u subseteq A)", "Definition of power set"),
    ("x is in the power set of A iff x is a subset of A", "Power set definition"),
    ("forall q, (q is in A cross B iff exists s in A, exists t in B, q = pair(s, t))", "Definition of Cartesian product"),
    ("p is in A cross B iff (exists s in A, exists t in B, p = pair(s, t))", "Cartesian product definition"),
    ("pair(a, b) = pair(c, d) iff (a = c and b = d)", "Definition of ordered pair"),
    ("Pair(a, b) = Pair(c, d) iff (a = c and b = d)", "Ordered pair equality"),
])
def test_a_proof_cites_each_definition_in_the_forms_it_is_written(line, citation):
    ok, err = _check(f"{DECLARATIONS}2. {line}. ({citation})\n")
    assert ok, err


def test_a_proof_cites_a_definition_for_a_term_of_the_proof():
    ok, err = _check(
        "1. Let A, B be any set. (Declaration)\n"
        "2. forall u, (In(u, Union(Union(A, B), EmptySet)) iff (In(u, Union(A, B)) or In(u, EmptySet))). (Definition of union)\n"
    )
    assert ok, err


@pytest.mark.parametrize("line,citation,rule_name,statement", [
    ("In(x, Union(A, B)) iff (In(x, A) and In(x, B))", "Definition of union",
     "UnionDefinition", "forall u, (In(u, Union(S, T)) iff (In(u, S) or In(u, T)))"),
    ("In(x, Intersection(A, B)) iff (In(x, A) or In(x, B))", "Definition of intersection",
     "IntersectionDefinition", "forall u, (In(u, Intersection(S, T)) iff (In(u, S) and In(u, T)))"),
    ("In(x, PowerSet(A)) iff In(x, A)", "Definition of power set",
     "PowerSetDefinition", "forall u, (In(u, PowerSet(S)) iff forall w, (In(w, u) -> In(w, S)))"),
    ("In(p, CartesianProduct(A, B)) iff In(p, A)", "Definition of Cartesian product",
     "CartesianProductDefinition", "exists a in S, exists b in T, p = Pair(a, b)"),
    ("Pair(a, b) = Pair(c, d) iff a = c", "Definition of ordered pair",
     "OrderedPairDefinition", "Pair(a, b) = Pair(c, d) iff (a = c and b = d)"),
])
def test_a_refused_citation_names_the_rule_and_says_what_it_is_cited_for(line, citation, rule_name, statement):
    ok, err = _check(f"{DECLARATIONS}2. {line}. ({citation})\n")
    assert not ok
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert rule_name in err.detail
    assert f"{citation} is cited for the sentence" in err.detail
    assert statement in err.detail
    reason = next(d.rule.reason for d in DEFINITIONS if d.rule.name == rule_name)
    assert reason and reason in err.detail


@pytest.mark.parametrize("key", KEYS)
def test_a_rule_asked_to_explain_a_citation_with_lines_says_it_takes_none(key):
    definition = BY_KEY[key]
    message = definition.rule.explain_in_context([SOME_PREMISE], _canonical(definition), None)
    assert message == f"{definition.citation} takes no cited premises."


@pytest.mark.parametrize("line,citation", [
    ("In(x, Union(A, B)) iff (In(x, A) or In(x, B))", "Definition of union from 2"),
    ("In(x, Intersection(A, B)) iff (In(x, A) and In(x, B))", "Definition of intersection from 2"),
    ("In(x, PowerSet(A)) iff x subseteq A", "Definition of power set from 2"),
    ("p is in A cross B iff (exists s in A, exists t in B, p = pair(s, t))", "Definition of Cartesian product from 2"),
    ("Pair(a, b) = Pair(c, d) iff (a = c and b = d)", "Definition of ordered pair from 2"),
])
def test_a_definition_cited_with_a_line_is_refused(line, citation):
    ok, err = _check(f"{DECLARATIONS}2. In(x, A). (Premise)\n3. {line}. ({citation})\n")
    assert not ok
    assert err.category == pl.CATEGORY_ARITY_MISMATCH


def test_a_captured_variable_is_refused_with_the_reason():
    ok, err = _check(
        "1. Let A be any set. (Declaration)\n"
        "2. forall w, (In(w, PowerSet(A)) iff (forall w, (In(w, w) -> In(w, A)))). (Definition of power set)\n"
    )
    assert not ok
    assert "must not occur free in u or S" in err.detail
    ok, err = _check(
        "1. Let A, B be any set. (Declaration)\n"
        "2. forall a, (In(a, CartesianProduct(A, B)) iff (exists a, (In(a, A) and exists b, (In(b, B) and a = Pair(a, b))))). "
        "(Definition of Cartesian product)\n"
    )
    assert not ok
    assert "must differ and must not occur free in p, S or T" in err.detail


def test_the_definition_makes_the_union_of_a_declared_term_usable_by_set_property():
    """The characterization form is what `Set property` reads: from it and a
    member of A, the line says the member is in the union."""
    ok, err = _check(
        "1. Let A, B be any set, and x be any object. (Declaration)\n"
        "2. In(x, A). (Premise)\n"
        "3. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)\n"
        "4. In(x, Union(A, B)). (Set property from 3, 2)\n"
    )
    assert ok, err


def test_a_member_of_a_union_is_not_a_member_without_the_definition():
    """Without the definition the symbol means nothing: the same step is refused."""
    ok, err = _check(
        "1. Let A, B be any set, and x be any object. (Declaration)\n"
        "2. In(x, A). (Premise)\n"
        "3. In(x, Union(A, B)). (Set property from 2)\n"
    )
    assert not ok


def test_the_definitions_are_available_where_set_theory_is_extended():
    text = (
        "Use discrete math.\n\n"
        "# 1\n## Proof that\n"
        "1. Let A, B be any set. (Declaration)\n"
        "2. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)\n"
    )
    assert [(number, ok) for number, _expected, ok, _message, _crashed in mp.run_multi_proof_file(text)] == [("1", True)]


# --------------------------------------------------------------------
# The proof fixture
# --------------------------------------------------------------------

def test_the_definition_fixture_behaves_as_it_says():
    project = Path(__file__).resolve().parents[1]
    results = validator.check_file(project / "tests" / "testSetTheory" / "set_operation_definitions.txt")
    assert [result.proof_id for result in results] == [str(number) for number in range(1, 35)]
    assert all(result.passed for result in results), [result for result in results if not result.passed]
    refused = [result for result in results if not result.expected_valid]
    valid = [result for result in results if result.expected_valid]
    assert (len(valid), len(refused)) == (13, 21)
    rule_names = [definition.rule.name for definition in DEFINITIONS]
    for result in refused:
        # Each invalid proof is refused by one of the definition rules, and not for
        # some other reason (a parse error, an undeclared name).
        assert any(f"'{name}'" in result.message for name in rule_names), result
