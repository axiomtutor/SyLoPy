"""Tests for the definition of a thing that exists only under a condition.

`f(x)` makes sense only for an `x` in the domain of `f`, and `sup(X)` only for a set
that has a supremum. The owner decided (`todos.txt`, "Owner decisions") that such a
term always names something: the only thing that has the stated property, if exactly
one thing has it, and a fixed default otherwise -- the empty set, in set theory.
`Definitions.unique_or_default_definition` builds the definition:

    F(p) = m  iff  (m has the property and nothing else does)
                   or (no thing is the only one that has it, and m = default)

Its evidence is a proof, written by the builder, that some thing satisfies the
sentence for any values of the parameters (by cases on whether some thing is the
only one with the property). The facility checks it like any other evidence, so
these tests run the builder on a toy theory and on set theory, through the whole
pipeline, and look at four things:

  * what the sentence means, against every small finite model, by an oracle that
    does not use the builder;
  * that the evidence is accepted for properties and defaults of several shapes,
    whatever names they use (the proof makes up names of its own, and none may
    clash with one the definition has);
  * that a proof can cite the definition for the sentence about any terms and for
    nothing else, and gets from it the only-thing case and the default case;
  * that what is not a definition of this form is refused when it is built.

`test_definitions.py` is about the facility itself.
"""
from __future__ import annotations

import dataclasses
import itertools
from typing import Callable, NamedTuple, Optional, Tuple

import pytest

from SyLoPy.source import Definitions as df
from SyLoPy.source.ProofElaboration import TheoryEnvironment

from .support import atom, c, fl, fn, pl, pp, st, v


def generates(first, second):
    return atom("Generates", first, second)


ZERO = c("Zero")


# ---------------------------------------------------------------------------
# A toy theory and the definitions made in it
# ---------------------------------------------------------------------------

VOCABULARY = [
    pl.Declaration("Generates", pl.DeclarationKind.PREDICATE, arity=2),
    pl.Declaration("Triple", pl.DeclarationKind.PREDICATE, arity=3),
    pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
    pl.Declaration("Next", pl.DeclarationKind.FUNCTION, arity=1),
    pl.Declaration("Plus", pl.DeclarationKind.FUNCTION, arity=2),
]


def theory(*definitions: df.Definition, declarations=()) -> TheoryEnvironment:
    """A theory that has `definitions`, and what the tests define them with
    (`VOCABULARY`), and the `declarations` a test adds."""
    holder = {}
    environment = TheoryEnvironment(
        name="toy",
        rules=df.definition_rules(definitions, lambda: holder["environment"]),
        declarations=[*df.definition_declarations(definitions), *VOCABULARY, *declarations],
        citable_titles=df.definition_titles(definitions),
    )
    holder["environment"] = environment
    return environment


def generator(**changes) -> df.Definition:
    """`Gen(G)`: the only generator of G if G has exactly one, and `Zero` if not."""
    fields = dict(title="Definition of generator", symbol="Gen", parameters=("G",),
                  defining_property=generates(v("y"), v("G")), default=ZERO)
    return df.unique_or_default_definition(**{**fields, **changes})


GEN = generator()
TOY = theory(GEN)


def rule_of(definition: df.Definition, environment: TheoryEnvironment) -> df.DefinitionRule:
    return next(r for r in environment.rules
                if isinstance(r, df.DefinitionRule) and r.definition is definition)


def evidence_problem(definition: df.Definition, environment: Optional[TheoryEnvironment] = None):
    """Why the evidence of `definition` is refused in its theory, or None."""
    environment = theory(definition) if environment is None else environment
    return rule_of(definition, environment).evidence_problem()


def check(text: str, environment: TheoryEnvironment = TOY):
    """`(ok, error)` for the proof `text` checked in `environment`."""
    entries, _lines = pp.parse_proof_text(text, environment)
    return pl.Proof(entries).check_detailed()


def refusal(text: str, environment: TheoryEnvironment = TOY) -> str:
    """The reason the proof is refused; the proof must be refused."""
    ok, error = check(text, environment)
    assert not ok, "the proof was accepted"
    return error.detail


# ---------------------------------------------------------------------------
# The definition the builder makes
# ---------------------------------------------------------------------------

CLAIM = ("exists Y, forall m, (Y = m iff ((Generates(m, G) and forall z, (Generates(z, G) -> z = m)) "
         "or (not exists y, (Generates(y, G) and forall z, (Generates(z, G) -> z = y)) and m = Zero)))")


def test_the_sentence_says_the_only_thing_with_the_property_or_else_the_default():
    assert GEN.sentence() == (
        "Gen(G) = m iff ((Generates(m, G) and forall z, (Generates(z, G) -> z = m)) "
        "or (not exists y, (Generates(y, G) and forall z, (Generates(z, G) -> z = y)) and m = Zero))")


