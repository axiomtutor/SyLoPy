"""Adversarial probes for the definition facility and the set-theory definitions."""

from dataclasses import replace
from pathlib import Path

import pytest

from SyLoPy.source import Definitions as df
from SyLoPy.source import SetTheory as st
from SyLoPy.source.ProofElaboration import ElaborationError, TheoryEnvironment

from .support import atom, c, fl, fn, mp, pl, pp, v


def _in(element, set_term):
    return atom("In", element, set_term)


def _union(element, left, right):
    return fl.Iff(
        _in(element, fn("Union", left, right)),
        fl.Or(_in(element, left), _in(element, right)),
    )


def _power_set(element, base):
    member = v("w")
    return fl.Iff(
        _in(element, fn("PowerSet", base)),
        fl.ForAll("w", fl.Implies(_in(member, element), _in(member, base))),
    )


def _check(text, environment=st.SET_THEORY_ENVIRONMENT):
    entries, _raw = pp.parse_proof_text(text, environment)
    return entries, pl.Proof(entries).check_detailed()


def _failure(text, environment=st.SET_THEORY_ENVIRONMENT):
    _entries, (ok, error) = _check(text, environment)
    assert not ok, "the proof was accepted"
    assert error is not None
    return error


def _fixture():
    return (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "testSetTheory"
        / "definition_red_team.txt"
    ).read_text()


# ---------------------------------------------------------------------------
# 1. Citation forms, nearby sentences, and bound-variable names
# ---------------------------------------------------------------------------

def test_definition_accepts_vacuous_and_reordered_leading_universals():
    definition = st.UNION_DEFINITION
    canonical = _union(v("u"), c("A"), c("B"))

    assert definition.instance_problem(canonical) is None
    assert definition.instance_problem(
        _union(v("u"), c("B"), c("A"))
    ) is None
    assert definition.instance_problem(fl.Iff(canonical.right, canonical.left)) is None
    assert definition.instance_problem(fl.ForAll("z", canonical)) is None

    closed = fl.ForAll(
        "B",
        fl.ForAll(
            "u",
            fl.ForAll("A", _union(v("u"), v("A"), v("B"))),
        ),
    )
    assert definition.instance_problem(closed) is None


@pytest.mark.parametrize(
    "term",
    [
        c("Y"), c("Y_1"), c("u"), c("w"),
        v("Y"), v("Y_1"), v("u"), v("w"),
        fn("f", c("Y")),
        fn("f", c("Y_1")),
        fn("f", c("u")),
        fn("f", c("w")),
        fn("f", v("w")),
    ],
    ids=[
        "constant-Y", "constant-Y1", "constant-u", "constant-w",
        "variable-Y", "variable-Y1", "variable-u", "variable-w",
        "function-of-constant-Y", "function-of-constant-Y1",
        "function-of-constant-u", "function-of-constant-w",
        "function-of-variable-w",
    ],
)
def test_union_definition_accepts_terms_named_like_variables(term):
    assert st.UNION_DEFINITION.instance_problem(_union(term, c("A"), c("B"))) is None


def test_power_set_definition_distinguishes_constants_from_variables_named_w():
    definition = st.POWER_SET_DEFINITION

    # A constant spelled w is not the variable bound inside the subset clause.
    assert definition.instance_problem(_power_set(c("w"), c("A"))) is None
    assert definition.instance_problem(_power_set(v("x"), c("w"))) is None

    # A variable w used as the element is free in the instance. The definition's
    # own subset-clause binder must be renamed to w_1 instead of capturing it.
    renamed = fl.Iff(
        _in(v("w"), fn("PowerSet", c("A"))),
        fl.ForAll(
            "w_1",
            fl.Implies(_in(v("w_1"), v("w")), _in(v("w_1"), c("A"))),
        ),
    )
    assert definition.instance_problem(renamed) is None

    # The same capture avoidance is needed when a set argument contains w.
    set_term = fn("f", v("w"))
    renamed_argument = fl.Iff(
        _in(v("x"), fn("PowerSet", set_term)),
        fl.ForAll(
            "w_1",
            fl.Implies(_in(v("w_1"), v("x")), _in(v("w_1"), set_term)),
        ),
    )
    assert definition.instance_problem(renamed_argument) is None


