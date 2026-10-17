"""Tests for the named axiom-citation rules `UnionAxiomRule`,
`PowerSetAxiomRule` and `InfinityAxiomRule` (cited `(Axiom of union)`,
`(Axiom of power set)`, `(Axiom of infinity)`).

Each rule is a zero-premise shape check, like `SeparationSchemaRule`: the
cited formula must have the shape the axiom allows, and the rule introduces
nothing. Union and Power Set take the axiom either in full (`forall X, exists
Y, ...`) or, like `PairingAxiomRule`, already instantiated at a term of the
proof (`exists Y, ...`). `PairingAxiomRule` itself is covered in
`test_set_axioms.py`, `test_pairing_witness.py` and `test_set_property.py`.

The builders below write each axiom with the names of its bound variables as
parameters, so a test can say exactly which shape it means.
"""

from pathlib import Path

import pytest

from .support import pl, fl, tl, mp, pp, st, c, v


def _in(element, set_term):
    return st.membership_formula(element, set_term)


def _union(set_term=None, *, x="X", y="Y", u="u", w="v"):
    """`forall x, exists y, forall u, (u in y <-> exists w, (w in x and u in w))`.

    Given `set_term`, the instance for that term instead: no `forall x`, and
    `set_term` where `x` stood."""
    U, W, Y = v(u), v(w), v(y)
    parameter = v(x) if set_term is None else set_term
    body = fl.Exists(y, fl.ForAll(u, fl.Iff(
        _in(U, Y),
        fl.Exists(w, fl.And(_in(W, parameter), _in(U, W))),
    )))
    return body if set_term is not None else fl.ForAll(x, body)


def _power_set(set_term=None, *, x="X", y="Y", u="u", w=None):
    """`forall x, exists y, forall u, (u in y <-> u subset x)`, or the instance
    for `set_term`. `w` names the bound variable of the written-out subset
    clause; left out, it is whatever `u subset x` builds in a proof."""
    U, Y = v(u), v(y)
    parameter = v(x) if set_term is None else set_term
    if w is None:
        clause = st.subset_formula(U, parameter)
    else:
        W = v(w)
        clause = fl.ForAll(w, fl.Implies(_in(W, U), _in(W, parameter)))
    body = fl.Exists(y, fl.ForAll(u, fl.Iff(_in(U, Y), clause)))
    return body if set_term is not None else fl.ForAll(x, body)


def _infinity(x="X", y="y", s="S", u="u", *, empty=st.EMPTY_SET, container=None,
              guard=None, member=None, successor=None, target=None, closure=fl.Implies,
              x_quantifier=fl.Exists, y_quantifier=fl.ForAll, s_quantifier=fl.Exists,
              u_quantifier=fl.ForAll):
    """`exists x, (0 in x and forall y, (y in x -> exists s, (forall u, (u in s <->
    (u in y or u = y)) and s in x)))`, with the pieces a test wants to break
    as keyword arguments: `empty` and `container` for `0 in x`, `guard` for
    `y in x`, `successor` for the biconditional, `member` and `target` for `s
    in x`, `closure` for the connective after `forall y`, and the four
    quantifiers."""
    X, Y, S, U = v(x), v(y), v(s), v(u)
    if successor is None:
        successor = fl.Iff(_in(U, S), fl.Or(_in(U, Y), fl.Equals(U, Y)))
    return x_quantifier(x, fl.And(
        _in(empty, X if container is None else container),
        y_quantifier(y, closure(
            _in(Y, X) if guard is None else guard,
            s_quantifier(s, fl.And(
                u_quantifier(u, successor),
                _in(S if member is None else member, X if target is None else target),
            )),
        )),
    ))


UNION = st.UnionAxiomRule()
POWER_SET = st.PowerSetAxiomRule()
INFINITY = st.InfinityAxiomRule()

A = c("A")
SOME_PREMISE = fl.Equals(c("a"), c("a"))


def _binder_ids(names):
    return ",".join(f"{key}={value}" for key, value in names.items())


def _near_miss_params(make):
    """One pytest case for each near miss of the universal form and of the
    instance for `A`."""
    return (
        [pytest.param(None, name, id=f"universal: {name}") for name in make()]
        + [pytest.param(A, name, id=f"instance: {name}") for name in make(A)]
    )


# Terms an instance of the union or power set axiom may be about: anything
# that does not mention the instance's own bound variables.
SET_TERMS = {
    "a declared set": A,
    "a variable": v("x"),
    "a function term": tl.FunctionTerm("f", [c("a")]),
    "the empty set": st.EMPTY_SET,
    "a constant spelled like a binder": c("Y"),
}

# Terms that mention a variable the instance itself binds, which that binder
# would capture: not instances of the axiom at all. The binders of an instance
# of the union axiom are Y, u and v; of the power set axiom, Y, u and the
# subset clause's variable (here w).
UNION_CAPTURED = {
    "Y": v("Y"),
    "u": v("u"),
    "v": v("v"),
    "f(Y)": tl.FunctionTerm("f", [v("Y")]),
    "f(u)": tl.FunctionTerm("f", [v("u")]),
    "g(a, v)": tl.FunctionTerm("g", [c("a"), v("v")]),
}

POWER_SET_CAPTURED = {
    "Y": v("Y"),
    "u": v("u"),
    "w": v("w"),
    "f(Y)": tl.FunctionTerm("f", [v("Y")]),
    "f(u)": tl.FunctionTerm("f", [v("u")]),
    "g(a, w)": tl.FunctionTerm("g", [c("a"), v("w")]),
}


# --------------------------------------------------------------------
# Union: the universal axiom
# --------------------------------------------------------------------

def test_union_accepts_the_universal_axiom():
    assert UNION.applies([], _union())
    assert UNION.applies([], st.UNION_AXIOM)


def test_union_accepts_any_names_for_its_binders():
    assert UNION.applies([], _union(x="S", y="T", u="z", w="w"))


def test_union_takes_no_cited_lines():
    assert not UNION.applies([SOME_PREMISE], _union())
    assert not UNION.applies([_union()], _union())
    assert not UNION.applies([SOME_PREMISE], _union(A))


def _union_near_misses(instance_of=None):
    """Shapes close to the union axiom -- or, given `instance_of`, to its
    instance for that term -- that are not it."""
    S = v("X") if instance_of is None else instance_of
    Y, U, W = v("Y"), v("u"), v("v")

    def wrap(inner, new_set=fl.Exists, element=fl.ForAll):
        body = new_set("Y", element("u", inner))
        return body if instance_of is not None else fl.ForAll("X", body)

    standard = fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(W, S), _in(U, W))))
    misses = {
        "every set is the union, not some set": wrap(standard, new_set=fl.ForAll),
        "some element, not every element, is in the union": wrap(standard, element=fl.Exists),
        "membership target swapped": wrap(fl.Iff(_in(Y, U), fl.Exists("v", fl.And(_in(W, S), _in(U, W))))),
        "conjuncts reversed": wrap(fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(U, W), _in(W, S))))),
        "or for and": wrap(fl.Iff(_in(U, Y), fl.Exists("v", fl.Or(_in(W, S), _in(U, W))))),
        "implication for iff": wrap(fl.Implies(_in(U, Y), fl.Exists("v", fl.And(_in(W, S), _in(U, W))))),
        "the converse only": wrap(fl.Implies(fl.Exists("v", fl.And(_in(W, S), _in(U, W))), _in(U, Y))),
        "forall for exists": wrap(fl.Iff(_in(U, Y), fl.ForAll("v", fl.And(_in(W, S), _in(U, W))))),
        "the members of the set, not of its members": wrap(fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(W, S), _in(W, U))))),
        "a third conjunct": wrap(fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(W, S), _in(U, W), _in(U, S))))),
        "no inner quantifier": wrap(fl.Iff(_in(U, Y), fl.And(_in(W, S), _in(U, W)))),
        "bare membership": wrap(_in(U, Y)),
        "membership of another element in the new set": wrap(
            fl.Iff(_in(c("a"), Y), fl.Exists("v", fl.And(_in(W, S), _in(U, W))))),
        "membership in a set other than the new one": wrap(
            fl.Iff(_in(U, c("Z")), fl.Exists("v", fl.And(_in(W, S), _in(U, W))))),
        "u in the set itself, not in a member of it": wrap(
            fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(W, S), _in(U, S))))),
        "the first conjunct is about u, not v": wrap(
            fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(U, S), _in(U, W))))),
        "u is missing from the second conjunct": wrap(
            fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(W, S), _in(W, W))))),
    }
    if instance_of is None:
        # Any term is an instance of the axiom, so this one is a near miss
        # only of the universal form.
        misses["an unrelated set in place of X"] = wrap(
            fl.Iff(_in(U, Y), fl.Exists("v", fl.And(_in(W, c("Z")), _in(U, W)))))
    return misses


