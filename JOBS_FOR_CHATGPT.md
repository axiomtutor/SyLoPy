# Delegated Jobs for ChatGPT

This is the concise delegated-work tracker. Stable collaboration rules live in [`AGENT_COLLABORATION.md`](AGENT_COLLABORATION.md); current feature status, invariants, design decisions, and owner-gated work live in [`todos.txt`](todos.txt). Use PRs and issues for implementation details and discussion.

Completed job specifications and their original task instructions are preserved in [`docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md). That file is historical context, not an active work queue.

## Current queue

Start a job only after the pull request that adds it has been merged, so the instructions and implementation can be read together. Do not resume a completed or archived task unless the owner explicitly re-queues it or provides new direction.

### J28 — Register every elaborated declaration in ProofContext

**Goal:** Keep the elaboration-time lexical declaration context synchronized with every declaration emitted into core entries, including declarations produced by `Existence from L` and the generic declaration-prefix path used by declaration-like premises.

**Allowed scope:** `source/ProofParser.py`, a focused new regression module under `pytest_tests/`, and this tracker. Do not edit `ProofLogic.py` or `ProofJustification.py`.

**Tests:** Verify that an existence witness and a declaration parsed from a `Premise` with `such that` are visible to a later declaration recipe that refers to them as a carrier; verify duplicate declarations are rejected during elaboration; preserve existing compound-declaration, scope, and typed-declaration behavior.

**Done when:** All declaration objects emitted by an elaborated entry are registered exactly once in the current `ProofContext`, already-registered compound-declaration objects are not re-registered, duplicate names fail at the source line, and CI passes the full test suite and enforced/informational fixture corpus.

Status: in progress (PR #142).



## Completed jobs

| Job | Title | Result |
| --- | --- | --- |
| J0 | CI shows why a fixture or test failed | merged ([PR #87](https://github.com/axiomtutor/SyLoPy/pull/87)) |
| J1 | Set-theory proofs, batch 1 | merged ([PR #88](https://github.com/axiomtutor/SyLoPy/pull/88)) |
| J2 | Refresh proof-format documentation | merged ([PR #89](https://github.com/axiomtutor/SyLoPy/pull/89)) |
| J3 | Red-team the set-theory rules | merged ([PR #90](https://github.com/axiomtutor/SyLoPy/pull/90)) |
| J4 | Parse oracle: more phrases | merged ([PR #91](https://github.com/axiomtutor/SyLoPy/pull/91)) |
| J5 | Order and relation proofs | merged ([PR #92](https://github.com/axiomtutor/SyLoPy/pull/92)) |
| J6 | Number-theory proofs and a missing-axiom list | merged ([PR #97](https://github.com/axiomtutor/SyLoPy/pull/97)) |
| J7 | Mutation-check tool | merged ([PR #99](https://github.com/axiomtutor/SyLoPy/pull/99)) |
| J8 | Negative set phrases in the parser | merged ([PR #100](https://github.com/axiomtutor/SyLoPy/pull/100)) |
| J9 | Union, intersection, and disjointness phrases | merged ([PR #101](https://github.com/axiomtutor/SyLoPy/pull/101)) |
| J16 | First-order logic classics | merged ([PR #111](https://github.com/axiomtutor/SyLoPy/pull/111)) |
| J17 | Red-team the quantifier and scope rules | merged ([PR #112](https://github.com/axiomtutor/SyLoPy/pull/112)) |
| J18 | Equivalence classes and partitions | merged ([PR #113](https://github.com/axiomtutor/SyLoPy/pull/113)) |
| J19 | Fix the J16 and J18 review findings | merged ([PR #114](https://github.com/axiomtutor/SyLoPy/pull/114)) |
| J20 | Fix the J17 review findings | merged ([PR #115](https://github.com/axiomtutor/SyLoPy/pull/115)) |
| J21 | Reject ambiguous parity shorthand under quantifiers | merged ([PR #117](https://github.com/axiomtutor/SyLoPy/pull/117)) |
| J22 | Centralize parser extension assembly | merged ([PR #118](https://github.com/axiomtutor/SyLoPy/pull/118)) |
| J23 | Expand informational relation and order proofs | merged ([PR #119](https://github.com/axiomtutor/SyLoPy/pull/119)) |
| J24 | Red-team Mutatis mutandis | merged ([PR #123](https://github.com/axiomtutor/SyLoPy/pull/123)) |
| J25 | Where stage 1 of Mutatis mutandis stops | merged ([PR #124](https://github.com/axiomtutor/SyLoPy/pull/124)) |
| J26 | Red-team Mutatis mutandis stages 2 and 3 | merged ([PR #135](https://github.com/axiomtutor/SyLoPy/pull/135)) |
| J27 | Where Mutatis mutandis stops, second look | merged ([PR #139](https://github.com/axiomtutor/SyLoPy/pull/139)) |

## Rules for new jobs

1. Add an explicit job before starting delegated work. Each job must state its goal, allowed scope/files, tests or fixtures to add, and an observable “Done when” condition.
2. Use one small branch and one PR per job; normally keep a PR to about 400 changed lines or fewer. Keep no more than three delegated PRs open at once. The owner merges.
3. Treat CI as the test run. Keep the PR a draft until its stated completion criteria pass. Report the exact tested commit, CI run, test totals, coverage, enforced fixtures, informational fixtures, and remaining failures; never infer results from an uninspected run.
4. `source/ProofLogic.py` and `source/ProofJustification.py` are kernel-owned; do not edit them without coordination. Do not alter existing tests, fixtures, or parser-oracle expectations merely to make a change pass. Do not start items marked as requiring owner approval in `todos.txt`.
5. A checker defect is a finding, not a reason to weaken a test. File a focused issue with the smallest proof, exact accepted/rejected behavior or message, suspected rule/file, and `Owner: Claude` when the kernel is involved. Include strict expected-failure regression coverage for an invalid proof that is incorrectly accepted, following the collaboration guide.
6. A job is complete only after its PR is merged and the status table above is updated. Preserve its full specification and task-specific notes in the archive rather than keeping completed instructions in this live tracker.

Historical note: this tracker replaces the former long-form queue. Archived job text is retained for provenance, but current repository guidance and explicit owner decisions take precedence.

## Active maintenance

### J29 — Consolidate the legacy natural-number fixture runner

**Goal:** Keep `source/test_runner_NatNum.py` as a compatibility command, but delegate suite execution, theory-resource configuration, reporting, and exit status to `source/validate_all_proofs.py`.

**Allowed scope:** `source/test_runner_NatNum.py`, `pytest_tests/test_import_contract.py`, and this tracker. Do not change proof semantics, fixtures, or kernel code.

**Tests:** Run the compatibility command from the same subprocess/import environment as its existing test; assert successful exit and the full natural-number suite summary.

**Done when:** The duplicate runner implementation is removed, the old command continues to validate `testProofsNat`, regression coverage verifies its result, and full CI passes.

Status: in progress.
