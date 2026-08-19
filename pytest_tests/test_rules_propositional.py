


import pytest

from .support import pl, fl, tl, c, v, fn, atom, A, B, C, D


def test_ast_eq_is_structural_not_semantic():
    a1, a2 = c("a", 1), c("a", 2)
    assert pl._ast_eq(atom("P", a1), atom("P", a2))
    assert not pl._ast_eq(atom("P", a1), atom("Q", a2))
    assert not pl._ast_eq(fl.And(A, B), fl.And(B, A))
    assert not pl._ast_eq(c("a"), v("a"))


def test_ast_eq_all_formula_and_term_shapes():
    x1, x2 = v("x"), v("x")
    left = fl.ForAll("x", fl.Iff(
        fl.Implies(atom("P", fn("f", x1)), fl.Not(atom("Q", x1))),
        fl.Exists("y", fl.Equals(fn("g", x1), v("y"))),
    ))
    right = fl.ForAll("x", fl.Iff(
        fl.Implies(atom("P", fn("f", x2)), fl.Not(atom("Q", x2))),
        fl.Exists("y", fl.Equals(fn("g", x2), v("y"))),
    ))
    assert pl._ast_eq(left, right)
    assert not pl._ast_eq(left, fl.ForAll("z", right.body))


@pytest.mark.parametrize(
    "rule,candidates,phi",
    [
        (pl.ConjunctionEliminationRule(), [fl.And(A, B)], A),
        (pl.ConjunctionIntroductionRule(), [A, B], fl.And(A, B)),
        (pl.DisjunctionIntroductionRule(), [A], fl.Or(B, A, C)),
        (pl.BiconditionalEliminationRule(), [fl.Iff(A, B)], fl.Implies(A, B)),
        (pl.BiconditionalEliminationRule(), [fl.Iff(A, B)], fl.Implies(B, A)),
        (pl.BiconditionalIntroductionRule(), [fl.Implies(A, B), fl.Implies(B, A)], fl.Iff(A, B)),
        (pl.ReiterationRule(), [A], atom("A")),
        (pl.ModusPonensRule(), [A, fl.Implies(A, B)], B),
        (pl.ModusPonensRule(), [fl.Implies(A, B), A], B),
        (pl.ModusTollensRule(), [fl.Implies(A, B), fl.Not(B)], fl.Not(A)),
        (pl.DisjunctiveSyllogismRule(), [fl.Or(A, B), fl.Not(A)], B),
        (pl.DisjunctiveSyllogismRule(), [fl.Not(B), fl.Or(A, B)], A),
        (pl.HypotheticalSyllogismRule(), [fl.Implies(A, B), fl.Implies(B, C)], fl.Implies(A, C)),
        (pl.HypotheticalSyllogismRule(), [fl.Implies(B, C), fl.Implies(A, B)], fl.Implies(A, C)),
    ],
)
def test_basic_propositional_rules_accept(rule, candidates, phi):
    assert rule.applies(candidates, phi)


@pytest.mark.parametrize(
    "rule,candidates,phi",
    [
        (pl.ConjunctionEliminationRule(), [fl.Or(A, B)], A),
        (pl.ConjunctionEliminationRule(), [fl.And(A, B)], C),
        (pl.ConjunctionIntroductionRule(), [A], fl.And(A)),
        (pl.ConjunctionIntroductionRule(), [A, B], fl.And(B, A)),
        (pl.DisjunctionIntroductionRule(), [A], fl.And(A, B)),
        (pl.DisjunctionIntroductionRule(), [A], fl.Or(B, C)),
        (pl.BiconditionalEliminationRule(), [fl.Implies(A, B)], fl.Implies(A, B)),
        (pl.BiconditionalIntroductionRule(), [fl.Implies(A, B), fl.Implies(A, B)], fl.Iff(A, B)),
        (pl.ReiterationRule(), [A], B),
        (pl.ModusPonensRule(), [B, fl.Implies(A, C)], C),
        (pl.ModusTollensRule(), [fl.Implies(A, B), fl.Not(A)], fl.Not(B)),
        (pl.DisjunctiveSyllogismRule(), [fl.Or(A, B, C), fl.Not(A)], B),
        (pl.HypotheticalSyllogismRule(), [fl.Implies(A, B), fl.Implies(C, D)], fl.Implies(A, D)),
    ],
)
def test_basic_propositional_rules_reject(rule, candidates, phi):
    assert not rule.applies(candidates, phi)


