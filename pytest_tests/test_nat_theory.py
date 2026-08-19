


from pathlib import Path

import pytest

from .support import nt, pl, fl, tl, pp, atom, c, v


def test_nat_type_metadata_and_holds():
    assert nt.NAT_TYPE.name == "Nat"
    assert nt.NAT_TYPE.predicate == "Nat"
    assert len(nt.NAT_TYPE.axioms) == 4
    assert len(nt.NAT_TYPE.schema_rules) == 1
    assert repr(nt.NAT_TYPE.holds(c("a"))) == "Nat(a)"


def test_nat_axiom_shapes():
    zero, closure, no_predecessor, injective = nt.NAT_AXIOMS
    assert repr(zero) == "Nat(Zero)"
    assert repr(closure) == "(∀x. (Nat(x) → Nat(Succ(x))))"
    assert repr(no_predecessor) == "(∀x. (Nat(x) → ¬Succ(x) = Zero))"
    assert "Succ(x) = Succ(y)" in repr(injective)
    assert repr(injective).endswith("x = y)))")


def test_combine_types_flattens_axioms_and_schema_rules():
    dummy = pl.Type("Dummy", "D", [atom("D", c("d"))], [pl.ReiterationRule()])
    axioms, rules = pl.combine_types(nt.NAT_TYPE, dummy)
    assert axioms[:4] == nt.NAT_AXIOMS
    assert len(axioms) == 5
    assert isinstance(rules[0], pl.InductionRule)
    assert isinstance(rules[1], pl.ReiterationRule)


def test_induction_rule_accepts_valid_schema_with_any_step_variable_name():
    rule = nt.NAT_TYPE.schema_rules[0]
    zero = nt.Zero
    base = atom("P", zero)
    step = fl.ForAll(
        "k",
        fl.Implies(
            fl.And(atom("Nat", v("k")), atom("P", v("k"))),
            atom("P", tl.FunctionTerm("Succ", [v("k")])),
        ),
    )
    conclusion = fl.ForAll("x", fl.Implies(atom("Nat", v("x")), atom("P", v("x"))))
    assert rule.applies([base, step], conclusion)


@pytest.mark.parametrize(
    "base,step,conclusion",
    [
        (
            atom("P", c("a")),
            fl.ForAll("n", fl.Implies(fl.And(atom("Nat", v("n")), atom("P", v("n"))), atom("P", tl.FunctionTerm("Succ", [v("n")])))),
            fl.ForAll("x", fl.Implies(atom("Nat", v("x")), atom("P", v("x")))),
        ),
        (
            atom("P", nt.Zero),
            fl.ForAll("n", fl.Implies(fl.And(atom("Nat", v("n")), atom("P", v("n"))), atom("P", v("n")))),
            fl.ForAll("x", fl.Implies(atom("Nat", v("x")), atom("P", v("x")))),
        ),
        (
            atom("P", nt.Zero),
            fl.ForAll("n", fl.Implies(fl.And(atom("Nat", v("n")), atom("P", v("n"))), atom("P", tl.FunctionTerm("Succ", [v("n")])))),
            fl.ForAll("x", atom("P", v("x"))),
        ),
    ],
)
def test_induction_rule_rejects_wrong_base_step_or_conclusion(base, step, conclusion):
    assert not nt.NAT_TYPE.schema_rules[0].applies([base, step], conclusion)


def test_nat_theory_end_to_end_induction_proof():
    axioms, schema_rules = pl.combine_types(nt.NAT_TYPE)
    zero = nt.Zero
    base = atom("P", zero)
    step = fl.ForAll(
        "n",
        fl.Implies(
            fl.And(atom("Nat", v("n")), atom("P", v("n"))),
            atom("P", tl.FunctionTerm("Succ", [v("n")])),
        ),
    )
    conclusion = fl.ForAll("x", fl.Implies(atom("Nat", v("x")), atom("P", v("x"))))
    entries = [
        ("1", base, ("premise",)),
        ("2", step, ("premise",)),
        ("3", conclusion, ("rule", pl.NamedRulePlaceholder("Induction"), ["1", "2"])),
    ]
    ok, msg = pl.Proof(
        entries, premises=[base, step], axioms=axioms, rules=pl.default_rules() + schema_rules,
        declarations=pl.combine_type_declarations(nt.NAT_TYPE) + [pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1)],
    ).check()
    assert ok, msg


def test_current_nat_fixture_corpus():
    project = Path(__file__).resolve().parents[1]
    fixture_dir = project / "tests" / "testProofsNat"
    axioms, schema_rules = pl.combine_types(nt.NAT_TYPE)
    declarations = pl.combine_type_declarations(nt.NAT_TYPE)

    outcomes = {}
    for path in fixture_dir.glob("*.txt"):
        entries, _ = pp.parse_proof_text(path.read_text())
        outcomes[path.name] = pl.Proof(
            entries,
            axioms=axioms,
            rules=pl.default_rules() + schema_rules,
            declarations=declarations,
        ).check()[0]

    assert outcomes["nat_closure_under_succ.txt"] is True
    assert all(
        not valid
        for name, valid in outcomes.items()
        if name.startswith("invalid_")
    )


def test_nat_type_declarations():
    declarations = pl.combine_type_declarations(nt.NAT_TYPE)
    assert {(d.name, d.kind, d.arity) for d in declarations} == {
        ("Nat", pl.DeclarationKind.PREDICATE, 1),
        ("Zero", pl.DeclarationKind.OBJECT, None),
        ("Succ", pl.DeclarationKind.FUNCTION, 1),
    }




