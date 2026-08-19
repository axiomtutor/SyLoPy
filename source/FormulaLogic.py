


"""First-order formula classes and evaluation, building on TermLogic.

Classes:
 - AtomicFormula(predicate, args)
 - And, Or, Not, Implies, Iff
 - Equals(left, right) -- equality between two Terms
 - ForAll(var_name, body), Exists(var_name, body)

Function: evaluate_formula(formula, substitution_schema=None, domains=None)
 - `substitution_schema` maps variable names to values (or Terms) and function
   symbols to callables.  Quantifiers use `domains` (dict) or a default domain
   provided under key '__domain__' in `substitution_schema`.
"""

import typing as _t
import SyLoPy.source.TermLogic as tl


class Formula:
    def __repr__(self):
        raise NotImplementedError


class AtomicFormula(Formula):
    def __init__(self, predicate, args: _t.List[tl.Term]):
        # predicate: a string name looked up in substitution
        self.predicate = predicate
        self.args = list(args)

    def __repr__(self) -> str:
        args = ", ".join(repr(a) for a in self.args)
        return f"{self.predicate}({args})"


class And(Formula):
    def __init__(self, *conjuncts: Formula):
        self.conjuncts = list(conjuncts)

    def __repr__(self):
        return "(" + " ∧ ".join(repr(c) for c in self.conjuncts) + ")"


class Or(Formula):
    def __init__(self, *disjuncts: Formula):
        self.disjuncts = list(disjuncts)

    def __repr__(self):
        return "(" + " ∨ ".join(repr(d) for d in self.disjuncts) + ")"


class Not(Formula):
    def __init__(self, sub: Formula):
        self.sub = sub

    def __repr__(self):
        return f"¬{repr(self.sub)}"


class Implies(Formula):
    def __init__(self, antecedent: Formula, consequent: Formula):
        self.antecedent = antecedent
        self.consequent = consequent

    def __repr__(self):
        return f"({repr(self.antecedent)} → {repr(self.consequent)})"


