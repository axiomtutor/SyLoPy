"""Discrete-mathematics theory facade.

Relation syntax and semantics are implemented by ``DiscreteMathCore`` and
exposed here through the public theory environment and declaration-recipe
boundary.
"""
from __future__ import annotations

import re

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.ProofElaboration import TheoryEnvironment
from SyLoPy.source import DiscreteMathCore as _core
from SyLoPy.source.DiscreteMathCore import *  # noqa: F401,F403


# The names the bound variables of the sugar below are taken from, in order.
# The first two that are neither the relation nor its carrier are used.
_BOUND_VARIABLE_NAMES = ("x", "y", "u", "v", "s", "t")


def relation_subset_formula(relation: str, carrier: str) -> fl.Formula:
    """`relation` is a subset of `carrier` x `carrier`, as a formula.

    ``forall x, forall y, (R(x, y) -> (In(x, X) and In(y, X)))``. A relation is
    a predicate here, not a set of pairs, so this is the formula that says what
    "R is a subset of X x X" says: whatever R relates is in X.

    The variables are `x` and `y` unless the relation or its carrier is called
    that, so that the formula never prints a bound variable and a constant under
    one name. Proof text states the formulas it derives from this one, and
    binder names have to agree exactly.
    """
    x, y = [name for name in _BOUND_VARIABLE_NAMES if name not in (relation, carrier)][:2]
    first, second = tl.VariableTerm(x), tl.VariableTerm(y)
    carrier_term = tl.ConstantTerm(carrier, carrier)
    return fl.ForAll(x, fl.ForAll(y, fl.Implies(
        fl.AtomicFormula(relation, [first, second]),
        fl.And(
            fl.AtomicFormula(_core.MEMBERSHIP, [first, carrier_term]),
            fl.AtomicFormula(_core.MEMBERSHIP, [second, carrier_term]),
        ),
    )))


class RelationDeclarationRecipe:
    """Recognize relation declarations and lower them to typed predicates.

    `Let R be a ... relation on X` declares R as a binary predicate that
    carries its carrier and properties as metadata (what the relation rules
    read), and states that R is a subset of X x X: the formula
    `relation_subset_formula`, one for each relation named, as a fact of the
    declaration line, like the `In(a, X)` of `a be in X`. It is sugar for
    that formula, so a proof can use it with the ordinary rules."""

    name = "relation"
    _aliases = {
        "equivalence relation": {"reflexive", "symmetric", "transitive"},
        "equivalence": {"reflexive", "symmetric", "transitive"},
        "partial order": {"reflexive", "antisymmetric", "transitive"},
        "poset": {"reflexive", "antisymmetric", "transitive"},
        "strict partial order": {"irreflexive", "transitive"},
        "strict poset": {"irreflexive", "transitive"},
        "total order": {"reflexive", "antisymmetric", "transitive", "total"},
        "linear order": {"reflexive", "antisymmetric", "transitive", "total"},
    }
    _properties = (
        "reflexive", "irreflexive", "symmetric", "antisymmetric",
        "asymmetric", "transitive", "total",
    )

    def try_match(self, clauses, index):
        if index >= len(clauses):
            return None
        clause = clauses[index]
        descriptor = getattr(clause, "normalized_descriptor", "")
        if "relation" not in descriptor and not any(
            alias in descriptor for alias in self._aliases
        ):
            return None
        carrier_match = re.search(
            r"\bon\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
            getattr(clause, "descriptor", ""),
            re.I,
        )
        if carrier_match is None:
            raise ValueError("relation declaration must specify a carrier, e.g. 'relation on X'")
        carrier = carrier_match.group(1)

        # The carrier is a set the proof has already declared: by an earlier
        # clause of this line, or before it (an earlier line, an enclosing
        # proof). Otherwise this recipe declines, and the generic declaration
        # path reports the carrier as not declared yet.
        previous_names = {
            name
            for previous in clauses[:index]
            for name in getattr(previous, "names", ())
        }
        is_declared = getattr(clause, "is_declared", None)
        if carrier not in previous_names and not (is_declared is not None and is_declared(carrier)):
            return None

        matched_alias = next(
            (
                alias
                for alias in sorted(self._aliases, key=len, reverse=True)
                if re.search(rf"\b{re.escape(alias)}\b", descriptor)
            ),
            None,
        )
        properties = set(self._aliases.get(matched_alias, ()))
        for property_name in self._properties:
            if re.search(rf"\b{property_name}\b", descriptor, re.I):
                properties.add(property_name)
        if "connected" in descriptor:
            properties.add("total")

        metadata = (("carrier", carrier), ("properties", tuple(sorted(properties))))
        declarations = [
            pl.Declaration(
                name=name,
                kind=pl.DeclarationKind.PREDICATE,
                arity=2,
                type_name=getattr(clause, "descriptor", "relation"),
                metadata=metadata,
            )
            for name in clause.names
        ]
        subsets = [relation_subset_formula(name, carrier) for name in clause.names]
        return (1, declarations, subsets, [])


RELATION_DECLARATION_RECIPE = RelationDeclarationRecipe()
DISCRETE_MATH_ENVIRONMENT = _core.DISCRETE_MATH_ENVIRONMENT.extended(
    TheoryEnvironment(declaration_recipes=[RELATION_DECLARATION_RECIPE])
)