def test_the_definition_names_a_function_of_its_parameters():
    assert (GEN.title, GEN.symbol, GEN.kind, GEN.arity) == (
        "Definition of generator", "Gen", pl.DeclarationKind.FUNCTION, 1)
    assert GEN.variables == ("G", "m")
    assert GEN.parameters == ("G",)


def test_what_the_definition_has_to_show_is_that_some_thing_satisfies_the_sentence():
    assert df.show(GEN.existence_claim()) == CLAIM
    assert fl.free_variables(GEN.existence_claim()) == {"G"}


def test_a_proof_states_it_about_a_particular_object():
    assert df.show(GEN.existence_statement()) == CLAIM
    assert fl.free_variables(GEN.existence_statement()) == set()


def test_the_evidence_is_a_proof_the_facility_checks_like_any_other():
    assert isinstance(GEN.evidence, df.ByProof)
    assert evidence_problem(GEN) is None


def test_the_type_of_the_thing_is_the_one_given_and_none_if_none_is():
    assert GEN.type_name is None
    assert generator(type_name="set operation").type_name == "set operation"
    assert generator(type_name="set operation").declaration().type_name == "set operation"


def test_two_definitions_of_this_form_are_registered_like_any_two_definitions():
    other = generator(title="Definition of cyclic generator", symbol="CGen")
    assert [r.definition.symbol for r in df.definition_rules([GEN, other], lambda: None)] == ["Gen", "CGen"]
    with pytest.raises(df.DefinitionError, match="Gen is already defined by Definition of generator"):
        df.definition_rules([GEN, generator(title="Definition of another generator")], lambda: None)


# ---------------------------------------------------------------------------
# What the sentence means: an oracle over every small finite model
# ---------------------------------------------------------------------------
#
# A model is a domain, a relation on it for the predicate the property is about
# (`Generates`, or `Triple` for three arguments), and the function `Next` that
# moves along the domain. `Zero` is the element called "Zero"; it is always
# in the domain, and since the relation is every relation on the domain, every
# choice of which element `Zero` is, up to renaming, is covered. The oracle
# looks only at the property of the definition and works out the right
# value by itself: the only thing with the property if exactly one thing has it,
# else what the default names. It does not look at how the builder wrote the
# sentence, so it can tell if the sentence is right.

class Shape(NamedTuple):
    name: str
    definition: df.Definition
    parameters: Tuple[str, ...]
    arity: int                  # of the relation the property is about
    sizes: Tuple[int, ...]      # the sizes of the domains tried
    has: Callable               # (domain, relation, thing, *parameters) -> does the thing have the property?
    default: Callable           # (domain) -> the element the default names


def _next_default(domain):
    return domain[1 % len(domain)]


SHAPES = [
    Shape("an atom", GEN, ("G",), 2, (1, 2, 3),
          lambda domain, relation, y, g: (y, g) in relation,
          lambda domain: "Zero"),
    Shape("a thing called otherwise", generator(thing="x", defining_property=generates(v("x"), v("G"))),
          ("G",), 2, (1, 2, 3),
          lambda domain, relation, y, g: (y, g) in relation,
          lambda domain: "Zero"),
    Shape("a property with a quantifier of its own",
          generator(defining_property=fl.ForAll("w", fl.Implies(generates(v("w"), v("y")),
                                                                generates(v("w"), v("G"))))),
          ("G",), 2, (1, 2, 3),
          lambda domain, relation, y, g: all((w, y) not in relation or (w, g) in relation for w in domain),
          lambda domain: "Zero"),
    Shape("two parameters",
          generator(parameters=("G", "H"), defining_property=atom("Triple", v("y"), v("G"), v("H"))),
          ("G", "H"), 3, (1, 2),
          lambda domain, relation, y, g, h: (y, g, h) in relation,
          lambda domain: "Zero"),
    Shape("a parameter the property does not use",
          generator(parameters=("G", "H")),
          ("G", "H"), 2, (1, 2),
          lambda domain, relation, y, g, h: (y, g) in relation,
          lambda domain: "Zero"),
    Shape("a default that is a term", generator(default=fn("Next", ZERO)),
          ("G",), 2, (1, 2, 3),
          lambda domain, relation, y, g: (y, g) in relation,
          _next_default),
    Shape("a property that does not mention the thing",
          generator(defining_property=fl.ForAll("w", generates(v("w"), v("G")))),
          ("G",), 2, (1, 2, 3),
          lambda domain, relation, y, g: all((w, g) in relation for w in domain),
          lambda domain: "Zero"),
]
SHAPE = {shape.name: shape for shape in SHAPES}


def relations(domain, arity):
    """Every relation of the given arity on `domain`."""
    cases = list(itertools.product(domain, repeat=arity))
    for chosen in itertools.product((False, True), repeat=len(cases)):
        yield {case for case, picked in zip(cases, chosen) if picked}


