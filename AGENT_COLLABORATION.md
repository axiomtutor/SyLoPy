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

- Copilot added `parse_oracle/number_theory_edge_cases.txt` on `master` (commit `16dec2e`): 13 cases covering negation, divisibility inside connectives and quantifiers, nested quotient terms, biconditionals, and malformed divisibility/quotient syntax. They complement the existing number-theory oracle rather than changing parser behavior. ChatGPT reviewed them as a useful, well-scoped addition (8.5/10); retain them.
- The latest observed full test run after the recent test additions reported **703 passed, 1 failed**. The sole failure remains `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`; it is expected to remain pending because the fixture uses the unimplemented `WLOG`, `Mutatis mutandis`, and `Uniqueness`. All enforced proof fixtures pass (48/48). [Run](https://github.com/axiomtutor/SyLoPy/actions/runs/37883443051).
- PRs #3–#8 are merged. Recent independent work has strengthened the surface-language specification and executable examples without adding kernel rules. This is valuable regression coverage, while the main set-theory design backlog remains intentionally gated by owner approval.
- The counts in `README.md` and `todos.txt` are older than the current run. Do not edit those status/count lines opportunistically; the owner can decide when to refresh the documentation.
- A possible next test-only audit is lexical capture/shadowing in theory-generated formulas, particularly whether a generated divisibility witness name can collide with a legal source variable. First construct a focused reproducer/oracle expectation; do not change theory implementation until the behavior is demonstrated and file ownership is clear.



## Questions for the owner / Claude / Copilot

Please answer briefly here so this remains the compact source of truth.

1. **Uniqueness status/ownership:** Is `Uniqueness` active or complete? If active, give the branch/PR and files Claude has reserved.
2. **WLOG approval:** Has the owner explicitly authorized WLOG implementation or test preparation? Until yes, leave WLOG and the reserved axiom backlog untouched.
3. **Next independent tasks:** Please assign ChatGPT 2–4 bounded tasks grounded in the current tree. For each, name target files, explain why it does not overlap active work, give a test command, and state whether implementation is approved.
4. **Potential test-only audit:** Should ChatGPT investigate possible generated-witness name capture in number-theory syntax, without changing `source/NumberTheory.py`? Identify any ownership boundary.
5. **Other conflicts:** Which files/branches are currently reserved by Claude or Copilot, and what should ChatGPT avoid?

I'm best placed to take work that leaves shared implementation files free: independent oracle cases, isolated proof examples, or bounded documentation/API tasks once their files are available.


## Handoff protocol

Reply in this file with current status and task assignments. ChatGPT should branch from the latest `master`, implement only the assigned independent task, run the narrow tests and then the full suite, and report the PR plus test results. The owner deletes merged branches.