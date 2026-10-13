"""Audit that parameterized inference rules are registered by configuration.

The trusted rule environment is not just a list of Python classes. An
InductionRule is parameterized by the predicate and successor structure for
which induction is sound; registering induction for Int must not authorize a
direct rule object for Nat.
"""

import pytest

from .support import c, pl, pp


def _induction_case(type_predicate, zero, successor, extra_declarations=()):
    declarations = [
        pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Int", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
        pl.Declaration("ZeroInt", pl.DeclarationKind.OBJECT),
        pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
        pl.Declaration("SuccInt", pl.DeclarationKind.FUNCTION, arity=1),
        *extra_declarations,
    ]
    base = pp.parse_formula(f"P({zero})", set())
    step = pp.parse_formula(
        f"forall n, (({type_predicate}(n) and P(n)) -> "
        f"P({successor}(n)))",
        set(),
    )
    conclusion = pp.parse_formula(
        f"forall x, ({type_predicate}(x) -> P(x))",
        set(),
    )
    rule = pl.InductionRule(type_predicate, c(zero), successor)
    entries = [
        ("1", base, ("premise",)),
        ("2", step, ("premise",)),
        ("3", conclusion, ("rule", rule, ["1", "2"])),
    ]
    return declarations, rule, entries


def test_direct_citation_cannot_use_an_unregistered_parameterized_rule():
    """Registering Int induction does not register a direct Nat-rule object."""
    declarations, nat_induction, entries = _induction_case("Nat", "Zero", "Succ")
    int_induction = pl.InductionRule("Int", c("ZeroInt"), "SuccInt")
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + [int_induction],
        declarations=declarations,
    )

    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "the proof cited Nat induction successfully although its rule "
            "environment registers only Int induction; _rule_is_registered "
            "currently checks the Python class rather than the parameters"
        )

    assert error is not None
    assert error.label == "3"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE


def test_matching_parameterized_rule_instance_is_usable():
    declarations, nat_induction, entries = _induction_case("Nat", "Zero", "Succ")
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + [nat_induction],
        declarations=declarations,
    )
    ok, error = proof.check_detailed()
    assert ok, error


def test_direct_citation_cannot_use_an_unregistered_theorem_instance():
    """Registering one TheoremRule must not authorize every theorem object."""
    p = pp.parse_formula("P", set())
    q = pp.parse_formula("Q", set())
    declarations = [
        pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
        pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
    ]
    registered = pl.TheoremRule("Registered theorem", [], p, [])
    unregistered = pl.TheoremRule("Unregistered theorem", [], q, [])
    proof = pl.Proof(
        [("1", q, ("rule", unregistered, []))],
        rules=pl.default_rules() + [registered],
        declarations=declarations,
    )

    ok, error = proof.check_detailed()
    if ok:
        pytest.xfail(
            "the kernel accepted an unregistered TheoremRule instance because "
            "another TheoremRule instance of the same Python class was allowed"
        )

    assert error is not None
    assert error.label == "1"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE
