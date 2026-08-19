


"""Set-theory vocabulary, surface syntax, and proof elaborators.

Set-specific proof forms are not added as primitive rules to the logical
kernel.  In particular, a natural-language ``Subset proof below`` is lowered
to Universal Generalization plus Conditional Introduction before
``ProofLogic`` validates it.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

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
    variable = tl.VariableTerm(var_name)
    return fl.ForAll(
        var_name,
        fl.Implies(
            membership_formula(variable, left),
            membership_formula(variable, right),
        ),
    )


def try_parse_set_expression(text: str, bound_vars: set) -> Optional[SurfaceExpression]:
    """Parse membership and subset wording before the generic formula parser."""

    s = re.sub(r"\s+", " ", text.strip().rstrip(".")).strip()

    m = re.match(r"^(.+?)\s+is\s+(?:a\s+)?subset\s+of\s+(.+)$", s, flags=re.I)
    if m:
        left = try_parse_set_term(m.group(1), bound_vars)
        right = try_parse_set_term(m.group(2), bound_vars)
        if left is not None and right is not None:
            return SurfaceExpression("subset", (left, right), text)

    m = re.match(r"^(.+?)\s+has\s+no\s+elements$", s, flags=re.I)
    if m:
        set_term = try_parse_set_term(m.group(1), bound_vars)
        if set_term is not None:
            witness = "__no_elements_witness"
            return SurfaceExpression(
                "core",
                fl.ForAll(witness, fl.Not(membership_formula(tl.VariableTerm(witness), set_term))),
                text,
            )

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


def parse_set_formula(text: str, bound_vars: Optional[set] = None) -> Optional[fl.Formula]:
    """Public convenience parser for set expressions.

    Subset notation is returned in its definitionally expanded core form.
    """

    expression = try_parse_set_expression(text, bound_vars or set())
    if expression is None:
        return None
    if expression.kind == "core":
        return expression.value
    if expression.kind == "subset":
        left, right = expression.value
        return subset_formula(left, right)
    return None


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


SET_DECLARATIONS = [
    pl.Declaration(EMPTY_SET_SYMBOL, pl.DeclarationKind.OBJECT, type_name="set"),
    pl.Declaration(MEMBERSHIP_SYMBOL, pl.DeclarationKind.PREDICATE, arity=2),
]

SET_THEORY_ENVIRONMENT = TheoryEnvironment(
    name="set theory",
    formula_parsers=[try_parse_set_expression],
    line_elaborators=[elaborate_subset_proof],
    rules=[EmptySetPropertyRule(), SetEqualityRule()],
    declarations=SET_DECLARATIONS,
    term_parsers=[try_parse_set_term],
    nested_formula_parsers=[parse_set_formula],
)




