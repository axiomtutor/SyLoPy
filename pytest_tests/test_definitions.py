"""Tests for the definition facility, `source/Definitions.py`.

A definition names a new symbol by a sentence that says what it is. For a thing
(a set, a function value) it first shows that there is one, and it adds no axiom.
The facility belongs to no theory, so these tests use a toy theory with an algebra
word and an arithmetic one -- the predicate `Cyclic` and the function `Double` --
and run proofs about them through the whole pipeline: the proof text is parsed in
the toy theory's environment, elaborated, and checked by the validator, which
resolves a citation of a definition's title to its rule.

`test_set_operation_definitions.py` is the same facility on set theory.
"""
from __future__ import annotations

import dataclasses

import pytest

from SyLoPy.source import Definitions as df
from SyLoPy.source import DiscreteMath as dm
from SyLoPy.source.ProofElaboration import ElaborationError, TheoryEnvironment

from .support import atom, c, fl, fn, pl, pp, st, tl, v


def generates(first, second):
    return atom("Generates", first, second)


def plus(first, second):
    return fn("Plus", first, second)


# ---------------------------------------------------------------------------
# The toy definitions
# ---------------------------------------------------------------------------

def cyclic_definition(**changes) -> df.Definition:
    """`Cyclic(G) iff exists g, Generates(g, G)`: a predicate defined by abbreviation."""
    fields = dict(
        title="Definition of cyclic", symbol="Cyclic", variables=("G",),
        definiendum=atom("Cyclic", v("G")),
        definiens=fl.Exists("g", generates(v("g"), v("G"))),
    )
    return df.Definition(**{**fields, **changes})


def double_claim(label: str, next_label: str, indent: str = "", thing: str = "Y", value: str = "m") -> str:
    """Lines of a proof that derive what `Double(n)` has to show, for a declared `n`:
    ``exists Y, forall m, (Y = m iff m = Plus(n, n))`` -- exactly one thing is
    `Plus(n, n)`. The universal line is numbered `label` and the existential
    `next_label`; `indent` is the depth of the line they stand at."""
    equal = f"Plus(n, n) = {value}"
    turned = f"{value} = Plus(n, n)"
    return f"""\
{indent}{label}. forall {value}, ({equal} iff {turned}). (Universal Generalization from subproof below)
{indent}begin subproof
{indent} {label}.0. let c be arbitrary. (Arbitrary)
{indent} {label}.1. Plus(n, n) = c -> c = Plus(n, n). (Conditional Introduction from subproof below)
{indent}  {label}.1.1. Plus(n, n) = c. (Assumption for Conditional Introduction)
{indent}  {label}.1.2. c = Plus(n, n). (Symmetry from {label}.1.1)
{indent} {label}.2. c = Plus(n, n) -> Plus(n, n) = c. (Conditional Introduction from subproof below)
{indent}  {label}.2.1. c = Plus(n, n). (Assumption for Conditional Introduction)
{indent}  {label}.2.2. Plus(n, n) = c. (Symmetry from {label}.2.1)
{indent} {label}.3. Plus(n, n) = c iff c = Plus(n, n). (Biconditional Introduction from {label}.1, {label}.2)
{indent}end subproof
{indent}{next_label}. Exists {thing}, forall {value}, ({thing} = {value} iff {turned}). (Existential Introduction from {label})
"""


DOUBLE_EXISTS = "1. Let n be any object. (Declaration)\n" + double_claim("2", "3")


def double_definition(**changes) -> df.Definition:
    """`Double(n) = m iff m = Plus(n, n)`: a function symbol, a thing, so the
    definition shows that for every n there is exactly one such m. `changes`
    replace fields: `evidence=...` is the proof or axiom that shows it."""
    fields = dict(
        title="Definition of double", symbol="Double", variables=("n", "m"),
        definiendum=fl.Equals(fn("Double", v("n")), v("m")),
        definiens=fl.Equals(v("m"), plus(v("n"), v("n"))),
        evidence=df.ByProof(DOUBLE_EXISTS),
    )
    return df.Definition(**{**fields, **changes})


CYCLIC = cyclic_definition()
DOUBLE = double_definition()


def toy_theory(*definitions: df.Definition, rules=(), declarations=(), recipes=()) -> TheoryEnvironment:
    """A theory that has `definitions`, and `Generates` and `Plus` to define them with."""
    holder = {}
    environment = TheoryEnvironment(
        name="toy",
        rules=[*rules, *df.definition_rules(definitions, lambda: holder["environment"])],
        declarations=[
            *df.definition_declarations(definitions),
            pl.Declaration("Generates", pl.DeclarationKind.PREDICATE, arity=2),
            pl.Declaration("Plus", pl.DeclarationKind.FUNCTION, arity=2),
            pl.Declaration("Marked", pl.DeclarationKind.PREDICATE, arity=1),
            *declarations,
        ],
        declaration_recipes=list(recipes),
        citable_titles=df.definition_titles(definitions),
    )
    holder["environment"] = environment
    return environment


TOY = toy_theory(CYCLIC, DOUBLE)


def check(text: str, environment: TheoryEnvironment = TOY):
    """`(ok, error)` for the proof `text` checked in `environment`."""
    entries, _lines = pp.parse_proof_text(text, environment)
    return pl.Proof(entries).check_detailed()


def refusal(text: str, environment: TheoryEnvironment = TOY) -> str:
    """The reason the proof is refused; the proof must be refused."""
    ok, error = check(text, environment)
    assert not ok, "the proof was accepted"
    return error.detail


def rule_of(definition: df.Definition, environment: TheoryEnvironment = TOY) -> df.DefinitionRule:
    return next(r for r in environment.rules
                if isinstance(r, df.DefinitionRule) and r.definition is definition)


# ---------------------------------------------------------------------------
# A definition that is not one is refused when it is built
# ---------------------------------------------------------------------------

BAD_DEFINITIONS = [
    ("an empty title", lambda: cyclic_definition(title=""), "needs a title"),
    ("a title with spaces around it", lambda: cyclic_definition(title=" Definition of cyclic"),
     "without spaces at either end"),
    ("a title with `from`", lambda: cyclic_definition(title="Cyclic from generators"),
     "`from` or `subproof`"),
    ("a title with `subproof`", lambda: cyclic_definition(title="Cyclic subproof"),
     "`from` or `subproof`"),
    ("the name of a rule", lambda: cyclic_definition(title="Modus Ponens"), "already the name of a rule"),
    ("a rule's alias", lambda: cyclic_definition(title="reflexivity"), "already the name of a rule"),
    ("variables that repeat", lambda: cyclic_definition(variables=("G", "G")), "must be distinct names"),
    ("a variable with no name", lambda: cyclic_definition(variables=("",)), "must be distinct names"),
    ("a definiendum that is a conjunction",
     lambda: cyclic_definition(definiendum=fl.And(atom("Cyclic", v("G")), atom("Cyclic", v("G")))),
     "must be an atom or an equation"),
    ("a definiendum that does not use the symbol",
     lambda: cyclic_definition(definiendum=atom("Abelian", v("G"))), "exactly once, not 0 times"),
    ("a definiendum that uses the symbol twice",
     lambda: double_definition(definiendum=fl.Equals(fn("Double", fn("Double", v("n"))), v("m"))),
     "exactly once, not 2 times"),
    ("a symbol applied to a term that is not a variable",
     lambda: cyclic_definition(definiendum=atom("Cyclic", fn("f", v("G")))), "applied to distinct variables"),
    ("a symbol applied to a variable twice",
     lambda: cyclic_definition(definiendum=atom("Cyclic", v("G"), v("G"))), "applied to distinct variables"),
    ("a definiendum with a constant",
     lambda: cyclic_definition(symbol="Related", variables=("G",),
                               definiendum=atom("Has", c("e"), fn("Related", v("G")))), "has a constant in it"),
    ("a definiendum with a constant inside a term",
     lambda: cyclic_definition(symbol="Related", variables=("G",),
                               definiendum=atom("Has", fn("Related", v("G")), fn("f", c("e")))),
     "has a constant in it"),
    ("a variable the definiendum does not have",
     lambda: cyclic_definition(variables=("G", "H")), "must occur exactly once in the definiendum"),
    ("a variable of the definiendum that is not listed",
     lambda: cyclic_definition(variables=()), "must occur exactly once in the definiendum"),
    ("a variable at two places of the definiendum",
     lambda: double_definition(definiendum=fl.Equals(fn("Double", v("n")), v("n")), variables=("n", "m")),
     "must occur exactly once in the definiendum"),
    ("a definiens that uses the symbol",
     lambda: cyclic_definition(definiens=atom("Cyclic", v("G"))), "uses Cyclic, which it is defining"),
    ("a definiens that uses the symbol in a term",
     lambda: double_definition(definiens=fl.Equals(v("m"), fn("Double", v("n")))),
     "uses Double, which it is defining"),
    ("a definiens that uses the symbol deep inside a term",
     lambda: double_definition(definiens=fl.Equals(v("m"), plus(fn("Double", v("n")), v("n")))),
     "uses Double, which it is defining"),
    ("a definiens with a variable of its own",
     lambda: cyclic_definition(definiens=generates(v("g"), v("G"))), "has g free"),
    ("a definiens that binds a variable of the definition",
     lambda: cyclic_definition(symbol="Gen", variables=("G", "g"), definiendum=atom("Gen", v("G"), v("g")),
                               definiens=fl.Exists("g", generates(v("g"), v("G")))),
     "binds g, which is also a variable of the definition"),
    ("a thing with no evidence",
     lambda: double_definition(evidence=None), "names a thing, so the definition must show"),
    ("a predicate with evidence",
     lambda: cyclic_definition(evidence=df.ByProof("")), "defined by abbreviation, so there is nothing to show"),
]


