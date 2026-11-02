"""Integer order theory and phrase-level `<`/`<=` syntax.

The strict order predicates ``Less(a, b)`` and ``LessEqual(a, b)`` are
the theory vocabulary used for concrete integer order proofs.  Relation
declarations and partial/total-order metadata remain owned by DiscreteMath.
"""
from __future__ import annotations

import re
from typing import Optional

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.NumberTheory as nt
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.ProofElaboration import TheoryEnvironment


LESS_PREDICATE = "Less"
LESS_EQUAL_PREDICATE = "LessEqual"
PLUS = nt.PLUS
TIMES = nt.TIMES
ZERO = nt.Zero
ONE = nt.One

_x = tl.VariableTerm("x")
_y = tl.VariableTerm("y")
_z = tl.VariableTerm("z")


def _Less(a: tl.Term, b: tl.Term) -> fl.Formula:
    return fl.AtomicFormula(LESS_PREDICATE, [a, b])


def _LessEqual(a: tl.Term, b: tl.Term) -> fl.Formula:
    return fl.AtomicFormula(LESS_EQUAL_PREDICATE, [a, b])


def _Int(a: tl.Term) -> fl.Formula:
    return fl.AtomicFormula(nt.INT_PREDICATE, [a])


def _Plus(a: tl.Term, b: tl.Term) -> tl.Term:
    return tl.FunctionTerm(PLUS, [a, b])


def _Times(a: tl.Term, b: tl.Term) -> tl.Term:
    return tl.FunctionTerm(TIMES, [a, b])


ORDER_AXIOMS = [
    # A strict integer order is irreflexive.
    fl.ForAll("x", fl.Implies(_Int(_x), fl.Not(_Less(_x, _x)))),
    # Strict order is transitive.
    fl.ForAll("x", fl.ForAll("y", fl.ForAll("z", fl.Implies(
        fl.And(fl.And(_Int(_x), _Int(_y)), _Int(_z)),
        fl.Implies(fl.And(_Less(_x, _y), _Less(_y, _z)), _Less(_x, _z)),
    )))),
    # For integers, exactly one strict-order alternative holds.
    fl.ForAll("x", fl.ForAll("y", fl.Implies(
        fl.And(_Int(_x), _Int(_y)),
        fl.Or(_Less(_x, _y), fl.Or(fl.Equals(_x, _y), _Less(_y, _x))),
    ))),
    # LessEqual is precisely Less or equal.
    fl.ForAll("x", fl.ForAll("y", fl.Implies(
        fl.And(_Int(_x), _Int(_y)),
        fl.Iff(_LessEqual(_x, _y), fl.Or(_Less(_x, _y), fl.Equals(_x, _y))),
    ))),
    # Addition preserves strict order in each summand.
    fl.ForAll("x", fl.ForAll("y", fl.ForAll("z", fl.Implies(
        fl.And(fl.And(_Int(_x), _Int(_y)), _Int(_z)),
        fl.Implies(_Less(_x, _y), _Less(_Plus(_x, _z), _Plus(_y, _z))),
    )))),
    # The product of positive integers is positive.
    fl.ForAll("x", fl.ForAll("y", fl.Implies(
        fl.And(fl.And(_Int(_x), _Int(_y)),
               fl.And(_Less(ZERO, _x), _Less(ZERO, _y))),
        _Less(ZERO, _Times(_x, _y)),
    ))),
]


