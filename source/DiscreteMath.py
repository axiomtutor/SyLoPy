"""Discrete-mathematics theory facade.

Relation syntax and semantics are implemented by ``DiscreteMathCore`` and
exposed here through the public theory environment and declaration-recipe
boundary.
"""
from __future__ import annotations

import re

import SyLoPy.source.ProofLogic as pl
from SyLoPy.source.ProofElaboration import TheoryEnvironment
from SyLoPy.source import DiscreteMathCore as _core
from SyLoPy.source.DiscreteMathCore import *  # noqa: F401,F403


class RelationDeclarationRecipe:
    """Recognize relation declarations and lower them to typed predicates."""

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

        previous_names = {
            name
            for previous in clauses[:index]
            for name in getattr(previous, "names", ())
        }
        if carrier not in previous_names:
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
        return (1, declarations, [], [])


RELATION_DECLARATION_RECIPE = RelationDeclarationRecipe()
DISCRETE_MATH_ENVIRONMENT = _core.DISCRETE_MATH_ENVIRONMENT.extended(
    TheoryEnvironment(declaration_recipes=[RELATION_DECLARATION_RECIPE])
)