@pytest.mark.parametrize("instance_of,name", _near_miss_params(_union_near_misses))
def test_union_rejects_a_near_miss(instance_of, name):
    assert not UNION.applies([], _union_near_misses(instance_of)[name])


@pytest.mark.parametrize("names", [
    dict(y="X"),            # the new set is named like the parameter
    dict(u="X"),
    dict(u="Y"),
    dict(w="X"),
    dict(w="Y"),
    dict(w="u"),
], ids=_binder_ids)
def test_union_rejects_binders_that_share_a_name(names):
    assert not UNION.applies([], _union(**names))


def test_union_rejects_things_that_are_not_formulas_of_its_shape():
    assert not UNION.applies([], fl.Equals(c("a"), c("b")))
    assert not UNION.applies([], fl.Not(_union()))
    assert not UNION.applies([], _power_set())
    assert not UNION.applies([], fl.Not(_union(A)))


# --------------------------------------------------------------------
# Union: the instance for a set of the proof
# --------------------------------------------------------------------
#
# Like `PairingAxiomRule` and `SeparationSchemaRule`, the rule takes the
# axiom already instantiated -- `exists Y, forall u, (u in Y <-> exists v,
# (v in S and u in v))` for a term S outside the binders, with no `forall X`
# in front -- so a proof cites `(Axiom of union)` for the set it means
# without writing the axiom out in full, or instantiating it in a second line.

@pytest.mark.parametrize("name", sorted(SET_TERMS))
def test_union_accepts_the_instance_for_a_set_term(name):
    assert UNION.applies([], _union(SET_TERMS[name]))


def test_union_accepts_any_names_for_the_binders_of_an_instance():
    assert UNION.applies([], _union(A, y="T", u="z", w="w"))


@pytest.mark.parametrize("name", sorted(SET_TERMS))
def test_the_union_instance_is_what_universal_instantiation_gives(name):
    term = SET_TERMS[name]
    instantiated = fl.substitute_in_formula(st.UNION_AXIOM.body, "X", term)
    assert pl._ast_eq(instantiated, _union(term))
    assert UNION.applies([], instantiated)


@pytest.mark.parametrize("name", sorted(UNION_CAPTURED))
def test_union_rejects_an_instance_whose_set_term_a_binder_would_capture(name):
    assert not UNION.applies([], _union(UNION_CAPTURED[name]))


def test_union_only_counts_its_own_binders_as_capturing():
    # `w` is not bound in this formula, so a variable called `w` is free in it.
    assert UNION.applies([], _union(v("w")))
    assert UNION.applies([], _union(tl.FunctionTerm("f", [v("w")])))
    # Rename the inner binder and `v` is no longer captured, but `w` is.
    assert UNION.applies([], _union(v("v"), w="w"))
    assert not UNION.applies([], _union(v("w"), w="w"))


@pytest.mark.parametrize("names", [
    dict(u="Y"),
    dict(w="Y"),
    dict(w="u"),
], ids=_binder_ids)
def test_union_rejects_an_instance_whose_binders_share_a_name(names):
    assert not UNION.applies([], _union(A, **names))


# --------------------------------------------------------------------
# Power set: the universal axiom
# --------------------------------------------------------------------

def test_power_set_accepts_the_universal_axiom_as_the_subset_syntax_builds_it():
    assert POWER_SET.applies([], _power_set())


def test_power_set_accepts_any_names_for_its_binders():
    assert POWER_SET.applies([], _power_set(x="S", y="T", u="z"))


def test_power_set_takes_no_cited_lines():
    assert not POWER_SET.applies([SOME_PREMISE], _power_set())
    assert not POWER_SET.applies([_power_set()], _power_set())
    assert not POWER_SET.applies([SOME_PREMISE], _power_set(A))