@pytest.mark.parametrize("build, reason", [case[1:] for case in BAD_DEFINITIONS],
                         ids=[case[0] for case in BAD_DEFINITIONS])
def test_a_definition_that_is_not_one_is_refused_when_it_is_built(build, reason):
    with pytest.raises(df.DefinitionError, match=reason):
        build()


def test_a_refusal_names_the_definition_it_is_about():
    with pytest.raises(df.DefinitionError) as raised:
        cyclic_definition(definiens=generates(v("g"), v("G")))
    assert str(raised.value).startswith("Definition of cyclic: ")


def test_a_predicate_needs_no_evidence_and_has_nothing_to_show():
    # Defined by abbreviation: nothing is named, so nothing has to exist.
    assert CYCLIC.evidence is None
    assert CYCLIC.existence_claim() is None and CYCLIC.parameters == ()


# ---------------------------------------------------------------------------
# What a definition says about itself
# ---------------------------------------------------------------------------

def test_a_definition_introduces_the_symbol_it_names():
    assert CYCLIC.declaration() == pl.Declaration("Cyclic", pl.DeclarationKind.PREDICATE, arity=1)
    assert DOUBLE.declaration() == pl.Declaration("Double", pl.DeclarationKind.FUNCTION, arity=1)
    typed = double_definition(type_name="arithmetic operation")
    assert typed.declaration() == pl.Declaration(
        "Double", pl.DeclarationKind.FUNCTION, arity=1, type_name="arithmetic operation")
    assert (CYCLIC.kind, CYCLIC.arity) == (pl.DeclarationKind.PREDICATE, 1)
    assert (DOUBLE.kind, DOUBLE.arity) == (pl.DeclarationKind.FUNCTION, 1)


def test_the_arity_is_the_number_of_arguments_of_the_symbol_not_of_the_atom():
    # `Gen(G, h)` has two variables and `Gen` applies to both; `In(u, Union(A, B))`
    # has three variables, and `Union` applies to two.
    two = cyclic_definition(symbol="Gen", variables=("G", "h"), definiendum=atom("Gen", v("G"), v("h")),
                            definiens=generates(v("h"), v("G")))
    assert two.arity == 2
    assert st.UNION_DEFINITION.arity == 2 and st.POWER_SET_DEFINITION.arity == 1


def test_the_sentence_is_written_the_way_a_proof_writes_it():
    assert CYCLIC.sentence() == "Cyclic(G) iff exists g, Generates(g, G)"
    assert DOUBLE.sentence() == "Double(n) = m iff m = Plus(n, n)"
    assert st.UNION_DEFINITION.sentence() == "In(u, Union(A, B)) iff (In(u, A) or In(u, B))"


@pytest.mark.parametrize("node, text", [
    (v("x"), "x"),
    (c("a"), "a"),
    (fn("f", v("x"), fn("g", c("a"))), "f(x, g(a))"),
    (atom("P", v("x"), c("a")), "P(x, a)"),
    (fl.And(atom("P"), atom("Q"), atom("R")), "(P() and Q() and R())"),
    (fl.Or(atom("P"), atom("Q")), "(P() or Q())"),
    (fl.Not(atom("P", v("x"))), "not P(x)"),
    (fl.Implies(atom("P"), atom("Q")), "(P() -> Q())"),
    (fl.Iff(atom("P"), atom("Q")), "(P() iff Q())"),
    (fl.Equals(v("x"), c("a")), "x = a"),
    (fl.ForAll("x", atom("P", v("x"))), "forall x, P(x)"),
    (fl.Exists("x", atom("P", v("x"))), "exists x, P(x)"),
])
def test_show_writes_terms_and_formulas_in_proof_syntax(node, text):
    assert df.show(node) == text


def test_the_parameters_are_the_variables_the_existence_statement_is_about():
    assert DOUBLE.parameters == ("n",)          # `m` is bound by the statement
    assert CYCLIC.parameters == ()               # no statement
    assert st.UNION_DEFINITION.parameters == ("A", "B")
    assert st.POWER_SET_DEFINITION.parameters == ("A",)


def test_the_parameters_keep_the_order_of_the_definitions_variables():
    both = double_definition(
        variables=("m", "n", "k"),
        definiendum=fl.Equals(fn("Add", v("n"), v("k")), v("m")), symbol="Add",
        definiens=fl.Equals(v("m"), plus(v("n"), v("k"))),
        title="Definition of add")
    assert both.parameters == ("n", "k")
    swapped = dataclasses.replace(both, variables=("k", "n", "m"))
    assert swapped.parameters == ("k", "n")


def test_the_existence_statement_is_about_particular_objects():
    statement = DOUBLE.existence_statement()
    assert df.show(statement) == "exists Y, forall m, (Y = m iff m = Plus(n, n))"
    iff = statement.body.body
    # The parameter is a constant, as a proof states it; the bound variables are not.
    assert isinstance(iff.right.right.args[0], tl.ConstantTerm)
    assert isinstance(iff.left.left, tl.VariableTerm) and isinstance(iff.left.right, tl.VariableTerm)
    assert CYCLIC.existence_statement() is None


def test_the_existence_statement_keeps_a_binder_that_a_parameter_does_not_clash_with():
    # `Y` is bound in the statement and a parameter is called `A`: nothing to rename.
    statement = st.UNION_DEFINITION.existence_statement()
    assert df.show(statement) == "exists Y, forall u, (In(u, Y) iff (In(u, A) or In(u, B)))"


# ---------------------------------------------------------------------------
# What a definition of a thing has to show: read off its sentence
# ---------------------------------------------------------------------------

def claim(definition):
    return df.show(definition.existence_claim())


def hull_definition(**changes) -> df.Definition:
    """`Generates(g, Hull(G)) iff Generates(g, G)`: a thing named by an atom, as a set is."""
    fields = dict(
        title="Definition of hull", symbol="Hull", variables=("g", "G"),
        definiendum=generates(v("g"), fn("Hull", v("G"))),
        definiens=generates(v("g"), v("G")),
        evidence=df.ByProof(""),
    )
    return df.Definition(**{**fields, **changes})


def test_the_claim_for_an_equation_is_that_exactly_one_thing_is_the_value():
    # An equation fixes its value, so what the definition adds is that there is just one.
    assert claim(DOUBLE) == "exists Y, forall m, (Y = m iff m = Plus(n, n))"
    turned = double_definition(definiendum=fl.Equals(v("m"), fn("Double", v("n"))))
    assert claim(turned) == "exists Y, forall m, (m = Y iff m = Plus(n, n))"


def test_the_claim_for_an_atom_is_that_some_thing_has_exactly_the_property():
    assert claim(hull_definition()) == "exists Y, forall g, (Generates(g, Y) iff Generates(g, G))"
    assert claim(st.INTERSECTION_DEFINITION) == \
        "exists Y, forall u, (In(u, Y) iff (In(u, A) and In(u, B)))"


def test_the_claim_is_about_the_variables_the_symbol_is_applied_to_and_binds_the_others():
    hull = hull_definition()
    assert hull.parameters == ("G",)
    assert fl.free_variables(hull.existence_claim()) == {"G"}


def test_the_variables_the_symbol_is_not_applied_to_are_bound_in_the_definitions_order():
    def between(variables):
        return df.Definition(
            title="Definition of middle", symbol="Middle", variables=variables,
            definiendum=atom("Between", v("a"), fn("Middle", v("x")), v("b")),
            definiens=fl.And(atom("Marked", v("a")), atom("Marked", v("b")), atom("Marked", v("x"))),
            evidence=df.ByProof(""))

    body = "Between(a, Y, b) iff (Marked(a) and Marked(b) and Marked(x))"
    assert claim(between(("a", "x", "b"))) == f"exists Y, forall a, forall b, ({body})"
    assert claim(between(("b", "x", "a"))) == f"exists Y, forall b, forall a, ({body})"
    assert claim(between(("x", "a", "b"))) == f"exists Y, forall a, forall b, ({body})"


def test_the_symbol_may_be_inside_another_term_of_the_definiendum():
    inside = df.Definition(
        title="Definition of inner", symbol="Inner", variables=("u", "x", "w"),
        definiendum=atom("In", v("u"), fn("Wrap", fn("Inner", v("x")), v("w"))),
        definiens=atom("Marked", v("u")), evidence=df.ByProof(""))
    assert claim(inside) == "exists Y, forall u, forall w, (In(u, Wrap(Y, w)) iff Marked(u))"
    assert inside.parameters == ()          # the definiens does not say anything about x


@pytest.mark.parametrize("definition, expected", [
    (lambda: double_definition(variables=("Y", "m"), definiendum=fl.Equals(fn("Double", v("Y")), v("m")),
                               definiens=fl.Equals(v("m"), plus(v("Y"), v("Y")))),
     "exists Y_1, forall m, (Y_1 = m iff m = Plus(Y, Y))"),
    (lambda: double_definition(variables=("n", "Y"), definiendum=fl.Equals(fn("Double", v("n")), v("Y")),
                               definiens=fl.Equals(v("Y"), plus(v("n"), v("n")))),
     "exists Y_1, forall Y, (Y_1 = Y iff Y = Plus(n, n))"),
    (lambda: hull_definition(definiens=fl.Exists("Y", generates(v("Y"), v("G")))),
     "exists Y_1, forall g, (Generates(g, Y_1) iff exists Y, Generates(Y, G))"),
    (lambda: hull_definition(variables=("g", "G", "Y_1"),
                             definiendum=atom("Has", v("g"), fn("Hull", v("G")), v("Y_1")),
                             definiens=fl.Exists("Y", generates(v("Y"), v("g")))),
     "exists Y_2, forall g, forall Y_1, (Has(g, Y_2, Y_1) iff exists Y, Generates(Y, g))"),
], ids=["a parameter named Y", "the value named Y", "a bound variable named Y", "Y and Y_1 both used"])
def test_the_thing_is_named_by_a_variable_the_definition_does_not_use(definition, expected):
    assert claim(definition()) == expected


# ---------------------------------------------------------------------------
# What a proof may cite: the defining sentence for any terms
# ---------------------------------------------------------------------------

H, K = c("H"), c("K")


def cyclic_sentence(term, binder="g", reverse=False):
    """`Cyclic(term) iff exists binder, Generates(binder, term)`."""
    sides = [atom("Cyclic", term), fl.Exists(binder, generates(v(binder), term))]
    return fl.Iff(*(reversed(sides) if reverse else sides))


ACCEPTED = {
    "for a constant": cyclic_sentence(H),
    "for a variable": cyclic_sentence(v("h")),
    "for a term built from others": cyclic_sentence(fn("Product", H, fn("Inverse", K))),
    "with the biconditional the other way round": cyclic_sentence(H, reverse=True),
    "with the bound variable named otherwise": cyclic_sentence(H, binder="k"),
    "for a constant spelled like its bound variable": cyclic_sentence(c("g")),
    "for a variable spelled like its bound variable, renamed": cyclic_sentence(v("g"), binder="k"),
    "with the leading forall over its variable": fl.ForAll("h", cyclic_sentence(v("h"))),
    "closed over the variable the definition has": fl.ForAll("G", cyclic_sentence(v("G"))),
    "closed over several variables": fl.ForAll("h", fl.ForAll("k", cyclic_sentence(v("h")))),
    "with a forall over a variable it does not have": fl.ForAll("x", cyclic_sentence(H)),
    "closed, the other way round": fl.ForAll("h", cyclic_sentence(v("h"), reverse=True)),
}

REFUSED = {
    "not a biconditional": atom("Cyclic", H),
    "only one direction": fl.Implies(atom("Cyclic", H), fl.Exists("g", generates(v("g"), H))),
    "the arguments of Generates the other way round":
        fl.Iff(atom("Cyclic", H), fl.Exists("g", generates(H, v("g")))),
    "another quantifier": fl.Iff(atom("Cyclic", H), fl.ForAll("g", generates(v("g"), H))),
    "a conjunct more":
        fl.Iff(atom("Cyclic", H), fl.And(fl.Exists("g", generates(v("g"), H)), atom("Abelian", H))),
    "another predicate in the definiens": fl.Iff(atom("Cyclic", H), fl.Exists("g", atom("Related", v("g"), H))),
    "another term in the definiens": fl.Iff(atom("Cyclic", H), fl.Exists("g", generates(v("g"), K))),
    "another term in the definiendum": fl.Iff(atom("Cyclic", K), fl.Exists("g", generates(v("g"), H))),
    "the symbol applied to more terms than the definition has":
        fl.Iff(atom("Cyclic", H, K), fl.Exists("g", generates(v("g"), H))),
    "the symbol applied to none": fl.Iff(atom("Cyclic"), fl.Exists("g", generates(v("g"), H))),
    "the symbol on both sides": fl.Iff(atom("Cyclic", H), atom("Cyclic", K)),
    "the symbol applied to a function of the term":
        fl.Iff(atom("Cyclic", fn("f", H)), fl.Exists("g", generates(v("g"), H))),
    "another symbol": fl.Iff(atom("Abelian", H), fl.Exists("g", generates(v("g"), H))),
    "a trivial biconditional": fl.Iff(atom("Cyclic", H), atom("Cyclic", H)),
    "a conjunction instead": fl.And(atom("Cyclic", H), fl.Exists("g", generates(v("g"), H))),
    "an existential over the sentence": fl.Exists("h", cyclic_sentence(v("h"))),
}


@pytest.mark.parametrize("phi", list(ACCEPTED.values()), ids=list(ACCEPTED))
def test_a_definition_is_cited_for_its_sentence_for_any_terms(phi):
    assert CYCLIC.instance_problem(phi) is None
    assert rule_of(CYCLIC).applies([], phi)


@pytest.mark.parametrize("phi", list(REFUSED.values()), ids=list(REFUSED))
def test_a_definition_is_cited_for_its_sentence_and_nothing_else(phi):
    assert CYCLIC.instance_problem(phi) is not None
    assert not rule_of(CYCLIC).applies([], phi)


def test_a_term_with_a_variable_called_like_the_bound_variable_is_not_captured():
    """`Cyclic(g) iff exists g, Generates(g, g)` is not the sentence for g: the
    quantifier would capture the g it was to leave alone, and the line would say
    that g is a generator of itself. The sentence is stated with the quantifier's
    variable renamed, and the refusal says so."""
    captured = cyclic_sentence(v("g"))
    message = CYCLIC.instance_problem(captured)
    assert message is not None
    assert message.endswith("here for Cyclic(g) the other side must be exists g_1, Generates(g_1, g).")
    # Taking a fresh name is not a pattern: whatever name is not in use will do.
    assert CYCLIC.instance_problem(cyclic_sentence(v("g"), binder="g_1")) is None
    assert CYCLIC.instance_problem(cyclic_sentence(v("g"), binder="anything")) is None


def test_the_refusal_names_a_binder_not_used_anywhere_else():
    # `g` and `g_1` are both in the term, so the sentence's binder is `g_2`.
    term = fn("Product", v("g"), v("g_1"))
    message = CYCLIC.instance_problem(cyclic_sentence(term))
    assert message.endswith("here for Cyclic(Product(g, g_1)) the other side must be "
                            "exists g_2, Generates(g_2, Product(g, g_1)).")


def test_the_refusal_says_what_the_sentence_is_and_how_the_line_differs():
    header = ("Definition of cyclic is cited for the sentence Cyclic(G) iff exists g, Generates(g, G), "
              "for any terms in place of G, with or without leading `forall`s and with the biconditional "
              "in either order; ")
    not_iff = CYCLIC.instance_problem(atom("Cyclic", H))
    assert not_iff == header + "here the line is not a biconditional."
    wrong = CYCLIC.instance_problem(REFUSED["another quantifier"])
    assert wrong == header + "here for Cyclic(H) the other side must be exists g, Generates(g, H)."
    neither = CYCLIC.instance_problem(REFUSED["another symbol"])
    assert neither == header + ("here neither side of the biconditional is a use of Cyclic of the form "
                                "Cyclic(G).")


def test_the_refusal_is_about_the_first_use_of_the_symbol_when_both_sides_are_one():
    message = CYCLIC.instance_problem(REFUSED["the symbol on both sides"])
    assert message.endswith("here for Cyclic(H) the other side must be exists g, Generates(g, H).")


def test_a_leading_forall_does_not_change_what_is_said_about_the_rest():
    inner = REFUSED["another quantifier"]
    assert CYCLIC.instance_problem(fl.ForAll("x", inner)) == CYCLIC.instance_problem(inner)


def test_the_sentence_is_compared_up_to_the_names_of_bound_variables_only():
    # The same sentence with another name for its bound variable is accepted;
    # the name of a *free* variable is not a bound one.
    assert CYCLIC.instance_problem(cyclic_sentence(v("h"), binder="h")) is not None


# Equations: `Double(n) = m` may be written either way round, as an equation is.

DOUBLE_ACCEPTED = {
    "as defined": fl.Iff(fl.Equals(fn("Double", c("x")), c("y")), fl.Equals(c("y"), plus(c("x"), c("x")))),
    "the equation of the definiendum the other way round":
        fl.Iff(fl.Equals(c("y"), fn("Double", c("x"))), fl.Equals(c("y"), plus(c("x"), c("x")))),
    "the biconditional the other way round":
        fl.Iff(fl.Equals(c("y"), plus(c("x"), c("x"))), fl.Equals(fn("Double", c("x")), c("y"))),
    "both the other way round":
        fl.Iff(fl.Equals(c("y"), plus(c("x"), c("x"))), fl.Equals(c("y"), fn("Double", c("x")))),
    "for a term as the argument": fl.Iff(
        fl.Equals(fn("Double", plus(c("a"), c("b"))), c("z")),
        fl.Equals(c("z"), plus(plus(c("a"), c("b")), plus(c("a"), c("b"))))),
    "for a term as the value": fl.Iff(
        fl.Equals(fn("Double", c("x")), fn("Double", c("y"))),
        fl.Equals(fn("Double", c("y")), plus(c("x"), c("x")))),
    "closed": fl.ForAll("a", fl.ForAll("b", fl.Iff(
        fl.Equals(fn("Double", v("a")), v("b")), fl.Equals(v("b"), plus(v("a"), v("a")))))),
}

DOUBLE_REFUSED = {
    "the value among the summands":
        fl.Iff(fl.Equals(fn("Double", c("x")), c("y")), fl.Equals(c("y"), plus(c("x"), c("y")))),
    "the other sum": fl.Iff(fl.Equals(fn("Double", c("x")), c("y")), fl.Equals(c("y"), plus(c("y"), c("y")))),
    "the sum on the other side of its equation":
        fl.Iff(fl.Equals(fn("Double", c("x")), c("y")), fl.Equals(plus(c("x"), c("x")), c("y"))),
    "no biconditional": fl.Equals(fn("Double", c("x")), plus(c("x"), c("x"))),
    "the double of another term":
        fl.Iff(fl.Equals(fn("Double", c("x")), c("y")), fl.Equals(c("y"), plus(c("x"), c("z")))),
    "no use of Double": fl.Iff(fl.Equals(c("x"), c("y")), fl.Equals(c("y"), plus(c("x"), c("x")))),
}


@pytest.mark.parametrize("phi", list(DOUBLE_ACCEPTED.values()), ids=list(DOUBLE_ACCEPTED))
def test_an_equation_defined_symbol_is_cited_either_way_round(phi):
    assert DOUBLE.instance_problem(phi) is None


@pytest.mark.parametrize("phi", list(DOUBLE_REFUSED.values()), ids=list(DOUBLE_REFUSED))
def test_an_equation_defined_symbol_is_cited_for_its_sentence_and_nothing_else(phi):
    assert DOUBLE.instance_problem(phi) is not None


def test_the_orientation_of_the_definiens_equation_is_part_of_the_sentence():
    # Only the use of the symbol may be turned round; `m = Plus(n, n)` is what is said,
    # and a proof derives `Plus(n, n) = m` from it with Symmetry.
    message = DOUBLE.instance_problem(DOUBLE_REFUSED["the sum on the other side of its equation"])
    assert message.endswith("here for Double(x) = y the other side must be y = Plus(x, x).")


# The symbol a definition defines may not be used by what defines it, wherever
# in it the use is: under each connective and quantifier, next to other symbols.

def _hide(wrapper, inner):
    other = atom("Abelian", v("G"))
    return {
        "a conjunction": fl.And(other, inner),
        "a disjunction": fl.Or(inner, other),
        "a negation": fl.Not(inner),
        "the antecedent of a conditional": fl.Implies(inner, other),
        "the consequent of a conditional": fl.Implies(other, inner),
        "the left of a biconditional": fl.Iff(inner, other),
        "the right of a biconditional": fl.Iff(other, inner),
        "a universal": fl.ForAll("z", inner),
        "an existential": fl.Exists("z", inner),
    }[wrapper]


WRAPPERS = ["a conjunction", "a disjunction", "a negation", "the antecedent of a conditional",
            "the consequent of a conditional", "the left of a biconditional", "the right of a biconditional",
            "a universal", "an existential"]


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_a_definiens_may_not_use_the_symbol_it_defines_under_a_connective_or_a_quantifier(wrapper):
    with pytest.raises(df.DefinitionError, match="uses Cyclic, which it is defining"):
        cyclic_definition(definiens=_hide(wrapper, atom("Cyclic", v("G"))))


def test_a_variable_that_does_not_match_is_told_which_the_definiendum_has_and_which_the_definition_lists():
    with pytest.raises(df.DefinitionError) as raised:
        cyclic_definition(variables=("G", "H"))
    assert str(raised.value).endswith("(it has G, the definition lists G, H)")
    with pytest.raises(df.DefinitionError) as raised:
        cyclic_definition(variables=())
    assert str(raised.value).endswith("(it has G, the definition lists none)")
    with pytest.raises(df.DefinitionError) as raised:
        cyclic_definition(symbol="Flag", variables=("x",), definiendum=atom("Flag"), definiens=atom("Q"))
    assert str(raised.value).endswith("(it has none, the definition lists x)")


def test_a_definition_is_a_value_that_cannot_be_changed():
    for value, field in (
        (CYCLIC, "title"),
        (DOUBLE.evidence, "text"),
        (df.ByRule(pl.ReflexivityRule()), "rule"),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, field, None)


def test_the_variables_of_a_definition_are_kept_as_a_tuple_so_that_it_can_be_hashed():
    listed = cyclic_definition(variables=["G"])
    assert listed.variables == ("G",) and isinstance(listed.variables, tuple)
    assert isinstance(hash(listed), int)


# A definition may have a constant in what it says, though not in what it defines.

ORIGIN = df.Definition(
    title="Definition of origin", symbol="Origin", variables=("x",),
    definiendum=atom("Origin", v("x")),
    definiens=fl.Equals(plus(v("x"), c("zero")), v("x")),
)


def origin_sentence(term, other=None):
    return fl.Iff(atom("Origin", term), fl.Equals(plus(term, c("zero")), other or term))


def test_a_definition_may_say_something_about_a_constant():
    a, b = c("a"), c("b")
    for term in (a, v("x"), plus(a, b), fn("f", fn("g", a))):
        assert ORIGIN.instance_problem(origin_sentence(term)) is None, term
    assert ORIGIN.instance_problem(origin_sentence(a, other=b)) == (
        "Definition of origin is cited for the sentence Origin(x) iff Plus(x, zero) = x, for any terms in "
        "place of x, with or without leading `forall`s and with the biconditional in either order; "
        "here for Origin(a) the other side must be Plus(a, zero) = a.")
    other_constant = fl.Iff(atom("Origin", a), fl.Equals(plus(a, c("one")), a))
    assert ORIGIN.instance_problem(other_constant) is not None


def test_a_constant_of_the_definition_is_the_constant_not_a_variable_of_that_name():
    assert ORIGIN.instance_problem(fl.Iff(atom("Origin", c("a")), fl.Equals(plus(c("a"), v("zero")), c("a")))) \
        is not None


