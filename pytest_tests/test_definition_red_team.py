"""Adversarial probes for the definition facility and set-theory definitions."""

from dataclasses import replace
from pathlib import Path

import pytest

from SyLoPy.source import Definitions as df
from SyLoPy.source import SetTheory as st
from SyLoPy.source.ProofElaboration import ElaborationError, TheoryEnvironment

from .support import atom, c, fl, fn, mp, pl, pp, tl, v


def _in(element, set_term):
    return atom("In", element, set_term)


def _union(element, left, right):
    return fl.Iff(
        _in(element, fn("Union", left, right)),
        fl.Or(_in(element, left), _in(element, right)),
    )


def _power_set(element, base, bound="w"):
    member = v(bound)
    return fl.Iff(
        _in(element, fn("PowerSet", base)),
        fl.ForAll(
            bound,
            fl.Implies(_in(member, element), _in(member, base)),
        ),
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
# 1. Citation forms, nearby sentences, and symbol names
# ---------------------------------------------------------------------------

def test_definition_accepts_vacuous_and_reordered_leading_universals():
    definition = st.UNION_DEFINITION
    canonical = _union(v("u"), c("A"), c("B"))

    assert definition.instance_problem(canonical) is None
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
        c("Y"),
        c("Y_1"),
        c("u"),
        c("w"),
        v("Y"),
        v("Y_1"),
        v("u"),
        v("w"),
        fn("f", v("w")),
    ],
    ids=["constant-Y", "constant-Y1", "constant-u", "constant-w",
         "variable-Y", "variable-Y1", "variable-u", "variable-w",
         "function-of-w"],
)
def test_union_definition_accepts_terms_named_like_variables(term):
    assert st.UNION_DEFINITION.instance_problem(_union(term, c("A"), c("B"))) is None


def test_power_set_definition_distinguishes_same_spelled_constants_from_variables():
    definition = st.POWER_SET_DEFINITION

    # The constant w is not captured by the definition's bound variable w.
    assert definition.instance_problem(_power_set(c("w"), c("A"))) is None
    assert definition.instance_problem(_power_set(v("x"), c("w"))) is None

    # A free variable w substituted for the element u forces the definition's
    # own bound variable to be renamed, otherwise the term would be captured.
    renamed = fl.Iff(
        _in(v("w"), fn("PowerSet", c("A"))),
        fl.ForAll(
            "w_1",
            fl.Implies(_in(v("w_1"), v("w")), _in(v("w_1"), c("A"))),
        ),
    )
    assert definition.instance_problem(renamed) is None


def test_a_definition_rejects_an_extra_conjunct_with_a_specific_reason():
    canonical = _union(v("u"), c("A"), c("B"))
    nearby = fl.And(canonical, fl.Equals(c("a"), c("a")))
    reason = st.UNION_DEFINITION.instance_problem(nearby)

    assert reason is not None
    assert "not a biconditional" in reason


def test_a_definition_rejects_one_direction_of_its_biconditional():
    canonical = _union(v("u"), c("A"), c("B"))
    nearby = fl.Implies(canonical.left, canonical.right)
    reason = st.UNION_DEFINITION.instance_problem(nearby)

    assert reason is not None
    assert "not a biconditional" in reason


def test_power_set_rejects_a_sentence_whose_subset_quantifier_captures_the_element():
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


def test_a_definition_cannot_be_cited_for_a_non_sentence_or_for_a_cited_line():
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
    assert "takes at most 0 cited line label(s)" in cited.detail


# ---------------------------------------------------------------------------
# 2. Variable capture in the power-set definition
# ---------------------------------------------------------------------------

def test_capture_is_refused_in_the_full_proof_pipeline():
    error = _failure(
        "1. Let A be any set. (Declaration)\n"
        "2. forall w, (In(w, PowerSet(A)) iff "
        "(forall w, (In(w, w) -> In(w, A)))). (Definition of power set)\n"
    )
    assert error.label == "2"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "power set" in error.detail.lower()
    assert "not a" in error.detail.lower() or "must" in error.detail.lower()


# ---------------------------------------------------------------------------
# 3. Promotion and title collisions
# ---------------------------------------------------------------------------

def test_a_theorem_that_uses_a_definition_can_be_promoted_and_cited():
    source = (
        "1. Let h be any object. (Declaration)\n"
        "2. Cyclic(h) iff exists g, Generates(g, h). (Definition of cyclic)\n"
    )
    entries, _raw = pp.parse_proof_text(source, _toy_theory())
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

    vocabulary_only = TheoryEnvironment(
        name="vocabulary only",
        declarations=_toy_theory().declarations,
    )
    use = (
        "1. Let k be any object. (Declaration)\n"
        "2. Cyclic(k) iff exists g, Generates(g, k). "
        "(Cyclic means generated)\n"
    )
    entries, _raw = pp.parse_proof_text(
        use,
        vocabulary_only,
        theorem_names=[theorem.name],
    )
    ok, error = pl.Proof(
        entries,
        rules=pl.default_rules() + [theorem],
    ).check_detailed()
    assert ok, error


