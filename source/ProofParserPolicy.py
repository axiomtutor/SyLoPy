"""Language-policy extensions for the proof parser.

The parser implementation lives in :mod:`ProofParser`.  Importing this module
installs the public language policy onto that facade: conventional connective
precedence, the justification parser, ``such that`` wording, membership
characterization, and declaration line-break handling.  Those extensions stay
here so theory-specific surface syntax does not accumulate inside the core
parser module.
"""
from __future__ import annotations

import re

from SyLoPy.source import ProofParser as _parser
from SyLoPy.source.ProofJustification import parse_justification
from SyLoPy.source.LineBreakSyntax import install as _install_line_break_syntax


# The justification parser is the authoritative implementation now.
_parser.parse_justification = parse_justification
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
    """Parse formulas using conventional connective precedence.

    This is deliberately an extension of the core parser rather than a
    second parser implementation.  Theory-specific nested parsers and the
    core term parser remain authoritative.
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
_parser._split_trailing_parenthetical = _parser._split_trailing_parenthetical
