"""Language-policy extensions for the proof parser.

The parser implementation lives in :mod:`ProofParser`.  This module contains
small, explicit policy extensions that used to be installed by a compatibility
facade.  Keeping them separate avoids putting theory-specific surface syntax
into the core parser while avoiding any dependency on a legacy parser module.
"""
from __future__ import annotations

import re

from SyLoPy.source import ProofParser as _parser
from SyLoPy.source.LineBreakSyntax import install as _install_line_break_syntax


# `parse_justification` no longer needs to be installed here: it has no
# dependency on anything in `ProofParser`, so `ProofParser.py` now imports
# `ProofJustification.parse_justification` directly at its own top level
# instead of relying on this module to patch it in after the fact.
_install_line_break_syntax(_parser)


_original_parse_surface_declaration_statement = _parser.parse_surface_declaration_statement


def _parse_surface_declaration_statement(text, span):
    normalized = re.sub(
        r"\bsuch\s+that\s*(?!:)",
        "such that: ",
        text,
        count=1,
        flags=re.I,
    )
    return _original_parse_surface_declaration_statement(normalized, span)


_parser.parse_surface_declaration_statement = _parse_surface_declaration_statement


def _parse_formula_conventional(s: str, bound_vars=None, environment=None):
    """Parse formulas using conventional connective precedence: ``not``
    binds tightest, then ``and``, then ``or``, then ``->``/``implies``,
    loosest of all the biconditional family -- the textbook convention,
    not the order this function's own checks run in (see below for why
    those two things differ). This is the `parse_formula` every caller
    actually gets: it's installed onto `ProofParser.parse_formula` at
    import time (see the bottom of this module) and is deliberately an
    *extension* of the core parser rather than a second parser
    implementation -- it reaches back into `ProofParser`'s own
    `split_top_level`, `parse_term`, `_match_applied_symbol`, and
    `_BARE_IDENTIFIER_RE` for everything except connective ordering.
    Theory-specific nested parsers and the core term parser remain
    authoritative.

    Recognizes, in this order:

      1. ``let X be in the domain.`` / ``let X be arbitrary`` -- the
         special "fresh constant" flag formula (see
         `ProofLogic.SubproofRecord`'s docstring for how this
         nullary-predicate encoding is used by `UniversalGeneralizationRule`)
      2. ``for all x, ...`` / ``forall x, ...`` -- the comma is optional
      3. ``exists x, ...`` / ``there exists x, ...`` -- comma optional
      4. the biconditional family: ``if and only if``, ``<->``, ``<=>``,
         ``↔``, ``iff`` -- tried together, in this priority order
      5. ``if X then Y``
      6. ``->`` / ``implies`` -- right-associative for a chain like
         ``"A -> B -> C"``
      7. top-level ``or`` (N-ary: ``A or B or C`` all becomes one `Or`)
      8. top-level ``and`` (N-ary, same idea)
      9. a fully parenthesized remainder, e.g. ``(A and B)`` -> unwrap and
         re-parse the inside
      10. ``not ...`` / ``¬...``
      11. ``=/=`` (negated equality between two Terms)
      12. ``=`` (equality between two Terms -- see `FormulaLogic.Equals`)
      13. theory syntax from `environment.nested_formula_parsers` (e.g.
          SetTheory's "a is in X", NumberTheory's "a|n") -- tried after
          every connective above has had a chance to split the string,
          but before the final atomic-predicate/bare-atomic fallback,
          *not* before: a theory phrase containing a connective keyword as
          a substring would otherwise risk swallowing more than intended
          (checking "a|n" against the whole of "if a|n then b" before
          "if...then" has split it apart would wrongly capture "if a" as
          part of a term)
      14. ``pred(arg, arg, ...)`` -- an atomic predicate with arguments
      15. (fallback) a bare atomic proposition, `AtomicFormula(s, [])`

    Because whichever check fires *first* on an unparenthesized string
    becomes that string's outermost connective, this recognition order is
    also, read top to bottom through steps 4-10, exactly the precedence
    table from loosest-binding to tightest: ``iff`` > ``->``/``implies`` >
    ``or`` > ``and`` > ``not``. So ``parse_formula("A -> B and C")``
    parses as ``A -> (B and C)`` (`and` groups before `->` claims either
    side), and ``"A or B and C"`` parses as ``A or (B and C)`` (`and`
    groups before `or` does) -- both the ordinary textbook reading.

    `environment` is threaded through every recursive call (not just
    consulted once at the top), so theory syntax is recognized in nested
    positions too -- e.g. the "a|n" inside "if a|n then b" -- not only
    when a formula happens to consist of nothing else. Defaults to the
    core parser's cached `default_theory_environment()` when omitted.
    (`environment.formula_parsers`, by contrast, is only consulted by
    `_ElaborationContext.parse_surface_expression` at the top of a single
    proof line, since some of its results carry extra structure -- like
    SetTheory's raw subset operands -- that only the elaborator that asked
    for them knows how to use.)

    Examples::

        >>> repr(_parse_formula_conventional('A -> B and C'))
        '(A() → (B() ∧ C()))'
        >>> repr(_parse_formula_conventional('A or B and C'))
        '(A() ∨ (B() ∧ C()))'
        >>> repr(_parse_formula_conventional('for all x, P(x) -> Q(x)'))
        '(∀x. (P(x) → Q(x)))'
        >>> repr(_parse_formula_conventional('let c be in the domain'))
        'c()'
    """
    if bound_vars is None:
        bound_vars = set()
    if environment is None:
        environment = _parser._cached_default_environment()

    s = s.strip()

    m = re.match(
        r"^let\s+([A-Za-z_][A-Za-z0-9_]*)\s+be\s+(?:in\s+the\s+domain|arbitrary)\.?$",
        s,
        flags=re.I,
    )
    if m:
        import SyLoPy.source.FormulaLogic as fl
        return fl.AtomicFormula(m.group(1), [])

    import SyLoPy.source.FormulaLogic as fl

    m = re.match(
        r"^(?:for all|forall)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$",
        s,
        flags=re.I,
    )
    if m:
        var = m.group(1)
        return fl.ForAll(
            var,
            _parse_formula_conventional(m.group(2), bound_vars | {var}, environment),
        )

    m = re.match(
        r"^(?:exists|there exists)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$",
        s,
        flags=re.I,
    )
    if m:
        var = m.group(1)
        return fl.Exists(
            var,
            _parse_formula_conventional(m.group(2), bound_vars | {var}, environment),
        )

    for sep in (" if and only if ", " <-> ", " <=> ", " ↔ ", " iff "):
        parts = _parser.split_top_level(s, sep)
        if len(parts) > 1:
            if len(parts) != 2:
                raise ValueError(
                    f"Multiple top-level biconditionals are not supported: {s!r}"
                )
            return fl.Iff(
                _parse_formula_conventional(parts[0], bound_vars, environment),
                _parse_formula_conventional(parts[1], bound_vars, environment),
            )

    m = re.match(r"^if\s+(.*?)\s+then\s+(.*)$", s, flags=re.I)
    if m:
        return fl.Implies(
            _parse_formula_conventional(m.group(1), bound_vars, environment),
            _parse_formula_conventional(m.group(2), bound_vars, environment),
        )

    for sep in (" -> ", " implies "):
        parts = _parser.split_top_level(s, sep)
        if len(parts) > 1:
            result = _parse_formula_conventional(parts[-1], bound_vars, environment)
            for part in reversed(parts[:-1]):
                result = fl.Implies(
                    _parse_formula_conventional(part, bound_vars, environment),
                    result,
                )
            return result

    parts = _parser.split_top_level(s, " or ")
    if len(parts) > 1:
        return fl.Or(
            *[_parse_formula_conventional(p, bound_vars, environment) for p in parts]
        )

    parts = _parser.split_top_level(s, " and ")
    if len(parts) > 1:
        return fl.And(
            *[_parse_formula_conventional(p, bound_vars, environment) for p in parts]
        )

    if s.startswith("(") and s.endswith(")"):
        depth = 0
        balanced = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    balanced = False
                    break
        if balanced and depth == 0:
            return _parse_formula_conventional(s[1:-1], bound_vars, environment)

    m = re.match(r"^(?:not|¬)\s+(.*)$", s, flags=re.I)
    if m:
        return fl.Not(_parse_formula_conventional(m.group(1), bound_vars, environment))

    parts = _parser.split_top_level(s, " =/= ")
    if len(parts) == 2:
        return fl.Not(
            fl.Equals(
                _parser.parse_term(parts[0], bound_vars, environment),
                _parser.parse_term(parts[1], bound_vars, environment),
            )
        )

    parts = _parser.split_top_level(s, " = ")
    if len(parts) == 2:
        return fl.Equals(
            _parser.parse_term(parts[0], bound_vars, environment),
            _parser.parse_term(parts[1], bound_vars, environment),
        )

    for nested_parser in environment.nested_formula_parsers:
        formula = nested_parser(s, bound_vars)
        if formula is not None:
            return formula

    matched = _parser._match_applied_symbol(s)
    if matched:
        predicate, args_str = matched
        return fl.AtomicFormula(
            predicate,
            _parser._parse_arg_list(args_str, bound_vars, environment),
        )

    if _parser._BARE_IDENTIFIER_RE.match(s):
        return fl.AtomicFormula(s, [])

    raise ValueError(f"Unrecognized formula syntax: {s!r}")


