"""A theorem about the relation of a declaration, cited for another relation.

Two things made such a citation unsound, and a third made it unusable:

* the theorem's premises were left about the theorem's own relation symbol
  `R`, so facts about `R` stood in for facts about the relation `S` that the
  conclusion spoke of, and a plain `S` was proved to have what `R` was assumed
  to have;
* a carrier that the citation instantiated by a compound term (`A union B`)
  was compared with the declared carrier as if it had not been instantiated,
  so a relation reflexive on `X` was accepted as reflexive on `A union B`;
* with the premises unrenamed, no citation for a relation of another name
  could be accepted at all.

`tests/testDiscreteMath/promoted_relation_theorems.txt` holds the proofs; each
invalid one has a valid twin there that differs by the one thing it lacks.
These tests pin the outcome of every proof and the guard that refuses it.
"""

from pathlib import Path

import pytest

from .support import atom, c, fl, mp, pl, pp


PROJECT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT / "tests" / "testDiscreteMath" / "promoted_relation_theorems.txt"

# What a theorem says when the relation it is cited for lacks the carrier or a
# property that the theorem's proof read from the declaration of its own.
DECLARATION_REQUIREMENT = "requires a matching declared relation carrier and properties at the citation"


def _results():
    text = FIXTURE.read_text(encoding="utf-8")
    return {
        str(number): (expected_valid, ok, message, crashed)
        for number, expected_valid, ok, message, crashed in mp.run_multi_proof_file(text)
    }


RESULTS = _results()

THEOREMS = ("1", "2", "3")
CITATIONS = ("4", "5", "6", "7")
REFUSED_BY_THE_PREMISES = {"8": 5}
REFUSED_BY_THE_DECLARATION = {"9": 2, "10": 4, "11": 4}


def test_the_fixture_has_exactly_these_proofs():
    assert sorted(RESULTS, key=int) == [
        str(number) for number in range(1, 12)
    ], "a proof was added or removed: classify it in this module"
    assert set(THEOREMS + CITATIONS) | set(REFUSED_BY_THE_PREMISES) | set(REFUSED_BY_THE_DECLARATION) \
        == set(RESULTS)


@pytest.mark.parametrize("number", THEOREMS + CITATIONS)
def test_valid_proofs_are_accepted(number):
    expected_valid, ok, message, crashed = RESULTS[number]
    assert expected_valid and ok and not crashed, message


@pytest.mark.parametrize("number,line", sorted(REFUSED_BY_THE_PREMISES.items()))
def test_premises_about_the_theorems_own_relation_are_refused_at_the_citation(number, line):
    expected_valid, ok, message, crashed = RESULTS[number]
    assert not expected_valid and not ok and not crashed
    assert message.startswith(f"Line {line}: 'Symmetry from a premise' does not justify"), message
    # Not the declaration check: the premises are what is wrong, and the twin
    # (proof 7) has the same declarations and is accepted.
    assert DECLARATION_REQUIREMENT not in message


@pytest.mark.parametrize("number,line", sorted(REFUSED_BY_THE_DECLARATION.items()))
def test_a_relation_without_the_carrier_or_properties_is_refused_by_the_declaration_check(number, line):
    expected_valid, ok, message, crashed = RESULTS[number]
    assert not expected_valid and not ok and not crashed
    assert message.startswith(f"Line {line}: "), message
    assert DECLARATION_REQUIREMENT in message


# --- the matcher and the premises of an instance ----------------------------

THEOREM_FROM_A_PREMISE = """
1. Let X be any set, R be a relation on X. (Declaration)
2. forall a, forall b, (R(a,b) -> R(b,a)). (Premise)
3. Let u, v be in X. (Declaration)
4. forall b, (R(u,b) -> R(b,u)). (Universal Instantiation from 2)
5. R(u,v) -> R(v,u). (Universal Instantiation from 4)
"""


def _theorem():
    entries, _ = pp.parse_proof_text(THEOREM_FROM_A_PREMISE)
    proof = pl.Proof(entries)
    assert proof.check()[0]
    return pl.promote_theorem("Symmetry from a premise", proof)


def test_the_theorem_generalizes_its_relation_symbol_and_states_its_premises_about_it():
    theorem = _theorem()
    assert "R" in theorem.generalized_names
    assert [repr(premise) for premise in theorem.premises] == [
        "(∀x. (∀y. (R(x, y) → (In(x, X) ∧ In(y, X)))))",
        "(∀a. (∀b. (R(a, b) → R(b, a))))",
        "In(u, X)",
        "In(v, X)",
    ]


def test_the_premises_of_an_instance_are_about_the_relation_it_is_cited_for():
    theorem = _theorem()
    conclusion = fl.Implies(atom("S", c("u"), c("v")), atom("S", c("v"), c("u")))
    instance = theorem._match_instance(conclusion, [])
    assert instance is not None
    substitution, expected = instance
    assert substitution.predicates == {"R": "S"}
    assert [repr(premise) for premise in expected] == [
        "(∀x. (∀y. (S(x, y) → (In(x, X) ∧ In(y, X)))))",
        "(∀a. (∀b. (S(a, b) → S(b, a))))",
        "In(u, X)",
        "In(v, X)",
    ]


def test_the_matcher_keeps_relation_symbols_apart_from_terms():
    matcher = pl.ConstantGeneralizingMatcher({"R", "a"})
    assert matcher.match_formula(atom("R", c("a"), c("a")), atom("S", c("b"), c("b")))
    assert matcher.predicates == {"R": "S"}
    assert set(matcher.mapping) == {"a"}
    substitution = matcher.substitution()
    assert substitution.predicates == {"R": "S"}
    assert substitution["a"].name == "b"


def test_a_relation_symbol_is_instantiated_the_same_way_everywhere():
    matcher = pl.ConstantGeneralizingMatcher({"R"})
    pattern = fl.And(atom("R", c("a"), c("b")), atom("R", c("b"), c("a")))
    assert not matcher.match_formula(
        pattern, fl.And(atom("S", c("a"), c("b")), atom("T", c("b"), c("a"))))
