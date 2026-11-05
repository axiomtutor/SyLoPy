# Delegated Jobs for ChatGPT

This file is the live queue and concise disposition ledger. Stable collaboration rules are in [`AGENT_COLLABORATION.md`](AGENT_COLLABORATION.md); current status and owner decisions are in [`todos.txt`](todos.txt). Full historical task specifications are preserved in [`docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md).

## Current queue

No delegated jobs are currently queued. Add a scoped job here only after its entry has been approved and merged; do not restart archived work without the owner's direction.

## Recent dispositions

- **J31:** PR #148 closed without merge; the dedicated red-team expansion is not active.
- **J32:** relation-subset examples and their focused runner are implemented.
- **J33:** arbitrary-property WLOG implementation and focused coverage are complete; optional standalone target/twin fixtures remain.
- **J34:** closed-axiom implementation and focused coverage are complete; optional standalone red-team fixtures remain.
- **J35:** four basic divisibility proofs merged in PR #158.

Original specifications and their final dispositions are preserved in the archive.

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
| J28 | Register every elaborated declaration in ProofContext | merged ([PR #142](https://github.com/axiomtutor/SyLoPy/pull/142)) |
| J29 | Consolidate the legacy natural-number fixture runner | merged ([PR #143](https://github.com/axiomtutor/SyLoPy/pull/143)) |
| J30 | Declaration lines must not drop or absorb text | merged ([PR #146](https://github.com/axiomtutor/SyLoPy/pull/146)) |
| J31 | Relation-subset red-team expansion | closed without merge (PR #148); not re-queued |
| J32 | Relation-subset examples | implemented |
| J33 | Arbitrary-property WLOG targets | implementation complete; optional standalone fixtures remain |
| J34 | Closed-axiom red-team | implementation complete; optional standalone fixtures remain |
| J35 | Basic divisibility identity proofs | merged (PR #158) |

## Rules for new jobs

1. Add an explicit job before starting delegated work. Each job must state its goal, allowed scope/files, tests or fixtures to add, and an observable “Done when” condition.
2. Use one small branch and one PR per job; normally keep a PR to about 400 changed lines or fewer. Keep no more than three delegated PRs open at once. The owner merges.
3. Treat CI as the test run. Keep the PR a draft until its stated completion criteria pass. Report the exact tested commit, CI run, test totals, coverage, enforced fixtures, informational fixtures, and remaining failures; never infer results from an uninspected run.
4. `source/ProofLogic.py` and `source/ProofJustification.py` are kernel-owned; do not edit them without coordination. Do not alter existing tests, fixtures, or parser-oracle expectations merely to make a change pass. Do not start items marked as requiring owner approval in `todos.txt`.
5. A checker defect is a finding, not a reason to weaken a test. File a focused issue with the smallest proof, exact accepted/rejected behavior or message, suspected rule/file, and `Owner: Claude` when the kernel is involved. Include strict expected-failure regression coverage for an invalid proof that is incorrectly accepted, following the collaboration guide.
6. A job is complete only after its PR is merged and the status table above is updated. Preserve its full specification and task-specific notes in the archive rather than keeping completed instructions in this live tracker.

Historical note: this tracker replaces the former long-form queue. Archived job text is retained for provenance, but current repository guidance and explicit owner decisions take precedence.

## Current project infrastructure

- The default CI/local project run is named `default`; it runs the standard
  Python tests and all proof fixture suites.
- The slower audit/adversarial tests are named `extended`; they are not run by
  `./run_tests.sh` unless `--suite extended`, `--suite all`, or the compatibility
  flag `--extended` is requested.
- There are currently no active pytest `xfail` tests or strict expected-failure
  cases. Standalone J33/J34 fixture expansion remains optional coverage work
  rather than an unresolved correctness blocker.
