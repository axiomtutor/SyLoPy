"""Adversarial schema-rule tests for the integer and natural-number theories.

These probes focus on operand alignment, required premise shapes/order, and the
full conclusion schema. They complement the existing happy-path and ordinary
wrong-shape tests rather than modifying either theory or the kernel.
"""

import pytest

from .support import numt, nt, pl, fl, tl, atom, c, v, fn


def _int(term):
    return atom(numt.INT_PREDICATE, term)


def _quotient(n, a):
    return fn(numt.QUOTIENT, n, a)


def _times(a, b):
    return fn(numt.TIMES, a, b)


# ---------------------------------------------------------------------------
# Quotient defining property: Int(n/a) -> n = a * (n/a)
# ---------------------------------------------------------------------------

def _quotient_defining_case():
    n, a = c("n"), c("a")
    quotient = _quotient(n, a)
    return [ _int(quotient) ], fl.Equals(n, _times(a, quotient))


def test_quotient_defining_property_accepts_only_the_aligned_division_equation():
    candidates, conclusion = _quotient_defining_case()
    assert numt.QuotientDefiningPropertyRule().applies(candidates, conclusion)


@pytest.mark.parametrize("mutate", [
    # Times operands reversed: commutativity is not a built-in axiom.
    lambda n, a, q: fl.Equals(n, _times(q, a)),
    # The quotient in the product uses another numerator.
    lambda n, a, q: fl.Equals(n, _times(a, _quotient(c("other_n"), a))),
    # The quotient in the product uses another divisor.
    lambda n, a, q: fl.Equals(n, _times(a, _quotient(n, c("other_a")))),
    # A different operation cannot stand in for Times.
    lambda n, a, q: fl.Equals(n, fn(numt.PLUS, a, q)),
    # The equation cannot be reversed without a separate equality step.
    lambda n, a, q: fl.Equals(_times(a, q), n),
])
def test_quotient_defining_property_rejects_misaligned_conclusions(mutate):
    n, a = c("n"), c("a")
    q = _quotient(n, a)
    assert not numt.QuotientDefiningPropertyRule().applies(
        [_int(q)], mutate(n, a, q)
    )


@pytest.mark.parametrize("candidate", [
    lambda n, a, q: _int(n),
    lambda n, a, q: _int(_quotient(a, n)),
    lambda n, a, q: atom("Nat", q),
])
def test_quotient_defining_property_rejects_wrong_side_conditions(candidate):
    n, a = c("n"), c("a")
    q = _quotient(n, a)
    rule = numt.QuotientDefiningPropertyRule()
    assert not rule.applies([candidate(n, a, q)], fl.Equals(n, _times(a, q)))


def test_quotient_defining_property_rejects_missing_or_extra_premises():
    candidates, conclusion = _quotient_defining_case()
    rule = numt.QuotientDefiningPropertyRule()
    assert not rule.applies([], conclusion)
    assert not rule.applies(candidates + [atom("P")], conclusion)


# ---------------------------------------------------------------------------
# Quotient uniqueness: Int(m), n = a*m  |-  n/a = m
# ---------------------------------------------------------------------------

def _quotient_uniqueness_case():
    n, a, m = c("n"), c("a"), c("m")
    return (
        [_int(m), fl.Equals(n, _times(a, m))],
        fl.Equals(_quotient(n, a), m),
    )


def test_quotient_uniqueness_accepts_the_integer_witness_and_matching_equation():
    candidates, conclusion = _quotient_uniqueness_case()
    assert numt.QuotientUniquenessRule().applies(candidates, conclusion)


@pytest.mark.parametrize("mutate", [
    # Not the same quotient as in the equation.
    lambda n, a, m: fl.Equals(_quotient(n, c("other_a")), m),
    lambda n, a, m: fl.Equals(_quotient(c("other_n"), a), m),
    # The equation must be n = a*m in this direction and order.
    lambda n, a, m: fl.Equals(n, _times(m, a)),
    lambda n, a, m: fl.Equals(_times(a, m), n),
    # A different operation does not give a quotient solution.
    lambda n, a, m: fl.Equals(n, fn(numt.PLUS, a, m)),
])
def test_quotient_uniqueness_rejects_nonmatching_conclusions(mutate):
    n, a, m = c("n"), c("a"), c("m")
    rule = numt.QuotientUniquenessRule()
    assert not rule.applies(
        [_int(m), fl.Equals(n, _times(a, m))],
        mutate(n, a, m),
    )


@pytest.mark.parametrize("first,second", [
    # The quotient candidate must itself be known integer.
    (lambda n, a, m: _int(_quotient(n, a)),
     lambda n, a, m: fl.Equals(n, _times(a, m))),
    # The equation's witness must match the first candidate's m.
    (lambda n, a, m: _int(m),
     lambda n, a, m: fl.Equals(n, _times(a, c("other_m")))),
    # A natural-number fact is not the integer premise required by this rule.
    (lambda n, a, m: atom("Nat", m),
     lambda n, a, m: fl.Equals(n, _times(a, m))),
])
def test_quotient_uniqueness_rejects_wrong_premise_shapes(first, second):
    n, a, m = c("n"), c("a"), c("m")
    conclusion = fl.Equals(_quotient(n, a), m)
    rule = numt.QuotientUniquenessRule()
    assert not rule.applies([first(n, a, m), second(n, a, m)], conclusion)