def _power_set_near_misses(instance_of=None):
    """Shapes close to the power set axiom -- or, given `instance_of`, to its
    instance for that term -- that are not it."""
    S = v("X") if instance_of is None else instance_of
    Y, U, W = v("Y"), v("u"), v("w")

    def wrap(inner, new_set=fl.Exists, element=fl.ForAll):
        body = new_set("Y", element("u", inner))
        return body if instance_of is not None else fl.ForAll("X", body)

    standard = fl.Iff(_in(U, Y), st.subset_formula(U, S))
    misses = {
        "every set is the power set, not some set": wrap(standard, new_set=fl.ForAll),
        "some element, not every element, is in the power set": wrap(standard, element=fl.Exists),
        "membership target swapped": wrap(fl.Iff(_in(Y, U), st.subset_formula(U, S))),
        "subset reversed": wrap(fl.Iff(_in(U, Y), st.subset_formula(S, U))),
        "membership in the set, not inclusion in it": wrap(fl.Iff(_in(U, Y), _in(U, S))),
        "implication for iff": wrap(fl.Implies(_in(U, Y), st.subset_formula(U, S))),
        "the converse only": wrap(fl.Implies(st.subset_formula(U, S), _in(U, Y))),
        "bare membership": wrap(_in(U, Y)),
        "a subset clause with the wrong inner membership": wrap(fl.Iff(_in(U, Y), fl.ForAll(
            "w", fl.Implies(_in(W, U), _in(U, S))))),
        "a subset clause with the inclusion reversed": wrap(fl.Iff(_in(U, Y), fl.ForAll(
            "w", fl.Implies(_in(W, S), _in(W, U))))),
        "a subset clause that is an equivalence": wrap(fl.Iff(_in(U, Y), fl.ForAll(
            "w", fl.Iff(_in(W, U), _in(W, S))))),
        "an existential subset clause": wrap(fl.Iff(_in(U, Y), fl.Exists(
            "w", fl.Implies(_in(W, U), _in(W, S))))),
        "a subset clause about a conjunction": wrap(fl.Iff(_in(U, Y), fl.ForAll(
            "w", fl.And(_in(W, U), _in(W, S))))),
        "membership of another element in the new set": wrap(
            fl.Iff(_in(c("a"), Y), st.subset_formula(U, S))),
        "membership in a set other than the new one": wrap(
            fl.Iff(_in(U, c("Z")), st.subset_formula(U, S))),
        "a subset clause about another set than u": wrap(fl.Iff(_in(U, Y), fl.ForAll(
            "w", fl.Implies(_in(W, c("Z")), _in(W, S))))),
        "a subset clause whose antecedent is about another element": wrap(fl.Iff(_in(U, Y), fl.ForAll(
            "w", fl.Implies(_in(c("a"), U), _in(W, S))))),
    }
    if instance_of is None:
        misses["a subset of an unrelated set"] = wrap(fl.Iff(_in(U, Y), st.subset_formula(U, c("Z"))))
    return misses


@pytest.mark.parametrize("instance_of,name", _near_miss_params(_power_set_near_misses))
def test_power_set_rejects_a_near_miss(instance_of, name):
    assert not POWER_SET.applies([], _power_set_near_misses(instance_of)[name])


@pytest.mark.parametrize("names", [
    dict(y="X"),
    dict(u="X"),
    dict(u="Y"),
], ids=_binder_ids)
def test_power_set_rejects_binders_that_share_a_name(names):
    assert not POWER_SET.applies([], _power_set(**names))


def test_power_set_rejects_things_that_are_not_formulas_of_its_shape():
    assert not POWER_SET.applies([], fl.Equals(c("a"), c("b")))
    assert not POWER_SET.applies([], fl.Not(_power_set()))
    assert not POWER_SET.applies([], _union())
    assert not POWER_SET.applies([], fl.Not(_power_set(A)))


# --------------------------------------------------------------------
# Power set: the subset clause written out
# --------------------------------------------------------------------
#
# `u subset X` is the usual way to write the clause, and what a proof gets
# from it. Written out -- `forall v, (v in u -> v in X)`, as `POWER_SET_AXIOM`
# has it -- it says the same thing, and the rule takes any name for `v` that
# the other binders do not use.

