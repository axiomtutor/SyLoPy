"""Definitions: naming a new thing by a sentence that says what it is.

A definition in mathematics gives a name to something whose existence is
already settled, and asserts nothing new by doing so. "The union of A and B"
names the set whose members are exactly the objects in A or in B; ZF already
proves that there is such a set (and, by Extensionality, only one), so the
name adds nothing that did not follow. That discipline is all of this module,
and it is here once so that every theory defines its words the same way --
set theory defines the union, an algebra module can define a cyclic group, a
number theory module the divisibility relation:

  1. A definition *names* one symbol (`Union`, `Cyclic`) that no other
     definition names and that its own sentence does not use.
  2. Its *defining sentence* says what the symbol means, as a biconditional
     between a use of the symbol and what it stands for::

         In(u, Union(A, B))  iff  (In(u, A) or In(u, B))
         Cyclic(G)           iff  exists g, Generates(g, G)

     This is the sentence a proof cites, for any terms in place of u, A, B or
     G (`Definition`'s docstring says exactly what is accepted).
  3. A definition of a *thing* -- a set, a function value -- *checks that it
     exists*. The sentence gives the symbol the meaning "the thing with this
     property", which is only a meaning if some thing has it. The definition
     carries the existence statement and the evidence for it: an axiom that
     says so (`ByRule`: Separation for the intersection, Power Set for the
     power set) or a proof that derives it from nothing (`ByProof`: the union
     of two sets needs Pairing and Union and a page of reasoning). A
     definition of a *predicate* needs no such evidence: `Cyclic(G)` is
     simply short for what it is defined as.
  4. It adds *no axiom*. Taking the sentence as the meaning of the symbol is
     conservative: every sentence that does not mention the symbol and is
     provable with the definition is provable without it. For a thing this is
     the textbook argument (a symbol defined by a property that exactly one
     thing has can be eliminated everywhere in favor of "the thing with the
     property"), and for a predicate it is plain abbreviation. That is why a
     definition is checked, not assumed: if the evidence is wrong, the
     definition is refused, and so is every line that cites it.

A definition is cited by its title -- `(Definition of union)` -- in any theory
that registers it. The kernel sees an ordinary zero-premise rule, a
`DefinitionRule`, and a rule is how a theory says "this is justified"; but what
the rule is built from is a `Definition`, a statement of what is being named,
not code. That is the difference between a definition and an axiom schema: an
axiom schema is a recognizer written by hand for each axiom, and a definition
is data that one rule checks.

What is not built yet, and where it would go. A function defined by a
description ("the identity of G") needs *unique* existence; it is the same
`Definition` with an `exists!` statement as its `Existence`. A definition whose
evidence uses an earlier definition needs the evidence checked in a theory that
has that definition; today the evidence is checked without any definition (see
`DefinitionRule`), so a proof of existence can only use the theory's axioms.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.ProofElaboration import TheoryEnvironment


class DefinitionError(ValueError):
    """A definition that is not one: raised when it is built, not when it is cited."""


# ---------------------------------------------------------------------------
# Writing formulas the way a proof writes them (for the reasons a refusal gives)
# ---------------------------------------------------------------------------

def show(node) -> str:
    """`node` (a term or a formula) written the way a proof writes it, so that
    a refusal quotes what the proof would say rather than the kernel's symbols:
    ``In(u, Union(A, B)) iff (In(u, A) or In(u, B))``."""
    if isinstance(node, tl.FunctionTerm):
        return f"{node.symbol}({', '.join(show(a) for a in node.args)})"
    if isinstance(node, fl.AtomicFormula):
        return f"{node.predicate}({', '.join(show(a) for a in node.args)})"
    if isinstance(node, fl.And):
        return "(" + " and ".join(show(c) for c in node.conjuncts) + ")"
    if isinstance(node, fl.Or):
        return "(" + " or ".join(show(d) for d in node.disjuncts) + ")"
    if isinstance(node, fl.Not):
        return f"not {show(node.sub)}"
    if isinstance(node, fl.Implies):
        return f"({show(node.antecedent)} -> {show(node.consequent)})"
    if isinstance(node, fl.Iff):
        return f"({show(node.left)} iff {show(node.right)})"
    if isinstance(node, fl.Equals):
        return f"{show(node.left)} = {show(node.right)}"
    if isinstance(node, fl.ForAll):
        return f"forall {node.var}, {show(node.body)}"
    if isinstance(node, fl.Exists):
        return f"exists {node.var}, {show(node.body)}"
    return repr(node)  # a variable or a constant is its name


# ---------------------------------------------------------------------------
# Instantiating and matching
# ---------------------------------------------------------------------------

def _fresh_name(base: str, used: set) -> str:
    """`base`, or `base_1`, `base_2`, ... -- the first that is not in `used`."""
    if base not in used:
        return base
    number = 1
    while f"{base}_{number}" in used:
        number += 1
    return f"{base}_{number}"


def _instantiate_term(term: tl.Term, binding: Dict[str, tl.Term], scope: Dict[str, str]) -> tl.Term:
    """`term` with each variable of `binding` replaced by its term, and each
    variable renamed by `scope` (the quantifiers around it that were renamed)."""
    if isinstance(term, tl.VariableTerm):
        if term.name in scope:
            return tl.VariableTerm(scope[term.name])
        return binding.get(term.name, term)
    if isinstance(term, tl.FunctionTerm):
        return tl.FunctionTerm(term.symbol, [_instantiate_term(a, binding, scope) for a in term.args])
    return term


def _instantiate(formula: fl.Formula, binding: Dict[str, tl.Term], used: set,
                 scope: Optional[Dict[str, str]] = None) -> fl.Formula:
    """`formula` with each free variable named in `binding` replaced by its term.

    A quantifier of `formula` whose variable occurs free in a replacing term
    would capture it, and the result would say something else; so that
    variable is renamed (to a name not in `used`) throughout the quantifier's
    scope. A constant is never captured by a variable, and a quantifier whose
    variable occurs in no replacing term keeps its name.
    """
    scope = scope or {}
    recur = lambda part: _instantiate(part, binding, used, scope)  # noqa: E731
    if isinstance(formula, fl.AtomicFormula):
        return fl.AtomicFormula(formula.predicate, [_instantiate_term(a, binding, scope) for a in formula.args])
    if isinstance(formula, fl.And):
        return fl.And(*[recur(c) for c in formula.conjuncts])
    if isinstance(formula, fl.Or):
        return fl.Or(*[recur(d) for d in formula.disjuncts])
    if isinstance(formula, fl.Not):
        return fl.Not(recur(formula.sub))
    if isinstance(formula, fl.Implies):
        return fl.Implies(recur(formula.antecedent), recur(formula.consequent))
    if isinstance(formula, fl.Iff):
        return fl.Iff(recur(formula.left), recur(formula.right))
    if isinstance(formula, fl.Equals):
        return fl.Equals(_instantiate_term(formula.left, binding, scope),
                         _instantiate_term(formula.right, binding, scope))
    if isinstance(formula, (fl.ForAll, fl.Exists)):
        brought_in = set()
        for term in binding.values():
            brought_in |= fl.term_free_variables(term)
        name = _fresh_name(formula.var, used) if formula.var in brought_in else formula.var
        used.add(name)
        body = _instantiate(formula.body, binding, used, {**scope, formula.var: name})
        return type(formula)(name, body)
    raise TypeError(f"cannot instantiate {formula!r}")


def _match_term(pattern: tl.Term, target: tl.Term, binding: Dict[str, tl.Term]) -> bool:
    """Does `target` have the shape of `pattern`, a variable standing for any
    term? The variables of a definiendum each occur once, so a variable binds
    whatever is in its place without having to agree with another place."""
    if isinstance(pattern, tl.VariableTerm):
        binding[pattern.name] = target
        return True
    if isinstance(pattern, tl.FunctionTerm):
        return (isinstance(target, tl.FunctionTerm) and target.symbol == pattern.symbol
                and len(target.args) == len(pattern.args)
                and all(_match_term(p, t, binding) for p, t in zip(pattern.args, target.args)))
    return pl._ast_eq(pattern, target)


def _match_definiendum(pattern: fl.Formula, candidate: fl.Formula) -> Optional[Dict[str, tl.Term]]:
    """The terms in place of the definiendum's variables if `candidate` is a
    use of the symbol of the form `pattern`, and None if it is not. An equation
    is a use whichever way round it is written."""
    if isinstance(pattern, fl.AtomicFormula):
        if not (isinstance(candidate, fl.AtomicFormula) and candidate.predicate == pattern.predicate
                and len(candidate.args) == len(pattern.args)):
            return None
        binding: Dict[str, tl.Term] = {}
        if all(_match_term(p, t, binding) for p, t in zip(pattern.args, candidate.args)):
            return binding
        return None
    if isinstance(pattern, fl.Equals) and isinstance(candidate, fl.Equals):
        for left, right in ((candidate.left, candidate.right), (candidate.right, candidate.left)):
            binding = {}
            if _match_term(pattern.left, left, binding) and _match_term(pattern.right, right, binding):
                return binding
    return None


def _strip_universals(phi: fl.Formula) -> fl.Formula:
    """`phi` without its leading ``forall``s (and so with their variables free)."""
    while isinstance(phi, fl.ForAll):
        phi = phi.body
    return phi


# ---------------------------------------------------------------------------
# Reading a definiendum
# ---------------------------------------------------------------------------

def _term_heads(term: tl.Term) -> Iterator[Tuple[str, int]]:
    if isinstance(term, tl.FunctionTerm):
        yield term.symbol, len(term.args)
        for argument in term.args:
            yield from _term_heads(argument)


def _heads(node) -> Iterator[Tuple[str, int]]:
    """Every symbol a formula (or a term) applies, as ``(name, arity)``: the
    predicates of its atoms and the function symbols of its terms."""
    if isinstance(node, tl.Term):
        yield from _term_heads(node)
    elif isinstance(node, fl.AtomicFormula):
        yield node.predicate, len(node.args)
        for argument in node.args:
            yield from _term_heads(argument)
    elif isinstance(node, fl.And):
        for part in node.conjuncts:
            yield from _heads(part)
    elif isinstance(node, fl.Or):
        for part in node.disjuncts:
            yield from _heads(part)
    elif isinstance(node, fl.Not):
        yield from _heads(node.sub)
    elif isinstance(node, fl.Implies):
        yield from _heads(node.antecedent)
        yield from _heads(node.consequent)
    elif isinstance(node, (fl.Iff, fl.Equals)):
        yield from _heads(node.left)
        yield from _heads(node.right)
    elif isinstance(node, (fl.ForAll, fl.Exists)):
        yield from _heads(node.body)


def _terms_of(formula: fl.Formula) -> List[tl.Term]:
    """The terms an atom or an equation is made of."""
    if isinstance(formula, fl.AtomicFormula):
        return list(formula.args)
    if isinstance(formula, fl.Equals):
        return [formula.left, formula.right]
    return []


def _applications(formula: fl.Formula, symbol: str) -> List[Tuple[str, List[tl.Term]]]:
    """Each use of `symbol` in the atom or equation `formula`, as ``(kind,
    arguments)``: kind "predicate" for an atom of that predicate, "function"
    for an application of it inside a term."""
    uses: List[Tuple[str, List[tl.Term]]] = []
    if isinstance(formula, fl.AtomicFormula) and formula.predicate == symbol:
        uses.append(("predicate", list(formula.args)))

    def look(term: tl.Term) -> None:
        if isinstance(term, tl.FunctionTerm):
            if term.symbol == symbol:
                uses.append(("function", list(term.args)))
            for argument in term.args:
                look(argument)

    for term in _terms_of(formula):
        look(term)
    return uses


def _variable_occurrences(formula: fl.Formula) -> List[str]:
    """The variables of an atom or an equation, once for each place."""
    names: List[str] = []

    def look(term: tl.Term) -> None:
        if isinstance(term, tl.VariableTerm):
            names.append(term.name)
        elif isinstance(term, tl.FunctionTerm):
            for argument in term.args:
                look(argument)

    for term in _terms_of(formula):
        look(term)
    return names


def _has_constant(formula: fl.Formula) -> bool:
    def look(term: tl.Term) -> bool:
        if isinstance(term, tl.ConstantTerm):
            return True
        return isinstance(term, tl.FunctionTerm) and any(look(argument) for argument in term.args)

    return any(look(term) for term in _terms_of(formula))


# ---------------------------------------------------------------------------
# Evidence that the thing named exists
# ---------------------------------------------------------------------------

class Evidence:
    """How a definition shows that there is the thing it names.

    `problem(definition, environment)` is None when the evidence holds in the
    theory `environment`, and otherwise a sentence saying what is wrong with it.
    """

    def problem(self, definition: "Definition", environment: TheoryEnvironment) -> Optional[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class ByRule(Evidence):
    """The theory has an axiom that says there is such a thing: `rule` accepts
    the existence statement. Separation says there is an intersection, Power
    Set that there is a power set.

    `rule` must be a rule of the theory, since an axiom the theory does not
    have shows nothing in it.
    """

    rule: pl.InferenceRule

    def problem(self, definition: "Definition", environment: TheoryEnvironment) -> Optional[str]:
        if not pl._rule_among(self.rule, environment.rules):
            return f"{self.rule.name} is not a rule of the theory"
        statement = definition.existence_statement()
        try:
            accepted = self.rule.applies([], statement)
        except Exception as exc:  # a rule that cannot read the statement does not accept it
            return f"{self.rule.name} could not read {show(statement)}: {exc}"
        if accepted:
            return None
        return f"{self.rule.name} does not accept {show(statement)}"


def _lines(entries: Sequence) -> Iterator:
    """Every line of a proof, at any depth: those of the proof itself, of each
    standalone block, of the subproof attached to a line, and of each subproof
    of a `Proof by Cases`."""
    for raw in entries:
        parsed = pl._classify_entry(raw)
        if isinstance(parsed, str):
            continue
        if parsed.is_subproof_block:
            yield from _lines(parsed.subproof_entries)
            continue
        yield parsed
        if parsed.nested_subproof is not None:
            justification = parsed.justification
            cases = isinstance(justification, tuple) and justification[:1] == ("rule_hybrid",)
            for block in (parsed.nested_subproof if cases else [parsed.nested_subproof]):
                yield from _lines(block)


def _declarations_of(parsed) -> List[pl.Declaration]:
    """The declarations a line makes, if it makes any."""
    justification = parsed.justification
    if isinstance(justification, tuple) and len(justification) >= 2 and isinstance(justification[1], list):
        return list(justification[1])
    return []


# The type names the elaborator gives the names a proof introduces for something
# it has already shown to exist: `Let P be such a set. (Existence from L)` and
# `Define h = w. (Existence from L)`.
_NAMING_TYPES = {"existential witness", "definition"}


def _witness_formulas(entries: Sequence) -> List[fl.Formula]:
    """The formula of each line that only names something the proof showed to
    exist. The kernel records such a line as a premise of the proof (it says of
    the new name what the existential says), though the proof did not assume it."""
    formulas: List[fl.Formula] = []
    for parsed in _lines(entries):
        if not any(declaration.type_name in _NAMING_TYPES for declaration in _declarations_of(parsed)):
            continue
        phi = parsed.phi
        formulas.extend(phi if isinstance(phi, list) else [phi])
    return [formula for formula in formulas if isinstance(formula, fl.Formula)]


def _top_level_declarations(entries: Sequence) -> List[pl.Declaration]:
    declarations: List[pl.Declaration] = []
    for raw in entries:
        parsed = pl._classify_entry(raw)
        if not isinstance(parsed, str) and not parsed.is_subproof_block:
            declarations.extend(_declarations_of(parsed))
    return declarations


def _without_definitions(environment: TheoryEnvironment) -> TheoryEnvironment:
    """`environment` with no definition in it. The evidence for a definition is
    checked there: a definition is justified by the axioms alone, so evidence
    that used another definition (or this one) would be circular, or would
    depend on the order the theory lists them in."""
    return dataclasses.replace(
        environment,
        rules=[rule for rule in environment.rules if not isinstance(rule, DefinitionRule)],
        citable_titles=[],
    )


@dataclass(frozen=True)
class ByProof(Evidence):
    """A proof, written out, derives the existence statement from the theory's
    axioms and nothing else. The union of two sets exists by Pairing and Union
    and a page of reasoning, and that page is the evidence.

    The proof is checked in the theory without any definition, and it must:

      * be a valid proof, and derive the existence statement (up to the names
        of its bound variables) at its top level;
      * declare each parameter of the statement -- the variables of the
        definition that the statement is about -- as a plain object at its top
        level, and take nothing for granted about it;
      * take nothing else for granted either. A premise, a declared property
        (`Let A be a finite set`), an assumed structure or an axiom the proof
        merely lists would make the existence a consequence of a hypothesis. The
        lines that name what the proof has already shown to exist
        (`Let P be such a set. (Existence from L)`) are not hypotheses, and
        are fine wherever they stand, a subproof or a case included.

    The check is that the proof *promotes* to a theorem
    (`ProofLogic.promote_theorem`) that generalizes the parameters, and that
    what it premises is only such naming lines. Generalizing a parameter is
    what shows that the proof treated it as arbitrary: a proof that names a
    parameter as a witness (`Let B be such a set`), or defines it, proves the
    statement about one set it found, not about every set, and the kernel
    refuses to generalize a name the proof did not declare as an object.
    """

    text: str

    def problem(self, definition: "Definition", environment: TheoryEnvironment) -> Optional[str]:
        # Imported here: the parser imports the theories, and a theory imports this module.
        import SyLoPy.source.ProofParser as parser

        statement = definition.existence_statement()
        parameters = list(definition.parameters)
        try:
            entries, _raw = parser.parse_proof_text(self.text, _without_definitions(environment))
        except ValueError as exc:
            return f"the proof of existence does not parse: {exc}"
        proof = pl.Proof(entries)
        ok, error = proof.check_detailed()
        if not ok:
            return f"the proof of existence is not a valid proof: {error}"

        derived, _objects, _predicates = pl._top_level_promotion_inputs(proof.entries)
        derived_statement = next((formula for formula in derived if pl._alpha_eq(formula, statement)), None)
        if derived_statement is None:
            return f"the proof of existence does not derive {show(statement)} at its top level"

        try:
            theorem = pl.promote_theorem(definition.title, proof, generalized_names=parameters,
                                         conclusion=derived_statement)
        except ValueError as exc:
            return f"the proof of existence is not a proof about arbitrary objects: {exc}"

        if theorem.declaration_requirements or theorem.relation_requirements:
            return ("the proof of existence takes for granted a structure (a relation and its properties) "
                    "that it declares")
        naming = _witness_formulas(proof.entries)
        for premise in theorem.premises:
            if not any(pl._ast_eq(premise, formula) for formula in naming):
                return (f"the proof of existence takes {show(premise)} for granted; it may name what it has "
                        "shown to exist and assume nothing else")
        for declaration in _top_level_declarations(proof.entries):
            if declaration.name in parameters and declaration.metadata:
                return (f"the proof of existence declares {declaration.name} as more than an arbitrary "
                        "object")
        return None


@dataclass(frozen=True)
class Existence:
    """What a definition of a thing must show: the `statement` that there is
    such a thing (``exists Y, forall u, (In(u, Y) iff ...)``, with the
    definition's parameters free) and the `evidence` that it holds."""

    statement: fl.Formula
    evidence: Evidence


# ---------------------------------------------------------------------------
# The definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Definition:
    """The name of something, with the sentence that says what it is.

    `symbol` is the new name; `definiendum` is a use of it, an atom or an
    equation, in which every variable of the definition occurs exactly once
    (``In(u, Union(A, B))``, ``Cyclic(G)``); `definiens` says what the use
    means, in terms of those variables (``In(u, A) or In(u, B)``). The
    definition is the sentence ``definiendum iff definiens``. `existence` is
    required exactly when the symbol names a thing (a function symbol, as
    `Union` does) and is how the definition shows there is one; a predicate is
    defined by abbreviation and has none.

    What a proof may cite is that sentence for any terms in place of the
    variables, written in any of the forms in which a sentence about all of
    them is the same sentence:

      * with or without leading ``forall``s (what holds for all values of its
        variables holds for any terms, and the ``forall``s say no more);
      * with the two sides of the biconditional in either order;
      * with its own bound variables named as the proof likes, provided no
        term put in place of a variable is captured by one.

    The last is what keeps a citation a citation. In the definition of the
    power set, ``u`` is a subset of ``A`` is ``forall w, (In(w, u) -> In(w, A))``;
    for ``u := w`` the line ``In(w, PowerSet(A)) iff forall w, (In(w, w) ->
    In(w, A))`` has the quantifier capture the ``w`` it was to leave alone, and
    says something else (every set that is not a member of itself is in the
    power set of A), so it is refused.

    A definition that is not one is refused when it is built
    (`DefinitionError`): the symbol must occur once in the definiendum, with
    distinct variables as arguments, and not in the definiens; the definiendum
    has no other variable and no constant; the definiens has no variable the
    definiendum does not determine and no bound variable named like one that
    does; a symbol that names a thing has its existence claim, and the claim
    does not use the symbol; and the title is one a proof can cite.
    """

    title: str
    symbol: str
    variables: Tuple[str, ...]
    definiendum: fl.Formula
    definiens: fl.Formula
    existence: Optional[Existence] = None
    type_name: Optional[str] = None

    def __post_init__(self):
        fail = self._fail
        title = self.title
        if not title or title != title.strip():
            fail("a definition needs a title, written without spaces at either end")
        if "from" in title.lower() or "subproof" in title.lower():
            fail("its title is cited as the justification of a line, and a justification with "
                 "`from` or `subproof` in it reads as a citation of lines or of a subproof")
        if self._is_a_rule_name(title):
            fail("its title is already the name of a rule, and a citation of it would mean the rule")
        variables = tuple(self.variables)
        object.__setattr__(self, "variables", variables)
        if len(set(variables)) != len(variables) or not all(variables):
            fail("its variables must be distinct names")
        if not isinstance(self.definiendum, (fl.AtomicFormula, fl.Equals)):
            fail("the definiendum must be an atom or an equation that uses the symbol")

        uses = _applications(self.definiendum, self.symbol)
        if len(uses) != 1:
            fail(f"the definiendum must use {self.symbol} exactly once, not {len(uses)} times")
        kind, arguments = uses[0]
        if not all(isinstance(a, tl.VariableTerm) for a in arguments) or \
                len({a.name for a in arguments}) != len(arguments):
            fail(f"{self.symbol} must be applied to distinct variables in the definiendum")

        occurrences = _variable_occurrences(self.definiendum)
        if _has_constant(self.definiendum):
            fail("the definiendum has a constant in it; a symbol is defined for variables")
        if sorted(occurrences) != sorted(variables):
            fail("each of the definition's variables must occur exactly once in the definiendum, and "
                 f"no other variable may (it has {', '.join(occurrences) or 'none'}, "
                 f"the definition lists {', '.join(variables) or 'none'})")

        if any(symbol == self.symbol for symbol, _arity in _heads(self.definiens)):
            fail(f"the definiens uses {self.symbol}, which it is defining")
        hidden = fl.free_variables(self.definiens) - set(variables)
        if hidden:
            fail(f"the definiens has {', '.join(sorted(hidden))} free, which the definiendum does not "
                 "determine: a definition cannot say something about an unspecified object")
        clashing = fl.bound_variable_names(self.definiens) & set(variables)
        if clashing:
            fail(f"the definiens binds {', '.join(sorted(clashing))}, which is also a variable of the "
                 "definition; rename the bound variable")

        if kind == "function" and self.existence is None:
            fail(f"{self.symbol} names a thing, so the definition must show that there is one "
                 "(an `Existence`)")
        if self.existence is not None:
            statement = self.existence.statement
            if any(symbol == self.symbol for symbol, _arity in _heads(statement)):
                fail(f"the existence claim uses {self.symbol}, which has no meaning until it is shown")
            stray = fl.free_variables(statement) - set(variables)
            if stray:
                fail(f"the existence claim has {', '.join(sorted(stray))} free, which are not variables "
                     "of the definition")

    def _fail(self, reason: str):
        raise DefinitionError(f"{self.title or '(untitled definition)'}: {reason}")

    @staticmethod
    def _is_a_rule_name(title: str) -> bool:
        # Imported here: the justification parser is the authority on what a name means.
        import SyLoPy.source.ProofJustification as justification
        try:
            justification._rule(title)
        except ValueError:
            return False
        return True

    # -- what it introduces ------------------------------------------------

    @property
    def kind(self) -> str:
        """`pl.DeclarationKind.FUNCTION` if the symbol names a thing,
        `pl.DeclarationKind.PREDICATE` if it names a property or relation."""
        use_kind, _arguments = _applications(self.definiendum, self.symbol)[0]
        return pl.DeclarationKind.FUNCTION if use_kind == "function" else pl.DeclarationKind.PREDICATE

    @property
    def arity(self) -> int:
        return len(_applications(self.definiendum, self.symbol)[0][1])

    def declaration(self) -> pl.Declaration:
        """The declaration of the symbol this definition names."""
        return pl.Declaration(self.symbol, self.kind, arity=self.arity, type_name=self.type_name)

    # -- the sentence ------------------------------------------------------

    def sentence(self) -> str:
        """The defining sentence as a proof writes it."""
        return f"{show(self.definiendum)} iff {show(self.definiens)}"

    def instance_problem(self, phi: fl.Formula) -> Optional[str]:
        """None if `phi` is this definition's sentence for some terms, in one of
        the forms the class docstring lists; otherwise why it is not."""
        header = (f"{self.title} is cited for the sentence {self.sentence()}, for any terms in place of "
                  f"{', '.join(self.variables)}, with or without leading `forall`s and with the "
                  "biconditional in either order;")
        body = _strip_universals(phi)
        if not isinstance(body, fl.Iff):
            return f"{header} here the line is not a biconditional."
        mismatch = None
        for use, other in ((body.left, body.right), (body.right, body.left)):
            binding = _match_definiendum(self.definiendum, use)
            if binding is None:
                continue
            used = set(fl.formula_names(self.definiens)) | set(binding)
            for term in binding.values():
                used |= fl.term_names(term)
            expected = _instantiate(self.definiens, binding, used)
            if pl._alpha_eq(other, expected):
                return None
            if mismatch is None:
                instance = _instantiate(self.definiendum, binding, set(used))
                mismatch = f"here for {show(instance)} the other side must be {show(expected)}."
        if mismatch is not None:
            return f"{header} {mismatch}"
        return (f"{header} here neither side of the biconditional is a use of {self.symbol} of the "
                f"form {show(self.definiendum)}.")

    # -- what it must show ---------------------------------------------------

    @property
    def parameters(self) -> Tuple[str, ...]:
        """The variables the existence statement is about, in the definition's
        order: what the thing named depends on."""
        if self.existence is None:
            return ()
        free = fl.free_variables(self.existence.statement)
        return tuple(name for name in self.variables if name in free)

    def existence_statement(self) -> Optional[fl.Formula]:
        """The existence statement as a proof states it: for particular
        objects, the parameters written as constants of the same names."""
        if self.existence is None:
            return None
        binding = {name: tl.ConstantTerm(name, name) for name in self.parameters}
        return _instantiate(self.existence.statement, binding,
                            set(fl.formula_names(self.existence.statement)) | set(binding))


# ---------------------------------------------------------------------------
# The rule a theory registers
# ---------------------------------------------------------------------------

_UNSET = object()


class DefinitionRule(pl.InferenceRule):
    """A definition as a zero-premise rule, cited by the definition's title.

    It accepts the defining sentence for any terms (`Definition.instance_problem`)
    and nothing else -- and only if the evidence that the thing exists holds.
    The evidence is checked once, when the first line cites the rule, in the
    theory `environment` without any definition (`_without_definitions`); a
    definition whose evidence fails is refused, with the reason, wherever it is
    cited. `environment` is the theory's environment, or a function that
    returns it: the rules go into the environment, so a theory that lists them
    in its own environment cannot have it yet.
    """

    premise_arity = 0

    def __init__(self, definition: Definition,
                 environment: Union[TheoryEnvironment, Callable[[], TheoryEnvironment]]):
        self.definition = definition
        self.name = definition.title
        self.citation = definition.title
        self._environment = environment
        self._verdict = _UNSET
        self._checking = False

    def same_configuration(self, other) -> bool:
        # A rule is the definition it was built for: another definition (or an
        # equal one built again) is not what a proof or a theorem asked for.
        return type(other) is type(self) and other.definition is self.definition

    def theory(self) -> TheoryEnvironment:
        return self._environment() if callable(self._environment) else self._environment

    def evidence_problem(self) -> Optional[str]:
        """Why the evidence that the thing exists fails, or None if it holds
        (or the definition needs none). Settled once."""
        existence = self.definition.existence
        if existence is None:
            return None
        if self._verdict is not _UNSET:
            return self._verdict
        if self._checking:
            return "its evidence depends on the definition it is evidence for"
        self._checking = True
        try:
            problem = existence.evidence.problem(self.definition, self.theory())
        finally:
            self._checking = False
        self._verdict = problem
        return problem

    def applies(self, candidates: list, phi: fl.Formula) -> bool:
        return (not candidates and self.definition.instance_problem(phi) is None
                and self.evidence_problem() is None)

    def explain_in_context(self, candidates, phi, context):
        if candidates:
            return f"{self.name} takes no cited lines."
        problem = self.definition.instance_problem(phi)
        if problem is not None:
            return problem
        evidence = self.evidence_problem()
        if evidence is not None:
            return f"{self.name} is refused, since {evidence}."
        return None


def _normalized(title: str) -> str:
    import SyLoPy.source.ProofJustification as justification
    return justification._normalize(title)


def definition_rules(definitions: Iterable[Definition],
                     environment: Union[TheoryEnvironment, Callable[[], TheoryEnvironment]]) -> List[DefinitionRule]:
    """The rules for `definitions`, to put in the theory's environment. Two
    definitions may not share a symbol or a title (a title is matched without
    regard to case, hyphens and spacing, so those count as one)."""
    definitions = list(definitions)
    symbols: Dict[str, str] = {}
    titles: Dict[str, str] = {}
    for definition in definitions:
        if definition.symbol in symbols:
            raise DefinitionError(f"{definition.title}: {definition.symbol} is already defined by "
                                  f"{symbols[definition.symbol]}")
        symbols[definition.symbol] = definition.title
        key = _normalized(definition.title)
        if key in titles:
            raise DefinitionError(f"{definition.title}: a citation of it cannot be told from "
                                  f"{titles[key]}")
        titles[key] = definition.title
    return [DefinitionRule(definition, environment) for definition in definitions]


def definition_declarations(definitions: Iterable[Definition]) -> List[pl.Declaration]:
    """The declarations of the symbols `definitions` name, for the theory's
    environment: a symbol is declared once, by the definition that names it."""
    return [definition.declaration() for definition in definitions]


def definition_titles(definitions: Iterable[Definition]) -> List[str]:
    """The titles a proof may cite the definitions by
    (`TheoryEnvironment.citable_titles`)."""
    return [definition.title for definition in definitions]