# A line the definiendum does not have the shape of is not a use of the symbol, whatever it is.

SHAPES = {
    "two atoms": fl.Iff(atom("P"), atom("Q")),
    "an atom and an equation": fl.Iff(atom("Cyclic", H), fl.Equals(H, K)),
    "an equation and an atom": fl.Iff(fl.Equals(H, K), atom("Cyclic", H)),
    "two equations": fl.Iff(fl.Equals(H, K), fl.Equals(K, H)),
    "a negation and an atom": fl.Iff(fl.Not(atom("Cyclic", H)), atom("Cyclic", H)),
}
# `Cyclic(H)` is a use of Cyclic wherever it stands, so for Cyclic a line that has it is refused for
# what the other side says; for Double, an equation `Double(n) = m` is the only use, and none of these is.
CYCLIC_HAS_NO_USE = ["two atoms", "two equations"]


@pytest.mark.parametrize("definition, shape", [(d, name) for d in (CYCLIC, DOUBLE) for name in SHAPES],
                         ids=[f"{d.symbol}-{name}" for d in (CYCLIC, DOUBLE) for name in SHAPES])
def test_a_biconditional_of_another_shape_is_refused_without_error(definition, shape):
    message = definition.instance_problem(SHAPES[shape])
    assert message is not None
    if definition is DOUBLE or shape in CYCLIC_HAS_NO_USE:
        assert message.endswith(f"here neither side of the biconditional is a use of {definition.symbol} "
                                f"of the form {df.show(definition.definiendum)}.")
    else:
        assert "the other side must be" in message
    assert not rule_of(definition).applies([], SHAPES[shape])


def test_an_atom_is_a_use_of_an_atom_symbol_and_an_equation_of_an_equation_symbol_only():
    # `Double(x) = y` is a use of Double; the atom `Double(x, y)` is not.
    assert DOUBLE.instance_problem(fl.Iff(atom("Double", c("x"), c("y")), fl.Equals(c("y"), plus(c("x"), c("x"))))) \
        is not None
    # `Cyclic(H) = K` is an equation, not an atom of Cyclic.
    assert CYCLIC.instance_problem(fl.Iff(fl.Equals(fn("Cyclic", H), K), fl.Exists("g", generates(v("g"), H)))) \
        is not None


# The helpers, on what the rules never give them.

def test_a_fresh_name_is_numbered_from_one_and_is_not_one_in_use():
    assert df._fresh_name("w", {"w"}) == "w_1"
    assert df._fresh_name("w", {"w", "w_1"}) == "w_2"
    assert df._fresh_name("w", {"w", "w_2"}) == "w_1"
    assert df._fresh_name("w", {"w_1", "v_1"}) == "w_2"


def test_each_quantifier_that_must_be_renamed_gets_a_name_of_its_own():
    # forall w, (P(w, x) and forall w, Q(w, x)) with the term w for x: both binders
    # are renamed, and the inner one is not the outer one.
    inner = fl.ForAll("w", atom("Q", v("w"), v("x")))
    formula = fl.ForAll("w", fl.And(atom("P", v("w"), v("x")), inner))
    result = df._instantiate(formula, {"x": v("w")}, {"w", "x"})
    assert df.show(result) == "forall w_1, (P(w_1, w) and forall w_2, Q(w_2, w))"


def test_a_quantifier_whose_variable_is_in_no_term_put_in_keeps_its_name():
    formula = fl.ForAll("w", atom("Q", v("w"), v("x")))
    assert df.show(df._instantiate(formula, {"x": v("y")}, {"w", "x", "y"})) == "forall w, Q(w, y)"


def test_a_formula_of_a_kind_the_instantiation_does_not_know_is_a_failure_not_a_copy():
    class Unknown(fl.Formula):
        def __repr__(self):
            return "Unknown"

    with pytest.raises(TypeError, match="cannot instantiate Unknown"):
        df._instantiate(Unknown(), {}, set())


def test_a_term_matches_a_pattern_of_its_shape_and_a_constant_matches_itself_only():
    binding = {}
    target = fn("f", c("a"))
    assert df._match_term(v("x"), target, binding) is True and binding["x"] is target
    assert df._match_term(fn("f", v("x")), fn("f", c("a")), {}) is True
    assert df._match_term(fn("f", v("x")), fn("g", c("a")), {}) is False
    assert df._match_term(fn("f", v("x")), fn("f", c("a"), c("b")), {}) is False
    assert df._match_term(fn("f", v("x")), c("a"), {}) is False
    assert df._match_term(c("a"), c("a"), {}) is True
    assert df._match_term(c("a"), c("b"), {}) is False
    assert df._match_term(c("a"), fn("a"), {}) is False


def _declared(name):
    return ("declare", [pl.Declaration(name, pl.DeclarationKind.OBJECT, type_name="object")])


def test_every_line_of_a_proof_is_visited_at_any_depth_and_a_block_is_not_a_line():
    phi = atom("P")
    entries = [
        "not an entry",
        ("1", phi, _declared("a")),
        ("2", "subproof", [("2.1", phi, _declared("b"))]),
        ("3", phi, ("rule_cond", []), [("3.1", phi, _declared("c")), ("3.2", phi, ("rule_x", []))]),
        ("4", phi, ("rule_hybrid", []), [[("4.1", phi, _declared("d"))], [("4.2", phi, _declared("e"))]]),
        ("5", phi, ("rule_x", [])),
    ]
    assert [parsed.label for parsed in df._lines(entries)] == \
        ["1", "2.1", "3", "3.1", "3.2", "4", "4.1", "4.2", "5"]


def test_the_top_level_declarations_are_those_of_the_lines_of_the_proof_itself():
    phi = atom("P")
    entries = [
        "not an entry",
        ("1", phi, _declared("a")),
        ("2", "subproof", [("2.1", phi, _declared("b"))]),
        ("3", phi, ("rule_cond", []), [("3.1", phi, _declared("c"))]),
        ("4", phi, ("rule_x", [])),
        ("5", phi, _declared("d")),
    ]
    assert [d.name for d in df._top_level_declarations(entries)] == ["a", "d"]


# ---------------------------------------------------------------------------
# The rule a theory registers
# ---------------------------------------------------------------------------

def test_a_definition_rule_is_cited_by_the_title_of_its_definition_and_takes_no_lines():
    rule = rule_of(CYCLIC)
    assert isinstance(rule, pl.InferenceRule)
    assert rule.name == rule.citation == "Definition of cyclic"
    assert rule.premise_arity == 0
    assert rule.definition is CYCLIC
    phi = ACCEPTED["for a constant"]
    assert rule.applies([], phi)
    assert not rule.applies([atom("P")], phi)
    assert rule.explain_in_context([atom("P")], phi, None) == "Definition of cyclic takes no cited lines."


def test_a_refused_citation_is_told_why():
    rule = rule_of(CYCLIC)
    assert rule.explain_in_context([], ACCEPTED["for a constant"], None) is None
    refused = REFUSED["another quantifier"]
    assert rule.explain_in_context([], refused, None) == CYCLIC.instance_problem(refused)


class Counting(df.Evidence):
    """Evidence that says `answer` and counts how often it is asked."""

    def __init__(self, answer=None):
        self.answer = answer
        self.asked = []

    def problem(self, definition, environment):
        self.asked.append(environment)
        return self.answer


def test_the_evidence_is_checked_once_and_in_the_theory_of_the_definition():
    evidence = Counting()
    definition = double_definition(evidence=evidence)
    theory = toy_theory(definition)
    rule = rule_of(definition, theory)
    sentence = DOUBLE_ACCEPTED["as defined"]
    assert evidence.asked == []                      # not when the theory is built
    assert rule.applies([], sentence) and rule.applies([], sentence)
    assert rule.evidence_problem() is None
    assert len(evidence.asked) == 1 and evidence.asked[0] is theory


def test_a_predicate_needs_no_evidence_so_none_is_asked_for():
    asked = []
    rule = df.DefinitionRule(CYCLIC, lambda: asked.append("the theory") or TOY)
    assert rule.applies([], ACCEPTED["for a constant"])
    assert rule.evidence_problem() is None
    assert asked == []


def test_the_theory_is_asked_for_when_the_first_citation_needs_it():
    asked = []

    def provider():
        asked.append("asked")
        return TOY

    rule = df.DefinitionRule(DOUBLE, provider)
    assert asked == []
    assert not rule.applies([], DOUBLE_REFUSED["no biconditional"])    # refused before the evidence
    assert asked == []
    assert rule.applies([], DOUBLE_ACCEPTED["as defined"])
    assert rule.applies([], DOUBLE_ACCEPTED["closed"])
    assert asked == ["asked"]


