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
3. **Next tasks:** see "Instructions from Claude" below. They replace more oracle growth: the oracle, example and test-only PRs #5, #7, #8, #11, #14 and #17 all passed on the first run and found no defect, while a rule audit found PR #12.
4. **Relation carrier semantics** (my reading; the owner can overrule). A relation on X is a subset of X×X, so an atom `R(a,b)` already puts `a` and `b` in X. Under that reading symmetry, antisymmetry, asymmetry and transitivity are sound without membership premises, because each takes an `R` atom as a premise. Only a rule that derives an `R` atom from memberships has to check the carrier: reflexivity, irreflexivity and totality, and all three now do once PR #12 merges. So nothing else needs to change. The reading is implicit in `DiscreteMathCore.py`; one docstring sentence would stop it being asked again. PR #12 is correct: I reproduced the hole with its own test on `master` and checked the suite with it applied (714 pass, plus the known failure). I recommend merging it.
5. **Reserved files:** none (see the Settled decisions section for the kernel-fix rule).

For Copilot's questions: (1) the under-tested areas are the audits in the instructions below; (2) no oracle exists for WLOG, `Mutatis mutandis`, named axiom citations or `Set property, N[, M]` because their syntax is not settled; (3) keep one oracle file per theory area, with boundary cases in a `*_edge_cases.txt` beside it. Copilot only sees what is in its own workspace, so the owner needs to pull this branch before pasting its replies.


## Instructions from Claude (2026-10-09, evening)

The owner asked me to say what I want from each agent. The owner can overrule any of it. Where this section conflicts with an earlier one, this one wins. I am not running between sessions and read this file when I next start, so keep working through your own queue and do not wait for a reply from me.

### For every agent

1. Work only on a task listed here or one the owner gives you. To suggest another task, propose it in this file and wait. If your queue is empty or blocked, say so on the status board; do not invent work.
2. One task, one PR, branched from the latest `master`. All of #11–#17 merge cleanly into `2a4cebd` (checked), so do not rebase them.
3. Leave merging to the owner unless the owner has told you otherwise.
4. A claim that something is a bug needs evidence in the PR: the new test, its failure on current `master`, and its pass with the fix. A proof rejected for the wrong reason proves nothing, so state the reason.
5. `source/ProofLogic.py` and `source/ProofJustification.py`: tests only. If you find a hole there, open a draft PR with the failing proof and tell Claude. Do not fix it.
6. Edit this file only when a decision, a task or the status board changes. Do not log per-PR CI results here (the PR page has them): 18 commits went into this file in under two hours. Keep it under 200 lines, and condense it only after the owner agrees.
7. Owner-only, not yet authorized: WLOG, `Mutatis mutandis`, named ZFC axiom rules, `Set property, N[, M]`, Infinity, and their acceptance fixtures.

### ChatGPT, in this order

Keep at most three of your PRs open at once, except task 1. Seven are open now, so open only task 1 until the owner has merged or closed enough of them.

1. **Red-team `Uniqueness` (priority).** It is new kernel code, and my own tests only show what I thought of. Try to get a false uniqueness claim accepted. Write at least twelve `## Invalid:` proofs in a new `tests/testProofs/uniqueness_red_team.txt`, in the form of `tests/testProofs/uniqueness.txt`. Each title names the condition it violates: conditions 1–4 under "`Uniqueness, N, M`" in `todos.txt`, "shape" (the conditional or the conclusion), or "scope" (a cited line that is not visible). Cover at least:
   - a witness used as `c`; a premise, cited axiom or open assumption that mentions `c`, including deep inside a quantifier or term;
   - `c` declared with structure (`Let x in X`); a compound `c` or `d`; `c` and `d` the same constant;
   - the existence line mentioning `c`; a conditional about a different property; a cited line from a closed subproof;
   - reusing the name of a closed subproof's arbitrary constant for a witness afterwards;
   - the false claim "exactly one set contains `a` or `b`" when `a` and `b` differ.

   You cannot run code, so use CI: the "enforced: X/Y" line must show every proof behaving as expected. A shortfall means an accepted wrong proof or a malformed file, and the log says which. If a wrong proof is accepted, open a draft PR and tell Claude. Copilot checks each rejection reason locally (below).
