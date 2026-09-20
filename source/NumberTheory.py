


"""The theory of `Int`: integers, built on top of `NatThry` (naturals) and
`SetTheory`, in the sense the project's overall design calls for -- a
theory module extends the base logic and whatever other theories it
genuinely needs. Number theory needs naturals (every natural is an
integer) and, eventually, set-builder reasoning (the well-ordering
argument in `basicNT.txt`'s second proof), so this module imports both.

Usage::

    import SyLoPy.source.ProofParser as pp
    import SyLoPy.source.ProofLogic as pl
    from SyLoPy.source.NumberTheory import NUMBER_THEORY_ENVIRONMENT

    entries, _ = pp.parse_proof_text(text, NUMBER_THEORY_ENVIRONMENT)
    ok, err = pl.Proof(
        entries,
        axioms=NUMBER_THEORY_ENVIRONMENT.axioms,
        rules=pl.default_rules() + NUMBER_THEORY_ENVIRONMENT.rules,
        declarations=NUMBER_THEORY_ENVIRONMENT.declarations,
    ).check_detailed()

or, more simply, since `ProofParser.default_theory_environment()` already
tries to import this module: just call `pp.parse_proof_text(text)` and
`pl.Proof(entries)` and let `ElaboratedEntries.required_*` supply the Int
axioms/rules/declarations automatically (see `ProofLogic.Proof.__init__`).

--------------------------------------------------------------------------
What's characterized here
--------------------------------------------------------------------------
  1. `forall x, (Nat(x) -> Int(x))` -- every natural is an integer. This is
     the concrete instance of the "types can be overlapping" item on the
     project's todo list: `Nat` and `Int` are two predicates over the same
     domain of terms, one a subset of the other, not two disjoint types.
  2-4. Closure of `Int` under `Plus`, `Times`, and `Neg` (additive
     inverse) -- the minimal structure needed to call this "the integers"
     rather than just "the naturals with different notation".
  5-6. Two axioms characterizing `Quotient` (infix `n/a`) as *partial*
     division: `Quotient(n, a)` is only ever asserted to equal anything
     when it's already known to be an integer (i.e., when `a` evenly
     divides `n`) -- there is no axiom saying `Quotient` is total, and no
     axiom governing what `n/a` means when it *isn't* an integer.
       - Defining property: if `n/a` is an integer, then `n = a * (n/a)`.
       - Uniqueness: if `m` is an integer and `n = a * m`, then `n/a = m`.
     Both are exposed as one-step citable rules (`QuotientDefiningPropertyRule`,
     `QuotientUniquenessRule`) rather than left as a generic "Algebra"
     black box -- see the note on that below.
  7. `Times` associativity -- the first ring fact relating `Plus`/`Times`/
     `Neg` to each other (added because divisibility transitivity needed
     it; see the axiom's own comment), not a deliberate first step toward
     characterizing a full ring.
  8. Left distributivity of `Times` over `Plus` -- added the same way,
     because divisibility distributing over sums needed it (see that
     axiom's own comment). `Times` commutativity is not characterized, so
     right distributivity isn't implied by this and is separately absent.
     `Plus` associativity/commutativity remain absent too -- tracked below
     under "not here yet", to be added the same way these two were: when
     an actual proof needs one, not speculatively ahead of that.

Divisibility (`a|n`, "a divides n") is *not* a new primitive or a new
rule. It is definitional sugar, expanded at parse time to
`exists m, (Int(m) and n = a * m)` -- the same principle `SetTheory`'s
subset notation already follows (see `ELABORATION_ARCHITECTURE.md`).
Existential Introduction/Elimination, already in `ProofLogic.default_rules()`,
are what a proof actually cites to introduce or use a divisibility fact;
there is no separate "Definition of Divisibility" rule to look up, the
same way there was never a `SubsetRule` in `SetTheory`.

--------------------------------------------------------------------------
On "Algebra" and "Definition of Divisibility"
--------------------------------------------------------------------------
Earlier drafts of number-theory proof text cited steps as "(Algebra
from ...)" and "(Definition of Divisibility from ...)" as bare
placeholders, back when neither was a real, checked rule anywhere in
this project's history. Those drafts (and the redundant copies of them
that had accumulated in `source/ntProofs/`, `tests/testNT/`, and
`source/setProofs/`) are gone now, superseded by real fixtures under
`tests/testNumberTheory/`; see `todos.txt`'s Phase 6 entry for the
specifics of what was deleted and why. "Definition of Divisibility"
turns out not to be needed at all, for the reason above: divisibility
is definitional sugar, not a primitive a proof ever needs to invoke by
name. "Algebra" *is* needed, and is now real: `AlgebraRule`, in
`ProofLogic.py`, is a genuine congruence-closure decision procedure (see
that class's own docstring for exactly why it's sound, not a rubber
stamp), citable from proof text as "(Algebra from L1, L2, ...)" or
"(algebra from ...)" -- `ProofJustification`'s alias resolution is
case-insensitive for every rule name it recognizes, the same as "Modus
Ponens"/"modus ponens", so there was never a clean way to keep one
capitalization citable while rejecting the other once the rule itself
was sound. (An earlier version of this module's docstring, and a test
named for it, asserted that a capitalized "(Algebra ...)" citation
specifically should keep raising "unknown inference rule" -- that was
right while "Algebra" name a rubber stamp, and stopped being right the
moment `AlgebraRule` became a real procedure; both are updated now.)
The two `Quotient` axioms above remain their own named rules
(`QuotientDefiningPropertyRule`, `QuotientUniquenessRule`) rather than
folded into `AlgebraRule`, since they characterize what `Quotient`
*means* -- something no amount of congruence closure over already-cited
equations can produce on its own.

--------------------------------------------------------------------------
What's deliberately not here yet
--------------------------------------------------------------------------
No order relation (`<`, `<=`), no trichotomy, no well-ordering principle,
no set-builder-driven arguments, no GCD, no quotient-remainder
decomposition, no `Plus` associativity/commutativity, no `Times`
commutativity or right distributivity. The order-theory list is what the
GCD/Bezout argument needs (see `tests/testNumberTheory/`'s docstrings and
`todos.txt`'s Phase 6/7 entries for the fixture history here) and is a
substantially larger undertaking -- an order theory plus a well-ordering
axiom/schema, at minimum -- left for a follow-up rather than attempted
here. The ring facts are each individually small; each gets added when a
real proof needs it (this is how `Times` associativity and left
distributivity, above, got added), not ahead of that. `a|n` iff `n/a` is
an integer, and divisibility's closure under `Plus`/`Times` (sums and
transitivity both), do not need any of this and are fully supported.
"""

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.NatThry as nt
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.SetTheory as st
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.ProofElaboration import TheoryEnvironment