def try_parse_order_formula(text: str, bound_vars):
    """Parse integer order vocabulary as ordinary atomic predicates."""
    import SyLoPy.source.ProofParser as pp

    s = " ".join(text.strip().rstrip(".").split())

    phrases = (
        (r"^(.+?)\s+is\s+less\s+than\s+or\s+equal\s+to\s+(.+)$", LESS_EQUAL_PREDICATE, False),
        (r"^(.+?)\s+is\s+at\s+most\s+(.+)$", LESS_EQUAL_PREDICATE, False),
        (r"^(.+?)\s+is\s+greater\s+than\s+or\s+equal\s+to\s+(.+)$", LESS_EQUAL_PREDICATE, True),
        (r"^(.+?)\s+is\s+at\s+least\s+(.+)$", LESS_EQUAL_PREDICATE, True),
        (r"^(.+?)\s+is\s+less\s+than\s+(.+)$", LESS_PREDICATE, False),
        (r"^(.+?)\s+is\s+greater\s+than\s+(.+)$", LESS_PREDICATE, True),
    )
    for pattern, predicate, reversed_terms in phrases:
        match = re.match(pattern, s, flags=re.I)
        if match:
            left = pp.parse_term(match.group(1), bound_vars)
            right = pp.parse_term(match.group(2), bound_vars)
            if reversed_terms:
                left, right = right, left
            return fl.AtomicFormula(predicate, [left, right])

    operators = (
        ("<=", LESS_EQUAL_PREDICATE),
        (">=", LESS_EQUAL_PREDICATE),
        ("<", LESS_PREDICATE),
        (">", LESS_PREDICATE),
    )
    for operator, predicate in operators:
        if operator not in s:
            continue
        parts = pp.split_top_level(s, operator)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            left = pp.parse_term(parts[0], bound_vars)
            right = pp.parse_term(parts[1], bound_vars)
            if operator == ">":
                left, right = right, left
            if operator == ">=":
                left, right = right, left
            return fl.AtomicFormula(predicate, [left, right])
    return None


def _less_terms(phi: fl.Formula):
    if (isinstance(phi, fl.AtomicFormula) and phi.predicate == LESS_PREDICATE
            and len(phi.args) == 2):
        return phi.args
    return None


def _less_equal_terms(phi: fl.Formula):
    if (isinstance(phi, fl.AtomicFormula) and phi.predicate == LESS_EQUAL_PREDICATE
            and len(phi.args) == 2):
        return phi.args
    return None


class OrderTransitivityRule(pl.InferenceRule):
    name = "Order Transitivity"
    premise_arity = 2

    def applies(self, candidates, phi):
        if len(candidates) != 2:
            return False
        first, second = _less_terms(candidates[0]), _less_terms(candidates[1])
        target = _less_terms(phi)
        if first is None or second is None or target is None:
            return False
        return (pl._ast_eq(first[1], second[0])
                and pl._ast_eq(first[0], target[0])
                and pl._ast_eq(second[1], target[1]))


class OrderIrreflexivityRule(pl.InferenceRule):
    name = "Order Irreflexivity"
    premise_arity = 1

    def applies(self, candidates, phi):
        if len(candidates) != 1 or not isinstance(phi, fl.Not):
            return False
        integer = candidates[0]
        if not (isinstance(integer, fl.AtomicFormula)
                and integer.predicate == nt.INT_PREDICATE
                and len(integer.args) == 1):
            return False
        target = _less_terms(phi.sub)
        return (target is not None
                and pl._ast_eq(integer.args[0], target[0])
                and pl._ast_eq(target[0], target[1]))


class OrderLessEqualRule(pl.InferenceRule):
    name = "LessEqual Definition"
    premise_arity = 1

    def applies(self, candidates, phi):
        if len(candidates) != 1 or len(_less_equal_terms(phi) or ()) != 2:
            return False
        target = _less_equal_terms(phi)
        if isinstance(candidates[0], fl.Or) and len(candidates[0].disjuncts) == 2:
            left, right = target
            return ((pl._ast_eq(candidates[0].disjuncts[0], _Less(left, right))
                     and pl._ast_eq(candidates[0].disjuncts[1], fl.Equals(left, right)))
                    or
                    (pl._ast_eq(candidates[0].disjuncts[1], _Less(left, right))
                     and pl._ast_eq(candidates[0].disjuncts[0], fl.Equals(left, right))))
        return False


ORDER_THEORY_ENVIRONMENT = TheoryEnvironment(
    name="order theory",
    nested_formula_parsers=[try_parse_order_formula],
    rules=[
        OrderTransitivityRule(),
        OrderIrreflexivityRule(),
        OrderLessEqualRule(),
    ],
    axioms=ORDER_AXIOMS,
    declarations=[
        pl.Declaration(LESS_PREDICATE, pl.DeclarationKind.PREDICATE, arity=2),
        pl.Declaration(LESS_EQUAL_PREDICATE, pl.DeclarationKind.PREDICATE, arity=2),
    ],
).extended(nt.NUMBER_THEORY_ENVIRONMENT)