def test_a_definition_rejects_an_extra_conjunct_and_a_one_way_conditional():
    canonical = _union(v("u"), c("A"), c("B"))
    extra = fl.And(canonical, fl.Equals(c("a"), c("a")))
    one_way = fl.Implies(canonical.left, canonical.right)

    extra_reason = st.UNION_DEFINITION.instance_problem(extra)
    one_way_reason = st.UNION_DEFINITION.instance_problem(one_way)

    assert extra_reason is not None and "not a biconditional" in extra_reason
    assert one_way_reason is not None and "not a biconditional" in one_way_reason


def test_a_definition_cannot_be_cited_for_an_atom_or_for_a_cited_line():
    atomic = _failure(
        "1. Let A be any set, and x be any object. (Declaration)\n"
        "2. In(x, Union(A, A)). (Definition of union)\n"
    )
    assert atomic.label == "2"
    assert atomic.category == pl.CATEGORY_RULE_MISMATCH
    assert "not a biconditional" in atomic.detail

    cited = _failure(
        "1. Let A, B be any set. (Declaration)\n"
        "2. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). "
        "(Definition of union)\n"
        "3. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). "
        "(Definition of union from 2)\n"
    )
    assert cited.label == "3"
    assert cited.category == pl.CATEGORY_BAD_REFERENCE
    assert "takes no cited" in cited.detail


# ---------------------------------------------------------------------------
# 2. Variable capture in the power-set definition
# ---------------------------------------------------------------------------

def test_power_set_rejects_a_subset_quantifier_that_captures_the_element():
    captured = fl.ForAll(
        "w",
        fl.Iff(
            _in(v("w"), fn("PowerSet", c("A"))),
            fl.ForAll(
                "w",
                fl.Implies(_in(v("w"), v("w")), _in(v("w"), c("A"))),
            ),
        ),
    )
    reason = st.POWER_SET_DEFINITION.instance_problem(captured)

    assert reason is not None
    assert "other side must" in reason or "neither side" in reason


# ---------------------------------------------------------------------------
# 3. Promotion and definition/theorem title collisions
# ---------------------------------------------------------------------------

def test_a_theorem_using_a_definition_can_be_promoted_and_cited_later():
    from .test_definitions import TOY

    source = (
        "1. Let h be any object. (Declaration)\n"
        "2. Cyclic(h) iff exists g, Generates(g, h). (Definition of cyclic)\n"
    )
    entries, _raw = pp.parse_proof_text(source, TOY)
    proof = pl.Proof(entries)
    ok, error = proof.check_detailed()
    assert ok, error

    theorem = pl.promote_theorem(
        "Cyclic means generated",
        proof,
        generalized_names=["h"],
    )
    assert [rule.name for rule in theorem.required_rules] == ["Definition of cyclic"]
    assert theorem.premises == []

    vocabulary = TheoryEnvironment(name="vocabulary only", declarations=TOY.declarations)
    use = (
        "1. Let k be any object. (Declaration)\n"
        "2. Cyclic(k) iff exists g, Generates(g, k). "
        "(Cyclic means generated)\n"
    )
    entries, _raw = pp.parse_proof_text(use, vocabulary, theorem_names=[theorem.name])
    ok, error = pl.Proof(entries, rules=pl.default_rules() + [theorem]).check_detailed()
    assert ok, error