@pytest.mark.parametrize("w", ["v", "w", "z", "__subset_element"])
def test_power_set_accepts_the_subset_clause_written_out(w):
    assert POWER_SET.applies([], _power_set(w=w))


def test_power_set_accepts_the_module_s_own_statement_of_the_axiom():
    assert POWER_SET.applies([], st.POWER_SET_AXIOM)


@pytest.mark.parametrize("w", ["X", "Y", "u"])
def test_power_set_rejects_a_subset_binder_that_shares_a_name_with_another(w):
    assert not POWER_SET.applies([], _power_set(w=w))


# --------------------------------------------------------------------
# Power set: the instance for a set of the proof
# --------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(SET_TERMS))
def test_power_set_accepts_the_instance_for_a_set_term(name):
    assert POWER_SET.applies([], _power_set(SET_TERMS[name]))
    assert POWER_SET.applies([], _power_set(SET_TERMS[name], w="w"))


def test_power_set_accepts_any_names_for_the_binders_of_an_instance():
    assert POWER_SET.applies([], _power_set(A, y="T", u="z"))
    assert POWER_SET.applies([], _power_set(A, y="T", u="z", w="t"))
    # No `forall X` here, so X is free to name the subset clause's binder.
    assert POWER_SET.applies([], _power_set(A, w="X"))


@pytest.mark.parametrize("name", sorted(SET_TERMS))
def test_the_power_set_instance_is_what_universal_instantiation_gives(name):
    term = SET_TERMS[name]
    instantiated = fl.substitute_in_formula(st.POWER_SET_AXIOM.body, "X", term)
    assert pl._ast_eq(instantiated, _power_set(term, w="v"))
    assert POWER_SET.applies([], instantiated)


@pytest.mark.parametrize("name", sorted(POWER_SET_CAPTURED))
def test_power_set_rejects_an_instance_whose_set_term_a_binder_would_capture(name):
    # Written out with the subset clause's variable called w.
    assert not POWER_SET.applies([], _power_set(POWER_SET_CAPTURED[name], w="w"))


@pytest.mark.parametrize("name", ["Y", "u", "f(Y)", "f(u)"])
def test_power_set_rejects_a_captured_set_term_in_the_subset_syntax_too(name):
    assert not POWER_SET.applies([], _power_set(POWER_SET_CAPTURED[name]))


def test_power_set_only_counts_its_own_binders_as_capturing():
    # The subset syntax picks a variable name no term of the formula uses, so
    # a variable called `w` -- or `v` -- is free in the instance it builds.
    assert POWER_SET.applies([], _power_set(v("w")))
    assert POWER_SET.applies([], _power_set(v("v")))
    # Written out with another name for the clause's variable, `v` is free
    # and `w` is bound.
    assert POWER_SET.applies([], _power_set(v("v"), w="w"))
    assert not POWER_SET.applies([], _power_set(v("w"), w="w"))


@pytest.mark.parametrize("names", [
    dict(u="Y"),
    dict(w="Y"),
    dict(w="u"),
], ids=_binder_ids)
def test_power_set_rejects_an_instance_whose_binders_share_a_name(names):
    assert not POWER_SET.applies([], _power_set(A, **names))


# --------------------------------------------------------------------
# Infinity
# --------------------------------------------------------------------

def test_infinity_accepts_the_axiom():
    assert INFINITY.applies([], _infinity())
    assert INFINITY.applies([], st.INFINITY_AXIOM)


def test_infinity_accepts_any_names_for_its_binders():
    assert INFINITY.applies([], _infinity(x="I", y="n", s="m", u="t"))


def test_infinity_accepts_the_successor_written_either_way_round():
    Y, S, U = v("y"), v("S"), v("u")
    swapped = fl.Iff(_in(U, S), fl.Or(fl.Equals(U, Y), _in(U, Y)))
    assert INFINITY.applies([], _infinity(successor=swapped))


def test_infinity_takes_no_cited_lines():
    assert not INFINITY.applies([SOME_PREMISE], _infinity())
    assert not INFINITY.applies([_infinity()], _infinity())