def test_the_theory_may_be_given_as_an_environment_or_as_a_function_of_none():
    for theory in (TOY, lambda: TOY):
        rule = df.DefinitionRule(DOUBLE, theory)
        assert rule.theory() is TOY
        assert rule.applies([], DOUBLE_ACCEPTED["as defined"])


def test_a_definition_whose_evidence_fails_is_refused_wherever_it_is_cited():
    evidence = Counting("there is no such thing")
    definition = double_definition(evidence=evidence)
    theory = toy_theory(definition)
    rule = rule_of(definition, theory)
    sentence = DOUBLE_ACCEPTED["as defined"]
    assert not rule.applies([], sentence)
    assert rule.evidence_problem() == "there is no such thing"
    assert rule.explain_in_context([], sentence, None) == \
        "Definition of double is refused, since there is no such thing."
    assert len(evidence.asked) == 1
    # Through the pipeline, for the sentence itself and for an instance of it.
    reason = refusal("1. Let x, y be any object. (Declaration)\n"
                     "2. Double(x) = y iff y = Plus(x, x). (Definition of double)\n", theory)
    assert reason.endswith("Definition of double is refused, since there is no such thing.")


def test_a_refusal_for_the_sentence_comes_before_one_for_the_evidence():
    evidence = Counting("there is no such thing")
    definition = double_definition(evidence=evidence)
    rule = rule_of(definition, toy_theory(definition))
    other = DOUBLE_REFUSED["the other sum"]
    assert rule.explain_in_context([], other, None) == definition.instance_problem(other)
    assert evidence.asked == []        # a line that is not the sentence never asks


def test_evidence_that_depends_on_its_own_definition_is_refused_not_looped():
    holder = []

    class Circular(df.Evidence):
        def problem(self, definition, environment):
            return holder[0].evidence_problem()

    definition = double_definition(evidence=Circular())
    rule = df.DefinitionRule(definition, TOY)
    holder.append(rule)
    assert rule.evidence_problem() == "its evidence depends on the definition it is evidence for"
    # Settled: asking again does not run it again, and the guard is not left set.
    assert rule.evidence_problem() == "its evidence depends on the definition it is evidence for"
    assert not rule.applies([], DOUBLE_ACCEPTED["as defined"])


def test_evidence_that_raises_leaves_the_rule_unsettled_and_the_guard_released():
    class Broken(df.Evidence):
        def problem(self, definition, environment):
            raise RuntimeError("the evidence is broken")

    rule = df.DefinitionRule(double_definition(evidence=Broken()), TOY)
    for _ in range(2):      # a leftover guard would make the second ask answer, not raise
        with pytest.raises(RuntimeError, match="the evidence is broken"):
            rule.evidence_problem()


def test_a_rule_is_the_definition_it_was_built_for():
    rule = rule_of(CYCLIC)
    assert rule.same_configuration(rule)
    assert rule.same_configuration(df.DefinitionRule(CYCLIC, TOY))             # the same definition
    assert not rule.same_configuration(df.DefinitionRule(cyclic_definition(), TOY))   # an equal one, built again
    assert not rule.same_configuration(rule_of(DOUBLE))
    assert not rule.same_configuration(pl.ReflexivityRule())
    assert not rule.same_configuration(None)

    class Subclass(df.DefinitionRule):
        pass

    assert not rule.same_configuration(Subclass(CYCLIC, TOY))


def test_a_registered_rule_authorizes_the_citation_of_that_definition_only():
    forged = df.DefinitionRule(cyclic_definition(), TOY)
    registered = rule_of(CYCLIC)
    assert pl._rule_among(registered, [registered])
    assert not pl._rule_among(forged, [registered])
    assert pl._rule_among(df.DefinitionRule(CYCLIC, TOY), [registered])


# ---------------------------------------------------------------------------
# Evidence: an axiom of the theory (`ByRule`)
# ---------------------------------------------------------------------------

class DoublesAxiom(pl.InferenceRule):
    """A toy axiom: every object has a double. It accepts the statement that
    `Double` has to show, and nothing else."""

    name = "Axiom of doubles"
    premise_arity = 0

    def applies(self, candidates, phi):
        return not candidates and pl._alpha_eq(phi, DOUBLE.existence_statement())


class Unreadable(pl.InferenceRule):
    name = "Unreadable axiom"
    premise_arity = 0

    def applies(self, candidates, phi):
        raise ValueError("cannot read this")


class Tagged(pl.InferenceRule):
    """An axiom that is a configuration: `Tagged("a")` is not `Tagged("b")`."""

    name = "Tagged axiom"
    premise_arity = 0

    def __init__(self, tag):
        self.tag = tag

    def same_configuration(self, other):
        return type(other) is Tagged and other.tag == self.tag

    def applies(self, candidates, phi):
        return not candidates and pl._alpha_eq(phi, DOUBLE.existence_statement())


def by_rule(axiom, *registered):
    """The `Double` definition whose evidence is `axiom`, and a theory with the rules `registered`."""
    definition = double_definition(evidence=df.ByRule(axiom))
    return definition, toy_theory(definition, rules=registered)


def evidence_problem(definition, theory):
    return rule_of(definition, theory).evidence_problem()


STATEMENT = "exists Y, forall m, (Y = m iff m = Plus(n, n))"


def test_the_statement_a_definition_has_to_show_is_written_as_a_proof_writes_it():
    assert df.show(DOUBLE.existence_statement()) == STATEMENT


def test_evidence_by_an_axiom_the_theory_has_and_that_accepts_the_statement():
    axiom = DoublesAxiom()
    definition, theory = by_rule(axiom, axiom)
    assert evidence_problem(definition, theory) is None
    assert check("1. Let x, y be any object. (Declaration)\n"
                 "2. Double(x) = y iff y = Plus(x, x). (Definition of double)\n", theory)[0]


def test_evidence_by_an_axiom_the_theory_does_not_have_shows_nothing():
    axiom = DoublesAxiom()
    definition, theory = by_rule(axiom)
    assert evidence_problem(definition, theory) == "Axiom of doubles is not a rule of the theory"
    reason = refusal("1. Let x, y be any object. (Declaration)\n"
                     "2. Double(x) = y iff y = Plus(x, x). (Definition of double)\n", theory)
    assert reason.endswith("Definition of double is refused, since Axiom of doubles is not a rule "
                           "of the theory.")


def test_evidence_by_an_axiom_that_does_not_say_there_is_such_a_thing():
    axiom = pl.ReflexivityRule()
    definition, theory = by_rule(axiom, axiom)
    assert evidence_problem(definition, theory) == f"Reflexivity does not accept {STATEMENT}"


def test_evidence_by_an_axiom_that_cannot_read_the_statement():
    axiom = Unreadable()
    definition, theory = by_rule(axiom, axiom)
    assert evidence_problem(definition, theory) == f"Unreadable axiom could not read {STATEMENT}: cannot read this"


def test_evidence_by_an_axiom_is_by_that_axiom_in_that_configuration():
    definition, theory = by_rule(Tagged("a"), Tagged("b"))
    assert evidence_problem(definition, theory) == "Tagged axiom is not a rule of the theory"
    definition, theory = by_rule(Tagged("a"), Tagged("b"), Tagged("a"))
    assert evidence_problem(definition, theory) is None


def test_the_axiom_is_asked_without_premises():
    asked = []

    class Spy(DoublesAxiom):
        name = "Spy axiom"

        def applies(self, candidates, phi):
            asked.append(list(candidates))
            return super().applies(candidates, phi)

    spy = Spy()
    definition, theory = by_rule(spy, spy)
    assert evidence_problem(definition, theory) is None
    assert asked == [[]]


# ---------------------------------------------------------------------------
# Evidence: a proof (`ByProof`)
# ---------------------------------------------------------------------------

class MarkedRecipe:
    """`Let n be a marked object.`: a declaration that says more of n than that it
    is an object -- a structure recorded in its metadata, and (if `states`) a
    formula `Marked(n)` the proof may use."""

    name = "marked object"

    def __init__(self, states):
        self.states = states

    def try_match(self, clauses, index):
        if index >= len(clauses):
            return None
        clause = clauses[index]
        descriptor = clause.normalized_descriptor.strip().lower()
        if descriptor not in ("marked object", "a marked object"):
            return None
        declarations = [pl.Declaration(name=name, kind=pl.DeclarationKind.OBJECT, type_name="object",
                                       metadata=(("marked", True),)) for name in clause.names]
        formulas = [atom("Marked", c(name)) for name in clause.names] if self.states else []
        return (1, declarations, formulas, [])


