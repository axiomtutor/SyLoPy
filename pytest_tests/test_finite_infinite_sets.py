import pytest

from .support import pp, pl, fl, tl, st


def c(name):
    return tl.ConstantTerm(name, name)


def test_finite_and_infinite_declarations_add_core_claims():
    entries, _ = pp.parse_proof_text(
        "1. Let A be a finite set, B be an infinite set. (Declaration)\n"
    )
    claims = entries[0][1]
    assert [repr(claim) for claim in claims] == ["Finite(A)", "Infinite(B)"]
    declarations = {d.name: d for d in entries[0][2][1]}
    assert declarations["A"].type_name == "set"
    assert declarations["B"].type_name == "set"
    assert pl.Proof(entries).check()[0]


def test_typed_bijection_declaration_adds_relation_claim():
    entries, _ = pp.parse_proof_text(
        "1. Let A be a set, B be a set, f: A -> B be a bijection. (Declaration)\n"
    )
    claims = entries[0][1]
    claim_list = claims if isinstance(claims, list) else [claims]
    assert [repr(claim) for claim in claim_list] == ["Bijection(f, A, B)"]
    declarations = {d.name: d for d in entries[0][2][1]}
    function = declarations["f"]
    assert function.kind == pl.DeclarationKind.FUNCTION
    assert function.arity == 1
    assert dict(function.metadata)["domain"] == "A"
    assert dict(function.metadata)["codomain"] == "B"
    assert dict(function.metadata)["bijection"] is True
    assert pl.Proof(entries).check()[0]


def test_surface_finite_infinite_and_bijection_claims():
    assert repr(st.parse_set_formula("A is finite")) == "Finite(A)"
    assert repr(st.parse_set_formula("B is infinite")) == "Infinite(B)"
    assert repr(
        st.parse_set_formula("f is a bijection from A to B")
    ) == "Bijection(f, A, B)"


def test_bijection_transfers_finite_and_infinite_both_directions():
    f, A, B = c("f"), c("A"), c("B")
    bijection = fl.AtomicFormula("Bijection", [f, A, B])

    finite = st.FiniteUnderBijectionRule()
    assert finite.applies(
        [fl.AtomicFormula("Finite", [A]), bijection],
        fl.AtomicFormula("Finite", [B]),
    )
    assert finite.applies(
        [bijection, fl.AtomicFormula("Finite", [B])],
        fl.AtomicFormula("Finite", [A]),
    )

    infinite = st.InfiniteUnderBijectionRule()
    assert infinite.applies(
        [fl.AtomicFormula("Infinite", [A]), bijection],
        fl.AtomicFormula("Infinite", [B]),
    )
    assert not infinite.applies(
        [fl.AtomicFormula("Finite", [A]), bijection],
        fl.AtomicFormula("Infinite", [B]),
    )


def test_malformed_property_claim_arity_is_rejected_by_symbol_validation():
    entries, _ = pp.parse_proof_text(
        "1. Let A be a set. (Declaration)\n"
        "2. Finite(A, A). (Premise)\n"
    )
    ok, message = pl.Proof(entries).check()
    assert not ok
    assert "arity" in str(message).lower()


def test_bijection_declaration_rejects_sets_not_declared_first():
    with pytest.raises(Exception, match="bijection.*|not.*declared|has not been declared"):
        pp.parse_proof_text(
            "1. f: A -> B be a bijection. (Declaration)\n"
        )


def test_explicit_finite_cardinality_surface_and_declarations():
    assert repr(st.parse_set_formula("A has cardinality 3")) == "Cardinality(A, 3)"
    assert repr(st.parse_set_formula("A has 3 elements")) == "Cardinality(A, 3)"
    assert repr(st.parse_set_formula("Cardinality(A, 3)")) == "Cardinality(A, 3)"

    entries, _ = pp.parse_proof_text(
        "1. Let A be a finite set of cardinality 3. (Declaration)\n"
    )
    claims = entries[0][1]
    claim_list = claims if isinstance(claims, list) else [claims]
    assert [repr(claim) for claim in claim_list] == ["Finite(A)", "Cardinality(A, 3)"]


def test_empty_and_cardinality_closure_rules():
    finite_empty = st.EmptySetFiniteRule()
    assert finite_empty.applies([], fl.AtomicFormula("Finite", [st.EMPTY_SET]))

    cardinality_empty = st.EmptySetCardinalityRule()
    assert cardinality_empty.applies(
        [],
        fl.AtomicFormula("Cardinality", [st.EMPTY_SET, tl.ConstantTerm("0", 0)]),
    )

    implication = st.CardinalityImpliesFiniteRule()
    A = c("A")
    assert implication.applies(
        [fl.AtomicFormula("Cardinality", [A, tl.ConstantTerm("3", 3)])],
        fl.AtomicFormula("Finite", [A]),
    )


def test_cardinality_arithmetic_rules():
    A, B = c("A"), c("B")
    power = tl.FunctionTerm("PowerSet", [A])
    assert st.CardinalityPowerSetRule().applies(
        [fl.AtomicFormula("Cardinality", [A, tl.ConstantTerm("3", 3)])],
        fl.AtomicFormula("Cardinality", [power, tl.ConstantTerm("8", 8)]),
    )

    product = tl.FunctionTerm("CartesianProduct", [A, B])
    assert st.CardinalityCartesianProductRule().applies(
        [
            fl.AtomicFormula("Cardinality", [A, tl.ConstantTerm("3", 3)]),
            fl.AtomicFormula("Cardinality", [B, tl.ConstantTerm("4", 4)]),
        ],
        fl.AtomicFormula("Cardinality", [product, tl.ConstantTerm("12", 12)]),
    )


def test_finite_operations_are_closed():
    A, B = c("A"), c("B")
    union = tl.FunctionTerm("Union", [A, B])
    assert st.FiniteUnionRule().applies(
        [
            fl.AtomicFormula("Finite", [A]),
            fl.AtomicFormula("Finite", [B]),
        ],
        fl.AtomicFormula("Finite", [union]),
    )

    product = tl.FunctionTerm("CartesianProduct", [A, B])
    assert st.FiniteCartesianProductRule().applies(
        [
            fl.AtomicFormula("Finite", [A]),
            fl.AtomicFormula("Finite", [B]),
        ],
        fl.AtomicFormula("Finite", [product]),
    )
