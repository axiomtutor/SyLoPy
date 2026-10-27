

"""Discrete mathematics vocabulary and inference rules.

This module supplies the first discrete-mathematics layer: binary relations
and their standard properties.  Relation declarations are surface-language
metadata (a carrier and a set of properties on the ``Declaration``); the rules
below are ordinary core inference rules that read the declaration a relation
has at the line they justify.

Supported relation properties:
    reflexive, irreflexive, symmetric, antisymmetric, asymmetric, transitive,
    total/connected.

Convenience relation descriptors:
    equivalence relation = reflexive + symmetric + transitive
    partial order = reflexive + antisymmetric + transitive
    strict partial order = irreflexive + transitive
    total order / linear order = reflexive + antisymmetric + transitive + total

The rules are deliberately declaration-sensitive.  A relation rule can only
apply to a relation whose declaration explicitly supplied the corresponding
property.  Thus declaring R as transitive does not accidentally license
transitivity for an unrelated relation S.

The declaration a rule consults is the one in scope at the line being
justified (``RuleContext.declaration``).  A relation declared in a subproof has
its carrier and properties in that subproof and in the subproofs nested in it,
and nowhere else; a sibling subproof's ``R`` is a different relation, and the
rules keep no table of relations that could blur the two.
"""

from __future__ import annotations

from typing import Optional, Tuple

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.ProofElaboration import TheoryEnvironment

MEMBERSHIP = "In"

PROPERTY_ALIASES = {
    "reflexive": "reflexive",
    "irreflexive": "irreflexive",
    "symmetric": "symmetric",
    "antisymmetric": "antisymmetric",
    "asymmetric": "asymmetric",
    "transitive": "transitive",
    "total": "total",
    "connected": "total",
}

RELATION_TYPE_PROPERTIES = {
    "equivalence relation": {"reflexive", "symmetric", "transitive"},
    "equivalence": {"reflexive", "symmetric", "transitive"},
    "partial order": {"reflexive", "antisymmetric", "transitive"},
    "poset": {"reflexive", "antisymmetric", "transitive"},
    "strict partial order": {"irreflexive", "transitive"},
    "strict poset": {"irreflexive", "transitive"},
    "total order": {"reflexive", "antisymmetric", "transitive", "total"},
    "linear order": {"reflexive", "antisymmetric", "transitive", "total"},
}


def _relation_terms(phi: fl.Formula) -> Optional[Tuple[str, tl.Term, tl.Term]]:
    if not isinstance(phi, fl.AtomicFormula) or len(phi.args) != 2:
        return None
    if not isinstance(phi.predicate, str):
        return None
    left, right = phi.args
    if not isinstance(left, tl.Term) or not isinstance(right, tl.Term):
        return None
    return phi.predicate, left, right


def _membership_terms(phi: fl.Formula) -> Optional[Tuple[tl.Term, str]]:
    if not isinstance(phi, fl.AtomicFormula) or phi.predicate != MEMBERSHIP or len(phi.args) != 2:
        return None
    element, carrier = phi.args
    if not isinstance(element, tl.Term) or not isinstance(carrier, tl.ConstantTerm):
        return None
    return element, carrier.name


def _ast_eq(a, b) -> bool:
    return pl._ast_eq(a, b)


class _RelationRule(pl.InferenceRule):
    """Base of the relation-property rules.

    A relation rule holds no information about any relation. What it needs --
    the carrier a relation was declared on and the properties its declaration
    supplied -- it reads when asked, from the declaration the relation's name
    has at the line being justified (`RuleContext.declaration`). A declaration
    made in a subproof is visible in that subproof and in the ones nested in
    it, and nowhere else, so two sibling subproofs can each declare their own
    `R` without either lending its properties to the other.

    Subclasses implement `applies_in_context`. Asked with `applies`, outside
    any proof, a relation rule has no declaration to read and says no.
    """
    property_name = ""

    def applies(self, candidates, phi):
        return self.applies_in_context(candidates, phi, pl.RuleContext())

    def applies_in_context(self, candidates, phi, context):
        raise NotImplementedError

    @staticmethod
    def _declared(relation: str, context: pl.RuleContext) -> Optional[Tuple[object, frozenset]]:
        """`(carrier, properties)` the declaration of the binary relation
        `relation` supplied, as visible at this line; None if no such
        declaration is visible. Metadata entries that are not
        `(key, value)` pairs are somebody else's and are ignored."""
        declaration = context.declaration(relation)
        if (declaration is None or declaration.kind != pl.DeclarationKind.PREDICATE
                or declaration.arity != 2):
            return None
        metadata = {
            entry[0]: entry[1]
            for entry in declaration.metadata
            if isinstance(entry, tuple) and len(entry) == 2
        }
        return metadata.get("carrier"), frozenset(str(p) for p in metadata.get("properties", ()))

    def _allowed(self, relation: str, context: pl.RuleContext) -> bool:
        declared = self._declared(relation, context)
        return declared is not None and self.property_name in declared[1]

    def _carrier_matches(self, relation: str, carrier: str, context: pl.RuleContext) -> bool:
        declared = self._declared(relation, context)
        return declared is not None and declared[0] == carrier