def by_proof(text, recipes=()):
    """`(definition, theory)` for `Double` with the evidence `text`, in a theory that
    also has `Cyclic`."""
    definition = double_definition(evidence=df.ByProof(text))
    return definition, toy_theory(CYCLIC, definition, recipes=recipes)


PROOF_ACCEPTED = {
    "the proof the definition is built with": (DOUBLE_EXISTS, ()),
    "the claim with other names for its variables": (
        "1. Let n be any object. (Declaration)\n" + double_claim("2", "3", thing="Z", value="k"), ()),
    "an object declared besides the parameter": (
        "1. Let n, k be any object. (Declaration)\n" + double_claim("2", "3"), ()),
    "a witness named at the top level": ("""\
1. Let n be any object. (Declaration)
2. Plus(n, n) = Plus(n, n). (Reflexivity)
3. Exists p, p = Plus(n, n). (Existential Introduction from 2)
4. Let q be such an object. (Existence from 3)
""" + double_claim("5", "6"), ()),
    "a witness and a definition named in the cases of a proof by cases": ("""\
1. Let n be any object. (Declaration)
2. n = n. (Reflexivity)
3. n = n or n = n. (Disjunction Introduction from 2)
4. Plus(n, n) = Plus(n, n). (Reflexivity)
5. Exists p, p = Plus(n, n). (Existential Introduction from 4)
6. Exists m, m = Plus(n, n). (Proof by Cases from 3, subproofs below)
begin subproof
 6.1. n = n. (Case)
 6.2. Let q be such an object. (Existence from 5)
 6.3. Exists m, m = Plus(n, n). (Existential Introduction from 4)
end subproof
begin subproof
 6.1. n = n. (Case)
 6.2. Define r = n and s = Plus(r, r). (Existence from 5)
 6.3. Exists m, m = Plus(n, n). (Existential Introduction from 4)
end subproof
""" + double_claim("7", "8"), ()),
}

PROOF_REFUSED = {
    "a proof that is not written as one": (
        "this is not a proof\n", (),
        "the proof of existence does not parse: Source line 1: missing explicit justification"),
    "a proof with a step that does not follow": ("""\
1. Let n be any object. (Declaration)
2. Exists m, m = Plus(n, n). (Reflexivity)
""", (), "the proof of existence is not a valid proof: Line 2: 'Reflexivity' does not justify"),
    "a proof of something else": ("""\
1. Let n be any object. (Declaration)
2. Plus(n, n) = Plus(n, n). (Reflexivity)
""", (), f"the proof of existence does not derive {STATEMENT} at its top level"),
    "a proof of the existence of the value without its uniqueness": ("""\
1. Let n be any object. (Declaration)
2. Plus(n, n) = Plus(n, n). (Reflexivity)
3. Exists m, m = Plus(n, n). (Existential Introduction from 2)
""", (), f"the proof of existence does not derive {STATEMENT} at its top level"),
    "a proof that derives it only inside a subproof": ("""\
1. Let n be any object. (Declaration)
2. n = n -> Exists Y, forall m, (Y = m iff m = Plus(n, n)). (Conditional Introduction from subproof below)
 2.1. n = n. (Assumption for Conditional Introduction)
""" + double_claim("2.2", "2.3", indent=" "), (),
     f"the proof of existence does not derive {STATEMENT} at its top level"),
    "a proof about an object it never declared": ("""\
1. Plus(n, n) = Plus(n, n). (Reflexivity)
2. Exists m, m = Plus(n, n). (Existential Introduction from 1)
""", (), "the proof of existence is not a valid proof: Line 1: constant 'n' is used but has not been declared"),
    "a proof that takes a fact about the parameter as a premise": ("""\
1. Let n be any object. (Declaration)
2. n = n. (Premise)
""" + double_claim("3", "4"), (), "the proof of existence takes n = n for granted; it may name what it has "
                                   "shown to exist and assume nothing else"),
    "a proof that takes a fact about another object as a premise": ("""\
1. Let n, k be any object. (Declaration)
2. k = k. (Premise)
""" + double_claim("3", "4"), (), "the proof of existence takes k = k for granted; it may name what it has "
                                   "shown to exist and assume nothing else"),
    "a proof that names the parameter as a witness": ("""\
1. Let k be any object. (Declaration)
2. k = k. (Reflexivity)
3. Exists n, n = k. (Existential Introduction from 2)
4. Let n be such an object. (Existence from 3)
""" + double_claim("5", "6"), (),
     "the proof of existence is not a proof about arbitrary objects: cannot generalize over 'n'"),
    "a proof that defines the parameter": ("""\
1. Let k be any object. (Declaration)
2. k = k. (Reflexivity)
3. Exists n, n = k. (Existential Introduction from 2)
4. Define n = k. (Existence from 3)
""" + double_claim("5", "6"), (),
     "the proof of existence is not a proof about arbitrary objects: cannot generalize over 'n'"),
    "a proof about a parameter declared with a property": (
        "1. Let n be a marked object. (Declaration)\n" + double_claim("2", "3"), (MarkedRecipe(True),),
        "the proof of existence takes Marked(n) for granted; it may name what it has shown to exist and "
        "assume nothing else"),
    "a proof about a parameter declared with a structure and no formula": (
        "1. Let n be a marked object. (Declaration)\n" + double_claim("2", "3"), (MarkedRecipe(False),),
        "the proof of existence declares n as more than an arbitrary object"),
    "a proof that declares a relation and its properties": ("""\
1. Let n, A be any object. (Declaration)
2. Let R be a reflexive relation on A. (Declaration)
""" + double_claim("3", "4"), (dm.RELATION_DECLARATION_RECIPE,),
     "the proof of existence takes for granted a structure (a relation and its properties) that it declares"),
    "a proof that cites a definition of the theory": ("""\
1. Let n be any object. (Declaration)
2. Cyclic(n) iff exists g, Generates(g, n). (Definition of cyclic)
""" + double_claim("3", "4"), (), "the proof of existence is not a valid proof: Line 2: no rule named "
                                   "'Definition of cyclic' is registered for this proof"),
    "a proof that cites the definition it is evidence for": ("""\
1. Let n, m be any object. (Declaration)
2. Double(n) = m iff m = Plus(n, n). (Definition of double)
""" + double_claim("3", "4"), (), "the proof of existence is not a valid proof: Line 2: no rule named "
                                   "'Definition of double' is registered for this proof"),
}


@pytest.mark.parametrize("text, recipes", list(PROOF_ACCEPTED.values()), ids=list(PROOF_ACCEPTED))
def test_a_proof_of_existence_that_derives_the_statement_about_arbitrary_objects_is_evidence(text, recipes):
    definition, theory = by_proof(text, recipes)
    assert evidence_problem(definition, theory) is None


@pytest.mark.parametrize("text, recipes, expected", list(PROOF_REFUSED.values()), ids=list(PROOF_REFUSED))
def test_a_proof_that_does_not_show_it_for_arbitrary_objects_is_not_evidence(text, recipes, expected):
    definition, theory = by_proof(text, recipes)
    problem = evidence_problem(definition, theory)
    assert problem is not None and problem.startswith(expected), problem
    # And the definition is refused wherever it is cited, with that reason.
    reason = refusal("1. Let x, y be any object. (Declaration)\n"
                     "2. Double(x) = y iff y = Plus(x, x). (Definition of double)\n", theory)
    assert reason.endswith(f"Definition of double is refused, since {problem}.")


def test_a_witness_named_in_a_case_is_a_witness_the_kernel_counts_as_a_premise():
    """What the proof of existence may not do is assume. A witness line is recorded
    by the kernel as a premise of the proof (it says of the new name what the
    existential says), and the definition tells it from an assumption by the
    line's declaration, wherever the line stands."""
    text, _recipes = PROOF_ACCEPTED["a witness and a definition named in the cases of a proof by cases"]
    definition, theory = by_proof(text)
    entries, _lines = pp.parse_proof_text(text, df._without_definitions(theory))
    proof = pl.Proof(entries)
    assert proof.check_detailed()[0]
    theorem = pl.promote_theorem("a theorem", proof, generalized_names=["n"],
                                 conclusion=definition.existence_statement())
    # What the kernel counts as the proof's premises: the three names it introduced, none of them assumed.
    assert [df.show(premise) for premise in theorem.premises] == \
        ["q = Plus(n, n)", "r = Plus(n, n)", "s = Plus(r, r)"]
    assert evidence_problem(definition, theory) is None