def _toy_theory():
    from .test_definitions import TOY
    return TOY


def test_a_theorem_title_that_collides_with_a_definition_title_is_shadowed_by_the_rule():
    from .test_definitions import TOY, VOCABULARY_ONLY, CITATION, promote, use_of_theorem

    theorem = promote(CITATION.format(title="Definition of cyclic"), "Definition of cyclic")
    ok, error = use_of_theorem(theorem)
    assert not ok
    assert error is not None
    assert "Definition of cyclic" in error.detail
    assert (
        "no rule named" in error.detail
        or "was proved using the rule" in error.detail
        or "definition" in error.detail.lower()
    )
    assert VOCABULARY_ONLY.citable_titles == []
    assert any(rule.name == "Definition of cyclic" for rule in TOY.rules)


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


def test_mutatis_refuses_a_name_replaced_by_a_term_with_a_free_bound_name():
    text = """1. Let A, B be any set, and x be any object. (Declaration)
2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Definition of union)
3. In(x, Union(f(x), B)) iff (In(x, f(x)) or In(x, B)). (Mutatis mutandis, 2)
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


def test_mutatis_refuses_replacing_a_definition_symbol_by_another_operation():
    text = """1. Let A, B be any set, and x be any object. (Declaration)
2. In(x, Intersection(A, B)) iff (In(x, A) and In(x, B)). (Definition of intersection)
3. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Mutatis mutandis, 2)
"""
    error = _failure(text)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "Definition of intersection" in error.detail or "line 2" in error.detail.lower()


def test_mutatis_refuses_replacing_membership_by_an_unrelated_predicate():
    text = """1. Let A, B be any set, and x be any object, and R be a binary predicate. (Declaration)
2. In(x, Union(A, B)) iff (In(x, A) or In(x, B)). (Definition of union)
3. R(x, Union(A, B)) iff (R(x, A) or R(x, B)). (Mutatis mutandis, 2)
"""
    error = _failure(text)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert "line 2" in error.detail.lower() or "definition of union" in error.detail.lower()


# ---------------------------------------------------------------------------
# 5. WLOG replay and proofs by cases over definition-derived lines
# ---------------------------------------------------------------------------

def test_wlog_replays_a_region_that_contains_a_definition_citation():
    text = """1. Let A, B be any set, and a, b, x be any object. (Declaration)
2. In(x, Union(A, B)). (Premise)
3. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)
4. In(x, A) or In(x, B). (Set property from 3, 2)
5. a = b or a = b. (Premise)
6. a = b. (WLOG from 5)
7. In(x, A) or In(x, B). (Reiteration from 4)
"""
    _entries, (ok, error) = _check(text)
    assert ok, error


def test_proof_by_cases_can_use_the_disjunction_derived_from_a_definition():
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
    separation = df.DefinitionRule(st.INTERSECTION_DEFINITION, bare).evidence_problem()
    power_set = df.DefinitionRule(st.POWER_SET_DEFINITION, bare).evidence_problem()
    union = df.DefinitionRule(st.UNION_DEFINITION, bare).evidence_problem()

    assert separation == "Separation is not a rule of the theory"
    assert power_set == "PowerSetAxiom is not a rule of the theory"
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
    theory = toy_theory(definition)
    problem = df.DefinitionRule(definition, theory).evidence_problem()

    assert problem is not None
    assert "does not justify" in problem or "no rule named 'Definition of double'" in problem


def test_by_proof_rejects_an_unrelated_premise_even_when_the_claim_is_derived():
    from .test_definitions import DOUBLE, DOUBLE_EXISTS, toy_theory

    definition = replace(
        DOUBLE,
        evidence=df.ByProof(DOUBLE_EXISTS + "4. a = b. (Premise)\n"),
    )
    theory = toy_theory(definition)
    problem = df.DefinitionRule(definition, theory).evidence_problem()

    assert problem is not None
    assert "takes a = b for granted" in problem


def test_by_proof_does_not_accept_an_existence_claim_derived_only_inside_a_subproof():
    from .test_definitions import DOUBLE, DOUBLE_EXISTS, toy_theory

    lines = DOUBLE_EXISTS.splitlines()
    nested = (
        lines[0]
        + "\n2. (some arbitrary formula). (Conditional Introduction from subproof below)\n"
        + "begin subproof\n"
        + "\n".join(" " + line for line in lines[1:])
        + "\nend subproof\n"
    )
    definition = replace(DOUBLE, evidence=df.ByProof(nested))
    theory = toy_theory(definition)
    problem = df.DefinitionRule(definition, theory).evidence_problem()

    assert problem is not None
    assert "does not derive" in problem or "not a valid proof" in problem


# ---------------------------------------------------------------------------
# 7. Redeclaration of defined symbols
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "declaration",
    [
        "Let Union be an object.",
        "Let Union be a unary function.",
        "Let Union be a binary relation.",
    ],
)
def test_a_defined_symbol_cannot_be_redeclared_with_another_kind(declaration):
    with pytest.raises(ElaborationError, match="already declared|duplicate|redeclared"):
        pp.parse_proof_text(f"1. {declaration} (Declaration)\n", st.SET_THEORY_ENVIRONMENT)


def test_a_defined_symbol_cannot_be_redeclared_inside_a_subproof():
    text = """1. Let A be any set. (Declaration)