_parser.parse_formula = _parse_formula_conventional


_original_elaborate_compound_declaration = _parser.elaborate_compound_declaration


def _membership_characterization(text: str):
    s = text.strip().rstrip(".").strip()
    match = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*)\s+is\s+in\s+(.+?)\s+iff\s+(.+)",
        s,
        flags=re.I,
    )
    return (
        None
        if match is None
        else (match.group(1), match.group(2).strip(), match.group(3).strip())
    )


def _elaborate_membership_characterization(entry, context):
    statement = entry.declaration_statement
    if statement is None:
        return None

    justification = entry.justification_text.strip().lower()
    if justification not in ("declaration", "declare"):
        return None

    characterization = None
    for clause in statement.clauses:
        if isinstance(clause, _parser.SurfacePremiseClause):
            parsed = _membership_characterization(clause.formula)
            if parsed is not None:
                if characterization is not None:
                    raise _parser.ElaborationError(
                        "a set declaration may contain only one membership characterization",
                        clause.span or entry.span,
                    )
                characterization = (clause, parsed)

    if characterization is None:
        return _original_elaborate_compound_declaration(entry, context)

    clause, (variable, set_text, property_text) = characterization
    if context.lookup_declaration(variable) is not None:
        raise _parser.ElaborationError(
            f"membership characterization variable '{variable}' must be fresh",
            clause.span or entry.span,
        )

    local_names = {
        declaration.name
        for item in statement.clauses
        if isinstance(item, _parser.SurfaceDeclarationClause)
        for declaration in item.declarations
    }
    if variable in local_names:
        raise _parser.ElaborationError(
            f"membership characterization variable '{variable}' must be fresh and cannot be declared in the same statement",
            clause.span or entry.span,
        )

    rewritten_formula = (
        f"for all {variable}, {variable} is in {set_text} iff {property_text}"
    )
    statement.clauses[:] = [
        _parser.SurfacePremiseClause(
            rewritten_formula if item is clause else item.formula,
            item.span,
        )
        if isinstance(item, _parser.SurfacePremiseClause)
        else item
        for item in statement.clauses
    ]
    return _original_elaborate_compound_declaration(entry, context)


_parser.elaborate_compound_declaration = _elaborate_membership_characterization
