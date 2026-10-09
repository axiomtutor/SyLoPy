# SyLoPy Agent Collaboration Notes

Purpose: keep durable decisions, active work, and low-conflict task handoffs in one short place. This is a live coordination branch, **not a branch to merge into `master`**. The owner has final authority; explicit owner decisions override proposals below. Claude has usually been the primary implementer, with ChatGPT and Copilot contributing reviews and independent work.

## Project model and working rules

The pipeline is:

```text
surface proof -> parse -> elaborate -> core entries -> kernel validation
```

- Prefer theory-local parsers, elaborators, declaration recipes, and desugaring over generic parser special cases or new kernel primitives.
- `ProofContext` owns source-level lexical bindings during elaboration. Kernel `LabelScope` and `DeclarationScope` remain separate, validation-time structures; don't merge the layers just to remove overlap.
- Treat `parse_oracle/*.txt` as the independent language specification. For new syntax, write intended readings and rejection cases first; expected formulas should use plain core logic, not mirror implementation details. A disagreement calls for reviewing the specification or parser, not weakening a case without justification.
- Before coding, check current `master`, open PRs, and active branches; state file ownership and keep changes small. Do not update project-status counts opportunistically.
- `./run_tests.sh` is the canonical full test command. One known failure remains intentionally pending: `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. The corresponding fixture is ahead of implementation and fails because it uses `WLOG`, `Mutatis mutandis`, and `Uniqueness`. Do not mask this with `xfail` unless the owner approves.

## Settled decisions and boundaries

**Witness introduction and set axioms**
- `Let Y be such a set. (Existence from L)` is elaboration sugar over an already-cited existential: declare the chosen name in the current lexical scope and assert the existential body instantiated at it. It is not a new kernel rule.
- Axiom citations remain ordinary existential formulas. Named axiom rules for Pairing, Union, Power Set, and Infinity should check formula shape but must not introduce names.
- The direct-witness Pairing form from PR #2 remains on `master` as a legacy special case; the owner explicitly rejected it as the design and instructed agents **not to extend it** to Union, Power Set, or Infinity. Do not build a generic `WitnessElaboration` abstraction around an assumed family of such rules.

**Uniqueness**
- Unique existence is intended as sugar for `exists Y, (P(Y) and forall X, (P(X) -> X = Y))`, not a new AST connective.
- Previous status note: Claude was implementing this with kernel/justification changes. Refresh this status before touching any shared file.

**WLOG**
- WLOG begins at its assertion and extends to the end of the current proof block; it has no separately delimited subproof syntax.
- The accepted design is replay plus revalidation, not an unchecked symmetry assertion. The first implementation target is equality disjuncts that differ in exactly one constant term.
- During replay, substitute formulas and declarations; remap citations inside the region to replayed counterparts. An outside citation must map to an already-visible matching transformed fact; never use a future line or a closed sibling scope. Revalidate each transformed line with its ordinary rule.
- WLOG implementation is **not authorized** without explicit owner approval. The earlier proposal to prepare informational acceptance fixtures also requested owner approval first; leave it alone until that approval is given.

**Other reserved work**
- Do not implement named ZFC axiom rules, `Set property, N[, M]`, Infinity, or `Mutatis mutandis` without explicit owner approval.
- Do not edit `source/ProofLogic.py`, `source/ProofJustification.py`, `pytest_tests/test_set_phrase_parsing.py`, or status/count lines in `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` while Claude says they are active. Confirm ownership/status first.

## Completed independent ChatGPT contributions

All of these PRs have been merged:

- [PR #3 — Set-theory parser semantic oracle](https://github.com/axiomtutor/SyLoPy/pull/3): independent expected readings and rejection cases for set-theory phrases.
- [PR #4 — Set-bounded quantifier syntax](https://github.com/axiomtutor/SyLoPy/pull/4): theory-level sugar for bounded universal and existential quantifiers; no kernel change.
- [PR #5 — Bounded-quantifier oracle cases](https://github.com/axiomtutor/SyLoPy/pull/5): scope, nesting, connective composition, and rejection cases for the new syntax.
- [PR #6 — Executable proof-file format examples](https://github.com/axiomtutor/SyLoPy/pull/6): a test validates marked complete proofs from `docs/PROOF_FILE_FORMAT.md` and checks concrete justification examples.
- [PR #7 — Number-theory parser oracle cases](https://github.com/axiomtutor/SyLoPy/pull/7): independent readings for integer assertions, quotient notation, divisibility, compound terms, and nested logical contexts.

CI for these changes continued to report the single known ZFC-fixture failure; the new tests/oracle cases passed. The full test suite should be rerun against current `master` when assessing later work.

## Questions for the owner / Claude / Copilot

1. **Is `Uniqueness` now complete or still active?** Please state the current branch/PR and reserved files, and update this handoff if the old status is stale.
2. **Has the owner approved any WLOG test-preparation work?** Unless the answer is yes, I will continue to leave WLOG, its fixtures, and the axiom-rule backlog untouched.
3. **What independent work should ChatGPT take next?** Please suggest 2–4 concrete, bounded tasks based on the current repository—not merely top-level TODO headings. For each, specify target files, why it does not overlap current work, relevant tests, and whether it is approved to start.

I am available for work that keeps shared implementation files free—for example, a new oracle/test file for existing behavior, an isolated informational proof example, or a bounded documentation/API task after shared docs are released. Please also identify any branch or file to avoid.

## Handoff protocol

Reply in this file with current status and task assignments. ChatGPT should branch from the latest `master`, implement only the assigned independent task, run the narrow tests and then the full suite, and report the PR plus test results. The owner deletes merged branches.