def evaluated(formula, schema, domain) -> bool:
    return fl.evaluate_formula(formula, schema, {"_": domain})


def disagreement(shape: Shape, sentence: Optional[fl.Formula] = None, claim: bool = True) -> Optional[str]:
    """What is wrong with `sentence` (the definition's own by default) as a meaning for the
    shape's thing: the first model, and values of the parameters, where the things that satisfy the
    sentence are not exactly the one the property and the default call for -- or where the
    definition's existence claim is false. None if it is right everywhere."""
    definition = shape.definition
    value = definition.variables[-1]
    sentence = definition.definiens if sentence is None else sentence
    existence = definition.existence_claim()
    for size in shape.sizes:
        domain = ["Zero", *range(1, size)]
        for relation in relations(domain, shape.arity):
            holds = lambda *arguments: tuple(arguments) in relation          # noqa: E731
            schema = {"Generates": holds, "Triple": holds,
                      "Next": lambda x: domain[(domain.index(x) + 1) % len(domain)]}
            for values in itertools.product(domain, repeat=len(shape.parameters)):
                given = dict(zip(shape.parameters, values))
                things = [y for y in domain if shape.has(domain, relation, y, *values)]
                expected = things[0] if len(things) == 1 else shape.default(domain)
                satisfying = [m for m in domain if evaluated(sentence, {**schema, **given, value: m}, domain)]
                where = f"on {domain} with the relation {sorted(relation, key=str)} and {given}"
                if satisfying != [expected]:
                    return f"{where}, the value should be {expected!r} and the sentence is satisfied by {satisfying}"
                if claim and not evaluated(existence, {**schema, **given}, domain):
                    return f"{where}, the existence claim is false"
    return None


@pytest.mark.parametrize("shape", SHAPES, ids=[shape.name for shape in SHAPES])
def test_the_value_is_the_only_thing_with_the_property_and_the_default_if_there_is_not_exactly_one(shape):
    assert disagreement(shape) is None


def _only(term, argument=v("G"), other="z"):
    """`term` is a generator of `argument`, and nothing else is."""
    return fl.And(generates(term, argument),
                  fl.ForAll(other, fl.Implies(generates(v(other), argument), fl.Equals(v(other), term))))


def _some_only(argument=v("G"), thing="y"):
    """Some thing is the only generator of `argument`."""
    return fl.Exists(thing, _only(v(thing), argument))


NEARLY_RIGHT = {
    "the sentence written by hand, as it should be": (
        lambda m: fl.Or(_only(m), fl.And(fl.Not(_some_only()), fl.Equals(m, ZERO))), True),
    "a generator rather than the only one": (
        lambda m: fl.Or(generates(m, v("G")),
                        fl.And(fl.Not(fl.Exists("y", generates(v("y"), v("G")))), fl.Equals(m, ZERO))), False),
    "the parameter as the default": (
        lambda m: fl.Or(_only(m), fl.And(fl.Not(_some_only()), fl.Equals(m, v("G")))), False),
    "no default at all": (lambda m: _only(m), False),
    "the default also when there are no generators only": (
        lambda m: fl.Or(_only(m),
                        fl.And(fl.Not(fl.Exists("y", generates(v("y"), v("G")))), fl.Equals(m, ZERO))), False),
}


@pytest.mark.parametrize("sentence, is_right", list(NEARLY_RIGHT.values()), ids=list(NEARLY_RIGHT))
def test_the_oracle_accepts_the_right_sentence_and_not_one_that_is_nearly_right(sentence, is_right):
    problem = disagreement(SHAPE["an atom"], sentence(v("m")), claim=False)
    assert (problem is None) == is_right, problem


# ---------------------------------------------------------------------------
# Names: the proof makes up some of its own, and none may clash
# ---------------------------------------------------------------------------

def _all_of(*names, thing="y"):
    """The property that `thing` is a generator of each of `names`."""
    parts = [generates(v(thing), v(name)) for name in names]
    return parts[0] if len(parts) == 1 else fl.And(*parts)


CLASHES = {
    "a parameter called a": generator(parameters=("a",), defining_property=_all_of("a")),
    "parameters called like the constants the proof makes up": generator(
        parameters=("a", "b", "v", "w"), defining_property=_all_of("a", "b", "v", "w")),
    "a parameter called m, the name of the value": generator(parameters=("m",), defining_property=_all_of("m")),
    "a parameter called z": generator(parameters=("z",), defining_property=_all_of("z")),
    "a parameter that the property does not use, called m": generator(parameters=("G", "m")),
    "a parameter that the property does not use, called z": generator(parameters=("G", "z")),
    "a thing that the property does not mention, called m": generator(
        thing="m", defining_property=fl.ForAll("w", generates(v("w"), v("G")))),
    "a thing that the property does not mention, called z": generator(
        thing="z", defining_property=fl.ForAll("w", generates(v("w"), v("G")))),
    "a thing called m": generator(thing="m", defining_property=_all_of("G", thing="m")),
    "a thing called z": generator(thing="z", defining_property=_all_of("G", thing="z")),
    "a thing called a": generator(thing="a", defining_property=_all_of("G", thing="a")),
    "bound variables called like the ones the proof makes up": generator(
        defining_property=fl.ForAll("w", fl.Implies(
            generates(v("w"), v("y")),
            fl.Exists("m", fl.And(generates(v("m"), v("w")), fl.ForAll("z", generates(v("z"), v("G")))))))),
    "the symbol called m": generator(symbol="m"),
}


