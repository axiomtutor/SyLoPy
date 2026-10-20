"""Red-team the core quantifier rules and lexical proof scopes without editing the kernel."""

from pathlib import Path

import pytest

import SyLoPy.source.validate_all_proofs as mp
from .support import atom, c, fl, pl, v

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "testProofs"

# (fixture filename, case number): (refusing line, canonical rule name, message fragment)
# Scope-only references are pinned separately because they are intentionally
# refused at the visibility boundary, not by an inference-rule matcher.
REFUSALS = {
    ("red_team_UniversalGeneralization.txt", "2"): ("2", "UniversalGeneralization", "does not justify"),
    ("red_team_UniversalGeneralization.txt", "3"): ("2", "UniversalGeneralization", "does not justify"),
    ("red_team_UniversalGeneralization.txt", "4"): ("2", "UniversalGeneralization", "does not justify"),
    ("red_team_UniversalGeneralization.txt", "5"): ("2", "UniversalGeneralization", "occurs in a hypothesis in force"),
            ("red_team_UniversalGeneralization.txt", "6"): ("3", "UniversalGeneralization", "occurs in a hypothesis in force"),
    ("red_team_ExistentialElimination.txt", "2"): ("4", "ExistentialElimination", "does not justify"),
    ("red_team_ExistentialElimination.txt", "3"): ("4", "ExistentialElimination", "does not justify"),
    ("red_team_ExistentialElimination.txt", "4"): ("4", "ExistentialElimination", "does not justify"),
    ("red_team_ExistentialElimination.txt", "5"): ("3", "ExistentialElimination", "occurs in the existential formula"),
    ("red_team_ExistentialIntroduction.txt", "2"): ("2", "ExistentialIntroduction", "does not justify"),
    ("red_team_ExistentialIntroduction.txt", "3"): ("2", "ExistentialIntroduction", "does not justify"),
    ("red_team_UniversalInstantiation.txt", "2"): ("2", "UniversalInstantiation", "does not justify"),
    ("red_team_UniversalInstantiation.txt", "3"): ("2", "UniversalInstantiation", "does not justify"),
    ("red_team_UniversalInstantiation.txt", "4"): ("2", "UniversalInstantiation", "does not justify"),
    ("red_team_ConditionalIntroduction.txt", "2"): ("2", "ConditionalIntroduction", "does not justify"),
    ("red_team_ConditionalIntroduction.txt", "3"): ("2", "ConditionalIntroduction", "does not justify"),
    ("red_team_ConditionalIntroduction.txt", "4"): ("2", "ConditionalIntroduction", "does not justify"),
    ("red_team_ProofByContradiction.txt", "2"): ("2", "ProofByContradiction", "does not justify"),
    ("red_team_ProofByContradiction.txt", "3"): ("2", "ProofByContradiction", "does not justify"),
    ("red_team_DisjunctionElimination.txt", "2"): ("2", "DisjunctionElimination", "does not justify"),
        ("red_team_DisjunctionElimination.txt", "4"): ("2", "DisjunctionElimination", "does not justify"),
    ("red_team_LeibnizSubstitution.txt", "2"): ("5", "Substitution", "does not justify"),
    ("red_team_LeibnizSubstitution.txt", "3"): ("5", "Substitution", "does not justify"),
    ("red_team_LeibnizSubstitution.txt", "4"): ("5", "Substitution", "does not justify"),
    ("red_team_Reiteration.txt", "2"): ("3", "Reiteration", "does not justify"),
}


def _case(filename, number):
    text = (FIXTURE_DIR / filename).read_text(encoding="utf-8")
    cases = mp.parse_multi_proof_file(text)
    matches = [case for case in cases if case.number == number]
    assert len(matches) == 1, (filename, number, [case.number for case in cases])
    return text, matches[0]