INT_PREDICATE = "Int"
PLUS = "Plus"
TIMES = "Times"
NEG = "Neg"
QUOTIENT = "Quotient"

_n = tl.VariableTerm('n')
_a = tl.VariableTerm('a')
_m = tl.VariableTerm('m')
_x = tl.VariableTerm('x')
_y = tl.VariableTerm('y')
_z = tl.VariableTerm('z')


def _Int(term: tl.Term) -> fl.Formula:
    return fl.AtomicFormula(INT_PREDICATE, [term])


def _Plus(x: tl.Term, y: tl.Term) -> tl.Term:
    return tl.FunctionTerm(PLUS, [x, y])


def _Times(x: tl.Term, y: tl.Term) -> tl.Term:
    return tl.FunctionTerm(TIMES, [x, y])


def _Neg(x: tl.Term) -> tl.Term:
    return tl.FunctionTerm(NEG, [x])


def _Quotient(x: tl.Term, y: tl.Term) -> tl.Term:
    return tl.FunctionTerm(QUOTIENT, [x, y])


INT_AXIOMS = [
    # 1. Every natural is an integer -- Nat and Int overlap rather than
    #    partition the domain (see the module docstring).
    fl.ForAll('x', fl.Implies(nt._Nat(_x), _Int(_x))),

    # 2-4. Closure under Plus, Times, and Neg.
    fl.ForAll('x', fl.ForAll('y', fl.Implies(
        fl.And(_Int(_x), _Int(_y)), _Int(_Plus(_x, _y)),
    ))),
    fl.ForAll('x', fl.ForAll('y', fl.Implies(
        fl.And(_Int(_x), _Int(_y)), _Int(_Times(_x, _y)),
    ))),
    fl.ForAll('x', fl.Implies(_Int(_x), _Int(_Neg(_x)))),

    # 5. Quotient defining property: if n/a is (already known to be) an
    #    integer, it satisfies the equation division is supposed to solve.
    fl.ForAll('n', fl.ForAll('a', fl.Implies(
        _Int(_Quotient(_n, _a)), fl.Equals(_n, _Times(_a, _Quotient(_n, _a))),
    ))),

    # 6. Quotient uniqueness: any integer solution to that same equation
    #    *is* n/a -- division is the unique inverse of multiplication when
    #    an inverse exists at all.
    fl.ForAll('n', fl.ForAll('a', fl.ForAll('m', fl.Implies(
        fl.And(_Int(_m), fl.Equals(_n, _Times(_a, _m))),
        fl.Equals(_Quotient(_n, _a), _m),
    )))),

    # 7. Times associativity. The first (of eventually several -- see the
    #    module docstring's "not here yet" list) ordinary ring fact this
    #    module characterizes, added because a real proof needed it
    #    (divisibility transitivity: a|b and b|c gives b = a*m and c = b*n
    #    for some integers m, n, so c = (a*m)*n by substitution -- but
    #    concluding a|c needs a witness of the shape a*(something), i.e.
    #    c = a*(m*n), which requires knowing (a*m)*n = a*(m*n)).
    #    AlgebraRule's congruence closure can chain this once it's cited
    #    as a premise, the same as any other equation -- it just can't
    #    produce the fact on its own, since it never assumes anything
    #    about what a cited function symbol *means* (see that rule's own
    #    docstring on exactly this boundary).
    fl.ForAll('x', fl.ForAll('y', fl.ForAll('z', fl.Implies(
        fl.And(fl.And(_Int(_x), _Int(_y)), _Int(_z)),
        fl.Equals(_Times(_Times(_x, _y), _z), _Times(_x, _Times(_y, _z))),
    )))),

    # 8. Left distributivity of Times over Plus -- added the same way
    #    associativity was, because a real proof needed it: divisibility
    #    distributing over sums (a|b and a|c implies a|(b+c)) gives
    #    b = a*m and c = a*n, so b+c = a*m + a*n by congruence -- but
    #    exhibiting b+c as a*(something) needs a*m + a*n = a*(m+n), the
    #    other direction of this same axiom. Deliberately not named
    #    "Distribution"/"Distributivity" in ProofJustification's alias
    #    table -- those names are already the propositional-logic law
    #    (`PropositionalEquivalenceRule`) -- so a proof cites this one the
    #    same way as associativity: write out the quantified axiom itself
    #    as "(Axiom)", then Universal Instantiation down to the needed
    #    ground instance.
    fl.ForAll('x', fl.ForAll('y', fl.ForAll('z', fl.Implies(
        fl.And(fl.And(_Int(_x), _Int(_y)), _Int(_z)),
        fl.Equals(_Times(_x, _Plus(_y, _z)), _Plus(_Times(_x, _y), _Times(_x, _z))),
    )))),
]

