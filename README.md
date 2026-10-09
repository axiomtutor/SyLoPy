# SyLoPy

SyLoPy is a proof-language checker for natural-deduction mathematics. It accepts
proofs written in a human-readable surface syntax, elaborates them into a core
proof representation, and validates the result with the kernel in
`source/ProofLogic.py`.

The project currently has some implementations for first-order logic, set theory, order theory, arithmetic, and number theory.
It should soon develop features for more mathematical subjects.

## Current status

At the time of writing, the project is in a stable state, with one known,
tracked exception.

- 766 Python tests; 765 pass, 1 known failure (a stale fixture test,
  tracked in `todos.txt`).
- All enforced proof fixtures pass.
- All but one informational proof fixture pass (the same known issue: a
  fixture written ahead of an agreed-but-unimplemented feature).

This is the key fact to keep in mind for planning: the core parser,
elaboration pipeline, and kernel rule set are working as a coherent system.
The remaining work is mostly consolidation, cleanup, and feature expansion,
not repairing a broken proof engine. See `todos.txt` for the detailed,
living task list, including design decisions that are agreed but not yet
implemented.

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
cite earlier results by name without inheriting local proof structure.

This is deliberate: proof reuse across proofs is explicit and theory-scoped,
not a shared lexical environment.

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

3. Expand theory modules and surface syntax.
   - Add richer algebraic and order-theoretic features without destabilizing the
     existing core logic.
   - Prefer theory-local syntax and declaration recipes over generic ad hoc
     elaboration hacks.
   - Implement the agreed set-theory design backlog (named axiom-citation
     rules, a checked WLOG rule, and more) — see `todos.txt` for the full,
     current design.

4. Continue proof-corpus growth.
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