def test_a_theorem_titled_like_a_definition_is_shadowed_when_cited():
    source = (
        "1. Let A be any set. (Declaration)\\n"
        "2. A = A. (Reflexivity)\\n"
    )
    entries, _raw = pp.parse_proof_text(source, st.SET_THEORY_ENVIRONMENT)
    theorem_proof = pl.Proof(entries)
    theorem_ok, theorem_error = theorem_proof.check_detailed()
    assert theorem_ok, theorem_error
    theorem = pl.promote_theorem(
        "Definition of union",
        theorem_proof,
        generalized_names=["A"],
    )

    use = (
        "1. Let A be any set. (Declaration)\\n"
        "2. A = A. (Definition of union)\\n"
    )
    entries, _raw = pp.parse_proof_text(
        use,
        st.SET_THEORY_ENVIRONMENT,
        theorem_names=[theorem.name],
    )
    # The citation is resolved to the definition rule, not the theorem.
    assert entries[1][2][0] == "rule"
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules + [theorem],
    )
    ok, error = proof.check_detailed()

    assert not ok
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "Definition of union" in error.detail


# ---------------------------------------------------------------------------
# 4. Mutatis mutandis over a line citing a definition
# ---------------------------------------------------------------------------

def test_mutatis_accepts_two_definition_parameters_exchanged_together():
    text = """1. Let A, B be any set, and x be any object. (Declaration)
2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Definition of union)
3. In(x, Union(B, A)) iff (In(x, B) or In(x, A)). (Mutatis mutandis, 2)
"""
    _entries, (ok, error) = _check(text)
    assert ok, error


def test_mutatis_accepts_a_name_replaced_by_a_closed_function_term():
    text = """1. Let A, B be any set, and x, a be any object, and f be a unary function. (Declaration)
2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Definition of union)
3. In(x, Union(f(a), B)) iff (In(x, f(a)) or In(x, B)). (Mutatis mutandis, 2)
"""
    _entries, (ok, error) = _check(text)
    assert ok, error


def test_mutatis_refuses_a_name_replaced_by_a_term_containing_a_bound_name():
    text = """1. Let A, B be any set. (Declaration)
2. forall z, (In(z, Union(A, B)) iff (In(z, A) or In(z, B))). (Definition of union)
3. forall z, (In(z, Union(f(z), B)) iff (In(z, f(z)) or In(z, B))). (Mutatis mutandis, 2)
"""
    error = _failure(text)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "variable" in error.detail.lower() or "term" in error.detail.lower()


def test_mutatis_replays_a_range_containing_a_definition_citation():
    text = """1. Let A, B be any set, and x be any object. (Declaration)
2. x is in A union B. (Premise)
3. x is in B union A. (Premise)
4. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)
5. In(x, A) or In(x, B). (Set property from 4, 2)
6. In(x, B) or In(x, A). (Mutatis mutandis, 4 to 5)
"""
    _entries, (ok, error) = _check(text)
    assert ok, error


def test_mutatis_refuses_replacing_intersection_by_union_in_a_definition_citation():
    text = """1. Let A, B be any set, and x be any object. (Declaration)
2. In(x, Intersection(A, B)) iff (In(x, A) and In(x, B)). (Definition of intersection)
3. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Mutatis mutandis, 2)
"""
    error = _failure(text)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "line 2" in error.detail.lower() or "definition of intersection" in error.detail.lower()


def test_mutatis_refuses_replacing_membership_by_an_unrelated_predicate():
    text = """1. Let A, B be any set, and x be any object, and R be a binary predicate. (Declaration)
2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Definition of union)
3. R(x, Union(A, B)) iff (R(x, A) or R(x, B)). (Mutatis mutandis, 2)
"""
    error = _failure(text)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "line 2" in error.detail.lower() or "definition of union" in error.detail.lower()

def test_mutatis_refuses_replacing_union_by_a_declared_binary_function():
    text = """1. Let A, B be any set, and x be any object, and f be a binary function. (Declaration)
2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Definition of union)
3. In(x, f(A, B)) iff (In(x, A) or In(x, B)). (Mutatis mutandis, 2)
"""
    error = _failure(text)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "definition of union" in error.detail.lower()