INT_DECLARATIONS = [
    pl.Declaration(INT_PREDICATE, pl.DeclarationKind.PREDICATE, arity=1),
    pl.Declaration(PLUS, pl.DeclarationKind.FUNCTION, arity=2),
    pl.Declaration(TIMES, pl.DeclarationKind.FUNCTION, arity=2),
    pl.Declaration(NEG, pl.DeclarationKind.FUNCTION, arity=1),
    pl.Declaration(QUOTIENT, pl.DeclarationKind.FUNCTION, arity=2),
]


class QuotientDefiningPropertyRule(pl.AxiomSchemaRule):
    """From `Int(n/a)`, infer `n = a * (n/a)`: Universal Instantiation of
    axiom 5 above at this proof's own `n`/`a`, plus Modus Ponens, bundled
    into one step so a proof cites it directly instead of spelling out
    both -- the same convenience `ReflexivityRule`/`SymmetryRule`/
    `TransitivityRule` already provide over bare Substitution (see
    `ProofLogic.py`'s section 6.5 commentary).

    Example::

        2.1. n/a is an integer. (Assumption for Conditional Introduction)
        2.2. n = Times(a, n/a). (Quotient Defining Property from 2.1)
    """
    name = "QuotientDefiningProperty"
    premise_arity = 1

    def _expected(self, phi, candidates):
        if not isinstance(phi, fl.Equals):
            return None
        n_term = phi.left
        rhs = phi.right
        if not (isinstance(rhs, tl.FunctionTerm) and rhs.symbol == TIMES and len(rhs.args) == 2):
            return None
        a_term, quotient_term = rhs.args
        if not (isinstance(quotient_term, tl.FunctionTerm) and quotient_term.symbol == QUOTIENT
                and len(quotient_term.args) == 2):
            return None
        if not (pl._ast_eq(quotient_term.args[0], n_term) and pl._ast_eq(quotient_term.args[1], a_term)):
            return None
        return [_Int(quotient_term)]


