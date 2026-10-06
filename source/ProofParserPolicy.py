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


_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
# Words that can never be the *kind* in "there exists a KIND NAME ...", and
# words that can never be the *variable* (the kinds "set" and "object" are
# also kept out, so that "there exists a set such that P" is an error rather
# than a quantifier over a variable named "set").
_NOT_A_KEYWORD = r"(?!(?:such|that|which|unique)\b)"
_NOT_A_VARIABLE = r"(?!(?:such|that|which|unique|set|object)\b)"
# "there exists x such that BODY"  (one variable; several are handled by the
# multi-variable "such that" forms in `_parse_formula_conventional`)
_EXISTS_SUCH_THAT_RE = re.compile(
    rf"^(?:exists|there\s+exists)\s+(?P<name>{_NOT_A_VARIABLE}{_NAME})\s+such\s+that\s*:?\s*(?P<rest>.+)$",
    re.I,
)
# "there exists a [unique] [kind] NAME  (such that BODY | that PHRASE | = TERM)"
_EXISTS_ARTICLE_RE = re.compile(
    r"^there\s+(?:exists|is)\s+"
    r"(?P<quant>(?:an?\s+)?unique|exactly\s+one|an?|one)\s+"
    rf"(?:{_NOT_A_KEYWORD}(?P<kind>{_NAME})\s+)?"
    rf"(?P<name>{_NOT_A_VARIABLE}{_NAME}|\{{[^{{}}]*\}})\s*"
    r"(?P<connector>such\s+that|that|which|=|,)\s*:?\s*(?P<rest>.+)$",
    re.I,
)
# Kinds that add no condition: every object of set theory is a set.
_UNTYPED_KINDS = {"set", "object"}
# The start of the article form, used only to explain a failure to read it.
_ARTICLE_FORM_START_RE = re.compile(r"^there\s+(?:exists|is)\s+(?:an?|one|unique|exactly\s+one)\s+\S", re.I)
_EXISTENTIAL_FORMS_HELP = (
    "Supported: 'there exists x such that BODY', "
    "'there exists a [unique] [set] Y such that BODY', "
    "'there exists a [unique] [set] Y that PHRASE', "
    "'there exists a [unique] [set] Y = {a, b}', "
    "'there exists a [unique] [set] Y, BODY'"
)


def _bracket_depths(s: str) -> list:
    """For each index of `s`, how many ( or { are open just before it."""
    depths, depth = [], 0
    for ch in s:
        depths.append(depth)
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth = max(0, depth - 1)
    return depths


_EXISTENTIAL_OPENER_RE = re.compile(r"\b(?:there\s+(?:exists|is)|exists)\s", re.I)
_THEN_RE = re.compile(r"\s+then\s+", re.I)


def _embedded_existential_spans(s: str) -> list:
    """Spans of natural-language existentials that follow something else in `s`.

    "P and there exists a unique set {c, d} that contains exactly c and d": like
    an existential at the start of a string, the quantifier takes everything to
    its right, so the span runs to the end of `s` -- except that it stops at a
    top-level "then", which can only belong to an enclosing "if ... then".
    Only the natural forms count (see `_parse_natural_existential`); the
    symbolic ``exists x, BODY`` keeps the scope the grammar gives it.
    """
    depths = _bracket_depths(s)
    spans = []
    for opener in _EXISTENTIAL_OPENER_RE.finditer(s):
        start = opener.start()
        if start == 0 or depths[start] != 0:
            continue
        end = len(s)
        for then in _THEN_RE.finditer(s, start):
            if depths[then.start()] == 0:
                end = then.start()
                break
        candidate = s[start:end]
        if _EXISTS_SUCH_THAT_RE.match(candidate) or _EXISTS_ARTICLE_RE.match(candidate):
            spans.append((start, end))
    return spans