# ---------------------------------------------------------------------------
# 5. WLOG replay and proof by cases over definition-derived lines
# ---------------------------------------------------------------------------

def test_wlog_replays_a_region_that_contains_a_definition_citation():
    text = """1. Let A, B be any set, and a, x, y be any object, and Q be a closed formula. (Declaration)
2. x is in A union B. (Premise)
3. y is in A union B. (Premise)
4. In(x, A) -> Q. (Premise)
5. In(x, B) -> Q. (Premise)
6. In(y, A) -> Q. (Premise)
7. In(y, B) -> Q. (Premise)
8. a = x or a = y. (Premise)
9. a = x. (WLOG from 8)
10. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)
11. In(x, A) or In(x, B). (Set property from 10, 2)
12. Q. (Proof by Cases from 11, subproofs below)
begin subproof
 12.1.case1. In(x, A). (Case)
 12.2.case1. Q. (Modus Ponens from 4, 12.1.case1)
end subproof
begin subproof
 12.1.case2. In(x, B). (Case)
 12.2.case2. Q. (Modus Ponens from 5, 12.1.case2)
end subproof
"""
    _entries, (ok, error) = _check(text)
    assert ok, error


def test_proof_by_cases_can_use_a_disjunction_derived_from_a_definition():
    text = """1. Let A, B be any set, and x be any object, and P be a unary predicate. (Declaration)
2. In(x, Union(A, B)). (Premise)
3. In(x, A) -> P(x). (Premise)
4. In(x, B) -> P(x). (Premise)
5. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)
6. In(x, A) or In(x, B). (Set property from 5, 2)
7. P(x). (Proof by Cases from 6, subproofs below)
begin subproof
 7.1.case1. In(x, A). (Case)
 7.2.case1. P(x). (Modus Ponens from 3, 7.1.case1)
end subproof
begin subproof
 7.1.case2. In(x, B). (Case)
 7.2.case2. P(x). (Modus Ponens from 4, 7.1.case2)
end subproof
"""
    _entries, (ok, error) = _check(text)
    assert ok, error


# ---------------------------------------------------------------------------
# 6. Evidence for existence claims
# ---------------------------------------------------------------------------

def test_by_rule_evidence_fails_when_the_theory_lacks_the_required_axiom():
    bare = TheoryEnvironment(
        name="bare set theory",
        declarations=st.SET_THEORY_ENVIRONMENT.declarations,
    )
    assert df.DefinitionRule(st.INTERSECTION_DEFINITION, bare).evidence_problem() == \
        "Separation is not a rule of the theory"
    assert df.DefinitionRule(st.POWER_SET_DEFINITION, bare).evidence_problem() == \
        "PowerSetAxiom is not a rule of the theory"
    union = df.DefinitionRule(st.UNION_DEFINITION, bare).evidence_problem()
    assert union.startswith("the proof of existence is not a valid proof:")
    assert "no rule named 'PairingAxiom' is registered" in union


def test_by_proof_evidence_cannot_cite_the_definition_it_is_evidence_for():
    from .test_definitions import DOUBLE, DOUBLE_EXISTS, toy_theory

    definition = replace(
        DOUBLE,
        evidence=df.ByProof(
            DOUBLE_EXISTS
            + "4. Double(n) = m iff m = Plus(n, n). (Definition of double)\n"
        ),
    )
    problem = df.DefinitionRule(definition, toy_theory(definition)).evidence_problem()

    assert problem is not None
    assert "Definition of double" in problem
    assert "does not parse" in problem or "not a valid proof" in problem