class QuotientUniquenessRule(pl.AxiomSchemaRule):
    """From `Int(m)` and `n = a * m` (cited in that order), infer `n/a = m`:
    Universal Instantiation of axiom 6 above plus Modus Ponens, bundled
    the same way as `QuotientDefiningPropertyRule`.

    Example::

        3.2. Int(m). (Conjunction Elimination from 3.1)
        3.3. n = Times(a, m). (Conjunction Elimination from 3.1)
        3.4. n/a = m. (Quotient Uniqueness from 3.2, 3.3)
    """
    name = "QuotientUniqueness"
    premise_arity = 2

    def _expected(self, phi, candidates):
        if not isinstance(phi, fl.Equals):
            return None
        quotient_term, m_term = phi.left, phi.right
        if not (isinstance(quotient_term, tl.FunctionTerm) and quotient_term.symbol == QUOTIENT
                and len(quotient_term.args) == 2):
            return None
        n_term, a_term = quotient_term.args
        return [_Int(m_term), fl.Equals(n_term, _Times(a_term, m_term))]


INT_TYPE = pl.Type(
    name="Int",
    predicate=INT_PREDICATE,
    axioms=INT_AXIOMS,
    schema_rules=[QuotientDefiningPropertyRule(), QuotientUniquenessRule()],
    declarations=INT_DECLARATIONS,
)


def divides_formula(a: tl.Term, n: tl.Term, witness_name: str = "__div_witness") -> fl.Formula:
    """`a | n` ("a divides n"), expanded to its defining existential:
    `exists m, (Int(m) and n = a * m)`. Definitional sugar, not a
    primitive -- see the module docstring.
    """
    witness = tl.VariableTerm(witness_name)
    return fl.Exists(witness_name, fl.And(_Int(witness), fl.Equals(n, _Times(a, witness))))


def _split_top_level(text: str, sep: str):
    """Delegates to `ProofParser.split_top_level`, imported lazily (inside
    the function body, not at module load time) to avoid a load-time
    circular import: `ProofParser.default_theory_environment` imports this
    module, so this module cannot import `ProofParser` at the top level
    without the two racing each other during import. By the time any
    parsing function here is actually *called*, both modules have long
    since finished loading, so a deferred import is safe -- the same
    trick `ProofParser.parse_term`/`parse_formula` already used for
    `SetTheory` before `term_parsers`/`nested_formula_parsers` existed.
    """
    import SyLoPy.source.ProofParser as pp
    return pp.split_top_level(text, sep)


