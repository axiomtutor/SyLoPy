


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

    m = re.match(r"^(.+?)\s+(?:is\s+(?:a\s+)?subset\s+of|subseteq)\s+(.+)$", s, flags=re.I)
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
to the natural `v` -- citing this axiom means writing it out verbatim, and
nobody should have to type the synthetic name to do that.
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

    for some term X and some formula B. B is not checked for any particular
    shape beyond being a formula at all -- *any* B gives a sound instance,
    which is the schema's entire content. X is likewise unconstrained here
    (that it is actually a set already in scope is `ProofValidator`'s job,
    not this rule's).

    Example::

        1. Let X be any set. (Declaration)
        2. exists Y, forall u, (u in Y <-> (u in X and u is not in X)).
           (Separation)

    (a deliberately trivial B, to show any formula qualifies -- this
    instance asserts the existence of a subset of X cut out by a condition
    no element can satisfy, i.e. the empty set; true, but not the point.
    The point is that `applies` places no constraint on B at all.)
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
        membership_in_X, _B = right.conjuncts
        return (isinstance(membership_in_X, fl.AtomicFormula) and membership_in_X.predicate == MEMBERSHIP_SYMBOL
                and len(membership_in_X.args) == 2 and pl._ast_eq(membership_in_X.args[0], u))


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

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False
        
        # Try to match the universal form first (original behavior)
        if isinstance(phi, fl.ForAll):
            return self._check_universal_form(phi)
        
        # Try to match the instance form (for specific a, b)
        if isinstance(phi, fl.Exists):
            return self._check_instance_form(phi)
        
        return False
    
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
        
        # The disjuncts should be equations involving u and two distinct terms (a and b)
        left1, right1 = eq1.left, eq1.right
        left2, right2 = eq2.left, eq2.right
        
        # Check if the equations have the form (u = a) and (u = b) in either order
        u_eq_a = (pl._ast_eq(left1, u_term) and not pl._ast_eq(right1, u_term))
        a_eq_u = (pl._ast_eq(right1, u_term) and not pl._ast_eq(left1, u_term))
        u_eq_b = (pl._ast_eq(left2, u_term) and not pl._ast_eq(right2, u_term))
        b_eq_u = (pl._ast_eq(right2, u_term) and not pl._ast_eq(left2, u_term))
        
        return (u_eq_a or a_eq_u) and (u_eq_b or b_eq_u)



class UnionAxiomRule(pl.InferenceRule):
    """Axiom of union: for any X, there is a set Y = union(X) whose members
    are exactly those objects that belong to some member of X.
    
    This is a zero-premise rule, cited as "(Axiom of union)".
    
    `phi` must have the exact shape:
        forall X, exists Y, forall u, (u in Y <-> exists v, (v in X and u in v))
    """
    name = "UnionAxiom"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False
        
        if not isinstance(phi, fl.ForAll):
            return False
        X_name = phi.var
        inner1 = phi.body
        
        if not isinstance(inner1, fl.Exists):
            return False
        Y_name = inner1.var
        if Y_name == X_name:
            return False
        inner2 = inner1.body
        
        if not isinstance(inner2, fl.ForAll):
            return False
        u_name = inner2.var
        if u_name in (X_name, Y_name):
            return False
        biconditional = inner2.body
        
        if not isinstance(biconditional, fl.Iff):
            return False
        membership_u_Y, right = biconditional.left, biconditional.right
        
        if not (isinstance(membership_u_Y, fl.AtomicFormula) and
                membership_u_Y.predicate == MEMBERSHIP_SYMBOL and
                len(membership_u_Y.args) == 2 and
                pl._ast_eq(membership_u_Y.args[0], tl.VariableTerm(u_name)) and
                pl._ast_eq(membership_u_Y.args[1], tl.VariableTerm(Y_name))):
            return False
        
        if not isinstance(right, fl.Exists):
            return False
        v_name = right.var
        if v_name in (X_name, Y_name, u_name):
            return False
        body = right.body
        
        if not isinstance(body, fl.And) or len(body.conjuncts) != 2:
            return False
        membership_v_X, membership_u_v = body.conjuncts
        
        return (isinstance(membership_v_X, fl.AtomicFormula) and
                membership_v_X.predicate == MEMBERSHIP_SYMBOL and
                len(membership_v_X.args) == 2 and
                pl._ast_eq(membership_v_X.args[0], tl.VariableTerm(v_name)) and
                pl._ast_eq(membership_v_X.args[1], tl.VariableTerm(X_name)) and
                isinstance(membership_u_v, fl.AtomicFormula) and
                membership_u_v.predicate == MEMBERSHIP_SYMBOL and
                len(membership_u_v.args) == 2 and
                pl._ast_eq(membership_u_v.args[0], tl.VariableTerm(u_name)) and
                pl._ast_eq(membership_u_v.args[1], tl.VariableTerm(v_name)))


class PowerSetAxiomRule(pl.InferenceRule):
    """Axiom of power set: for any X, there is a set Y = P(X) whose members
    are exactly the subsets of X.
    
    This is a zero-premise rule, cited as "(Axiom of power set)".
    
    `phi` must have the exact shape:
        forall X, exists Y, forall u, (u in Y <-> u subset X)
    
    where "u subset X" is the standard subset formula (forall v, (v in u -> v in X)).
    """
    name = "PowerSetAxiom"
    premise_arity = 0

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        if candidates:
            return False
        
        if not isinstance(phi, fl.ForAll):
            return False
        X_name = phi.var
        inner1 = phi.body
        
        if not isinstance(inner1, fl.Exists):
            return False
        Y_name = inner1.var
        if Y_name == X_name:
            return False
        inner2 = inner1.body
        
        if not isinstance(inner2, fl.ForAll):
            return False
        u_name = inner2.var
        if u_name in (X_name, Y_name):
            return False
        biconditional = inner2.body
        
        if not isinstance(biconditional, fl.Iff):
            return False
        membership_u_Y, subset_clause = biconditional.left, biconditional.right
        
        if not (isinstance(membership_u_Y, fl.AtomicFormula) and
                membership_u_Y.predicate == MEMBERSHIP_SYMBOL and
                len(membership_u_Y.args) == 2 and
                pl._ast_eq(membership_u_Y.args[0], tl.VariableTerm(u_name)) and
                pl._ast_eq(membership_u_Y.args[1], tl.VariableTerm(Y_name))):
            return False
        
        u_term = tl.VariableTerm(u_name)
        X_term = tl.VariableTerm(X_name)
        return pl._ast_eq(subset_clause, subset_formula(u_term, X_term))


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
    that is not itself the uniqueness clause) and is otherwise unconstrained
    -- any formula qualifies, exactly as for Separation.

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
        return pl._ast_eq(B_xy_again, B_xy)


SET_DECLARATIONS = [
    pl.Declaration(EMPTY_SET_SYMBOL, pl.DeclarationKind.OBJECT, type_name="set"),
    pl.Declaration(MEMBERSHIP_SYMBOL, pl.DeclarationKind.PREDICATE, arity=2),
]

SET_THEORY_ENVIRONMENT = TheoryEnvironment(
    name="set theory",
    formula_parsers=[try_parse_set_expression],
    line_elaborators=[elaborate_subset_proof],
    rules=[EmptySetPropertyRule(), SetEqualityRule(), SeparationSchemaRule(), ReplacementSchemaRule(),
           PairingAxiomRule(), UnionAxiomRule(), PowerSetAxiomRule(), InfinityAxiomRule()],
    axioms=SET_AXIOMS,
    declarations=SET_DECLARATIONS,
    term_parsers=[try_parse_set_term],
    nested_formula_parsers=[parse_set_formula],
)