def test_by_proof_rejects_an_unrelated_premise_even_when_the_claim_is_derived():
    from .test_definitions import DOUBLE, DOUBLE_EXISTS, toy_theory

    evidence = (
        DOUBLE_EXISTS
        + "4. Let a, b be any objects. (Declaration)\n"
        + "5. a = b. (Premise)\n"
    )
    definition = replace(DOUBLE, evidence=df.ByProof(evidence))
    problem = df.DefinitionRule(definition, toy_theory(definition)).evidence_problem()

    assert problem is not None
    assert "takes" in problem and "for granted" in problem
    assert "a" in problem and "b" in problem


def test_a_declaration_that_adds_membership_is_an_evidence_hypothesis():
    from .test_definitions import DOUBLE, DOUBLE_EXISTS, toy_theory

    evidence = DOUBLE_EXISTS.replace(
        "1. Let n be any object. (Declaration)",
        "1. Let A be any set, n be in A. (Declaration)",
    )
    definition = replace(DOUBLE, evidence=df.ByProof(evidence))
    problem = df.DefinitionRule(definition, toy_theory(definition)).evidence_problem()

    assert problem is not None
    assert "takes" in problem and "for granted" in problem
    assert "A" in problem and "n" in problem


def test_a_witness_line_does_not_erase_the_existential_premise_used_to_name_it():
    from .test_definitions import DOUBLE, DOUBLE_EXISTS, toy_theory

    evidence = (
        DOUBLE_EXISTS
        + "4. exists q, q = Plus(n, n). (Premise)\n"
        + "5. Let r be such an object. (Existence from 4)\n"
    )
    definition = replace(DOUBLE, evidence=df.ByProof(evidence))
    problem = df.DefinitionRule(definition, toy_theory(definition)).evidence_problem()

    assert problem is not None
    assert "takes" in problem and "for granted" in problem
    assert "exists" in problem.lower()


def test_an_existence_claim_derived_only_inside_a_subproof_is_not_top_level_evidence():
    from .test_definitions import DOUBLE, double_claim, toy_theory

    statement = df.show(DOUBLE.existence_statement())
    evidence = (
        "1. Let n be any object. (Declaration)\n"
        f"2. n = n -> ({statement}). (Conditional Introduction from subproof below)\n"
        "begin subproof\n"
        " 2.1. n = n. (Assumption for Conditional Introduction)\n"
        + double_claim("2.2", "2.3", indent=" ")
        + "end subproof\n"
    )
    definition = replace(DOUBLE, evidence=df.ByProof(evidence))
    problem = df.DefinitionRule(definition, toy_theory(definition)).evidence_problem()

    assert problem is not None
    assert "does not derive" in problem
    assert "at its top level" in problem


# ---------------------------------------------------------------------------
# 7. Redeclaration of defined symbols
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "declaration",
    [
        "Let Union be an object.",
        "Let Union be a constant.",
        "Let Union be a unary function.",
        "Let Union be a binary relation.",
    ],
)
def test_a_defined_symbol_cannot_be_redeclared_with_another_kind(declaration):
    with pytest.raises(ElaborationError, match="already declared|duplicate|redeclared"):
        pp.parse_proof_text(
            f"1. {declaration} (Declaration)\n",
            st.SET_THEORY_ENVIRONMENT,
        )


def test_a_defined_symbol_cannot_be_redeclared_inside_a_subproof():
    text = """1. A -> A. (Conditional Introduction from subproof below)
begin subproof
 1.1. A. (Assumption for Conditional Introduction)
 1.2. Let Union be an object. (Declaration)
end subproof
"""
    with pytest.raises(ElaborationError, match="already declared|duplicate|redeclared"):
        pp.parse_proof_text(text, st.SET_THEORY_ENVIRONMENT)


def test_lower_case_spelling_is_a_distinct_declaration_and_not_the_defined_symbol():
    entries, _raw = pp.parse_proof_text(
        "1. Let union be an object. (Declaration)\n",
        st.SET_THEORY_ENVIRONMENT,
    )
    declarations = entries[0][2][1]
    assert [declaration.name for declaration in declarations] == ["union"]
    assert all(declaration.name != "Union" for declaration in declarations)
    assert any(
        declaration.name == "Union"
        for declaration in st.SET_THEORY_ENVIRONMENT.declarations
    )


# ---------------------------------------------------------------------------
# 8. Derived existence claims are not axioms
# ---------------------------------------------------------------------------

def test_existence_claim_for_an_unbounded_property_exposes_the_full_unique_set_claim():
    definition = df.Definition(
        title="Definition of self-membered choice",
        symbol="SelfMemberedChoice",
        variables=("x", "y"),
        definiendum=fl.Equals(fn("SelfMemberedChoice", v("x")), v("y")),
        definiens=_in(v("y"), v("y")),
        evidence=df.ByRule(st.PowerSetAxiomRule()),
    )
    claim = definition.existence_claim()

    assert claim is not None
    assert df.show(claim) == "exists Y, forall y, (Y = y iff In(y, y))"
    assert definition.parameters == ("x",)
    assert definition.evidence.problem(definition, st.SET_THEORY_ENVIRONMENT) is not None


def test_existence_claim_for_a_non_unique_function_equation_requires_one_unique_value():
    definition = df.Definition(
        title="Definition of arbitrary value",
        symbol="ArbitraryValue",
        variables=("x", "y"),
        definiendum=fl.Equals(fn("ArbitraryValue", v("x")), v("y")),
        definiens=fl.Equals(v("y"), v("y")),
        evidence=df.ByRule(st.PowerSetAxiomRule()),
    )
    claim = definition.existence_claim()

    assert claim is not None
    assert df.show(claim) == "exists Y, forall y, (Y = y iff y = y)"
    problem = definition.evidence.problem(definition, st.SET_THEORY_ENVIRONMENT)
    assert problem is not None
    assert "does not accept" in problem


def test_a_definition_that_uses_its_own_symbol_in_the_definiens_is_refused_when_built():
    with pytest.raises(df.DefinitionError, match="definiens uses RecursiveChoice"):
        df.Definition(
            title="Definition of recursive choice",
            symbol="RecursiveChoice",
            variables=("x",),
            definiendum=fl.Equals(fn("RecursiveChoice", v("x")), v("x")),
            definiens=atom("P", fn("RecursiveChoice", v("x"))),
            evidence=df.ByProof(""),
        )


# ---------------------------------------------------------------------------
# 9. The enforced fixture pins proof-level behavior and exact reasons
# ---------------------------------------------------------------------------

def test_definition_red_team_fixture_has_grounded_conclusions_and_expected_results():
    source = _fixture()
    cases = mp.parse_multi_proof_file(source)

    assert len(cases) == 10
    assert all(case.stated_conclusion is not None for case in cases)
    assert all(case.parse_error is None for case in cases)

    results = mp.run_multi_proof_file(source)
    assert [(result[0], result[1], result[2]) for result in results] == [
        ("1", True, True),
        ("2", True, True),
        ("3", True, True),
        ("4", False, False),
        ("5", False, False),
        ("6", False, False),
        ("7", False, False),
        ("8", False, False),
        ("9", True, True),
        ("10", True, True),
    ]
    expected = {
        "4": ("2", pl.CATEGORY_RULE_MISMATCH, "not a biconditional"),
        "5": ("2", pl.CATEGORY_RULE_MISMATCH, "power set"),
        "6": ("3", pl.CATEGORY_BAD_REFERENCE, "cited"),
        "7": ("2", pl.CATEGORY_RULE_MISMATCH, "not a biconditional"),
        "8": ("2", pl.CATEGORY_RULE_MISMATCH, "not a biconditional"),
    }
    for case in cases:
        if case.number not in expected:
            continue
        label, category, phrase = expected[case.number]
        ok, error = pl.Proof(case.entries).check_detailed()
        assert not ok
        assert error is not None
        assert error.label == label
        assert error.category == category
        assert phrase in error.detail.lower()