def _checked(case):
    assert case.parse_error is None, case.parse_error
    proof = pl.Proof(
        case.entries,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    return proof.check_detailed()


@pytest.mark.parametrize("filename", sorted({
    filename for filename, _number in REFUSALS
} | {"red_team_Scope.txt"}))
def test_every_red_team_fixture_has_a_valid_control_and_expected_outcomes(filename):
    text = (FIXTURE_DIR / filename).read_text(encoding="utf-8")
    cases = mp.parse_multi_proof_file(text)
    assert cases, f"{filename}: no proof cases parsed"
    assert any(case.expected_valid for case in cases), f"{filename}: missing accepted boundary control"
    results = mp.run_multi_proof_file(
        text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert [case.number for case in cases] == [row[0] for row in results]
    for (number, expected, ok, message, crashed), case in zip(results, cases):
        assert not crashed, f"{filename} case {number} raised in a core rule: {message}"
        assert expected == ok, f"{filename} case {number}: {message}"
        assert case.title, f"{filename} case {number}: missing case title"


@pytest.mark.parametrize(
    "filename,number",
    sorted(REFUSALS),
    ids=[f"{filename}-case-{number}" for filename, number in sorted(REFUSALS)],
)
def test_invalid_core_rule_cases_fail_at_the_intended_line_and_rule(filename, number):
    line, rule, detail_fragment = REFUSALS[(filename, number)]
    _text, case = _case(filename, number)
    ok, error = _checked(case)
    assert not ok, f"{filename} case {number} was accepted"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == line, error
    assert error.category == pl.CATEGORY_RULE_MISMATCH, error
    assert f"'{rule}' does not justify" in error.detail, error
    assert detail_fragment in error.detail, error


def test_missing_disjunction_case_is_refused_before_kernel_validation():
    _text, case = _case("red_team_DisjunctionElimination.txt", "3")
    assert case.parse_error is not None, "the parser accepted a missing case block"
    assert "requires 2 subproof(s) below" in case.parse_error, case.parse_error


def test_forward_reference_is_refused_before_the_target_label_exists():
    _text, case = _case("red_team_Scope.txt", "3")
    assert case.parse_error is None, case.parse_error
    ok, error = _checked(case)
    assert not ok, "an earlier line cited a later label"
    assert isinstance(error, pl.ValidationError), error
    assert error.label == "2", error
    assert error.category == pl.CATEGORY_BAD_REFERENCE, error
    assert "3" in error.detail, error


def test_closed_subproof_reference_is_refused_at_the_visibility_boundary():
    _text, case = _case("red_team_Scope.txt", "2")
    if case.parse_error:
        diagnostic = case.parse_error.casefold()
        assert any(fragment in diagnostic for fragment in (
            "not in scope", "not found", "not defined", "already used", "enclosing scope"
        )), case.parse_error
        return
    ok, error = _checked(case)
    assert not ok, "a label from a closed subproof was accepted outside its scope"
    assert isinstance(error, pl.ValidationError), error
    assert error.category == pl.CATEGORY_BAD_REFERENCE, error
    assert "2.1" in error.detail, error


def test_label_scope_keeps_parent_visibility_but_blocks_shadowing_and_leakage():
    parent = pl.LabelScope()
    outer = object()
    inner = object()
    parent["1"] = outer
    child = parent.child()

    assert child["1"] is outer
    child["1.1"] = inner
    assert "1.1" not in parent
    assert child["1.1"] is inner
    with pytest.raises(KeyError):
        child["1"] = object()
    with pytest.raises(KeyError):
        parent["1"] = object()


def test_declaration_scope_keeps_parent_visibility_but_blocks_shadowing_and_leakage():
    parent = pl.DeclarationScope()
    outer = pl.Declaration("X", pl.DeclarationKind.OBJECT)
    relation = pl.Declaration("R", pl.DeclarationKind.PREDICATE, arity=2)
    parent.declare(outer)
    child = parent.child()

    assert child.lookup("X") == outer
    child.declare(relation)
    assert parent.lookup("R") is None
    assert child.lookup("R") == relation
    with pytest.raises(KeyError):
        child.declare(pl.Declaration("X", pl.DeclarationKind.OBJECT))



def _generalization_fixture(outer=()):
    flag = atom("c")
    conclusion = atom("P", c("c"))
    subproof = pl.SubproofRecord(
        flag,
        [flag, conclusion],
        outer_context_ref=list(outer),
        boundary_index=len(outer),
    )
    target = fl.ForAll("x", atom("P", v("x")))
    return [subproof], target


def test_universal_generalization_refuses_a_constant_mentioned_in_outer_context():
    outer = [atom("Q", c("c"))]
    candidates, target = _generalization_fixture(outer)
    reason = pl.UniversalGeneralizationRule().explain_in_context(
        candidates, target, pl.RuleContext()
    )
    assert reason is not None
    assert "visible before the subproof opened" in reason


@pytest.mark.parametrize(
    "context,expected",
    [
        (pl.RuleContext(given=[atom("P", c("c"))]), "occurs in a hypothesis in force"),
        (pl.RuleContext(assumptions=[atom("Q", c("c"))]), "occurs in a hypothesis in force"),
        (pl.RuleContext(given=[atom("P", c("c"))]), "occurs in a hypothesis in force"),
        (pl.RuleContext(constrained_names=["c"]), "structure of a declaration"),
    ],
    ids=["premise-or-axiom", "enclosing-assumption", "such-that-or-witness-hypothesis", "constrained-carrier"],
)
def test_universal_generalization_refuses_each_kind_of_constraining_hypothesis(context, expected):
    candidates, target = _generalization_fixture()
    reason = pl.UniversalGeneralizationRule().explain_in_context(candidates, target, context)
    assert reason is not None
    assert expected in reason


def _existential_elimination_fixture(outer=()):
    existential = fl.Exists("x", atom("P", fl.VariableTerm("x")))
    assumption = atom("P", c("w"))
    conclusion = atom("Q", c("a"))
    subproof = pl.SubproofRecord(
        assumption,
        [assumption, conclusion],
        outer_context_ref=list(outer),
        boundary_index=len(outer),
    )
    return [existential, subproof], conclusion


def test_existential_elimination_refuses_a_witness_mentioned_in_outer_context():
    candidates, target = _existential_elimination_fixture([atom("R", c("w"))])
    reason = pl.ExistentialEliminationRule().explain_in_context(
        candidates, target, pl.RuleContext()
    )
    assert reason is not None
    assert "visible before the subproof opened" in reason


def test_existential_elimination_refuses_a_witness_in_a_hypothesis_in_force():
    candidates, target = _existential_elimination_fixture()
    context = pl.RuleContext(given=[atom("R", c("w"))])
    reason = pl.ExistentialEliminationRule().explain_in_context(candidates, target, context)
    assert reason is not None
    assert "occurs in a hypothesis in force" in reason


def test_existential_elimination_refuses_a_witness_named_by_declaration_structure():
    candidates, target = _existential_elimination_fixture()
    context = pl.RuleContext(constrained_names=["w"])
    reason = pl.ExistentialEliminationRule().explain_in_context(candidates, target, context)
    assert reason is not None
    assert "structure of a declaration" in reason