def _infinity_near_misses():
    X, Y, S, U = v("X"), v("y"), v("S"), v("u")
    return {
        "the empty set is not required": _infinity(empty=c("a")),
        "the empty set belongs to another set": _infinity(container=c("Z")),
        "the closure is about another element": _infinity(guard=_in(c("a"), X)),
        "the closure is about another set": _infinity(guard=_in(Y, c("Z"))),
        "the successor does not belong to the set": _infinity(target=c("Z")),
        "another set belongs to the set": _infinity(member=c("a")),
        "closure is a conjunction": _infinity(closure=fl.And),
        "the successor is y alone": _infinity(successor=fl.Iff(_in(U, S), _in(U, Y))),
        "the successor is an implication": _infinity(
            successor=fl.Implies(_in(U, S), fl.Or(_in(U, Y), fl.Equals(U, Y)))),
        "the successor is a conjunction": _infinity(
            successor=fl.Iff(_in(U, S), fl.And(_in(U, Y), fl.Equals(U, Y)))),
        "the successor's membership target is swapped": _infinity(
            successor=fl.Iff(_in(S, U), fl.Or(_in(U, Y), fl.Equals(U, Y)))),
        "a universal quantifier on the outside": fl.ForAll("X", _infinity().body),
        "some y, not every y, has a successor": _infinity(y_quantifier=fl.Exists),
        "every set, not some set, is the successor": _infinity(s_quantifier=fl.ForAll),
        "some u, not every u, is described": _infinity(u_quantifier=fl.Exists),
    }


@pytest.mark.parametrize("name", sorted(_infinity_near_misses()))
def test_infinity_rejects_a_near_miss(name):
    assert not INFINITY.applies([], _infinity_near_misses()[name])


# The successor of y is the set whose members are those of y, and y itself:
# `u in S <-> (u in y or u = y)`. Each of these gets one part of that wrong, and
# is tried with the disjuncts in both orders, as the rule accepts both.
_SUCCESSOR_NEAR_MISSES = {
    "it describes another element": (_in(c("a"), v("S")), _in(v("u"), v("y")), fl.Equals(v("u"), v("y"))),
    "it describes another set": (_in(v("u"), c("Z")), _in(v("u"), v("y")), fl.Equals(v("u"), v("y"))),
    "the members are those of another element": (
        _in(v("u"), v("S")), _in(c("a"), v("y")), fl.Equals(v("u"), v("y"))),
    "the members are those of another set": (
        _in(v("u"), v("S")), _in(v("u"), c("Z")), fl.Equals(v("u"), v("y"))),
    "what is added is not u": (_in(v("u"), v("S")), _in(v("u"), v("y")), fl.Equals(c("a"), v("y"))),
    "what is added is not y": (_in(v("u"), v("S")), _in(v("u"), v("y")), fl.Equals(v("u"), c("a"))),
}


@pytest.mark.parametrize("order", ["membership first", "equality first"])
@pytest.mark.parametrize("name", sorted(_SUCCESSOR_NEAR_MISSES))
def test_infinity_rejects_a_successor_that_is_not_y_with_y_added(name, order):
    described, membership, equality = _SUCCESSOR_NEAR_MISSES[name]
    disjuncts = [membership, equality] if order == "membership first" else [equality, membership]
    assert not INFINITY.applies([], _infinity(successor=fl.Iff(described, fl.Or(*disjuncts))))


@pytest.mark.parametrize("names", [
    dict(y="X"),
    dict(s="X"),
    dict(s="y"),
    dict(u="X"),
    dict(u="y"),
    dict(u="S"),
], ids=_binder_ids)
def test_infinity_rejects_binders_that_share_a_name(names):
    assert not INFINITY.applies([], _infinity(**names))


def test_infinity_rejects_things_that_are_not_formulas_of_its_shape():
    assert not INFINITY.applies([], fl.Equals(c("a"), c("b")))
    assert not INFINITY.applies([], fl.Not(_infinity()))
    assert not INFINITY.applies([], _union())


# --------------------------------------------------------------------
# The named rules and the axiom formulas agree
# --------------------------------------------------------------------

_NAMED_RULES = [st.PairingAxiomRule(), UNION, POWER_SET, INFINITY]


