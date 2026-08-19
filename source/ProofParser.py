"""Public proof parser facade.

The historical parser remains in :mod:`ProofParserLegacy` while this facade
owns language-level policy that should not be embedded in the large parsing
implementation. Existing imports continue to use ``ProofParser``.
"""
from __future__ import annotations

from SyLoPy.source import ProofParserLegacy as _legacy
from SyLoPy.source.ProofParserLegacy import *  # noqa: F401,F403
from SyLoPy.source.ProofJustification import parse_justification
from SyLoPy.source.LineBreakSyntax import install as _install_line_break_syntax


_legacy.parse_justification = parse_justification
_install_line_break_syntax(_legacy)


# The legacy declaration grammar historically required `such that:`. The
# surface language uses the natural phrase without requiring punctuation, so
# normalize both forms at the facade boundary before the legacy parser builds
# its SurfaceDeclarationStatement.
_original_parse_surface_declaration_statement = _legacy.parse_surface_declaration_statement


def _parse_surface_declaration_statement(text, span):
    import re
    normalized = re.sub(r'\bsuch\s+that\s*(?=\S)', 'such that: ', text, count=1, flags=re.I)
    return _original_parse_surface_declaration_statement(normalized, span)


_legacy.parse_surface_declaration_statement = _parse_surface_declaration_statement


def _parse_formula_conventional(s: str, bound_vars=None, environment=None):
    """Parse formulas with conventional logical precedence."""
    if bound_vars is None:
        bound_vars = set()
    if environment is None:
        environment = _legacy._cached_default_environment()
    s = s.strip()

    import re
    import SyLoPy.source.FormulaLogic as fl

    m = re.match(r'^let\s+([A-Za-z_][A-Za-z0-9_]*)\s+be\s+(?:in\s+the\s+domain|arbitrary)\.?$', s, flags=re.I)
    if m:
        return fl.AtomicFormula(m.group(1), [])

    m = re.match(r'^(?:for all|forall)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$', s, flags=re.I)
    if m:
        var = m.group(1)
        return fl.ForAll(var, _parse_formula_conventional(m.group(2), bound_vars | {var}, environment))

    m = re.match(r'^(?:exists|there exists)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$', s, flags=re.I)
    if m:
        var = m.group(1)
        return fl.Exists(var, _parse_formula_conventional(m.group(2), bound_vars | {var}, environment))

    for sep in (' if and only if ', ' <-> ', ' <=> ', ' ↔ ', ' iff '):
        parts = _legacy.split_top_level(s, sep)
        if len(parts) > 1:
            if len(parts) != 2:
                raise ValueError(f"Multiple top-level biconditionals are not supported: {s!r}")
            return fl.Iff(_parse_formula_conventional(parts[0], bound_vars, environment), _parse_formula_conventional(parts[1], bound_vars, environment))

    m = re.match(r'^if\s+(.*?)\s+then\s+(.*)$', s, flags=re.I)
    if m:
        return fl.Implies(
            _parse_formula_conventional(m.group(1), bound_vars, environment),
            _parse_formula_conventional(m.group(2), bound_vars, environment),
        )
    for sep in (' -> ', ' implies '):
        parts = _legacy.split_top_level(s, sep)
        if len(parts) > 1:
            result = _parse_formula_conventional(parts[-1], bound_vars, environment)
            for part in reversed(parts[:-1]):
                result = fl.Implies(_parse_formula_conventional(part, bound_vars, environment), result)
            return result

    parts = _legacy.split_top_level(s, ' or ')
    if len(parts) > 1:
        return fl.Or(*[_parse_formula_conventional(p, bound_vars, environment) for p in parts])

    parts = _legacy.split_top_level(s, ' and ')
    if len(parts) > 1:
        return fl.And(*[_parse_formula_conventional(p, bound_vars, environment) for p in parts])

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
            return _parse_formula_conventional(s[1:-1], bound_vars, environment)

    m = re.match(r'^(?:not|¬)\s+(.*)$', s, flags=re.I)
    if m:
        return fl.Not(_parse_formula_conventional(m.group(1), bound_vars, environment))

    parts = _legacy.split_top_level(s, ' =/= ')
    if len(parts) == 2:
        return fl.Not(
            fl.Equals(
                _legacy.parse_term(parts[0], bound_vars, environment),
                _legacy.parse_term(parts[1], bound_vars, environment),
            )
        )

    parts = _legacy.split_top_level(s, ' = ')
    if len(parts) == 2:
        return fl.Equals(
            _legacy.parse_term(parts[0], bound_vars, environment),
            _legacy.parse_term(parts[1], bound_vars, environment),
        )

    for nested_parser in environment.nested_formula_parsers:
        formula = nested_parser(s, bound_vars)
        if formula is not None:
            return formula

    matched = _legacy._match_applied_symbol(s)
    if matched:
        pred, args_str = matched
        return fl.AtomicFormula(pred, _legacy._parse_arg_list(args_str, bound_vars, environment))

    if _legacy._BARE_IDENTIFIER_RE.match(s):
        return fl.AtomicFormula(s, [])

    raise ValueError(
        f"Unrecognized formula syntax: {s!r}. Expected a logical connective, "
        "an atomic predicate like 'P(x)', a simple atomic proposition name, "
        "or syntax registered by an imported theory module -- not a raw, "
        "unrecognized expression silently treated as an opaque atom."
    )