@pytest.mark.parametrize("definition", list(CLASHES.values()), ids=list(CLASHES))
def test_the_evidence_is_accepted_whatever_the_property_and_the_parameters_are_called(definition):
    assert evidence_problem(definition) is None


DECLARED_CONSTANTS = {name: pl.Declaration(name, pl.DeclarationKind.OBJECT) for name in ("a", "b", "v", "w", "m", "z")}


@pytest.mark.parametrize("name", ["a", "b", "v", "w", "m", "z"])
def test_the_evidence_is_accepted_for_a_default_called_like_a_name_the_proof_makes_up(name):
    definition = generator(default=c(name))
    assert evidence_problem(definition, theory(definition, declarations=[DECLARED_CONSTANTS[name]])) is None


@pytest.mark.parametrize("name", ["a", "v", "w", "m", "z"])
def test_the_evidence_is_accepted_for_a_default_that_applies_a_function_called_like_such_a_name(name):
    definition = generator(default=fn(name, ZERO))
    function = pl.Declaration(name, pl.DeclarationKind.FUNCTION, arity=1)
    assert evidence_problem(definition, theory(definition, declarations=[function])) is None


@pytest.mark.parametrize("name", ["a", "b", "v", "w", "m", "z"])
def test_the_evidence_is_accepted_for_a_property_that_applies_a_symbol_called_like_a_name_the_proof_makes_up(name):
    predicate = generator(defining_property=atom(name, v("y"), v("G")))
    function = generator(defining_property=generates(fn(name, v("y")), v("G")))
    assert evidence_problem(predicate, theory(
        predicate, declarations=[pl.Declaration(name, pl.DeclarationKind.PREDICATE, arity=2)])) is None
    assert evidence_problem(function, theory(
        function, declarations=[pl.Declaration(name, pl.DeclarationKind.FUNCTION, arity=1)])) is None


def test_the_evidence_is_accepted_for_other_shapes():
    for definition in [shape.definition for shape in SHAPES] + [
            generator(default=fn("Plus", fn("Next", ZERO), ZERO)),
            generator(parameters=("G", "H", "K"), defining_property=_all_of("G", "H", "K")),
            generator(defining_property=fl.Or(generates(v("y"), v("G")), fl.Not(generates(v("G"), v("y"))))),
            generator(defining_property=fl.Equals(v("y"), v("G"))),
            generator(defining_property=fl.ForAll("w", generates(v("w"), v("G"))))]:
        assert evidence_problem(definition) is None, definition.sentence()


@pytest.mark.parametrize("changes, value, the_other", [
    (dict(), "m", "z"),
    (dict(parameters=("m",), defining_property=_all_of("m")), "m1", "z"),
    (dict(parameters=("m", "m1"), defining_property=_all_of("m", "m1")), "m2", "z"),
    (dict(thing="m", defining_property=_all_of("G", thing="m")), "m1", "z"),
    (dict(symbol="m"), "m1", "z"),
    (dict(default=c("m")), "m1", "z"),
    (dict(defining_property=fl.ForAll("m", generates(v("m"), v("G")))), "m1", "z"),
    (dict(parameters=("z",), defining_property=_all_of("z")), "m", "z1"),
    (dict(thing="z", defining_property=_all_of("G", thing="z")), "m", "z1"),
    (dict(defining_property=fl.ForAll("z", generates(v("z"), v("G")))), "m", "z1"),
])
def test_the_names_made_up_are_the_first_that_the_definition_does_not_use(changes, value, the_other):
    definition = generator(**changes)
    assert definition.variables[-1] == value
    assert f"forall {the_other}, " in definition.sentence()


@pytest.mark.parametrize("other", [
    generator(default=fn("Next", ZERO)),
    generator(defining_property=generates(v("G"), v("y"))),
], ids=["another default", "another property"])
def test_the_evidence_is_for_the_sentence_it_was_built_with_and_for_no_other(other):
    borrowed = dataclasses.replace(GEN, evidence=other.evidence)
    problem = evidence_problem(borrowed, theory(borrowed))
    assert problem is not None and problem.startswith("the proof of existence"), problem


