# SyLoPy

SyLoPy is a proof-language checker for natural-deduction mathematics. It accepts
proofs written in a human-readable surface syntax, elaborates them into a core
proof representation, and validates the result with the kernel in
`source/ProofLogic.py`.

The project currently has some implementations for first-order logic, set theory, order theory, arithmetic, and number theory.
It should soon develop features for more mathematical subjects.

## Current status

The last recorded baseline comparison against `master` at
[`bc990e5`](https://github.com/axiomtutor/SyLoPy/commit/bc990e57ce71f9e607ff8e227399a6921289d40a)
is documented in [PR #67](https://github.com/axiomtutor/SyLoPy/pull/67). On
Python 3.12, that baseline had 1,138 passing Python tests, 1 failing test, and
2 expected failures. The failing test is:
`pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`.
Coverage passed, and all 80 enforced proof fixtures passed. The informational
proof corpus had 59 passing fixtures out of 60.

The single known failure is the deliberately deferred ZFC fixture: it reaches
the `WLOG` / `Mutatis mutandis` steps, which remain unimplemented on
`master`. Do not interpret the informational fixture failure as an enforced
proof-corpus regression.

These figures describe that baseline comparison, not a guarantee that counts
remain fixed as tests and fixtures are added. For the latest run, consult
[GitHub Actions](https://github.com/axiomtutor/SyLoPy/actions).

The core parser, elaboration pipeline, and kernel rule set are working as a
coherent system. Remaining work includes consolidation, cleanup, and feature
expansion. See `todos.txt` for the detailed task list and the design decisions
that constrain unfinished work.

## Proof-processing pipeline

```text
natural proof text
        ↓
SurfaceProof AST with source-span metadata
        ↓
elaboration / desugaring
        ↓
ElaboratedEntries
        ↓
ProofLogic proof validation
```

The parser, elaborator and `ProofParser.elaborate_proof` live in
`source/ProofParser.py`; `source/ProofElaboration.py` holds the surface AST,
`ElaboratedEntries` and `TheoryEnvironment` data types they share. Source-origin
metadata is preserved all the way through validation so diagnostics can still be
mapped back to the user's original proof text.

## What the project already supports

### Set theory and proof syntax

The surface language supports declarations, assumptions, subproofs, quantifiers,
and set-theoretic reasoning such as subset proofs and membership arguments.

```text
1. Let X be any set.
2. The empty set is a subset of X.
 2.1. Let a in the empty set.
 2.2. a is not in the empty set.
 2.3. a is in X.
```

Set theory reads a good deal of ordinary mathematical wording, all of it
sugar for plain first-order formulas:

```text
Y = {a, b}                          x is in {a, b}          x is a or b
Y = {u in X: P(u)}                  Y = {F(x): x in X}      S contains exactly a, b and c
X subseteq Y                        Let X and Y be sets.
there exists a unique set {a, b} that contains exactly a and b
```

Citations may be written `Modus Ponens from 2, 3` or `Modus Ponens, 2, 3`.

Set theory is the active frontier: the ZFC axiom-citation design (named
axiom rules, WLOG, unique existence) is written up in `todos.txt`; the syntax
above is implemented, and so is the rule `Uniqueness`. The rules `WLOG` and
`Mutatis mutandis` are not.

### Number theory

`source/NumberTheory.py` extends the base logic with natural-number reasoning,
integer closure, quotient notation, and divisibility rules.

### Discrete mathematics

`source/DiscreteMath.py` adds relation declarations and relation-property rules,
including reflexive, irreflexive, symmetric, antisymmetric, asymmetric,
transitive, total/connected, and the common derived relation families such as
partial orders and equivalence relations.

### Theorem promotion and reuse

`ProofLogic.promote_theorem(...)` converts a checked proof into a reusable
inference rule. The multi-proof file runner in `source/validate_all_proofs.py`
automatically promotes titled proofs within a file, which allows later proofs to
cite earlier results by name without inheriting local proof structure. A theorem
with premises is cited with the lines that state them, as in
`(Pair transport from 4, 5)`; see `docs/PROOF_FILE_FORMAT.md`.

This is deliberate: proof reuse across proofs is explicit and theory-scoped,
not a shared lexical environment.

A promoted theorem carries every hypothesis its proof took for granted -- premise
lines at any depth, declarations that state a formula, witness lines -- as
premises, so it cannot be cited where they are not supplied. It also records
the axioms its proof cited and the rules it used beyond the standard logical
ones, and can only be cited in a proof that lists those axioms and allows those
rules: a theorem is a theorem of the theory it was proved in. An explicit
conclusion must be a formula the proof derived at the top level, and generalized
names must be objects the proof declared at its top level. Promotion refuses a
proof that relied on structure recorded in a declaration and stated by no
formula (a relation declared symmetric); state the property as a premise
formula instead. See `todos.txt`, item 8.

### Proof context and lexical scoping

`source/ProofContext.py` is the lexical environment used during elaboration.
It tracks declarations, assumptions, proof-line labels, arbitrary bindings,
and nested scopes.

The kernel deliberately does not use `ProofContext` directly. During validation,
`source/ProofLogic.py` uses its own `LabelScope` and `DeclarationScope` over the
already-elaborated proof entries. The two layers implement the same relevant
lexical-scope semantics, but keeping them separate preserves the boundary
between elaboration and kernel validation.

## Where the project is going

The current direction is not a rewrite; it is a consolidation phase.
`ProofContext` is the lexical environment used during elaboration. The kernel
retains independent scope structures for validation of the elaborated proof.
This separation is intentional: the elaborator resolves source-level bindings,
while the kernel validates the resulting proof representation.

As new theory features are designed, the guiding principle is: most things
beyond the level of pure logic should be sugar. New mathematical convenience
— a notation, a derived fact like "exists a unique X" — should desugar into
forms the kernel already understands rather than growing the kernel itself.
Kernel/AST changes are reserved for genuinely new logical primitives.

Short term, the project is heading toward:

- a clearer public API for parsing and checking proofs;
- broader theory support without breaking the existing proof corpus;
- continued proof-corpus growth and regression coverage.

In other words, the project is already functionally solid. The next step is to
make it easier to extend and maintain.

## Next work priorities

1. Tighten the public-facing API.
   - Keep the parser and proof-checking entry points clear and documented.
   - Document canonical usage patterns and expected outputs for users.

2. Expand theory modules and surface syntax.
   - Add richer algebraic and order-theoretic features without destabilizing the
     existing core logic.
   - Prefer theory-local syntax and declaration recipes over generic ad hoc
     elaboration hacks.
   - Implement the agreed set-theory design backlog (named axiom-citation
     rules, a checked WLOG rule, and more) — see `todos.txt` for the full,
     current design.

3. Continue proof-corpus growth.
   - Add more examples and end-to-end fixtures for edge cases, not just the core
     rules already covered.
   - Keep the existing enforced proof corpus as the regression floor.

## Project structure

- `source/ProofParser.py` — proof parser and elaborator (public entry point).
- `source/ProofParserPolicy.py`, `source/LineBreakSyntax.py` — small
  language-policy and line-break syntax extensions installed on the parser.
- `source/ProofElaboration.py` — shared data types: surface AST, source spans,
  `ElaboratedEntries`, `TheoryEnvironment`.
- `source/ProofLogic.py` — proof kernel, rules, axioms, and validation.
- `source/ProofContext.py` — elaboration-time lexical scoping for declarations,
  labels, assumptions, and arbitrary/fresh bindings.
- `source/ProofJustification.py` — parses proof-line justifications (e.g.
  "Modus Ponens from 2, 3") into rule citations.
- `source/SetTheory.py`, `source/NatThry.py`, `source/NumberTheory.py`,
  `source/DiscreteMath.py` (rules in `DiscreteMathCore.py`), plus
  `TermLogic.py` / `FormulaLogic.py` for terms and formulas —
  per-subject theory modules and logic building blocks that extend the base logic (see "What the
  project already supports").
- `source/validate_all_proofs.py` — multi-proof file runner and theorem promotion.
- `tests/` — enforced proof fixtures (plus `tests/setTheoryProofs`, which is
  informational); `source/testProofs/` — informational fixtures.
- `parse_oracle/` — independent surface-to-formula cases for the parser,
  checked by `pytest_tests/test_parse_oracle.py`.
- `pytest_tests/` — Python unit/integration tests. The code imports itself as
  `SyLoPy.source...`; `pytest_tests/support.py` and `./run_tests.sh` make that
  work whatever the checkout directory is called.
- `completion/run_tests.bash` — shell completion for the test runner.

## Recommended Python API

For ordinary surface-language proofs, `ProofParser.check_proof_text` is the direct entry point. It parses the proof text, elaborates its notation, validates the resulting proof, and returns `(ok, error)`; `error` is a structured `ValidationError` when checking fails and `None` on success.

<!-- python-api-test: surface-check -->
```python
import SyLoPy.source.ProofParser as pp
import SyLoPy.source.SetTheory as st

proof_text = """1. Let P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption for Conditional Introduction)
 2.2. P. (Reiteration from 2.1)
end subproof
"""

ok, error = pp.check_proof_text(
    proof_text,
    environment=st.SET_THEORY_ENVIRONMENT,
)
if not ok:
    print(error)
```

Pass the theory environment deliberately when you want a specific theory boundary. Examples include `SET_THEORY_ENVIRONMENT`, `NUMBER_THEORY_ENVIRONMENT`, and `DISCRETE_MATH_ENVIRONMENT`. Omitting `environment` selects `ProofParser.default_theory_environment()`, which combines the built-in environments that are available. The chosen environment's axioms, rules, and declarations are carried in `ElaboratedEntries` and merged by `ProofLogic.Proof` during checking.

For source inspection, structured diagnostics, or theorem promotion, use the pipeline stages directly:

<!-- python-api-test: theorem-promotion -->
```python
import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.SetTheory as st

import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.TermLogic as tl

proof_text = """1. Let a be any object. (Declaration)
2. a = a. (Reflexivity)
"""

entries, raw_lines = pp.parse_proof_text(
    proof_text,
    environment=st.SET_THEORY_ENVIRONMENT,
)
proof = pl.Proof(entries)
ok, error = proof.check_detailed()
if not ok:
    raise ValueError(str(error))

identity = pl.promote_theorem("Identity", proof)

b = tl.ConstantTerm("b", "b")
b_equals_b = fl.Equals(b, b)
use_entries = [
    ("1", None, ("declare", [
        pl.Declaration("b", pl.DeclarationKind.OBJECT),
    ])),
    ("2", b_equals_b, ("rule", identity, [])),
]
use = pl.Proof(use_entries, rules=pl.default_rules() + [identity])
ok, error = use.check_detailed()
if not ok:
    raise ValueError(str(error))
```

`parse_proof_text` returns elaborated entries plus the original raw lines. `Proof.check_detailed()` returns the same structured result shape as `check_proof_text`; `Proof.check()` is the compatibility option when a string message is enough. Promotion validates the source proof and creates a reusable `TheoremRule`; its hypotheses and nonstandard rule / axiom requirements are carried with it. Only formulas derived at the top level can be selected as theorem conclusions, and only top-level object declarations can be generalized.

For surface-language proof reuse across titled proof blocks, see the informational example [`source/testProofs/theoremPromotion.txt`](source/testProofs/theoremPromotion.txt). Its first proof establishes identity for an arbitrary object; the following proof cites that title for a different object.

For a compact quantifier example that instantiates universal premises at an arbitrary object and then generalizes the result, see [`source/testProofs/quantifierReasoning.txt`](source/testProofs/quantifierReasoning.txt).

When constructing a proof directly from core entries rather than from surface text, supply its theory resources explicitly. The `Type` helper provides a reusable package for fixed type vocabularies:

<!-- python-api-test: core-type-resources -->
```python
import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.TermLogic as tl
from SyLoPy.source.NatThry import NAT_TYPE

axioms, schema_rules = pl.combine_types(NAT_TYPE)
declarations = pl.combine_type_declarations(NAT_TYPE)

zero_is_nat = fl.AtomicFormula(
    "Nat", [tl.ConstantTerm("Zero", "Zero")]
)
entries = [
    ("1", zero_is_nat, ("axiom",)),
    ("2", zero_is_nat, ("rule", pl.ReiterationRule(), ["1"])),
]
proof = pl.Proof(
    entries,
    axioms=axioms,
    rules=pl.default_rules() + schema_rules,
    declarations=declarations,
)
ok, error = proof.check_detailed()
if not ok:
    raise ValueError(str(error))
```

Use the `ElaboratedEntries` path for natural-language proofs and the explicit core-resource path when you are building validator entries yourself.

## Running the project

```bash
./run_tests.sh
```

Suite names can be listed or selected when needed:

```bash
./run_tests.sh --list-suites
./run_tests.sh --suite testProofsDeclared --verbose
```

For Bash completion:

```bash
source completion/run_tests.bash
```

## Summary

SyLoPy is a working proof-language checker with a mature core, a validated proof
corpus, and a clear next phase: architecture cleanup and extension. After that, develop the set theory features until it can prove core set theory theorems.