_legacy.parse_formula = _parse_formula_conventional
parse_formula = _parse_formula_conventional


_original_elaborate_compound_declaration = _legacy.elaborate_compound_declaration


def _membership_characterization(text: str):
    """Recognize ``a is in X iff P(a)`` with an implicit bound variable."""
    import re

    s = text.strip().rstrip('.').strip()
    match = re.fullmatch(
        r'([A-Za-z_][A-Za-z0-9_]*)\s+is\s+in\s+(.+?)\s+iff\s+(.+)',
        s,
        flags=re.I,
    )
    if not match:
        return None
    return match.group(1), match.group(2).strip(), match.group(3).strip()


def _elaborate_membership_characterization(entry, context):
    """Elaborate ``a is in X iff P(a)`` as a universally quantified premise."""
    statement = entry.declaration_statement
    if statement is None:
        return None
    just = entry.justification_text.strip().lower()
    if just not in ('declaration', 'declare'):
        return None

    characterization = None
    for clause in statement.clauses:
        if isinstance(clause, _legacy.SurfacePremiseClause):
            parsed = _membership_characterization(clause.formula)
            if parsed is not None:
                if characterization is not None:
                    raise _legacy.ElaborationError(
                        "a set declaration may contain only one membership characterization",
                        clause.span or entry.span,
                    )
                characterization = (clause, parsed)

    if characterization is None:
        return None

    clause, (variable, set_text, property_text) = characterization

    if context.lookup_declaration(variable) is not None:
        raise _legacy.ElaborationError(
            f"membership characterization variable '{variable}' must be fresh",
            clause.span or entry.span,
        )

    local_names = {
        declaration.name
        for item in statement.clauses
        if isinstance(item, _legacy.SurfaceDeclarationClause)
        for declaration in item.declarations
    }
    if variable in local_names:
        raise _legacy.ElaborationError(
            f"membership characterization variable '{variable}' must be fresh and cannot be declared in the same statement",
            clause.span or entry.span,
        )

    try:
        import SyLoPy.source.SetTheory as st
        set_term = st.try_parse_set_term(set_text, set())
    except ImportError:
        set_term = None
    if set_term is None:
        raise _legacy.ElaborationError(
            f"membership characterization has invalid set expression: {set_text!r}",
            clause.span or entry.span,
        )

    rewritten_formula = f"for all {variable}, {variable} is in {set_text} iff {property_text}"
    statement.clauses[:] = [
        _legacy.SurfacePremiseClause(
            rewritten_formula if item is clause else item.formula,
            item.span,
        ) if isinstance(item, _legacy.SurfacePremiseClause) else item
        for item in statement.clauses
    ]
    return _original_elaborate_compound_declaration(entry, context)


_legacy.elaborate_compound_declaration = _elaborate_membership_characterization