def test_the_names_of_the_bound_variables_do_not_matter_to_the_evidence():
    """The facility compares what the proof derives with what has to be shown up to the names of
    bound variables, so the evidence of a definition that calls the thing `x` shows what one that
    calls it `y` has to show."""
    borrowed = dataclasses.replace(GEN, evidence=generator(thing="x", defining_property=generates(v("x"), v("G"))).evidence)
    assert evidence_problem(borrowed, theory(borrowed)) is None


# ---------------------------------------------------------------------------
# The theory that registers it
# ---------------------------------------------------------------------------

def test_the_theory_must_declare_the_default():
    theory_without_zero = TheoryEnvironment(
        name="toy", rules=df.definition_rules([GEN], lambda: theory_without_zero),
        declarations=[*df.definition_declarations([GEN]), VOCABULARY[0]],
        citable_titles=df.definition_titles([GEN]))
    assert "constant 'Zero' is used but has not been declared" in evidence_problem(GEN, theory_without_zero)


def test_the_theory_must_declare_what_the_property_uses():
    theory_without_generates = TheoryEnvironment(
        name="toy", rules=df.definition_rules([GEN], lambda: theory_without_generates),
        declarations=[*df.definition_declarations([GEN]), VOCABULARY[2]],
        citable_titles=df.definition_titles([GEN]))
    assert "'Generates' is used but has not been declared" in evidence_problem(GEN, theory_without_generates)


def test_the_property_may_use_a_symbol_that_an_earlier_definition_introduced():
    cyclic = df.Definition(title="Definition of cyclic", symbol="Cyclic", variables=("G",),
                           definiendum=atom("Cyclic", v("G")),
                           definiens=fl.Exists("g", generates(v("g"), v("G"))))
    generated = generator(title="Definition of cyclic generator", symbol="CGen",
                          defining_property=atom("Cyclic", v("y")))
    environment = theory(cyclic, generated)
    assert evidence_problem(generated, environment) is None
    ok, error = check("1. Let G, g be any object. (Declaration)\n"
                      "2. Cyclic(g). (Premise)\n"
                      "3. forall z, (Cyclic(z) -> z = g). (Premise)\n"
                      "4. Cyclic(g) and (forall z, (Cyclic(z) -> z = g)). (Conjunction Introduction from 2, 3)\n"
                      "5. CGen(G) = g iff ((Cyclic(g) and (forall z, (Cyclic(z) -> z = g))) or "
                      "((not (exists y, (Cyclic(y) and (forall z, (Cyclic(z) -> z = y))))) and (g = Zero))). "
                      "(Definition of cyclic generator)\n", environment)
    assert ok, error


# ---------------------------------------------------------------------------
# The sentence a proof cites
# ---------------------------------------------------------------------------

H, K = c("H"), c("K")


def sentence_for(term, argument=v("G"), *, thing="y", other="z", default=ZERO, reverse=False,
                 the_property=generates, symbol="Gen"):
    """`Gen(argument) = term iff (term is the only generator of argument) or (no thing
    is, and term = Zero)`, written without the builder, with the names `thing` and
    `other` for the bound variables. Tests change one detail at a time."""
    z, y = v(other), v(thing)

    def only(t):
        return fl.And(the_property(t, argument),
                      fl.ForAll(other, fl.Implies(the_property(z, argument), fl.Equals(z, t))))

    some_only = fl.Exists(thing, only(y))
    sides = [fl.Equals(fn(symbol, argument), term),
             fl.Or(only(term), fl.And(fl.Not(some_only), fl.Equals(term, default)))]
    return fl.Iff(*(reversed(sides) if reverse else sides))


def test_the_sentence_a_test_writes_by_hand_is_the_one_the_builder_writes():
    assert pl._ast_eq(fl.Iff(GEN.definiendum, GEN.definiens), sentence_for(v("m")))


ACCEPTED = {
    "for a constant": sentence_for(H),
    "for a variable": sentence_for(v("h")),
    "for a term built from others": sentence_for(fn("Plus", H, fn("Next", K))),
    "about a constant in place of the parameter": sentence_for(H, argument=K),
    "about a term in place of the parameter": sentence_for(H, argument=fn("Next", K)),
    "with the biconditional the other way round": sentence_for(H, reverse=True),
    "with the bound variables called otherwise": sentence_for(H, thing="k", other="j"),
    "for a variable called like a bound variable, which the quantifier must not capture":
        sentence_for(v("z"), other="k"),
    "for a variable called like the other bound variable, renamed": sentence_for(v("y"), thing="k"),
    "with the leading forall over the variable the definition has": fl.ForAll("G", sentence_for(H, argument=v("G"))),
    "closed over several variables": fl.ForAll("h", fl.ForAll("G", sentence_for(v("h")))),
    "closed over a variable it does not have": fl.ForAll("x", sentence_for(H)),
}

