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
- [PR #8 — Theorem promotion and subproof example](https://github.com/axiomtutor/SyLoPy/pull/8): end-to-end coverage of a proof with a subproof, promotion to a reusable theorem, a later theorem instance, and rejection of a wrong-shape instance.

## Latest progress and assessment (2026-10-09)

- PRs #3–#10 are now merged. They add independent parser specifications, bounded-quantifier syntax, executable proof-file documentation checks, number-theory coverage, theorem-promotion/subproof coverage, and the generated-binder capture fixes described below.
- Copilot's follow-up was added to `master` in commit [`1d333e0`](https://github.com/axiomtutor/SyLoPy/commit/1d333e0c1c8fd85341d65d99a2b88efaa96027fb). It recommends continuing with specification/regression work rather than changing the parser/elaborator/kernel architecture. Candidate topics include discrete-math relation declarations, order-theory examples, targeted negative oracle cases, documentation drift checks, and scope/theorem-promotion tests.
- [PR #9 — Prevent variable capture in divisibility sugar](https://github.com/axiomtutor/SyLoPy/pull/9) fixed the generated `__div_witness` colliding with a variable in a divisor or dividend. It was merged in [`1cbfc7f`](https://github.com/axiomtutor/SyLoPy/commit/1cbfc7f6980c682f8555daab92b14c6c3d43d285).
- [PR #10 — Prevent variable capture in generated set-theory binders](https://github.com/axiomtutor/SyLoPy/pull/10) fixed three collisions: `X has no elements`, the set-display equality fallback binder, and `subset_formula`'s default binder. Four independent oracle cases cover them. It was merged in [`94893c7`](https://github.com/axiomtutor/SyLoPy/commit/94893c76dca7bc850381add42449d24c9339f140).
- The generated-binder audit found that hard-coded variable names in theory-level desugaring can change formula meaning when a legal source variable has the same name. The known full-suite failure remains `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, which depends on the not-yet-implemented `WLOG`, `Mutatis mutandis`, and `Uniqueness`.
- The branch `chatgpt-agent-guidance` remains a coordination-only branch and is deliberately not merged into `master`. This file is stale until this post-merge status update is pushed; future notes should continue to distinguish coordination commits from code PRs.
- ChatGPT took the test-only relation-declaration task and opened [PR #11 — Expand relation declaration parsing tests](https://github.com/axiomtutor/SyLoPy/pull/11). It changes only `pytest_tests/test_discrete_math.py`: all relation aliases, case/whitespace normalization, property composition, `connected` as totality, and missing-carrier rejection. CI run #347 completed with 714 passed and one known failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`; the enforced proof fixture corpus passed 48/48. The new relation-declaration tests are passing. Local pytest could not run because the container could not resolve GitHub. Avoid duplicating edits to this test file while PR #11 is being checked.
- A separate rule audit found that `RelationTotalityRule` checked that its two membership premises used the same carrier, but not that this carrier matched the total relation's declared carrier. [PR #12 — Restrict relation totality to its declared carrier](https://github.com/axiomtutor/SyLoPy/pull/12) adds that check and focused regression coverage in a separate source file/test module. CI run #353 had 714 passed and the one already-known ZFC fixture failure; the enforced proof fixture corpus passed 48/48. This PR does not touch the files in PR #11.
- After the current PRs are resolved, other viable tasks are a standalone README-example drift check or additional negative oracle cases. Do not edit project status counts in README/todos opportunistically; the owner can decide when to refresh them.

## Questions for the owner / Claude / Copilot

Please answer briefly here so this remains the compact source of truth.

1. **Uniqueness status/ownership:** Is `Uniqueness` active or complete? If active, give the branch/PR and files Claude has reserved.
2. **WLOG approval:** Has the owner explicitly authorized WLOG implementation or test preparation? Until yes, leave WLOG and the reserved axiom backlog untouched.
3. **Next independent tasks:** Please assign ChatGPT 2–4 bounded tasks grounded in the current tree. For each, name target files, explain why it does not overlap active work, give a test command, and state whether implementation is approved.
4. **Next-task assignment:** Is the proposed test-only relation-declaration audit in `pytest_tests/test_discrete_math.py` acceptable, or does Claude have a conflicting task? If conflicting, assign one of the other bounded options recorded above.
5. **Other conflicts:** Which files/branches are currently reserved by Claude or Copilot, and what should ChatGPT avoid?

I'm best placed to take work that leaves shared implementation files free: independent oracle cases, isolated proof examples, or bounded documentation/API tasks once their files are available.


## Handoff protocol

Reply in this file with current status and task assignments. ChatGPT should branch from the latest `master`, implement only the assigned independent task, run the narrow tests and then the full suite, and report the PR plus test results. The owner deletes merged branches.