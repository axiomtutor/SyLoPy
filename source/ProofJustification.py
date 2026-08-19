"""Deterministic parsing of proof justifications.

Rule names are resolved by explicit aliases rather than substring matching.
Theory-specific rules are represented by named placeholders and resolved by
ProofLogic when the proof's theory environment supplies the corresponding
rule instance.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List

import SyLoPy.source.ProofLogic as pl

RuleFactory = Callable[[], object]


def _normalize(text: str) -> str:
    text = text.strip().lower().replace("’", "'")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .")


def _alias_map() -> Dict[str, RuleFactory]:
    mapping: Dict[str, RuleFactory] = {}
    def add(factory: RuleFactory, *aliases: str) -> None:
        for alias in aliases:
            mapping[_normalize(alias)] = factory
    add(pl.UniversalInstantiationRule, "Universal Instantiation", "Universal Instantiation Rule")
    add(pl.UniversalGeneralizationRule, "Universal Generalization", "Universal Generalization Rule")
    add(pl.ExistentialIntroductionRule, "Existential Introduction", "Existential Introduction Rule")
    add(pl.ExistentialEliminationRule, "Existential Elimination", "Existential Elimination Rule")
    add(pl.ConjunctionEliminationRule, "Conjunction Elimination", "Conjunction Elimination Rule", "And Elimination", "And Elim")
    add(pl.ConjunctionIntroductionRule, "Conjunction Introduction", "Conjunction Introduction Rule", "And Introduction", "And Intro")
    add(pl.DisjunctionIntroductionRule, "Disjunction Introduction", "Disjunction Introduction Rule", "Or Introduction", "Or Intro", "Addition")
    add(pl.DisjunctionEliminationRule, "Disjunction Elimination", "Disjunction Elimination Rule", "Or Elimination", "Or Elim", "Proof by Cases", "Cases")
    add(pl.BiconditionalIntroductionRule, "Biconditional Introduction", "Biconditional Introduction Rule", "Conditional Equivalence Introduction")
    add(pl.BiconditionalEliminationRule, "Biconditional Elimination", "Biconditional Elimination Rule", "Conditional Equivalence", "Conditional Equivalence Elimination")
    add(pl.ConditionalIntroductionRule, "Conditional Introduction", "Conditional Introduction Rule", "Conditional Intro")
    add(pl.ProofByContradictionRule, "Proof by Contradiction", "Proof by Contradiction Rule", "Reductio", "Reductio Ad Absurdum")
    add(pl.ModusPonensRule, "Modus Ponens", "Modus Ponens Rule")
    add(pl.ModusTollensRule, "Modus Tollens", "Modus Tollens Rule")
    add(pl.DisjunctiveSyllogismRule, "Disjunctive Syllogism", "Disjunctive Syllogism Rule")
    add(pl.HypotheticalSyllogismRule, "Hypothetical Syllogism", "Hypothetical Syllogism Rule")
    add(pl.ExplosionRule, "Explosion", "Explosion Rule", "Ex Falso")
    add(pl.ReiterationRule, "Reiteration", "Reiterate", "Reiteration Rule")
    add(pl.LeibnizSubstitutionRule, "Substitution", "Leibniz Substitution", "Leibniz")
    add(pl.SymmetryRule, "Symmetry", "Symmetry Rule")
    add(pl.TransitivityRule, "Transitivity", "Transitivity Rule")
    add(pl.ReflexivityRule, "Reflexivity", "Reflexivity Rule")
    add(pl.PropositionalEquivalenceRule, "De Morgan", "De Morgan's", "De Morgans", "De Morgan's Laws", "Distribution", "Distributivity", "Double Negation", "Propositional Equivalence", "Logical Equivalence")
    return mapping

_ALIASES = _alias_map()


def _parse_indices(text: str) -> List[str]:
    return [token.strip() for token in re.split(r"\s*(?:,|and)\s*", text) if token.strip()]


def _rule(name: str):
    factory = _ALIASES.get(_normalize(name))
    if factory is not None:
        return factory()
    placeholders = {
        "relation reflexivity": "RelationReflexivity",
        "relation irreflexivity": "RelationIrreflexivity",
        "relation symmetry": "RelationSymmetry",
        "relation antisymmetry": "RelationAntisymmetry",
        "relation asymmetry": "RelationAsymmetry",
        "relation transitivity": "RelationTransitivity",
        "relation totality": "RelationTotality",
        "totality": "RelationTotality",
        "quotient defining property": "QuotientDefiningProperty",
        "quotient definition": "QuotientDefiningProperty",
        "quotient uniqueness": "QuotientUniqueness",
        "set equality": "SetEquality",
        "induction": "Induction",
        "empty set property": "EmptySetProperty",
        "set property": "EmptySetProperty",
    }
    target = placeholders.get(_normalize(name))
    if target is not None:
        return pl.NamedRulePlaceholder(target)
    if _normalize(name) and "from" not in _normalize(name) and "subproof" not in _normalize(name):
        return pl.NamedRulePlaceholder(name.strip())
    raise ValueError(f"Unknown inference rule '{name.strip()}' in justification")


def parse_justification(s: str):
    s = s.strip()
    if not s:
        raise ValueError("Justification text is required for every proof line")
    low = s.lower()
    m = re.match(r"^(.*?)from\s+subpro+f\s+below$", low)
    if m:
        rule_name = s[:m.start(0) + len(m.group(1))].strip()
        normalized = _normalize(rule_name)
        if normalized in {"conditional introduction", "conditional introduction rule"}:
            return ("rule_below", pl.ConditionalIntroductionRule())
        if normalized in {"proof by contradiction", "proof by contradiction rule", "reductio ad absurdum", "reductio"}:
            return ("rule_below", pl.ProofByContradictionRule())
        if normalized in {"universal generalization", "universal generalization rule"}:
            return ("rule_below", pl.UniversalGeneralizationRule())
        raise ValueError(f"Unknown inference rule '{rule_name}' in justification")
    hybrid = re.match(r"^(.*?)from\s+([0-9]+(?:\.[A-Za-z0-9_]+)*(?:\s*(?:,|and)\s*[0-9]+(?:\.[A-Za-z0-9_]+)*)*)\s*,?\s+subproofs?\s+below$", low)
    if hybrid:
        base_refs = re.sub(r"\s+and\s+", ", ", hybrid.group(2).strip())
        rule_name = s[:hybrid.start(0) + len(hybrid.group(1))].strip()
        return ("rule_hybrid", _rule(rule_name), _parse_indices(base_refs))
    if re.search(r"\bfrom\s*$", low):
        raise ValueError(f"Malformed rule justification: {s}")
    citation = re.match(r"^(.*?)from\s+([0-9]+(?:\.[A-Za-z0-9_]+)*(?:\s*(?:,|and)\s*[0-9]+(?:\.[A-Za-z0-9_]+)*)*)$", low)
    if citation:
        rule_name = s[:citation.start(0) + len(citation.group(1))].strip()
        return ("rule", _rule(rule_name), _parse_indices(citation.group(2)))
    normalized = _normalize(s)
    if normalized in {"arbitrary", "fresh variable", "fresh constant", "arbitrary object"}:
        return ("arbitrary",)
    if normalized in {"declare", "declaration"}:
        return ("declare",)
    if normalized in {"premise", "given"}:
        return ("premise",)
    if normalized.startswith("assume") or normalized.startswith("assumption") or normalized == "case":
        return ("assume",)
    if normalized == "axiom":
        return ("axiom",)
    if normalized == "reflexivity":
        return ("rule", pl.ReflexivityRule(), [])
    if normalized in {"set property", "empty set property"}:
        return ("rule", pl.NamedRulePlaceholder("EmptySetProperty"), [])
    if "from" not in low and "subproof" not in low:
        return ("rule", _rule(s), [])
    raise ValueError(f"Invalid justification format: '{s}'")
