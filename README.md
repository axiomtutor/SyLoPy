# SyLoPy

SyLoPy is a proof-language checker for natural-deduction mathematics. It accepts
proofs written in a human-readable surface syntax, elaborates them into a core
proof representation, and validates the result with the kernel in
`source/ProofLogic.py`.

The project currently has some implementations for first-order logic, set theory, order theory, arithmetic, and number theory.
It should soon develop features for more mathematical subjects.

## Current status

At the time of writing, the project is in a stable state.

- `./run_tests.sh` passes with 368 passing Python tests.
- All enforced proof fixtures pass.
- All informational proof fixtures pass.

This is the key fact to keep in mind for planning: the core parser,
elaboration pipeline, and kernel rule set are working as a coherent system.
The remaining work is mostly consolidation, cleanup, and feature expansion,
not repairing a broken proof engine.

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

The parser facade lives in `source/ProofParser.py`, while the elaboration logic
and theory plumbing live around `source/ProofElaboration.py`. Source-origin
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

The project now treats declarations, assumptions, labels, arbitrary bindings,
and nested scopes as explicit lexical state through `source/ProofContext.py`.
This aligns elaboration with the kernel's scoping behavior and avoids the old
pattern of reconstructing visibility rules independently in multiple places.

## Where the project is going

The current direction is not a rewrite; it is a consolidation phase.
The main architectural goal is to make the proof context the single source of
truth for lexical bookkeeping while reducing legacy duplication in the
elaborator and preserving the validated proof corpus.

Short term, the project is heading toward:

- a cleaner elaboration model with `ProofContext` fully authoritative;
- less duplicated state between elaboration and validation;
- a clearer public API for parsing and checking proofs;
- broader theory support without breaking the existing proof corpus.

In other words, the project is already functionally solid. The next step is to
make it easier to extend and maintain.

## Next work priorities

1. Consolidate remaining elaboration bookkeeping.
   - Remove duplicated declaration/label state that still exists alongside
     `ProofContext`.
   - Confirm that elaboration and validation use the same lexical semantics.

2. Tighten the public-facing API.
   - Keep the parser and proof-checking entry points clear and documented.
   - Document canonical usage patterns and expected outputs for users.

3. Expand theory modules and surface syntax.
   - Add richer algebraic and order-theoretic features without destabilizing the
     existing core logic.
   - Prefer theory-local syntax and declaration recipes over generic ad hoc
     elaboration hacks.

4. Continue proof-corpus growth.
   - Add more examples and end-to-end fixtures for edge cases, not just the core
     rules already covered.
   - Keep the existing enforced proof corpus as the regression floor.

## Project structure

- `source/ProofParser.py` — public proof parsing and elaboration facade.
- `source/ProofElaboration.py` — surface representation, theory environment,
  and elaboration logic.
- `source/ProofLogic.py` — proof kernel, rules, axioms, and validation.
- `source/ProofContext.py` — lexical scoping for declarations, labels, and
  assumptions.
- `source/validate_all_proofs.py` — multi-proof file runner and theorem promotion.
- `tests/` and `pytest_tests/` — regression tests and proof fixtures.
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