class RelationReflexivityRule(_RelationRule):
    """From x in X and R reflexive on X, infer R(x,x)."""

    name = "RelationReflexivity"
    property_name = "reflexive"
    premise_arity = 1

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 1:
            return False
        membership = _membership_terms(candidates[0])
        relation = _relation_terms(phi)
        if membership is None or relation is None:
            return False
        x, carrier = membership
        r, left, right = relation
        return (self._allowed(r, context) and self._carrier_matches(r, carrier, context) and
                _ast_eq(x, left) and _ast_eq(x, right))


class RelationIrreflexivityRule(_RelationRule):
    """From x in X and R irreflexive on X, infer not R(x,x)."""

    name = "RelationIrreflexivity"
    property_name = "irreflexive"
    premise_arity = 1

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 1 or not isinstance(phi, fl.Not):
            return False
        membership = _membership_terms(candidates[0])
        relation = _relation_terms(phi.sub)
        if membership is None or relation is None:
            return False
        x, carrier = membership
        r, left, right = relation
        return (self._allowed(r, context) and self._carrier_matches(r, carrier, context) and
                _ast_eq(x, left) and _ast_eq(x, right))


class RelationSymmetryRule(_RelationRule):
    """From R(x,y), infer R(y,x) when R is declared symmetric."""

    name = "RelationSymmetry"
    property_name = "symmetric"
    premise_arity = 1

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 1:
            return False
        source = _relation_terms(candidates[0])
        target = _relation_terms(phi)
        if source is None or target is None:
            return False
        r1, a, b = source
        r2, c, d = target
        return self._allowed(r1, context) and r1 == r2 and _ast_eq(a, d) and _ast_eq(b, c)


class RelationAntisymmetryRule(_RelationRule):
    """From R(x,y) and R(y,x), infer x=y when R is antisymmetric."""

    name = "RelationAntisymmetry"
    property_name = "antisymmetric"
    premise_arity = 2

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 2 or not isinstance(phi, fl.Equals):
            return False
        first = _relation_terms(candidates[0])
        second = _relation_terms(candidates[1])
        if first is None or second is None:
            return False
        r1, a, b = first
        r2, c, d = second
        if r1 != r2 or not self._allowed(r1, context):
            return False
        return (_ast_eq(a, d) and _ast_eq(b, c) and
                _ast_eq(phi.left, a) and _ast_eq(phi.right, b))


class RelationAsymmetryRule(_RelationRule):
    """From R(x,y), infer not R(y,x) when R is asymmetric."""

    name = "RelationAsymmetry"
    property_name = "asymmetric"
    premise_arity = 1

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 1 or not isinstance(phi, fl.Not):
            return False
        source = _relation_terms(candidates[0])
        target = _relation_terms(phi.sub)
        if source is None or target is None:
            return False
        r1, a, b = source
        r2, c, d = target
        return self._allowed(r1, context) and r1 == r2 and _ast_eq(a, d) and _ast_eq(b, c)


class RelationTransitivityRule(_RelationRule):
    """From R(x,y), R(y,z), infer R(x,z)."""

    name = "RelationTransitivity"
    property_name = "transitive"
    premise_arity = 2

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 2:
            return False
        first = _relation_terms(candidates[0])
        second = _relation_terms(candidates[1])
        target = _relation_terms(phi)
        if first is None or second is None or target is None:
            return False
        r1, a, b = first
        r2, c, d = second
        r3, e, f = target
        return (r1 == r2 == r3 and self._allowed(r1, context) and
                _ast_eq(b, c) and _ast_eq(e, a) and _ast_eq(f, d))


class RelationTotalityRule(_RelationRule):
    """From x in X and y in X, infer R(x,y) or R(y,x) for a total relation."""

    name = "RelationTotality"
    property_name = "total"
    premise_arity = 2

    def applies_in_context(self, candidates, phi, context):
        if len(candidates) != 2 or not isinstance(phi, fl.Or) or len(phi.disjuncts) != 2:
            return False
        memberships = [_membership_terms(c) for c in candidates]
        if any(m is None for m in memberships):
            return False
        first_rel = _relation_terms(phi.disjuncts[0])
        second_rel = _relation_terms(phi.disjuncts[1])
        if first_rel is None or second_rel is None:
            return False
        r1, a, b = first_rel
        r2, c, d = second_rel
        if r1 != r2 or not self._allowed(r1, context):
            return False
        x, carrier_x = memberships[0]
        y, carrier_y = memberships[1]
        if carrier_x != carrier_y or not self._carrier_matches(r1, carrier_x, context):
            return False
        return ((_ast_eq(a, x) and _ast_eq(b, y) and _ast_eq(c, y) and _ast_eq(d, x)) or
                (_ast_eq(a, y) and _ast_eq(b, x) and _ast_eq(c, x) and _ast_eq(d, y)))


# The relation rules are a fixed list: they carry no per-proof state, so they
# belong to the theory, not to any one proof. Which relations they apply to is
# decided line by line, from the declarations in scope.
DISCRETE_MATH_ENVIRONMENT = TheoryEnvironment(
    name="discrete mathematics",
    rules=[
        RelationReflexivityRule(),
        RelationIrreflexivityRule(),
        RelationSymmetryRule(),
        RelationAntisymmetryRule(),
        RelationAsymmetryRule(),
        RelationTransitivityRule(),
        RelationTotalityRule(),
    ],
)