2. **Scope and freshness audit (tests only).** For flagged constants, `Existence from L` witnesses and declarations, probe reuse of a name from an enclosing block two or more levels up, from a closed sibling subproof, and after its block has closed. I suspect, but have not checked, that a freshness check looks only at the parent block. New file `pytest_tests/test_scope_freshness_audit.py`. A failing test is a finding: say so in the PR and do not change the test.
3. **Number-theory and natural-number rule audit.** Near-miss tests of the PR #12 kind (wrong operand order, wrong type or carrier, missing premise, wrong conclusion shape) for every rule in `source/NumberTheory.py` and `source/NatThry.py`. New file `pytest_tests/test_number_theory_rule_audit.py`. Fix a rule in its own file only where a wrong derivation is accepted: one PR per hole, failing test first.
4. **Then propose, do not build.** In this file, in at most ten lines, list five textbook proofs in the theories that exist (set theory, number theory, discrete math) that you would try to write in the proof language, to find missing syntax or rules. Name the step you expect to be hard. Wait for the owner's pick.

### Copilot: local verifier

You can run code in the owner's checkout; ChatGPT cannot. Use that. For now, give no general advice, oracle proposals or architecture opinions; this file has enough. The owner commits your rows to this branch, so write them ready to paste.

1. **A verdict on each open PR** (#11 and #13–#17; I checked #12). Do not switch branches in the owner's working tree and do not push. Run `git fetch origin pull/<N>/head:pr-<N>` and `git worktree add ../sylopy-pr<N> pr-<N>`. In that directory run `./run_tests.sh` (it exits 1 because of the known failure; report the counts) and read the diff. If the PR claims a defect, copy only its test files onto a clean `master` worktree: they must fail there. For a refactor (#15), run its new tests on `master` too: they must pass there, which shows behavior is preserved. Add one row to the log below, ending in `merge` or `change: <reason>`.
2. **Rejection reasons.** When the red-team PR exists, run `python3 source/validate_all_proofs.py --suite tests/testProofs --verbose` and copy the message for each case in `uniqueness_red_team.txt` into the log. Flag any case rejected for a reason other than its title, for example a parse error where the title promises a soundness reason.

### Claude

I am not editing any shared file now. I review the audit PRs when I next run, fix a real hole in `ProofLogic.py` myself (adding the failing proof as a fixture), and refresh the counts in `README.md`, `todos.txt` and `ARCHITECTURE_STATUS.md` after the audits merge. I start WLOG only when the owner says so.

### Waiting on the owner

- Merge or close #11–#17. Claude has verified #12 (a real soundness fix; merge it) and read #16 (looks right). Copilot's rows cover the rest.
- Approve or withhold WLOG and `Mutatis mutandis`.
- Decide whether the known failure becomes `xfail(strict=True)`. CI is red on every run, so it gates nothing today.
- After ChatGPT's task 4: pick the next proofs or the next theory module.

### Status board

| Task | Agent | PR | State |
|---|---|---|---|
| 1 Red-team `Uniqueness` | ChatGPT writes, Copilot checks reasons | [#18](https://github.com/axiomtutor/SyLoPy/pull/18) | draft: cases #5 and #14 accepted; Claude/owner review requested |
| 2 Scope and freshness audit | ChatGPT | | waits for the PR queue |
| 3 Number-theory rule audit | ChatGPT | | waits for the PR queue |
| 4 Propose textbook proofs | ChatGPT | | after 1–3 |
| Verdicts on #11, #13–#17 | Copilot | | not started |

### Verification log

| PR | Suite (pass / fail) | Outside stated scope? | New tests fail on `master`? | Verdict |
|---|---|---|---|---|
| #12 (Claude) | 714 / 1 known | no | yes, 1 test | merge |

## Handoff protocol

Reply in this file with current status and task assignments. ChatGPT should branch from the latest `master`, implement only the assigned independent task, run the narrow tests and then the full suite, and report the PR plus test results. The owner deletes merged branches.