def test_each_set_axiom_formula_is_accepted_by_its_named_rule():
    assert len(_NAMED_RULES) == len(st.SET_AXIOMS)
    for rule, axiom in zip(_NAMED_RULES, st.SET_AXIOMS):
        assert rule.applies([], axiom), rule.name


def test_each_named_rule_accepts_only_its_own_axiom():
    for i, rule in enumerate(_NAMED_RULES):
        for j, axiom in enumerate(st.SET_AXIOMS):
            assert rule.applies([], axiom) == (i == j), (rule.name, j)


# --------------------------------------------------------------------
# Cited from proof text
# --------------------------------------------------------------------

def _check(text):
    entries = pp.parse_proof_text(text)[0]
    return pl.Proof(entries).check_detailed()


_UNION_OF_A = "Exists Y, forall u, (In(u, Y) iff (exists v, (In(v, A) and In(u, v))))"
_UNION_IN_FULL = "forall X, exists Y, forall u, (In(u, Y) iff (exists v, (In(v, X) and In(u, v))))"
_POWER_SET_OF_A = "Exists Y, forall u, (In(u, Y) iff u subset A)"
_POWER_SET_IN_FULL = "forall X, exists Y, forall u, (In(u, Y) iff u subset X)"
_POWER_SET_WRITTEN_OUT = "forall X, exists Y, forall u, (In(u, Y) iff (forall v, (In(v, u) -> In(v, X))))"
_INFINITY = ("exists X, (In(EmptySet, X) and forall y, (In(y, X) -> exists S, "
             "((forall u, (In(u, S) iff (In(u, y) or u = y))) and In(S, X))))")


@pytest.mark.parametrize("formula,citation", [
    (_UNION_OF_A, "Axiom of union"),
    (_POWER_SET_OF_A, "Axiom of power set"),
], ids=["union", "power set"])
def test_a_proof_cites_an_axiom_for_a_declared_set(formula, citation):
    ok, err = _check(f"1. Let A be any set. (Declaration)\n2. {formula}. ({citation})\n")
    assert ok, err


@pytest.mark.parametrize("full,instance,citation", [
    (_UNION_IN_FULL, _UNION_OF_A, "Axiom of union"),
    (_POWER_SET_IN_FULL, _POWER_SET_OF_A, "Axiom of power set"),
], ids=["union", "power set"])
def test_the_direct_instance_is_what_universal_instantiation_of_the_axiom_in_full_gives(full, instance, citation):
    ok, err = _check(
        "1. Let A be any set. (Declaration)\n"
        f"2. {full}. ({citation})\n"
        f"3. {instance}. (Universal Instantiation from 2)\n"
        f"4. {instance}. ({citation})\n"
    )
    assert ok, err


def test_a_proof_may_write_the_power_set_axiom_out_in_full():
    ok, err = _check(f"1. {_POWER_SET_WRITTEN_OUT}. (Axiom of power set)\n")
    assert ok, err


def test_a_proof_cites_the_axiom_of_infinity():
    ok, err = _check(f"1. {_INFINITY}. (Axiom of infinity)\n")
    assert ok, err


@pytest.mark.parametrize("template,good,bad,citation", [
    # S is the bound `v`: "the set" would change with the element.
    ("Exists Y, forall u, (In(u, Y) iff (exists v, (In(v, {}) and In(u, v))))", "A", "v", "Axiom of union"),
    # S is the bound `u`: the instance would say every set u belongs to Y.
    ("Exists Y, forall u, (In(u, Y) iff u subset {})", "A", "u", "Axiom of power set"),
], ids=["union", "power set"])
def test_a_proof_cannot_cite_an_axiom_for_a_set_its_own_binder_captures(template, good, bad, citation):
    # Only the set differs between the two formulas.
    ok, err = _check(f"1. Let A be any set. (Declaration)\n2. {template.format(good)}. ({citation})\n")
    assert ok, err
    ok, err = _check(f"1. Let A be any set. (Declaration)\n2. {template.format(bad)}. ({citation})\n")
    assert not ok
    assert err.label == "2"
    assert err.category == pl.CATEGORY_RULE_MISMATCH