def test_conditional_introduction():
    sp = pl.SubproofRecord(A, [A, B])
    assert pl.ConditionalIntroductionRule().applies([sp], fl.Implies(A, B))
    assert not pl.ConditionalIntroductionRule().applies([sp], fl.Implies(B, A))


def test_disjunction_elimination_order_independent_for_disjunction_and_subproofs():
    sp_a = pl.SubproofRecord(A, [A, C])
    sp_b = pl.SubproofRecord(B, [B, C])
    disj = fl.Or(A, B)
    rule = pl.DisjunctionEliminationRule()
    assert rule.applies([disj, sp_a, sp_b], C)
    assert rule.applies([sp_b, disj, sp_a], C)
    assert not rule.applies([disj, sp_a, pl.SubproofRecord(B, [B, D])], C)
    assert not rule.applies([fl.Or(A, B, C), sp_a, sp_b], C)


def test_proof_by_contradiction_positive_and_negative_conclusion():
    contradiction = fl.And(B, fl.Not(B))
    rule = pl.ProofByContradictionRule()
    sp_not_a = pl.SubproofRecord(fl.Not(A), [fl.Not(A), contradiction])
    sp_a = pl.SubproofRecord(A, [A, contradiction])
    assert rule.applies([sp_not_a], A)
    assert rule.applies([sp_a], fl.Not(A))
    assert not rule.applies([sp_not_a], B)


@pytest.mark.parametrize(
    "formula,expected",
    [
        (fl.And(A, fl.Not(A)), True),
        (fl.And(fl.Not(A), A), True),
        (fl.And(fl.Not(fl.Not(A)), fl.Not(A)), True),
        (fl.And(fl.Not(fl.Not(A)), A), False),
        (fl.And(A, B), False),
        (fl.And(A, fl.Not(A), B), False),
        (fl.Or(A, fl.Not(A)), False),
    ],
)
def test_contradiction_recognition(formula, expected):
    assert pl._is_contradiction(formula) is expected


@pytest.mark.parametrize(
    "old,new",
    [
        (A, fl.Not(fl.Not(A))),
        (fl.Not(fl.Not(A)), A),
        (fl.Not(fl.And(A, B)), fl.Or(fl.Not(A), fl.Not(B))),
        (fl.Not(fl.Or(A, B)), fl.And(fl.Not(A), fl.Not(B))),
        (fl.Implies(A, B), fl.Or(fl.Not(A), B)),
        (fl.And(A, fl.Or(B, C)), fl.Or(fl.And(A, B), fl.And(A, C))),
        (fl.Or(A, fl.And(B, C)), fl.And(fl.Or(A, B), fl.Or(A, C))),
        (fl.Or(A, fl.Not(fl.Not(B))), fl.Or(A, B)),
        (fl.ForAll("x", fl.Not(fl.Not(atom("P", v("x"))))), fl.ForAll("x", atom("P", v("x")))),
    ],
)
def test_propositional_equivalence_accepts_supported_rewrites(old, new):
    assert pl.PropositionalEquivalenceRule().applies([old], new)


@pytest.mark.parametrize(
    "old,new",
    [
        (A, A),
        (fl.And(A, B), fl.And(B, A)),
        (fl.Implies(A, B), fl.Or(B, fl.Not(A))),
        (fl.ForAll("x", atom("P", v("x"))), fl.ForAll("y", atom("P", v("y")))),
        (fl.And(A, fl.Or(B, C)), fl.And(fl.Or(A, B), fl.Or(A, C))),
    ],
)
def test_propositional_equivalence_rejects_unsupported_or_noop_rewrites(old, new):
    assert not pl.PropositionalEquivalenceRule().applies([old], new)


def test_rule_arity_metadata_matches_validator_contract():
    expected = {
        pl.ReflexivityRule: 0,
        pl.ReiterationRule: 1,
        pl.ModusPonensRule: 2,
        pl.DisjunctionEliminationRule: 3,
    }
    for cls, arity in expected.items():
        assert cls.premise_arity == arity




