


# Declaration and Premise Support

This project version includes scoped declarations and declaration-aware premises.

Implemented behavior:

- `Let ... be ...` declaration syntax.
- Declaration-only `(Declare)` and `(Declaration)` lines.
- Declarations attached to premise formulas through `such that:`.
- Lexical declaration scopes for nested subproofs.
- Unconditional undeclared-symbol checking: every constant, function, and
  predicate symbol must be declared -- by the proof itself (`Let ...`,
  `(Declare)`) or by a theory module's built-in `declarations` -- with no
  opt-out. There used to be a `require_declared_constants` flag defaulting
  to off; it has been removed rather than defaulted on, since a checker
  that can silently skip checking declarations isn't one you can trust by
  default. `ProofLogic.infer_declarations`/`collect_formulas_from_entries`
  exist for the one legitimate case this makes harder: constructing
  `declarations=` programmatically for hand-assembled entries instead of
  parsed text.
- Declaration kind, arity, conflict, and out-of-scope errors.
- Theory-provided declarations for natural-number and set-theory vocabulary.
- Arbitrary constants as local object declarations.
- Bundled premise formulas and hybrid subproof citations.

The declaration work is now integrated with the surface-proof elaboration pipeline described in `ELABORATION_ARCHITECTURE.md`.

Verified result: 271 tests passed.




