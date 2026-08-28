


"""Translates plain-text Fitch-style proofs into the ``entries`` tuples that
`ProofLogic.Proof` checks.

This module implements the front end of a small proof compiler.  It first
parses the user's natural proof notation into a source-located
``ProofElaboration.SurfaceProof`` and then elaborates syntactic sugar into the
strict tuple language checked by ``ProofLogic``.  Generated core steps retain
origin metadata, so errors can still be reported against the lines the user
actually wrote.

--------------------------------------------------------------------------
The text grammar, worked example
--------------------------------------------------------------------------
A proof is a sequence of lines. Each line is either:

  * a numbered formula line:   ``<label>. <formula>. (<justification>)``
    e.g. ``3. C(a). (Modus Ponens from 1,2)``
  * a subproof delimiter:      ``begin subproof`` / ``end subproof``

Numbered lines may use dotted labels ("2.1", "1.2.1", ...) to reflect
subproof nesting, though the label text itself is never interpreted
structurally -- nesting is entirely determined by ``begin subproof`` /
``end subproof`` blocks; labels are just opaque strings used to cite lines
later ("from 2.1"). A logical line may be wrapped across several physical
text lines (see `parse_proof_text`); only lines that *start* a new numbered
entry or a subproof delimiter begin a new logical line.

Given (testProofs/mp_premises.txt)::

    1. A(a). (Premise)
    2. A(a) -> C(a). (Premise)
    3. C(a). (Modus Ponens from 1,2)

``parse_proof_text`` produces (schematically)::

    entries = [
        (None, AtomicFormula('A', [a]), ('premise',)),
        (None, Implies(AtomicFormula('A', [a]), AtomicFormula('C', [a])), ('premise',)),
        (None, AtomicFormula('C', [a]), ('rule', ModusPonensRule(), ['1', '2'])),
    ]

ready to hand to ``ProofLogic.Proof(entries)``. A subproof (testProofs/proof_by_contradiction.txt)::

    1. A or not A. (Proof by Contradiction from subproof below)
    begin subproof
     1.1. not (A or not A). (Assumption for contradiction)
     1.2. (not A) and not (not A). (De Morgans from 1.1)
    end subproof

produces a single 4-element entry for line 1, whose last element is the
subproof's own (recursively parsed) entry list::

    (None, Or(A, Not(A)), ('rule_below', ProofByContradictionRule()), [
        (None, Not(Or(A, Not(A))), ('assume',)),
        (None, And(Not(A), Not(Not(A))), ('rule', PropositionalEquivalenceRule(), ['1.1'])),
    ])

--------------------------------------------------------------------------
Two things worth knowing before writing new proof text
--------------------------------------------------------------------------
1. **Connective precedence in `parse_formula` is not the textbook one.**
   Checks run in this order: quantifiers, ``and``, ``or``, parenthesized
   unwrap, ``not``, the ``<->``/``iff`` family, ``->``/``implies``/``if...then``.
   Whichever pattern is tried *first* ends up as the outermost (loosest-
   binding) connective for an unparenthesized string, so -- unlike most
   textbooks, where ``and`` binds *tighter* than ``->`` -- here ``and``/``or``
   are split before ``->`` is even considered, making them the *looser*
   connective when both appear unparenthesized in the same string:
   ``parse_formula("A -> B and C")`` parses as ``(A -> B) and C``, not
   ``A -> (B and C)``. Every formula in testProofs/ that mixes connectives
   uses explicit parentheses specifically to sidestep this; new proof text
   should do the same rather than rely on implicit precedence.

2. **Natural-language biconditional wording is supported.** The phrase
   ``A if and only if B`` is recognized before the top-level ``and`` split,
   so its embedded word "and" does not interfere with biconditional parsing.
"""

import re
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.TermLogic as tl
import SyLoPy.source.ProofContext as pc
from SyLoPy.source.ProofElaboration import (
    CoreOrigin,
    ElaboratedEntries,
    ElaborationError,
    SourceSpan,
    SurfaceExpression,
    SurfaceLine,
    SurfaceProof,
    SurfaceSubproof,
    SurfaceDeclaration,
    SurfaceDeclarationClause,
    SurfacePremiseClause,
    SurfaceDeclarationStatement,
    TheoryEnvironment,
)


# Compiled once and reused everywhere a "begin subproof" / "end subproof"
# delimiter needs to be recognized, instead of re-typing (and re-compiling)
# the same pattern at each of the several call sites below.
_BEGIN_SUBPROOF_RE = re.compile(r'^begin\s+subproof', re.I)
_END_SUBPROOF_RE = re.compile(r'^end\s+subproof', re.I)

_USE_THEORY_RE = re.compile(r'^use\s+(.+?)\.?$', re.I)
_SUPPORTED_THEORIES = {
    "discrete math",
    "discrete mathematics",
}


def _is_theory_directive(text: str) -> bool:
    match = _USE_THEORY_RE.match(text.strip())
    if not match:
        return False
    theory = re.sub(r"\s+", " ", match.group(1).strip().lower())
    if theory in _SUPPORTED_THEORIES:
        return True
    raise ElaborationError(f"unknown theory directive: {text.strip()!r}")

# A numbered line's label, e.g. "2" or "1.2.1", followed by its trailing '.'.
_LABELED_LINE_RE = re.compile(r'^\s*([0-9]+(?:\.[A-Za-z0-9_]+)*)\.\s*(.*)$')

# `parse_term`/`parse_formula` need a `TheoryEnvironment` to recognize
# theory-specific syntax even in *nested* positions -- e.g. "a|n" inside
# "if a|n then ...", which reaches these functions through their own
# recursive calls, never through `_ElaborationContext.parse_surface_expression`
# (that only ever sees the *top* of one proof line). Rebuilding
# `default_theory_environment()` -- which imports every known theory module
# -- on every recursive call would be wasteful, so it's built once and
# cached here. Call sites that already have a specific environment (the
# elaboration context) pass it through explicitly instead of using this.
_DEFAULT_ENVIRONMENT_CACHE: Optional[TheoryEnvironment] = None


def _cached_default_environment() -> TheoryEnvironment:
    global _DEFAULT_ENVIRONMENT_CACHE
    if _DEFAULT_ENVIRONMENT_CACHE is None:
        _DEFAULT_ENVIRONMENT_CACHE = default_theory_environment()
    return _DEFAULT_ENVIRONMENT_CACHE


def split_top_level(s: str, sep: str) -> List[str]:
    """Split `s` on every top-level (paren-depth-0) occurrence of `sep`,
    left to right, leaving anything inside parentheses untouched.

    This is what lets `parse_formula` tell "the *outer* connective is
    this" from "there's a connective-looking substring, but it's nested
    inside a sub-formula I haven't unwrapped yet".

    Examples::

        >>> split_top_level("A and (B and C)", " and ")
        ['A', '(B and C)']
        >>> split_top_level("f(x, g(y, z)), w", ",")
        ['f(x, g(y, z))', 'w']
        >>> split_top_level("A or B or C", " or ")
        ['A', 'B', 'C']
    """
    parts = []
    depth = 0
    buf = []
    i = 0
    while i < len(s):
        if s[i] == '(':
            depth += 1
            buf.append(s[i])
        elif s[i] == ')':
            depth -= 1
            if depth < 0:
                raise ValueError("Unmatched closing parenthesis in string: " + s)
            buf.append(s[i])
        elif depth == 0 and s.startswith(sep, i):
            parts.append(''.join(buf).strip())
            buf = []
            i += len(sep) - 1
        else:
            buf.append(s[i])
        i += 1
    if depth > 0:
        raise ValueError("Unmatched opening parenthesis in string: " + s)
    if buf:
        parts.append(''.join(buf).strip())
    return parts


def _parse_arg_list(args_str: str, bound_vars: set, environment: Optional[TheoryEnvironment] = None) -> List[tl.Term]:
    """Parse a comma-separated argument list (the inside of `pred(...)` or
    `func(...)`) into a list of Terms, splitting only on top-level commas
    so nested calls like `f(x, g(y, z)), w` split into exactly two
    arguments, not four. Shared by `parse_term` (function terms) and
    `parse_formula` (atomic predicates) since both need identical
    argument-list handling. An empty `args_str` (e.g. the `()` in a
    zero-arity `P()`) correctly yields `[]`.
    """
    return [parse_term(a, bound_vars, environment) for a in split_top_level(args_str, ',')]


# Bare identifier, matched against a leading declared/bound symbol name
# (also reused as the "is this bare string a legal fallback atom/constant"
# check, since a legal symbol name is exactly what's legal there too).
_BARE_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*$')


