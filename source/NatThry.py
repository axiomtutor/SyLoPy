


"""The theory of `Nat`: the first concrete `Type` (see ProofLogic.Type),
built entirely on general-purpose machinery -- nothing here required any
change to ProofLogic.py, FormulaLogic.py, or ProofParser.py.

Usage::

    import ProofLogic as pl
    from NatThry import NAT_TYPE

    axioms, schema_rules = pl.combine_types(NAT_TYPE)
    declarations = pl.combine_type_declarations(NAT_TYPE)
    proof = pl.Proof(
        entries,
        axioms=axioms,
        rules=pl.default_rules() + schema_rules,
        declarations=declarations,
    )

A future theory (Int, Rational, Set, ...) is a sibling file exporting its
own `Type` the same way; combine several by passing multiple `Type`s to
`combine_types(NAT_TYPE, INT_TYPE, ...)`.

--------------------------------------------------------------------------
What's characterized here
--------------------------------------------------------------------------
Four axioms establish the pure successor structure -- that `Nat` is
*exactly* `{Zero, Succ(Zero), Succ(Succ(Zero)), ...}`, nothing more and
nothing less:

  1. `Nat(Zero)` -- zero is a natural number.
  2. `forall x, (Nat(x) -> Nat(Succ(x)))` -- naturals are closed under
     successor.
  3. `forall x, (Nat(x) -> not (Succ(x) = Zero))` -- successor never
     produces zero (rules out the structure "wrapping around").
  4. `forall x, forall y, ((Nat(x) and Nat(y) and Succ(x) = Succ(y)) -> x = y)`
     -- successor is injective (rules out two different naturals
     collapsing to the same successor).

Axioms 3 and 4 depend on equality (`Equals`, and the `ReflexivityRule`/
`LeibnizSubstitutionRule`/`SymmetryRule`/`TransitivityRule` quartet in
`ProofLogic.py`) -- without them, axioms 1-2 alone would be satisfied by
structures other than the naturals (e.g. one where `Succ` cycles back to
`Zero`), so they aren't optional polish.

`NAT_TYPE.schema_rules` supplies induction, via `InductionRule` -- the
*fifth* thing needed to fully pin `Nat` down to exactly the naturals and
nothing larger (without it, "the whole domain" would also satisfy axioms
1-4). See `ProofLogic.InductionRule`'s docstring for exactly how a
citation is shaped and checked.

--------------------------------------------------------------------------
What's deliberately not here yet
--------------------------------------------------------------------------
No `+`, `*`, `<`, or their axioms -- this file characterizes *what a
natural number is*, not arithmetic operations over them. Addition and
multiplication would each be their own function symbol plus their own
pair of defining axioms (a base case and a successor case, the same
recursive shape as induction itself, e.g.
`forall x, (Nat(x) -> Plus(x, Zero) = x)` and
`forall x, forall y, ((Nat(x) and Nat(y)) -> Plus(x, Succ(y)) = Succ(Plus(x, y)))`)
-- a natural next addition to this same file once the structural axioms
below are in use.
"""

import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.TermLogic as tl

Zero = tl.ConstantTerm('Zero', 'Zero')
SUCC = 'Succ'   # the successor function symbol's name, as used in Succ(x) = FunctionTerm(SUCC, [x])

_x = tl.VariableTerm('x')
_y = tl.VariableTerm('y')


def _Nat(term: tl.Term) -> fl.Formula:
    return fl.AtomicFormula('Nat', [term])


def _Succ(term: tl.Term) -> tl.Term:
    return tl.FunctionTerm(SUCC, [term])


NAT_AXIOMS = [
    # 1. Nat(Zero)
    _Nat(Zero),

    # 2. forall x, (Nat(x) -> Nat(Succ(x)))
    fl.ForAll('x', fl.Implies(_Nat(_x), _Nat(_Succ(_x)))),

    # 3. forall x, (Nat(x) -> not (Succ(x) = Zero))
    fl.ForAll('x', fl.Implies(_Nat(_x), fl.Not(fl.Equals(_Succ(_x), Zero)))),

    # 4. forall x, forall y, ((Nat(x) and Nat(y) and Succ(x) = Succ(y)) -> x = y)
    # Antecedent is a *nested* binary conjunction, `(Nat(x) and Nat(y)) and
    # Succ(x)=Succ(y)`, rather than one flat 3-ary And -- ConjunctionIntroductionRule
    # is capped at exactly 2 citations per step (see its docstring in
    # ProofLogic.py), so a proof building up to this antecedent needs two
    # binary steps, which only lines up with a nested shape.
    fl.ForAll('x', fl.ForAll('y', fl.Implies(
        fl.And(fl.And(_Nat(_x), _Nat(_y)), fl.Equals(_Succ(_x), _Succ(_y))),
        fl.Equals(_x, _y),
    ))),
]

NAT_DECLARATIONS = [
    pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
    pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
    pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
]


NAT_TYPE = pl.Type(
    name="Nat",
    predicate="Nat",
    axioms=NAT_AXIOMS,
    schema_rules=[pl.InductionRule(type_predicate="Nat", zero_term=Zero, succ_symbol=SUCC)],
    declarations=NAT_DECLARATIONS,
)


if __name__ == "__main__":
    # A minimal end-to-end sanity check: prove `forall x, (Nat(x) -> P(x))`
    # from `P(Zero)` and the inductive step, for an arbitrary made-up P,
    # exercising the base axioms, Induction, and the surrounding Proof/
    # ProofValidator machinery together.
    P = lambda t: fl.AtomicFormula('P', [t])
    n = tl.VariableTerm('n')

    axioms, schema_rules = pl.combine_types(NAT_TYPE)
    declarations = pl.combine_type_declarations(NAT_TYPE)

    p_zero = P(Zero)
    step = fl.ForAll('n', fl.Implies(fl.And(_Nat(n), P(n)), P(_Succ(n))))
    conclusion = fl.ForAll('x', fl.Implies(_Nat(_x), P(_x)))

    entries = [
        ('1', p_zero, ('premise',)),
        ('2', step, ('premise',)),
        ('3', conclusion, ('rule', schema_rules[0], ['1', '2'])),
    ]
    proof = pl.Proof(
        entries,
        premises=[p_zero, step],
        axioms=axioms,
        rules=pl.default_rules() + schema_rules,
        declarations=declarations + [pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1)],
    )
    ok, err = proof.check_detailed()
    print("NatTheory self-check:", "PASS" if ok else f"FAIL ({err})")