REFUSED = {
    "the equation alone": fl.Equals(fn("Gen", v("G")), H),
    "only one direction": fl.Implies(sentence_for(H).left, sentence_for(H).right),
    "without the uniqueness of the thing": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(generates(H, v("G")),
              fl.And(fl.Not(_some_only()), fl.Equals(H, ZERO)))),
    "without the case that none is the only one": fl.Iff(fl.Equals(fn("Gen", v("G")), H), _only(H)),
    "with the cases in the other order": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(fl.And(fl.Not(_some_only()), fl.Equals(H, ZERO)), _only(H))),
    "with the default of another definition": sentence_for(H, default=K),
    "with the default the parameter": sentence_for(H, default=v("G")),
    "with the default the other way round": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(_only(H), fl.And(fl.Not(_some_only()), fl.Equals(ZERO, H)))),
    "with a different property": sentence_for(H, the_property=lambda t, g: generates(g, t)),
    "with the property about another argument": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(_only(H, K), fl.And(fl.Not(_some_only(K)), fl.Equals(H, ZERO)))),
    "about a thing other than the one the equation names": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(_only(K), fl.And(fl.Not(_some_only()), fl.Equals(K, ZERO)))),
    "for the symbol applied to another term": fl.Iff(
        fl.Equals(fn("Gen", K), H),
        fl.Or(_only(H), fl.And(fl.Not(_some_only()), fl.Equals(H, ZERO)))),
    "with a quantifier that captures the term": sentence_for(v("z"), other="z"),
    "with the existential quantifier changed": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(_only(H), fl.And(fl.Not(fl.ForAll("y", _only(v("y")))), fl.Equals(H, ZERO)))),
    "with the negation dropped": fl.Iff(
        fl.Equals(fn("Gen", v("G")), H),
        fl.Or(_only(H), fl.And(_some_only(), fl.Equals(H, ZERO)))),
    "another symbol": sentence_for(H, symbol="Other"),
}


@pytest.mark.parametrize("phi", list(ACCEPTED.values()), ids=list(ACCEPTED))
def test_the_definition_is_cited_for_its_sentence_about_any_terms(phi):
    assert GEN.instance_problem(phi) is None
    assert rule_of(GEN, TOY).applies([], phi)


@pytest.mark.parametrize("phi", list(REFUSED.values()), ids=list(REFUSED))
def test_the_definition_is_cited_for_its_sentence_and_nothing_else(phi):
    assert GEN.instance_problem(phi) is not None
    assert not rule_of(GEN, TOY).applies([], phi)


# ---------------------------------------------------------------------------
# What a proof gets from it: the only-thing case and the default case
# ---------------------------------------------------------------------------

SOME_ONLY = "(exists y, (Generates(y, G) and (forall z, (Generates(z, G) -> z = y))))"


def only_line(term):
    return f"(Generates({term}, G) and (forall z, (Generates(z, G) -> z = {term})))"


def sentence_line(term):
    return f"Gen(G) = {term} iff ({only_line(term)} or ((not {SOME_ONLY}) and ({term} = Zero)))"


THE_ONLY_GENERATOR = f"""\
1. Let G, g be any object. (Declaration)
2. Generates(g, G). (Premise)
3. forall z, (Generates(z, G) -> z = g). (Premise)
4. Generates(g, G) and (forall z, (Generates(z, G) -> z = g)). (Conjunction Introduction from 2, 3)
5. {sentence_line("g")}. (Definition of generator)
6. {only_line("g")} or ((not {SOME_ONLY}) and (g = Zero)). (Disjunction Introduction from 4)
7. ({only_line("g")} or ((not {SOME_ONLY}) and (g = Zero))) -> Gen(G) = g. (Biconditional Elimination from 5)
8. Gen(G) = g. (Modus Ponens from 6, 7)
"""

NO_GENERATOR_IS_THE_ONLY_ONE = f"""\
1. Let G be any object. (Declaration)
2. not {SOME_ONLY}. (Premise)
3. Zero = Zero. (Reflexivity)
4. (not {SOME_ONLY}) and (Zero = Zero). (Conjunction Introduction from 2, 3)
5. {sentence_line("Zero")}. (Definition of generator)
6. {only_line("Zero")} or ((not {SOME_ONLY}) and (Zero = Zero)). (Disjunction Introduction from 4)
7. ({only_line("Zero")} or ((not {SOME_ONLY}) and (Zero = Zero))) -> Gen(G) = Zero. (Biconditional Elimination from 5)
8. Gen(G) = Zero. (Modus Ponens from 6, 7)
"""


def test_the_only_thing_with_the_property_is_the_value():
    ok, error = check(THE_ONLY_GENERATOR)
    assert ok, error


def test_the_default_is_the_value_if_no_thing_is_the_only_one_with_the_property():
    ok, error = check(NO_GENERATOR_IS_THE_ONLY_ONE)
    assert ok, error


