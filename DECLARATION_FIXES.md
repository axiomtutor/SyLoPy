# Declaration and Premise Support

This document records the declaration-system implementation that established
scoped declarations and declaration-aware premises. It is historical design
and implementation documentation; current verification results are produced
by the repository test suite and GitHub Actions rather than recorded here as
a hard-coded test count.

Implemented behavior:

- `Let ... be ...` declaration syntax.
- Declaration-only `(Declare)` and `(Declaration)` lines.
- Declarations attached to premise formulas through `such that:`.
- Lexical declaration scopes for nested subproofs.
- Unconditional undeclared-symbol checking: every constant, function, and
  predicate symbol must be declared -- by the proof itself (`Let ...`,
  `(Declare)`) or by a theory module's built-in `declarations` -- with no
  opt-out.
- Declaration kind, arity, conflict, and out-of-scope errors.
- Theory-provided declarations for natural-number and set-theory vocabulary.
- Arbitrary constants as local object declarations.
- Bundled premise formulas and hybrid subproof citations.

The declaration work is integrated with the surface-proof elaboration pipeline
described in `ELABORATION_ARCHITECTURE.md`.