def _protect_phrases(s: str, environment) -> str:
    """Wrap each top-level theory phrase inside `s` in parentheses.

    The phrases are those the environment's `phrase_spans` finders report (see
    `TheoryEnvironment.phrase_spans`), plus natural-language existentials that
    follow something else in the string. The grammar below cuts a string at its
    top-level "or"/"and"/..., and a phrase such as "w is h, i, j, or k" would
    be cut apart with it; inside parentheses it is out of the grammar's reach
    and arrives whole at the phrase parsers. A span that is already inside
    brackets needs nothing, which is also what ends the recursion: the wrapped
    string has no top-level spans left. `s` is returned unchanged when there is
    nothing to protect, or when one span is the whole string.
    """
    spans = _embedded_existential_spans(s)
    for find in environment.phrase_spans:
        spans.extend(find(s))
    if not spans:
        return s
    depths = _bracket_depths(s)
    spans = sorted({span for span in spans if span[0] < span[1] and depths[span[0]] == 0})
    merged = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    if not merged or merged == [(0, len(s))]:
        return s
    pieces, position = [], 0
    for start, end in merged:
        pieces.extend((s[position:start], "(", s[start:end], ")"))
        position = end
    pieces.append(s[position:])
    return "".join(pieces)


def _fresh_name(used, candidates) -> str:
    for candidate in candidates:
        if candidate not in used:
            return candidate
    index = 1
    while f"{candidates[0]}{index}" in used:
        index += 1
    return f"{candidates[0]}{index}"