def test_a_proof_of_existence_is_checked_in_the_theory_without_its_definitions():
    definition, theory = by_proof(DOUBLE_EXISTS)
    stripped = df._without_definitions(theory)
    assert [r for r in stripped.rules if isinstance(r, df.DefinitionRule)] == []
    assert stripped.citable_titles == []
    assert any(isinstance(r, df.DefinitionRule) for r in theory.rules)      # the theory itself is not changed
    assert theory.citable_titles == ["Definition of cyclic", "Definition of double"]
    assert [d.name for d in stripped.declarations] == [d.name for d in theory.declarations]


# ---------------------------------------------------------------------------
# Registering definitions in a theory
# ---------------------------------------------------------------------------

def test_a_theory_registers_one_rule_declaration_and_title_per_definition():
    definitions = [CYCLIC, DOUBLE]
    rules = df.definition_rules(definitions, TOY)
    assert [r.definition for r in rules] == definitions
    assert all(isinstance(r, df.DefinitionRule) for r in rules)
    assert [(d.name, d.kind, d.arity) for d in df.definition_declarations(definitions)] == \
        [("Cyclic", pl.DeclarationKind.PREDICATE, 1), ("Double", pl.DeclarationKind.FUNCTION, 1)]
    assert df.definition_titles(definitions) == ["Definition of cyclic", "Definition of double"]
    assert df.definition_rules([], TOY) == [] and df.definition_declarations([]) == []
    assert df.definition_titles([]) == []


def test_two_definitions_may_not_name_the_same_symbol():
    again = cyclic_definition(title="Another definition of cyclic")
    with pytest.raises(df.DefinitionError,
                       match="Another definition of cyclic: Cyclic is already defined by Definition of cyclic"):
        df.definition_rules([CYCLIC, again], TOY)


@pytest.mark.parametrize("title", ["definition of Cyclic", "Definition-of-cyclic", "DEFINITION OF  CYCLIC"])
def test_two_definitions_may_not_have_titles_a_citation_cannot_tell_apart(title):
    other = cyclic_definition(title=title, symbol="Cyclical", definiendum=atom("Cyclical", v("G")))
    with pytest.raises(df.DefinitionError,
                       match=f"{title}: a citation of it cannot be told from Definition of cyclic"):
        df.definition_rules([CYCLIC, other], TOY)


def test_a_definition_may_not_be_titled_like_a_rule():
    with pytest.raises(df.DefinitionError, match="already the name of a rule"):
        cyclic_definition(title="Reflexivity")


# ---------------------------------------------------------------------------
# A proof cites a definition
# ---------------------------------------------------------------------------

CITATION = """\
1. Let h be any object. (Declaration)
2. Cyclic(h) iff exists g, Generates(g, h). ({title})
"""


@pytest.mark.parametrize("title", ["Definition of cyclic", "definition of cyclic", "Definition-of-cyclic",
                                   "DEFINITION OF  CYCLIC", "Definition Of Cyclic"])
def test_a_definition_is_cited_by_its_title_however_the_title_is_spelled(title):
    ok, error = check(CITATION.format(title=title))
    assert ok, error


@pytest.mark.parametrize("title", ["Definition of cyclics", "Definition of a cyclic group", "Cyclic"])
def test_a_title_that_is_not_the_definitions_is_a_rule_that_does_not_exist(title):
    assert refusal(CITATION.format(title=title)).startswith(f"no rule named '{title}' is registered")


def test_a_definition_is_not_cited_for_lines():
    reason = refusal("1. Let h be any object. (Declaration)\n"
                     "2. Cyclic(h) iff exists g, Generates(g, h). (Definition of cyclic)\n"
                     "3. Cyclic(h) iff exists g, Generates(g, h). (Definition of cyclic from 2)\n")
    assert reason == "'Definition of cyclic' requires at most 0 cited line label(s), but 1 were given (['2'])"


def test_a_theory_that_lists_a_title_must_have_its_rule_too():
    listed = TheoryEnvironment(name="titles only", declarations=TOY.declarations,
                               citable_titles=["Definition of cyclic"])
    reason = refusal(CITATION.format(title="Definition of cyclic"), listed)
    assert reason.startswith("no rule named 'Definition of cyclic' is registered for this proof")


def test_the_rule_is_cited_by_the_exact_title_without_listing_it_but_not_by_a_spelling_of_it():
    """`citable_titles` is what lets a proof spell the title otherwise: a bare name
    that no alias table knows is kept as written, and the validator looks the rule
    up by it."""
    unlisted = dataclasses.replace(TOY, citable_titles=[])
    assert check(CITATION.format(title="Definition of cyclic"), unlisted)[0]
    assert refusal(CITATION.format(title="definition of cyclic"), unlisted).startswith(
        "no rule named 'definition of cyclic' is registered")


def test_a_citation_of_a_definition_with_a_subproof_is_not_a_citation_of_it():
    with pytest.raises(ElaborationError, match="Invalid justification format"):
        pp.parse_proof_text(CITATION.format(title="Definition of cyclic subproof below"), TOY)


def test_a_theory_that_extends_another_has_the_titles_of_both():
    more = TheoryEnvironment(name="more", citable_titles=["Another title"])
    assert TOY.extended(more).citable_titles == ["Definition of cyclic", "Definition of double", "Another title"]
    assert more.extended(TOY).citable_titles == ["Another title", "Definition of cyclic", "Definition of double"]
    assert TheoryEnvironment().citable_titles == []
    extended = TOY.extended(more)
    ok, error = check(CITATION.format(title="definition-of-cyclic"), extended)
    assert ok, error


def test_a_definition_is_a_rule_a_theory_may_combine_with_another():
    """The rules and declarations travel with `extended`, so a theory built on
    this one cites the definitions as its own."""
    child = TOY.extended(TheoryEnvironment(name="child"))
    assert check(CITATION.format(title="Definition of cyclic"), child)[0]
    assert rule_of(CYCLIC, child) is rule_of(CYCLIC, TOY)


# ---------------------------------------------------------------------------
# A theorem proved from a definition
# ---------------------------------------------------------------------------

def promote(text, name, environment=TOY, generalized=("h",)):
    entries, _lines = pp.parse_proof_text(text, environment)
    proof = pl.Proof(entries)
    assert proof.check_detailed()[0]
    return pl.promote_theorem(name, proof, generalized_names=list(generalized))


def test_a_theorem_proved_from_a_definition_requires_the_definition():
    theorem = promote(CITATION.format(title="Definition of cyclic"), "Cyclic means generated")
    assert [r.name for r in theorem.required_rules] == ["Definition of cyclic"]
    assert theorem.premises == []


def test_a_theorem_proved_from_a_definition_is_citable_where_the_definition_is_a_rule():
    theorem = promote(CITATION.format(title="Definition of cyclic"), "Cyclic means generated")
    ok, error = use_of_theorem(theorem, rule_of(CYCLIC))
    assert ok, error


# A theory that has the vocabulary of the toy theory and none of its definitions.
VOCABULARY_ONLY = TheoryEnvironment(name="vocabulary only", declarations=TOY.declarations)
USE_OF_THEOREM = """\
1. Let k be any object. (Declaration)
2. Cyclic(k) iff exists g, Generates(g, k). (Cyclic means generated)
"""


def use_of_theorem(theorem, *rules):
    entries, _lines = pp.parse_proof_text(USE_OF_THEOREM, VOCABULARY_ONLY, theorem_names=(theorem.name,))
    return pl.Proof(entries, rules=pl.default_rules() + [theorem, *rules]).check_detailed()


def test_a_theorem_proved_from_a_definition_is_not_citable_where_the_definition_is_not_a_rule():
    theorem = promote(CITATION.format(title="Definition of cyclic"), "Cyclic means generated")
    ok, error = use_of_theorem(theorem)
    assert not ok
    assert "the theorem 'Cyclic means generated' was proved using the rule 'Definition of cyclic'" in error.detail


def test_a_theorem_proved_from_a_definition_is_not_citable_where_another_definition_is_the_rule():
    """The definition a theorem was proved from is that definition: an equal one,
    built again, is another one (its evidence is not this one's)."""
    theorem = promote(CITATION.format(title="Definition of cyclic"), "Cyclic means generated")
    ok, error = use_of_theorem(theorem, df.DefinitionRule(cyclic_definition(), TOY))
    assert not ok
    assert "was proved using the rule 'Definition of cyclic'" in error.detail