class Iff(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"({repr(self.left)} ↔ {repr(self.right)})"


class Equals(Formula):
    """The equality predicate `left = right`.

    Unlike And/Or/Implies/Iff (which combine sub-*formulas*), `left` and
    `right` here are Terms -- structurally this is closer to
    AtomicFormula's argument list than to the other connectives. It's
    still given its own Formula subclass rather than folded into
    AtomicFormula('=', [left, right]), because ProofLogic.py's equality
    rules (Reflexivity, Substitution, Symmetry, Transitivity) need to
    recognize equality unambiguously by type, the same way every other
    rule recognizes And/Or/Implies/etc. by isinstance rather than by
    string-comparing a predicate name.
    """
    def __init__(self, left: tl.Term, right: tl.Term):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"{repr(self.left)} = {repr(self.right)}"


class ForAll(Formula):
    def __init__(self, var_name: str, body: Formula):
        self.var = var_name
        self.body = body

    def __repr__(self):
        return f"(∀{self.var}. {repr(self.body)})"


class Exists(Formula):
    def __init__(self, var_name: str, body: Formula):
        self.var = var_name
        self.body = body

    def __repr__(self):
        return f"(∃{self.var}. {repr(self.body)})"


def evaluate_formula(formula: Formula,
                     substitution_schema: _t.Optional[dict] = None,
                     domains: _t.Optional[dict] = None) -> bool:
    if substitution_schema is None:
        substitution_schema = {}
    if domains is None:
        # allow default domain inside substitution_schema under '__domain__'
        domains = substitution_schema.get("__domain__") or {}

    if isinstance(formula, AtomicFormula):
        # Evaluate each term to a concrete value using TermLogic.evaluate_term
        vals = [tl.evaluate_term(t, substitution_schema) if isinstance(t, tl.Term) else t for t in formula.args]

        pred = formula.predicate
        # predicate may be a callable or a string key to look up a callable in the schema
        if isinstance(pred, str):
            if pred not in substitution_schema:
                raise Exception(f"Predicate '{pred}' not found in substitution schema")
            pred = substitution_schema[pred]
        elif not callable(pred):
            raise Exception("Predicate must be a callable or a string key referring to a callable in the substitution schema")

        if not callable(pred):
            raise Exception("Predicate must be callable")

        return bool(pred(*vals))

    if isinstance(formula, And):
        return all(evaluate_formula(c, substitution_schema, domains) for c in formula.conjuncts)

    if isinstance(formula, Or):
        return any(evaluate_formula(d, substitution_schema, domains) for d in formula.disjuncts)

    if isinstance(formula, Not):
        return not evaluate_formula(formula.sub, substitution_schema, domains)

    if isinstance(formula, Implies):
        a = evaluate_formula(formula.antecedent, substitution_schema, domains)
        b = evaluate_formula(formula.consequent, substitution_schema, domains)
        return (not a) or b

    if isinstance(formula, ForAll):
        dom = None
        if isinstance(domains, dict) and formula.var in domains:
            dom = domains[formula.var]
        elif isinstance(domains, dict) and "_" in domains:
            dom = domains["_"]
        else:
            raise Exception(f"No domain provided for universal quantifier variable '{formula.var}'")

        for val in dom:
            subs = substitution_schema.copy()
            subs[formula.var] = val
            if not evaluate_formula(formula.body, subs, domains):
                return False
        return True

    if isinstance(formula, Exists):
        dom = None
        if isinstance(domains, dict) and formula.var in domains:
            dom = domains[formula.var]
        elif isinstance(domains, dict) and "_" in domains:
            dom = domains["_"]
        else:
            raise Exception(f"No domain provided for existential quantifier variable '{formula.var}'")

        for val in dom:
            subs = substitution_schema.copy()
            subs[formula.var] = val
            if evaluate_formula(formula.body, subs, domains):
                return True
        return False

    if isinstance(formula, Iff):
        a = evaluate_formula(formula.left, substitution_schema, domains)
        b = evaluate_formula(formula.right, substitution_schema, domains)
        return a == b

    if isinstance(formula, Equals):
        return tl.evaluate_term(formula.left, substitution_schema) == tl.evaluate_term(formula.right, substitution_schema)

    raise Exception("Unknown formula type")


def term_free_variables(term: tl.Term) -> set:
    """Return the set of variable names that occur free in a term."""
    if isinstance(term, tl.VariableTerm):
        return {term.name}
    if isinstance(term, tl.ConstantTerm):
        return set()
    if isinstance(term, tl.FunctionTerm):
        s = set()
        for a in term.args:
            s |= term_free_variables(a)
        return s
    return set()


def free_variables(formula: Formula) -> set:
    """Return the set of free variable names in a formula."""
    if isinstance(formula, AtomicFormula):
        s = set()
        for t in formula.args:
            if isinstance(t, tl.Term):
                s |= term_free_variables(t)
        return s
    if isinstance(formula, And):
        s = set()
        for c in formula.conjuncts:
            s |= free_variables(c)
        return s
    if isinstance(formula, Or):
        s = set()
        for d in formula.disjuncts:
            s |= free_variables(d)
        return s
    if isinstance(formula, Not):
        return free_variables(formula.sub)
    if isinstance(formula, Implies):
        return free_variables(formula.antecedent) | free_variables(formula.consequent)
    if isinstance(formula, Iff):
        return free_variables(formula.left) | free_variables(formula.right)
    if isinstance(formula, Equals):
        return term_free_variables(formula.left) | term_free_variables(formula.right)
    if isinstance(formula, ForAll) or isinstance(formula, Exists):
        s = free_variables(formula.body)
        if formula.var in s:
            s.remove(formula.var)
        return s
    return set()


def is_closed(formula: Formula) -> bool:
    """A formula is closed when it has no free variables."""
    return len(free_variables(formula)) == 0


def substitute_in_term(term: tl.Term, var_name: str, replacement: tl.Term) -> tl.Term:
    """Return a new Term where occurrences of VariableTerm(var_name) are replaced by `replacement`."""
    if isinstance(term, tl.VariableTerm):
        if term.name == var_name:
            return replacement
        return term
    if isinstance(term, tl.ConstantTerm):
        return term
    if isinstance(term, tl.FunctionTerm):
        new_args = [substitute_in_term(a, var_name, replacement) for a in term.args]
        return tl.FunctionTerm(term.symbol, new_args)
    return term


def substitute_in_formula(formula: Formula, var_name: str, replacement: tl.Term) -> Formula:
    """Return a new Formula where free occurrences of `var_name` are replaced by `replacement`.
    Note: does not rename bound variables — user must ensure no capture.
    """
    if isinstance(formula, AtomicFormula):
        new_args = [substitute_in_term(t, var_name, replacement) if isinstance(t, tl.Term) else t for t in formula.args]
        return AtomicFormula(formula.predicate, new_args)
    if isinstance(formula, And):
        return And(*[substitute_in_formula(c, var_name, replacement) for c in formula.conjuncts])
    if isinstance(formula, Or):
        return Or(*[substitute_in_formula(d, var_name, replacement) for d in formula.disjuncts])
    if isinstance(formula, Not):
        return Not(substitute_in_formula(formula.sub, var_name, replacement))
    if isinstance(formula, Implies):
        return Implies(substitute_in_formula(formula.antecedent, var_name, replacement), substitute_in_formula(formula.consequent, var_name, replacement))
    if isinstance(formula, Iff):
        return Iff(substitute_in_formula(formula.left, var_name, replacement), substitute_in_formula(formula.right, var_name, replacement))
    if isinstance(formula, Equals):
        return Equals(substitute_in_term(formula.left, var_name, replacement), substitute_in_term(formula.right, var_name, replacement))
    if isinstance(formula, ForAll):
        if formula.var == var_name:
            return formula  # variable is bound here; do not substitute
        return ForAll(formula.var, substitute_in_formula(formula.body, var_name, replacement))
    if isinstance(formula, Exists):
        if formula.var == var_name:
            return formula
        return Exists(formula.var, substitute_in_formula(formula.body, var_name, replacement))
    return formula


if __name__ == "__main__":
    # Demo using TermLogic's Term classes
    domain = [1, 2, 3]

    a = tl.ConstantTerm("a", 1)
    b = tl.ConstantTerm("b", 2)
    x = tl.VariableTerm("x")

    # Predicate: "P" holds when value is even
    def P(val):
        return (val % 2) == 0

    # Atomic formula P(x)
    atom = AtomicFormula(P, [x])

    # Evaluate ∃x. P(x) over domain
    ex = Exists("x", atom)
    print("Exists x P(x):", evaluate_formula(ex, substitution_schema={}, domains={"_": domain}))

    # Universal example ∀x. (x == a or x == b)
    def eq_a_or_b(v):
        return v == a.value or v == b.value

    fatom = AtomicFormula(eq_a_or_b, [x])
    un = ForAll("x", fatom)
    print("ForAll x (x==a or x==b):", evaluate_formula(un, substitution_schema={}, domains={"_": domain}))