def _match_applied_symbol(s: str) -> Optional[Tuple[str, str]]:
    """Match `s` against ``symbol(args)`` -- a leading identifier followed
    by a parenthesized group whose matching close-paren is the *last*
    character of `s` -- and return `(symbol, args_str)`, or `None` if `s`
    isn't shaped like that.

    This exists instead of the tempting one-line regex
    ``^([A-Za-z_][A-Za-z0-9_]*)\\((.*)\\)$`` because that regex only checks
    that `s` *ends* with ``)``; it doesn't check that this is the close-paren
    matching the *first* open-paren. Since `.*` is greedy, it happily
    matches something shaped like ``f(y) < f(z)`` too -- capturing group 2
    as the nonsense string ``y) < f(z`` -- because that also ends in ``)``.
    Callers used to feed that straight to `_parse_arg_list`, which choked on
    the stray leading ``)`` with a confusing "Unmatched closing parenthesis"
    error that gave no hint the real problem was an unsupported infix
    comparison. Scanning paren depth explicitly, the way `split_top_level`
    does, instead of pattern-matching the whole string, is what correctly
    rejects this shape instead of mis-accepting it.
    """
    m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*\(', s)
    if not m:
        return None
    sym = m.group(1)
    rest = s[m.end():]
    depth = 1
    for i, ch in enumerate(rest):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                # The matching close-paren for the *first* '(' must be the
                # last character of `s` -- anything trailing it (like the
                # " < f(z)" in "f(y) < f(z)") means this isn't a bare
                # application after all, just a string that happens to
                # contain one.
                return (sym, rest[:i]) if i == len(rest) - 1 else None
    return None  # unbalanced -- no matching close-paren found


def parse_term(s: str, bound_vars=None, environment: Optional[TheoryEnvironment] = None):
    """Parse a single term: a function application, a bound variable, or a
    constant.

    `bound_vars` is the set of variable names currently in scope (threaded
    down from any enclosing quantifier in `parse_formula`); a bare name is
    a `VariableTerm` if and only if it's in that set, otherwise it's
    treated as a `ConstantTerm` naming itself (`ConstantTerm(s, s)` --
    since this is a purely syntactic checker, a constant's "value" is
    never actually used, only its identity for equality/matching, so it
    defaults to its own name).

    `environment` supplies theory-specific term syntax (e.g. SetTheory's
    "the empty set", a future NumberTheory's "n/a") via its `term_parsers`;
    defaults to the cached `default_theory_environment()` when omitted, so
    every known theory's term sugar is recognized unless a caller
    deliberately passes a narrower environment.

    Examples::

        >>> parse_term('a')                        # no bound_vars -> constant
        a
        >>> parse_term('x', bound_vars={'x'})       # in scope -> variable
        x
        >>> parse_term('f(x, a)', bound_vars={'x'})
        f(x, a)
    """
    if bound_vars is None:
        bound_vars = set()
    if environment is None:
        environment = _cached_default_environment()
    s = s.strip()
    for term_parser in environment.term_parsers:
        result = term_parser(s, bound_vars)
        if result is not None:
            return result
    matched = _match_applied_symbol(s)
    if matched:
        sym, args_str = matched
        return tl.FunctionTerm(sym, _parse_arg_list(args_str, bound_vars, environment))
    if s in bound_vars:
        return tl.VariableTerm(s)
    if _BARE_IDENTIFIER_RE.match(s):
        return tl.ConstantTerm(s, s)
    raise ValueError(
        f"Unrecognized term syntax: {s!r}. Expected a bound variable, a "
        f"function application like 'f(x)', a simple constant name, or "
        f"syntax registered by an imported theory module -- not a raw, "
        f"unrecognized expression silently treated as an opaque constant."
    )



def _parse_formula_or_bundle(text: str, environment: Optional[TheoryEnvironment] = None):
    """Parse one formula or a period-separated bundle of formulas.

    Premise lines may introduce several assumptions at once, e.g.:

        Let A, B be closed formulas such that: A -> B. B -> C.

    A bundle is represented as a list so one proof-line label can refer to
    all of its component formulas at once.
    """
    parts = [part.strip() for part in split_top_level(text.strip().rstrip('.'), '.') if part.strip()]
    formulas = [parse_formula(part, environment=environment) for part in parts]
    if len(formulas) == 1:
        return formulas[0]
    return formulas


def _declaration_kind_from_descriptor(descriptor: str) -> Tuple[str, Optional[str]]:
    d = re.sub(r'\s+', ' ', descriptor.strip().lower())
    d = re.sub(r'^(?:a|an|any|the)\s+', '', d)
    if 'closed formula' in d:
        return pl.DeclarationKind.CLOSED_FORMULA, None
    if 'predicate' in d or 'property' in d:
        return pl.DeclarationKind.PREDICATE, None
    if 'function' in d:
        return pl.DeclarationKind.FUNCTION, None
    if 'object' in d:
        return pl.DeclarationKind.OBJECT, None
    return pl.DeclarationKind.OBJECT, d or None


def parse_declaration_prefix(text: str) -> Tuple[List[pl.Declaration], Optional[str]]:
    """Parse a leading `Let ...` declaration clause.

    Returns `(declarations, formula_text)`.  A declaration-only line has
    `formula_text is None`; a premise line using `such that:` returns the
    formula after the declaration prefix.

    This is the *fallback* case of the more general mechanism just below
    (`elaborate_typed_declaration` / `DECLARATION_RECIPE_REGISTRY`): a
    plain object with no registered structure recipe for its descriptor.
    It stays a free-standing function (rather than folding into that
    mechanism entirely) because "such that:" premises need it directly,
    without going through a full line's worth of recipe-dispatch.
    """
    s = text.strip().rstrip('.').strip()
    if not re.match(r'^let\b', s, flags=re.I):
        return [], None

    m = re.search(r'\bsuch\s+that\s*:\s*', s, flags=re.I)
    if m:
        declaration_text = s[:m.start()].strip()
        formula_text = s[m.end():].strip().rstrip('.').strip()
        if not formula_text:
            raise ValueError("'such that:' must be followed by a formula")
    else:
        declaration_text = s
        formula_text = None

    m = re.match(r'^let\s+(.+)$', declaration_text, flags=re.I)
    if not m:
        return [], None

    declarations: List[pl.Declaration] = []
    for clause in split_declaration_clauses(m.group(1)):
        dc = parse_declaration_clause(clause)
        if dc.domain is not None:
            raise ValueError(
                f"Invalid declaration clause: {clause!r} (a 'NAME: DOM -> COD' "
                f"clause needs a matching structure recipe -- see "
                f"DECLARATION_RECIPE_REGISTRY -- to say what that typed "
                f"function's descriptor, {dc.descriptor!r}, means)"
            )
        for name in dc.names:
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
                raise ValueError(f"Invalid declared symbol name: {name!r}")
        kind, type_name = _declaration_kind_from_descriptor(dc.descriptor)
        declarations.extend(
            pl.Declaration(name=name, kind=kind, type_name=type_name)
            for name in dc.names
        )

    return declarations, formula_text


_DECLARATION_CLAUSE_SEPARATORS = (', and let ', ' and let ', ', let ', ' and ')


def split_declaration_clauses(s: str) -> List[str]:
    """Split the body of a `Let ...` declaration into clauses, paren-depth
    aware -- so the comma inside a tuple target like `(W, <)` is never
    mistaken for a clause boundary -- and accepting a "let" repeated per
    clause (", let " / " and let ") in addition to the original
    single-"let"-shared-across-clauses style (plain " and ", e.g. "Let X
    be A and Y be B").

    This used to be duplicated per theory module (OrderTheory had its own
    copy for parsing poset declarations); it's shared now because clause
    splitting is the same mechanical problem for every structure type a
    theory module might ever declare, not something specific to posets.
    """
    parts: List[str] = []
    depth = 0
    buf: List[str] = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch == '(':
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ')':
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if depth == 0:
            sep = next((c for c in _DECLARATION_CLAUSE_SEPARATORS if s.startswith(c, i)), None)
            if sep:
                parts.append(''.join(buf).strip())
                buf = []
                i += len(sep)
                continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append(''.join(buf).strip())
    return [p for p in parts if p]


class DeclarationClause:
    """One `NAME(S) be DESCRIPTOR` clause from a `Let ...` line, already
    picked apart into its structural pieces -- shared, parsed-once input
    for both the plain-object fallback (`parse_declaration_prefix`) and
    every registered structure recipe (`DECLARATION_RECIPE_REGISTRY`), so
    neither has to re-parse tuple targets or function-type annotations
    itself.

    `names`: the symbol name(s) this clause introduces -- more than one
    only when `is_tuple` (`(W, <)`) or from old-style comma-joined names
    under one descriptor (`Let a, b be sets`).
    `domain`/`codomain`: set only for a `NAME: DOM -> COD` clause (a
    typed-function target); `None` otherwise.
    `descriptor`: the raw text after "be" (before any kind/type-name
    interpretation -- that's the recipe's or `_declaration_kind_from_
    descriptor`'s job, not this class's).
    """
    __slots__ = ('names', 'is_tuple', 'domain', 'codomain', 'descriptor', 'normalized_descriptor')

    def __init__(self, names: List[str], is_tuple: bool, descriptor: str,
                 domain: Optional[str] = None, codomain: Optional[str] = None):
        self.names = names
        self.is_tuple = is_tuple
        self.descriptor = descriptor
        self.domain = domain
        self.codomain = codomain
        # `descriptor` with whitespace collapsed, lowercased, and a
        # leading "a"/"an"/"any"/"the" stripped -- computed once here
        # rather than left for every recipe to redo (and risk forgetting:
        # this normalization step is exactly what `Type.as_declaration_
        # recipe` originally got wrong before this field existed).
        normalized = re.sub(r'\s+', ' ', descriptor.strip().lower())
        self.normalized_descriptor = re.sub(r'^(?:a|an|any|the)\s+', '', normalized)

    def __repr__(self):
        typed = f", domain={self.domain!r}, codomain={self.codomain!r}" if self.domain else ""
        return f"DeclarationClause(names={self.names!r}, is_tuple={self.is_tuple}{typed}, descriptor={self.descriptor!r})"


_FUNCTION_TARGET_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\s+be\s+(.+)$', re.I)
_TUPLE_TARGET_RE = re.compile(r'^\((.+)\)\s+be\s+(.+)$', re.I)
_PLAIN_TARGET_RE = re.compile(r'^(.+?)\s+(?:be|are)\s+(.+)$', re.I)


def parse_declaration_clause(clause: str) -> DeclarationClause:
    """Parse one clause (as produced by `split_declaration_clauses`) into
    a `DeclarationClause`. Recognizes, in this order: a typed-function
    target (`f: W -> W be ...`), a tuple target (`(W, <) be ...`), or a
    plain comma-joined name list (`X be ...` / `a, b be ...`).
    """
    clause = clause.strip()
    m = _FUNCTION_TARGET_RE.match(clause)
    if m:
        name, domain, codomain, descriptor = m.groups()
        return DeclarationClause([name], is_tuple=False, descriptor=descriptor, domain=domain, codomain=codomain)
    m = _TUPLE_TARGET_RE.match(clause)
    if m:
        inner, descriptor = m.groups()
        names = [n.strip() for n in split_top_level(inner, ',') if n.strip()]
        return DeclarationClause(names, is_tuple=True, descriptor=descriptor)
    m = _PLAIN_TARGET_RE.match(clause)
    if m:
        names_part, descriptor = m.groups()
        names = [n.strip() for n in names_part.split(',') if n.strip()]
        return DeclarationClause(names, is_tuple=False, descriptor=descriptor)
    raise ValueError(f"Invalid declaration clause: {clause!r}")



_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_DECL_START_RE = re.compile(r'^(?:[A-Za-z_][A-Za-z0-9_]*\s*,\s*)*[A-Za-z_][A-Za-z0-9_]*\s+(?:be|are)\b', re.I)
_FORMULA_START_RE = re.compile(
    r'^(?:not\b|for\s+all\b|forall\b|exists\b|there\s+exists\b|if\b|[A-Za-z_][A-Za-z0-9_]*\s*\()',
    re.I,
)


def _top_level_keyword_positions(s: str, keyword: str) -> List[int]:
    positions = []
    depth = 0
    i = 0
    low = s.lower()
    needle = keyword.lower()
    while i <= len(s) - len(keyword):
        ch = s[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if depth == 0 and low.startswith(needle, i):
            positions.append(i)
            i += len(keyword)
            continue
        i += 1
    return positions


def _text_after_is_declaration_start(s: str) -> bool:
    return bool(_DECL_START_RE.match(s.strip()))


def _text_after_is_formula_start(s: str) -> bool:
    return bool(_FORMULA_START_RE.match(s.strip()))


def _next_top_level_separator(s: str, start: int) -> str:
    """Return the next top-level `and`/comma-separated segment."""
    depth = 0
    i = start
    while i < len(s):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
        elif depth == 0:
            if s[i] == ',':
                return s[start:i]
            if s[i:i+5].lower() == ' and ':
                return s[start:i]
        i += 1
    return s[start:]


def _split_compound_declaration_items(body: str) -> List[str]:
    """Split a coordinated ``Let`` body into declaration and premise clauses.

    Commas have two roles in this language: they coordinate clauses and they
    occur inside grouped names (``a, b, c``) and relation descriptions
    (``reflexive, antisymmetric, transitive``).  Parentheses protect formula
    argument lists.  Once a premise clause has begun, a top-level comma is a
    clause separator unless the following text starts another declaration.
    """
    items: List[str] = []
    buf: List[str] = []
    depth = 0
    premise_mode = False
    i = 0

    descriptor_words = {
        "a", "an", "any", "the", "object", "objects", "set", "sets",
        "formula", "formulas", "predicate", "predicates", "property",
        "properties", "function", "functions", "relation", "relations",
        "reflexive", "symmetric", "antisymmetric", "transitive", "unary",
        "binary", "on", "from", "to", "such", "that",
    }

    def flush() -> None:
        text = ''.join(buf).strip().strip(',')
        if text:
            items.append(text)
        buf.clear()

    def next_nonspace(pos: int) -> str:
        return body[pos:].lstrip()

    def looks_like_formula(text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        if _text_after_is_formula_start(text):
            return True
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\b', text)
        if not m:
            return False
        return m.group(1).lower() not in descriptor_words

    while i < len(body):
        ch = body[i]
        if ch == '(':
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ')':
            depth -= 1
            if depth < 0:
                raise ValueError("Unmatched closing parenthesis in declaration statement")
            buf.append(ch)
            i += 1
            continue

        if depth == 0 and body[i:i + 5].lower() == ' and ':
            rest = body[i + 5:].lstrip()
            current = ''.join(buf).strip()
            if _text_after_is_declaration_start(rest):
                flush()
                premise_mode = False
                i += 5
                continue
            if premise_mode or looks_like_formula(rest):
                flush()
                premise_mode = True
                i += 5
                continue

        if depth == 0 and ch == ',':
            current = ''.join(buf).strip()
            rest = next_nonspace(i + 1)

            # Before ``be/are`` commas are grouped-name separators.  Check
            # this before the general declaration-boundary test: otherwise
            # ``a, b, c be objects`` would be mistaken for three clauses.
            if re.match(
                r'^[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*$',
                current,
            ) and re.match(
                r'^(?:[A-Za-z_][A-Za-z0-9_]*\s*,\s*)*'
                r'[A-Za-z_][A-Za-z0-9_]*\s+(?:be|are)\b',
                rest,
                re.I,
            ):
                buf.append(ch)
                i += 1
                continue

            # A comma followed by another declaration starts a new clause.
            if _text_after_is_declaration_start(rest):
                flush()
                premise_mode = False
                i += 1
                continue

            if premise_mode:
                # Premise clauses may themselves be comma-coordinated.
                flush()
                i += 1
                continue

            # After a completed declaration, a formula starts a new clause.
            # Otherwise retain the comma as part of a natural-language
            # descriptor such as ``reflexive, antisymmetric, transitive``.
            if re.search(r'\b(?:be|are)\b', current, re.I) and looks_like_formula(rest):
                flush()
                premise_mode = True
                i += 1
                continue

        buf.append(ch)
        i += 1

    if depth != 0:
        raise ValueError("Unmatched opening parenthesis in declaration statement")
    flush()
    return items


def _surface_declaration_from_clause(
    clause: str,
    span: SourceSpan,
) -> SurfaceDeclarationClause:
    dc = parse_declaration_clause(clause)
    descriptor = dc.descriptor.strip()
    normalized = dc.normalized_descriptor

    if re.match(r'^(?:in)\b', normalized):
        membership = re.sub(r'^(?:in)\s+', '', descriptor, flags=re.I).strip()
        if not membership:
            raise ElaborationError("membership declaration requires a target set", span)
        declarations = [
            SurfaceDeclaration(
                name=name,
                kind=pl.DeclarationKind.OBJECT,
                descriptor=descriptor,
                attributes={"membership": membership},
                span=span,
            )
            for name in dc.names
        ]
        return SurfaceDeclarationClause(declarations, span, membership)

    attributes: Dict[str, Any] = {}
    kind, type_name = _declaration_kind_from_descriptor(descriptor)

    relation_type_aliases = {
        'equivalence relation': ('reflexive', 'symmetric', 'transitive'),
        'equivalence': ('reflexive', 'symmetric', 'transitive'),
        'strict partial order': ('irreflexive', 'transitive'),
        'strict poset': ('irreflexive', 'transitive'),
        'partial order': ('reflexive', 'antisymmetric', 'transitive'),
        'poset': ('reflexive', 'antisymmetric', 'transitive'),
        'total order': ('reflexive', 'antisymmetric', 'transitive', 'total'),
        'linear order': ('reflexive', 'antisymmetric', 'transitive', 'total'),
    }
    matched_alias = next((alias for alias in relation_type_aliases if re.search(rf'\b{re.escape(alias)}\b', normalized)), None)
    if 'relation' in normalized or matched_alias is not None:
        kind = pl.DeclarationKind.PREDICATE
        arity = 2
        carrier_match = re.search(r'\bon\s+([A-Za-z_][A-Za-z0-9_]*)\s*$', descriptor, re.I)
        if not carrier_match:
            raise ElaborationError(
                f"relation declaration must specify a carrier, e.g. 'relation on X': {clause!r}",
                span,
            )
        attributes["carrier"] = carrier_match.group(1)
        property_words = [
            word.strip().lower()
            for word in re.split(r',|\band\b', normalized)
            if word.strip() and word.strip() not in {
                "a", "an", "any", "the", "relation",
            } and word.strip() != "on " + carrier_match.group(1).lower()
        ]
        properties = list(relation_type_aliases.get(matched_alias, ())) if matched_alias else []
        for property_name in ("reflexive", "irreflexive", "symmetric", "antisymmetric", "asymmetric", "transitive", "total", "connected"):
            if re.search(rf'\b{property_name}\b', normalized, re.I):
                canonical = 'total' if property_name == 'connected' else property_name
                if canonical not in properties:
                    properties.append(canonical)
        if properties:
            attributes["properties"] = tuple(properties)
    elif kind == pl.DeclarationKind.PREDICATE:
        arity = 1 if re.search(r'\bunary\b', normalized) else (
            2 if re.search(r'\bbinary\b', normalized) else None
        )
    elif kind == pl.DeclarationKind.FUNCTION:
        arity = 1 if re.search(r'\bunary\b', normalized) else (
            2 if re.search(r'\bbinary\b', normalized) else None
        )
    else:
        arity = None

    declarations = [
        SurfaceDeclaration(
            name=name,
            kind=kind,
            descriptor=descriptor,
            attributes={
                **attributes,
                **({"arity": arity} if arity is not None else {}),
            },
            span=span,
        )
        for name in dc.names
    ]
    return SurfaceDeclarationClause(declarations, span)


def parse_surface_declaration_statement(
    text: str,
    span: SourceSpan,
) -> Optional[SurfaceDeclarationStatement]:
    """Parse the coordinated surface language beginning with `Let`.

    This is intentionally a small hand-written grammar. It recognizes
    declaration clauses and premise clauses independently; formulas are not
    parsed until elaboration.
    """
    source = text.strip().rstrip('.').strip()
    if not re.match(r'^let\b', source, re.I):
        return None

    body = re.sub(r'^let\s+', '', source, flags=re.I, count=1).strip()
    clauses: List[Any] = []

    such_that = re.search(r'\bsuch\s+that\s*:\s*', body, re.I)
    if such_that:
        declaration_body = body[:such_that.start()].strip().rstrip(',')
        premise_body = body[such_that.end():].strip()
        for item in _split_compound_declaration_items(declaration_body):
            clauses.append(_surface_declaration_from_clause(item, span))
        for formula in split_top_level(premise_body, ' and '):
            if formula.strip():
                clauses.append(SurfacePremiseClause(formula.strip(), span))
        return SurfaceDeclarationStatement(clauses, span)

    for item in _split_compound_declaration_items(body):
        item = item.strip()
        if re.search(r'\b(?:be|are)\b', item, re.I):
            clauses.append(_surface_declaration_from_clause(item, span))
        else:
            for formula in split_top_level(item, ' and '):
                if formula.strip():
                    clauses.append(SurfacePremiseClause(formula.strip(), span))

    return SurfaceDeclarationStatement(clauses, span)



def _surface_clause_to_recipe_clause(clause: SurfaceDeclarationClause) -> DeclarationClause:
    names = [d.name for d in clause.declarations]
    descriptor = clause.declarations[0].descriptor if clause.declarations else ""
    return DeclarationClause(names, is_tuple=False, descriptor=descriptor)


def _declaration_metadata(attributes: Dict[str, Any]) -> tuple:
    return tuple(
        (str(key), value)
        for key, value in sorted(attributes.items(), key=lambda item: item[0])
    )


def elaborate_compound_declaration(entry: 'SurfaceLine', context: '_ElaborationContext') -> Optional[tuple]:
    """Elaborate the coordinated `Let ...` surface AST from left to right.

    Declarations are entered into the elaboration registry before later
    clauses are processed. Membership clauses introduce object declarations
    and ordinary membership premises. Formula clauses are parsed only after
    all declarations preceding them have been registered.

    The returned core representation intentionally uses only the existing
    semantic concepts: declarations plus a formula or formula bundle marked
    as a premise. The kernel never sees a compound-declaration construct.
    """
    statement = entry.declaration_statement
    if statement is None:
        return None

    just = entry.justification_text.strip().lower()
    if just not in ('declaration', 'declare'):
        return None

    declarations: List[pl.Declaration] = []
    formulas: List[fl.Formula] = []

    for clause in statement.clauses:
        if isinstance(clause, SurfaceDeclarationClause):
            recipe_clause = _surface_clause_to_recipe_clause(clause)
            matched = None
            for recipe in context.environment.declaration_recipes:
                matched = recipe.try_match([recipe_clause], 0)
                if matched is not None:
                    break

            if matched is not None:
                consumed, extra_decls, extra_formulas, extra_rules = matched
                if consumed != 1:
                    raise ElaborationError(
                        f"declaration recipe {getattr(recipe, 'name', '<unknown>')!r} "
                        "requires a declaration sequence that is not supported by this surface clause",
                        clause.span or entry.span,
                    )
                for declaration in extra_decls:
                    context.register_declaration(declaration, clause.span or entry.span)
                    declarations.append(declaration)
                formulas.extend(extra_formulas)
                for rule in extra_rules:
                    context.add_extra_rule(rule)
                continue

            for surface_decl in clause.declarations:
                name = surface_decl.name
                if not _IDENTIFIER_RE.match(name):
                    raise ElaborationError(
                        f"invalid declared symbol name: {name!r}",
                        surface_decl.span or entry.span,
                    )

                carrier = surface_decl.attributes.get("carrier")
                if carrier is not None and context.lookup_declaration(carrier) is None:
                    raise ElaborationError(
                        f"declaration of '{name}' refers to '{carrier}', which has not "
                        "been declared yet",
                        surface_decl.span or entry.span,
                    )

                arity = surface_decl.attributes.get("arity")
                metadata = _declaration_metadata(
                    {
                        key: value
                        for key, value in surface_decl.attributes.items()
                        if key not in {"arity"}
                    }
                )
                declaration = pl.Declaration(
                    name=name,
                    kind=surface_decl.kind,
                    arity=arity,
                    type_name=surface_decl.descriptor,
                    metadata=metadata,
                )
                context.register_declaration(declaration, surface_decl.span or entry.span)
                declarations.append(declaration)

            if clause.membership_expression is not None:
                target = clause.membership_expression
                if not target:
                    raise ElaborationError(
                        "membership declaration requires a target expression",
                        clause.span or entry.span,
                    )
                for surface_decl in clause.declarations:
                    formula_text = f"{surface_decl.name} is in {target}"
                    try:
                        formulas.append(context.parse_core_formula(formula_text))
                    except (TypeError, ValueError) as exc:
                        raise ElaborationError(str(exc), clause.span or entry.span) from exc

        elif isinstance(clause, SurfacePremiseClause):
            try:
                formula = context.parse_core_formula(clause.formula)
            except (TypeError, ValueError) as exc:
                raise ElaborationError(str(exc), clause.span or entry.span) from exc
            formulas.append(formula)
        else:
            raise TypeError(f"unknown declaration statement clause: {clause!r}")

    context.register_origin(entry.label, entry.span, "compound declaration")

    if not formulas:
        return (entry.label, None, ('declare', declarations))

    value: Any = formulas[0] if len(formulas) == 1 else formulas
    return (entry.label, value, ('premise', declarations))


def elaborate_typed_declaration(entry: 'SurfaceLine', context: '_ElaborationContext') -> Optional[tuple]:
    """The single, general entry point for every `Let ...` declaration
    line: split into clauses, and for each, try every registered
    `DeclarationRecipe` (from `context.environment.declaration_recipes`,
    populated by whichever theory modules are loaded) before falling back
    to a bare object/predicate/function declaration for whatever no
    recipe recognized. Always returns a result for a `Let ...` line
    (never `None`) -- unlike a typical `line_elaborator`, this doesn't
    decline, because it *is* the declaration path now, not an optional
    override of it; `parse_declaration_prefix` remains as the "such
    that:" premise case and as this function's own per-clause fallback,
    not as a separate thing declaration lines might reach instead.

    Registering a brand new structure type (a group, a ring, ...) is
    exactly: write an `expand` function computing the declarations,
    formulas, and rules a declaration of that type should carry, wrap it
    as a `DeclarationRecipe`, and add it to your module's
    `TheoryEnvironment(declaration_recipes=[...])`. No change here, or to
    any other theory module, is needed.
    """
    just = entry.justification_text.strip().lower()
    if just not in ('declaration', 'declare'):
        return None
    text = entry.formula_text.strip().rstrip('.').strip()
    if not re.match(r'^let\b', text, flags=re.I):
        return None
    if re.search(r'\bsuch\s+that\s*:\s*', text, flags=re.I):
        return None  # "such that:" premises stay on parse_declaration_prefix's original path

    body = re.sub(r'^let\s+', '', text, flags=re.I, count=1)
    clauses = [parse_declaration_clause(c) for c in split_declaration_clauses(body)]

    declarations: List[pl.Declaration] = []
    bundle: List[fl.Formula] = []
    recipes = context.environment.declaration_recipes

    i = 0
    while i < len(clauses):
        matched = None
        for recipe in recipes:
            result = recipe.try_match(clauses, i)
            if result is not None:
                matched = result
                break
        if matched is not None:
            consumed, extra_decls, extra_formulas, extra_rules = matched
            declarations.extend(extra_decls)
            bundle.extend(extra_formulas)
            for rule in extra_rules:
                context.add_extra_rule(rule)
            i += max(consumed, 1)
            continue

        dc = clauses[i]
        if dc.domain is not None:
            # A typed-function clause with no recipe claiming its
            # descriptor: still declare the function itself (so proofs
            # that don't need any extra derived facts aren't forced to
            # find/write a recipe just to name a typed function), just
            # without any bundled range/behavior facts.
            declarations.append(pl.Declaration(name=dc.names[0], kind=pl.DeclarationKind.FUNCTION,
                                                arity=1, type_name=dc.descriptor.strip()))
        else:
            for name in dc.names:
                if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
                    raise ElaborationError(f"Invalid declared symbol name: {name!r}", entry.span)
            kind, type_name = _declaration_kind_from_descriptor(dc.descriptor)
            declarations.extend(pl.Declaration(name=name, kind=kind, type_name=type_name) for name in dc.names)
        i += 1

    context.register_origin(entry.label, entry.span)
    if not bundle:
        return (entry.label, None, ('declare', declarations))
    formula = bundle[0] if len(bundle) == 1 else bundle
    return (entry.label, formula, ('premise', declarations))


def parse_formula(s: str, bound_vars=None, environment: Optional[TheoryEnvironment] = None):
    """Parse a formula from its plain-text notation.

    Recognizes, in this order (see the module docstring's precedence note
    for why order matters):

      1. ``let X be in the domain.`` / ``let X be arbitrary`` -- the special
         "fresh constant" flag formula (see `ProofLogic.SubproofRecord`'s
         docstring for how this nullary-predicate encoding is used by
         UniversalGeneralizationRule)
      2. ``for all x, ...`` / ``forall x, ...`` -- the comma is optional
      3. ``exists x, ...`` / ``there exists x, ...`` -- comma optional
      4. top-level ``if and only if`` / biconditional wording
      5. top-level ``and`` (N-ary: ``A and B and C`` all becomes one `And`)
      6. top-level ``or`` (N-ary, same idea)
      7. a fully parenthesized remainder, e.g. ``(A and B)`` -> unwrap and
         re-parse the inside
      7. ``not ...`` / ``¬...``
      8. ``<->`` / ``<=>`` / ``↔`` / ``iff`` / ``if and only if`` (see the
         module docstring for the "if and only if" caveat)
      10. ``->`` / ``implies`` / ``if X then Y``
      11. ``pred(arg, arg, ...)`` -- an atomic predicate with arguments
      12. (fallback) a bare atomic proposition, `AtomicFormula(s, [])`

    `environment` supplies theory-specific formula syntax (e.g. SetTheory's
    "a is in X", NumberTheory's "a|n") via its `nested_formula_parsers`,
    tried after every connective in the list above has had a chance to
    split the string, but before the final atomic-predicate/bare-atomic
    fallback -- *not* before, or a theory phrase containing a connective
    keyword as a substring risks swallowing more than intended (e.g.
    checking "a|n" against the whole of "if a|n then b" before "if...then"
    has split it apart would wrongly capture "if a" as part of a term).
    Defaults to the cached `default_theory_environment()` when omitted,
    and is threaded through every recursive call in this function, so
    theory syntax is recognized in nested positions too -- e.g. the "a|n"
    inside "if a|n then b" -- not only when a formula happens to consist
    of nothing else. (`environment.formula_parsers`, by contrast, is only
    consulted by `_ElaborationContext.parse_surface_expression` at the top
    of a single proof line, since some of its results carry extra
    structure -- like SetTheory's raw subset operands -- that only the
    elaborator that asked for them knows how to use.)

    Examples::

        >>> repr(parse_formula('A and B'))
        '(A() ∧ B())'
        >>> repr(parse_formula('for all x, P(x) -> Q(x)'))
        '(∀x. (P(x) → Q(x)))'
        >>> repr(parse_formula('A <-> B'))
        '(A() ↔ B())'
        >>> repr(parse_formula('let c be in the domain'))
        'c()'
    """
    if bound_vars is None:
        bound_vars = set()
    if environment is None:
        environment = _cached_default_environment()
    s = s.strip()

    m = re.match(r'^let\s+([A-Za-z_][A-Za-z0-9_]*)\s+be\s+(?:in\s+the\s+domain|arbitrary)\.?$', s, flags=re.I)
    if m:
        return fl.AtomicFormula(m.group(1), [])

    m = re.match(r'^(?:for all|forall)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$', s, flags=re.I)
    if m:
        var = m.group(1)
        body = m.group(2)
        return fl.ForAll(var, parse_formula(body, bound_vars | {var}, environment))

    m = re.match(r'^(?:exists|there exists)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$', s, flags=re.I)
    if m:
        var = m.group(1)
        body = m.group(2)
        return fl.Exists(var, parse_formula(body, bound_vars | {var}, environment))

    parts = split_top_level(s, ' if and only if ')
    if len(parts) > 1:
        return fl.Iff(parse_formula(parts[0], bound_vars, environment), parse_formula(parts[1], bound_vars, environment))

    parts = split_top_level(s, ' and ')
    if len(parts) > 1:
        return fl.And(*[parse_formula(p, bound_vars, environment) for p in parts])

    parts = split_top_level(s, ' or ')
    if len(parts) > 1:
        return fl.Or(*[parse_formula(p, bound_vars, environment) for p in parts])

    if s.startswith('(') and s.endswith(')'):
        depth = 0
        balanced = True
        for i, ch in enumerate(s):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    balanced = False
                    break
        if balanced and depth == 0:
            return parse_formula(s[1:-1], bound_vars, environment)

    m = re.match(r'^(?:not|¬)\s+(.*)$', s, flags=re.I)
    if m:
        return fl.Not(parse_formula(m.group(1), bound_vars, environment))

    for sep in [' <-> ', ' <=> ', ' ↔ ']:
        if sep in s:
            a, b = split_top_level(s, sep)
            return fl.Iff(parse_formula(a, bound_vars, environment), parse_formula(b, bound_vars, environment))

    parts = split_top_level(s, ' iff ')
    if len(parts) > 1:
        return fl.Iff(parse_formula(parts[0], bound_vars, environment), parse_formula(parts[1], bound_vars, environment))

    # NOTE: "if and only if" contains the literal substring " and ", so for
    # an unparenthesized formula the top-level `and`-split above (step 4)
    # will normally have already fired on that embedded "and" before
    # control ever reaches this point -- see the module docstring. This
    # check is not dead code (a formula like "(A) if and only if (B)",
    # where "and" ends up inside parens relative to nothing at this
    # recursion level, can still reach here), but it is not the safety net
    # for the general case it might look like.
    m = re.search(r'\bif and only if\b', s, flags=re.I)
    if m:
        a, b = re.split(r'\bif and only if\b', s, maxsplit=1, flags=re.I)
        return fl.Iff(parse_formula(a, bound_vars, environment), parse_formula(b, bound_vars, environment))

    # Implication, checked before '=' (see below) for the same reason
    # 'and'/'or' are checked even earlier, above: '->' is a connective
    # between Formulas and should bind looser than '=', a relation
    # between Terms -- "f(a) = b -> c" has to mean "(f(a) = b) -> c",
    # since '='s operands must be Terms and only the left side, on its
    # own, is one. Checking '=' first used to split that on its '=' and
    # try to parse "f(a)" and "b -> c" as Terms, silently producing
    # nonsense before the loud-failure fallback existed, and a clear but
    # misleading "Unrecognized term syntax: 'f(a) = b'"-style error
    # after it -- correct in that it refused to guess, but pointing at
    # the wrong problem (a term that was never supposed to be parsed as
    # one at all, rather than the real fix: check '->' first).
    m = re.search(r'\s->\s', s)
    if m:
        a, b = s.split('->', 1)
        return fl.Implies(parse_formula(a, bound_vars, environment), parse_formula(b, bound_vars, environment))

    m = re.search(r'\bimplies\b', s, flags=re.I)
    if m:
        a, b = re.split(r'\bimplies\b', s, maxsplit=1, flags=re.I)
        return fl.Implies(parse_formula(a, bound_vars, environment), parse_formula(b, bound_vars, environment))

    m = re.match(r'^if\s+(.*?)\s+then\s+(.*)$', s, flags=re.I)
    if m:
        a, b = m.group(1), m.group(2)
        return fl.Implies(parse_formula(a, bound_vars, environment), parse_formula(b, bound_vars, environment))

    # Equality between two Terms (not Formulas -- see FormulaLogic.Equals).
    # Checked here, after the iff-family and after '->'/'implies'/'if
    # ... then' above, because '<=>' contains a literal '=' -- if this
    # ran before the iff-family it would wrongly split "A <=> B" on the
    # '=' buried inside "<=>" the same way an unguarded 'and'-split would
    # mis-handle "if and only if" (see the module docstring). Requires
    # spaces around '=', matching every other binary connective in this
    # grammar (' -> ', ' <-> ', etc.); only a single '=' is recognized --
    # "a = b = c" isn't supported (write "a = b and b = c" instead).
    parts = split_top_level(s, ' = ')
    if len(parts) == 2:
        return fl.Equals(parse_term(parts[0], bound_vars, environment), parse_term(parts[1], bound_vars, environment))

    for nested_parser in environment.nested_formula_parsers:
        formula = nested_parser(s, bound_vars)
        if formula is not None:
            return formula

    matched = _match_applied_symbol(s)
    if matched:
        pred, args_str = matched
        return fl.AtomicFormula(pred, _parse_arg_list(args_str, bound_vars, environment))

    if _BARE_IDENTIFIER_RE.match(s):
        return fl.AtomicFormula(s, [])

    raise ValueError(
        f"Unrecognized formula syntax: {s!r}. Expected a logical "
        f"connective, an atomic predicate like 'P(x)', a simple atomic "
        f"proposition name, or syntax registered by an imported theory "
        f"module -- not a raw, unrecognized expression silently treated "
        f"as an opaque atom."
    )


def parse_justification(s: str):
    """Parse a proof line's parenthesized justification text into the
    small tuple `ProofLogic.ProofValidator` expects (see ProofLogic.py's
    module docstring for the five possible shapes).

    Two-phase strategy, and why the order is soundness-relevant:

      **Phase 1 -- explicit rule citations.** First tries to match
      ``"<rule name> from subproof below"`` or ``"<rule name> from
      <label>, <label>, ..."``. If either matches, the rule name is
      resolved via keyword checks (below) and this function returns
      immediately -- it never falls through to phase 2 for text that
      matched a citation pattern, even if that text also happens to
      contain a keyword like "assume" somewhere in the rule name.

      **Phase 2 -- bare keyword fallback.** Only reached when the text
      *isn't* shaped like a rule citation at all (no trailing "from ...").
      Checks for "arbitrary"/"fresh variable", "premise", "assume"/"assum",
      "axiom", in that order.

      Running phase 1 first is what stops a rule-citation phrase that
      happens to contain "assum" as a substring (or any of the other
      phase-2 keywords) from being misread as a bare assumption. Bare
      assumptions are also independently restricted to only the first
      line of a subproof by `ProofValidator._validate_assume_or_arbitrary`
      -- the two checks are complementary, not redundant: phase ordering
      here stops a rule citation from being *misclassified* as 'assume' in
      the first place; the validator's position check stops a genuine
      'assume' tag from being legal anywhere but line 0 of a subproof.

    Rule-name resolution is by substring keyword, not exact phrase
    matching, so proofs can use fairly natural phrasing ("Conjunction
    Introduction", "And Intro", "Addition" all work for the same rule via
    different keyword checks) as long as the checks below are read in
    order -- earlier checks can shadow later ones. In particular:
    any rule name containing "equiv" (checked while looking for De
    Morgan's/Distribution/Double-Negation/generic-equivalence phrasing)
    is routed to `PropositionalEquivalenceRule` *before* the later,
    more specific-looking ``'conditional' in rule_name and 'equiv' in
    rule_name`` check further down is ever reached -- so that later check,
    which returns `BiconditionalEliminationRule`, is unreachable for any
    input: every string that would satisfy it already satisfied the
    earlier, more general "contains 'equiv'" check first. It's left as-is
    (removing it changes nothing about what actually runs) but is worth
    knowing about if you're trying to trace how a given justification
    phrase resolves. "Conditional Elimination" (no "equiv") is unaffected
    and does still resolve to `BiconditionalEliminationRule` via the
    'conditional'+'elimin' check below it.

    Examples::

        >>> parse_justification('Premise')
        ('premise',)
        >>> parse_justification('Modus Ponens from 1,2')
        ('rule', ModusPonensRule(), ['1', '2'])
        >>> parse_justification('Proof by Contradiction from subproof below')
        ('rule_below', ProofByContradictionRule())
    """
    s = s.strip()
    if not s:
        raise ValueError("Justification text is required for every proof line")
    s_low = s.lower()

    m = re.match(r'^(.*)from\s+subpro+f\s+below$', s_low)
    if m:
        rule_name = m.group(1).strip()
        if 'conditional' in rule_name and 'elimin' not in rule_name:
            return ('rule_below', pl.ConditionalIntroductionRule())
        if 'contradict' in rule_name or 'proof by contradiction' in rule_name or 'reductio' in rule_name:
            return ('rule_below', pl.ProofByContradictionRule())
        if 'general' in rule_name:
            return ('rule_below', pl.UniversalGeneralizationRule())
        raise ValueError(f"Unknown inference rule '{rule_name}' in justification")

    m_hybrid = re.match(r'^(.*)from\s+([0-9]+(?:\.[A-Za-z0-9_]+)*(?:\s*(?:,|and)\s*[0-9]+(?:\.[A-Za-z0-9_]+)*)*)\s*,?\s+subproofs?\s+below$', s_low)
    if m_hybrid:
        base_refs = re.sub(r'\s+and\s+', ', ', m_hybrid.group(2).strip())
        base = f"{m_hybrid.group(1).strip()} from {base_refs}"
        parsed = parse_justification(base)
        if not isinstance(parsed, tuple) or len(parsed) != 3 or parsed[0] != 'rule':
            raise ValueError(f"Invalid hybrid subproof justification: '{s}'")
        return ('rule_hybrid', parsed[1], parsed[2])

    if re.search(r'\bfrom\s*$', s_low):
        raise ValueError(f"Malformed rule justification: {s}")

    m = re.match(r'^(.*)from\s+([0-9]+(?:\.[A-Za-z0-9_]+)*(?:\s*(?:,|and)\s*[0-9]+(?:\.[A-Za-z0-9_]+)*)*)$', s_low)
    if m:
        rule_name = m.group(1).strip()
        indices = [token.strip() for token in re.split(r'\s*(?:,|and)\s*', m.group(2)) if token.strip()]

        if 'univ' in rule_name and 'instant' in rule_name:
            return ('rule', pl.UniversalInstantiationRule(), indices)
        if 'general' in rule_name:
            return ('rule', pl.UniversalGeneralizationRule(), indices)
        if 'exist' in rule_name and ('intro' in rule_name or 'general' in rule_name):
            return ('rule', pl.ExistentialIntroductionRule(), indices)
        if 'exist' in rule_name and ('elim' in rule_name or 'instant' in rule_name):
            return ('rule', pl.ExistentialEliminationRule(), indices)
        if ('disjunction' in rule_name and 'intro' in rule_name) or 'addition' in rule_name:
            return ('rule', pl.DisjunctionIntroductionRule(), indices)
        if ('disjunction' in rule_name and 'elim' in rule_name) or 'cases' in rule_name:
            return ('rule', pl.DisjunctionEliminationRule(), indices)
        if 'conjunction' in rule_name and 'elimin' in rule_name:
            return ('rule', pl.ConjunctionEliminationRule(), indices)
        if 'conjunction' in rule_name and 'intro' in rule_name:
            return ('rule', pl.ConjunctionIntroductionRule(), indices)
        if 'biconditional' in rule_name and 'intro' in rule_name:
            return ('rule', pl.BiconditionalIntroductionRule(), indices)
        if 'biconditional' in rule_name and 'elim' in rule_name:
            return ('rule', pl.BiconditionalEliminationRule(), indices)
        if 'modus' in rule_name and 'ponens' in rule_name:
            return ('rule', pl.ModusPonensRule(), indices)
        if 'modus' in rule_name and 'tollens' in rule_name:
            return ('rule', pl.ModusTollensRule(), indices)
        if 'disjunctive' in rule_name and 'syllogism' in rule_name:
            return ('rule', pl.DisjunctiveSyllogismRule(), indices)
        if 'hypothetical' in rule_name and 'syllogism' in rule_name:
            return ('rule', pl.HypotheticalSyllogismRule(), indices)
        if 'explosion' in rule_name or 'ex falso' in rule_name:
            return ('rule', pl.ExplosionRule(), indices)
        if 'reiteration' in rule_name or 'reiterate' in rule_name:
            return ('rule', pl.ReiterationRule(), indices)
        if 'substitution' in rule_name or 'leibniz' in rule_name:
            return ('rule', pl.LeibnizSubstitutionRule(), indices)
        if 'relation' in rule_name and 'irreflexiv' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('RelationIrreflexivity'), indices)
        if 'relation' in rule_name and 'reflexiv' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('RelationReflexivity'), indices)
        if 'relation' in rule_name and 'antisymmetr' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('RelationAntisymmetry'), indices)
        if 'relation' not in rule_name and 'antisymmetr' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('RelationAntisymmetry'), indices)
        if 'relation' in rule_name and 'asymmetr' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('RelationAsymmetry'), indices)
        if 'relation' in rule_name and 'symmetr' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('RelationSymmetry'), indices)
        if 'relation' in rule_name and ('transitiv' in rule_name):
            return ('rule', pl.NamedRulePlaceholder('RelationTransitivity'), indices)
        if 'relation' in rule_name and ('total' in rule_name or 'connected' in rule_name):
            return ('rule', pl.NamedRulePlaceholder('RelationTotality'), indices)
        if 'symmetry' in rule_name:
            return ('rule', pl.SymmetryRule(), indices)
        if 'transitivity' in rule_name:
            return ('rule', pl.TransitivityRule(), indices)
        if 'quotient' in rule_name and ('defin' in rule_name or 'property' in rule_name):
            # Like Induction below, resolved by name against whatever
            # Proof.rules this justification is actually checked against --
            # see NumberTheory.QuotientDefiningPropertyRule.
            return ('rule', pl.NamedRulePlaceholder('QuotientDefiningProperty'), indices)
        if 'quotient' in rule_name and 'uniq' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('QuotientUniqueness'), indices)
        if 'set' in rule_name and 'equal' in rule_name:
            return ('rule', pl.NamedRulePlaceholder('SetEquality'), indices)
        if 'induction' in rule_name:
            # Unlike every other rule here, Induction needs per-proof
            # configuration (which type's Zero/Succ/predicate) that the
            # justification text can't supply -- see NamedRulePlaceholder
            # in ProofLogic.py for how this gets resolved against whatever
            # Type was actually combined into this Proof's `rules=` list.
            return ('rule', pl.NamedRulePlaceholder('Induction'), indices)
        # Parenthesized here to make the actual grouping explicit -- this
        # is one 4-way OR (morgan | distribut | (double AND negation) |
        # equiv), exactly matching Python's implicit `and`-before-`or`
        # precedence from the original unparenthesized form, just spelled
        # out. Because the last arm matches on the bare substring "equiv",
        # ANY rule name containing "equiv" -- including "conditional
        # equivalence" -- resolves here; see this function's docstring.
        if ('morgan' in rule_name or 'distribut' in rule_name or
                ('double' in rule_name and 'negation' in rule_name) or 'equiv' in rule_name):
            return ('rule', pl.PropositionalEquivalenceRule(), indices)
        if 'conditional' in rule_name and 'equiv' in rule_name:
            # Unreachable: every rule_name that would satisfy this line already
            # satisfied the broader "'equiv' in rule_name" arm above and
            # returned before reaching here. Left in place rather than
            # deleted so the historical intent (an explicit alias for
            # "Conditional Equivalence") stays visible; see the docstring.
            return ('rule', pl.BiconditionalEliminationRule(), indices)
        if 'conditional' in rule_name and 'elimin' in rule_name:
            return ('rule', pl.BiconditionalEliminationRule(), indices)
        if 'conditional' in rule_name or 'conditional introduction' in rule_name or 'conditional-intro' in rule_name:
            return ('rule', pl.ConditionalIntroductionRule(), indices)
        if 'contradict' in rule_name or 'proof by contradiction' in rule_name or 'reductio' in rule_name:
            return ('rule', pl.ProofByContradictionRule(), indices)

        raise ValueError(f"Unknown inference rule '{rule_name}' in justification")

    if 'arbitrary' in s_low or 'fresh variable' in s_low:
        return ('arbitrary',)
    if 'set property' in s_low:
        return ('rule', pl.NamedRulePlaceholder('EmptySetProperty'), [])
    if 'reflexivity' in s_low:
        # The one rule with premise_arity 0: no 'from ...' clause to match
        # in Phase 1 at all, so it's recognized here as a bare keyword
        # instead, the same way 'premise'/'assume'/'axiom' are -- but
        # still resolves to a genuine ('rule', ReflexivityRule(), [])
        # citation, not a new tag of its own.
        return ('rule', pl.ReflexivityRule(), [])
    if 'declare' in s_low or 'declaration' in s_low:
        return ('declare',)
    if 'premise' in s_low:
        return ('premise',)
    if 'assume' in s_low or 'assum' in s_low or s_low == 'case':
        return ('assume',)
    if 'axiom' in s_low:
        return ('axiom',)

    # Last resort: a bare phrase naming a promoted theorem with no
    # premises of its own, e.g. "(The empty set subset theorem)" citing
    # a `TheoremRule` built by `ProofLogic.promote_theorem`. Preserves the
    # original casing/spacing of `s` (not `s_low`) since that is exactly
    # what the theorem was promoted under. Deferred to validation the same
    # way "Induction"/"EmptySetProperty" already are: if no rule with this
    # name is registered for the proof, that is where the failure surfaces,
    # with a clear message naming the missing rule.
    #
    # Guarded against text containing "from" or "subproof": every genuine
    # rule-citation shape above already tried to match those and failed,
    # so text that still contains either word here is far more likely a
    # malformed citation (e.g. "from subproof above" instead of "below")
    # than an actual theorem title -- and should fail loudly and
    # immediately, not be swallowed into a placeholder that only fails
    # later, with a confusing "no rule named ... is registered" message.
    if 'from' not in s_low and 'subproof' not in s_low:
        return ('rule', pl.NamedRulePlaceholder(s), [])

    raise ValueError(f"Invalid justification format: '{s}'")


