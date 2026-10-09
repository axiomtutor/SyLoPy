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
- `./run_tests.sh` is the canonical full test command. One known failure remains intentionally pending: `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. The corresponding fixture is ahead of implementation: it stops at its first `WLOG` line, and also uses `Mutatis mutandis`. Do not mask this with `xfail` unless the owner approves.

## Settled decisions and boundaries

**Witness introduction and set axioms**
- `Let Y be such a set. (Existence from L)` is elaboration sugar over an already-cited existential: declare the chosen name in the current lexical scope and assert the existential body instantiated at it. It is not a new kernel rule.
- Axiom citations remain ordinary existential formulas. Named axiom rules for Pairing, Union, Power Set, and Infinity should check formula shape but must not introduce names.
- The direct-witness Pairing form from PR #2 remains on `master` as a legacy special case; the owner explicitly rejected it as the design and instructed agents **not to extend it** to Union, Power Set, or Infinity. Do not build a generic `WitnessElaboration` abstraction around an assumed family of such rules.

**Uniqueness**
- Landed on `master` in `2a4cebd` as the kernel rule `UniquenessRule`. Its conclusion is the ordinary `exists Y, (P(Y) and forall X, (P(X) -> X = Y))` form, not a new AST connective.
- It is sound only when the generalized constant is arbitrary, so it uses a new opt-in hook, `applies_in_context`, and a `RuleContext` (hypotheses in force, arbitrary constants). Design note: `todos.txt`, item "`Uniqueness, N, M`".

**WLOG**
- WLOG begins at its assertion and extends to the end of the current proof block; it has no separately delimited subproof syntax.
- The accepted design is replay plus revalidation, not an unchecked symmetry assertion. The first implementation target is equality disjuncts that differ in exactly one constant term.
- During replay, substitute formulas and declarations; remap citations inside the region to replayed counterparts. An outside citation must map to an already-visible matching transformed fact; never use a future line or a closed sibling scope. Revalidate each transformed line with its ordinary rule.
- WLOG implementation is **not authorized** without explicit owner approval. The earlier proposal to prepare informational acceptance fixtures also requested owner approval first; leave it alone until that approval is given.

**Other reserved work**
- Do not implement named ZFC axiom rules, `Set property, N[, M]`, Infinity, or `Mutatis mutandis` without explicit owner approval.
- As of `2a4cebd` Claude has no files reserved. `source/ProofLogic.py` and `source/ProofJustification.py` are kernel files: add tests freely, but send kernel fixes through Claude or the owner. The counts in `README.md`, `todos.txt` and `ARCHITECTURE_STATUS.md` were refreshed in `2a4cebd`; do not update them opportunistically.

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
- The generated-binder audit found that hard-coded variable names in theory-level desugaring can change formula meaning when a legal source variable has the same name. The known full-suite failure remains `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, which depends on the not-yet-implemented `WLOG` and `Mutatis mutandis` (`Uniqueness` landed in `2a4cebd`).
- The branch `chatgpt-agent-guidance` remains a coordination-only branch and is deliberately not merged into `master`. Keep its handoff notes current as code PRs evolve, and distinguish coordination commits from code PRs.
- ChatGPT took the test-only relation-declaration task and opened [PR #11 — Expand relation declaration parsing tests](https://github.com/axiomtutor/SyLoPy/pull/11). It changes only `pytest_tests/test_discrete_math.py`: all relation aliases, case/whitespace normalization, property composition, `connected` as totality, and missing-carrier rejection. CI run #347 completed with 714 passed and one known failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`; the enforced proof fixture corpus passed 48/48. The new relation-declaration tests are passing. Local pytest could not run because the container could not resolve GitHub. Avoid duplicating edits to this test file while PR #11 is being checked.
- A separate rule audit found that `RelationTotalityRule` checked that its two membership premises used the same carrier, but not that this carrier matched the total relation's declared carrier. [PR #12 — Restrict relation totality to its declared carrier](https://github.com/axiomtutor/SyLoPy/pull/12) adds that check and focused regression coverage in a separate source file/test module. CI run #353 had 714 passed and the one already-known ZFC fixture failure; the enforced proof fixture corpus passed 48/48. This PR does not touch the files in PR #11.
- [PR #13 — Make documented subproof examples executable](https://github.com/axiomtutor/SyLoPy/pull/13) marks the explicit conditional-introduction and proof-by-cases examples in `docs/PROOF_FILE_FORMAT.md` as runnable valid proofs. The examples now include their premises and real inference steps; the existing docs-test harness runs them, without adding a new test mechanism. The first run exposed an undeclared-formula issue in the conditional-introduction example; the example was corrected to declare its closed formulas. CI run #361 then completed with 710 passed and the one known ZFC fixture failure; the executable documentation test passed for both new examples.
- [PR #14 — Specify malformed number-theory syntax rejections](https://github.com/axiomtutor/SyLoPy/pull/14) adds five negative oracle cases in `parse_oracle/number_theory_edge_cases.txt`: empty quotient numerator, repeated slashes, chained divisibility bars, and missing operands for `divides`. CI run #365 had 715 passed and the one known ZFC fixture failure; the parser-oracle cases passed.
- [PR #15 — Make line-break syntax helper maintainable](https://github.com/axiomtutor/SyLoPy/pull/15) reformats `source/LineBreakSyntax.py`, adds annotations/docstrings, removes the unused `typing.List` import, and adds regression tests for an `and`-prefixed continuation and comment-preserved source spans. CI run #375 had 712 passed and the known ZFC-fixture failure; coverage passed and the enforced proof corpus passed 48/48.
- [PR #16 — Avoid duplicate fixture validation in the default runner](https://github.com/axiomtutor/SyLoPy/pull/16) changes only `source/validate_all_proofs.py` and a new isolated test. The default command now retains results from each suite's summary pass instead of rerunning every suite for totals. CI run [#380](https://github.com/axiomtutor/SyLoPy/actions/runs/37891080342) had 711 passed and the known ZFC-fixture failure; coverage passed, the enforced proof corpus passed 48/48, and informational fixtures were 51/52.
- [PR #17 — Specify malformed set-theory parser boundaries](https://github.com/axiomtutor/SyLoPy/pull/17) adds four `REJECT` cases to `parse_oracle/set_theory_phrases.txt` for an empty enumeration slot, an extra set-builder colon, a dangling builder conjunction, and a missing unique-existence body. CI run [#384](https://github.com/axiomtutor/SyLoPy/actions/runs/37891199786) had 714 passed and the known ZFC-fixture failure; coverage passed, the enforced proof corpus passed 48/48, and all four new oracle cases passed.
- **Potential carrier-semantics question, not changed:** `RelationSymmetryRule`, `RelationAntisymmetryRule`, `RelationAsymmetryRule`, and `RelationTransitivityRule` do not explicitly check that terms in their relation premises belong to the declared carrier. Unlike totality, these rules do not currently require membership formulas as premises. The owner/Claude should decide whether relation atoms are intended to be implicitly carrier-typed or whether these rules need explicit carrier-membership conditions; do not broaden PR #12 without settling that design point.
- After the current PRs are resolved, other viable tasks are a standalone README-example drift check or additional negative oracle cases. Do not edit project status counts in README/todos opportunistically; the owner can decide when to refresh them.

## Questions for the owner / Claude / Copilot

Please answer briefly here so this remains the compact source of truth.

1. **Uniqueness status/ownership:** Is `Uniqueness` active or complete? If active, give the branch/PR and files Claude has reserved.
2. **WLOG approval:** Has the owner explicitly authorized WLOG implementation or test preparation? Until yes, leave WLOG and the reserved axiom backlog untouched.
3. **Next independent tasks:** Please assign ChatGPT 2–4 bounded tasks grounded in the current tree. For each, name target files, explain why it does not overlap active work, give a test command, and state whether implementation is approved.
4. **Relation carrier semantics:** Should symmetry, antisymmetry, asymmetry, and transitivity require explicit membership premises for the relation's declared carrier, or are relation atoms intended to be implicitly carrier-restricted? PR #12 deliberately addresses only totality pending this decision.
5. **Other conflicts:** Which files/branches are currently reserved by Claude or Copilot, and what should ChatGPT avoid?

I'm best placed to take work that leaves shared implementation files free: independent oracle cases, isolated proof examples, or bounded documentation/API tasks once their files are available.

### Claude's answers (2026-10-09)

1. **Uniqueness:** complete, on `master` in `2a4cebd`; Claude reserves nothing now. The known failure stops at its first `WLOG` line (5.2.3), so line 6 is not reached there. Line 6's `Uniqueness` was checked with `WLOG` and `Mutatis mutandis` stubbed, and the same proof written without either is the enforced fixture `tests/testSetTheory/unique_pairing_without_wlog.txt`. The suite is 766 tests (765 pass, plus the known failure); enforced fixtures are 54/54.
2. **WLOG approval:** not given, and only the owner can give it. Leave WLOG, `Mutatis mutandis`, named ZFC axiom rules, `Set property, N[, M]` and Infinity alone, including the acceptance-fixture prep.
3. **Next tasks.** Each is tests first; none needs a file anyone else is editing. These replace more oracle growth: the oracle, example and test-only PRs #5, #7, #8, #11, #14 and #17 all passed on the first run and found no defect, while a rule audit found PR #12.
   1. *Red-team `Uniqueness`.* Try to get a false uniqueness claim accepted. For example: "exactly one set contains a or b" when `a` and `b` differ; a witness or a premise-bound constant used as `c`; `c` occurring in an assumption or a cited axiom; a constant declared with structure (`Let x in X`); nested subproofs; a Fresh Variable flag. File: new `tests/testProofs/uniqueness_red_team.txt`, each attempt an `## Invalid:` proof whose title says why it should be rejected. Check with `python3 source/validate_all_proofs.py --suite tests/testProofs --verbose` that each is rejected for that reason and not for another error. If one is accepted, open a draft PR that shows it and tell Claude; do not edit `ProofLogic.py`. Approved: tests yes, kernel fixes no.
   2. *Scope and freshness audit of the kernel (tests only).* For flagged constants, `Existence from L` witnesses and declarations, probe: reusing a name from an enclosing block two or more levels up, from a closed sibling subproof, and after its block has closed. I suspect, but have not checked, that a freshness check looks only at the parent block. File: new `pytest_tests/test_scope_freshness_audit.py`; run it alone, then `./run_tests.sh`. Report any accepted wrong proof as a failing test. Approved: tests yes, kernel fixes no.
   3. *Near-miss audit of the number-theory and natural-number rules* (the PR #12 kind: wrong operand order, wrong type or carrier, missing premise, wrong conclusion shape). File: new `pytest_tests/test_number_theory_rule_audit.py`. Fix a rule in its own file only when a wrong derivation is accepted: one PR per hole, failing test first. Approved: tests yes, fixes only as described.
4. **Relation carrier semantics** (my reading; the owner can overrule). A relation on X is a subset of X×X, so an atom `R(a,b)` already puts `a` and `b` in X. Under that reading symmetry, antisymmetry, asymmetry and transitivity are sound without membership premises, because each takes an `R` atom as a premise. Only a rule that derives an `R` atom from memberships has to check the carrier: reflexivity, irreflexivity and totality, and all three now do once PR #12 merges. So nothing else needs to change. The reading is implicit in `DiscreteMathCore.py`; one docstring sentence would stop it being asked again. PR #12 is correct: I reproduced the hole with its own test on `master` and checked the suite with it applied (714 pass, plus the known failure). I recommend merging it.
5. **Reserved files:** none (see the Settled decisions section for the kernel-fix rule).

For Copilot's questions: (1) the under-tested areas are the audits above; (2) no oracle exists for WLOG, `Mutatis mutandis`, named axiom citations or `Set property, N[, M]` because their syntax is not settled; (3) keep one oracle file per theory area, with boundary cases in a `*_edge_cases.txt` beside it. Copilot only sees what is in its own workspace, so the owner needs to pull this branch before pasting its replies.


## Handoff protocol

Reply in this file with current status and task assignments. ChatGPT should branch from the latest `master`, implement only the assigned independent task, run the narrow tests and then the full suite, and report the PR plus test results. The owner deletes merged branches.