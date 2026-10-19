


"""Set-theory vocabulary, surface syntax, and proof elaborators.

Set-specific proof forms are not added as primitive rules to the logical
kernel.  In particular, a natural-language ``Subset proof below`` is lowered
to Universal Generalization plus Conditional Introduction before
``ProofLogic`` validates it.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.ProofElaboration import (
    CoreOrigin,
    ElaborationError,
    SurfaceExpression,
    SurfaceLine,
    SurfaceSubproof,
    TheoryEnvironment,
)


EMPTY_SET_SYMBOL = "EmptySet"
MEMBERSHIP_SYMBOL = "In"
SUBSET_BOUND_VARIABLE = "__subset_element"

EMPTY_SET = tl.ConstantTerm(EMPTY_SET_SYMBOL, EMPTY_SET_SYMBOL)


def _name_term(name: str, bound_vars: set) -> tl.Term:
    return tl.VariableTerm(name) if name in bound_vars else tl.ConstantTerm(name, name)


def try_parse_set_term(text: str, bound_vars: Optional[set] = None) -> Optional[tl.Term]:
    """Parse the small natural-language set-term vocabulary."""

    bound_vars = bound_vars or set()
    s = re.sub(r"\s+", " ", text.strip().rstrip(".")).strip()
    if re.fullmatch(r"(?:the\s+)?empty\s+set|∅", s, flags=re.I):
        return EMPTY_SET
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
        return _name_term(s, bound_vars)
    return None


def membership_formula(element: tl.Term, set_term: tl.Term) -> fl.Formula:
    return fl.AtomicFormula(MEMBERSHIP_SYMBOL, [element, set_term])


def subset_formula(left: tl.Term, right: tl.Term, var_name: str = SUBSET_BOUND_VARIABLE) -> fl.Formula:
    # The generated element variable must not capture a variable occurring in
    # either set term, even when a caller uses the default name explicitly.
    used_names = fl.term_names(left) | fl.term_names(right)
    var_name = _fresh_generated_variable_name(used_names, var_name)
    variable = tl.VariableTerm(var_name)
    return fl.ForAll(
        var_name,
        fl.Implies(
            membership_formula(variable, left),
            membership_formula(variable, right),
        ),
    )


# --- Set-display sugar: `{a, b}`, `{u in X: P(u)}`, "x is a or b", "S contains exactly a and b" ---
#
# A braced expression -- an enumeration `{a, b}` or a builder `{u in X: P(u)}` --
# is deliberately NOT a term. As `PAIRING_AXIOM`'s docstring explains, a function
# symbol for "the pair of a and b" has to wait until a proof has derived the
# pair's existence *and* uniqueness and promoted it. Instead, a display is sugar
# that exists only next to a relation, and desugars into ordinary formulas the
# kernel already understands. Writing "v in D" for "v belongs to the set that the
# display D describes":
#
#     Y = D  /  D = Y               ==>  forall v, (In(v, Y) iff (v in D))
#     x is in D                     ==>  x in D
#     x is not in D                 ==>  not (x in D)
#
# where "v in D" unfolds, depending on the display, as
#
#     {a, b}            :  v = a or v = b
#     {u in X: P(u)}    :  In(v, X) and P(v)
#     {y: P(y)}         :  P(v)
#     {F(x): x in X}    :  exists x, (In(x, X) and v = F(x))
#
# Related sentence-level sugar, also pure disjunction/biconditional:
#
#     x is a or b                    ==>  x = a or x = b     (also "x is a, b, or c")
#     S contains exactly a, b and c  ==>  S = {a, b, c}
#
# A display is not accepted anywhere else (for example as a function argument),
# because there is no term for it to be.

_DISPLAY_PATTERN = r"\{[^{}]*\}"
_VARIABLE_LIKE = re.compile(r"[A-Za-z][0-9_']*")
_ELEMENT_NAME_CANDIDATES = ["u", "v", "w", "t", "s", "r"]
_NAME = r"[A-Za-z_][A-Za-z0-9_]*"


def _parse_enumeration(text: str, bound_vars: set) -> Optional[List[tl.Term]]:
    """Parse ``{t1, t2, ...}`` into its element terms, or return None."""

    m = re.fullmatch(r"\{\s*([^{}]*?)\s*\}", text.strip())
    if not m:
        return None
    pieces = [piece.strip() for piece in m.group(1).split(",")]
    if not pieces or any(not piece for piece in pieces):
        return None
    terms = [try_parse_set_term(piece, bound_vars) for piece in pieces]
    if any(term is None for term in terms):
        return None
    return terms


def _term_names(term: tl.Term) -> set:
    return fl.term_names(term)


def _fresh_generated_variable_name(used_names: set, preferred: str, candidates=()) -> str:
    """Pick an unused generated binder name, including when candidates are exhausted."""
    for candidate in candidates:
        if candidate not in used_names:
            return candidate
    name = preferred
    suffix = 1
    while name in used_names:
        name = f"{preferred}_{suffix}"
        suffix += 1
    return name


def _equals_any(element: tl.Term, options: List[tl.Term]) -> fl.Formula:
    """``element = o1 or element = o2 or ...`` (just ``element = o1`` for one)."""

    equalities = [fl.Equals(element, option) for option in options]
    return equalities[0] if len(equalities) == 1 else fl.Or(*equalities)


class _SetDisplay:
    """A braced set expression, seen as a membership condition.

    `names`: every name the expression mentions, so a fresh variable can avoid them.
    `bound`: the names it binds internally (an element term may not use them).
    `variable`: the expression's own variable, reused as the quantified variable
        of "Y = {...}" when that is free of clashes (so `Y = {u in X: P(u)}`
        reads `forall u, ...` rather than `forall v, ...`).
    """

    def __init__(self, names, condition, bound=(), variable=None):
        self.names = set(names)
        self._condition = condition
        self.bound = set(bound)
        self.variable = variable

    def contains(self, element: tl.Term) -> fl.Formula:
        """The formula saying `element` belongs to the set this display describes."""

        clash = fl.term_names(element) & self.bound
        if clash:
            raise ValueError(
                f"{sorted(clash)[0]!r} cannot be used as an element of this set expression: "
                "that name is bound inside the expression"
            )
        return self._condition(element)


def _enumeration_display(elements: List[tl.Term]) -> _SetDisplay:
    names = set()
    for element in elements:
        names |= fl.term_names(element)
    return _SetDisplay(names, lambda element: _equals_any(element, elements))


def _split_once_at_colon(text: str) -> Optional[Tuple[str, str]]:
    import SyLoPy.source.ProofParser as pp  # late import: ProofParser imports this module lazily too

    try:
        parts = pp.split_top_level(text, ":")
    except ValueError:
        return None
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    return parts[0].strip(), parts[1].strip()


def _parse_builder(text: str, bound_vars: set) -> Optional[_SetDisplay]:
    """Parse ``{u in X: P(u)}``, ``{y: P(y)}`` or ``{F(x): x in X}``, or return None."""

    import SyLoPy.source.ProofParser as pp

    m = re.fullmatch(r"\{(.*)\}", text.strip(), flags=re.S)
    if not m:
        return None
    halves = _split_once_at_colon(m.group(1))
    if halves is None:
        return None
    head, body = halves

    m_in = re.fullmatch(rf"({_NAME})\s+in\s+(.+)", head, flags=re.I)
    if m_in:  # {u in X: P(u)}
        variable = m_in.group(1)
        source = try_parse_set_term(m_in.group(2), bound_vars)
        if source is None:
            return None
        predicate = pp.parse_formula(body, bound_vars | {variable})
        return _SetDisplay(
            fl.formula_names(predicate) | fl.term_names(source) | {variable},
            lambda element: fl.And(
                membership_formula(element, source),
                fl.substitute_in_formula(predicate, variable, element),
            ),
            bound=fl.bound_variable_names(predicate),
            # If this binder shadows an enclosing variable, let the equality
            # expansion choose a fresh display-element name. Otherwise the
            # generated forall can capture an outer occurrence in the range set.
            variable=None if variable in bound_vars else variable,
        )

    if re.fullmatch(_NAME, head):  # {y: P(y)}
        variable = head
        predicate = pp.parse_formula(body, bound_vars | {variable})
        return _SetDisplay(
            fl.formula_names(predicate) | {variable},
            lambda element: fl.substitute_in_formula(predicate, variable, element),
            bound=fl.bound_variable_names(predicate),
            # If this binder shadows an enclosing variable, let the equality
            # expansion choose a fresh display-element name. Otherwise the
            # generated forall can capture an outer occurrence in the range set.
            variable=None if variable in bound_vars else variable,
        )

    return _parse_replacement_builder(head, body, bound_vars)  # {F(x): x in X}


def _parse_replacement_builder(head: str, body: str, bound_vars: set) -> Optional[_SetDisplay]:
    """``{t(x): x in X}`` -- the values of a term as ``x`` ranges over a set.

    The body is a list of clauses joined by "and" or commas. Clauses of the
    form ``x in X`` say what the variables range over; any other clause is an
    extra condition on them.
    """

    import SyLoPy.source.ProofParser as pp

    clauses: List[str] = []
    try:
        for piece in pp.split_top_level(body, " and "):
            clauses.extend(pp.split_top_level(piece, ","))
    except ValueError:
        return None
    ranges: List[Tuple[str, tl.Term]] = []
    extras: List[str] = []
    for clause in clauses:
        m = re.fullmatch(rf"({_NAME})\s+in\s+(.+)", clause.strip(), flags=re.I)
        source = try_parse_set_term(m.group(2), bound_vars) if m else None
        if m and source is not None:
            ranges.append((m.group(1), source))
        else:
            extras.append(clause.strip())
    if not ranges:
        return None

    variables = [name for name, _source in ranges]
    inner_bound = bound_vars | set(variables)
    head_term = pp.parse_term(head, inner_bound)
    extra_formulas = [pp.parse_formula(text, inner_bound) for text in extras]

    # Range sets are parsed in the surrounding scope, before the comprehension
    # variables bind. If a range set mentions an outer variable whose name is
    # also used as a comprehension variable, the generated Exists would capture
    # that occurrence. Alpha-rename those local binders (and their body
    # occurrences) before assembling the formula; keep the source terms intact.
    source_free_variables = set().union(
        *(fl.term_free_variables(source) for _name, source in ranges)
    )
    captured_names = set(variables) & source_free_variables
    used_names = set(bound_vars) | set(variables) | fl.term_names(head_term)
    for _name, source in ranges:
        used_names |= fl.term_names(source)
    for formula in extra_formulas:
        used_names |= fl.formula_names(formula)

    renamed = {}
    for name in variables:
        if name in captured_names and name not in renamed:
            fresh = _fresh_generated_variable_name(used_names, f"__set_builder_{name}")
            renamed[name] = fresh
            used_names.add(fresh)

    for original, fresh in renamed.items():
        replacement = tl.VariableTerm(fresh)
        head_term = fl.substitute_in_term(head_term, original, replacement)
        extra_formulas = [
            fl.substitute_in_formula(formula, original, replacement)
            for formula in extra_formulas
        ]

    binding_ranges = [(renamed.get(name, name), source) for name, source in ranges]
    binding_variables = [renamed.get(name, name) for name in variables]
    names = set(binding_variables) | fl.term_names(head_term)
    bound = set(binding_variables)
    for _name, source in binding_ranges:
        names |= fl.term_names(source)
    for formula in extra_formulas:
        names |= fl.formula_names(formula)
        bound |= fl.bound_variable_names(formula)

    def condition(element: tl.Term) -> fl.Formula:
        conjuncts = [
            membership_formula(tl.VariableTerm(name), source)
            for name, source in binding_ranges
        ]
        conjuncts += extra_formulas
        conjuncts.append(fl.Equals(element, head_term))
        result = conjuncts[0] if len(conjuncts) == 1 else fl.And(*conjuncts)
        for name in reversed(binding_variables):
            result = fl.Exists(name, result)
        return result

    return _SetDisplay(names, condition, bound=bound)


def _parse_display(text: str, bound_vars: set) -> Optional[_SetDisplay]:
    elements = _parse_enumeration(text, bound_vars)
    if elements is not None:
        return _enumeration_display(elements)
    return _parse_builder(text, bound_vars)


def _display_equality(set_term: tl.Term, display: _SetDisplay) -> fl.Formula:
    """``S = D``: S has exactly the members the display describes."""

    set_names = fl.term_names(set_term)
    if display.variable is not None and display.variable not in set_names:
        name = display.variable
    else:
        used = set_names | display.names
        name = _fresh_generated_variable_name(used, "__display_element", _ELEMENT_NAME_CANDIDATES)
    variable = tl.VariableTerm(name)
    return fl.ForAll(name, fl.Iff(membership_formula(variable, set_term), display.contains(variable)))


def _parse_element_list(text: str, bound_vars: set) -> Optional[List[tl.Term]]:
    """``a``, ``a and b``, ``a, b and c``, ``a, b, and c`` -> their terms, or None."""

    pieces = [p.strip() for p in re.split(r"\s*,\s*(?:and\s+)?|\s+and\s+", text.strip()) if p.strip()]
    if not pieces:
        return None
    terms = [try_parse_set_term(piece, bound_vars) for piece in pieces]
    return None if any(term is None for term in terms) else terms


def _try_parse_display_expression(s: str, text: str, bound_vars: set) -> Optional[SurfaceExpression]:
    m = re.match(rf"^(.+?)\s*=\s*({_DISPLAY_PATTERN})$", s)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        display = _parse_display(m.group(2), bound_vars)
        if set_term is not None and display is not None:
            return SurfaceExpression("core", _display_equality(set_term, display), text)

    m = re.match(rf"^({_DISPLAY_PATTERN})\s*=\s*(.+)$", s)
    if m:
        display = _parse_display(m.group(1), bound_vars)
        set_term = try_parse_set_term(m.group(2), bound_vars)
        if set_term is not None and display is not None:
            return SurfaceExpression("core", _display_equality(set_term, display), text)

    m = re.match(rf"^(.+?)\s+is\s+(not\s+)?in\s+({_DISPLAY_PATTERN})$", s, flags=re.I)
    if m:
        element = try_parse_set_term(m.group(1), bound_vars)
        display = _parse_display(m.group(3), bound_vars)
        if element is not None and display is not None:
            formula = display.contains(element)
            return SurfaceExpression("core", fl.Not(formula) if m.group(2) else formula, text)

    m = re.match(r"^(.+?)\s+contains\s+exactly\s+(.+)$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        elements = _parse_element_list(m.group(2), bound_vars)
        if set_term is not None and elements is not None:
            return SurfaceExpression("core", _display_equality(set_term, _enumeration_display(elements)), text)

    # "x is a or b" / "x is a, b, or c". Only variable-like names are accepted
    # as alternatives, so ordinary English such as "n is even or odd" is not
    # misread as a disjunction of equalities.
    m = re.match(r"^(\S+?)\s+is\s+(.+)$", s, flags=re.I)
    if m:
        subject = try_parse_set_term(m.group(1), bound_vars)
        alternatives = [a.strip() for a in re.split(r"\s*,\s*(?:or\s+)?|\s+or\s+", m.group(2).strip())]
        if (subject is not None and len(alternatives) >= 2
                and all(_VARIABLE_LIKE.fullmatch(a) for a in alternatives)):
            options = [_name_term(a, bound_vars) for a in alternatives]
            return SurfaceExpression("core", _equals_any(subject, options), text)

    return None


# Candidate wording for the two phrases that contain "and"/"or"/commas. A
# candidate counts only if the phrase parser accepts exactly that text.
_ALTERNATIVE_NAME = r"[A-Za-z][0-9_']*(?![\w(])"
# Words that begin or join phrases rather than naming the subject of one: "...
# a unique set {a, b} that contains exactly a and b" is not about a set "that".
_NOT_A_SUBJECT = r"(?!(?:that|which|and|or|not|if|then|iff|implies|such)\b)"
_ALTERNATIVES_CANDIDATE = re.compile(
    rf"(?<![\w.]){_NOT_A_SUBJECT}{_NAME}\s+is\s+{_ALTERNATIVE_NAME}"
    rf"(?:(?:\s*,\s*(?:or\s+)?|\s+or\s+){_ALTERNATIVE_NAME})+(?!\s+is\b)",
    re.I,
)
_LISTED_NAME = rf"{_NAME}(?![\w(])"
_CONTAINS_EXACTLY_CANDIDATE = re.compile(
    rf"(?<![\w.]){_NOT_A_SUBJECT}{_NAME}\s+contains\s+exactly\s+{_LISTED_NAME}"
    rf"(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+){_LISTED_NAME})*",
    re.I,
)


def find_phrase_spans(text: str) -> List[Tuple[int, int]]:
    """Spans of `text` that are one set-theory phrase although they contain
    "or"/"and"/commas: "x is a, b, or c" and "S contains exactly a, b and c".

    Used to keep such a phrase whole when it sits inside a larger formula (see
    `TheoryEnvironment.phrase_spans`). Names after "contains exactly" run on
    as long as the list does, so in "S contains exactly a and b and Q" the
    trailing "Q" is read as a third name; parenthesize the phrase to end it.
    """

    spans = []
    for pattern in (_ALTERNATIVES_CANDIDATE, _CONTAINS_EXACTLY_CANDIDATE):
        for match in pattern.finditer(text):
            if _try_parse_display_expression(match.group(0), match.group(0), set()) is not None:
                spans.append(match.span())
    return spans


def try_parse_set_expression(text: str, bound_vars: set) -> Optional[SurfaceExpression]:
    """Parse membership and subset wording before the generic formula parser."""

    s = re.sub(r"\s+", " ", text.strip().rstrip(".")).strip()

    display = _try_parse_display_expression(s, text, bound_vars)
    if display is not None:
        return display

    # Negative subset phrasing must be recognized before the generic connective
    # grammar sees "not". Expand it to the negation of the ordinary subset formula.
    m = re.match(
        r"^(.+?)\s+(?:is\s+not\s+(?:(?:a\s+)?subset\s+of|subseteq)|not\s+(?:subseteq|subset\s+of))\s+(.+)$",
        s, flags=re.I,
    )
    if m:
        left = try_parse_set_term(m.group(1), bound_vars)
        right = try_parse_set_term(m.group(2), bound_vars)
        if left is not None and right is not None:
            return SurfaceExpression("core", fl.Not(subset_formula(left, right)), text)

    m = re.match(r"^(.+?)\s+(?:is\s+(?:a\s+)?subset\s+of|subseteq|subset)\s+(.+)$", s, flags=re.I)
    if m:
        left = try_parse_set_term(m.group(1), bound_vars)
        right = try_parse_set_term(m.group(2), bound_vars)
        if left is not None and right is not None:
            return SurfaceExpression("subset", (left, right), text)

    m = re.match(r"^(.+?)\s+has\s+no\s+elements$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        if set_term is not None:
            # Avoid shadowing a same-named set variable from the surrounding scope.
            used_names = set(bound_vars or ()) | fl.term_names(set_term)
            witness = _fresh_generated_variable_name(
                used_names, "__no_elements_witness", _ELEMENT_NAME_CANDIDATES
            )
            return SurfaceExpression(
                "core",
                fl.ForAll(witness, fl.Not(membership_formula(tl.VariableTerm(witness), set_term))),
                text,
            )

    # Empty and nonempty claims desugar to ordinary quantifiers. Generated binders
    # must not capture the name of the set or variables from the surrounding scope.
    m = re.match(r"^(.+?)\s+is\s+not\s+nonempty$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        if set_term is not None:
            used_names = set(bound_vars or ()) | fl.term_names(set_term)
            witness = _fresh_generated_variable_name(
                used_names, "__nonempty_witness", _ELEMENT_NAME_CANDIDATES
            )
            return SurfaceExpression(
                "core", fl.Not(fl.Exists(witness, membership_formula(tl.VariableTerm(witness), set_term))), text
            )

    m = re.match(r"^(.+?)\s+is\s+(?:not\s+)?empty$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        if set_term is not None:
            used_names = set(bound_vars or ()) | fl.term_names(set_term)
            witness = _fresh_generated_variable_name(
                used_names, "__empty_witness", _ELEMENT_NAME_CANDIDATES
            )
            if re.search(r"\s+is\s+not\s+empty$", s, flags=re.I):
                return SurfaceExpression(
                    "core", fl.Exists(witness, membership_formula(tl.VariableTerm(witness), set_term)), text
                )
            return SurfaceExpression(
                "core", fl.ForAll(witness, fl.Not(membership_formula(tl.VariableTerm(witness), set_term))), text
            )

    m = re.match(r"^(.+?)\s+is\s+nonempty$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        if set_term is not None:
            used_names = set(bound_vars or ()) | fl.term_names(set_term)
            witness = _fresh_generated_variable_name(
                used_names, "__nonempty_witness", _ELEMENT_NAME_CANDIDATES
            )
            return SurfaceExpression(
                "core", fl.Exists(witness, membership_formula(tl.VariableTerm(witness), set_term)), text
            )

    m = re.match(r"^(.+?)\s+has\s+an?\s+element$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        if set_term is not None:
            used_names = set(bound_vars or ()) | fl.term_names(set_term)
            witness = _fresh_generated_variable_name(
                used_names, "__element_witness", _ELEMENT_NAME_CANDIDATES
            )
            return SurfaceExpression(
                "core", fl.Exists(witness, membership_formula(tl.VariableTerm(witness), set_term)), text
            )

    m = re.match(r"^(.+?)\s+does\s+not\s+belong\s+to\s+(.+)$", s, flags=re.I)
    if m:
        element = try_parse_set_term(m.group(1), bound_vars)
        set_term = try_parse_set_term(m.group(2), bound_vars)
        if element is not None and set_term is not None:
            return SurfaceExpression("core", fl.Not(membership_formula(element, set_term)), text)

    m = re.match(r"^(.+?)\s+does\s+not\s+contain\s+(.+)$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        element = try_parse_set_term(m.group(2), bound_vars)
        if element is not None and set_term is not None:
            return SurfaceExpression("core", fl.Not(membership_formula(element, set_term)), text)

    m = re.match(r"^(.+?)\s+is\s+an?\s+element\s+of\s+(.+)$", s, flags=re.I)
    if m:
        element = try_parse_set_term(m.group(1), bound_vars)
        set_term = try_parse_set_term(m.group(2), bound_vars)
        if element is not None and set_term is not None:
            return SurfaceExpression("core", membership_formula(element, set_term), text)

    m = re.match(r"^(.+?)\s+is\s+not\s+in\s+(.+)$", s, flags=re.I)
    if m:
        element = try_parse_set_term(m.group(1), bound_vars)
        set_term = try_parse_set_term(m.group(2), bound_vars)
        if element is not None and set_term is not None:
            return SurfaceExpression("core", fl.Not(membership_formula(element, set_term)), text)

    m = re.match(r"^(.+?)\s+is\s+in\s+(.+)$", s, flags=re.I)
    if m:
        element = try_parse_set_term(m.group(1), bound_vars)
        set_term = try_parse_set_term(m.group(2), bound_vars)
        if element is not None and set_term is not None:
            return SurfaceExpression("core", membership_formula(element, set_term), text)

    return None


_BOUNDED_QUANTIFIER_NAME = r"[A-Za-z_][A-Za-z0-9_]*"

_BOUNDED_QUANTIFIER_SPAN_RE = re.compile(
    rf"(?<![\w.])(?:for\s+all|forall|there\s+exists|exists)\s+"
    rf"{_BOUNDED_QUANTIFIER_NAME}\s+in\s+[^,]+(?:,|\s+we\s+have\s+|\s+such\s+that\s+).*$",
    flags=re.I,
)


def find_bounded_quantifier_spans(text: str) -> List[Tuple[int, int]]:
    """Protect bounded quantifiers embedded in larger formulas."""
    spans = []
    depths = []
    depth = 0
    for ch in text:
        depths.append(depth)
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth = max(0, depth - 1)
    for match in re.finditer(r"\b(?:for\s+all|forall|there\s+exists|exists)\s+", text, flags=re.I):
        start = match.start()
        if start > 0 and depths[start] != 0:
            continue
        end = len(text)
        for then in re.finditer(r"\s+then\s+", text[match.end():], flags=re.I):
            absolute = match.end() + then.start()
            if depths[absolute] == 0:
                end = absolute
                break
        candidate = text[start:end]
        if _BOUNDED_QUANTIFIER_SPAN_RE.fullmatch(candidate.strip()):
            spans.append((start, end))
    return spans


def _parse_bounded_quantifier(text: str, bound_vars: set) -> Optional[fl.Formula]:
    """Parse set-bounded quantifiers into ordinary first-order logic."""
    s = re.sub(r"\s+", " ", text.strip().rstrip(".")).strip()

    forall = re.fullmatch(
        rf"(?:for\s+all|forall)\s+({_BOUNDED_QUANTIFIER_NAME})\s+in\s+(.+?)"
        rf"\s*(?:,\s*|we\s+have\s+)(.+)",
        s, flags=re.I,
    )
    if forall:
        variable, source_text, body_text = forall.groups()
        source = try_parse_set_term(source_text.strip(), bound_vars)
        if source is None:
            return None
        import SyLoPy.source.ProofParser as pp
        body = pp.parse_formula(body_text.strip(), bound_vars | {variable})
        binder = variable
        if variable in bound_vars:
            # The range set is parsed outside this binder, but the body is
            # inside it. Use a fresh internal name so a same-named outer
            # variable in the range set remains free relative to this quantifier.
            used_names = set(bound_vars) | fl.formula_names(body) | fl.term_names(source)
            binder = _fresh_generated_variable_name(used_names, f"__bounded_{variable}")
            body = fl.substitute_in_formula(body, variable, tl.VariableTerm(binder))
        return fl.ForAll(binder, fl.Implies(
            membership_formula(tl.VariableTerm(binder), source), body))

    exists = re.fullmatch(
        rf"(?:there\s+exists|exists)\s+({_BOUNDED_QUANTIFIER_NAME})\s+in\s+(.+?)"
        rf"\s*(?:,\s*|such\s+that\s+)(.+)",
        s, flags=re.I,
    )
    if exists:
        variable, source_text, body_text = exists.groups()
        source = try_parse_set_term(source_text.strip(), bound_vars)
        if source is None:
            return None
        import SyLoPy.source.ProofParser as pp
        body = pp.parse_formula(body_text.strip(), bound_vars | {variable})
        binder = variable
        if variable in bound_vars:
            used_names = set(bound_vars) | fl.formula_names(body) | fl.term_names(source)
            binder = _fresh_generated_variable_name(used_names, f"__bounded_{variable}")
            body = fl.substitute_in_formula(body, variable, tl.VariableTerm(binder))
        return fl.Exists(binder, fl.And(
            membership_formula(tl.VariableTerm(binder), source), body))

    return None

def parse_set_formula(text: str, bound_vars: Optional[set] = None) -> Optional[fl.Formula]:
    """Public convenience parser for set expressions.

    Subset notation is returned in its definitionally expanded core form.
    """

    expression = try_parse_set_expression(text, bound_vars or set())
    if expression is not None:
        if expression.kind == "core":
            return expression.value
        if expression.kind == "subset":
            left, right = expression.value
            return subset_formula(left, right)
    return _parse_bounded_quantifier(text, bound_vars or set())


class EmptySetPropertyRule(pl.InferenceRule):
    """No object belongs to the empty set."""

    name = "EmptySetProperty"
    premise_arity = 0

    def applies(self, candidates, phi) -> bool:
        if candidates or not isinstance(phi, fl.Not):
            return False
        atom = phi.sub
        return (
            isinstance(atom, fl.AtomicFormula)
            and atom.predicate == MEMBERSHIP_SYMBOL
            and len(atom.args) == 2
            and pl._ast_eq(atom.args[1], EMPTY_SET)
        )

    def explain_in_context(self, candidates, phi, context):
        if candidates:
            return "EmptySetProperty takes no cited premises."
        if not isinstance(phi, fl.Not):
            return "EmptySetProperty must conclude nonmembership, not membership."
        atom = phi.sub
        if not (isinstance(atom, fl.AtomicFormula)
                and atom.predicate == MEMBERSHIP_SYMBOL and len(atom.args) == 2):
            return "EmptySetProperty must negate an In(element, set) atom."
        if not pl._ast_eq(atom.args[1], EMPTY_SET):
            return "the target must be nonmembership in the empty set"
        return None


def _membership_parts(formula: fl.Formula) -> Optional[Tuple[tl.Term, tl.Term]]:
    """`(element, set)` if `formula` is exactly `In(element, set)`; else `None`."""
    if (isinstance(formula, fl.AtomicFormula) and formula.predicate == MEMBERSHIP_SYMBOL
            and len(formula.args) == 2):
        return formula.args[0], formula.args[1]
    return None


def match_membership_characterization(formula: fl.Formula) -> Optional[Tuple[str, tl.Term, fl.Formula]]:
    """Recognize `forall u, (In(u, S) <-> P(u))` (either side of the
    biconditional may carry the membership atom) and return `(u, S, P)`.

    Purely structural: this says what the formula *looks like*, and makes
    no judgment about what may be inferred from it -- that stays with
    `SetPropertyRule`. It rejects a formula whose set term `S` mentions the
    bound variable `u` itself, since then "u in S" is not a statement about
    one fixed set.
    """
    if not isinstance(formula, fl.ForAll) or not isinstance(formula.body, fl.Iff):
        return None
    var, iff = formula.var, formula.body
    for membership_side, property_side in ((iff.left, iff.right), (iff.right, iff.left)):
        parts = _membership_parts(membership_side)
        if parts is None:
            continue
        element, set_term = parts
        if not pl._ast_eq(element, tl.VariableTerm(var)):
            continue
        if var in fl.term_free_variables(set_term):
            continue
        return var, set_term, property_side
    return None


def _orientations(formula: fl.Formula):
    """`formula`, and also its mirror image when it is an equality: `s = t`
    and `t = s` say the same thing, so an equality may be written either way
    round (as `LeibnizSubstitutionRule` already allows)."""
    yield formula
    if isinstance(formula, fl.Equals):
        yield fl.Equals(formula.right, formula.left)


class SetPropertyRule(pl.InferenceRule):
    """General `Set property`: use a set's defining membership property.

    Cites two lines: a membership characterization
    `forall u, (In(u, S) <-> P(u))`, and an instance of one side of it for
    a particular term `t`. The conclusion is the matching instance of the
    other side. All four directions are accepted, positive and negated::

        In(t, S)      =>  P(t)          P(t)      =>  In(t, S)
        not In(t, S)  =>  not P(t)      not P(t)  =>  not In(t, S)

    Example (the characterization of a pair set, then reasoning about an
    arbitrary x)::

        1. forall u, (In(u, Y) iff (u = a or u = b)). (...)
        2. In(x, Y). (...)
        3. x = a or x = b. (Set property from 1, 2)

    The rule knows nothing about *which* set it is -- the empty set,
    a pair, a union, a power set all work alike; only the cited
    characterization matters. Like `UniversalModusPonensRule`, it bundles
    steps already derivable from Universal Instantiation and Biconditional
    Elimination, so the kernel gains no new logical power. The citation
    order is free: the rule recognizes the characterization wherever it
    appears among the two cited lines.

    One more case: when the property is a disjunction, a cited line that is
    one of its disjuncts gives membership (Disjunction Introduction, then the
    biconditional), and nonmembership gives the negated disjunct::

        1. forall u, (In(u, Y) iff (u = a or u = b)). (...)
        2. x = a. (...)
        3. In(x, Y). (Set property from 1, 2)

    That case runs one way. Membership does not say which disjunct holds,
    and `not x = a` does not exclude `x = b`, so `In(x, Y)` does not give
    `x = a`, and `not x = a` does not give `not In(x, Y)`.

    A line that is just an equality may be written either way round, whether
    it is cited or concluded, positive or negated, and whether it matches a
    disjunct of the property or the whole property. `a = x` does what
    `x = a` does::

        3. a = x. (...)
        4. In(x, Y). (Set property from 1, 3)

    The mirror image is the same statement, so this adds no inference and
    leaves the one-way case one-way. An equality inside a larger formula is
    not turned round; it must match as written.
    """

    name = "SetProperty"
    premise_arity = 2

    def applies(self, candidates, phi) -> bool:
        if len(candidates) != 2 or not all(isinstance(c, fl.Formula) for c in candidates):
            return False
        for characterization, instance in (candidates, candidates[::-1]):
            if self._derives(characterization, instance, phi):
                return True
        return False

    @staticmethod
    def _derives(characterization, instance, phi) -> bool:
        matched = match_membership_characterization(characterization)
        if matched is None:
            return False
        var, set_term, prop = matched
        # Peel matching negations off both sides (nonmembership <-> negated
        # property). An odd number of them reverses the direction of the
        # one-way case below.
        negated = False
        while isinstance(instance, fl.Not) and isinstance(phi, fl.Not):
            instance, phi = instance.sub, phi.sub
            negated = not negated
        # One of instance/phi must be the membership atom; the other is the property instance.
        for membership_is_conclusion in (False, True):
            membership, other = (phi, instance) if membership_is_conclusion else (instance, phi)
            parts = _membership_parts(membership)
            if parts is None:
                continue
            element, member_of = parts
            if not pl._ast_eq(member_of, set_term):
                continue
            for oriented in _orientations(other):
                matcher = pl.FormulaMatcher(var)
                if matcher.match_formula(prop, oriented):
                    bound_to = matcher.mapping.get(var)
                    if bound_to is None or pl._ast_eq(bound_to, element):
                        # If P does not mention u, the match is vacuous; the
                        # instance must still agree exactly with P.
                        return True

            # Equality can supply one disjunct of the membership property.
            # From A (one disjunct of A or B), Disjunction Introduction gives
            # the full property instance, which the biconditional turns into
            # membership. Do not generalize this to conjunctions or arbitrary
            # subformulas: one true conjunct/subformula does not establish a
            # whole defining property.
            #
            # This runs one way only. A disjunct gives membership, and so
            # nonmembership gives the negated disjunct. Membership does not
            # say *which* disjunct holds, and a negated disjunct does not rule
            # out the others, so those directions are not derived. (The
            # whole-property match above is an equivalence: both ways.)
            if isinstance(prop, fl.Or) and membership_is_conclusion != negated:
                for disjunct in prop.disjuncts:
                    for oriented in _orientations(other):
                        disjunct_matcher = pl.FormulaMatcher(var)
                        if not disjunct_matcher.match_formula(disjunct, oriented):
                            continue
                        bound_to = disjunct_matcher.mapping.get(var)
                        if bound_to is None or pl._ast_eq(bound_to, element):
                            return True
        return False

    def explain_in_context(self, candidates, phi, context):
        if len(candidates) != 2 or not all(isinstance(c, fl.Formula) for c in candidates):
            return "SetProperty requires two cited formulas."
        matched_chars = [
            (candidate, match_membership_characterization(candidate))
            for candidate in candidates
        ]
        matched_chars = [(candidate, matched) for candidate, matched in matched_chars if matched]
        if not matched_chars:
            for candidate in candidates:
                if (isinstance(candidate, fl.ForAll)
                        and isinstance(candidate.body, fl.Implies)):
                    implication = candidate.body
                    parts = _membership_parts(implication.antecedent)
                    if parts is not None:
                        return "the membership characterization must be a biconditional, not a one-way conditional"
            return "a cited line must characterize membership in a fixed set by a universal biconditional"

        for _characterization, (var, set_term, prop) in matched_chars:
            # A membership atom anywhere among the cited/target formulas must
            # refer to the same set named by the characterization.
            membership_locations = []
            for candidate in candidates:
                membership_locations.append(_membership_parts(candidate))
            membership_locations.append(_membership_parts(phi))
            for parts in membership_locations:
                if parts is not None and not pl._ast_eq(parts[1], set_term):
                    return "the membership instance must refer to the set named by its characterization"

            # Determine which side is the membership instance and test the
            # same-element and one-way-disjunction boundaries explicitly.
            for membership_is_conclusion in (False, True):
                membership, other = (phi, candidates[0]) if membership_is_conclusion else (candidates[0], phi)
                # Consider either citation order, without depending on it.
                for candidate in candidates:
                    if candidate is not _characterization:
                        membership, other = (
                            (phi, candidate) if membership_is_conclusion
                            else (candidate, phi)
                        )
                        parts = _membership_parts(membership)
                        if parts is None or not pl._ast_eq(parts[1], set_term):
                            continue
                        element = parts[0]
                        for oriented in _orientations(other):
                            matcher = pl.FormulaMatcher(var)
                            if matcher.match_formula(prop, oriented):
                                bound_to = matcher.mapping.get(var)
                                if bound_to is not None and not pl._ast_eq(bound_to, element):
                                    return "the property instance must use the same element as the membership atom"
                            if isinstance(prop, fl.Or):
                                for disjunct in prop.disjuncts:
                                    disjunct_matcher = pl.FormulaMatcher(var)
                                    if not disjunct_matcher.match_formula(disjunct, oriented):
                                        continue
                                    bound_to = disjunct_matcher.mapping.get(var)
                                    if bound_to is not None and not pl._ast_eq(bound_to, element):
                                        return "a property disjunct must use the same element as the membership atom"
                                    allowed = membership_is_conclusion != (
                                        isinstance(other, fl.Not) and isinstance(phi, fl.Not)
                                    )
                                    if not allowed:
                                        return "membership alone does not identify one disjunct of a disjunctive property"
                        if isinstance(prop, fl.Or):
                            return "a disjunct may establish membership, but membership alone cannot establish that disjunct"
        return "the cited instance must match the full defining property or a permitted disjunct in the allowed direction"


def _extract_subset_operands(formula: fl.Formula) -> Optional[Tuple[tl.Term, tl.Term]]:
    """If `formula` has exactly the shape `subset_formula` produces --
    `forall v, (In(v, A) -> In(v, B))` -- return `(A, B)`; otherwise `None`.

    Used by `SetEqualityRule` to recognize two subset facts as being about
    the same pair of sets in opposite directions, without caring how each
    one was derived (elaborated from "Subset proof below" sugar, cited
    from a promoted theorem, or built any other way -- only the resulting
    formula's shape matters, matching every other rule in this module).
    """
    if not isinstance(formula, fl.ForAll):
        return None
    body = formula.body
    if not isinstance(body, fl.Implies):
        return None
    antecedent, consequent = body.antecedent, body.consequent
    if not (isinstance(antecedent, fl.AtomicFormula) and antecedent.predicate == MEMBERSHIP_SYMBOL
            and len(antecedent.args) == 2):
        return None
    if not (isinstance(consequent, fl.AtomicFormula) and consequent.predicate == MEMBERSHIP_SYMBOL
            and len(consequent.args) == 2):
        return None
    bound = tl.VariableTerm(formula.var)
    if not (pl._ast_eq(antecedent.args[0], bound) and pl._ast_eq(consequent.args[0], bound)):
        return None
    return antecedent.args[1], consequent.args[1]


class SetEqualityRule(pl.InferenceRule):
    """Set Extensionality's antisymmetry direction: from `X subset Y` and
    `Y subset X` (cited in either order), infer `X = Y` -- a `Formula
    Logic.Equals` between the two *set terms* themselves, not a
    biconditional of formulas the way `BiconditionalIntroductionRule`
    combines two conditionals.

    Example::

        1.2. X is a subset of the empty set. (Subset proof below) ...
        1.3. The empty set is a subset of X. (The empty set subset theorem)
        1.4. X equals the empty set. (Set Equality from 1.2, 1.3)
    """
    name = "SetEquality"
    premise_arity = 2

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if len(candidates) != 2 or not isinstance(phi, fl.Equals):
            return False
        first, second = _extract_subset_operands(candidates[0]), _extract_subset_operands(candidates[1])
        if first is None or second is None:
            return False
        (a1, b1), (a2, b2) = first, second
        if not (pl._ast_eq(a1, b2) and pl._ast_eq(b1, a2)):
            return False
        return (pl._ast_eq(phi.left, a1) and pl._ast_eq(phi.right, b1)) or \
               (pl._ast_eq(phi.left, b1) and pl._ast_eq(phi.right, a1))

    def explain_in_context(self, candidates, phi, context):
        if not isinstance(phi, fl.Equals):
            return "SetEquality must conclude equality of the two set terms."
        if len(candidates) != 2:
            return "SetEquality requires both subset directions."
        first = _extract_subset_operands(candidates[0]) if isinstance(candidates[0], fl.Formula) else None
        second = _extract_subset_operands(candidates[1]) if isinstance(candidates[1], fl.Formula) else None
        if first is None or second is None:
            return "both cited premises must be subset facts of the form forall u, (In(u, A) -> In(u, B))"
        (a1, b1), (a2, b2) = first, second
        if pl._ast_eq(a1, a2) or pl._ast_eq(b1, b2):
            return "the two subset facts must point in opposite directions"
        if not (pl._ast_eq(a1, b2) and pl._ast_eq(b1, a2)):
            return "the inclusions must concern the same two sets in opposite directions"
        if not ((pl._ast_eq(phi.left, a1) and pl._ast_eq(phi.right, b1))
                or (pl._ast_eq(phi.left, b1) and pl._ast_eq(phi.right, a1))):
            return "the conclusion must equate exactly the two sets in the cited inclusions"
        return None


def _parse_subset_assumption(text: str) -> Optional[Tuple[str, tl.Term]]:
    """Return ``(witness_name, left_set)`` for natural subset assumptions."""

    s = re.sub(r"\s+", " ", text.strip().rstrip(".")).strip()
    patterns = [
        r"^let\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:be\s+)?in\s+(.+)$",
        r"^suppose\s+([A-Za-z_][A-Za-z0-9_]*)\s+is\s+in\s+(.+)$",
        r"^let\s+([A-Za-z_][A-Za-z0-9_]*)\s+be\s+arbitrary\s*,?\s+and\s+suppose\s+(?:\1\s+)?is\s+in\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, s, flags=re.I)
        if match:
            witness = match.group(1)
            set_text = match.group(2)
            set_term = try_parse_set_term(set_text, set())
            if set_term is not None:
                return witness, set_term
    return None


def elaborate_subset_proof(line: SurfaceLine, context):
    """Elaborate ``(Subset proof below)`` to core natural deduction.

    Surface form::

        2. S is a subset of T. (Subset proof below)
         2.1. Let a in S. (Assumption for subset proof)
         ...
         2.n. a is in T. (...)

    Core form::

        2. forall x, In(x,S) -> In(x,T). (UG from subproof below)
          2.__arbitrary. a. (Arbitrary)
          2.__conditional. In(a,S) -> In(a,T).
              (Conditional Introduction from subproof below)
              [the user's 2.1 ... 2.n subproof]
    """

    if "subset proof below" not in line.justification_text.lower():
        return None

    expression = context.parse_surface_expression(line.formula_text)
    if expression.kind != "subset":
        raise ElaborationError(
            "'Subset proof below' requires a conclusion of the form "
            "'S is a subset of T'",
            line.span,
        )
    if len(line.subproofs) != 1:
        raise ElaborationError(
            "a subset proof requires exactly one subproof immediately below it",
            line.span,
        )

    left, right = expression.value
    surface_subproof = line.subproofs[0]
    if not surface_subproof.entries or not isinstance(surface_subproof.entries[0], SurfaceLine):
        raise ElaborationError(
            "a subset proof must begin by introducing an arbitrary object in the left-hand set",
            surface_subproof.span,
        )

    first = surface_subproof.entries[0]
    assumption_info = _parse_subset_assumption(first.formula_text)
    if assumption_info is None:
        raise ElaborationError(
            "a subset proof must begin with wording such as "
            "'Let a in S' or 'Suppose a is in S'",
            first.span,
        )
    witness_name, assumed_set = assumption_info
    if not pl._ast_eq(assumed_set, left):
        raise ElaborationError(
            "the opening assumption of a subset proof must put the arbitrary "
            "object in the left-hand set",
            first.span,
        )

    witness = tl.ConstantTerm(witness_name, witness_name)
    assumption = membership_formula(witness, left)
    target = membership_formula(witness, right)

    body = []
    context.register_origin(first.label, first.span, "subset-proof assumption")
    body.append((first.label, assumption, ("assume",)))
    for entry in surface_subproof.entries[1:]:
        body.append(context.elaborate_entry(entry))

    if len(body) == 1:
        raise ElaborationError(
            "a subset proof must derive membership in the right-hand set",
            line.span,
        )

    last_formula = context.core_formula_of(body[-1])
    if last_formula is None or not pl._ast_eq(last_formula, target):
        last_span = getattr(surface_subproof.entries[-1], "span", line.span)
        raise ElaborationError(
            f"a subset proof must conclude that {witness_name} is in "
            f"{context.display_term(right)}",
            last_span,
        )

    label_base = line.label or f"source_{line.span.start_line}"
    arbitrary_label = f"{label_base}.__arbitrary"
    conditional_label = f"{label_base}.__conditional"

    context.register_origin(
        arbitrary_label, line.span, "subset proof: arbitrary-object introduction", synthetic=True
    )
    context.register_origin(
        conditional_label, line.span, "subset proof: conditional introduction", synthetic=True
    )
    context.register_origin(line.label, line.span, "subset proof")

    flag = fl.AtomicFormula(witness_name, [])
    conditional = fl.Implies(assumption, target)
    generalized = subset_formula(left, right)

    outer_subproof = [
        (arbitrary_label, flag, ("arbitrary",)),
        (
            conditional_label,
            conditional,
            ("rule_below", pl.ConditionalIntroductionRule()),
            body,
        ),
    ]
    return (
        line.label,
        generalized,
        ("rule_below", pl.UniversalGeneralizationRule()),
        outer_subproof,
    )


# ---------------------------------------------------------------------------
# ZFC axioms (Jech's presentation, "Set Theory").  Extensionality through
# Infinity are plain formulas, cited verbatim as "(Axiom)" the same way
# NumberTheory's Times-associativity/distributivity axioms already are: a
# proof writes out the exact quantified statement and matches it structurally
# (`_ast_eq`) against one entry of `SET_AXIOMS`, then works with it by
# ordinary inference (Universal Instantiation, Existential Elimination, ...).
# Separation and Replacement are *schemas* -- "for every property" ranges
# over formulas, which this theory has no way to quantify over -- so each is
# a zero-premise rule instead, matching `EmptySetPropertyRule`'s own
# zero-premise precedent just above: a proof asserts one concrete instance
# outright and cites "(Separation)"/"(Replacement)" directly, the same way
# "(Set property)" cites `EmptySetPropertyRule` with nothing else cited.
#
# Extensionality itself adds no formula here. Jech's axiom has two
# directions: "X=Y -> mutual subset" is a theorem of equality alone in any
# first-order theory (substitute X for Y inside "u in X"), not a set-theoretic
# commitment -- no textbook treatment actually needs to assert it. "mutual
# subset -> X=Y" *is* the real content, and it is already exactly
# `SetEqualityRule`, above (see that class's own docstring). Nothing to add.
# ---------------------------------------------------------------------------

_a = tl.VariableTerm('a')
_b = tl.VariableTerm('b')
_u = tl.VariableTerm('u')
_v = tl.VariableTerm('v')
_X = tl.VariableTerm('X')
_Y = tl.VariableTerm('Y')
_y = tl.VariableTerm('y')
_S = tl.VariableTerm('S')

PAIRING_AXIOM = fl.ForAll('a', fl.ForAll('b', fl.Exists('Y', fl.ForAll(
    'u', fl.Iff(membership_formula(_u, _Y), fl.Or(fl.Equals(_u, _a), fl.Equals(_u, _b)))
))))
"""For any a, b, there is a set Y = {a, b} containing exactly a and b.
Jech's Axiom 2. No function symbol for "the pair of a and b" is introduced
here -- that waits until a proof has actually derived the pair's existence
*and* uniqueness (the latter follows from `SetEqualityRule`) and promotes it,
the project's own standing mechanism for turning a proven fact into reusable
notation, rather than building the shortcut speculatively ahead of it.
"""

UNION_AXIOM = fl.ForAll('X', fl.Exists('Y', fl.ForAll(
    'u', fl.Iff(
        membership_formula(_u, _Y),
        fl.Exists('v', fl.And(membership_formula(_v, _X), membership_formula(_u, _v))),
    )
)))
"""For any X, there is a set Y = union(X) = {u : exists v in X, u in v}.
Jech's Axiom 4 (the empty_set_subset.txt comment's "{u in U: U in X}" is
Jech's informal shorthand for exactly this -- U ranges over members of X,
it is not a separately-declared set). Same "existential only, no function
symbol yet" stance as Pairing.
"""

POWER_SET_AXIOM = fl.ForAll('X', fl.Exists('Y', fl.ForAll(
    'u', fl.Iff(membership_formula(_u, _Y), subset_formula(_u, _X, var_name='v'))
)))
"""For any X, there is a set Y = P(X) = {u : u subset X}. Jech's Axiom 5.
Reuses `subset_formula` directly rather than re-deriving subset notation,
overriding its default (synthetic, `__subset_element`) bound-variable name
to the natural `v`. This full formula remains the form used by the generic
`(Axiom)` citation, which requires the axiom to be restated verbatim; the
named `PowerSetAxiomRule` also accepts the intended instance form.
"""

INFINITY_AXIOM = fl.Exists('X', fl.And(
    membership_formula(EMPTY_SET, _X),
    fl.ForAll('y', fl.Implies(
        membership_formula(_y, _X),
        fl.Exists('S', fl.And(
            fl.ForAll('u', fl.Iff(
                membership_formula(_u, _S),
                fl.Or(membership_formula(_u, _y), fl.Equals(_u, _y)),
            )),
            membership_formula(_S, _X),
        )),
    )),
))
"""There is a set X containing the empty set and closed under
y |-> y union {y}. Jech's Axiom 6. "S = y union {y}" is stated directly by
its membership condition -- (forall u, (u in S <-> (u in y or u = y))) and
S in X -- rather than built from separate Pairing/Union function symbols,
for the same "no function symbols yet" reason as above: it needs nothing
beyond what is already primitive (`In`, `Equals`).
"""

SET_AXIOMS = [PAIRING_AXIOM, UNION_AXIOM, POWER_SET_AXIOM, INFINITY_AXIOM]


class SeparationSchemaRule(pl.InferenceRule):
    """Jech's Axiom 3 (axiom *schema* of separation): for any set X and any
    formula B(u) -- Jech's "property P with parameter p", parameters already
    closed over by whatever B mentions freely -- there exists
    Y = {u in X : B(u)}.

    This is a schema, not a single formula: "for every property" ranges over
    formulas, and this theory cannot bind a formula with a quantifier (that
    would be second-order). So there is no single `fl.Formula` to add to
    `SET_AXIOMS` the way Pairing/Union/Power-Set are above. Instead, *each
    instance* -- each concrete choice of B -- is itself a zero-premise fact a
    proof can assert outright, exactly the way `EmptySetPropertyRule` already
    does for a different zero-premise fact: `premise_arity = 0`, nothing is
    cited, a proof writes the specific instance it needs and cites
    "(Separation)" directly.

    `phi` must have the exact shape::

        exists Y, forall u, (u in Y <-> (u in X and B(u)))

    for some term X and some formula B(u). B may be any formula about `u` and
    whatever parameters it mentions freely -- that is the schema's content --
    but the instance is only an instance of Separation, rather than an
    unbounded or self-referential comprehension, under three side conditions,
    all checked here:

      * `u` and `Y` are distinct variables;
      * X is a term outside both binders (no free `u` or `Y`). An X that
        mentioned `u` would let the "bounding" set vary with the element, so
        the instance could define `{u : B(u)}` outright;
      * `Y` is not free in B. Otherwise B can refer to the set being defined:
        with `B := u not in Y`, any X that has an element gives
        `Y = {u in X : u not in Y}`, which is contradictory and makes the
        whole theory inconsistent.

    That X is actually a set already in scope is `ProofValidator`'s job, not
    this rule's.

    Example::

        1. Let X be any set. (Declaration)
        2. exists Y, forall u, (u in Y <-> (u in X and u is not in X)).
           (Separation)

    (a deliberately trivial B -- this instance asserts the existence of a
    subset of X cut out by a condition no element can satisfy, i.e. the empty
    set; true, but not the point. The point is that B ranges over formulas.)
    """
    name = "Separation"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates or not isinstance(phi, fl.Exists):
            return False
        Y = tl.VariableTerm(phi.var)
        inner = phi.body
        if not isinstance(inner, fl.ForAll):
            return False
        u = tl.VariableTerm(inner.var)
        biconditional = inner.body
        if not isinstance(biconditional, fl.Iff):
            return False
        membership_in_Y, right = biconditional.left, biconditional.right
        if not (isinstance(membership_in_Y, fl.AtomicFormula) and membership_in_Y.predicate == MEMBERSHIP_SYMBOL
                and len(membership_in_Y.args) == 2
                and pl._ast_eq(membership_in_Y.args[0], u) and pl._ast_eq(membership_in_Y.args[1], Y)):
            return False
        if not (isinstance(right, fl.And) and len(right.conjuncts) == 2):
            return False
        membership_in_X, B = right.conjuncts
        if not (isinstance(membership_in_X, fl.AtomicFormula) and membership_in_X.predicate == MEMBERSHIP_SYMBOL
                and len(membership_in_X.args) == 2 and pl._ast_eq(membership_in_X.args[0], u)):
            return False
        # Side conditions that make this Separation rather than a self-referential
        # or unbounded comprehension: u and Y are distinct binders, the bounding
        # set X lies outside both binders, and the new set Y is not free in B
        # (otherwise B can say "u is not in Y" and the instance is contradictory).
        if u.name == Y.name:
            return False
        X_term = membership_in_X.args[1]
        if fl.term_free_variables(X_term) & {u.name, Y.name}:
            return False
        return Y.name not in fl.free_variables(B)

    def explain_in_context(self, candidates, phi, context):
        if candidates:
            return "Separation takes no cited premises."
        if not isinstance(phi, fl.Exists) or not isinstance(phi.body, fl.ForAll):
            return "Separation requires exists Y, forall u, (In(u, Y) iff (In(u, X) and B(u)))"
        Y = tl.VariableTerm(phi.var)
        inner = phi.body
        u = tl.VariableTerm(inner.var)
        if not isinstance(inner.body, fl.Iff):
            return "Separation requires a membership biconditional."
        membership_in_Y, right = inner.body.left, inner.body.right
        if not (isinstance(membership_in_Y, fl.AtomicFormula)
                and membership_in_Y.predicate == MEMBERSHIP_SYMBOL
                and len(membership_in_Y.args) == 2
                and pl._ast_eq(membership_in_Y.args[0], u)
                and pl._ast_eq(membership_in_Y.args[1], Y)):
            return "the left side of the Separation biconditional must be In(u, Y)"
        if not (isinstance(right, fl.And) and len(right.conjuncts) == 2):
            return "the right side of Separation must be In(u, X) and B(u)"
        membership_in_X, B = right.conjuncts
        if not (isinstance(membership_in_X, fl.AtomicFormula)
                and membership_in_X.predicate == MEMBERSHIP_SYMBOL
                and len(membership_in_X.args) == 2
                and pl._ast_eq(membership_in_X.args[0], u)):
            return "the first conjunct must be In(u, X)"
        if u.name == Y.name:
            return "u and Y must be distinct variables"
        X_term = membership_in_X.args[1]
        free_in_X = fl.term_free_variables(X_term)
        if u.name in free_in_X:
            return "the bounding set X must not mention u"
        if Y.name in free_in_X:
            return "the bounding set X must not mention Y"
        if Y.name in fl.free_variables(B):
            return "the defining property B must not mention Y"
        return "formula does not have the exact Separation instance shape"


class PairingAxiomRule(pl.InferenceRule):
    """Axiom of pairing: for any a, b, there is a set Y containing exactly a and b.
    
    This is a zero-premise rule (like `SeparationSchemaRule` and 
    `ReplacementSchemaRule`) that asserts a concrete instance outright,
    cited as "(Axiom of pairing)".
    
    `phi` can have one of two shapes:
    1. Universal form (matching the full axiom):
        forall a, forall b, exists Y, forall u, (u in Y <-> (u = a or u = b))
    
    2. Instance form (instantiated with context variables):
        exists Y, forall u, (u in Y <-> (u = a or u = b))
       where a and b are specific variables from context.
    """
    name = "PairingAxiom"
    premise_arity = 0

    def __init__(self, witness_name: Optional[str] = None):
        self.witness_name = witness_name

    def same_configuration(self, other: object) -> bool:
        """The ordinary axiom-instance rule, or the rule for one particular
        direct witness line (`There is a set Y = {a, b}`): not interchangeable.
        The witness form checks the defining property of the constant it names,
        so it is registered by that name -- the elaborator registers the one it
        builds for each such line (`elaborate_pairing_witness`)."""
        return type(other) is type(self) and self.witness_name == other.witness_name

    def as_requirement(self) -> "PairingAxiomRule":
        """A theorem proved through a direct witness line asks for the Pairing
        rule, not for a rule named after that line's witness: the line's
        defining property is already one of the theorem's premises, and the
        proof that cites the theorem has its own witness, or none."""
        return PairingAxiomRule() if self.witness_name is not None else self

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False

        if self.witness_name is not None:
            return self._check_witness_form(phi)

        # Preserve the ordinary zero-premise axiom-instance behavior.
        if isinstance(phi, fl.ForAll):
            return self._check_universal_form(phi)

        if isinstance(phi, fl.Exists):
            return self._check_instance_form(phi)

        return False

    def _check_witness_form(self, phi: fl.Formula) -> bool:
        """Check the defining property produced by direct witness syntax.

        The witness has already been introduced as an ordinary constant by
        the elaborator. This rule therefore checks only the defining property:
        forall u, (In(u, Y) iff (u = a or u = b)).
        """
        if not isinstance(phi, fl.ForAll):
            return False
        u_name = phi.var
        body = phi.body
        if not isinstance(body, fl.Iff):
            return False
        membership, right = body.left, body.right
        if not (
            isinstance(membership, fl.AtomicFormula)
            and membership.predicate == MEMBERSHIP_SYMBOL
            and len(membership.args) == 2
            and pl._ast_eq(membership.args[0], tl.VariableTerm(u_name))
            and pl._ast_eq(membership.args[1], tl.ConstantTerm(self.witness_name, self.witness_name))
        ):
            return False
        if not isinstance(right, fl.Or) or len(right.disjuncts) != 2:
            return False
        eq1, eq2 = right.disjuncts
        if not (isinstance(eq1, fl.Equals) and isinstance(eq2, fl.Equals)):
            return False

        u_term = tl.VariableTerm(u_name)

        def other_side(eq: fl.Equals) -> Optional[tl.Term]:
            if pl._ast_eq(eq.left, u_term):
                return eq.right
            if pl._ast_eq(eq.right, u_term):
                return eq.left
            return None

        first, second = other_side(eq1), other_side(eq2)
        if first is None or second is None:
            return False
        witness = self.witness_name
        return not (
            witness in fl.term_names(first)
            or witness in fl.term_names(second)
        )

    def _check_universal_form(self, phi: fl.ForAll) -> bool:
        """Check the fully universal form: forall a, forall b, exists Y, forall u, ..."""
        a_name = phi.var
        inner1 = phi.body
        
        if not isinstance(inner1, fl.ForAll):
            return False
        b_name = inner1.var
        if b_name == a_name:
            return False
        inner2 = inner1.body
        
        if not isinstance(inner2, fl.Exists):
            return False
        Y_name = inner2.var
        if Y_name in (a_name, b_name):
            return False
        inner3 = inner2.body
        
        if not isinstance(inner3, fl.ForAll):
            return False
        u_name = inner3.var
        if u_name in (a_name, b_name, Y_name):
            return False
        biconditional = inner3.body
        
        if not isinstance(biconditional, fl.Iff):
            return False
        membership_u_Y, right = biconditional.left, biconditional.right
        
        if not (isinstance(membership_u_Y, fl.AtomicFormula) and 
                membership_u_Y.predicate == MEMBERSHIP_SYMBOL and
                len(membership_u_Y.args) == 2 and
                pl._ast_eq(membership_u_Y.args[0], tl.VariableTerm(u_name)) and
                pl._ast_eq(membership_u_Y.args[1], tl.VariableTerm(Y_name))):
            return False
        
        if not isinstance(right, fl.Or) or len(right.disjuncts) != 2:
            return False
        eq1, eq2 = right.disjuncts
        
        if not (isinstance(eq1, fl.Equals) and isinstance(eq2, fl.Equals)):
            return False
        
        a_term = tl.VariableTerm(a_name)
        b_term = tl.VariableTerm(b_name)
        u_term = tl.VariableTerm(u_name)
        
        return ((pl._ast_eq(eq1.left, u_term) and pl._ast_eq(eq1.right, a_term) and
                 pl._ast_eq(eq2.left, u_term) and pl._ast_eq(eq2.right, b_term)) or
                (pl._ast_eq(eq1.left, u_term) and pl._ast_eq(eq1.right, b_term) and
                 pl._ast_eq(eq2.left, u_term) and pl._ast_eq(eq2.right, a_term)))
    
    def _check_instance_form(self, phi: fl.Exists) -> bool:
        """Check an instantiated form: exists Y, forall u, (u in Y <-> (u = a or u = b))
        where a and b are specific terms (not bound variables)."""
        Y_name = phi.var
        inner1 = phi.body
        
        if not isinstance(inner1, fl.ForAll):
            return False
        u_name = inner1.var
        if u_name == Y_name:
            return False
        biconditional = inner1.body
        
        if not isinstance(biconditional, fl.Iff):
            return False
        membership_u_Y, right = biconditional.left, biconditional.right
        
        if not (isinstance(membership_u_Y, fl.AtomicFormula) and 
                membership_u_Y.predicate == MEMBERSHIP_SYMBOL and
                len(membership_u_Y.args) == 2 and
                pl._ast_eq(membership_u_Y.args[0], tl.VariableTerm(u_name)) and
                pl._ast_eq(membership_u_Y.args[1], tl.VariableTerm(Y_name))):
            return False
        
        if not isinstance(right, fl.Or) or len(right.disjuncts) != 2:
            return False
        eq1, eq2 = right.disjuncts
        
        if not (isinstance(eq1, fl.Equals) and isinstance(eq2, fl.Equals)):
            return False
        
        u_term = tl.VariableTerm(u_name)

        def other_side(eq: fl.Equals) -> Optional[tl.Term]:
            """The term `u` is equated with, if one side is exactly `u`."""
            if pl._ast_eq(eq.left, u_term):
                return eq.right
            if pl._ast_eq(eq.right, u_term):
                return eq.left
            return None

        a_term, b_term = other_side(eq1), other_side(eq2)
        if a_term is None or b_term is None:
            return False
        # The paired terms must be genuinely outside the quantifiers: if one
        # mentioned the bound Y or u, this would not be an instance of
        # Pairing at all (e.g. `u = Y` would make Y a member of itself).
        bound = {u_name, Y_name}
        return not (fl.term_free_variables(a_term) & bound or fl.term_free_variables(b_term) & bound)



def _split_defined_set(phi: fl.Formula) -> Optional[Tuple[Optional[str], str, str, fl.Formula]]:
    """Split ``[forall x,] exists y, forall u, (u in y <-> R)`` into
    ``(x, y, u, R)``, or return `None` if `phi` is not of that shape.

    `x` is the variable the leading ``forall`` binds, and `None` when there is
    no leading ``forall`` -- the form of an axiom already instantiated at a set
    of the proof. Union and Power Set both define the new set `y` by what `u`
    must satisfy to belong to it, and differ only in `R`.
    """
    parameter = None
    if isinstance(phi, fl.ForAll):
        parameter, phi = phi.var, phi.body
    if not isinstance(phi, fl.Exists) or not isinstance(phi.body, fl.ForAll):
        return None
    y_name, u_name = phi.var, phi.body.var
    iff = phi.body.body
    if not isinstance(iff, fl.Iff):
        return None
    parts = _membership_parts(iff.left)
    if parts is None or not (pl._ast_eq(parts[0], tl.VariableTerm(u_name))
                             and pl._ast_eq(parts[1], tl.VariableTerm(y_name))):
        return None
    return parameter, y_name, u_name, iff.right


def _is_the_axioms_set(parameter: Optional[str], binders: List[str], term: tl.Term) -> bool:
    """Is `term` the set a Union or Power Set formula is about, with `binders`
    (the names its quantifiers bind, apart from the leading ``forall x``)?

    The names bound anywhere in the formula must all differ. In the axiom in
    full the set is the variable `parameter`, the leading ``forall`` binds. In
    an instance there is no such variable and the set is any term, provided no
    binder captures it: a free `y`, `u` or the like in the term would make the
    formula say something else (see the two rules' docstrings). A constant is
    never captured, whatever it is called.
    """
    names = ([parameter] if parameter is not None else []) + binders
    if len(set(names)) != len(names):
        return False
    if parameter is not None:
        return pl._ast_eq(term, tl.VariableTerm(parameter))
    return not (fl.term_free_variables(term) & set(binders))


class UnionAxiomRule(pl.InferenceRule):
    """Axiom of union: for any X, there is a set Y = union(X) whose members
    are exactly those objects that belong to some member of X.

    This is a zero-premise rule, cited as "(Axiom of union)". Like
    `PairingAxiomRule` and `SeparationSchemaRule` it checks the shape of the
    formula its line states and introduces nothing; naming the set it
    provides is `Let Y be such a set. (Existence from L)`.

    `phi` has one of two shapes::

        forall X, exists Y, forall u, (u in Y <-> exists v, (v in X and u in v))
        exists Y, forall u, (u in Y <-> exists v, (v in S and u in v))

    The first is the axiom in full. The second is the axiom already
    instantiated at a set S of the proof, which is how a proof usually cites
    it::

        1. Let A be any set. (Declaration)
        2. exists Y, forall u, (In(u, Y) iff (exists v, (In(v, A) and In(u, v)))).
           (Axiom of union)

    The bound variables may have any names, but the names must all differ.
    In the second form S is any term the binders do not capture, so it has no
    free `Y`, `u` or `v`. That is what keeps the instance an instance: with
    S := u it would say that the objects u with some v in u and u in v form a
    set, a comprehension with no bounding set that the axiom does not give.
    """
    name = "UnionAxiom"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False
        split = _split_defined_set(phi)
        if split is None:
            return False
        parameter, y_name, u_name, members = split

        # R is `exists v, (v in S and u in v)`.
        if not isinstance(members, fl.Exists):
            return False
        v_name, body = members.var, members.body
        if not (isinstance(body, fl.And) and len(body.conjuncts) == 2):
            return False
        v_in_set = _membership_parts(body.conjuncts[0])
        u_in_v = _membership_parts(body.conjuncts[1])
        if v_in_set is None or u_in_v is None:
            return False
        V, U = tl.VariableTerm(v_name), tl.VariableTerm(u_name)
        if not (pl._ast_eq(v_in_set[0], V)
                and pl._ast_eq(u_in_v[0], U) and pl._ast_eq(u_in_v[1], V)):
            return False
        return _is_the_axioms_set(parameter, [y_name, u_name, v_name], v_in_set[1])


class PowerSetAxiomRule(pl.InferenceRule):
    """Axiom of power set: for any X, there is a set Y = P(X) whose members
    are exactly the subsets of X.

    This is a zero-premise rule, cited as "(Axiom of power set)". Like
    `PairingAxiomRule` and `SeparationSchemaRule` it checks the shape of the
    formula its line states and introduces nothing; naming the set it
    provides is `Let Y be such a set. (Existence from L)`.

    `phi` has one of two shapes::

        forall X, exists Y, forall u, (u in Y <-> u subset X)
        exists Y, forall u, (u in Y <-> u subset S)

    The first is the axiom in full. The second is the axiom already
    instantiated at a set S of the proof, which is how a proof usually cites
    it::

        1. Let A be any set. (Declaration)
        2. exists Y, forall u, (In(u, Y) iff u subset A). (Axiom of power set)

    "u subset X" is the standard subset formula, `forall w, (w in u -> w in
    X)`, whether it comes from the `subset` syntax or is written out; `w` may
    have any name the other binders do not use.

    The bound variables may have any names, but the names must all differ.
    In the second form S is any term the binders do not capture, so it has no
    free `Y`, `u` or `w`. That is what keeps the instance an instance: with
    S := u it would say that every set u is a member of Y, a set of all sets,
    which the axiom does not give and which Separation refutes.
    """
    name = "PowerSetAxiom"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False
        split = _split_defined_set(phi)
        if split is None:
            return False
        parameter, y_name, u_name, subset_clause = split

        # R is the subset formula `forall w, (w in u -> w in S)`.
        if not isinstance(subset_clause, fl.ForAll):
            return False
        w_name, implication = subset_clause.var, subset_clause.body
        if not isinstance(implication, fl.Implies):
            return False
        w_in_u = _membership_parts(implication.antecedent)
        w_in_set = _membership_parts(implication.consequent)
        if w_in_u is None or w_in_set is None:
            return False
        W, U = tl.VariableTerm(w_name), tl.VariableTerm(u_name)
        if not (pl._ast_eq(w_in_u[0], W) and pl._ast_eq(w_in_u[1], U)
                and pl._ast_eq(w_in_set[0], W)):
            return False
        return _is_the_axioms_set(parameter, [y_name, u_name, w_name], w_in_set[1])


class InfinityAxiomRule(pl.InferenceRule):
    """Axiom of infinity: there is a set X containing the empty set and
    closed under the operation y |-> y union {y}.
    
    This is a zero-premise rule, cited as "(Axiom of infinity)".
    
    `phi` must have the exact shape:
        exists X, (0 in X and forall y, (y in X -> exists S, 
                  (forall u, (u in S <-> (u in y or u = y)) and S in X)))
    
    where 0 represents the empty set.
    """
    name = "InfinityAxiom"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False
        
        if not isinstance(phi, fl.Exists):
            return False
        X_name = phi.var
        body = phi.body
        
        if not isinstance(body, fl.And) or len(body.conjuncts) != 2:
            return False
        membership_empty, closure = body.conjuncts
        
        if not (isinstance(membership_empty, fl.AtomicFormula) and
                membership_empty.predicate == MEMBERSHIP_SYMBOL and
                len(membership_empty.args) == 2 and
                pl._ast_eq(membership_empty.args[0], EMPTY_SET) and
                pl._ast_eq(membership_empty.args[1], tl.VariableTerm(X_name))):
            return False
        
        if not isinstance(closure, fl.ForAll):
            return False
        y_name = closure.var
        if y_name == X_name:
            return False
        inner = closure.body
        
        if not isinstance(inner, fl.Implies):
            return False
        membership_y_X, exists_S = inner.antecedent, inner.consequent
        
        if not (isinstance(membership_y_X, fl.AtomicFormula) and
                membership_y_X.predicate == MEMBERSHIP_SYMBOL and
                len(membership_y_X.args) == 2 and
                pl._ast_eq(membership_y_X.args[0], tl.VariableTerm(y_name)) and
                pl._ast_eq(membership_y_X.args[1], tl.VariableTerm(X_name))):
            return False
        
        if not isinstance(exists_S, fl.Exists):
            return False
        S_name = exists_S.var
        if S_name in (X_name, y_name):
            return False
        S_body = exists_S.body
        
        if not isinstance(S_body, fl.And) or len(S_body.conjuncts) != 2:
            return False
        subset_property, membership_S_X = S_body.conjuncts
        
        if not (isinstance(membership_S_X, fl.AtomicFormula) and
                membership_S_X.predicate == MEMBERSHIP_SYMBOL and
                len(membership_S_X.args) == 2 and
                pl._ast_eq(membership_S_X.args[0], tl.VariableTerm(S_name)) and
                pl._ast_eq(membership_S_X.args[1], tl.VariableTerm(X_name))):
            return False
        
        if not isinstance(subset_property, fl.ForAll):
            return False
        u_name = subset_property.var
        if u_name in (X_name, y_name, S_name):
            return False
        inner_property = subset_property.body
        
        if not isinstance(inner_property, fl.Iff):
            return False
        membership_u_S, right = inner_property.left, inner_property.right
        
        if not (isinstance(membership_u_S, fl.AtomicFormula) and
                membership_u_S.predicate == MEMBERSHIP_SYMBOL and
                len(membership_u_S.args) == 2 and
                pl._ast_eq(membership_u_S.args[0], tl.VariableTerm(u_name)) and
                pl._ast_eq(membership_u_S.args[1], tl.VariableTerm(S_name))):
            return False
        
        if not isinstance(right, fl.Or) or len(right.disjuncts) != 2:
            return False
        membership_u_y, equality = right.disjuncts
        
        u_term = tl.VariableTerm(u_name)
        y_term = tl.VariableTerm(y_name)
        
        return ((isinstance(membership_u_y, fl.AtomicFormula) and
                 membership_u_y.predicate == MEMBERSHIP_SYMBOL and
                 len(membership_u_y.args) == 2 and
                 pl._ast_eq(membership_u_y.args[0], u_term) and
                 pl._ast_eq(membership_u_y.args[1], y_term) and
                 isinstance(equality, fl.Equals) and
                 pl._ast_eq(equality.left, u_term) and
                 pl._ast_eq(equality.right, y_term)) or
                (isinstance(equality, fl.AtomicFormula) and
                 equality.predicate == MEMBERSHIP_SYMBOL and
                 len(equality.args) == 2 and
                 pl._ast_eq(equality.args[0], u_term) and
                 pl._ast_eq(equality.args[1], y_term) and
                 isinstance(membership_u_y, fl.Equals) and
                 pl._ast_eq(membership_u_y.left, u_term) and
                 pl._ast_eq(membership_u_y.right, y_term)))


class ReplacementSchemaRule(pl.InferenceRule):
    """Jech's Axiom schema of replacement: if a formula B(x,y) -- free
    variables x, y, plus whatever parameters are already in scope -- is
    *functional* on a set A (every x in A has exactly one y with B(x,y)),
    then the image {y : exists x in A, B(x,y)} is itself a set.

    Like `SeparationSchemaRule`, this ranges over an arbitrary B and so, like
    it, is a zero-premise rule: the whole instance -- functionality
    hypothesis and image conclusion together -- is asserted directly and
    cited "(Replacement)", the same way a Separation instance is cited
    "(Separation)".

    `phi` must have the exact shape::

        forall x, (x in A -> exists y, (B(x,y) and forall z, (B(x,z) -> z = y)))
        ->
        exists C, forall y, (y in C <-> exists x, (x in A and B(x,y)))

    B is read off the antecedent (the conjunct of the witnessed existential
    that is not itself the uniqueness clause). As for Separation, it ranges
    over formulas but is not a free-for-all: the instance is only a
    Replacement instance when

      * x, y, z and C are four distinct variables;
      * C -- the image set being asserted -- is not free in B (else B
        refers to the set it defines), and z -- bound by the uniqueness
        clause -- is not free in B (else the clause captures it);
      * A is a term outside every binder it sits under (no free x, y, z or
        C). An A mentioning x would be a different set for each x, and the
        image of "the set of all x" is not a set.

    Two structural requirements tie the pieces together, and both follow
    this codebase's standing no-alpha-equivalence discipline (see
    `_ast_eq`'s docstring, and `InductionRule`'s) rather than inventing a
    capture-avoiding renaming scheme for this one rule:

      * The uniqueness clause's B(x,z) must be exactly B(x,y) with y
        replaced by z -- checked with `FormulaLogic.substitute_in_formula`,
        the same primitive `InductionRule` already relies on to build an
        expected comparison target. It is used here only to reconstruct
        what this rule expects to find (never applied to reshape the
        proof's own formula), then compared with `_ast_eq` -- no more
        capture risk than `InductionRule` already carries.
      * x and y must be spelled with the *same* names in the consequent as
        in the antecedent, and A likewise. This rule does not hunt for a
        consistent renaming between the two halves; the proof-writer simply
        reuses the names, which is both the natural way to write "the same
        x and y throughout" and already how every other schema rule in this
        project (Induction included) expects a citation to be written.

    Example (image of A under the trivial functional relation B(x,y) :=
    "y = x", i.e. a long-winded way of asserting A is a set -- chosen only
    to keep the example short; nothing about `applies` is specific to it)::

        1. Let A be any set. (Declaration)
        2. forall x, (x in A -> exists y, (y = x and forall z, (z = x -> z = y)))
           -> exists C, forall y, (y in C <-> exists x, (x in A and y = x)).
           (Replacement)
    """
    name = "Replacement"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates or not isinstance(phi, fl.Implies):
            return False
        antecedent, consequent = phi.antecedent, phi.consequent

        if not isinstance(antecedent, fl.ForAll):
            return False
        x_name = antecedent.var
        functionality = antecedent.body
        if not isinstance(functionality, fl.Implies):
            return False
        membership_x = functionality.antecedent
        if not (isinstance(membership_x, fl.AtomicFormula) and membership_x.predicate == MEMBERSHIP_SYMBOL
                and len(membership_x.args) == 2
                and pl._ast_eq(membership_x.args[0], tl.VariableTerm(x_name))):
            return False
        A_term = membership_x.args[1]

        unique_exists = functionality.consequent
        if not isinstance(unique_exists, fl.Exists):
            return False
        y_name = unique_exists.var
        if y_name == x_name:
            return False
        body = unique_exists.body
        if not (isinstance(body, fl.And) and len(body.conjuncts) == 2):
            return False
        B_xy, uniqueness = body.conjuncts
        if not isinstance(uniqueness, fl.ForAll):
            return False
        z_name = uniqueness.var
        if z_name in (x_name, y_name):
            return False
        step = uniqueness.body
        if not isinstance(step, fl.Implies):
            return False
        expected_B_xz = fl.substitute_in_formula(B_xy, y_name, tl.VariableTerm(z_name))
        if not pl._ast_eq(step.antecedent, expected_B_xz):
            return False
        if not pl._ast_eq(step.consequent, fl.Equals(tl.VariableTerm(z_name), tl.VariableTerm(y_name))):
            return False

        if not isinstance(consequent, fl.Exists):
            return False
        C_name = consequent.var
        outer = consequent.body
        if not isinstance(outer, fl.ForAll) or outer.var != y_name:
            return False
        biconditional = outer.body
        if not isinstance(biconditional, fl.Iff):
            return False
        membership_y = biconditional.left
        if not (isinstance(membership_y, fl.AtomicFormula) and membership_y.predicate == MEMBERSHIP_SYMBOL
                and len(membership_y.args) == 2
                and pl._ast_eq(membership_y.args[0], tl.VariableTerm(y_name))
                and pl._ast_eq(membership_y.args[1], tl.VariableTerm(C_name))):
            return False
        image = biconditional.right
        if not isinstance(image, fl.Exists) or image.var != x_name:
            return False
        image_body = image.body
        if not (isinstance(image_body, fl.And) and len(image_body.conjuncts) == 2):
            return False
        membership_x2, B_xy_again = image_body.conjuncts
        if not (isinstance(membership_x2, fl.AtomicFormula) and membership_x2.predicate == MEMBERSHIP_SYMBOL
                and len(membership_x2.args) == 2
                and pl._ast_eq(membership_x2.args[0], tl.VariableTerm(x_name))
                and pl._ast_eq(membership_x2.args[1], A_term)):
            return False
        if not pl._ast_eq(B_xy_again, B_xy):
            return False
        # Side conditions (as for Separation): the image set C may not occur free in B,
        # z (bound by the uniqueness clause) may not occur free in B, and A must lie
        # outside every binder it sits under.
        if len({x_name, y_name, z_name, C_name}) != 4:
            return False
        if {C_name, z_name} & fl.free_variables(B_xy):
            return False
        return not (fl.term_free_variables(A_term) & {x_name, y_name, z_name, C_name})

    def explain_in_context(self, candidates, phi, context):
        if candidates:
            return "Replacement takes no cited premises."
        if not isinstance(phi, fl.Implies):
            return "Replacement requires a functionality hypothesis implying an image-set conclusion"
        antecedent, consequent = phi.antecedent, phi.consequent
        if not isinstance(antecedent, fl.ForAll):
            return "the functionality hypothesis must universally quantify x"
        x_name = antecedent.var
        functionality = antecedent.body
        if not isinstance(functionality, fl.Implies):
            return "the functionality hypothesis must have the form In(x, A) -> exists y, ..."
        membership_x = functionality.antecedent
        if not (isinstance(membership_x, fl.AtomicFormula)
                and membership_x.predicate == MEMBERSHIP_SYMBOL
                and len(membership_x.args) == 2
                and pl._ast_eq(membership_x.args[0], tl.VariableTerm(x_name))):
            return "the functionality hypothesis must be guarded by In(x, A)"
        A_term = membership_x.args[1]
        unique_exists = functionality.consequent
        if not isinstance(unique_exists, fl.Exists):
            return "the functionality hypothesis must assert existence and uniqueness of an image y"
        y_name = unique_exists.var
        if y_name == x_name:
            return "the variables x and y must be distinct"
        body = unique_exists.body
        if not (isinstance(body, fl.And) and len(body.conjuncts) == 2):
            return "the functionality hypothesis must give both B(x, y) and a uniqueness clause"
        B_xy, uniqueness = body.conjuncts
        if not isinstance(uniqueness, fl.ForAll):
            return "the uniqueness clause must universally quantify a fresh variable z"
        z_name = uniqueness.var
        if z_name in (x_name, y_name):
            return "the variables x, y, and z must be distinct"
        step = uniqueness.body
        if not isinstance(step, fl.Implies):
            return "the uniqueness clause must have the form B(x, z) -> z = y"
        expected_B_xz = fl.substitute_in_formula(B_xy, y_name, tl.VariableTerm(z_name))
        if not pl._ast_eq(step.antecedent, expected_B_xz):
            return "the uniqueness clause must use B(x, z), obtained by substituting z for y in B(x, y)"
        if not pl._ast_eq(step.consequent, fl.Equals(tl.VariableTerm(z_name), tl.VariableTerm(y_name))):
            return "the uniqueness clause must conclude z = y"
        if not isinstance(consequent, fl.Exists):
            return "the consequent must existentially quantify the image set C"
        C_name = consequent.var
        outer = consequent.body
        if not isinstance(outer, fl.ForAll) or outer.var != y_name:
            return "the consequent must reuse the antecedent's y variable"
        if C_name in (x_name, y_name, z_name):
            return "the variables x, y, z, and C must be distinct"
        if not isinstance(outer.body, fl.Iff):
            return "the image-set conclusion must characterize membership by a biconditional"
        membership_y, image = outer.body.left, outer.body.right
        if not (isinstance(membership_y, fl.AtomicFormula)
                and membership_y.predicate == MEMBERSHIP_SYMBOL
                and len(membership_y.args) == 2
                and pl._ast_eq(membership_y.args[0], tl.VariableTerm(y_name))
                and pl._ast_eq(membership_y.args[1], tl.VariableTerm(C_name))):
            return "the image-set conclusion must begin with In(y, C)"
        if not isinstance(image, fl.Exists) or image.var != x_name:
            return "the image-set definition must reuse the antecedent's x variable"
        image_body = image.body
        if not (isinstance(image_body, fl.And) and len(image_body.conjuncts) == 2):
            return "the image-set definition must have In(x, A) and B(x, y)"
        membership_x2, B_xy_again = image_body.conjuncts
        if not (isinstance(membership_x2, fl.AtomicFormula)
                and membership_x2.predicate == MEMBERSHIP_SYMBOL
                and len(membership_x2.args) == 2
                and pl._ast_eq(membership_x2.args[0], tl.VariableTerm(x_name))):
            return "the image-set definition must reuse In(x, A)"
        if not pl._ast_eq(membership_x2.args[1], A_term):
            return "the same bounding set A must appear in both halves of Replacement"
        if not pl._ast_eq(B_xy_again, B_xy):
            return "the image-set definition must reuse the same B(x, y)"
        free_in_B = fl.free_variables(B_xy)
        if C_name in free_in_B:
            return "the image-set variable C must not occur free in B(x, y)"
        if z_name in free_in_B:
            return "the uniqueness variable z must not occur free in B(x, y)"
        free_in_A = fl.term_free_variables(A_term)
        if x_name in free_in_A:
            return "the bounding set A must not mention x"
        if y_name in free_in_A or z_name in free_in_A or C_name in free_in_A:
            return "the bounding set A must not mention y, z, or C"
        return "formula does not have the exact Replacement instance shape"


def elaborate_pairing_witness(entry: SurfaceLine, context) -> Optional[tuple]:
    """Elaborate direct Pairing witness syntax.

    The ordinary natural-existential parser already turns
    there is a set Y = {a, b}
    into Exists Y, P(Y), where P is the membership characterization of the
    displayed set. This elaborator names Y as an ordinary scoped declaration
    and lowers the citation to P(Y), so later Set property steps can use it
    directly.
    """
    if entry.justification_text.strip().lower() != "axiom of pairing":
        return None

    # Keep the existing symbolic existential citation form intact. Direct
    # witness introduction is specifically the natural-language form beginning
    # with "there is" or "there exists".
    surface = entry.formula_text.strip()
    if not re.match(r"^there\s+(?:is|exists)\b", surface, re.I):
        return None

    try:
        parsed = context.parse_core_formula(entry.formula_text)
    except (TypeError, ValueError) as exc:
        raise ElaborationError(str(exc), entry.span) from exc

    if not isinstance(parsed, fl.Exists):
        raise ElaborationError(
            "'Axiom of pairing' witness syntax must introduce an existentially named set, "
            "for example 'There is a set Y = {a, b}'",
            entry.span,
        )

    witness_name = parsed.var
    if context.lookup_declaration(witness_name) is not None:
        raise ElaborationError(
            f"pairing witness '{witness_name}' is already declared in this proof or an enclosing scope",
            entry.span,
        )

    declaration = pl.Declaration(
        name=witness_name,
        kind=pl.DeclarationKind.OBJECT,
        type_name="set-theoretic witness",
    )
    witness_term = tl.ConstantTerm(witness_name, witness_name)
    defining_property = fl.substitute_in_formula(parsed.body, parsed.var, witness_term)

    rule = PairingAxiomRule(witness_name=witness_name)
    if not rule.applies([], defining_property):
        raise ElaborationError(
            "'Axiom of pairing' witness syntax must describe a set containing exactly two terms, "
            "for example 'There is a set Y = {a, b}'",
            entry.span,
        )

    context.register_declaration(declaration, entry.span)
    context.register_origin(entry.label, entry.span)
    # The line cites this exact rule, so the proof must register it: a rule is
    # authorized by its configuration, not by sharing a class with the generic
    # `PairingAxiomRule()` the theory registers (`InferenceRule.same_configuration`).
    context.add_extra_rule(rule)
    return (entry.label, defining_property, ("rule", rule, [], [declaration]))


SET_DECLARATIONS = [
    pl.Declaration(EMPTY_SET_SYMBOL, pl.DeclarationKind.OBJECT, type_name="set"),
    pl.Declaration(MEMBERSHIP_SYMBOL, pl.DeclarationKind.PREDICATE, arity=2),
]

SET_THEORY_ENVIRONMENT = TheoryEnvironment(
    name="set theory",
    formula_parsers=[try_parse_set_expression],
    line_elaborators=[elaborate_subset_proof, elaborate_pairing_witness],
    rules=[EmptySetPropertyRule(), SetPropertyRule(), SetEqualityRule(), SeparationSchemaRule(), ReplacementSchemaRule(),
           PairingAxiomRule(), UnionAxiomRule(), PowerSetAxiomRule(), InfinityAxiomRule()],
    axioms=SET_AXIOMS,
    declarations=SET_DECLARATIONS,
    term_parsers=[try_parse_set_term],
    nested_formula_parsers=[parse_set_formula],
    phrase_parsers=[parse_set_formula],
    phrase_spans=[find_phrase_spans, find_bounded_quantifier_spans],
)