def test_a_thing_with_the_property_that_may_not_be_the_only_one_is_not_the_value():
    """The twin of the proof of the only generator, without the line that says nothing else generates G:
    the uniqueness is what the value needs."""
    without_uniqueness = THE_ONLY_GENERATOR.replace(
        "4. Generates(g, G) and (forall z, (Generates(z, G) -> z = g)). (Conjunction Introduction from 2, 3)\n",
        "4. Generates(g, G) and (forall z, (Generates(z, G) -> z = g)). (Conjunction Introduction from 2, 2)\n")
    assert refusal(without_uniqueness).startswith("'ConjunctionIntroduction' does not justify")


def test_the_property_alone_does_not_give_the_default_either():
    """The twin of the proof of the default, without the line that says no generator is the only one."""
    reason = refusal(NO_GENERATOR_IS_THE_ONLY_ONE.replace(
        f"2. not {SOME_ONLY}. (Premise)\n", "2. Generates(Zero, G). (Premise)\n"))
    assert reason.startswith("'ConjunctionIntroduction' does not justify")


def test_the_definition_is_cited_by_its_title():
    ok, error = check("1. Let G, h be any object. (Declaration)\n"
                      f"2. {sentence_line('h')}. (Definition of generator)\n")
    assert ok, error


def test_a_citation_of_the_definition_for_another_sentence_is_refused_and_says_why():
    reason = refusal("1. Let G, h be any object. (Declaration)\n"
                     f"2. Gen(G) = h iff {only_line('h')}. (Definition of generator)\n")
    assert reason.endswith("is not an instance of the sentence the definition cites") or "Definition of generator" in reason, reason


# ---------------------------------------------------------------------------
# A thing that is not a definition of this form is refused when it is built
# ---------------------------------------------------------------------------

BAD = {
    "no parameter": (dict(parameters=()), "needs a parameter"),
    "a parameter named twice": (dict(parameters=("G", "G")), "its parameters must be distinct names"),
    "a parameter with no name": (dict(parameters=("G", "")), "its parameters must be distinct names"),
    "no name for the thing": (dict(thing=""), "the thing needs a name"),
    "the thing called like a parameter": (dict(thing="G"), "the thing is called G, which is also a parameter"),
    "no symbol": (dict(symbol=""), "needs a symbol to name"),
    "a property with a variable that is neither the thing nor a parameter": (
        dict(defining_property=generates(v("y"), v("H"))), "has H free, which is neither the thing nor a parameter"),
    "several such variables": (
        dict(defining_property=fl.And(generates(v("y"), v("H")), generates(v("K"), v("G")))),
        "has H, K free"),
    "a default that is not a term": (dict(default="Zero"), "the default must be a term"),
    "a default with a variable": (dict(default=v("k")), "must be one fixed term, but it has k in it"),
    "a default with a variable inside a term": (
        dict(default=fn("Plus", ZERO, v("k"))), "must be one fixed term, but it has k in it"),
    "a default with a parameter in it": (dict(default=v("G")), "must be one fixed term, but it has G in it"),
    "an empty title": (dict(title=""), "needs a title"),
    "a title with `from`": (dict(title="Generator from generators"), "`from` or `subproof`"),
    "the name of a rule as the title": (dict(title="Modus Ponens"), "already the name of a rule"),
    "a property that uses the symbol it defines": (
        dict(defining_property=generates(fn("Gen", v("G")), v("y"))), "uses Gen, which it is defining"),
    "a property that binds a parameter": (
        dict(defining_property=fl.ForAll("G", generates(v("y"), v("G")))), "binds G"),
    "a property that binds the name of the thing": (
        dict(defining_property=fl.And(generates(v("y"), v("G")), fl.Exists("y", generates(v("y"), v("y"))))),
        "the property binds y, which is also the name of the thing; rename the bound variable"),
    "a property that binds the name of the thing and does not mention the thing": (
        dict(defining_property=fl.ForAll("y", generates(v("y"), v("G")))),
        "the property binds y, which is also the name of the thing"),
}


@pytest.mark.parametrize("changes, reason", list(BAD.values()), ids=list(BAD))
def test_what_is_not_a_definition_of_this_form_is_refused_when_it_is_built(changes, reason):
    with pytest.raises(df.DefinitionError, match=reason):
        generator(**changes)


def test_a_refusal_names_the_definition_it_is_about():
    with pytest.raises(df.DefinitionError, match="^Definition of generator: "):
        generator(parameters=())
    with pytest.raises(df.DefinitionError, match=r"^\(untitled definition\): "):
        generator(title="")


# ---------------------------------------------------------------------------
# Set theory: the only member of a set, and the empty set otherwise
# ---------------------------------------------------------------------------