def _parse_natural_existential(s, bound_vars, environment):
    """Natural-language existentials, desugared to ordinary quantifiers.

        there exists x such that BODY            ==>  exists x, BODY
        there exists a set Y such that BODY      ==>  exists Y, BODY
        there exists an integer n such that BODY ==>  exists n, (n is an integer and BODY)
        there is a set Y = {a, b}                ==>  exists Y, (Y = {a, b})
        there exists a set Y that PHRASE         ==>  exists Y, (Y PHRASE)

    "unique" (or "exactly one") adds the uniqueness clause, so with P(Y) the
    condition above,

        there exists a unique set Y such that P(Y)
            ==>  exists Y, (P(Y) and forall Z, (P(Z) -> Z = Y))

    for a variable Z that occurs nowhere in P. There is no "exists unique"
    connective: this is the ordinary formula, written out. The braces in
    "a unique set {a, b} that ..." only label the set; the condition after
    "that" is what constrains it.

    Returns None when `s` is not of this form.
    """
    import SyLoPy.source.FormulaLogic as fl
    import SyLoPy.source.TermLogic as tl

    m = _EXISTS_SUCH_THAT_RE.match(s)
    if m:
        variable = m.group("name")
        body = _parse_formula_conventional(m.group("rest"), bound_vars | {variable}, environment)
        return fl.Exists(variable, body)

    m = _EXISTS_ARTICLE_RE.match(s)
    if not m:
        return None
    quantity = re.sub(r"\s+", " ", m.group("quant").lower())
    unique = quantity.endswith("unique") or quantity == "exactly one"
    kind = m.group("kind")
    name = m.group("name")
    connector = re.sub(r"\s+", " ", m.group("connector").lower())
    rest = m.group("rest").strip()

    if name.startswith("{"):
        used = set(re.findall(_NAME, rest)) | set(bound_vars)
        variable = _fresh_name(used, ("S", "Y", "Z", "T", "V", "W"))
    else:
        variable = name
    inner_bound = bound_vars | {variable}

    if connector in ("that", "which"):
        body_text = f"{variable} {rest}"
    elif connector in ("such that", ","):
        body_text = rest
    else:
        body_text = f"{variable} = {rest}"
    condition = _parse_formula_conventional(body_text, inner_bound, environment)

    if kind and kind.lower() not in _UNTYPED_KINDS:
        article = "an" if kind[0].lower() in "aeiou" else "a"
        kind_text = f"{variable} is {article} {kind}"
        try:
            kind_condition = _parse_formula_conventional(kind_text, inner_bound, environment)
        except ValueError as error:
            raise ValueError(
                f"Cannot read {s!r}: no imported theory defines the condition {kind_text!r} "
                f"for the word {kind!r}. Say 'there exists {variable} such that ...' and state "
                f"the condition yourself ({error})"
            ) from None
        condition = fl.And(kind_condition, condition)

    if not unique:
        return fl.Exists(variable, condition)

    other = _fresh_name(fl.formula_names(condition) | set(bound_vars) | {variable}, ("X", "Z", "W", "V", "U", "T"))
    same_for_other = fl.substitute_in_formula(condition, variable, tl.VariableTerm(other))
    return fl.Exists(
        variable,
        fl.And(
            condition,
            fl.ForAll(
                other,
                fl.Implies(same_for_other, fl.Equals(tl.VariableTerm(other), tl.VariableTerm(variable))),
            ),
        ),
    )


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
      2. ``for all x, ...`` / ``forall x, ...`` -- the comma is optional.
         Also accepts several variables at once, ``forall x, y, ... such
         that: BODY`` (colon after "such that" optional too), desugaring
         to nested single-variable `ForAll`s in the order given
         (``forall x, y such that: P(x,y)`` is exactly `ForAll('x',
         ForAll('y', P(x,y)))`) -- this is why the "such that" form is
         checked first, and only for two or more names: a lone ``forall
         x, BODY`` must stay on the plain path below it, both because
         that is the overwhelmingly common case and because a would-be
         multi-variable regex with only one name captured can't tell "x"
         (the whole variable list) apart from "x" followed by a body that
         happens to start with something identifier-shaped (``forall x,
         P(x)`` -- is "P" a second bound variable, or the start of the
         body?). Requiring "such that" for the multi-variable form sidesteps
         that ambiguity entirely rather than guessing.
      3. ``exists x, ...`` / ``there exists x, ...`` -- comma optional,
         same multi-variable "such that" extension as `forall` above.
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

    (Before step 1, `environment.phrase_parsers` get the whole string: a
    theory phrase that is not splittable at a connective *because it is one
    phrase*, such as "x is a or b", is claimed there. Each phrase parser
    must match the entire string or return None. Right after them come the
    natural-language existentials, ``there exists x such that BODY`` and
    ``there exists a [unique] [set] Y such that/that/=/, ...``; see
    `_parse_natural_existential`. Like ``exists x, BODY``, they extend as
    far to the right as the string goes. Then any theory phrase *embedded*
    in a longer string (`environment.phrase_spans`) is wrapped in
    parentheses so that the connective grammar below cannot cut it apart:
    "Q(w) and w is h, i, j, or k" reads as "Q(w) and (w is h, i, j, or k)".)

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

    # Theory phrases that contain a connective or "=" must get the whole
    # string before the grammar below cuts it up (see
    # `TheoryEnvironment.phrase_parsers`).
    for phrase_parser in environment.phrase_parsers:
        formula = phrase_parser(s, bound_vars)
        if formula is not None:
            return formula

    existential = _parse_natural_existential(s, bound_vars, environment)
    if existential is not None:
        return existential

    # A theory phrase sitting inside a larger formula is fenced off before the
    # grammar can cut it at one of its own connective words.
    protected = _protect_phrases(s, environment)
    if protected != s:
        return _parse_formula_conventional(protected, bound_vars, environment)

    m = re.match(
        r"^(?:for all|forall)\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)+)\s+such\s+that\s*:?\s*(.*)$",
        s,
        flags=re.I,
    )
    if m:
        names = [name.strip() for name in m.group(1).split(",")]
        body = _parse_formula_conventional(m.group(2), bound_vars | set(names), environment)
        for name in reversed(names):
            body = fl.ForAll(name, body)
        return body

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
        r"^(?:exists|there exists)\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)+)\s+such\s+that\s*:?\s*(.*)$",
        s,
        flags=re.I,
    )
    if m:
        names = [name.strip() for name in m.group(1).split(",")]
        body = _parse_formula_conventional(m.group(2), bound_vars | set(names), environment)
        for name in reversed(names):
            body = fl.Exists(name, body)
        return body

    m = re.match(
        r"^(?:exists|there exists)\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*(.*)$",
        s,
        flags=re.I,
    )
    if m:
        var = m.group(1)
        try:
            body = _parse_formula_conventional(m.group(2), bound_vars | {var}, environment)
        except ValueError as error:
            if _ARTICLE_FORM_START_RE.match(s):
                # "there exists a ..." read as "the variable a, then a body"
                # failed; most likely the article form was meant.
                raise ValueError(f"Cannot read {s!r} ({error}). {_EXISTENTIAL_FORMS_HELP}") from None
            raise
        return fl.Exists(var, body)

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
