


"""Fitch-style natural-deduction proof checking for propositional and first-order logic.

This module is the semantic core of ProofLogic: it defines what counts as a
legal inference step, and how a whole proof -- a sequence of premises,
assumptions, and rule applications, possibly nested in Fitch-style
subproofs -- is checked line by line. It builds on the formula/term trees
defined in FormulaLogic and TermLogic but knows nothing about proof *text*;
ProofParser.py is the companion module that turns human-readable proof
notation into the plain-tuple ``entries`` format this module consumes.

--------------------------------------------------------------------------
The entries mini-language
--------------------------------------------------------------------------
A `Proof` is built from a list of *entries*. Each entry is one of:

    (phi, justification)                        unlabeled line
    (label, phi, justification)                  labeled line
    (label, phi, justification, nested_entries)  labeled line whose
                                                  justification opens an
                                                  inline subproof (e.g.
                                                  "... from subproof below")
    (label, 'subproof', nested_entries)          a standalone, labeled
    ('subproof', nested_entries)                 subproof block, cited by
                                                  label from a later line --
                                                  used by rules that take a
                                                  whole subproof as one of
                                                  several premises (see
                                                  DisjunctionEliminationRule,
                                                  ExistentialEliminationRule)

`justification` is itself a small tuple:

    ('premise',)                           phi is asserted as a premise
    ('axiom',)                             phi is asserted as an axiom
    ('assume',) / ('arbitrary',)           opens a subproof (must be its
                                            first line)
    ('rule', rule_instance, [labels...])   phi follows from the cited
                                            earlier lines by this rule
    ('rule_below', rule_instance)          phi follows from the subproof
                                            immediately below (paired with
                                            the 4-tuple entry form above)

Worked example -- the plain-text proof (see testProofs/mp_premises.txt)

    1. A(a). (Premise)
    2. A(a) -> C(a). (Premise)
    3. C(a). (Modus Ponens from 1,2)

is parsed by ProofParser into roughly:

    a = TermLogic.ConstantTerm('a', 'a')
    A_a, C_a = FormulaLogic.AtomicFormula('A', [a]), FormulaLogic.AtomicFormula('C', [a])
    entries = [
        (None, A_a, ('premise',)),
        (None, fl.Implies(A_a, C_a), ('premise',)),
        (None, C_a, ('rule', ModusPonensRule(), ['1', '2'])),
    ]
    ok, msg = Proof(entries).check()   # -> (True, None)

--------------------------------------------------------------------------
Checking a proof
--------------------------------------------------------------------------
`ProofValidator` walks the entries top to bottom, threading two pieces of
running state through recursive calls for nested subproofs:

  * `seen`   -- every formula (or SubproofRecord) justified so far in the
               *current* block, in order. A subproof's own conclusion and
               the "outer context" freshness checks (see SubproofRecord)
               are both computed from this.
  * `labels` -- a `LabelScope` mapping each line's label (e.g. "2.1") to
               the formula (or SubproofRecord) it justified, so later
               lines can cite it ("... from 2.1"). Scoped so a subproof's
               own labels disappear once the subproof closes, mirroring
               the Fitch rule that a closed subproof can't be cited into.

Each `InferenceRule` subclass implements exactly one method, `applies`,
which is a pure predicate: "given these already-validated `candidates`, is
`phi` a sound conclusion to draw from them?" Rules never see raw entries,
labels, or text -- only formulas and SubproofRecords the validator has
already checked. That keeps soundness logic (does this argument form work?)
cleanly separated from bookkeeping (is this reference in scope? has this
line already been justified?).

--------------------------------------------------------------------------
When a proof is invalid
--------------------------------------------------------------------------
`Proof.check()` returns `(False, message)` for an invalid proof, where
`message` names the first line that doesn't follow from what came before
it -- using the proof's own line label (e.g. "Line 11.2" for the third
line of the subproof opened at label "11"), not an internal position.
`Proof.check_detailed()` returns the same failure as a structured
`ValidationError` instead of a rendered string: `.label` is the bare
offending label, and `.category` is one of a small fixed set of
`CATEGORY_*` constants, so calling code can tell, for instance, a citation
of a label that doesn't exist (`CATEGORY_BAD_REFERENCE`) apart from a
citation of real, in-scope lines that the named rule simply doesn't
license the conclusion from (`CATEGORY_RULE_MISMATCH`) -- without parsing
the message text. See `ValidationError` for the full list of categories.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, NamedTuple, Optional, Tuple, Union
import itertools
import re

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.TermLogic as tl



class DeclarationKind:
    """Kinds of vocabulary that a proof can explicitly introduce."""

    OBJECT = "object"
    PREDICATE = "predicate"
    CLOSED_FORMULA = "closed_formula"
    FUNCTION = "function"


@dataclass(frozen=True)
class Declaration:
    """A declaration of a symbol used by the proof language.

    `type_name` is descriptive type metadata. `metadata` contains additional
    structure-specific information produced by the surface elaborator, such
    as a relation's carrier and declared relation properties. The kernel
    remains agnostic about the meaning of that metadata.
    """

    name: str
    kind: str
    arity: Optional[int] = None
    type_name: Optional[str] = None
    metadata: tuple = ()


class DeclarationScope:
    """Lexically scoped declaration table.

    Child scopes see parent declarations. Local declarations do not leak out,
    and shadowing an existing declaration is deliberately forbidden.
    """

    __slots__ = ("_local", "_parent")

    def __init__(self, parent: Optional["DeclarationScope"] = None,
                 initial: Optional[List[Declaration]] = None):
        self._local: Dict[str, Declaration] = {}
        self._parent = parent
        for declaration in initial or []:
            existing = self.lookup(declaration.name)
            if existing is not None:
                if existing.kind == declaration.kind and (
                    existing.arity == declaration.arity
                    or existing.arity is None
                    or declaration.arity is None
                ):
                    continue
                raise KeyError(declaration.name)
            self.declare(declaration)

    def child(self) -> "DeclarationScope":
        return DeclarationScope(parent=self)

    def lookup(self, name: str) -> Optional[Declaration]:
        scope = self
        while scope is not None:
            declaration = scope._local.get(name)
            if declaration is not None:
                return declaration
            scope = scope._parent
        return None

    def declare(self, declaration: Declaration) -> None:
        if not isinstance(declaration, Declaration):
            raise TypeError("declaration must be a Declaration instance")
        if not declaration.name:
            raise ValueError("declaration name cannot be empty")
        if declaration.kind not in {
            DeclarationKind.OBJECT,
            DeclarationKind.PREDICATE,
            DeclarationKind.CLOSED_FORMULA,
            DeclarationKind.FUNCTION,
        }:
            raise ValueError(f"unknown declaration kind: {declaration.kind!r}")
        if declaration.arity is not None and declaration.arity < 0:
            raise ValueError("declaration arity cannot be negative")
        if self.lookup(declaration.name) is not None:
            raise KeyError(declaration.name)
        self._local[declaration.name] = declaration

    def declarations_here(self) -> List[Declaration]:
        return list(self._local.values())


def _infer_declarations_from_term(term: tl.Term) -> List[Declaration]:
    if isinstance(term, tl.VariableTerm):
        return []
    if isinstance(term, tl.ConstantTerm):
        return [Declaration(term.name, DeclarationKind.OBJECT)]
    if isinstance(term, tl.FunctionTerm):
        result = [Declaration(term.symbol, DeclarationKind.FUNCTION, arity=len(term.args))]
        for arg in term.args:
            result.extend(_infer_declarations_from_term(arg))
        return result
    return []


def _infer_declarations_from_formula(phi: fl.Formula) -> List[Declaration]:
    """Infer vocabulary from an explicit `(Declare)` formula.

    This is not used for ordinary premises. For example, `Nat(a). (Declare)`
    introduces `Nat` as a predicate and `a` as an object while also asserting
    the formula `Nat(a)`.
    """
    result: List[Declaration] = []
    if isinstance(phi, fl.AtomicFormula):
        if isinstance(phi.predicate, str):
            if phi.args:
                result.append(Declaration(phi.predicate, DeclarationKind.PREDICATE, arity=len(phi.args)))
            else:
                result.append(Declaration(phi.predicate, DeclarationKind.CLOSED_FORMULA))
        for arg in phi.args:
            if isinstance(arg, tl.Term):
                result.extend(_infer_declarations_from_term(arg))
        return result
    if isinstance(phi, fl.And):
        for item in phi.conjuncts:
            result.extend(_infer_declarations_from_formula(item))
    elif isinstance(phi, fl.Or):
        for item in phi.disjuncts:
            result.extend(_infer_declarations_from_formula(item))
    elif isinstance(phi, fl.Not):
        result.extend(_infer_declarations_from_formula(phi.sub))
    elif isinstance(phi, fl.Implies):
        result.extend(_infer_declarations_from_formula(phi.antecedent))
        result.extend(_infer_declarations_from_formula(phi.consequent))
    elif isinstance(phi, fl.Iff):
        result.extend(_infer_declarations_from_formula(phi.left))
        result.extend(_infer_declarations_from_formula(phi.right))
    elif isinstance(phi, fl.Equals):
        result.extend(_infer_declarations_from_term(phi.left))
        result.extend(_infer_declarations_from_term(phi.right))
    elif isinstance(phi, (fl.ForAll, fl.Exists)):
        result.extend(_infer_declarations_from_formula(phi.body))
    return result


def _dedupe_declarations(declarations: List[Declaration]) -> List[Declaration]:
    result: List[Declaration] = []
    seen = set()
    for declaration in declarations:
        key = (
            declaration.name,
            declaration.kind,
            declaration.arity,
            declaration.type_name,
            declaration.metadata,
        )
        if key not in seen:
            seen.add(key)
            result.append(declaration)
    return result


def infer_declarations(formulas: Iterable[fl.Formula]) -> List[Declaration]:
    """Public wrapper around the same inference `(Declare)` lines use
    internally: derive a `Declaration` for every predicate, function, and
    object constant mentioned across `formulas`, deduplicated.

    Declaration checking is unconditional now (see `ProofValidator`) -- every
    symbol must be declared, either by the proof itself (`Let ...`/`(Declare)`)
    or by a theory module's `declarations=`. This helper is for the third,
    programmatic case: constructing `declarations=` for a `Proof` built from
    hand-assembled entries (rather than parsed proof text) without writing
    out each symbol by hand. It infers from *shape*, so it cannot tell a
    predicate meant to be a 2-ary relation from one that only happens to be
    used with 2 arguments in what's passed in -- pass explicit `Declaration`s
    instead wherever that distinction matters.
    """
    result: List[Declaration] = []
    for phi in formulas:
        if isinstance(phi, fl.Formula):
            result.extend(_infer_declarations_from_formula(phi))
    return _dedupe_declarations(result)


def collect_formulas_from_entries(entries: list, *, skip_self_declaring: bool = True) -> List[fl.Formula]:
    """Every `Formula` referenced anywhere in `entries`, including inside
    nested and standalone subproofs, for feeding to `infer_declarations`.

    Unlike `MultiproofParser._top_level_formulas`, this collects *every*
    formula regardless of how it was justified (premise, axiom, rule
    conclusion, ...), not just ones a proof actually derived -- inference
    needs to see every symbol the proof *uses*, not just what it proves.

    With `skip_self_declaring=True` (the default), formulas tagged
    `'declare'` or `'arbitrary'`, and any entry whose justification carries
    its own attached declarations list (e.g. a `('premise', [Declaration(...)])`
    from a `Let ... such that:` prefix), are excluded: those already have
    their own declaration handling inside `ProofValidator` (an `'arbitrary'`
    flag registers its own constant; a `'declare'` line or an attached-list
    entry registers its declarations directly), so re-inferring for them
    here risks a spurious `CATEGORY_DECLARATION_CONFLICT` if this function's
    result and the validator's own registration disagree on kind for the
    same name. An `'assume'` formula is *not* self-declaring -- assuming
    `not A` still needs `A` declared somewhere, the same as citing it any
    other way -- so it stays in scope for inference here.
    """
    result: List[fl.Formula] = []
    for e in entries:
        parsed = _classify_entry(e)
        if isinstance(parsed, str):
            continue
        if parsed.is_subproof_block:
            result.extend(collect_formulas_from_entries(parsed.subproof_entries, skip_self_declaring=skip_self_declaring))
            continue

        justification = parsed.justification
        tag = justification[0] if isinstance(justification, tuple) and justification else None
        has_attached_declarations = (
            isinstance(justification, tuple) and len(justification) >= 2 and isinstance(justification[1], list)
        )
        skip = skip_self_declaring and (tag in ('declare', 'arbitrary') or has_attached_declarations)
        if not skip:
            phi = parsed.phi
            if isinstance(phi, list):
                result.extend(f for f in phi if isinstance(f, fl.Formula))
            elif isinstance(phi, fl.Formula):
                result.append(phi)

        if parsed.nested_subproof is not None:
            if tag == 'rule_hybrid':
                for subproof in parsed.nested_subproof:
                    result.extend(collect_formulas_from_entries(subproof, skip_self_declaring=skip_self_declaring))
            else:
                result.extend(collect_formulas_from_entries(parsed.nested_subproof, skip_self_declaring=skip_self_declaring))
    return result


def self_declared_names_in_entries(entries: list) -> "set[str]":
    """Every symbol name that `entries` declares for itself somewhere --
    via a `'declare'` line (explicit or inferred from its formula), an
    `'arbitrary'` flag, or an attached declarations list on any other
    tag -- searched recursively through subproofs.

    Pairs with `collect_formulas_from_entries`/`infer_declarations`: a
    caller building `declarations=` for a `Proof` from inferred formulas
    should drop any inferred `Declaration` whose name appears here, since
    the proof already declares that name itself and `DeclarationScope`
    rejects declaring the same name twice, even with a matching kind.
    """
    names: set = set()
    for e in entries:
        parsed = _classify_entry(e)
        if isinstance(parsed, str):
            continue
        if parsed.is_subproof_block:
            names |= self_declared_names_in_entries(parsed.subproof_entries)
            continue

        justification = parsed.justification
        tag = justification[0] if isinstance(justification, tuple) and justification else None
        if isinstance(justification, tuple) and len(justification) >= 2 and isinstance(justification[1], list):
            names |= {d.name for d in justification[1]}
        elif tag == 'declare' and isinstance(parsed.phi, fl.Formula):
            names |= {d.name for d in _infer_declarations_from_formula(parsed.phi)}
        if tag == 'arbitrary' and isinstance(parsed.phi, fl.AtomicFormula) and not parsed.phi.args and isinstance(parsed.phi.predicate, str):
            names.add(parsed.phi.predicate)

        if parsed.nested_subproof is not None:
            if tag == 'rule_hybrid':
                for subproof in parsed.nested_subproof:
                    names |= self_declared_names_in_entries(subproof)
            else:
                names |= self_declared_names_in_entries(parsed.nested_subproof)
    return names


# ==========================================================================
# SECTION 1 -- Structural equality
# ==========================================================================

def _ast_eq(a: Any, b: Any) -> bool:
    """Deep structural ("same tree shape") equality for Terms and Formulas.

    Neither plain Python `==` nor `is` should be used to compare two
    `Formula`s -- `Formula` and its subclasses (And, Or, Implies, ...)
    deliberately don't define `__eq__`/`__hash__` (see FormulaLogic.py),
    so `==` falls back to object identity and two separately-constructed
    but logically-identical formulas would incorrectly compare unequal.
    Every rule in this module compares formulas through `_ast_eq` instead
    of `==` for exactly this reason. (`Term` and its subclasses, by
    contrast, *do* define `__eq__`/`__hash__` in TermLogic.py, based on
    `repr()`; `_ast_eq` handles terms too, structurally, without relying
    on that.)

    `_ast_eq` recurses structurally: two nodes are equal iff they have the
    same connective/predicate/type and their children are pairwise equal
    (recursively, through Terms too). It is syntactic, not semantic --
    `A and B` and `B and A` are NOT `_ast_eq`, even though they are
    logically equivalent. (For that weaker, law-aware notion of sameness,
    see PropositionalEquivalenceRule below.)

    Examples::

        >>> a1, a2 = tl.ConstantTerm('a', 'a'), tl.ConstantTerm('a', 'a')
        >>> P_a, P_a_again = fl.AtomicFormula('P', [a1]), fl.AtomicFormula('P', [a2])
        >>> _ast_eq(P_a, P_a_again)          # same shape, different objects
        True
        >>> Q_a = fl.AtomicFormula('Q', [a1])
        >>> _ast_eq(P_a, Q_a)                # different predicate name
        False
        >>> _ast_eq(fl.And(P_a, Q_a), fl.And(Q_a, P_a))   # conjunct order matters
        False
    """
    if type(a) != type(b):
        return False

    if isinstance(a, tl.VariableTerm):
        return a.name == b.name
    if isinstance(a, tl.ConstantTerm):
        return a.name == b.name
    if isinstance(a, tl.FunctionTerm):
        return (a.symbol == b.symbol and
                len(a.args) == len(b.args) and
                all(_ast_eq(xa, xb) for xa, xb in zip(a.args, b.args)))

    if isinstance(a, fl.AtomicFormula):
        return (a.predicate == b.predicate and
                len(a.args) == len(b.args) and
                all(_ast_eq(xa, xb) for xa, xb in zip(a.args, b.args)))
    if isinstance(a, fl.And):
        return (len(a.conjuncts) == len(b.conjuncts) and
                all(_ast_eq(xa, xb) for xa, xb in zip(a.conjuncts, b.conjuncts)))
    if isinstance(a, fl.Or):
        return (len(a.disjuncts) == len(b.disjuncts) and
                all(_ast_eq(xa, xb) for xa, xb in zip(a.disjuncts, b.disjuncts)))
    if isinstance(a, fl.Not):
        return _ast_eq(a.sub, b.sub)
    if isinstance(a, fl.Implies):
        return _ast_eq(a.antecedent, b.antecedent) and _ast_eq(a.consequent, b.consequent)
    if isinstance(a, fl.Iff):
        return _ast_eq(a.left, b.left) and _ast_eq(a.right, b.right)
    if isinstance(a, fl.Equals):
        return _ast_eq(a.left, b.left) and _ast_eq(a.right, b.right)
    if isinstance(a, (fl.ForAll, fl.Exists)):
        return a.var == b.var and _ast_eq(a.body, b.body)

    return a == b


# ==========================================================================
# SECTION 2 -- Pattern matching (quantifier instantiation / generalization)
# ==========================================================================

class FormulaMatcher:
    """Matches a quantifier's bound-variable template against a concrete
    formula, recovering the term the variable stands for.

    This single class backs every rule that moves between a quantified
    formula and one of its instances: Universal Instantiation and
    Universal Generalization match a `ForAll`'s body against a candidate;
    Existential Introduction and Existential Elimination do the same for
    `Exists`. All four are really the same operation -- "does `target`
    look like `pattern` with `var_name` consistently replaced by some
    term?" -- just applied to different formula/term positions in each
    rule, so the matching logic lives here once instead of once per rule.

    A `FormulaMatcher` is meant to be used for exactly one match: construct
    it with the bound variable's name, call `match_formula` once, and (if
    it returned True) read off what the variable matched to from
    `.mapping`.

    Example -- instantiating "for all x, P(x)" down to "P(a)"::

        >>> x, a = tl.VariableTerm('x'), tl.ConstantTerm('a', 'a')
        >>> pattern = fl.AtomicFormula('P', [x])       # the quantifier body
        >>> target = fl.AtomicFormula('P', [a])        # a candidate instance
        >>> m = FormulaMatcher('x')
        >>> m.match_formula(pattern, target)
        True
        >>> m.mapping                                  # what 'x' matched to
        {'x': a}

    The same mapping is built for Universal Generalization, just read in
    the opposite spirit: there, `target` is a subproof's concluding
    formula "P(c)", and matching recovers that the generalized variable
    corresponds to the fresh constant `c`, which `UniversalGeneralizationRule`
    then separately re-checks for freshness (see that class's docstring).

    Every occurrence of `var_name` inside `pattern` must map to the *same*
    term -- `match_term` checks each new binding against the first one via
    `_ast_eq` -- so "for all x, R(x, x)" matches "R(a, a)" but never
    "R(a, b)".

    `match_formula` also refuses to descend into a *nested* quantifier that
    rebinds the same variable name::

        if pattern.var == self.var_name or target.var == self.var_name:
            return False

    which stops a match from silently reaching past a shadowing inner
    quantifier and binding the wrong (shadowed) `x`.
    """
    __slots__ = ("var_name", "mapping")

    def __init__(self, var_name: str):
        self.var_name = var_name
        self.mapping = {}

    def match_term(self, pattern: tl.Term, target: tl.Term) -> bool:
        if isinstance(pattern, tl.VariableTerm) and pattern.name == self.var_name:
            if self.var_name not in self.mapping:
                self.mapping[self.var_name] = target
                return True
            return _ast_eq(self.mapping[self.var_name], target)

        if isinstance(pattern, tl.VariableTerm):
            return isinstance(target, tl.VariableTerm) and pattern.name == target.name
        if isinstance(pattern, tl.ConstantTerm):
            return isinstance(target, tl.ConstantTerm) and pattern.name == target.name
        if isinstance(pattern, tl.FunctionTerm):
            if not isinstance(target, tl.FunctionTerm): return False
            if pattern.symbol != target.symbol or len(pattern.args) != len(target.args): return False
            return all(self.match_term(pa, ta) for pa, ta in zip(pattern.args, target.args))
        return False

    def match_formula(self, pattern: fl.Formula, target: fl.Formula) -> bool:
        if type(pattern) != type(target):
            return False

        if isinstance(pattern, fl.AtomicFormula):
            if pattern.predicate != target.predicate or len(pattern.args) != len(target.args): return False
            for pa, ta in zip(pattern.args, target.args):
                if isinstance(pa, tl.Term) and isinstance(ta, tl.Term):
                    if not self.match_term(pa, ta): return False
                else:
                    if not _ast_eq(pa, ta): return False
            return True

        if isinstance(pattern, fl.And):
            if len(pattern.conjuncts) != len(target.conjuncts): return False
            return all(self.match_formula(p, t) for p, t in zip(pattern.conjuncts, target.conjuncts))
        if isinstance(pattern, fl.Or):
            if len(pattern.disjuncts) != len(target.disjuncts): return False
            return all(self.match_formula(p, t) for p, t in zip(pattern.disjuncts, target.disjuncts))
        if isinstance(pattern, fl.Not):
            return self.match_formula(pattern.sub, target.sub)
        if isinstance(pattern, fl.Implies):
            return self.match_formula(pattern.antecedent, target.antecedent) and self.match_formula(pattern.consequent, target.consequent)
        if isinstance(pattern, fl.Iff):
            return self.match_formula(pattern.left, target.left) and self.match_formula(pattern.right, target.right)
        if isinstance(pattern, fl.Equals):
            # Equals holds Terms, not Formulas (like AtomicFormula's args),
            # so this matches via match_term, not match_formula -- without
            # this branch, a quantifier whose body mentions equality (e.g.
            # `forall x, (P(x) and x = a)`) would silently fail to
            # instantiate/generalize at all, since match_formula's type
            # dispatch would fall through to `return False` at the bottom.
            return self.match_term(pattern.left, target.left) and self.match_term(pattern.right, target.right)
        if isinstance(pattern, (fl.ForAll, fl.Exists)):
            if pattern.var == self.var_name or target.var == self.var_name: return False
            return self.match_formula(pattern.body, target.body)

        return False




# ==========================================================================
# SECTION 3 -- Core proof data structures
# ==========================================================================

class InferenceRule:
    """Base class for every inference rule.

    A rule is a stateless predicate over already-validated premises: given
    the `candidates` a proof line cites -- each one either a `Formula`
    already justified earlier in scope, or a `SubproofRecord` for rules
    that take a whole subproof as a premise -- and a proposed conclusion
    `phi`, `applies` answers "is this a sound application of the rule?"

    `applies` should not assume `len(candidates) == premise_arity`, even
    though `ProofValidator` checks that before ever calling a rule -- most
    rules re-check their own arity defensively (`if len(candidates) != 2:
    return False`, etc.) so that calling a rule directly, without going
    through the validator (as in a unit test, or interactively), can't be
    misused to skip that check.

    Subclassing checklist:
      * set `name` to a human-readable rule name (used in error messages)
      * set `premise_arity` to how many labels a citation of this rule
        must have -- `len(indices) != rule.premise_arity` is rejected
        before `applies` is ever consulted
      * implement `applies(candidates, phi) -> bool`
    """
    name = "base"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        raise NotImplementedError


class ExplosionRule(InferenceRule):
    """Explosion (ex falso): from a contradiction, infer any formula.

    The cited pair may be ``P`` and ``not P`` in either order.  The rule is
    intentionally independent of the conclusion formula.
    """

    name = "Explosion"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2:
            return False
        first, second = candidates
        return (
            isinstance(first, fl.Not) and _ast_eq(first.sub, second)
        ) or (
            isinstance(second, fl.Not) and _ast_eq(second.sub, first)
        )


class SubproofRecord:
    """The validated result of one Fitch subproof: its opening assumption,
    every formula it derived (`inner`), and enough context for rules that
    require a subproof's fresh name not to "leak" into anything visible
    before the subproof opened (UniversalGeneralizationRule,
    ExistentialEliminationRule).

    `assumption` is `inner[0]`: the subproof's first line, which is always
    either a genuine assumption (e.g. "not A. (Assumption for
    contradiction)") or an arbitrary-constant flag. For the latter,
    ProofParser encodes "Let c be in the domain." as
    `AtomicFormula('c', [])` -- a nullary atomic formula whose *predicate
    name* is literally the fresh constant's name. `UniversalGeneralizationRule`
    checks for exactly this encoding (see its docstring) to confirm a
    subproof genuinely introduced `c` as arbitrary, rather than merely
    mentioning it somewhere.

    `conclusion` is `inner[-1]`: what the subproof ultimately derived.
    Every rule that consumes a `SubproofRecord` (ConditionalIntroductionRule,
    ProofByContradictionRule, UniversalGeneralizationRule,
    ExistentialEliminationRule, DisjunctionEliminationRule) only ever reads
    `assumption` and/or `conclusion`; the formulas in between are kept
    around in `inner` purely so `_term_occurs_in_formula` can search the
    whole subproof when checking freshness.

    Outer-context bookkeeping -- why `outer_context_ref` + `boundary_index`
    instead of just a `list`:

        A naive SubproofRecord could store `outer_context = list(seen)` at
        construction time: a snapshot of every formula visible before the
        subproof opened. But `seen` (the enclosing block's accumulator) is
        one list the validator keeps appending to for the rest of that
        block's run, including everything that happens *after* this
        subproof closes. Copying it at every subproof would mean a proof
        with many (or deeply nested) subproofs pays repeated, mostly
        thrown-away O(n) copies as it goes.

        Instead, a SubproofRecord keeps a *reference* to that still-growing
        list (`outer_context_ref`) plus how many elements existed in it at
        the moment this subproof opened (`boundary_index`).
        `get_outer_context()` then reconstructs "what was visible when this
        subproof opened" on demand, without ever copying: only the prefix
        `outer_context_ref[:boundary_index]` counts as outer context, no
        matter how much longer the underlying list has since grown.

    Example: in a proof that states a premise on line 1 and then opens a
    subproof on line 2 (see testProofs/nested_subproof_outer_reference.txt),
    that subproof's `get_outer_context()` yields exactly the one formula
    from line 1 -- regardless of how many more lines the outer proof adds
    once the subproof closes.
    """
    __slots__ = ("assumption", "inner", "conclusion", "outer_context_ref", "boundary_index")

    def __init__(self, assumption: fl.Formula, inner_formulas: list, outer_context_ref: Optional[list] = None, boundary_index: int = 0):
        self.assumption = assumption
        self.inner = list(inner_formulas)
        self.conclusion = self.inner[-1] if self.inner else None

        # Memory optimization: reference the existing list and a slice index
        # instead of copying (see class docstring).
        self.outer_context_ref = outer_context_ref if outer_context_ref is not None else []
        self.boundary_index = boundary_index

    def get_outer_context(self) -> Iterator[Any]:
        """Every formula (or SubproofRecord) visible before this subproof
        opened, in order.

        Returns a fresh, one-shot iterator rather than a list. Both call
        sites (UniversalGeneralizationRule, ExistentialEliminationRule) only
        ever do a single `for outer_formula in sp.get_outer_context():`
        pass, so there is no need to materialize -- and immediately
        discard -- a full list every time a rule checks freshness. Call
        this again if a second pass is ever needed; each call produces an
        independent iterator over the same underlying data.
        """
        return itertools.islice(self.outer_context_ref, self.boundary_index)


class LabelScope:
    """A chain of label -> formula mappings, one link per proof-block
    nesting level.

    `ProofValidator` uses this to answer "what does line label L refer
    to?" while walking a Fitch-style proof. A subproof can cite anything
    visible in every block that encloses it, but nothing it defines
    locally should be visible again once that subproof closes.

    The direct way to get that scoping is to copy the accumulated label
    dict every time a subproof opens (`dict(labels)`), so writes inside the
    subproof land in a private copy and never touch the enclosing dict.
    That is correct, but it means a proof nested D levels deep with L total
    labels can do up to O(D * L) dict-copy work purely for scoping -- work
    that is thrown away the moment each subproof closes.

    `LabelScope` gets the identical semantics -- inner writes are invisible
    outside, outer labels remain visible inside -- by keeping only the
    labels defined *at this level*, plus a pointer to the parent scope.
    Opening a subproof is `parent.child()`: O(1), no copying. A lookup
    walks outward through the chain until it finds the label or runs out
    of parents, which costs O(nesting depth) -- the same asymptotic price
    the copy-everything approach paid on *every* subproof, but here paid
    only when a label is actually looked up.

    Example::

        >>> root = LabelScope()
        >>> root['1'] = premise_A          # a top-level premise, line 1
        >>> sub = root.child()             # entering "begin subproof"
        >>> sub['1.1'] = assumption_notA   # local to the subproof
        >>> sub['1']                       # still sees the outer premise
        premise_A
        >>> '1.1' in root                  # never leaks back to the parent
        False
    """
    __slots__ = ("_local", "_parent")

    def __init__(self, parent: Optional["LabelScope"] = None):
        self._local: Dict[str, Any] = {}
        self._parent = parent

    def __setitem__(self, label: str, value: Any) -> None:
        self._local[label] = value

    def __getitem__(self, label: str) -> Any:
        scope = self
        while scope is not None:
            if label in scope._local:
                return scope._local[label]
            scope = scope._parent
        raise KeyError(label)

    def __contains__(self, label: str) -> bool:
        try:
            self[label]
            return True
        except KeyError:
            return False

    def child(self) -> "LabelScope":
        """Open a new, nested scope for a subproof. Labels set on the
        child are invisible to `self` and any of `self`'s ancestors;
        labels already visible from `self` remain visible (read-only)
        from the child.
        """
        return LabelScope(parent=self)


# ==========================================================================
# SECTION 4 -- Propositional and quantifier inference rules
# ==========================================================================

class ConjunctionEliminationRule(InferenceRule):
    """And Elimination (^ Elim): from `A and B and ...`, infer any one conjunct.

    Example (testProofs/conjunction_elim.txt)::

        1. A and B. (Premise)
        2. A. (Conjunction Elimination from 1)
    """
    name = "ConjunctionElimination"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1: return False
        cand = candidates[0]
        if not isinstance(cand, fl.And): return False
        return any(_ast_eq(phi, c) for c in cand.conjuncts)


class ConjunctionIntroductionRule(InferenceRule):
    """And Introduction (^ Intro): from `A`, `B`, ... cited in that order,
    infer `A and B and ...`.

    Example (testProofs/simple_conjunction.txt)::

        1. A (Premise)
        2. not A (Premise)
        3. A and not A (Conjunction Introduction from 1, 2)

    Note: `applies` itself is written generically -- it checks `phi`'s
    conjuncts positionally against however many `candidates` it is given,
    with no upper bound -- but `premise_arity` is a fixed `2`, and
    ProofValidator rejects a citation with the wrong number of labels
    *before* `applies` is ever called (see `ProofValidator._validate_rule`).
    So in practice, through the validator, this rule can currently only
    combine exactly two lines per step; `A and B and C` has to be built as
    `(A and B) and C` rather than cited from three premises in one step.
    Making `premise_arity` depend on `phi` would lift this restriction, but
    that changes behavior rather than just readability, so it's left as-is
    and simply noted here.
    """
    name = "ConjunctionIntroduction"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) < 2 or not isinstance(phi, fl.And) or len(phi.conjuncts) != len(candidates):
            return False
        return all(_ast_eq(phi.conjuncts[i], candidates[i]) for i in range(len(candidates)))


class BiconditionalEliminationRule(InferenceRule):
    """Biconditional Elimination (<-> Elim): from `A <-> B`, infer either
    direction as a plain conditional: `A -> B` or `B -> A`.

    Example (testProofs/iff_elim.txt)::

        1. A <-> B. (Premise)
        2. A -> B. (Biconditional Elimination from 1)
        3. B -> A. (Biconditional Elimination from 1)

    ProofParser also routes the informal phrase "Conditional Elimination"
    to this rule (see testProofs/iff_example.txt) as a colloquial synonym.
    "Conditional Equivalence" is a different phrase that is *not* routed
    here -- it goes to PropositionalEquivalenceRule instead; see the note
    above the relevant check in `ProofParser.parse_justification`.
    """
    name = "BiconditionalElimination"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(candidates[0], fl.Iff) or not isinstance(phi, fl.Implies):
            return False
        cand = candidates[0]
        return ((_ast_eq(phi.antecedent, cand.left) and _ast_eq(phi.consequent, cand.right)) or
                (_ast_eq(phi.antecedent, cand.right) and _ast_eq(phi.consequent, cand.left)))


class ReiterationRule(InferenceRule):
    """Reiteration: from `A`, infer `A` again -- e.g. to pull a formula
    from an outer scope into a subproof (testProofs/conditional_intro.txt
    reiterates line 1.1 inside a nested subproof), or simply to restate a
    formula as its own justified line.

    Requires *exact* structural equality (`_ast_eq`). This is the
    complement of PropositionalEquivalenceRule below, which requires the
    cited formula and `phi` to differ by at least one recognized rewrite
    law: Reiteration handles "nothing changed", PropositionalEquivalenceRule
    handles "something changed according to a known law". Neither rule
    accepts what the other is for.
    """
    name = "Reiteration"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        return len(candidates) == 1 and _ast_eq(candidates[0], phi)


class ModusPonensRule(InferenceRule):
    """Modus Ponens (MP): from `A` and `A -> B`, infer `B`.

    Example (testProofs/mp_premises.txt)::

        1. A(a). (Premise)
        2. A(a) -> C(a). (Premise)
        3. C(a). (Modus Ponens from 1,2)

    Both citation orders are accepted -- "from 1,2" and "from 2,1" both
    work, whichever of the two cited lines happens to be the conditional --
    matching ModusTollensRule, HypotheticalSyllogismRule,
    DisjunctiveSyllogismRule, and BiconditionalIntroductionRule, which all
    already try candidates in either order. (An earlier version of this
    rule required the plain formula first and the conditional second,
    making it the only strictly-ordered two-premise propositional rule in
    the module; that restriction wasn't load-bearing for anything -- P and
    P->Q entail Q regardless of which one was cited first -- so it was
    dropped for consistency with its siblings. The relaxation is
    one-directional: every citation order that used to validate still
    does, and some that used to be rejected now also validate.)
    """
    name = "ModusPonens"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2: return False
        first, second = candidates

        if isinstance(second, fl.Implies) and _ast_eq(first, second.antecedent):
            conditional = second
        elif isinstance(first, fl.Implies) and _ast_eq(second, first.antecedent):
            conditional = first
        else:
            return False

        return _ast_eq(conditional.consequent, phi)


class ModusTollensRule(InferenceRule):
    """Modus Tollens (MT): from `A -> B` and `not B`, infer `not A`.

    Example (testProofs/modustollens.txt)::

        1. A -> B. (Premise)
        2. not B. (Premise)
        3. not A. (Modus Tollens from 1, 2)

    Unlike ModusPonensRule, this rule tries both citation orders: either
    candidate may be the conditional, with the other the negated
    consequent, so both "from 1,2" and "from 2,1" work as long as one cited
    line is `X -> Y` and the other is `not Y`.
    """
    name = "ModusTollens"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2: return False
        first, second = candidates

        if isinstance(first, fl.Implies) and isinstance(second, fl.Not):
            conditional, neg_consequent = first, second
        elif isinstance(second, fl.Implies) and isinstance(first, fl.Not):
            conditional, neg_consequent = second, first
        else:
            return False

        if not _ast_eq(neg_consequent.sub, conditional.consequent): return False
        return isinstance(phi, fl.Not) and _ast_eq(phi.sub, conditional.antecedent)


class DisjunctionIntroductionRule(InferenceRule):
    """Disjunction Introduction (v Intro / Addition):
    From P, infer P v Q or Q v P.
    The premise can match any of the resulting disjuncts.

    Example (testProofs/or-intro.txt)::

        1. P. (Premise)
        2. P or Q. (Disjunction Introduction from 1)
        3. R or P. (Disjunction Introduction from 1)     -- P may be either disjunct
    """
    name = "DisjunctionIntroduction"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(phi, fl.Or):
            return False
        return any(_ast_eq(candidates[0], d) for d in phi.disjuncts)


class DisjunctionEliminationRule(InferenceRule):
    """Disjunction Elimination (v Elim / Proof by Cases):
    From P v Q, a subproof assuming P that concludes R, and a 
    subproof assuming Q that concludes R, infer R.

    This is one of two rules (see ExistentialEliminationRule below) that
    take *subproofs themselves* as premises, rather than a single formula a
    subproof derives. Their citations reference standalone subproof blocks
    by label -- the `(label, 'subproof', [...])` entry form ProofParser
    produces for a "begin subproof ... end subproof" block that is *not*
    immediately preceded by a "... from subproof below" line -- rather than
    the inline `rule_below` form used by ConditionalIntroductionRule,
    ProofByContradictionRule, and UniversalGeneralizationRule. Schematically:

        1. P or Q. (Premise)
        2. [subproof, label 2, assumes P, concludes R]
        3. [subproof, label 3, assumes Q, concludes R]
        4. R. (Disjunction Elimination from 1, 2, 3)

    No fixture file in testProofs/ currently exercises this rule, but the
    mechanism above is exactly what `applies` checks and was verified
    directly against `ProofValidator` while writing this docstring.
    """
    name = "DisjunctionElimination"
    premise_arity = 3

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 3:
            return False

        disjunction = None
        subproofs = []
        for c in candidates:
            if isinstance(c, fl.Or) and len(c.disjuncts) == 2 and disjunction is None:
                disjunction = c
            elif isinstance(c, SubproofRecord):
                subproofs.append(c)

        if disjunction is None or len(subproofs) != 2:
            return False

        sp1, sp2 = subproofs

        if sp1.conclusion is None or sp2.conclusion is None:
            return False
        if not _ast_eq(sp1.conclusion, phi) or not _ast_eq(sp2.conclusion, phi):
            return False

        d1, d2 = disjunction.disjuncts
        a1, a2 = sp1.assumption, sp2.assumption

        # The assumptions of the subproofs must match the disjuncts in any order
        return (_ast_eq(a1, d1) and _ast_eq(a2, d2)) or (_ast_eq(a1, d2) and _ast_eq(a2, d1))


class BiconditionalIntroductionRule(InferenceRule):
    """Biconditional Introduction (<-> Intro):
    From P -> Q and Q -> P, infer P <-> Q.

    Example (testProofs/iff_intro.txt)::

        1. A -> B. (Premise)
        2. B -> A. (Premise)
        3. A <-> B. (Biconditional Introduction from 1, 2)

    Like ModusTollensRule, both citation orders are accepted -- either
    candidate may supply the left-to-right or the right-to-left direction.
    """
    name = "BiconditionalIntroduction"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2 or not isinstance(phi, fl.Iff):
            return False

        c1, c2 = candidates
        if not isinstance(c1, fl.Implies) or not isinstance(c2, fl.Implies):
            return False

        return ((_ast_eq(c1.antecedent, phi.left) and _ast_eq(c1.consequent, phi.right) and
                 _ast_eq(c2.antecedent, phi.right) and _ast_eq(c2.consequent, phi.left)) or
                (_ast_eq(c2.antecedent, phi.left) and _ast_eq(c2.consequent, phi.right) and
                 _ast_eq(c1.antecedent, phi.right) and _ast_eq(c1.consequent, phi.left)))


class DisjunctiveSyllogismRule(InferenceRule):
    """Disjunctive Syllogism (DS):
    From P v Q and ~P, infer Q. (Or from P v Q and ~Q, infer P).

    Example (testProofs/disjunctivesyllogism.txt)::

        1. A or B. (Premise)
        2. not A. (Premise)
        3. B. (Disjunctive Syllogism from 1, 2)
        4. not B. (Premise)
        5. A. (Disjunctive Syllogism from 1, 4)

    Both citation orders are accepted (the disjunction and the negation may
    be cited in either order), and either disjunct may be the one negated.
    """
    name = "DisjunctiveSyllogism"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2:
            return False

        c1, c2 = candidates
        if isinstance(c1, fl.Or) and isinstance(c2, fl.Not):
            disj, neg = c1, c2
        elif isinstance(c2, fl.Or) and isinstance(c1, fl.Not):
            disj, neg = c2, c1
        else:
            return False

        if len(disj.disjuncts) != 2:
            return False

        d1, d2 = disj.disjuncts
        if _ast_eq(neg.sub, d1):
            return _ast_eq(phi, d2)
        if _ast_eq(neg.sub, d2):
            return _ast_eq(phi, d1)

        return False


class HypotheticalSyllogismRule(InferenceRule):
    """Hypothetical Syllogism (HS):
    From P -> Q and Q -> R, infer P -> R.

    Example (testProofs/hs.txt)::

        1. A -> B. (Premise)
        2. B -> C. (Premise)
        3. A -> C. (Hypothetical Syllogism from 1, 2)

    Both citation orders are accepted, as long as one candidate's consequent
    matches the other's antecedent (a "chain" in either order).
    """
    name = "HypotheticalSyllogism"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2 or not isinstance(phi, fl.Implies):
            return False

        c1, c2 = candidates
        if not isinstance(c1, fl.Implies) or not isinstance(c2, fl.Implies):
            return False

        if _ast_eq(c1.antecedent, phi.antecedent) and _ast_eq(c1.consequent, c2.antecedent) and _ast_eq(c2.consequent, phi.consequent):
            return True
        if _ast_eq(c2.antecedent, phi.antecedent) and _ast_eq(c2.consequent, c1.antecedent) and _ast_eq(c1.consequent, phi.consequent):
            return True

        return False


class ExistentialIntroductionRule(InferenceRule):
    """Existential Introduction (Exists Intro):
    From P(c), infer Exists x.P(x).

    Example (testProofs/exintro.txt)::

        1. P(a). (Premise)
        2. exists x, P(x). (Existential Introduction from 1)

    Uses `FormulaMatcher` in the "generalizing" direction: it matches the
    quantifier's body pattern `P(x)` against the concrete candidate `P(a)`
    to confirm `a` is a valid witness, without separately checking
    freshness -- unlike Universal Generalization or Existential
    Elimination, introducing an existential never requires the witness to
    be new.
    """
    name = "ExistentialIntroduction"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(phi, fl.Exists):
            return False

        matcher = FormulaMatcher(phi.var)
        return matcher.match_formula(phi.body, candidates[0])


class ExistentialEliminationRule(InferenceRule):
    """Existential Elimination (Exists Elim):
    From Exists x.P(x) and a subproof assuming P(c) (where c is a fresh constant) 
    that concludes Q, infer Q.

    Like DisjunctionEliminationRule above, this rule consumes a
    `SubproofRecord` as one of its premises (the subproof assuming `P(c)`),
    cited via a standalone labeled subproof block.

    Freshness: once `FormulaMatcher` recovers which constant `c` the
    subproof's assumption instantiated `x` to, `c` must not already occur
    in the conclusion `phi`, in the existential formula itself, or in
    *anything visible before the subproof opened* (`sp.get_outer_context()`)
    -- otherwise `c` wasn't really an arbitrary "some witness or other", it
    was smuggling in a specific, previously-mentioned term. If `x` doesn't
    actually occur free in `exists_form.body` (a vacuous quantifier), no
    constant is introduced by instantiation and these freshness checks are
    skipped, since nothing was actually generalized away.
    """
    name = "ExistentialElimination"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2:
            return False

        c1, c2 = candidates
        if isinstance(c1, fl.Exists) and isinstance(c2, SubproofRecord):
            exists_form, sp = c1, c2
        elif isinstance(c2, fl.Exists) and isinstance(c1, SubproofRecord):
            exists_form, sp = c2, c1
        else:
            return False

        if sp.conclusion is None or not _ast_eq(sp.conclusion, phi):
            return False

        matcher = FormulaMatcher(exists_form.var)
        if not matcher.match_formula(exists_form.body, sp.assumption):
            return False

        if exists_form.var in matcher.mapping:
            instantiated_term = matcher.mapping[exists_form.var]
            if not isinstance(instantiated_term, tl.ConstantTerm):
                return False

            # Freshness constraints for Existential Elimination
            if _term_occurs_in_formula(instantiated_term, phi):
                return False
            if _term_occurs_in_formula(instantiated_term, exists_form):
                return False
            for outer_formula in sp.get_outer_context():
                if _term_occurs_in_formula(instantiated_term, outer_formula):
                    return False

        return True


class UniversalInstantiationRule(InferenceRule):
    """Universal Instantiation (UI): from `for all x, P(x)`, infer `P(t)`
    for any term `t` (typically a specific constant).

    Example (testProofs/universal_instantiation.txt)::

        1. for all x, P(x). (Premise)
        2. P(a). (Universal Instantiation from 1)

    No freshness restriction applies here -- unlike Universal
    Generalization, instantiating a universal to a specific (possibly
    already-mentioned) term is always sound.
    """
    name = "UniversalInstantiation"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(candidates[0], fl.ForAll):
            return False
        earlier = candidates[0]
        matcher = FormulaMatcher(earlier.var)
        return matcher.match_formula(earlier.body, phi)


def _term_occurs_in_term(needle: tl.Term, haystack: tl.Term) -> bool:
    """True if `needle` occurs anywhere inside `haystack` (including
    `haystack` itself), searching through nested function terms.
    """
    if _ast_eq(needle, haystack): return True
    if isinstance(haystack, tl.FunctionTerm):
        return any(_term_occurs_in_term(needle, a) for a in haystack.args)
    return False


def _term_occurs_in_formula(needle: tl.Term, formula) -> bool:
    """True if the term `needle` occurs anywhere inside `formula`.

    Used exclusively for freshness checks (UniversalGeneralizationRule,
    ExistentialEliminationRule): a constant introduced as "arbitrary" or
    "fresh" inside a subproof must not already appear anywhere it could
    leak meaning back out, so both rules search entire formulas -- and,
    via the `SubproofRecord` branch here, entire subproofs -- for a given
    constant before allowing generalization/elimination to fire.
    """
    if isinstance(formula, SubproofRecord):
        return any(_term_occurs_in_formula(needle, f) for f in formula.inner)
    if isinstance(formula, fl.AtomicFormula):
        return any(isinstance(a, tl.Term) and _term_occurs_in_term(needle, a) for a in formula.args)
    if isinstance(formula, fl.And):
        return any(_term_occurs_in_formula(needle, c) for c in formula.conjuncts)
    if isinstance(formula, fl.Or):
        return any(_term_occurs_in_formula(needle, d) for d in formula.disjuncts)
    if isinstance(formula, fl.Not):
        return _term_occurs_in_formula(needle, formula.sub)
    if isinstance(formula, fl.Implies):
        return _term_occurs_in_formula(needle, formula.antecedent) or _term_occurs_in_formula(needle, formula.consequent)
    if isinstance(formula, fl.Iff):
        return _term_occurs_in_formula(needle, formula.left) or _term_occurs_in_formula(needle, formula.right)
    if isinstance(formula, fl.Equals):
        # Soundness-critical: without this branch, a fresh constant's
        # occurrence inside an equality statement (e.g. an outer-context
        # formula "a = c") would be invisible to this search, and
        # UniversalGeneralizationRule/ExistentialEliminationRule could
        # wrongly treat `c` as fresh when it's actually already
        # constrained by that equality.
        return _term_occurs_in_term(needle, formula.left) or _term_occurs_in_term(needle, formula.right)
    if isinstance(formula, (fl.ForAll, fl.Exists)):
        return _term_occurs_in_formula(needle, formula.body)
    return False


class UniversalGeneralizationRule(InferenceRule):
    """Universal Generalization (UG): from a subproof that introduces an
    arbitrary constant `c` ("Let c be in the domain.") and concludes
    `P(c)`, infer `for all x, P(x)`.

    Example (testProofs/ug.txt)::

        1. forall y, P(y) (premise)
        2. forall x, P(x) (universal generalization from subproof below)
        begin subproof
            2.0. Let c be in the domain.  (Fresh Variable)
            2.1. P(c) (universal instantiation from 1)
        end subproof

    This is the most constraint-heavy rule in the module; every check
    exists to block a specific way "c is arbitrary" could be violated:

      1. `FormulaMatcher(phi.var).match_formula(phi.body, sp_record.conclusion)`
         -- the subproof's conclusion must literally be `phi`'s body with
         `phi.var` replaced by some single term (the constant being
         generalized away).
      2. `isinstance(generalizing_term, tl.ConstantTerm)` -- generalizing
         over anything other than a plain constant (a variable, or a
         compound function term) isn't a valid instance of this rule.
      3. The "Let c be in the domain." encoding check -- `flag` (the
         subproof's assumption) must be a nullary `AtomicFormula` whose
         predicate name is literally the constant's name (see
         SubproofRecord's docstring for why this specific encoding is used).
         This confirms the subproof's *opening line* is the one that
         introduced `c`, not just that `c` happens to appear somewhere.
      4. The freshness loop over `sp_record.get_outer_context()` -- `c`
         must not occur anywhere visible *before* the subproof opened. If
         it did, `c` wouldn't be a fresh, arbitrary stand-in; it would be
         smuggling a constraint from outside the subproof into a
         conclusion that's supposed to hold for every object in the
         domain.
    """
    name = "UniversalGeneralization"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(candidates[0], SubproofRecord) or not isinstance(phi, fl.ForAll):
            return False

        sp_record = candidates[0]
        if sp_record.conclusion is None: return False

        matcher = FormulaMatcher(phi.var)
        if not matcher.match_formula(phi.body, sp_record.conclusion) or phi.var not in matcher.mapping:
            return False

        generalizing_term = matcher.mapping[phi.var]

        if not isinstance(generalizing_term, tl.ConstantTerm):
            return False

        flag = sp_record.assumption
        if not isinstance(flag, fl.AtomicFormula) or len(flag.args) != 0 or flag.predicate != generalizing_term.name:
            return False

        for outer_formula in sp_record.get_outer_context():
            if _term_occurs_in_formula(generalizing_term, outer_formula):
                return False

        return True


# ==========================================================================
# SECTION 5 -- Propositional equivalence substitution
# ==========================================================================
#
# PropositionalEquivalenceRule lets a proof rewrite a formula using one of
# four classic propositional laws -- Double Negation, De Morgan's, Material
# Implication, and Distribution -- applied anywhere inside the formula tree,
# not just at the top level. `_equivalent_by_substitution` is the entry
# point: it first tries all four laws at the current node, and if none
# match, recurses into corresponding children (same connective, same
# number of children) looking for the rewrite deeper in the tree.

def _match_double_negation(f1: fl.Formula, f2: fl.Formula) -> bool:
    """`A` <-> `not not A`, checked in whichever direction f1/f2 are given.

    Example: `_match_double_negation(B, Not(Not(B)))` and
    `_match_double_negation(Not(Not(B)), B)` are both True.
    """
    def one_way(a, b):
        return isinstance(b, fl.Not) and isinstance(b.sub, fl.Not) and _ast_eq(b.sub.sub, a)
    return one_way(f1, f2) or one_way(f2, f1)

def _match_demorgan(f1: fl.Formula, f2: fl.Formula) -> bool:
    """De Morgan's laws, generalized to N-ary And/Or:
    `not (A and B and ...)` <-> `(not A) or (not B) or ...`
    `not (A or B and ...)` <-> `(not A) and (not B) and ...`

    Example (testProofs/demorgan_doublenega.txt, line 2): matches
    `not (A and not B)` against `(not A) or not (not B)`.
    """
    def one_way(a, b):
        if isinstance(a, fl.Not) and isinstance(a.sub, fl.And):
            if isinstance(b, fl.Or) and len(b.disjuncts) == len(a.sub.conjuncts):
                return all(isinstance(d, fl.Not) and _ast_eq(d.sub, c) for c, d in zip(a.sub.conjuncts, b.disjuncts))
        if isinstance(a, fl.Not) and isinstance(a.sub, fl.Or):
            if isinstance(b, fl.And) and len(b.conjuncts) == len(a.sub.disjuncts):
                return all(isinstance(c, fl.Not) and _ast_eq(c.sub, d) for d, c in zip(a.sub.disjuncts, b.conjuncts))
        return False
    return one_way(f1, f2) or one_way(f2, f1)

def _match_material_implication(f1: fl.Formula, f2: fl.Formula) -> bool:
    """`A -> B` <-> `(not A) or B`.

    Note: only the disjuncts in exactly this order are recognized -- the
    Or's first disjunct must be the negated antecedent and its second the
    plain consequent. `B or (not A)` (disjuncts swapped) will *not* match
    `A -> B`, since this substitution system has no separate notion of
    commutativity for `and`/`or` (each of the four match_* functions here
    checks a specific shape, not "up to reordering"). Route around this by
    citing the disjunction already in `(not A) or B` order, e.g. via
    testProofs/conditional_contradiction.txt's use of this law.
    """
    def one_way(a, b):
        if not (isinstance(a, fl.Implies) and isinstance(b, fl.Or) and len(b.disjuncts) == 2): return False
        left, right = b.disjuncts
        return isinstance(left, fl.Not) and _ast_eq(left.sub, a.antecedent) and _ast_eq(right, a.consequent)
    return one_way(f1, f2) or one_way(f2, f1)

def _match_distribution(f1: fl.Formula, f2: fl.Formula) -> bool:
    """Binary distribution laws:
    `A and (B or C)` <-> `(A and B) or (A and C)`
    `A or (B and C)` <-> `(A or B) and (A or C)`
    checked with the "distributed-over" operand on either side of the
    outer connective, and the two results in either order.
    """
    def and_over_or(a, b):
        if not (isinstance(a, fl.And) and len(a.conjuncts) == 2): return False
        left, right = a.conjuncts
        for p, orpart in ((left, right), (right, left)):
            if not (isinstance(orpart, fl.Or) and len(orpart.disjuncts) == 2): continue
            q, r = orpart.disjuncts
            if not (isinstance(b, fl.Or) and len(b.disjuncts) == 2): continue
            b1, b2 = b.disjuncts
            if (_ast_eq(b1, fl.And(p, q)) and _ast_eq(b2, fl.And(p, r))) or (_ast_eq(b1, fl.And(p, r)) and _ast_eq(b2, fl.And(p, q))): return True
        return False

    def or_over_and(a, b):
        if not (isinstance(a, fl.Or) and len(a.disjuncts) == 2): return False
        left, right = a.disjuncts
        for p, andpart in ((left, right), (right, left)):
            if not (isinstance(andpart, fl.And) and len(andpart.conjuncts) == 2): continue
            q, r = andpart.conjuncts
            if not (isinstance(b, fl.And) and len(b.conjuncts) == 2): continue
            b1, b2 = b.conjuncts
            if (_ast_eq(b1, fl.Or(p, q)) and _ast_eq(b2, fl.Or(p, r))) or (_ast_eq(b1, fl.Or(p, r)) and _ast_eq(b2, fl.Or(p, q))): return True
        return False

    return and_over_or(f1, f2) or or_over_and(f1, f2) or and_over_or(f2, f1) or or_over_and(f2, f1)


def _equivalent_by_substitution(old: fl.Formula, new: fl.Formula) -> bool:
    """True if `new` can be reached from `old` by applying one or more of
    the four laws above, anywhere in the formula tree (possibly at several
    positions at once).

    First tries all four laws at the *top* level (`old` vs `new` as whole
    formulas). If none match, decomposes both into their immediate
    children -- requiring the same connective and, for quantifiers, the
    same bound variable name (this system does not rename bound variables,
    so `for all x, ...` can only become another `for all x, ...`, never
    `for all y, ...`) -- and recurses child by child: a child that is
    already `_ast_eq` is left alone, a child that differs must itself be
    `_equivalent_by_substitution`, and at least one child must actually
    differ (`changed`).

    That last condition means `_equivalent_by_substitution(X, X)` is
    always False, by design: citing the *same* formula again is
    Reiteration's job, not this rule's (see ReiterationRule above).

    Example: `_equivalent_by_substitution(Or(Not(A), Not(Not(B))), Or(Not(A), B))`
    is True even though neither side matches a law *at the top level*
    (the top connective is `Or`, not `Not`) -- it matches because the
    first disjunct is unchanged and the second differs by exactly a
    Double Negation rewrite. This is exactly how
    testProofs/demorgan_doublenega.txt's line 3 is justified.
    """
    if (_match_double_negation(old, new) or _match_demorgan(old, new) or
        _match_material_implication(old, new) or _match_distribution(old, new)):
        return True

    def get_children(form):
        if isinstance(form, fl.And): return ('and', list(form.conjuncts))
        if isinstance(form, fl.Or): return ('or', list(form.disjuncts))
        if isinstance(form, fl.Not): return ('not', [form.sub])
        if isinstance(form, fl.Implies): return ('implies', [form.antecedent, form.consequent])
        if isinstance(form, fl.Iff): return ('iff', [form.left, form.right])
        if isinstance(form, fl.ForAll): return (('forall', form.var), [form.body])
        if isinstance(form, fl.Exists): return (('exists', form.var), [form.body])
        return None

    old_info, new_info = get_children(old), get_children(new)
    if not old_info or not new_info or old_info[0] != new_info[0] or len(old_info[1]) != len(new_info[1]):
        return False

    changed = False
    for oc, nc in zip(old_info[1], new_info[1]):
        if _ast_eq(oc, nc): continue
        if not _equivalent_by_substitution(oc, nc): return False
        changed = True
    return changed


class PropositionalEquivalenceRule(InferenceRule):
    """From `A`, infer any `B` reachable from `A` by Double Negation,
    De Morgan's, Material Implication, or Distribution (see
    `_equivalent_by_substitution` above for exactly what that means).

    Example (testProofs/demorgan_doublenega.txt)::

        1. not (A and not B). (Premise)
        2. not A or not (not B). (De Morgans from 1)
        3. not A or B. (Double Negation from 2)

    ProofParser routes several rule-name phrases here -- "De Morgans",
    "Distribution", "Double Negation", any phrase containing "equiv"
    (including "Conditional Equivalence" -- see
    `ProofParser.parse_justification`) -- since all four laws are checked
    by the same underlying function regardless of which specific law a
    proof's justification text names.
    """
    name = "PropositionalEquivalence"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        return len(candidates) == 1 and _equivalent_by_substitution(candidates[0], phi)


# ==========================================================================
# SECTION 6 -- Rules that discharge a subproof directly (rule_below)
# ==========================================================================

class ConditionalIntroductionRule(InferenceRule):
    """Conditional Introduction (-> Intro): from a subproof that assumes
    `A` and concludes `B`, infer `A -> B`.

    Example (testProofs/conditional_intro.txt)::

        1. A -> (B -> A). (Conditional Introduction from subproof below)
        begin subproof
         1.1. A. (Assumption for conditional introduction)
         1.2. B -> A. (Conditional Introduction from subproof below)
         begin subproof
          1.2.1. B. (Assumption for conditional introduction)
          1.2.2. A. (Reiteration from 1.1)
         end subproof
        end subproof

    Cited via the `rule_below` mechanism (an inline subproof immediately
    following the justifying line), not by label -- contrast with
    DisjunctionEliminationRule/ExistentialEliminationRule, which cite
    subproofs by label instead.
    """
    name = "ConditionalIntroduction"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(candidates[0], SubproofRecord): return False
        sp = candidates[0]
        if sp.assumption is None or sp.conclusion is None: return False
        return isinstance(phi, fl.Implies) and _ast_eq(phi.antecedent, sp.assumption) and _ast_eq(phi.consequent, sp.conclusion)


def _is_contradiction(formula: fl.Formula) -> bool:
    """True if `formula` is `X and not X` (in either conjunct order), or
    more generally `X and Y` where `X` and `Y` are the same formula under
    an odd/even number of negations -- e.g. `not not A and not A` also
    counts, since stripping negations leaves `A` on both sides with
    mismatched parity.
    """
    if not isinstance(formula, fl.And) or len(formula.conjuncts) != 2: return False
    left, right = formula.conjuncts

    def unnegate(f):
        cnt = 0
        while isinstance(f, fl.Not):
            cnt += 1
            f = f.sub
        return f, cnt

    left_inner, left_cnt = unnegate(left)
    right_inner, right_cnt = unnegate(right)

    if _ast_eq(left_inner, right_inner) and (left_cnt % 2) != (right_cnt % 2):
        return True

    return (isinstance(left, fl.Not) and _ast_eq(left.sub, right)) or (isinstance(right, fl.Not) and _ast_eq(right.sub, left))


class ProofByContradictionRule(InferenceRule):
    """Proof by Contradiction / Reductio ad Absurdum: from a subproof that
    assumes `not A` and derives a contradiction, infer `A`. Symmetrically,
    from a subproof that assumes `A` and derives a contradiction, infer
    `not A`.

    Example (testProofs/proof_by_contradiction.txt)::

        1. A or not A. (Proof by Contradiction from subproof below)
        begin subproof
         1.1. not (A or not A). (Assumption for contradiction)
         1.2. (not A) and not (not A). (De Morgans from 1.1)
        end subproof

    Which direction applies is decided by the *shape of the assumption*:
    if the subproof assumed `not A`, `phi` must be `A`; otherwise `phi`
    must be `not (assumption)`. See `_is_contradiction` above for exactly
    what counts as a contradiction.
    """
    name = "ProofByContradiction"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(candidates[0], SubproofRecord): return False
        sp = candidates[0]
        if sp.conclusion is None or not _is_contradiction(sp.conclusion): return False

        if isinstance(sp.assumption, fl.Not):
            return _ast_eq(phi, sp.assumption.sub)
        return isinstance(phi, fl.Not) and _ast_eq(phi.sub, sp.assumption)


# ==========================================================================
# SECTION 6.5 -- Equality
# ==========================================================================
#
# Four rules form the equality kernel. Reflexivity and Substitution are the
# minimal sound pair -- symmetry and transitivity are both derivable from
# them (substituting into an instance of reflexivity gives symmetry; one
# substitution into a hypothesis gives transitivity directly) -- but both
# are implemented directly anyway, each a single O(1) structural check,
# rather than requiring a multi-step derivation every time a proof needs
# something this routine. This mirrors PropositionalEquivalenceRule, which
# packages several individually-derivable propositional laws into rules a
# proof can cite in one step for the same reason.

def _term_obtainable_by_replacing(source: tl.Term, s: tl.Term, t: tl.Term, target: tl.Term) -> Optional[bool]:
    """Is `target` reachable from `source` by replacing zero or more
    occurrences of the term `s` with `t`?

    Returns None if not reachable at all (a structural mismatch unrelated
    to s/t), otherwise True/False for whether at least one replacement
    actually happened within this subtree -- the two are kept distinct
    (rather than collapsing to a single "is this valid" bool) so that a
    citation making no actual substitution can be told apart from one that
    does; see LeibnizSubstitutionRule, which requires at least one
    genuine replacement, the same way PropositionalEquivalenceRule does.

    The two base checks are order-sensitive and deliberately checked in
    this order: "was this position s, and is it now t" is checked BEFORE
    "is this position unchanged", because if `source` happens to already
    equal `target` (nothing to replace) that check would otherwise fire
    first and report "valid, unchanged" even at a position that legitimately
    matches the substitution pattern.
    """
    if _ast_eq(source, s) and _ast_eq(target, t):
        return True
    if _ast_eq(source, target):
        return False
    if isinstance(source, tl.FunctionTerm) and isinstance(target, tl.FunctionTerm):
        if source.symbol != target.symbol or len(source.args) != len(target.args):
            return None
        results = [_term_obtainable_by_replacing(sa, s, t, ta) for sa, ta in zip(source.args, target.args)]
        if any(r is None for r in results):
            return None
        return any(results)
    return None


def _formula_obtainable_by_replacing(source: fl.Formula, s: tl.Term, t: tl.Term, target: fl.Formula) -> Optional[bool]:
    """Formula-level counterpart of `_term_obtainable_by_replacing`: is
    `target` reachable from `source` by replacing zero or more occurrences
    of the term `s` with `t`, anywhere inside `source`'s structure?

    Recurses through the propositional/quantifier connectives exactly the
    way `_equivalent_by_substitution` does (same connective and child
    count required at every level), bottoming out in
    `_term_obtannable_by_replacing` at `AtomicFormula`'s and `Equals`'s
    term-valued positions.
    """
    if type(source) != type(target):
        return None

    if isinstance(source, fl.AtomicFormula):
        if source.predicate != target.predicate or len(source.args) != len(target.args):
            return None
        results = [_term_obtainable_by_replacing(sa, s, t, ta) for sa, ta in zip(source.args, target.args)]
        if any(r is None for r in results):
            return None
        return any(results)

    if isinstance(source, fl.Equals):
        rl = _term_obtainable_by_replacing(source.left, s, t, target.left)
        rr = _term_obtainable_by_replacing(source.right, s, t, target.right)
        if rl is None or rr is None:
            return None
        return rl or rr

    if isinstance(source, fl.And):
        if len(source.conjuncts) != len(target.conjuncts): return None
        results = [_formula_obtainable_by_replacing(sc, s, t, tc) for sc, tc in zip(source.conjuncts, target.conjuncts)]
        if any(r is None for r in results): return None
        return any(results)
    if isinstance(source, fl.Or):
        if len(source.disjuncts) != len(target.disjuncts): return None
        results = [_formula_obtainable_by_replacing(sd, s, t, td) for sd, td in zip(source.disjuncts, target.disjuncts)]
        if any(r is None for r in results): return None
        return any(results)
    if isinstance(source, fl.Not):
        return _formula_obtainable_by_replacing(source.sub, s, t, target.sub)
    if isinstance(source, fl.Implies):
        ra = _formula_obtainable_by_replacing(source.antecedent, s, t, target.antecedent)
        rc = _formula_obtainable_by_replacing(source.consequent, s, t, target.consequent)
        if ra is None or rc is None: return None
        return ra or rc
    if isinstance(source, fl.Iff):
        rl = _formula_obtainable_by_replacing(source.left, s, t, target.left)
        rr = _formula_obtainable_by_replacing(source.right, s, t, target.right)
        if rl is None or rr is None: return None
        return rl or rr
    if isinstance(source, (fl.ForAll, fl.Exists)):
        if source.var != target.var:
            return None
        return _formula_obtainable_by_replacing(source.body, s, t, target.body)

    return None


class ReflexivityRule(InferenceRule):
    """From nothing, infer `t = t` for any term `t`.

    The only 0-premise rule in this module (`premise_arity = 0`): a
    citation supplies no labels at all, e.g. "(Reflexivity)" with no
    "from ...", and `ProofValidator._validate_rule`'s existing arity check
    (`len(indices) != rule.premise_arity`) already handles arity 0 exactly
    like any other arity, so no changes were needed there.
    """
    name = "Reflexivity"
    premise_arity = 0

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 0:
            return False
        return isinstance(phi, fl.Equals) and _ast_eq(phi.left, phi.right)


class LeibnizSubstitutionRule(InferenceRule):
    """Equality Elimination / Leibniz's Law: from `s = t` and a formula
    mentioning `s`, infer the same formula with one or more occurrences of
    `s` replaced by `t` -- or, symmetrically, `t` replaced by `s`, since in
    practice a single equality fact is used in either direction without
    first invoking SymmetryRule to flip it.

    Requires `s` and `t` to be *closed* terms (no free variables) -- this
    is a deliberate scope restriction, not an oversight: it sidesteps
    variable capture entirely, since a closed term can be substituted
    anywhere, including inside a quantifier's body, with no risk of
    colliding with that quantifier's bound name. Equalities between two
    closed terms (specific constants established earlier in a proof, e.g.
    "2 + 2 = 4") are overwhelmingly the common case; an equality
    genuinely involving a variable is out of scope for this rule.

    Like PropositionalEquivalenceRule, requires at least one actual
    replacement to have happened -- citing this rule to "substitute" a
    formula into itself unchanged is `ReiterationRule`'s job, not this
    one's.
    """
    name = "Substitution"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2:
            return False
        eq, source = candidates
        if not isinstance(eq, fl.Equals):
            eq, source = source, eq
            if not isinstance(eq, fl.Equals):
                return False
        s, t = eq.left, eq.right
        if fl.term_free_variables(s) or fl.term_free_variables(t):
            return False
        return (_formula_obtainable_by_replacing(source, s, t, phi) is True or
                _formula_obtainable_by_replacing(source, t, s, phi) is True)


class SymmetryRule(InferenceRule):
    """From `a = b`, infer `b = a` directly, in one step -- derivable from
    Reflexivity + Substitution (substitute into an instance of `a = a`),
    but implemented directly since re-deriving it at every use would make
    routine equality reasoning unbearably verbose.
    """
    name = "Symmetry"
    premise_arity = 1

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 1 or not isinstance(candidates[0], fl.Equals):
            return False
        if not isinstance(phi, fl.Equals):
            return False
        return _ast_eq(candidates[0].left, phi.right) and _ast_eq(candidates[0].right, phi.left)


class TransitivityRule(InferenceRule):
    """From `a = b` and `b = c`, infer `a = c` directly, in one step --
    again derivable from Substitution alone, implemented directly for the
    same reason as SymmetryRule. Both citation orders are accepted,
    matching every other two-premise rule in this module.
    """
    name = "Transitivity"
    premise_arity = 2

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if len(candidates) != 2:
            return False
        c1, c2 = candidates
        if not (isinstance(c1, fl.Equals) and isinstance(c2, fl.Equals)):
            return False
        if not isinstance(phi, fl.Equals):
            return False
        for first, second in ((c1, c2), (c2, c1)):
            if _ast_eq(first.right, second.left) and _ast_eq(phi.left, first.left) and _ast_eq(phi.right, second.right):
                return True
        return False


class AlgebraRule(InferenceRule):
    """``(algebra from L1, L2, ...)``: automatically finds a chain of
    Reflexivity/Symmetry/Transitivity/congruence steps connecting the
    cited equations to the claimed one, so a step like ``f(z) = y`` from
    ``y = f(z)`` doesn't require citing ``(Symmetry from ...)`` by name --
    or, for a longer chain, manually working out and citing each
    intermediate equation.

    -----------------------------------------------------------------
    Why this doesn't reopen the soundness gap "Algebra" was retired for
    -----------------------------------------------------------------
    The original "Algebra" (see the retirement note this replaces, in
    NumberTheory.py's module docstring) accepted *any* citation under
    that name -- there was no mechanism behind it at all, so it could
    only be sound by accident, or by silently rubber-stamping whatever
    the proof claimed. This one is a real decision procedure with no
    trust-me step: it only ever accepts `phi` when it can actually
    construct the chain, out of primitives that are independently sound
    on their own --

        this rule's guarantee = closure of {Reflexivity, Symmetry,
        Transitivity, congruence (i.e. Substitution restricted to
        replacing a subterm with something already proven equal to it)}
        under the cited equations

    -- the same primitives SymmetryRule and TransitivityRule are already
    justified by (see their docstrings: both are "derivable from
    Reflexivity + Substitution, implemented directly since re-deriving
    it at every use would make routine equality reasoning unbearably
    verbose"). This rule is that same convenience argument, generalized
    from one fixed step to a *searched* chain of them: every accepted
    case is one a sufficiently patient proof-writer could have
    justified with SymmetryRule/TransitivityRule/Substitution citations
    alone, just without having to work out and write down the
    intermediate equations by hand. Concretely, this is the classic
    *congruence closure* algorithm (union-find over subterms, merging
    two applications of the same function once their arguments are
    already merged, to a fixed point) -- a well-known, complete decision
    procedure for exactly this fragment (ground equalities over
    uninterpreted function symbols), not a bespoke, unaudited heuristic.

    -----------------------------------------------------------------
    What this covers, and what it deliberately doesn't yet
    -----------------------------------------------------------------
    In scope: pure equational reasoning -- reflexivity, symmetry,
    transitivity, and substitution of equals for equals at any depth
    (e.g. `a = b` lets `g(f(a), c)` and `g(f(b), c)` be recognized as
    equal). This is enough for definitional bookkeeping like `y = f(z),
    therefore f(z) = y`, or longer chains of renamings and substitutions,
    entirely domain-independently -- it works the same whether the terms
    involved are sets, numbers, or poset elements, because it never
    looks at what any function or constant symbol *means*, only at where
    the same symbol occurs.

    Out of scope, deliberately: any step whose validity depends on what
    an operation *means* rather than just which terms are which -- e.g.
    `2*x + 3*x = 5*x` needs distributivity, `a + b = b + a` needs
    commutativity. Nothing here knows those hold for `+`/`*`; treating
    them as true unconditionally would silently make this rule sound for
    number theory and unsound the moment some other domain reuses `+`/`*`
    without meaning a commutative ring by them. The extension point for
    this is by design the same one theory modules already use for
    everything else: a domain module (NumberTheory, say) would register
    its own ring axioms as additional *cited* equations available to
    reason from -- i.e. `a + b = b + a` becomes something citable by
    label (an axiom instance, established once, like `NAT_TYPE`'s
    axioms), not something this rule assumes -- so this same congruence
    closure procedure gets to use it once cited, without this rule
    itself ever hardcoding a single arithmetic fact. That module-level
    axiom work is future, separate, and deliberately not attempted here.

    -----------------------------------------------------------------
    Why `variable_arity`, not a fixed `premise_arity`
    -----------------------------------------------------------------
    A citation might resolve to one equation, or, through a bundled
    label (`ProofParser.try_elaborate_existence`'s "Define ... (Existence
    from ...)" is the running example -- see there), several -- and
    which of those actually matter for a given `phi` depends on `phi`,
    not on anything decidable from the citation text alone. See
    `Proof._validate_rule`'s `variable_arity` handling for the mechanics
    (every arity from all-of-what's-cited down to one is tried); this
    rule is the reason that branch exists.

    -----------------------------------------------------------------
    Worked example
    -----------------------------------------------------------------
    Cited: `y = f(z)`.  Claimed: `f(z) = y`.
    Union `y` and `f(z)`'s equivalence classes (from the cited
    equation) -> already in the same class -> accepted, in one
    `applies` call, with no intermediate `(Symmetry from ...)` line
    ever having to be written.
    """
    name = "Algebra"
    variable_arity = True

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        if not isinstance(phi, fl.Equals):
            return False
        equations = []
        for c in candidates:
            if not isinstance(c, fl.Equals):
                return False
            equations.append((c.left, c.right))
        return _congruence_closure_equates(equations, phi.left, phi.right)


def _term_key(term: tl.Term):
    """A hashable, structurally-faithful key for a Term -- `_ast_eq` is
    used everywhere else in this module instead of relying on `==`/`hash`
    directly for exactly the reason this function has to exist here too.
    """
    if isinstance(term, tl.FunctionTerm):
        return ('func', term.symbol, tuple(_term_key(a) for a in term.args))
    if isinstance(term, tl.VariableTerm):
        return ('var', term.name)
    if isinstance(term, tl.ConstantTerm):
        return ('const', term.name)
    return ('other', repr(term))


def _all_subterms(term: tl.Term):
    yield term
    if isinstance(term, tl.FunctionTerm):
        for arg in term.args:
            yield from _all_subterms(arg)


class _UnionFind:
    """Minimal union-find (disjoint-set) over `_term_key`-produced keys,
    with path compression but no union-by-rank -- the term sets involved
    in a single proof step are small enough (a handful of subterms) that
    the extra bookkeeping wouldn't pay for itself.
    """
    def __init__(self):
        self._parent: Dict[Any, Any] = {}

    def find(self, x):
        self._parent.setdefault(x, x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[rx] = ry


def _congruence_closure_equates(equations: List[Tuple[tl.Term, tl.Term]], p: tl.Term, q: tl.Term) -> bool:
    """The decision procedure `AlgebraRule` is built on: true exactly
    when `p = q` follows from `equations` via reflexivity, symmetry,
    transitivity, and congruence (substituting a subterm with something
    already proven equal to it) -- see `AlgebraRule`'s docstring for why
    that's the right (and sound) fragment for this rule to decide.
    """
    uf = _UnionFind()
    terms_by_key: Dict[Any, tl.Term] = {}

    def register(term: tl.Term) -> None:
        for sub in _all_subterms(term):
            key = _term_key(sub)
            terms_by_key.setdefault(key, sub)
            uf.find(key)

    for left, right in equations:
        register(left)
        register(right)
    register(p)
    register(q)

    for left, right in equations:
        uf.union(_term_key(left), _term_key(right))

    changed = True
    while changed:
        changed = False
        func_terms = [t for t in terms_by_key.values() if isinstance(t, tl.FunctionTerm)]
        for i, t1 in enumerate(func_terms):
            for t2 in func_terms[i + 1:]:
                if t1.symbol != t2.symbol or len(t1.args) != len(t2.args):
                    continue
                k1, k2 = _term_key(t1), _term_key(t2)
                if uf.find(k1) == uf.find(k2):
                    continue
                if all(uf.find(_term_key(a)) == uf.find(_term_key(b)) for a, b in zip(t1.args, t2.args)):
                    uf.union(k1, k2)
                    changed = True

    return uf.find(_term_key(p)) == uf.find(_term_key(q))


# ==========================================================================
# SECTION 6.6 -- Axiom schemas
# ==========================================================================
#
# An axiom schema (induction; later, ZFC's Separation/Replacement) isn't
# checked against one fixed formula -- it's parameterized by an arbitrary
# formula the proof-writer chooses implicitly, by what they write for phi
# and the cited candidates. AxiomSchemaRule factors out the shared part
# (compare candidates against formulas derived from phi) so each concrete
# schema only has to implement how to derive them.

class AxiomSchemaRule(InferenceRule):
    """Base for rules whose citation is checked against formulas *derived*
    from the proposed conclusion, rather than a fixed formula compared
    verbatim. Subclasses implement `_expected(phi, candidates)`: return
    None if `phi` isn't even shaped like an instance of this schema, or
    the list of formulas each candidate must `_ast_eq`-match, in citation
    order, if it is. `candidates` is passed (not just `phi`) because
    constructing the comparison target sometimes has to honor a bound
    variable name the proof-writer chose in a candidate -- see
    InductionRule, which needs exactly this.

    Override `_extra_conditions` for a schema with side conditions beyond
    candidate-matching (e.g. a freshness requirement).
    """
    def _expected(self, phi: fl.Formula, candidates: List[fl.Formula]) -> Optional[List[fl.Formula]]:
        raise NotImplementedError

    def _extra_conditions(self, phi: fl.Formula, candidates: List[fl.Formula]) -> bool:
        return True

    def applies(self, candidates: List[fl.Formula], phi: fl.Formula) -> bool:
        expected = self._expected(phi, candidates)
        if expected is None or len(candidates) != len(expected):
            return False
        if not all(_ast_eq(c, e) for c, e in zip(candidates, expected)):
            return False
        return self._extra_conditions(phi, candidates)


class InductionRule(AxiomSchemaRule):
    """Peano-style induction over a single inductively-generated type: one
    base constructor (`zero_term`) and one unary constructor
    (`succ_symbol`), with `type_predicate` the unary predicate
    characterizing membership (e.g. 'Nat'). A citation looks like:

        1. P(Zero). (...)
        2. forall n, ((Nat(n) and P(n)) -> P(Succ(n))). (...)
        3. forall x, (Nat(x) -> P(x)). (Induction from 1, 2)

    `P` is never named explicitly -- it's read directly off `phi` (line 3
    above: strip the `Nat(x) ->` guard and `P(x)` is what's left), and
    `_expected` reconstructs exactly what lines 1 and 2 must say using
    `FormulaLogic.substitute_in_formula`, the same primitive
    `_equivalent_by_substitution` already relies on elsewhere.

    The step formula's bound variable name is read off the *cited*
    candidate rather than invented by this rule -- `_ast_eq` requires
    literal name equality on `ForAll`, so a proof that names its induction
    variable `n` (or anything else) must be compared against a formula
    built using that same name, not a name this rule happens to pick.

    Scoped deliberately to this single-successor shape: a future
    inductively-defined type with more than one constructor (e.g. a tree
    type with a nullary leaf and a binary node) needs its own
    AxiomSchemaRule subclass with its own `_expected`, not a generalized
    version of this one.
    """
    name = "Induction"
    premise_arity = 2

    def __init__(self, type_predicate: str, zero_term: tl.Term, succ_symbol: str):
        self.type_predicate = type_predicate
        self.zero_term = zero_term
        self.succ_symbol = succ_symbol

    def _guarded(self, atom: fl.Formula, var_name: str) -> bool:
        return (isinstance(atom, fl.AtomicFormula) and atom.predicate == self.type_predicate
                and len(atom.args) == 1 and isinstance(atom.args[0], tl.VariableTerm)
                and atom.args[0].name == var_name)

    def _expected(self, phi: fl.Formula, candidates: List[fl.Formula]) -> Optional[List[fl.Formula]]:
        if not isinstance(phi, fl.ForAll) or not isinstance(phi.body, fl.Implies):
            return None
        x_name = phi.var
        if not self._guarded(phi.body.antecedent, x_name):
            return None
        Q = phi.body.consequent

        base = fl.substitute_in_formula(Q, x_name, self.zero_term)

        step_candidate = candidates[1] if len(candidates) > 1 else None
        n_name = step_candidate.var if isinstance(step_candidate, fl.ForAll) else x_name

        step = fl.ForAll(n_name, fl.Implies(
            fl.And(fl.AtomicFormula(self.type_predicate, [tl.VariableTerm(n_name)]),
                   fl.substitute_in_formula(Q, x_name, tl.VariableTerm(n_name))),
            fl.substitute_in_formula(Q, x_name, tl.FunctionTerm(self.succ_symbol, [tl.VariableTerm(n_name)])),
        ))
        return [base, step]


class ConstantGeneralizingMatcher:
    """Like `FormulaMatcher`, but generalizes over a *set* of free constant
    names at once instead of one quantifier-bound variable.

    A theorem proven "for any set X" states X as a declared object, not a
    bound variable -- `Let X be any set.` parses to `ConstantTerm('X', 'X')`,
    the same as any other constant, and the theorem's own conclusion
    formula simply mentions that constant freely (see `basicSTProofs.txt`
    proof #1: its conclusion is `forall x, (In(x, EmptySet) -> In(x, X))`,
    with "X" free and "x" bound). Citing that theorem again later for a
    *different* set needs to recover what term should stand in for "X" --
    structurally the same recovery `FormulaMatcher` does for a bound
    variable, just keyed on a constant's name rather than a `VariableTerm`.

    Construct with the set of names to generalize (`{"X"}`), then call
    `match_formula`/`match_term` once; on success, `.mapping` holds what
    each generalized name matched to. See `TheoremRule` for how this is
    used to promote a proved theorem into a citable rule.
    """
    __slots__ = ("names", "mapping")

    def __init__(self, names):
        self.names = set(names)
        self.mapping: Dict[str, tl.Term] = {}

    def match_term(self, pattern: tl.Term, target: tl.Term) -> bool:
        if isinstance(pattern, tl.ConstantTerm) and pattern.name in self.names:
            if pattern.name not in self.mapping:
                self.mapping[pattern.name] = target
                return True
            return _ast_eq(self.mapping[pattern.name], target)

        if isinstance(pattern, tl.VariableTerm):
            return isinstance(target, tl.VariableTerm) and pattern.name == target.name
        if isinstance(pattern, tl.ConstantTerm):
            return isinstance(target, tl.ConstantTerm) and pattern.name == target.name
        if isinstance(pattern, tl.FunctionTerm):
            if not isinstance(target, tl.FunctionTerm): return False
            if pattern.symbol != target.symbol or len(pattern.args) != len(target.args): return False
            return all(self.match_term(pa, ta) for pa, ta in zip(pattern.args, target.args))
        return False

    def match_formula(self, pattern: fl.Formula, target: fl.Formula) -> bool:
        if type(pattern) != type(target):
            return False

        if isinstance(pattern, fl.AtomicFormula):
            if pattern.predicate != target.predicate or len(pattern.args) != len(target.args): return False
            for pa, ta in zip(pattern.args, target.args):
                if isinstance(pa, tl.Term) and isinstance(ta, tl.Term):
                    if not self.match_term(pa, ta): return False
                else:
                    if not _ast_eq(pa, ta): return False
            return True
        if isinstance(pattern, fl.And):
            if len(pattern.conjuncts) != len(target.conjuncts): return False
            return all(self.match_formula(p, t) for p, t in zip(pattern.conjuncts, target.conjuncts))
        if isinstance(pattern, fl.Or):
            if len(pattern.disjuncts) != len(target.disjuncts): return False
            return all(self.match_formula(p, t) for p, t in zip(pattern.disjuncts, target.disjuncts))
        if isinstance(pattern, fl.Not):
            return self.match_formula(pattern.sub, target.sub)
        if isinstance(pattern, fl.Implies):
            return self.match_formula(pattern.antecedent, target.antecedent) and self.match_formula(pattern.consequent, target.consequent)
        if isinstance(pattern, fl.Iff):
            return self.match_formula(pattern.left, target.left) and self.match_formula(pattern.right, target.right)
        if isinstance(pattern, fl.Equals):
            return self.match_term(pattern.left, target.left) and self.match_term(pattern.right, target.right)
        if isinstance(pattern, (fl.ForAll, fl.Exists)):
            # A generalized name is a free constant, never a bound variable
            # name, so -- unlike FormulaMatcher -- there is no shadowing
            # case to guard against here; both sides just need the same
            # bound name, exactly as plain _ast_eq requires.
            if pattern.var != target.var: return False
            return self.match_formula(pattern.body, target.body)
        return False


def _substitute_constants_in_term(term: tl.Term, mapping: Dict[str, tl.Term]) -> tl.Term:
    """Term-level counterpart of `FormulaLogic.substitute_in_term`, keyed
    on constant names rather than a single variable name -- replace every
    `ConstantTerm` whose name is a key of `mapping` with the corresponding
    term, recursively.
    """
    if isinstance(term, tl.ConstantTerm):
        return mapping.get(term.name, term)
    if isinstance(term, tl.FunctionTerm):
        return tl.FunctionTerm(term.symbol, [_substitute_constants_in_term(a, mapping) for a in term.args])
    return term


def _substitute_constants_in_formula(formula: fl.Formula, mapping: Dict[str, tl.Term]) -> fl.Formula:
    """Formula-level counterpart of `_substitute_constants_in_term`."""
    if isinstance(formula, fl.AtomicFormula):
        return fl.AtomicFormula(formula.predicate, [
            _substitute_constants_in_term(a, mapping) if isinstance(a, tl.Term) else a for a in formula.args
        ])
    if isinstance(formula, fl.And):
        return fl.And(*[_substitute_constants_in_formula(c, mapping) for c in formula.conjuncts])
    if isinstance(formula, fl.Or):
        return fl.Or(*[_substitute_constants_in_formula(d, mapping) for d in formula.disjuncts])
    if isinstance(formula, fl.Not):
        return fl.Not(_substitute_constants_in_formula(formula.sub, mapping))
    if isinstance(formula, fl.Implies):
        return fl.Implies(_substitute_constants_in_formula(formula.antecedent, mapping),
                           _substitute_constants_in_formula(formula.consequent, mapping))
    if isinstance(formula, fl.Iff):
        return fl.Iff(_substitute_constants_in_formula(formula.left, mapping),
                       _substitute_constants_in_formula(formula.right, mapping))
    if isinstance(formula, fl.Equals):
        return fl.Equals(_substitute_constants_in_term(formula.left, mapping),
                          _substitute_constants_in_term(formula.right, mapping))
    if isinstance(formula, fl.ForAll):
        return fl.ForAll(formula.var, _substitute_constants_in_formula(formula.body, mapping))
    if isinstance(formula, fl.Exists):
        return fl.Exists(formula.var, _substitute_constants_in_formula(formula.body, mapping))
    return formula


class TheoremRule(AxiomSchemaRule):
    """A proved theorem, packaged as a rule later proofs can cite by name
    -- the "proofs create new inference rules" half of the project: once
    `A -> B` has been proved for an arbitrary `X`, later proofs shouldn't
    have to re-derive it, only cite it, the same way a published theorem
    works in ordinary mathematical practice.

    `conclusion` and `premises` are the theorem's own conclusion and
    premises, exactly as it proved them (mentioning whatever objects it
    generalized over -- e.g. `X` -- as ordinary free constants).
    `generalized_names` lists which of those constants a later citation is
    free to instantiate differently (typically: whatever the theorem's own
    top-level declarations introduced as "any" object, e.g. `Let X be any
    set.`). Anything the theorem's conclusion/premises mention that is
    *not* in `generalized_names` is treated as fixed -- a citation must
    match it exactly, the same way `EmptySet` in this example is not
    generalized: this theorem was proved about *the* empty set specifically,
    not about an arbitrary one.

    Citing it works like any other rule: cite zero or more earlier lines
    (matching `len(premises)`) and this theorem's own name as the rule.
    `applies` recovers a single consistent substitution for every
    generalized name from `phi` against `conclusion` alone, then requires
    that same substitution to turn `premises` into exactly what was cited
    -- so a theorem with premises can still only be invoked where those
    premises genuinely hold, not merely where the conclusion's shape
    matches.

    Example -- `basicSTProofs.txt`'s two proofs, the second citing the
    first by name with no premises at all (the theorem has none)::

        # 1: The empty set subset theorem
        1. Let X be any set. (Declaration)
        2. The empty set is a subset of X. (Subset proof below)
        ...
        # 2
        ...
         1.3. The empty set is a subset of X. (The empty set subset theorem)

    `promote_theorem` builds the `TheoremRule` for a case like this from
    an already-checked `Proof` plus the name of whichever top-level
    declared objects should generalize.
    """
    premise_arity = 0  # overwritten per instance in __init__

    def __init__(self, name: str, premises: List[fl.Formula], conclusion: fl.Formula,
                 generalized_names: List[str]):
        self.name = name
        self.premises = list(premises)
        self.conclusion = conclusion
        self.generalized_names = list(generalized_names)
        self.premise_arity = len(self.premises)

    def _expected(self, phi: fl.Formula, candidates: List[fl.Formula]) -> Optional[List[fl.Formula]]:
        matcher = ConstantGeneralizingMatcher(self.generalized_names)
        if not matcher.match_formula(self.conclusion, phi):
            return None
        return [_substitute_constants_in_formula(p, matcher.mapping) for p in self.premises]


def promote_theorem(name: str, proof: "Proof", generalized_names: Optional[List[str]] = None,
                     conclusion: Optional[fl.Formula] = None) -> TheoremRule:
    """Build a `TheoremRule` from an already-checked `Proof`.

    `proof` must validate (`proof.check()[0]` is True) -- promoting a
    proof that doesn't actually check would manufacture an inference rule
    out of nothing, exactly the soundness hole `VocabularyDeclaration`/
    `Declaration` were kept out of `Formula`'s class hierarchy to prevent
    for declarations; the same discipline applies here.

    `conclusion` defaults to the last top-level formula the proof actually
    *derived* (see `MultiproofParser._top_level_formulas`'s docstring for
    why "derived", not "premised", is the right notion); pass it
    explicitly for a proof whose intended theorem isn't simply its final
    line (e.g. one proving several things and stating the one that matters
    via a multi-proof file's `### then ...` line).

    `generalized_names` defaults to every symbol the proof's own top-level
    entries declare as an `OBJECT` (typically via `Let X be any ....`,
    outside of any subproof) -- the natural reading of "any X" in a
    theorem statement. Pass an explicit list to generalize over fewer
    names, or none at all for a theorem that isn't "for any X" but a
    single fixed fact.
    """
    ok, err = proof.check_detailed()
    if not ok:
        raise ValueError(f"cannot promote a proof that does not validate: {err}")

    if conclusion is None:
        derived = _top_level_derived_formulas(proof.entries)
        if not derived:
            raise ValueError("proof derives nothing at the top level to promote as a conclusion")
        conclusion = derived[-1]

    premises = _top_level_premise_formulas(proof.entries)

    if generalized_names is None:
        generalized_names = _top_level_object_declarations(proof.entries)

    return TheoremRule(name, premises, conclusion, generalized_names)


def _top_level_derived_formulas(entries: list) -> List[fl.Formula]:
    """Every formula a top-level (non-subproof) entry actually derived by
    inference, in order -- the same notion `MultiproofParser._top_level_formulas`
    uses, reimplemented here so `ProofLogic` doesn't depend on `MultiproofParser`
    (the dependency runs the other way already).
    """
    derived_tags = {'rule', 'rule_below', 'rule_hybrid'}
    result: List[fl.Formula] = []
    for e in entries:
        parsed = _classify_entry(e)
        if isinstance(parsed, str) or parsed.is_subproof_block:
            continue
        justification = parsed.justification
        if not isinstance(justification, tuple) or not justification or justification[0] not in derived_tags:
            continue
        phi = parsed.phi
        if isinstance(phi, list):
            result.extend(f for f in phi if isinstance(f, fl.Formula))
        elif isinstance(phi, fl.Formula):
            result.append(phi)
    return result


def _top_level_premise_formulas(entries: list) -> List[fl.Formula]:
    """Every formula a top-level `'premise'`-tagged entry asserts, in
    order -- what a promoted theorem needs a later citation to still
    supply.
    """
    result: List[fl.Formula] = []
    for e in entries:
        parsed = _classify_entry(e)
        if isinstance(parsed, str) or parsed.is_subproof_block:
            continue
        justification = parsed.justification
        tag = justification[0] if isinstance(justification, tuple) and justification else None
        if tag != 'premise':
            continue
        phi = parsed.phi
        if isinstance(phi, list):
            result.extend(f for f in phi if isinstance(f, fl.Formula))
        elif isinstance(phi, fl.Formula):
            result.append(phi)
    return result


def _top_level_object_declarations(entries: list) -> List[str]:
    """Names of every `OBJECT`-kind symbol declared by a top-level entry
    (an explicit `('declare', [...])` list, or a `Let X be any set.`
    premise-declaration-prefix) -- the default set of names a promoted
    theorem generalizes over. Declarations made *inside* a subproof are
    excluded: those were scoped to an argument within the proof, not
    stated as "for any X" about the theorem itself.
    """
    names: List[str] = []
    for e in entries:
        parsed = _classify_entry(e)
        if isinstance(parsed, str) or parsed.is_subproof_block:
            continue
        justification = parsed.justification
        if isinstance(justification, tuple) and len(justification) >= 2 and isinstance(justification[1], list):
            names.extend(d.name for d in justification[1] if d.kind == DeclarationKind.OBJECT)
    return names

class DeclarationRecipe:
    """A theory-registered recipe for what a `Let ...` declaration of a
    given structure type should *also* produce, beyond the bare symbol
    declaration(s) a plain object gets -- the parametrized generalization
    of `Type`, needed because not every type is a single, fixed, global
    structure the way `Nat` is. `Nat`'s axioms and `InductionRule` are
    genuinely the same for every proof that uses them, so `Type` making
    them fixed, computed once at import time, is exactly right for that
    case -- but a poset's carrier and relation are named fresh by each
    proof that declares one, so there's no fixed pair of symbols for a
    `Type` to hold axioms about in advance. This is that missing piece:
    a recipe computed from the *actual* symbol name(s) one specific
    declaration uses, at the moment it's elaborated.

    See `Type.as_declaration_recipe` for the common case (a type whose
    declared instances should simply satisfy `Type.holds`) and
    `OrderTheory.py`'s well-ordered-poset recipe for the fuller case
    (new relation/function symbols, and a rule parametrized to them, not
    just one new fact about one already-declared-shape object).

    `try_match(clauses, start)`: given the full list of
    `ProofParser.DeclarationClause`s on a `Let ...` line and a starting
    index, either returns `None` (this recipe doesn't recognize the
    clause(s) starting there) or `(consumed, extra_declarations,
    extra_formulas, extra_rules)`: `consumed` is how many clauses
    starting at `start` this recipe used (1 for a single-clause type like
    Nat; 2 for "well-ordered poset" followed by its increasing-function
    clause); the rest mirror what a `line_elaborator` returns for the
    corresponding pieces.

    Multi-clause recipes exist (rather than requiring every recipe to be
    single-clause and self-contained) because some relationships are
    genuinely not decidable from one clause alone -- "increasing" doesn't
    mean anything without a specific order relation in view, and that
    relation is named in the *other* clause, not this one. Forcing every
    recipe to be single-clause would mean either guessing which earlier
    relation symbol was "the" one meant (fragile, implicit) or requiring
    proofs to spell out "increasing with respect to <" by hand every time
    (exactly the convolutedness this whole mechanism exists to avoid) --
    so a recipe owning a short, fixed-shape run of clauses it recognizes
    together is the honest option, not a shortcut.
    """
    def __init__(self, name: str, try_match):
        self.name = name
        self.try_match = try_match


class Type:
    """A named domain/theory package.

    The original four constructor arguments remain valid. `declarations`
    supplies theory-level vocabulary such as Nat, Zero, and Succ.

    `descriptors` (new, optional): English `Let x be a/an <descriptor>`
    phrases (matched case-insensitively) that should make `x`
    automatically satisfy `self.holds(x)` the moment it's declared --
    e.g. `["natural number", "natural numbers"]` for `Nat`. A `Type`
    passing no `descriptors` behaves exactly as before: global
    axioms/vocabulary only, no automatic per-declaration fact. See
    `as_declaration_recipe`, and `DeclarationRecipe`'s docstring for why
    this exists as its own mechanism alongside `axioms`/`schema_rules`
    rather than folded into them.
    """

    def __init__(self, name: str, predicate: str, axioms: List[fl.Formula],
                 schema_rules: List[InferenceRule],
                 declarations: Optional[List[Declaration]] = None,
                 descriptors: Optional[List[str]] = None):
        self.name = name
        self.predicate = predicate
        self.axioms = list(axioms)
        self.schema_rules = list(schema_rules)
        self.declarations = list(declarations or [])
        self.descriptors = [d.lower() for d in (descriptors or [])]

    def holds(self, term: tl.Term) -> fl.Formula:
        return fl.AtomicFormula(self.predicate, [term])

    def as_declaration_recipe(self) -> DeclarationRecipe:
        """The `DeclarationRecipe` that makes `Let x be a <descriptor>`
        (for each of `self.descriptors`) also assert `self.holds(x)` as
        a citable fact at that declaration's own label -- the single-
        clause, "just one new fact about an otherwise-ordinary object"
        case of the mechanism `DeclarationRecipe` describes. A `Type`
        with no `descriptors` gets a recipe that never matches, so
        registering it is always safe.
        """
        def try_match(clauses, start):
            if not self.descriptors:
                return None
            dc = clauses[start]
            if dc.domain is not None:
                return None
            if dc.normalized_descriptor not in self.descriptors:
                return None
            declarations = [Declaration(name=name, kind=DeclarationKind.OBJECT, type_name=dc.descriptor.strip())
                             for name in dc.names]
            formulas = [self.holds(tl.ConstantTerm(name, name)) for name in dc.names]
            return (1, declarations, formulas, [])
        return DeclarationRecipe(self.name, try_match)


def combine_types(*types: Type) -> Tuple[List[fl.Formula], List[InferenceRule]]:
    """Merge theory axioms and schema rules; preserves the original API."""
    axioms = [ax for t in types for ax in t.axioms]
    schema_rules = [r for t in types for r in t.schema_rules]
    return axioms, schema_rules


def combine_type_declarations(*types: Type) -> List[Declaration]:
    """Merge vocabulary declarations supplied by one or more theories."""
    return _dedupe_declarations([d for t in types for d in t.declarations])


class NamedRulePlaceholder:
    """A stand-in for a rule cited by name only, to be resolved against
    whichever configured instance is actually registered for a given
    `Proof` at validation time.

    Every other rule ProofParser recognizes is stateless -- `ModusPonensRule()`
    means the same thing everywhere, so the parser can just construct one
    on the spot. `InductionRule`, though, needs per-proof configuration
    the text can't supply: citing "Induction" doesn't say *which* type's
    induction (Nat's `Zero`/`Succ`, or some other type defined later), and
    that configuration lives in whichever `Type` the proof was built with
    (e.g. `NatTheory.NAT_TYPE`), not in the justification text.

    ProofParser produces `NamedRulePlaceholder('Induction')` for such a
    citation; `ProofValidator._validate_rule` resolves it by looking up a
    registered rule with a matching `.name` before doing anything else
    (arity checking, `.applies()`) -- so from that point on, validation
    proceeds exactly as it would for any other rule. If no rule with that
    name is registered (e.g. the proof's `rules=` list doesn't include
    Nat's `InductionRule` because `NAT_TYPE` was never combined in), that
    resolution step is where the failure is reported.
    """
    def __init__(self, name: str):
        self.name = name


def default_rules() -> List[InferenceRule]:
    """The full set of inference rules `Proof` uses when none are given
    explicitly.

    Pulled out as its own function (rather than an inline list literal in
    `Proof.__init__`) so a restricted rule set can be built the same way
    the full one is -- e.g. a "propositional logic only" checker that
    excludes the quantifier rules:

        Proof(entries, rules=[r for r in default_rules()
                               if 'Universal' not in r.name and 'Existential' not in r.name])

    or simply by passing an explicit list of the desired rule instances.
    """
    return [
        ModusPonensRule(),
        ModusTollensRule(),
        HypotheticalSyllogismRule(),
        DisjunctiveSyllogismRule(),
        UniversalInstantiationRule(),
        UniversalGeneralizationRule(),
        ExistentialIntroductionRule(),
        ExistentialEliminationRule(),
        ConjunctionEliminationRule(),
        ConjunctionIntroductionRule(),
        DisjunctionIntroductionRule(),
        DisjunctionEliminationRule(),
        BiconditionalIntroductionRule(),
        BiconditionalEliminationRule(),
        ConditionalIntroductionRule(),
        ProofByContradictionRule(),
        ExplosionRule(),
        ReiterationRule(),
        PropositionalEquivalenceRule(),
        ReflexivityRule(),
        LeibnizSubstitutionRule(),
        SymmetryRule(),
        TransitivityRule(),
    ]


# ==========================================================================
# SECTION 7 -- The validator
# ==========================================================================

# ---- Failure categories -------------------------------------------------
# A small fixed vocabulary so calling code can branch on *kind* of failure
# (`err.category == CATEGORY_BAD_REFERENCE`) instead of parsing message
# text. The two that matter most for telling "what's wrong with this
# citation" apart are CATEGORY_BAD_REFERENCE (the cited label(s) don't
# resolve to anything in scope) and CATEGORY_RULE_MISMATCH (the cited
# label(s) resolve fine, but the rule doesn't actually license the
# conclusion from them) -- exactly the two situations that look identical
# from the outside ("this line doesn't follow") but need very different
# fixes (fix a typo'd label vs. fix which rule or which lines are cited).
CATEGORY_MALFORMED_ENTRY = "malformed_entry"                # not a recognized entry shape at all
CATEGORY_NOT_CLOSED = "not_closed"                          # formula has a free variable
CATEGORY_MALFORMED_JUSTIFICATION = "malformed_justification"  # justification tuple is the wrong shape
CATEGORY_UNKNOWN_TAG = "unknown_tag"                        # justification tag isn't any recognized kind
CATEGORY_WRONG_POSITION = "wrong_position"                  # 'assume'/'arbitrary' not at a subproof's first line
CATEGORY_BAD_OPENING = "bad_opening"                        # subproof's first line isn't an assumption/arbitrary at all
CATEGORY_EMPTY_SUBPROOF = "empty_subproof"                  # subproof has zero lines
CATEGORY_UNREGISTERED_FORMULA = "unregistered_formula"      # not in this proof's declared premises/axioms
CATEGORY_MISSING_SUBPROOF = "missing_subproof"              # 'rule_below' with no subproof actually below it
CATEGORY_UNRECOGNIZED_RULE = "unrecognized_rule"            # rule instance isn't part of this Proof's rule set
CATEGORY_ARITY_MISMATCH = "arity_mismatch"                  # wrong number of cited lines for this rule
CATEGORY_BAD_REFERENCE = "bad_reference"                    # cited label(s) don't resolve to anything in scope
CATEGORY_RULE_MISMATCH = "rule_mismatch"                    # cited lines resolve fine, but the rule rejects them
CATEGORY_RULE_RAISED = "rule_raised"                        # rule.applies() itself threw
CATEGORY_UNDECLARED_SYMBOL = "undeclared_symbol"      # symbol used without a visible declaration
CATEGORY_DECLARATION_CONFLICT = "declaration_conflict"  # duplicate/conflicting declaration
CATEGORY_DECLARATION_KIND_MISMATCH = "declaration_kind_mismatch"  # wrong symbol kind
CATEGORY_DECLARATION_ARITY_MISMATCH = "declaration_arity_mismatch"  # wrong function/predicate arity


class ValidationError(NamedTuple):
    """A single proof-validation failure: precisely where it happened,
    what kind of problem it was, and the specific explanation.

    `location` is always a complete, ready-to-print phrase -- `str(err)` is
    just `f"{err.location}: {err.detail}"` -- while `label` exposes the
    bare proof-file label (e.g. "11.2") on its own, for callers that want
    to look the offending line up directly (see
    `ProofParser.run_file`) rather than parse it back out of a sentence.

    `label` (and therefore a precise `location`) is available for
    essentially every real failure: any proof line produced by
    `ProofParser` has an explicit dotted label, whether it sits at the top
    level ("4") or inside a doubly-nested subproof ("11.2"). It's `None`
    only for a handful of failures that aren't about one specific labeled
    line -- an empty subproof, or a hand-built `entries` list that omits
    labels -- in which case `location` instead names the enclosing
    subproof ("the subproof at line 11") or "Root".

    `category` is one of the `CATEGORY_*` constants above. The two to
    know first: `CATEGORY_BAD_REFERENCE` means the citation points at a
    label that doesn't exist (or isn't in scope here); `CATEGORY_RULE_MISMATCH`
    means the citation resolved to real, in-scope lines, but the named
    rule doesn't actually license the conclusion from them. Distinguishing
    these is exactly "is this a typo'd line number, or the wrong rule/lines
    entirely?"
    """
    location: str
    label: Optional[str]
    category: str
    detail: str

    def __str__(self) -> str:
        return f"{self.location}: {self.detail}"


def _mk_error(entry_label: Optional[str], block_label: Optional[str], sidx: Optional[int],
              category: str, detail: str) -> ValidationError:
    """Build a `ValidationError`, preferring the failing entry's own
    proof-file label for `location` and falling back to a position
    relative to the enclosing block when there's no label to point to.

    In order of preference:
      1. `entry_label` given -- the common case for any text-parsed proof:
         `location = "Line 11.2"`.
      2. no label, but a position (`sidx`) within a block -- a hand-built,
         unlabeled entry: `location = "the unlabeled entry at position 2
         of the subproof at line 11"` (or "... of the top level" at Root).
      3. neither -- a whole-block failure with no single offending entry
         (only `empty subproof` reaches this): `location = "the subproof
         at line 11"` (or "Root").
    """
    if entry_label is not None:
        return ValidationError(location=f"Line {entry_label}", label=entry_label, category=category, detail=detail)

    where = f"the subproof at line {block_label}" if block_label is not None else "the top level"
    if sidx is not None:
        return ValidationError(location=f"the unlabeled entry at position {sidx} of {where}", label=None, category=category, detail=detail)

    where_block = f"the subproof at line {block_label}" if block_label is not None else "Root"
    return ValidationError(location=where_block, label=block_label, category=category, detail=detail)


class _ParsedEntry(NamedTuple):
    """One proof-file entry, normalized to a single shape regardless of
    which of ProofParser's five raw tuple forms produced it (see the
    module docstring's "entries mini-language" section).

    A plain `NamedTuple` rather than a small class: it's pure data handed
    from `_classify_entry` to `_validate_block` and read immediately, never
    mutated or stored, so a tuple's lower per-instance memory footprint
    (no per-instance `__dict__`) costs nothing here.

    `is_subproof_block` distinguishes the two kinds of subproof an entry
    can carry:
      * True  -- a *standalone* subproof, validated and then filed away
                 under `label` purely so a later line can cite it (this is
                 how DisjunctionEliminationRule and
                 ExistentialEliminationRule receive their subproof
                 premises). `subproof_entries` holds its body;
                 `phi`/`justification`/`nested_subproof` are all None.
      * False -- an ordinary formula line. It may itself carry a
                 `nested_subproof` when its `justification` is a
                 'rule_below' rule (ConditionalIntroductionRule,
                 ProofByContradictionRule, UniversalGeneralizationRule).
    """
    label: Optional[str]
    is_subproof_block: bool
    subproof_entries: Optional[list]
    phi: Optional[Any]
    justification: Optional[tuple]
    nested_subproof: Optional[list]


def _classify_entry(e: Any) -> Union[_ParsedEntry, str]:
    """Normalize one raw entry tuple from ProofParser into a `_ParsedEntry`.

    Returns the normalized entry on success, or a plain error string (with
    no location information attached -- `_validate_block` wraps it into a
    located `ValidationError` via `_mk_error`) if `e` isn't a recognized
    shape. This is the single place that needs to know about all five raw
    tuple forms ProofParser can produce, so the rest of the validator can
    work in terms of one shape.

    The check order matters and is preserved from the original inline
    version: a 3-tuple is checked for "is this actually a labeled
    standalone subproof block" (`e[1] == 'subproof'`) *before* being
    treated as an ordinary `(label, phi, justification)` line, and likewise
    a 2-tuple is checked for the unlabeled subproof-block form
    (`e[0] == 'subproof'`) before being treated as `(phi, justification)`.
    A formula that happened to be the literal string `'subproof'` in the
    wrong position could in principle confuse this sniffing -- there's no
    tag byte distinguishing "this tuple is a subproof block" from "this
    tuple is a two-element normal entry whose first element is the string
    'subproof'" other than shape plus a literal string match. In practice
    ProofParser never emits a formula as a bare Python string, only as a
    parsed `Formula` object, so this ambiguity is not currently reachable
    from proof text -- but it is a sharp edge for anyone constructing
    `entries` by hand rather than through `ProofParser.parse_proof_text`.
    """
    if not isinstance(e, tuple):
        return "invalid entry format"

    if len(e) == 3 and e[1] == 'subproof':
        label, _, subentries = e
        return _ParsedEntry(label, True, subentries, None, None, None)
    if len(e) == 2 and e[0] == 'subproof':
        _, subentries = e
        return _ParsedEntry(None, True, subentries, None, None, None)
    if len(e) == 2:
        phi, justification = e
        return _ParsedEntry(None, False, None, phi, justification, None)
    if len(e) == 3:
        label, phi, justification = e
        return _ParsedEntry(label, False, None, phi, justification, None)
    if len(e) == 4:
        label, phi, justification, nested_subproof = e
        return _ParsedEntry(label, False, None, phi, justification, nested_subproof)

    return "invalid entry shape"


class ProofValidator:
    """Walks a list of proof entries and checks that every line is
    justified: a premise or axiom that's actually in scope, an assumption
    or arbitrary-constant flag opening a subproof, or the sound conclusion
    of some `InferenceRule` applied to already-justified earlier lines.

    `validate` is the only public entry point; everything else is a
    private helper decomposing the walk into one method per concern:

        validate                       top-level entry point
        _validate_block                 one block (Root, or one subproof):
                                         empty/first-line checks, then loops
                                         entries
        _check_opens_with_assumption    "does this subproof legally open?"
        _validate_line                  one non-subproof-block entry: closed
                                         check, justification shape, then
                                         dispatches by tag
        _validate_assume_or_arbitrary   tag: 'assume' / 'arbitrary'
        _validate_membership            tag: 'premise' / 'axiom'
        _validate_rule_below            tag: 'rule_below'
        _validate_rule                  tag: 'rule'
        _rule_is_registered              shared "is this rule instance one
                                         of the ones this Proof allows?"
                                         check

    Every one of the five per-tag branches ends the same way on success --
    append `phi` to `seen`, and if the line has a `label`, register it in
    `labels` -- so that "commit" step is written once, in `_validate_line`,
    instead of being repeated at the end of every branch.

    Validation always proceeds top to bottom (depth-first through
    subproofs) and returns on the *first* entry that fails, so whatever
    `ValidationError` comes back always describes the first line that
    doesn't follow from what came before it -- including inside a
    subproof: a subproof's own entries are fully validated (and can fail)
    before the line that cites the subproof is ever checked, exactly
    matching the order a person reading the proof top to bottom would hit
    problems in.

    Every error's `location` is built from the *proof's own* line label
    (see `ValidationError`, `_mk_error`) -- e.g. "Line 11.2" for the third
    line of the subproof opened at label "11" -- rather than an internal,
    0-based position within whichever Python list happens to be holding
    that block's entries. `block_label` (threaded through every recursive
    call in place of an earlier internal-only block name) is what makes
    this possible: it's the proof-file label associated with whichever
    subproof is currently being validated (see `_validate_block`'s
    docstring for exactly how it's derived for each of the two ways a
    subproof can be opened).
    """
    def __init__(self, rules, premises, axioms,
                 declarations: Optional[List[Declaration]] = None):
        self.rules = rules
        self.premises = premises
        self.axioms = axioms
        self.initial_declarations = list(declarations or [])

    def validate(self, entries: list) -> Tuple[bool, Optional[ValidationError], Optional[SubproofRecord]]:
        seen: list = []
        labels = LabelScope()
        declarations = DeclarationScope(initial=self.initial_declarations)
        return self._validate_block(entries, None, seen, labels, declarations, outer_context=seen)

    def _validate_block(self, block_entries: list, block_label: Optional[str], seen: list, labels: LabelScope,
                        declarations: DeclarationScope, outer_context: list,
                        is_subproof: bool = False) -> Tuple[bool, Optional[ValidationError], Optional[SubproofRecord]]:
        """Validate one block of entries -- either the proof's top level
        (`block_label=None`) or the body of one subproof -- appending each
        justified formula (or nested SubproofRecord) to `seen` and each
        labeled one to `labels` as it goes.

        `block_label` identifies *this* block for error-location purposes
        when an entry inside it has no label of its own to report (see
        `_mk_error`). It is derived differently depending on how the
        subproof was entered, by whichever caller recurses into this
        method:
          * a standalone subproof block (`(label, 'subproof', [...])`) --
            the subproof's own label, e.g. "11" for `11. begin subproof`.
          * a `rule_below` inline subproof -- the label of the line whose
            justification opened it, e.g. "2" for a conclusion justified
            by "... from subproof below" on line 2 (there's no separate
            label for the subproof itself in this form).

        `outer_context` is the *enclosing* block's own `seen` list (for the
        Root block, that's `seen` itself); it is threaded through unchanged
        so that a SubproofRecord built at the end of this call can record
        where its own outer context boundary sits, without copying it (see
        SubproofRecord's docstring).
        """
        if not block_entries:
            detail = "subproof has no lines" if is_subproof else "proof has no lines"
            return False, _mk_error(None, block_label, None, CATEGORY_EMPTY_SUBPROOF, detail), None

        if is_subproof:
            opening_detail, opening_label = self._check_opens_with_assumption(block_entries[0])
            if opening_detail:
                return False, _mk_error(opening_label, block_label, 0, CATEGORY_BAD_OPENING, opening_detail), None

        for sidx, e in enumerate(block_entries):
            entry = _classify_entry(e)
            if isinstance(entry, str):
                return False, _mk_error(None, block_label, sidx, CATEGORY_MALFORMED_ENTRY, entry), None

            if entry.is_subproof_block:
                ok, err, sp_rec = self._validate_block(
                    entry.subproof_entries, entry.label,
                    [], labels.child(), declarations.child(), seen, is_subproof=True,
                )
                if not ok:
                    return False, err, None
                seen.append(sp_rec)
                if entry.label:
                    labels[entry.label] = sp_rec
                continue

            err = self._validate_line(entry, sidx, block_label, is_subproof, seen, labels, declarations, outer_context)
            if err:
                return False, err, None

        if is_subproof:
            boundary = len(outer_context) if outer_context else 0
            return True, None, SubproofRecord(seen[0], seen, outer_context_ref=outer_context, boundary_index=boundary)

        return True, None, None

    def _check_opens_with_assumption(self, first_entry: Any) -> Tuple[Optional[str], Optional[str]]:
        """A subproof must open with an assumption ("... (Assumption for
        contradiction)") or an arbitrary-constant introduction ("Let c be
        in the domain. (Fresh Variable)").

        Returns `(detail, label)`: `detail` is the error description, or
        None if `first_entry` is a legal opener; `label` is the entry's own
        proof-file label if one could be determined at all (regardless of
        whether it turned out to be a legal opener), so the caller can
        build an accurate `location` even when this check fails. Reuses
        `_classify_entry` rather than re-deriving its own shape checks, so
        there's exactly one place that understands ProofParser's entry
        shapes.
        """
        entry = _classify_entry(first_entry)
        if isinstance(entry, str):
            return entry, None

        if entry.is_subproof_block:
            return "first line must be an assumption or arbitrary-constant introduction, not a nested subproof", entry.label

        justification = entry.justification
        if not isinstance(justification, tuple) or not justification or justification[0] not in ('assume', 'arbitrary'):
            return "first line must be an assumption or arbitrary-constant introduction", entry.label
        return None, entry.label

    def _validate_line(self, entry: _ParsedEntry, sidx: int, block_label: Optional[str], is_subproof: bool,
                       seen: list, labels: LabelScope, declarations: DeclarationScope,
                       outer_context: list) -> Optional[ValidationError]:
        """Validate one ordinary proof line and commit it to the current scope."""
        phi, justification, nested_subproof, label = entry.phi, entry.justification, entry.nested_subproof, entry.label

        if not isinstance(justification, tuple) or not justification:
            return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_JUSTIFICATION, "invalid justification format")

        tag = justification[0]
        explicit_declarations = list(justification[1]) if len(justification) >= 2 and isinstance(justification[1], list) else []

        err = self._register_declarations(explicit_declarations, declarations, label, sidx, block_label)
        if err:
            return err

        if tag == 'declare':
            if phi is None:
                if not explicit_declarations:
                    return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_JUSTIFICATION,
                                     "declaration line contains no declarations")
                return None

            if not isinstance(phi, fl.Formula):
                return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_ENTRY,
                                 "a declaration line must contain a Formula or explicit declarations")

            inferred = self._infer_missing_declarations(phi, declarations)
            err = self._register_declarations(inferred, declarations, label, sidx, block_label)
            if err:
                return err

            err = self._validate_formula_symbols(phi, declarations, label, sidx, block_label)
            if err:
                return err
            if not fl.is_closed(phi):
                return _mk_error(label, block_label, sidx, CATEGORY_NOT_CLOSED,
                                 "formula is not closed (has a free variable)")

            seen.append(phi)
            if label:
                labels[label] = phi
            return None

        if phi is None:
            if tag == 'premise' and explicit_declarations:
                return None
            return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_ENTRY,
                             f"justification '{tag}' requires a Formula")

        if isinstance(phi, list):
            if tag != 'premise' or not all(isinstance(item, fl.Formula) for item in phi):
                return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_ENTRY,
                                 "only premise lines may contain a bundle of Formula objects")

            if explicit_declarations:
                inferred = []
                for item in phi:
                    inferred.extend(self._infer_missing_declarations(item, declarations))
                err = self._register_declarations(_dedupe_declarations(inferred), declarations, label, sidx, block_label)
                if err:
                    return err

            for item in phi:
                err = self._validate_formula_symbols(item, declarations, label, sidx, block_label)
                if err:
                    return err
                if not fl.is_closed(item):
                    return _mk_error(label, block_label, sidx, CATEGORY_NOT_CLOSED,
                                     "formula is not closed (has a free variable)")
                err = self._validate_membership(item, self.premises, 'premises', label, sidx, block_label)
                if err:
                    return err

            seen.extend(phi)
            if label:
                labels[label] = list(phi)
            return None

        if not isinstance(phi, fl.Formula):
            return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_ENTRY,
                             f"justification '{tag}' requires a Formula")

        if tag == 'premise' and explicit_declarations:
            inferred = self._infer_missing_declarations(phi, declarations)
            err = self._register_declarations(inferred, declarations, label, sidx, block_label)
            if err:
                return err

        # An arbitrary constant is a local object declaration. It must be
        # introduced before its opening formula is checked.
        if tag == 'arbitrary' and isinstance(phi, fl.AtomicFormula) and not phi.args and isinstance(phi.predicate, str):
            err = self._register_declarations(
                [Declaration(phi.predicate, DeclarationKind.OBJECT)],
                declarations, label, sidx, block_label,
            )
            if err:
                return err

        # The nullary AtomicFormula used by the 'arbitrary' tag is a
        # meta-level freshness flag, not a proposition whose predicate
        # symbol must be declared.  Its object declaration was registered
        # immediately above.
        if tag != 'arbitrary':
            err = self._validate_formula_symbols(phi, declarations, label, sidx, block_label)
            if err:
                return err

        if not fl.is_closed(phi):
            return _mk_error(label, block_label, sidx, CATEGORY_NOT_CLOSED,
                             "formula is not closed (has a free variable)")

        if tag in ('assume', 'arbitrary'):
            err = self._validate_assume_or_arbitrary(tag, label, sidx, block_label, is_subproof)
        elif tag == 'premise':
            err = self._validate_membership(phi, self.premises, 'premises', label, sidx, block_label)
        elif tag == 'axiom':
            err = self._validate_membership(phi, self.axioms, 'axioms', label, sidx, block_label)
        elif tag == 'rule_below':
            err = self._validate_rule_below(phi, justification, nested_subproof, label, sidx,
                                            block_label, labels, declarations, seen)
        elif tag == 'rule_hybrid':
            err = self._validate_rule_hybrid(phi, justification, nested_subproof, label, sidx,
                                             block_label, labels, declarations, seen)
        elif tag == 'rule':
            err = self._validate_rule(phi, justification, label, sidx, block_label, labels)
        else:
            err = _mk_error(label, block_label, sidx, CATEGORY_UNKNOWN_TAG,
                            f"unknown justification tag '{tag}'")

        if err:
            return err

        seen.append(phi)
        if label:
            labels[label] = phi
        return None

    def _register_declarations(self, declarations_to_add: List[Declaration], scope: DeclarationScope,
                               label: Optional[str], sidx: int, block_label: Optional[str]) -> Optional[ValidationError]:
        for declaration in declarations_to_add:
            try:
                scope.declare(declaration)
            except KeyError:
                existing = scope.lookup(declaration.name)
                return _mk_error(
                    label, block_label, sidx, CATEGORY_DECLARATION_CONFLICT,
                    f"symbol '{declaration.name}' is already declared as "
                    f"{existing.kind if existing else 'another symbol kind'}",
                )
            except (TypeError, ValueError) as exc:
                return _mk_error(label, block_label, sidx, CATEGORY_DECLARATION_CONFLICT, str(exc))
        return None

    def _infer_missing_declarations(self, phi: fl.Formula, scope: DeclarationScope) -> List[Declaration]:
        result = []
        for declaration in _dedupe_declarations(_infer_declarations_from_formula(phi)):
            if scope.lookup(declaration.name) is None:
                result.append(declaration)
        return result

    def _validate_formula_symbols(self, phi: fl.Formula, declarations: DeclarationScope,
                                  label: Optional[str], sidx: int,
                                  block_label: Optional[str]) -> Optional[ValidationError]:
        """Require all constants, functions, predicates, and proposition symbols to be declared."""
        def make_error(category: str, detail: str) -> ValidationError:
            return _mk_error(label, block_label, sidx, category, detail)

        def check_term(term: tl.Term) -> Optional[ValidationError]:
            if isinstance(term, tl.VariableTerm):
                return None
            if isinstance(term, tl.ConstantTerm):
                decl = declarations.lookup(term.name)
                if decl is None:
                    return make_error(CATEGORY_UNDECLARED_SYMBOL,
                                      f"constant '{term.name}' is used but has not been declared")
                if decl.kind != DeclarationKind.OBJECT:
                    return make_error(CATEGORY_DECLARATION_KIND_MISMATCH,
                                      f"symbol '{term.name}' is declared as {decl.kind}, but is used as an object constant")
                return None
            if isinstance(term, tl.FunctionTerm):
                decl = declarations.lookup(term.symbol)
                if decl is None:
                    return make_error(CATEGORY_UNDECLARED_SYMBOL,
                                      f"function '{term.symbol}' is used but has not been declared")
                if decl.kind != DeclarationKind.FUNCTION:
                    return make_error(CATEGORY_DECLARATION_KIND_MISMATCH,
                                      f"symbol '{term.symbol}' is declared as {decl.kind}, but is used as a function")
                if decl.arity is not None and decl.arity != len(term.args):
                    return make_error(CATEGORY_DECLARATION_ARITY_MISMATCH,
                                      f"function '{term.symbol}' expects arity {decl.arity}, but is used with {len(term.args)} argument(s)")
                for arg in term.args:
                    err = check_term(arg)
                    if err:
                        return err
                return None
            return None

        if isinstance(phi, fl.AtomicFormula):
            if isinstance(phi.predicate, str):
                decl = declarations.lookup(phi.predicate)
                if decl is None:
                    return make_error(CATEGORY_UNDECLARED_SYMBOL,
                                      f"predicate/formula symbol '{phi.predicate}' is used but has not been declared")
                if phi.args:
                    if decl.kind != DeclarationKind.PREDICATE:
                        return make_error(CATEGORY_DECLARATION_KIND_MISMATCH,
                                          f"symbol '{phi.predicate}' is declared as {decl.kind}, but is used as a predicate")
                    if decl.arity is not None and decl.arity != len(phi.args):
                        return make_error(CATEGORY_DECLARATION_ARITY_MISMATCH,
                                          f"predicate '{phi.predicate}' expects arity {decl.arity}, but is used with {len(phi.args)} argument(s)")
                elif decl.kind not in (DeclarationKind.CLOSED_FORMULA, DeclarationKind.PREDICATE):
                    return make_error(CATEGORY_DECLARATION_KIND_MISMATCH,
                                      f"symbol '{phi.predicate}' is declared as {decl.kind}, but is used as a proposition")
            for arg in phi.args:
                if isinstance(arg, tl.Term):
                    err = check_term(arg)
                    if err:
                        return err
            return None

        if isinstance(phi, fl.And):
            for item in phi.conjuncts:
                err = self._validate_formula_symbols(item, declarations, label, sidx, block_label)
                if err:
                    return err
            return None
        if isinstance(phi, fl.Or):
            for item in phi.disjuncts:
                err = self._validate_formula_symbols(item, declarations, label, sidx, block_label)
                if err:
                    return err
            return None
        if isinstance(phi, fl.Not):
            return self._validate_formula_symbols(phi.sub, declarations, label, sidx, block_label)
        if isinstance(phi, fl.Implies):
            return (self._validate_formula_symbols(phi.antecedent, declarations, label, sidx, block_label)
                    or self._validate_formula_symbols(phi.consequent, declarations, label, sidx, block_label))
        if isinstance(phi, fl.Iff):
            return (self._validate_formula_symbols(phi.left, declarations, label, sidx, block_label)
                    or self._validate_formula_symbols(phi.right, declarations, label, sidx, block_label))
        if isinstance(phi, fl.Equals):
            return check_term(phi.left) or check_term(phi.right)
        if isinstance(phi, (fl.ForAll, fl.Exists)):
            return self._validate_formula_symbols(phi.body, declarations, label, sidx, block_label)
        return None

    def _validate_assume_or_arbitrary(self, tag: str, label: Optional[str], sidx: int,
                                       block_label: Optional[str], is_subproof: bool) -> Optional[ValidationError]:
        """'assume'/'arbitrary' lines open a subproof and must be its first
        line. Restricting the tag to exactly `sidx == 0` of a genuine
        subproof block is soundness-critical: without it, a justification
        that happens to parse as a bare assumption could be inserted
        *anywhere* in a subproof, letting an unjustified formula slip into
        the middle of a derivation instead of only ever opening one.
        """
        if not is_subproof or sidx != 0:
            return _mk_error(label, block_label, sidx, CATEGORY_WRONG_POSITION, f"'{tag}' is only permitted as the first line of a subproof")
        return None

    def _validate_membership(self, phi: fl.Formula, allowed: list, kind: str,
                              label: Optional[str], sidx: int, block_label: Optional[str]) -> Optional[ValidationError]:
        """Shared check for the 'premise' and 'axiom' tags: `phi` must
        `_ast_eq`-match something in the allowed list (`self.premises` or
        `self.axioms`). An empty/falsy allowed list means "anything goes"
        -- `Proof()` constructed without explicit premises accepts any
        formula asserted as a premise.
        """
        if allowed and not any(_ast_eq(phi, item) for item in allowed):
            return _mk_error(label, block_label, sidx, CATEGORY_UNREGISTERED_FORMULA, f"asserted as a {kind[:-1]}, but does not match any declared {kind}")
        return None

    def _validate_rule_hybrid(self, phi: fl.Formula, justification: tuple,
                               nested_subproof: Optional[list], label: Optional[str],
                               sidx: int, block_label: Optional[str],
                               labels: LabelScope, declarations: DeclarationScope,
                               seen: list) -> Optional[ValidationError]:
        """Validate a rule that cites ordinary lines plus consecutive subproofs
        immediately below the rule line.

        Example::

            1. P or Q. (Premise)
            2. R. (Proof by Cases from 1, subproofs below)
            begin subproof
              2.1. P. (Case)
              2.2. R. (Modus Ponens from 3, 2.1)
            end subproof
            begin subproof
              2.1. Q. (Case)
              2.2. R. (Modus Ponens from 3, 2.1)
            end subproof

        The explicit labels are resolved in the current label scope; each
        attached subproof receives a fresh child declaration/label scope and
        cannot leak declarations or local labels back into the outer proof.
        """
        if len(justification) != 3:
            return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_JUSTIFICATION,
                             "malformed hybrid rule justification")
        rule, indices = justification[1], justification[2]
        if nested_subproof is None or not isinstance(nested_subproof, list):
            return _mk_error(label, block_label, sidx, CATEGORY_MISSING_SUBPROOF,
                             "hybrid rule requires subproofs below the cited line")

        if isinstance(rule, NamedRulePlaceholder):
            resolved = next((r for r in self.rules if r.name == rule.name), None)
            if resolved is None:
                return _mk_error(label, block_label, sidx, CATEGORY_UNRECOGNIZED_RULE,
                                 f"no rule named '{rule.name}' is registered for this proof (check that the relevant Type was combined in)")
            rule = resolved

        if not self._rule_is_registered(rule):
            return _mk_error(label, block_label, sidx, CATEGORY_UNRECOGNIZED_RULE,
                             f"rule '{rule.name}' is not one of the rules this proof allows")

        arity = getattr(rule, 'premise_arity', 0)
        expected_subproofs = arity - len(indices)
        if expected_subproofs <= 0 or len(nested_subproof) != expected_subproofs:
            return _mk_error(
                label, block_label, sidx, CATEGORY_ARITY_MISMATCH,
                f"'{rule.name}' requires {expected_subproofs} subproof(s) after {len(indices)} explicit citation(s), "
                f"but {len(nested_subproof)} were provided",
            )

        missing = [i for i in indices if i not in labels]
        if missing:
            return _mk_error(label, block_label, sidx, CATEGORY_BAD_REFERENCE,
                             f"cites {missing}, which {'is' if len(missing) == 1 else 'are'} not defined or not in scope at this point in the proof")

        available = []
        for index in indices:
            value = labels[index]
            if isinstance(value, list):
                available.extend(value)
            else:
                available.append(value)

        for subentries in nested_subproof:
            ok, err, sp_rec = self._validate_block(
                subentries,
                label,
                [],
                labels.child(),
                declarations.child(),
                seen,
                is_subproof=True,
            )
            if not ok:
                return err
            available.append(sp_rec)

        if len(available) < arity:
            return _mk_error(label, block_label, sidx, CATEGORY_ARITY_MISMATCH,
                             f"'{rule.name}' requires {arity} candidate premise(s), but the cited line(s) and subproofs provide only {len(available)}")

        for candidate_indices in itertools.combinations(range(len(available)), arity):
            candidates = [available[i] for i in candidate_indices]
            try:
                if rule.applies(candidates, phi):
                    return None
            except Exception as raised:
                return _mk_error(label, block_label, sidx, CATEGORY_RULE_RAISED,
                                 f"'{rule.name}' raised an exception while checking this line: {raised}")

        return _mk_error(label, block_label, sidx, CATEGORY_RULE_MISMATCH,
                         f"'{rule.name}' does not justify {phi!r} from the cited line(s) {indices} and attached subproofs")

    def _validate_rule_below(self, phi: fl.Formula, justification: tuple, nested_subproof: Optional[list],
                              label: Optional[str], sidx: int, block_label: Optional[str],
                              labels: LabelScope, declarations: DeclarationScope,
                              seen: list) -> Optional[ValidationError]:
        """'rule_below': `phi` is justified by a rule (ConditionalIntroduction,
        ProofByContradiction, or UniversalGeneralization) applied to the
        subproof written immediately below this line. That subproof is
        validated using `label` (this line's own label) as its
        `block_label`, since a `rule_below` subproof has no label of its
        own -- see `_validate_block`'s docstring.
        """
        if nested_subproof is None:
            return _mk_error(label, block_label, sidx, CATEGORY_MISSING_SUBPROOF, "justification requires an immediate subproof below, but none was found")
        rule = justification[1]
        ok, err, sp_rec = self._validate_block(
            nested_subproof, label, [], labels.child(), declarations.child(), seen, is_subproof=True
        )
        if not ok:
            return err

        if not self._rule_is_registered(rule):
            return _mk_error(label, block_label, sidx, CATEGORY_UNRECOGNIZED_RULE, f"rule '{rule.name}' is not one of the rules this proof allows")
        if not rule.applies([sp_rec], phi):
            return _mk_error(label, block_label, sidx, CATEGORY_RULE_MISMATCH, f"'{rule.name}' does not justify {phi!r} from the subproof immediately below this line")
        return None

    def _validate_rule(self, phi: fl.Formula, justification: tuple, label: Optional[str],
                       sidx: int, block_label: Optional[str], labels: LabelScope) -> Optional[ValidationError]:
        """Validate a rule citation, including labels that denote bundled premises."""
        if len(justification) != 3:
            return _mk_error(label, block_label, sidx, CATEGORY_MALFORMED_JUSTIFICATION,
                             "malformed rule justification (expected a rule and a list of cited lines)")
        rule, indices = justification[1], justification[2]

        if isinstance(rule, NamedRulePlaceholder):
            resolved = next((r for r in self.rules if r.name == rule.name), None)
            if resolved is None:
                return _mk_error(label, block_label, sidx, CATEGORY_UNRECOGNIZED_RULE,
                                  f"no rule named '{rule.name}' is registered for this proof (check that the relevant Type was combined in)")
            rule = resolved

        if not self._rule_is_registered(rule):
            return _mk_error(label, block_label, sidx, CATEGORY_UNRECOGNIZED_RULE,
                             f"rule '{rule.name}' is not one of the rules this proof allows")

        missing = [i for i in indices if i not in labels]
        if missing:
            return _mk_error(label, block_label, sidx, CATEGORY_BAD_REFERENCE,
                              f"cites {missing}, which {'is' if len(missing) == 1 else 'are'} not defined or not in scope at this point in the proof")

        available = []
        for index in indices:
            value = labels[index]
            if isinstance(value, list):
                available.extend(value)
            else:
                available.append(value)

        # Almost every rule has one fixed `premise_arity`, checked here,
        # the same as always. A rule may instead opt into
        # `variable_arity = True` (default `False` -- every existing rule
        # is entirely unaffected) when the *number* of facts it needs
        # genuinely isn't fixed -- AlgebraRule is the motivating case: a
        # citation might resolve to one equation or, through a bundled
        # label, several, and which of those (or which subset) are
        # actually relevant depends on what `phi` claims, not on anything
        # knowable from the citation text alone. Trying every arity from
        # `len(available)` down to 1 (largest first, so a combination that
        # uses everything cited is preferred over one that happens to
        # ignore some of it) costs at most `2**len(available)` calls to
        # `applies`, which is fine for citations in the single digits --
        # exactly the range this is for.
        if getattr(rule, 'variable_arity', False):
            if not available:
                return _mk_error(label, block_label, sidx, CATEGORY_ARITY_MISMATCH,
                                 f"'{rule.name}' requires at least one cited fact, but none were given")
            arities = range(len(available), 0, -1)
        else:
            arity = getattr(rule, 'premise_arity', 1)
            if len(indices) > arity:
                return _mk_error(label, block_label, sidx, CATEGORY_ARITY_MISMATCH,
                                 f"'{rule.name}' requires at most {arity} cited line label(s), but {len(indices)} were given ({indices})")
            if len(available) < arity:
                return _mk_error(label, block_label, sidx, CATEGORY_ARITY_MISMATCH,
                                 f"'{rule.name}' requires exactly {arity} candidate premise(s), but the cited line(s) provide only {len(available)}")
            arities = [arity]

        for arity_to_try in arities:
            for candidate_indices in itertools.combinations(range(len(available)), arity_to_try):
                candidates = [available[i] for i in candidate_indices]
                try:
                    if rule.applies(candidates, phi):
                        return None
                except Exception as raised:
                    return _mk_error(label, block_label, sidx, CATEGORY_RULE_RAISED,
                                     f"'{rule.name}' raised an exception while checking this line: {raised}")

        return _mk_error(label, block_label, sidx, CATEGORY_RULE_MISMATCH,
                         f"'{rule.name}' does not justify {phi!r} from the cited line(s) {indices}")

    def _rule_is_registered(self, rule: InferenceRule) -> bool:
        """Is `rule` an instance of one of the rule *types* this `Proof`
        was configured with? (A `Proof` built with a restricted `rules=`
        list -- see `default_rules` -- rejects citations of rules outside
        that list, even if the rule class exists in this module.)
        """
        return any(isinstance(rule, type(r)) for r in self.rules)


# ==========================================================================
# SECTION 8 -- Public façade
# ==========================================================================

class Proof:
    """A complete proof: a list of `entries` (see the module docstring),
    optionally restricted to a specific set of `premises`, `axioms`, and/or
    `rules`. Call `.check()` to validate it.

    Example::

        >>> ok, msg = Proof(entries, premises=[A_a, fl.Implies(A_a, C_a)]).check()
        >>> ok
        True
    """
    def __init__(self, entries: List[tuple], premises: Optional[List[fl.Formula]] = None,
                 axioms: Optional[List[fl.Formula]] = None, rules: Optional[List[InferenceRule]] = None,
                 declarations: Optional[List[Declaration]] = None):
        # ElaboratedEntries is a list subclass, so preserve its metadata before
        # converting the core entries to an ordinary list.  Theory resources
        # required by surface sugar are merged automatically.
        self.origin_by_label = dict(getattr(entries, 'origin_by_label', {}) or {})
        self.surface_proof = getattr(entries, 'surface_proof', None)
        required_rules = list(getattr(entries, 'required_rules', []) or [])
        required_axioms = list(getattr(entries, 'required_axioms', []) or [])
        required_declarations = list(getattr(entries, 'required_declarations', []) or [])

        self.entries = list(entries)
        self.premises = list(premises or [])

        self.axioms = list(axioms or [])
        for axiom in required_axioms:
            if not any(_ast_eq(axiom, existing) for existing in self.axioms):
                self.axioms.append(axiom)

        self.rules = list(rules if rules is not None else default_rules())
        for rule in required_rules:
            if not any(type(rule) is type(existing) and getattr(rule, 'name', None) == getattr(existing, 'name', None)
                       for existing in self.rules):
                self.rules.append(rule)

        self.declarations = list(declarations or [])
        by_name = {declaration.name: declaration for declaration in self.declarations}
        for declaration in required_declarations:
            existing = by_name.get(declaration.name)
            if existing is None:
                self.declarations.append(declaration)
                by_name[declaration.name] = declaration
            elif existing != declaration:
                raise ValueError(
                    f"conflicting built-in declaration for symbol '{declaration.name}'"
                )

    def check(self) -> Tuple[bool, Optional[str]]:
        """Validate the whole proof. Returns `(True, None)` if every line
        is justified, or `(False, message)` describing the first problem
        found, in the order lines appear (depth-first through subproofs).

        `message` is `str(err)` for the `ValidationError` `check_detailed`
        returns -- this method's `(bool, str)` contract is unchanged from
        before `ValidationError` existed, so existing callers (including
        `test_runner.py`, which only compares the boolean) are unaffected.
        Prefer `check_detailed()` for anything that wants to branch on
        *why* a proof failed, or needs the bare offending line label,
        rather than parsing this string.
        """
        ok, err = self.check_detailed()
        return ok, (str(err) if err is not None else None)

    def check_detailed(self) -> Tuple[bool, Optional[ValidationError]]:
        """Like `check()`, but returns the structured `ValidationError`
        instead of its rendered string -- lets a caller branch on
        `err.category` (see the `CATEGORY_*` constants) or read
        `err.label`/`err.location` directly. See `ProofParser.run_file`
        for an example that uses `err.label` to find the offending source
        line without any message-text parsing.
        """
        validator = ProofValidator(
            self.rules, self.premises, self.axioms,
            declarations=self.declarations,
        )
        ok, err, _ = validator.validate(self.entries)
        if err is not None and err.label in self.origin_by_label:
            origin = self.origin_by_label[err.label]
            surface_label = origin.span.label
            location = origin.span.location
            detail = err.detail
            if origin.synthetic:
                detail = f"Invalid {origin.construct}: {detail}"
            err = ValidationError(location, surface_label, err.category, detail)
        return ok, err


if __name__ == "__main__":
    print("=== ProofLogic module loaded successfully ===")