def set_theory_with(*definitions: df.Definition) -> TheoryEnvironment:
    holder = {}
    environment = st.SET_THEORY_ENVIRONMENT.extended(TheoryEnvironment(
        name="set theory with the definitions of the tests",
        rules=df.definition_rules(definitions, lambda: holder["environment"]),
        declarations=df.definition_declarations(definitions),
        citable_titles=df.definition_titles(definitions)))
    holder["environment"] = environment
    return environment


ONLY_MEMBER = df.unique_or_default_definition(
    "Definition of the only member", "OnlyMember", ("S",), atom("In", v("y"), v("S")), st.EMPTY_SET,
    type_name="set operation")
SETS = set_theory_with(ONLY_MEMBER)

THE_ONLY_MEMBER_SENTENCE = (
    "OnlyMember(S) = m iff ((In(m, S) and forall z, (In(z, S) -> z = m)) or "
    "(not exists y, (In(y, S) and forall z, (In(z, S) -> z = y)) and m = EmptySet))")


def test_set_theory_names_the_only_member_of_a_set_and_the_empty_set_otherwise():
    assert ONLY_MEMBER.sentence() == THE_ONLY_MEMBER_SENTENCE
    assert (ONLY_MEMBER.kind, ONLY_MEMBER.arity, ONLY_MEMBER.type_name) == (
        pl.DeclarationKind.FUNCTION, 1, "set operation")


def test_the_evidence_is_accepted_in_set_theory():
    assert evidence_problem(ONLY_MEMBER, SETS) is None


def in_(element, a_set):
    return f"In({element}, {a_set})"


def only_member_line(term, a_set):
    only = f"(In({term}, {a_set}) and (forall z, (In(z, {a_set}) -> z = {term})))"
    some = f"(exists y, (In(y, {a_set}) and (forall z, (In(z, {a_set}) -> z = y))))"
    return only, some, f"OnlyMember({a_set}) = {term} iff ({only} or ((not {some}) and ({term} = EmptySet)))"


def test_a_set_with_one_member_has_that_member_as_its_only_member():
    only, some, sentence = only_member_line("B", "A")
    ok, error = check(f"""\
1. Let A, B be any set. (Declaration)
2. In(B, A). (Premise)
3. forall z, (In(z, A) -> z = B). (Premise)
4. In(B, A) and (forall z, (In(z, A) -> z = B)). (Conjunction Introduction from 2, 3)
5. {sentence}. (Definition of the only member)
6. {only} or ((not {some}) and (B = EmptySet)). (Disjunction Introduction from 4)
7. ({only} or ((not {some}) and (B = EmptySet))) -> OnlyMember(A) = B. (Biconditional Elimination from 5)
8. OnlyMember(A) = B. (Modus Ponens from 6, 7)
""", SETS)
    assert ok, error


def test_the_empty_set_has_the_empty_set_as_its_only_member():
    only, some, sentence = only_member_line("EmptySet", "EmptySet")
    ok, error = check(f"""\
1. not {some}. (Proof by Contradiction from subproof below)
begin subproof
 1.1. {some}. (Assumption for contradiction)
 1.2. Let w be an object. (Declare)
 1.3. In(EmptySet, EmptySet) and (not In(EmptySet, EmptySet)). (Existential Elimination from 1.1, subproof below)
 begin subproof
  1.3.1. In(w, EmptySet) and (forall z, (In(z, EmptySet) -> z = w)). (Assumption for Existential Elimination)
  1.3.2. In(w, EmptySet). (Conjunction Elimination from 1.3.1)
  1.3.3. not In(w, EmptySet). (Set property)
  1.3.4. In(EmptySet, EmptySet) and (not In(EmptySet, EmptySet)). (Explosion from 1.3.2, 1.3.3)
 end subproof
end subproof
2. EmptySet = EmptySet. (Reflexivity)
3. (not {some}) and (EmptySet = EmptySet). (Conjunction Introduction from 1, 2)
4. {sentence}. (Definition of the only member)
5. {only} or ((not {some}) and (EmptySet = EmptySet)). (Disjunction Introduction from 3)
6. ({only} or ((not {some}) and (EmptySet = EmptySet))) -> OnlyMember(EmptySet) = EmptySet. (Biconditional Elimination from 4)
7. OnlyMember(EmptySet) = EmptySet. (Modus Ponens from 5, 6)
""", SETS)
    assert ok, error


def test_a_set_that_may_have_two_members_has_no_only_member_to_cite():
    """From `In(B, A)` alone, the only-member case is not available: the proof of the
    first case needs the line that says nothing else is in A."""
    only, some, sentence = only_member_line("B", "A")
    reason = refusal(f"""\
1. Let A, B be any set. (Declaration)
2. In(B, A). (Premise)
3. {sentence}. (Definition of the only member)
4. {only} or ((not {some}) and (B = EmptySet)). (Disjunction Introduction from 2)
""", SETS)
    assert reason.startswith("'DisjunctionIntroduction' does not justify")