def test_quotient_uniqueness_rejects_missing_extra_or_reversed_premises():
    candidates, conclusion = _quotient_uniqueness_case()
    rule = numt.QuotientUniquenessRule()
    assert not rule.applies([], conclusion)
    assert not rule.applies(candidates[:1], conclusion)
    assert not rule.applies(candidates[1:], conclusion)
    assert not rule.applies(list(reversed(candidates)), conclusion)
    assert not rule.applies(candidates + [atom("P")], conclusion)


# ---------------------------------------------------------------------------
# Nat induction: P(Zero), forall n. ((Nat(n) and P(n)) -> P(Succ(n)))
#   |- forall x. (Nat(x) -> P(x))
# ---------------------------------------------------------------------------

def _nat_formula(term):
    return atom("Nat", term)


def _succ(term):
    return fn(nt.SUCC, term)


def _induction_case():
    zero = nt.Zero
    base = atom("P", zero)
    step = fl.ForAll(
        "k",
        fl.Implies(
            fl.And(_nat_formula(v("k")), atom("P", v("k"))),
            atom("P", _succ(v("k"))),
        ),
    )
    conclusion = fl.ForAll(
        "x",
        fl.Implies(_nat_formula(v("x")), atom("P", v("x"))),
    )
    return base, step, conclusion


def test_nat_induction_accepts_the_configured_zero_successor_and_predicate():
    base, step, conclusion = _induction_case()
    assert nt.NAT_TYPE.schema_rules[0].applies([base, step], conclusion)


@pytest.mark.parametrize("base_mutation", [
    lambda: atom("P", c("not_zero")),
    lambda: atom("P", _succ(nt.Zero)),
    lambda: atom("Q", nt.Zero),
])
def test_nat_induction_rejects_wrong_base_instance(base_mutation):
    _base, step, conclusion = _induction_case()
    assert not nt.NAT_TYPE.schema_rules[0].applies(
        [base_mutation(), step], conclusion
    )


@pytest.mark.parametrize("step_mutation", [
    # Induction is over Nat, not an arbitrary predicate.
    lambda: fl.ForAll("k", fl.Implies(
        fl.And(atom("Int", v("k")), atom("P", v("k"))),
        atom("P", _succ(v("k"))),
    )),
    # The induction hypothesis and type guard must both occur.
    lambda: fl.ForAll("k", fl.Implies(
        atom("P", v("k")), atom("P", _succ(v("k")))
    )),
    # Reordering the antecedent is not silently normalized by schema matching.
    lambda: fl.ForAll("k", fl.Implies(
        fl.And(atom("P", v("k")), _nat_formula(v("k"))),
        atom("P", _succ(v("k"))),
    )),
    # The step must establish P(Succ(k)), not merely P(k).
    lambda: fl.ForAll("k", fl.Implies(
        fl.And(_nat_formula(v("k")), atom("P", v("k"))),
        atom("P", v("k")),
    )),
    # The successor must be applied to the induction variable.
    lambda: fl.ForAll("k", fl.Implies(
        fl.And(_nat_formula(v("k")), atom("P", v("k"))),
        atom("P", _succ(c("k"))),
    )),
])
def test_nat_induction_rejects_wrong_step_premise_or_successor(step_mutation):
    base, _step, conclusion = _induction_case()
    assert not nt.NAT_TYPE.schema_rules[0].applies(
        [base, step_mutation()], conclusion
    )


@pytest.mark.parametrize("conclusion_mutation", [
    # Missing the type guard.
    lambda: fl.ForAll("x", atom("P", v("x"))),
    # Wrong type guard.
    lambda: fl.ForAll("x", fl.Implies(atom("Int", v("x")), atom("P", v("x")))),
    # The conclusion's property must match the base and step property.
    lambda: fl.ForAll("x", fl.Implies(_nat_formula(v("x")), atom("Q", v("x")))),
    # The conclusion must quantify the type implication, not a bare fact.
    lambda: fl.Implies(_nat_formula(c("a")), atom("P", c("a"))),
])
def test_nat_induction_rejects_wrong_conclusion_shape(conclusion_mutation):
    base, step, _conclusion = _induction_case()
    assert not nt.NAT_TYPE.schema_rules[0].applies(
        [base, step], conclusion_mutation()
    )


def test_nat_induction_rejects_swapped_missing_and_extra_citations():
    base, step, conclusion = _induction_case()
    rule = nt.NAT_TYPE.schema_rules[0]
    assert not rule.applies([step, base], conclusion)
    assert not rule.applies([base], conclusion)
    assert not rule.applies([base, step, atom("P")], conclusion)


def test_invalid_induction_application_fails_at_the_cited_rule_line():
    base, step, conclusion = _induction_case()
    rule = nt.NAT_TYPE.schema_rules[0]
    declarations = [
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        *pl.combine_type_declarations(nt.NAT_TYPE),
    ]
    entries = [
        ("1", base, ("premise",)),
        ("2", step, ("premise",)),
        # Claims an induction conclusion for Q, despite the cited P cases.
        ("3", fl.ForAll(
            "x", fl.Implies(_nat_formula(v("x")), atom("Q", v("x")))
        ), ("rule", rule, ["1", "2"])),
    ]
    proof = pl.Proof(
        entries,
        premises=[base, step],
        rules=[rule],
        declarations=declarations + [
            pl.Declaration("Q", pl.DeclarationKind.PREDICATE, arity=1)
        ],
    )
    ok, error = proof.check_detailed()
    assert not ok
    assert error.category == pl.CATEGORY_RULE_MISMATCH
    assert error.label == "3"
