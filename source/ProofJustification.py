"""Deterministic parsing of proof justifications.

Rule names are resolved by explicit aliases rather than substring matching.
Theory-specific rules are represented by named placeholders and resolved by
ProofLogic when the proof's theory environment supplies the corresponding
rule instance.

A proved theorem is cited by its title, the way a rule is cited: bare when it
has no premises (`(Symmetry of equality)`), and with the lines that state its
premises when it has some (`(Property transport from 3)`, `(Property
transport, 3)`). The parser cannot tell a title from a misspelled rule name,
and a misspelled name followed by citations is an error here, not a
placeholder that fails later. So the caller says which titles exist
(`theorem_names`); a title that is not among them, and not a rule, is unknown.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import SyLoPy.source.ProofLogic as pl

RuleFactory = Callable[[], object]


def _normalize(text: str) -> str:
    text = text.strip().lower().replace("’", "'")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    # Strip surrounding parentheses if present
    text = text.strip(" .")
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return text.strip(" .")


def _alias_map() -> Dict[str, RuleFactory]:
    mapping: Dict[str, RuleFactory] = {}
    def add(factory: RuleFactory, *aliases: str) -> None:
        for alias in aliases:
            mapping[_normalize(alias)] = factory
    add(pl.UniversalInstantiationRule, "Universal Instantiation", "Universal Instantiation Rule")
    add(pl.UniversalGeneralizationRule, "Universal Generalization", "Universal Generalization Rule")
    add(pl.UniversalModusPonensRule, "Universal Modus Ponens", "Universal Modus Ponens Rule")
    add(pl.UniquenessRule, "Uniqueness", "Uniqueness Rule")
    add(pl.ExistentialIntroductionRule, "Existential Introduction", "Existential Introduction Rule", "Existential Generalization")
    add(pl.ExistentialEliminationRule, "Existential Elimination", "Existential Elimination Rule", "Existential Instantiation")
    add(pl.ConjunctionEliminationRule, "Conjunction Elimination", "Conjunction Elimination Rule", "And Elimination", "And Elim")
    add(pl.ConjunctionIntroductionRule, "Conjunction Introduction", "Conjunction Introduction Rule", "And Introduction", "And Intro")
    add(pl.DisjunctionIntroductionRule, "Disjunction Introduction", "Disjunction Introduction Rule", "Or Introduction", "Or Intro", "Addition")
    add(pl.DisjunctionEliminationRule, "Disjunction Elimination", "Disjunction Elimination Rule", "Or Elimination", "Or Elim", "Proof by Cases", "Cases")
    add(pl.BiconditionalIntroductionRule, "Biconditional Introduction", "Biconditional Introduction Rule", "Conditional Equivalence Introduction")
    add(pl.BiconditionalEliminationRule, "Biconditional Elimination", "Biconditional Elimination Rule", "Conditional Elimination")
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
    add(pl.AlgebraRule, "Algebra", "Algebraic Manipulation")
    add(pl.PropositionalEquivalenceRule, "De Morgan", "De Morgan's", "De Morgans", "De Morgan's Laws", "Distribution", "Distributivity", "Double Negation", "Propositional Equivalence", "Logical Equivalence", "Equivalence", "Conditional Equivalence")
    return mapping

_ALIASES = _alias_map()


def _parse_indices(text: str) -> List[str]:
    return [token.strip() for token in re.split(r"\s*(?:,|and)\s*", text) if token.strip()]


# A cited line label ("3", "3.2.1"), and a reference list made of labels and
# "A to B" ranges: "3, 3.2.1", "3.1 to 3.2", "2 and 3".
_LABEL_PATTERN = r"[0-9]+(?:\.[A-Za-z0-9_]+)*"
_REF_ITEM_PATTERN = rf"{_LABEL_PATTERN}(?:\s+to\s+{_LABEL_PATTERN})?"
_REF_LIST_PATTERN = rf"{_REF_ITEM_PATTERN}(?:\s*(?:,|and)\s*{_REF_ITEM_PATTERN})*"


def _parse_refs(text: str) -> List[str]:
    """Split a reference list into line labels, in order.

    ``"3, 3.2.1"`` gives ``["3", "3.2.1"]``. An ``A to B`` range gives its two
    endpoint labels, ``"3.1 to 3.2"`` -> ``["3.1", "3.2"]``; what the endpoints
    mean is up to the rule that is cited (the range is not expanded).
    """
    labels: List[str] = []
    for item in re.split(r"\s*(?:,|\band\b)\s*", text.strip()):
        labels.extend(part.strip() for part in re.split(r"\s+to\s+", item.strip()) if part.strip())
    return labels


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
        "axiom of separation": "Separation",
        "separation schema": "Separation",
        "axiom schema of separation": "Separation",
        "axiom of replacement": "Replacement",
        "replacement schema": "Replacement",
        "axiom schema of replacement": "Replacement",
        "axiom of pairing": "PairingAxiom",
        "axiom of union": "UnionAxiom",
        "axiom of power set": "PowerSetAxiom",
        "power set axiom": "PowerSetAxiom",
        "axiom of infinity": "InfinityAxiom",
        "wlog": "WLOG",
        "without loss of generality": "WLOG",
        "mutatis mutandis": "MutatisMutandis",
    }
    target = placeholders.get(_normalize(name))
    if target is not None:
        return pl.NamedRulePlaceholder(target)
    raise ValueError(f"Unknown inference rule '{name.strip()}' in justification")


def theorem_titles(names: Iterable[str]) -> Tuple[str, ...]:
    """`names` as a tuple of theorem titles. A lone string is one title, not
    the characters it is made of."""
    return (names,) if isinstance(names, str) else tuple(names)


def _theorem_title(name: str, theorem_names: Iterable[str]) -> Optional[str]:
    """The title in `theorem_names` that `name` cites, or None.

    A title written exactly wins. Otherwise the comparison is `_normalize`,
    the case-, hyphen- and spacing-insensitive one every built-in rule name
    gets, and it counts only when it picks out one title. The result is the
    title as the theorem was promoted under it, because that is what the
    validator looks a placeholder up by."""
    titles = list(theorem_names)
    wanted = name.strip()
    if wanted in titles:
        return wanted
    matches = {title for title in titles if _normalize(title) == _normalize(wanted)}
    return next(iter(matches)) if len(matches) == 1 else None


def _cited_rule(rule_name: str, refs: List[str], theorem_names: Iterable[str] = ()):
    """Resolve `rule_name`, choosing by citation count where a name covers
    two rules: bare "Set property" is the empty-set rule, while "Set
    property" citing lines is the general one. A name that is no rule at all
    may be the title of a theorem the caller knows (`theorem_names`); a
    built-in rule's name is never taken for one."""
    if refs and _normalize(rule_name) in {"set property", "set property rule"}:
        return pl.NamedRulePlaceholder("SetProperty")
    try:
        return _rule(rule_name)
    except ValueError:
        title = _theorem_title(rule_name, theorem_names)
        if title is None:
            raise
        return pl.NamedRulePlaceholder(title)


def parse_justification(s: str, theorem_names: Iterable[str] = ()):
    """Parse the text of a proof line's justification.

    `theorem_names` are the titles of the theorems the proof may cite (see
    the module docstring); with none, only rules and bare names are cited."""
    theorem_names = theorem_titles(theorem_names)
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
        refs = _parse_indices(citation.group(2))
        return ("rule", _cited_rule(rule_name, refs, theorem_names), refs)
    # "Rule, 3, 3.2.1" / "Rule, 3.1 to 3.2": the rule's name, then the lines it cites.
    comma_citation = re.match(rf"^(?P<name>[^,]*[A-Za-z][^,]*?)\s*,\s*(?P<refs>{_REF_LIST_PATTERN})\s*$", s)
    if comma_citation:
        refs = _parse_refs(comma_citation.group("refs"))
        return ("rule", _cited_rule(comma_citation.group("name"), refs, theorem_names), refs)
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
        # A bare, zero-citation rule name ("Axiom of pairing", "Separation"):
        # resolve known aliases and theory placeholders, and otherwise keep
        # the raw text -- or the title of a theorem it names -- as a
        # placeholder so the validator looks it up, or reports it, by name.
        try:
            return ("rule", _rule(s), [])
        except ValueError:
            return ("rule", pl.NamedRulePlaceholder(_theorem_title(s, theorem_names) or s), [])
    raise ValueError(f"Invalid justification format: '{s}'")