def _split_trailing_parenthetical(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Split a line's remainder into ``(formula_text, justification_text)``
    by finding the matching-depth ``(`` for the line's *final* ``)`` --
    i.e. the outermost, right-most parenthesized group -- rather than the
    first ``(`` found by a naive scan, so a formula that itself contains
    parentheses (``"(A and B) and not (if A then B)"``) doesn't get split
    in the wrong place. Returns `(None, None)` if `text` doesn't end in
    `)` at all (no justification present).

    Examples::

        >>> _split_trailing_parenthetical("A -> B (Modus Ponens from 1, 2)")
        ('A -> B', 'Modus Ponens from 1, 2')
        >>> _split_trailing_parenthetical("(A or B) and C. (Premise)")
        ('(A or B) and C', 'Premise')
        >>> _split_trailing_parenthetical("no trailing paren")
        (None, None)
    """
    if not text.endswith(')'):
        return None, None
    depth = 0
    for pos in range(len(text) - 1, -1, -1):
        ch = text[pos]
        if ch == ')':
            depth += 1
        elif ch == '(':
            depth -= 1
            if depth == 0:
                formula_text = text[:pos].strip().rstrip('.')
                just_text = text[pos + 1:-1].strip()
                return formula_text, just_text
    return None, None


@dataclass
class _LogicalSourceLine:
    text: str
    start_line: int
    end_line: int
    original_text: str


def _comment_preserving_newlines(match: re.Match) -> str:
    return ''.join('\n' if ch == '\n' else ' ' for ch in match.group(0))


def _prepare_surface_lines(text: str) -> Tuple[List[_LogicalSourceLine], List[str]]:
    """Remove comments/headings and join wrapped physical lines.

    Unlike the old direct parser, this retains physical source line numbers so
    elaboration and validation errors can be mapped back to the user's text.
    """
    cleaned = re.sub(r'\(\*.*?\*\)', _comment_preserving_newlines, text, flags=re.S)
    raw_lines: List[str] = []
    physical = []
    for line_number, line in enumerate(cleaned.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        raw_lines.append(line)
        if _is_theory_directive(stripped):
            continue
        physical.append((line_number, line))

    logical: List[_LogicalSourceLine] = []
    for line_number, line in physical:
        stripped = line.strip()
        starts_item = (
            _LABELED_LINE_RE.match(stripped)
            or _BEGIN_SUBPROOF_RE.match(stripped)
            or _END_SUBPROOF_RE.match(stripped)
        )
        if starts_item or not logical:
            logical.append(_LogicalSourceLine(line, line_number, line_number, line))
        else:
            previous = logical[-1]
            logical[-1] = _LogicalSourceLine(
                previous.text + ' ' + stripped,
                previous.start_line,
                line_number,
                previous.original_text + '\n' + line,
            )
    return logical, raw_lines


def _surface_span(item: _LogicalSourceLine, label: Optional[str] = None) -> SourceSpan:
    return SourceSpan(item.start_line, item.end_line, item.original_text, label)


def _line_label(item: _LogicalSourceLine) -> Optional[str]:
    match = _LABELED_LINE_RE.match(item.text.strip())
    return match.group(1) if match else None


def _is_descendant_label(label: Optional[str], parent: str) -> bool:
    return bool(label and label.startswith(parent + '.'))


def _implicit_block_end(lines: List[_LogicalSourceLine], start: int, parent_label: str) -> int:
    """End index of a descendant-label block, respecting explicit nesting."""
    index = start
    explicit_depth = 0
    while index < len(lines):
        stripped = lines[index].text.strip()
        if _BEGIN_SUBPROOF_RE.match(stripped):
            explicit_depth += 1
            index += 1
            continue
        if _END_SUBPROOF_RE.match(stripped):
            if explicit_depth > 0:
                explicit_depth -= 1
                index += 1
                continue
            break
        if explicit_depth == 0 and not _is_descendant_label(_line_label(lines[index]), parent_label):
            break
        index += 1
    return index


def _parse_surface_sequence(
    lines: List[_LogicalSourceLine],
    start: int = 0,
    *,
    stop_at_end: bool = False,
) -> Tuple[List[Any], int]:
    entries: List[Any] = []
    index = start

    while index < len(lines):
        item = lines[index]
        stripped = item.text.strip()

        if _END_SUBPROOF_RE.match(stripped):
            if not stop_at_end:
                raise ElaborationError("unexpected 'end subproof'", _surface_span(item))
            return entries, index + 1

        if _BEGIN_SUBPROOF_RE.match(stripped):
            body, next_index = _parse_surface_sequence(lines, index + 1, stop_at_end=True)
            end_item = lines[next_index - 1]
            entries.append(SurfaceSubproof(
                body,
                SourceSpan(item.start_line, end_item.end_line, item.original_text),
                implicit=False,
            ))
            index = next_index
            continue

        match = _LABELED_LINE_RE.match(stripped)
        label = match.group(1) if match else None
        rest = match.group(2) if match else stripped

        if _BEGIN_SUBPROOF_RE.match(rest):
            body, next_index = _parse_surface_sequence(lines, index + 1, stop_at_end=True)
            end_item = lines[next_index - 1]
            entries.append(SurfaceSubproof(
                body,
                SourceSpan(item.start_line, end_item.end_line, item.original_text, label),
                label=label,
                implicit=False,
            ))
            index = next_index
            continue

        formula_text, justification_text = _split_trailing_parenthetical(rest)
        if formula_text is None:
            raise ElaborationError(
                "missing explicit justification: expected a final parenthesized justification",
                _surface_span(item, label),
            )

        line_span = _surface_span(item, label)
        declaration_statement = None
        if justification_text.strip().lower() in {"declaration", "declare"}:
            declaration_statement = parse_surface_declaration_statement(formula_text, line_span)
        line = SurfaceLine(
            label=label,
            formula_text=formula_text,
            justification_text=justification_text,
            span=line_span,
            declaration_statement=declaration_statement,
        )
        index += 1

        # Explicit blocks immediately below a rule line belong to that line.
        if 'below' in justification_text.lower():
            while index < len(lines) and _BEGIN_SUBPROOF_RE.match(lines[index].text.strip()):
                begin_item = lines[index]
                body, next_index = _parse_surface_sequence(lines, index + 1, stop_at_end=True)
                end_item = lines[next_index - 1]
                line.subproofs.append(SurfaceSubproof(
                    body,
                    SourceSpan(begin_item.start_line, end_item.end_line, begin_item.original_text),
                    implicit=False,
                ))
                index = next_index

            # Natural proof files may omit begin/end and use dotted descendant
            # labels as the subproof boundary.
            if not line.subproofs and label and index < len(lines):
                next_label = _line_label(lines[index])
                if _is_descendant_label(next_label, label):
                    end = _implicit_block_end(lines, index, label)
                    body, consumed = _parse_surface_sequence(lines[index:end], 0)
                    if consumed != end - index:
                        raise ElaborationError("could not determine implicit subproof boundary", line.span)
                    span = SourceSpan(
                        lines[index].start_line,
                        lines[end - 1].end_line,
                        '\n'.join(x.original_text for x in lines[index:end]),
                        label,
                    )
                    line.subproofs.append(SurfaceSubproof(body, span, label=label, implicit=True))
                    index = end

        entries.append(line)

    if stop_at_end:
        span = _surface_span(lines[start - 1]) if start > 0 else None
        raise ElaborationError("Unterminated subproof block", span)
    return entries, index


def parse_surface_proof(text: str) -> SurfaceProof:
    """Parse proof text without lowering natural-language proof constructs."""
    logical_lines, raw_lines = _prepare_surface_lines(text)
    entries, consumed = _parse_surface_sequence(logical_lines)
    if consumed != len(logical_lines):
        raise ElaborationError("not all proof lines were consumed")
    return SurfaceProof(entries=entries, raw_lines=raw_lines, source_text=text)


_EXISTENCE_JUSTIFICATION_RE = re.compile(r'^existence\s+from\s+(.+)$', re.IGNORECASE)
_DEFINE_PREFIX_RE = re.compile(r'^define\s+(.+)$', re.IGNORECASE)
_NAME_EQUALS_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$')


def _split_and_clauses(s: str) -> List[str]:
    """Paren-aware split on ', and ' / ' and ' -- a simpler cousin of
    `split_declaration_clauses` above (no repeated keyword to strip,
    since 'Define' isn't repeated the way 'let' can be)."""
    parts: List[str] = []
    depth = 0
    buf: List[str] = []
    i, n = 0, len(s)
    seps = (', and ', ' and ')
    while i < n:
        ch = s[i]
        if ch == '(':
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ')':
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if depth == 0:
            sep = next((c for c in seps if s.startswith(c, i)), None)
            if sep:
                parts.append(''.join(buf).strip())
                buf = []
                i += len(sep)
                continue
        buf.append(ch)
        i += 1
    if buf:
        parts.append(''.join(buf).strip())
    return [p for p in parts if p]


def try_elaborate_existence(entry: 'SurfaceLine', context: '_ElaborationContext') -> Optional[tuple]:
    """``Define z = ..., and y = ... (Existence from L)``: checked sugar
    for naming a witness off an existential at label L, without spelling
    out a full `ExistentialEliminationRule` subproof each time.

    This is sound without that subproof structure for a reason worth
    spelling out, since it's not obvious on its face: `z` is declared
    through the *ordinary* declaration pathway (`('declare', [...])`,
    exactly like any `Let z be ...` line), and declarations are already
    scoped to the subproof (and its descendants) they're declared in --
    a symbol declared inside a subproof is already invisible once that
    subproof closes, the same as any other declared symbol, because
    undeclared-symbol checking is unconditional (see `Proof`'s validator).
    So the "fresh name, can't escape its subproof" discipline that makes
    formal existential elimination sound falls out of the *existing*,
    already-tested declaration-scoping machinery for free -- this
    function doesn't add any new scope tracking, only the part that *is*
    new: instantiating the existential's body at the chosen name and
    making that the declaration's own citable content.

    Only the *first* `NAME = ...` clause is treated as the witness (must
    match label `L`'s existential structurally in count -- there's
    exactly one bound variable to name). Every later clause (like `y =
    f(z)` here) is an ordinary definition: the right-hand side is parsed
    (so a typo is still caught) but not otherwise checked against
    anything, and becomes a plain citable equation. The witness clause's
    own right-hand side (`min(X)`) is treated the same way -- parsed, but
    intentionally *not* required to connect to any axiom about `min`;
    it's documentation of where the name came from, not a separately
    meaningful term. If a future proof wants `min(X)` to be reusable and
    independently meaningful on its own (not just as this one-time naming
    convenience), that's a different, larger feature -- a real choice
    function / definite-description mechanism -- not this one.
    """
    m_just = _EXISTENCE_JUSTIFICATION_RE.match(entry.justification_text.strip())
    if not m_just:
        return None
    citation_label = m_just.group(1).strip()

    m_define = _DEFINE_PREFIX_RE.match(entry.formula_text.strip().rstrip('.').strip())
    if not m_define:
        raise ElaborationError(
            "'Existence' expects a line of the form 'Define NAME = ...'", entry.span,
        )
    clauses = _split_and_clauses(m_define.group(1))
    if not clauses:
        raise ElaborationError("'Define' with nothing to define", entry.span)

    if citation_label not in context.formula_by_label:
        raise ElaborationError(f"'Existence' cites unknown label {citation_label!r}", entry.span)
    cited_formula = context.formula_by_label[citation_label]
    if not isinstance(cited_formula, fl.Exists):
        raise ElaborationError(
            f"'Existence from {citation_label}' needs an existential formula at that "
            f"label to name a witness from, not {cited_formula!r}", entry.span,
        )

    m_witness = _NAME_EQUALS_RE.match(clauses[0])
    if not m_witness:
        raise ElaborationError(f"Invalid 'Define' clause: {clauses[0]!r}", entry.span)
    witness_name = m_witness.group(1)
    parse_term(m_witness.group(2), set())  # parsed to catch typos; see docstring above

    declarations = [pl.Declaration(name=witness_name, kind=pl.DeclarationKind.OBJECT,
                                    type_name="existential witness")]
    witness_term = tl.ConstantTerm(witness_name, witness_name)
    bundle: List[fl.Formula] = [fl.substitute_in_formula(cited_formula.body, cited_formula.var, witness_term)]

    for clause in clauses[1:]:
        m = _NAME_EQUALS_RE.match(clause)
        if not m:
            raise ElaborationError(f"Invalid 'Define' clause: {clause!r}", entry.span)
        name, expr_text = m.group(1), m.group(2)
        declarations.append(pl.Declaration(name=name, kind=pl.DeclarationKind.OBJECT, type_name="definition"))
        expr_term = parse_term(expr_text, set())
        bundle.append(fl.Equals(tl.ConstantTerm(name, name), expr_term))

    context.register_origin(entry.label, entry.span)
    formula = bundle[0] if len(bundle) == 1 else bundle
    # 'premise', not 'declare', for the same reason OrderTheory's poset
    # declaration uses it: a list/bundle of formulas at one label is only
    # accepted by the validator under 'premise' (see
    # `Proof._validate_line`'s `isinstance(phi, list)` branch); 'declare'
    # requires `phi` to be `None` or a single `Formula`. Used uniformly
    # here (not just when `len(bundle) > 1`) so a one-clause `Define`
    # doesn't silently behave differently from a multi-clause one.
    return (entry.label, formula, ('premise', declarations))


def default_theory_environment() -> TheoryEnvironment:
    """The default surface language: base logic plus every theory module
    that happens to be importable, currently set theory and number theory.

    Each theory is optional and imported independently, so a checkout
    missing one module still gets the rest -- and a theory that itself
    extends another (`NumberTheory` extends `SetTheory`, per its own
    `NUMBER_THEORY_ENVIRONMENT`) can be composed with that other theory
    again here without duplicating anything: `Proof.__init__` merges
    `required_rules`/`required_axioms`/`required_declarations` by identity
    (rule type+name, axiom structural equality, declaration name), so a
    theory reachable through more than one path is just a harmless no-op
    the second time.
    """
    environment = TheoryEnvironment(line_elaborators=[elaborate_compound_declaration, elaborate_typed_declaration, try_elaborate_existence],
                                     rules=[pl.AlgebraRule()])
    try:
        import SyLoPy.source.SetTheory as st
        environment = environment.extended(st.SET_THEORY_ENVIRONMENT)
    except ImportError:
        pass
    try:
        import SyLoPy.source.NumberTheory as numt
        environment = environment.extended(numt.NUMBER_THEORY_ENVIRONMENT)
    except ImportError:
        pass
    try:
        import SyLoPy.source.OrderTheory as ot
        environment = environment.extended(ot.ORDER_THEORY_ENVIRONMENT)
    except ImportError:
        pass
    try:
        import SyLoPy.source.DiscreteMath as dm
        environment = environment.extended(dm.DISCRETE_MATH_ENVIRONMENT)
    except ImportError:
        pass
    return environment


class _ElaborationContext:
    def __init__(self, environment: TheoryEnvironment):
        self.environment = environment
        self.origin_by_label: Dict[str, CoreOrigin] = {}
        # Rules a `line_elaborator` constructs *while elaborating a specific
        # line* -- as opposed to `environment.rules`, which is fixed before
        # any proof text is even parsed. This exists for rules that must be
        # parametrized with symbol names a particular proof happens to
        # declare (e.g. OrderTheory's `WellOrderingRule(carrier_symbol)`,
        # built only once a `(W, <)`-shaped declaration names a carrier),
        # the same way `NatThry.NAT_TYPE` parametrizes `InductionRule` with
        # its fixed `Nat`/`Zero`/`Succ` symbols -- except here the symbols
        # aren't fixed, so the rule can't be built until elaboration sees
        # the declaration that names them. See `elaborate_proof`, which
        # merges these into the final `ElaboratedEntries.required_rules`.
        self.extra_rules: List[Any] = []
        self.declarations = pl.DeclarationScope(initial=list(environment.declarations))
        # `ProofContext` integration (see todos.txt, "ProofContext
        # integration" project, phase 2): the authoritative lexical scope
        # this elaborator is migrating *towards*. For now it is populated
        # alongside `self.declarations` above -- via `register_declaration`
        # below -- but nothing yet *reads* from it, so this cannot change
        # elaboration behavior. Seeded from `self.declarations.declarations_here()`
        # rather than `environment.declarations` directly because the latter
        # can contain literal duplicate `Declaration`s (e.g. SetTheory's
        # vocabulary reachable both directly and through NumberTheory's own
        # `.extended(SET_THEORY_ENVIRONMENT)`); `DeclarationScope.__init__`
        # already resolves that via its "skip a compatible duplicate" rule,
        # so reusing its result avoids re-implementing that same leniency
        # here and keeps the two structures declared-in-lockstep from the
        # start. `ProofContext.declare()` has no such leniency and would
        # raise `DuplicateBindingError` on a literal repeat.
        self.context = pc.ProofContext()
        for declaration in self.declarations.declarations_here():
            self.context.declare(declaration)
        # Populated by `elaborate_entry` as it goes, label -> that label's
        # resulting core formula (or bundle). See `elaborate_entry`'s
        # docstring for why this exists.
        self.formula_by_label: Dict[str, Any] = {}

    def add_extra_rule(self, rule: Any) -> None:
        self.extra_rules.append(rule)

    def lookup_declaration(self, name: str) -> Optional[pl.Declaration]:
        """Resolve a declaration reference through `self.context`
        (`ProofContext`) rather than the legacy `self.declarations`
        (`DeclarationScope`) -- this is the declaration half of todos.txt's
        "resolve declaration and label references through the context"
        step. Safe unconditionally: `self.declarations` and `self.context`
        are seeded identically (see `__init__`), written identically
        (`register_declaration` dual-writes both), and scoped identically
        (`elaborate_subproof_body` gives both a child per subproof), so
        for every name either structure can currently answer, they agree.
        `self.declarations` itself is untouched and still written to --
        `elaborate_proof`'s own feed into `DiscreteMath.relation_rule_set`
        (`context.declarations.declarations_here()`) still reads it
        directly, a separate concern from resolving a reference during
        elaboration -- so this is a narrower migration than retiring
        `self.declarations` outright.

        The *label* half of "resolve ... references through the context"
        remains undone: unlike declarations, `ProofContext.bind_label` and
        the kernel's `LabelScope` disagree about whether shadowing is
        legal (see `elaborate_entry`'s docstring), so switching label
        resolution over here first needs that policy settled, not just an
        equivalence check like this one.
        """
        return self.context.lookup_declaration(name)

    def register_declaration(self, declaration: pl.Declaration, span: SourceSpan) -> None:
        try:
            self.declarations.declare(declaration)
        except KeyError as exc:
            existing = self.declarations.lookup(declaration.name)
            raise ElaborationError(
                f"symbol '{declaration.name}' is already declared"
                + (f" as {existing.kind}" if existing else ""),
                span,
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ElaborationError(str(exc), span) from exc
        try:
            self.context.declare(declaration)
        except pc.DuplicateBindingError as exc:
            # Should be unreachable: `self.context` is seeded from, and
            # updated in lockstep with, `self.declarations` above, so
            # anything accepted by the check just above is already known
            # fresh here too. Translated (not silently swallowed) so a
            # real divergence between the two structures fails loudly
            # during this migration rather than leaving `self.context`
            # quietly out of sync with what elaboration actually declared.
            existing = self.context.lookup_declaration(declaration.name)
            raise ElaborationError(
                f"symbol '{declaration.name}' is already declared"
                + (f" as {existing.kind}" if existing else ""),
                span,
            ) from exc

    def register_origin(
        self,
        label: Optional[str],
        span: SourceSpan,
        construct: str = "proof line",
        synthetic: bool = False,
    ) -> None:
        if label:
            self.origin_by_label[label] = CoreOrigin(span, construct, synthetic)

    def parse_surface_expression(self, text: str, bound_vars: Optional[set] = None) -> SurfaceExpression:
        bound_vars = bound_vars or set()
        for parser in self.environment.formula_parsers:
            expression = parser(text, bound_vars)
            if expression is not None:
                return expression
        return SurfaceExpression("core", parse_formula(text, bound_vars, self.environment), text)

    def parse_core_formula(self, text: str, bound_vars: Optional[set] = None) -> fl.Formula:
        expression = self.parse_surface_expression(text, bound_vars)
        if expression.kind == "core":
            return expression.value
        if expression.kind == "subset":
            import SyLoPy.source.SetTheory as st
            left, right = expression.value
            return st.subset_formula(left, right)
        raise ValueError(f"no core lowering registered for surface expression kind {expression.kind!r}")

    def display_term(self, term: tl.Term) -> str:
        try:
            import SyLoPy.source.SetTheory as st
            if pl._ast_eq(term, st.EMPTY_SET):
                return "the empty set"
        except ImportError:
            pass
        return repr(term)

    def core_formula_of(self, entry: Any) -> Optional[fl.Formula]:
        parsed = pl._classify_entry(entry)
        if isinstance(parsed, str) or parsed.is_subproof_block:
            return None
        return parsed.phi if isinstance(parsed.phi, fl.Formula) else None

    def elaborate_subproof_body(self, entries: List[Any]) -> List[Any]:
        """Elaborate one subproof's body -- the entries between a `begin
        subproof`/`end subproof` pair, wherever it is attached (a
        standalone labeled block, a `rule_below` justification's
        immediate subproof, or one of a `rule_hybrid` justification's
        several attached subproofs) -- using a fresh child `ProofContext`
        and a fresh child `DeclarationScope` for the duration, then
        restores both.

        This is the elaboration-time counterpart of `ProofValidator.
        _validate_block`'s own `declarations.child()`/`labels.child()`
        calls for the same construct (see `ProofLogic.py`): a declaration
        or label registered while elaborating `entries` becomes invisible
        to anything outside them once this method returns, while the
        enclosing scope's own declarations/labels remain visible from
        inside (both `ProofContext.child()` and `DeclarationScope.child()`
        inherit, per their own implementations).

        `self.declarations` joined `self.context` here after both were
        confirmed to already agree on the underlying policy:
        `DeclarationScope.declare()` already walks its full parent chain
        via `lookup()` before raising, exactly like `ProofContext.declare()`
        -- unlike labels, where the kernel's `LabelScope` permits
        cross-scope shadowing that `ProofContext.bind_label` forbids (see
        `elaborate_entry`'s docstring), there was no policy question to
        settle here, only this implementation gap to close. Closing it is
        what flips `test_sibling_subproofs_can_reuse_a_compound_declaration_name`
        (formerly an `xfail`) to a genuine pass.

        `self.origin_by_label` and `self.formula_by_label` remain
        flat/global elaboration-time bookkeeping, untouched by this
        method -- both are keyed by full dotted label strings, which are
        unique across the whole proof by construction, so flatness never
        risked a collision the way `self.context`/`self.declarations`
        (keyed by bare symbol/label names, reused freely across sibling
        scopes) did.
        """
        parent_context = self.context
        parent_declarations = self.declarations
        self.context = parent_context.child()
        self.declarations = parent_declarations.child()
        try:
            return [self.elaborate_entry(item) for item in entries]
        finally:
            self.context = parent_context
            self.declarations = parent_declarations

    def elaborate_entry(self, entry: Any) -> Any:
        """Thin wrapper around `_elaborate_entry_impl` that also records
        each labeled line's resulting formula into `self.formula_by_label`
        as elaboration proceeds -- so a later `line_elaborator` (e.g. the
        base logic's `Existence` sugar, see `try_elaborate_existence`) can
        look up what an earlier-cited label actually says, the same way
        validation later looks facts up by label, just one pass earlier.
        Recurses the same way the old single method did, so nested
        subproof entries get recorded too, in source order.

        Also dual-writes into `self.context` (see `elaborate_subproof_body`
        for how that context is now scoped per subproof), choosing the
        binding that matches the line's own justification tag rather than
        always calling `bind_label`:

          * `'assume'` -- `self.context.assume(formula, label=label)`, not
            `bind_label`, since labels and labeled assumptions share one
            namespace (`ProofContext`'s "proof-reference" namespace) --
            calling both for the same label would immediately collide
            with itself.
          * `'arbitrary'` -- both `self.context.bind_arbitrary(name)` (the
            fresh constant's own name, recovered from the nullary
            atomic-formula flag encoding -- see `SubproofRecord`'s
            docstring in ProofLogic.py) and `self.context.bind_label(label,
            formula)`, since "this name is fresh" and "this label cites
            this line" are genuinely different, independent namespaces.
          * anything else -- `self.context.bind_label(label, formula)`,
            unchanged from before.

        A collision here is a genuinely *new*, stricter check rather than
        a defensive impossibility: `ProofContext`'s binding methods refuse
        to let a name shadow one already visible in an enclosing scope
        (see `test_each_namespace_rejects_duplicates_across_visible_scopes`
        in `test_proof_context.py`), whereas the kernel's own `LabelScope`
        currently permits label shadowing silently. No proof in the
        current fixture corpus does this, but one that did would now be
        rejected here, earlier and more clearly than before -- see this
        module's docstring/todos.txt for this policy gap, which matters
        once (not yet) `ProofContext` drives citation resolution.
        """
        result = self._elaborate_entry_impl(entry)
        if (isinstance(result, tuple) and len(result) >= 3
                and isinstance(result[0], str)
                and not (isinstance(result[1], str) and result[1] == 'subproof')):
            label, formula, justification = result[0], result[1], result[2]
            self.formula_by_label[label] = formula
            tag = justification[0] if isinstance(justification, tuple) and justification else None

            def bind_label_here(value: Any) -> None:
                try:
                    self.context.bind_label(label, value)
                except pc.DuplicateBindingError as exc:
                    raise ElaborationError(
                        f"label '{label}' is already used earlier in this "
                        "proof or an enclosing scope",
                        entry.span,
                    ) from exc

            if tag == 'assume':
                try:
                    self.context.assume(formula, label=label)
                except pc.DuplicateBindingError as exc:
                    raise ElaborationError(
                        f"label '{label}' is already used earlier in this "
                        "proof or an enclosing scope",
                        entry.span,
                    ) from exc
            elif (tag == 'arbitrary' and isinstance(formula, fl.AtomicFormula)
                  and not formula.args and isinstance(formula.predicate, str)):
                try:
                    self.context.bind_arbitrary(formula.predicate)
                except pc.DuplicateBindingError as exc:
                    raise ElaborationError(
                        f"'{formula.predicate}' is not fresh -- that name "
                        "is already visible in this proof or an enclosing "
                        "scope",
                        entry.span,
                    ) from exc
                bind_label_here(formula)
            else:
                bind_label_here(formula)
        return result

    def _elaborate_entry_impl(self, entry: Any) -> Any:
        if isinstance(entry, SurfaceSubproof):
            body = self.elaborate_subproof_body(entry.entries)
            if entry.label:
                self.register_origin(entry.label, entry.span, "subproof")
                return (entry.label, 'subproof', body)
            return ('subproof', body)

        if not isinstance(entry, SurfaceLine):
            raise TypeError(f"unknown surface entry: {entry!r}")

        for elaborator in self.environment.line_elaborators:
            result = elaborator(entry, self)
            if result is not None:
                return result

        try:
            justification = parse_justification(entry.justification_text)
            tag = justification[0]
            declarations = []

            if tag in ('premise', 'declare'):
                parsed_declarations, remainder = parse_declaration_prefix(entry.formula_text)
                if parsed_declarations:
                    declarations = parsed_declarations
                    if remainder is None:
                        formula = None
                    else:
                        formula = _parse_formula_or_bundle(remainder, self.environment) if tag == 'premise' else self.parse_core_formula(remainder)
                else:
                    formula = _parse_formula_or_bundle(entry.formula_text, self.environment) if tag == 'premise' else self.parse_core_formula(entry.formula_text)
                if declarations:
                    justification = (tag, declarations)
            else:
                formula = self.parse_core_formula(entry.formula_text)

            self.register_origin(entry.label, entry.span)

            if tag == 'rule_below':
                if len(entry.subproofs) != 1:
                    raise ElaborationError(
                        "this justification requires an immediate subproof below",
                        entry.span,
                    )
                nested = self.elaborate_subproof_body(entry.subproofs[0].entries)
                return (entry.label, formula, justification, nested)

            if tag == 'rule_hybrid':
                rule = justification[1]
                cited = justification[2]
                needed = getattr(rule, 'premise_arity', 0) - len(cited)
                if needed <= 0 or len(entry.subproofs) != needed:
                    raise ElaborationError(
                        f"this rule requires {needed} subproof(s) below",
                        entry.span,
                    )
                nested = [
                    self.elaborate_subproof_body(subproof.entries)
                    for subproof in entry.subproofs
                ]
                return (entry.label, formula, justification, nested)

            if entry.subproofs:
                raise ElaborationError(
                    "subproofs were supplied below a line whose justification does not consume them",
                    entry.span,
                )
            return (entry.label, formula, justification)
        except ElaborationError:
            raise
        except (TypeError, ValueError) as exc:
            raise ElaborationError(str(exc), entry.span) from exc


def elaborate_proof(
    surface_proof: SurfaceProof,
    environment: Optional[TheoryEnvironment] = None,
) -> ElaboratedEntries:
    """Lower a SurfaceProof to the strict ProofLogic entry language."""
    environment = environment or default_theory_environment()
    context = _ElaborationContext(environment)
    entries = [context.elaborate_entry(entry) for entry in surface_proof.entries]
    try:
        import SyLoPy.source.DiscreteMath as dm
        context.extra_rules.extend(dm.relation_rule_set(context.declarations.declarations_here()))
    except ImportError:
        pass
    return ElaboratedEntries(
        entries,
        origin_by_label=context.origin_by_label,
        surface_proof=surface_proof,
        required_rules=list(environment.rules) + context.extra_rules,
        required_axioms=environment.axioms,
        required_declarations=environment.declarations,
    )


def parse_proof_text(
    text: str,
    environment: Optional[TheoryEnvironment] = None,
):
    """Parse natural proof text and elaborate it to core proof entries.

    The return shape remains ``(entries, raw_lines)`` for compatibility.
    ``entries`` is an :class:`ElaboratedEntries` list subclass containing
    origin and theory metadata used by :class:`ProofLogic.Proof`.
    """
    surface = parse_surface_proof(text)
    entries = elaborate_proof(surface, environment)
    return entries, surface.raw_lines


def check_proof_text(
    text: str,
    *,
    environment: Optional[TheoryEnvironment] = None,
    premises: Optional[list] = None,
    axioms: Optional[list] = None,
    rules: Optional[list] = None,
    declarations: Optional[list] = None,
):
    """Parse, elaborate, and validate proof text in one source-aware call."""
    entries, _ = parse_proof_text(text, environment)
    return pl.Proof(
        entries,
        premises=premises,
        axioms=axioms,
        rules=rules,
        declarations=declarations,
    ).check_detailed()



def format_core_proof(entries: list) -> str:
    """Render elaborated core entries for diagnostics and teaching.

    This is intentionally a view of the AST, not a text-to-text preprocessing
    stage that is reparsed.  Synthetic labels therefore remain visible for
    inspection without becoming part of the user's source file.
    """

    lines: List[str] = []

    def justification_text(justification: tuple) -> str:
        if not isinstance(justification, tuple) or not justification:
            return repr(justification)
        tag = justification[0]
        if tag in {'premise', 'axiom', 'assume', 'arbitrary', 'declare'}:
            return tag
        if tag == 'rule':
            rule = justification[1]
            refs = justification[2]
            suffix = f" from {', '.join(refs)}" if refs else ''
            return f"{getattr(rule, 'name', type(rule).__name__)}{suffix}"
        if tag == 'rule_below':
            return f"{getattr(justification[1], 'name', type(justification[1]).__name__)} from subproof below"
        if tag == 'rule_hybrid':
            rule = justification[1]
            refs = justification[2]
            return f"{getattr(rule, 'name', type(rule).__name__)} from {', '.join(refs)}, subproofs below"
        return repr(justification)

    def walk(block: list, depth: int = 0) -> None:
        prefix = '  ' * depth
        for raw in block:
            parsed = pl._classify_entry(raw)
            if isinstance(parsed, str):
                lines.append(prefix + f"<malformed: {raw!r}>")
                continue
            if parsed.is_subproof_block:
                label = f"{parsed.label}. " if parsed.label else ''
                lines.append(prefix + label + 'begin subproof')
                walk(parsed.subproof_entries, depth + 1)
                lines.append(prefix + 'end subproof')
                continue

            label = f"{parsed.label}. " if parsed.label else ''
            if parsed.phi is None:
                formula = '<declarations only>'
            elif isinstance(parsed.phi, list):
                formula = '; '.join(repr(item) for item in parsed.phi)
            else:
                formula = repr(parsed.phi)
            lines.append(prefix + f"{label}{formula}. ({justification_text(parsed.justification)})")

            if parsed.nested_subproof is not None:
                nested = parsed.nested_subproof
                if parsed.justification and parsed.justification[0] == 'rule_hybrid':
                    for subproof in nested:
                        lines.append(prefix + 'begin subproof')
                        walk(subproof, depth + 1)
                        lines.append(prefix + 'end subproof')
                else:
                    lines.append(prefix + 'begin subproof')
                    walk(nested, depth + 1)
                    lines.append(prefix + 'end subproof')

    walk(entries)
    return '\n'.join(lines)

def run_file(path: str):
    """Convenience CLI entry point: parse and check the proof in `path`,
    printing the result and, for an invalid proof, the source line that
    caused it.

    Uses `Proof.check_detailed()` and its `ValidationError.label` directly
    to find the offending source line, by matching it against each raw
    line's own leading label (via `_LABELED_LINE_RE`) -- rather than
    trying to recover a line number by parsing the rendered message
    string, which is what an earlier version of this function attempted
    (regex-matching an "Entry N:" shape the validator never actually
    produced) and is generally fragile: a message string is meant for a
    person to read, not for a caller to parse back apart.

    Note: if the offending line was itself written wrapped across several
    physical lines (see `parse_proof_text`'s line-joining pass), only the
    first physical line is shown -- `raw_lines` holds the original,
    unwrapped lines, and the label only appears on the first of them.
    """
    with open(path, 'r') as f:
        text = f.read()
    entries, raw_lines = parse_proof_text(text)
    proof = pl.Proof(entries)
    ok, err = proof.check_detailed()
    if ok:
        print('Proof valid')
    else:
        print('Proof invalid:')
        print(err)
        if err.label is not None:
            for raw_line in raw_lines:
                m = _LABELED_LINE_RE.match(raw_line.strip())
                if m and m.group(1) == err.label:
                    print('Offending line:', raw_line.strip())
                    break


if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        print("Run with a proof text file as an argument.")





