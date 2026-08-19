


from pathlib import Path

from .support import numt, nt, pl, fl, tl, pp, atom, c, v


def test_int_axiom_shapes():
    nat_subset, plus_closure, times_closure, neg_closure, quotient_defining, quotient_unique = numt.INT_AXIOMS
    assert repr(nat_subset) == "(∀x. (Nat(x) → Int(x)))"
    assert "Int(Plus(x, y))" in repr(plus_closure)
    assert "Int(Times(x, y))" in repr(times_closure)
    assert repr(neg_closure) == "(∀x. (Int(x) → Int(Neg(x))))"
    assert "Int(Quotient(n, a))" in repr(quotient_defining)
    assert "n = Times(a, Quotient(n, a))" in repr(quotient_defining)
    assert "Quotient(n, a) = m" in repr(quotient_unique)


def test_divides_formula_is_the_defining_existential():
    formula = numt.divides_formula(c("a"), c("n"), witness_name="m")
    assert isinstance(formula, fl.Exists)
    assert formula.var == "m"
    assert repr(formula) == "(∃m. (Int(m) ∧ n = Times(a, m)))"


def test_quotient_defining_property_rule_accepts_and_rejects():
    rule = numt.QuotientDefiningPropertyRule()
    n, a = c("n"), c("a")
    quotient = tl.FunctionTerm(numt.QUOTIENT, [n, a])
    premise = atom(numt.INT_PREDICATE, quotient)
    conclusion = fl.Equals(n, tl.FunctionTerm(numt.TIMES, [a, quotient]))
    assert rule.applies([premise], conclusion)
    # Swapped operands in the Times() call don't match the axiom's shape.
    wrong = fl.Equals(n, tl.FunctionTerm(numt.TIMES, [quotient, a]))
    assert not rule.applies([premise], wrong)


def test_quotient_uniqueness_rule_accepts_and_rejects():
    rule = numt.QuotientUniquenessRule()
    n, a, m = c("n"), c("a"), c("m")
    int_m = atom(numt.INT_PREDICATE, m)
    equation = fl.Equals(n, tl.FunctionTerm(numt.TIMES, [a, m]))
    conclusion = fl.Equals(tl.FunctionTerm(numt.QUOTIENT, [n, a]), m)
    assert rule.applies([int_m, equation], conclusion)
    # Citation order matters, matching every other AxiomSchemaRule in the module.
    assert not rule.applies([equation, int_m], conclusion)
    # Without Int(m) established, uniqueness alone can't be invoked.
    assert not rule.applies([equation], conclusion)


def test_infix_quotient_and_divisibility_sugar_parse():
    assert repr(pp.parse_term("n/a")) == "Quotient(n, a)"
    assert repr(pp.parse_formula("n/a is an integer")) == "Int(Quotient(n, a))"
    divides = pp.parse_formula("a|n")
    assert isinstance(divides, fl.Exists)
    assert repr(divides.body).startswith("(Int(")


def test_divisibility_sugar_recognized_when_nested_inside_a_connective():
    # Regression coverage for the bug this caught during development: a
    # theory phrase containing a connective-looking character ('|') must
    # not swallow a surrounding "if ... then ..." before it gets to split.
    formula = pp.parse_formula("if n/a is an integer then a|n")
    assert isinstance(formula, fl.Implies)
    assert repr(formula.antecedent) == "Int(Quotient(n, a))"
    assert isinstance(formula.consequent, fl.Exists)


def test_number_theory_environment_includes_nat_and_set_theory():
    names = {rule.name for rule in numt.NUMBER_THEORY_ENVIRONMENT.rules}
    assert "QuotientDefiningProperty" in names
    assert "QuotientUniqueness" in names
    assert any(isinstance(rule, pl.InductionRule) for rule in numt.NUMBER_THEORY_ENVIRONMENT.rules)
    declared_names = {d.name for d in numt.NUMBER_THEORY_ENVIRONMENT.declarations}
    assert {"Int", "Plus", "Times", "Neg", "Quotient", "Nat", "Zero", "Succ", "EmptySet", "In"} <= declared_names


def test_current_number_theory_fixture_corpus():
    project = Path(__file__).resolve().parents[1]
    fixture_dir = project / "tests" / "testNumberTheory"

    outcomes = {}
    for path in fixture_dir.glob("*.txt"):
        entries, _ = pp.parse_proof_text(path.read_text())
        outcomes[path.name] = pl.Proof(entries).check()

    assert outcomes["divisibility_iff_quotient_integer.txt"][0] is True
    assert outcomes["nat_closure_gives_int.txt"][0] is True
    assert all(
        ok is False
        for name, (ok, _msg) in outcomes.items()
        if name.startswith("invalid_")
    )


def test_old_algebra_placeholder_citation_is_rejected_rather_than_silently_accepted():
    # "Algebra" was never a real rule (see NumberTheory.py's module
    # docstring); confirm it fails loudly instead of quietly validating.
    import pytest as _pytest
    with _pytest.raises(ValueError, match="Unknown inference rule"):
        pp.parse_justification("Algebra from 1")