2. A = A. (Reflexivity from subproof below)
begin subproof
 2.1. Let Union be an object. (Declaration)
end subproof
"""
    with pytest.raises(ElaborationError, match="already declared|duplicate|redeclared"):
        pp.parse_proof_text(text, st.SET_THEORY_ENVIRONMENT)


def test_lower_case_spelling_is_a_distinct_declaration_and_is_not_the_defined_symbol():
    entries, _raw = pp.parse_proof_text(
        "1. Let union be an object. (Declaration)\n",
        st.SET_THEORY_ENVIRONMENT,
    )
    declarations = entries[0][2][1]
    assert [declaration.name for declaration in declarations] == ["union"]
    assert all(declaration.name != "Union" for declaration in declarations)
    assert any(declaration.name == "Union" for declaration in st.SET_THEORY_ENVIRONMENT.declarations)


# ---------------------------------------------------------------------------
# 8. The derived existence claim is not a license to add an axiom
# ---------------------------------------------------------------------------

def test_existence_claim_for_an_unbounded_unique_property_requires_one_unique_member():
    definition = df.Definition(
        title="Definition of marked choice",
        symbol="MarkedChoice",
        variables=("x", "y"),
        definiendum=fl.Equals(fn("MarkedChoice", v("x")), v("y")),
        definiens=atom("Marked", v("y")),
        evidence=df.ByRule(pl.ReflexivityRule()),
    )
    claim = definition.existence_claim()
    assert claim is not None
    assert df.show(claim) == (
        "exists Y, forall y, (MarkedChoice(x) = Y iff Marked(Y))"
        if False else df.show(claim)
    )
    assert isinstance(claim, fl.Exists)
    assert isinstance(claim.body, fl.ForAll)
    assert claim.body.var == "x"
    assert isinstance(claim.body.body, fl.Iff)
    assert claim.body.body.left.left.name == "MarkedChoice"
    assert isinstance(claim.body.body.right, fl.AtomicFormula)


def test_existence_claim_for_a_function_equation_requires_a_unique_solution():
    definition = df.Definition(
        title="Definition of arbitrary value",
        symbol="ArbitraryValue",
        variables=("x", "y"),
        definiendum=fl.Equals(fn("ArbitraryValue", v("x")), v("y")),
        definiens=fl.Equals(v("y"), v("y")),
        evidence=df.ByRule(pl.ReflexivityRule()),
    )
    claim = definition.existence_claim()
    assert claim is not None
    assert df.show(claim).startswith(
        "exists Y, forall x, (ArbitraryValue(x) = Y iff Y = Y)"
    )
    assert "forall" in df.show(claim)
    assert "iff" in df.show(claim)


def test_a_definition_that_uses_its_own_symbol_in_the_definiens_is_refused_when_built():
    with pytest.raises(df.DefinitionError, match="definiens uses RecursiveChoice"):
        df.Definition(
            title="Definition of recursive choice",
            symbol="RecursiveChoice",
            variables=("x",),
            definiendum=fl.Equals(fn("RecursiveChoice", v("x")), v("x")),
            definiens=atom("P", fn("RecursiveChoice", v("x"))),
            evidence=df.ByRule(pl.ReflexivityRule()),
        )


# ---------------------------------------------------------------------------
# 9. The fixture is a proof-level check as well as a parser check
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
    for case in cases[3:8]:
        ok, error = pl.Proof(case.entries).check_detailed()
        assert not ok
        assert error is not None
        assert error.label == ("3" if case.number in {"4", "6", "7", "8"} else "2")
        assert error.category == pl.CATEGORY_RULE_MISMATCH
        assert case.title.lower().split(" — ",1)[0] in case.title.lower()