@pytest.mark.parametrize("formula,citation", [
    (_POWER_SET_OF_A, "Axiom of union"),
    (_UNION_OF_A, "Axiom of power set"),
    (_UNION_OF_A, "Axiom of infinity"),
    (_POWER_SET_OF_A, "Axiom of pairing"),
    (_UNION_IN_FULL, "Axiom of power set"),
], ids=["power set as union", "union as power set", "union as infinity", "power set as pairing", "union in full as power set"])
def test_a_proof_cannot_cite_an_axiom_for_a_formula_of_another_axiom(formula, citation):
    ok, err = _check(f"1. Let A be any set. (Declaration)\n2. {formula}. ({citation})\n")
    assert not ok
    assert err.label == "2"
    assert err.category == pl.CATEGORY_RULE_MISMATCH


def test_an_instance_for_another_set_does_not_justify_the_conclusion():
    # The axiom is cited for B, but the subset fact it is used with is about A:
    # the instance form is exact about which set it speaks of.
    ok, err = _check(
        "1. Let A, B be any set. (Declaration)\n"
        "2. B is a subset of A. (Premise)\n"
        "3. Exists Y, forall u, (In(u, Y) iff u subset A). (Axiom of power set)\n"
        "4. Let Y be such a set. (Existence from 3)\n"
        "5. In(B, Y). (Set property from 4, 2)\n"
    )
    assert ok, err
    ok, err = _check(
        "1. Let A, B be any set. (Declaration)\n"
        "2. B is a subset of A. (Premise)\n"
        "3. Exists Y, forall u, (In(u, Y) iff u subset B). (Axiom of power set)\n"
        "4. Let Y be such a set. (Existence from 3)\n"
        "5. In(B, Y). (Set property from 4, 2)\n"
    )
    assert not ok
    assert err.label == "5"
    assert err.category == pl.CATEGORY_RULE_MISMATCH


# --------------------------------------------------------------------
# Realistic proofs: tests/setTheoryProofs/union_and_power_set_theorems.txt
# --------------------------------------------------------------------

def _fixture_text() -> str:
    project = Path(__file__).resolve().parents[1]
    return (project / "tests" / "setTheoryProofs" / "union_and_power_set_theorems.txt").read_text()


def _outcomes(results):
    return [(number, ok) for number, _expected, ok, _msg, _crashed in results]


def test_union_and_power_set_theorems_fixture_all_pass():
    results = mp.run_multi_proof_file(_fixture_text())
    assert _outcomes(results) == [(str(n), True) for n in range(1, 7)]


def _proof(number: int) -> str:
    """The text of one proof of the fixture, header included."""
    parts = _fixture_text().split("\n# ")
    return next("# " + part for part in parts if part.startswith(f"{number}:"))


@pytest.mark.parametrize("number,right,wrong", [
    # The union of A, then the power set of A: each inclusion is a Set property
    # step from the characterization of the right set.
    (5, "5.2.3. In(x, Y). (Set property, 3, 5.2.2)", "5.2.3. In(x, Y). (Set property, 5.1, 5.2.2)"),
    (5, "5.3.3. In(y, X). (Set property, 5.1, 5.3.2)", "5.3.3. In(y, X). (Set property, 3, 5.3.2)"),
    (6, "5.2.3. In(x, Y). (Set property, 3, 5.2.2)", "5.2.3. In(x, Y). (Set property, 5.1, 5.2.2)"),
    (6, "5.3.3. In(y, X). (Set property, 5.1, 5.3.2)", "5.3.3. In(y, X). (Set property, 3, 5.3.2)"),
    (2, "5. In(B, Y). (Set property from 4, 2)", "5. In(B, Y). (Set property from 4, 3)"),
    (1, "8. In(c, Y). (Set property from 5, 7)", "8. In(c, Y). (Set property from 5, 6)"),
])
def test_a_wrong_citation_inside_a_real_proof_is_rejected_at_that_line(number, right, wrong):
    text = _proof(number)
    assert right in text
    results = mp.run_multi_proof_file(text.replace(right, wrong))
    assert _outcomes(results) == [(str(number), False)]
    label = wrong.split(". ", 1)[0]
    assert results[0][3].startswith(f"Line {label}:"), results[0][3]