def try_parse_int_term(text: str, bound_vars):
    """Term-level sugar: infix `n/a` -> `Quotient(n, a)`."""
    s = text.strip()
    if '/' not in s:
        return None
    parts = _split_top_level(s, '/')
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    import SyLoPy.source.ProofParser as pp
    return _Quotient(pp.parse_term(parts[0], bound_vars), pp.parse_term(parts[1], bound_vars))


def try_parse_int_formula(text: str, bound_vars):
    """Formula-level sugar recognized in *any* position (top of a line or
    nested inside a connective -- see `ProofParser.parse_formula`'s
    `environment` parameter):

      - ``a|n`` / ``a divides n`` -> the divisibility existential above.
      - ``TERM is an integer`` -> ``Int(TERM)``.
    """
    s = ' '.join(text.strip().rstrip('.').split())
    import SyLoPy.source.ProofParser as pp

    if '|' in s:
        parts = _split_top_level(s, '|')
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            a_term = pp.parse_term(parts[0], bound_vars)
            n_term = pp.parse_term(parts[1], bound_vars)
            return divides_formula(a_term, n_term)

    for pattern in (r'^(.+?)\s+divides\s+(.+)$',):
        import re
        m = re.match(pattern, s, flags=re.I)
        if m:
            a_term = pp.parse_term(m.group(1), bound_vars)
            n_term = pp.parse_term(m.group(2), bound_vars)
            return divides_formula(a_term, n_term)

    import re
    m = re.match(r'^(.+?)\s+is\s+an?\s+integer$', s, flags=re.I)
    if m:
        return _Int(pp.parse_term(m.group(1), bound_vars))

    return None


NUMBER_THEORY_ENVIRONMENT = TheoryEnvironment(
    name="number theory",
    nested_formula_parsers=[try_parse_int_formula],
    term_parsers=[try_parse_int_term],
    rules=[QuotientDefiningPropertyRule(), QuotientUniquenessRule()] + list(nt.NAT_TYPE.schema_rules),
    axioms=list(INT_AXIOMS) + list(nt.NAT_AXIOMS),
    declarations=list(INT_DECLARATIONS) + list(nt.NAT_DECLARATIONS),
).extended(st.SET_THEORY_ENVIRONMENT)


if __name__ == "__main__":
    # A minimal end-to-end sanity check in the same spirit as
    # NatThry.py's own self-check: prove that a|n iff n/a is an integer,
    # for an arbitrary a, n, exercising the Quotient axioms, the
    # divisibility sugar, and Existential Introduction/Elimination
    # together.
    import SyLoPy.source.ProofParser as pp

    text = """
1. Let a, n be integers. (Premise)
2. If n/a is an integer then a|n. (Conditional Introduction from subproof below)
begin subproof
 2.1. n/a is an integer. (Assumption for Conditional Introduction)
 2.2. n = Times(a, n/a). (Quotient Defining Property from 2.1)
 2.3. n/a is an integer and n = Times(a, n/a). (Conjunction Introduction from 2.1, 2.2)
 2.4. a|n. (Existential Introduction from 2.3)
end subproof
3. If a|n then n/a is an integer. (Conditional Introduction from subproof below)
begin subproof
 3.1. a|n. (Assumption for Conditional Introduction)
 3.2. Let m be an object. (Declare)
 3.3. n/a is an integer. (Existential Elimination from 3.1, subproof below)
 begin subproof
  3.3.1. Int(m) and n = Times(a, m). (Assumption for Existential Elimination)
  3.3.2. Int(m). (Conjunction Elimination from 3.3.1)
  3.3.3. n = Times(a, m). (Conjunction Elimination from 3.3.1)
  3.3.4. n/a = m. (Quotient Uniqueness from 3.3.2, 3.3.3)
  3.3.5. n/a is an integer. (Substitution from 3.3.2, 3.3.4)
 end subproof
end subproof
4. a|n if and only if n/a is an integer. (Biconditional Introduction from 2, 3)
"""
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries)
    ok, err = proof.check_detailed()
    print("NumberTheory self-check:", "PASS" if ok else f"FAIL ({err})")




