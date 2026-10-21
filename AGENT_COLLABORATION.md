# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This deliberately unmerged branch contains only changing coordination state; keep design rationale in the TODO, issue, or PR.

**Standing queue:** when you have no assigned task, take the next `todo` job in [`JOBS_FOR_CHATGPT.md`](JOBS_FOR_CHATGPT.md); the owner asked Claude to queue it. Keep this paragraph when condensing this file.

## Baseline and active follow-ups

- **Master:** [`1684146`](https://github.com/axiomtutor/SyLoPy/commit/1684146b2719e2a3879bb17b06fb79c3501add6b), merging PR #115. PRs #109–#115 are merged; follow-up PR #116 is open and adds valid controls for J16's wrong-rule examples plus the equal-or-disjoint equivalence-class theorem. Issues #75 and #98 remain open: #75 is fixed as a WLOG replay defect but stays red at the owner-deferred `Mutatis mutandis` line, and #98 records owner decisions about number-theory axioms.
- **Latest merged-code verification:** master commit [`1684146`](https://github.com/axiomtutor/SyLoPy/commit/1684146b2719e2a3879bb17b06fb79c3501add6b), CI [run #39633628601](https://github.com/axiomtutor/SyLoPy/actions/runs/39633628601): 1,588 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 236/236; informational fixtures 79/80. The sole CI failure is `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, which reaches the owner-deferred `Mutatis mutandis` at line 5.3.
- **[PR #84](https://github.com/axiomtutor/SyLoPy/pull/84), status/docs cleanup:** makes `todos.txt` the source for suite counts, removes stale README claims, and corrects next-work guidance. CI [run #758](https://github.com/axiomtutor/SyLoPy/actions/runs/39085002613) has only the known #75 failure.
- **[PR #85](https://github.com/axiomtutor/SyLoPy/pull/85), declaration consolidation:** removes the redundant `elaborate_typed_declaration` path and moves sequence-aware declaration-recipe dispatch into the active surface-AST path, with a two-clause recipe regression test. CI [run #760](https://github.com/axiomtutor/SyLoPy/actions/runs/39085118117): 1,428 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 69/70. The new test passes; only #75 fails.

## One known failing test

`pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass` is the sole test failure, and since [PR #86](https://github.com/axiomtutor/SyLoPy/pull/86) (Claude's WLOG fix, merged) it no longer fails because of #75's WLOG replay: the proof passes line 5.2.4 and stops at line 5.3, which uses `Mutatis mutandis`, deferred pending owner approval. The test stays red; do not weaken it, change the fixture or mask the failure. [Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) is still open for the owner to close.

The WLOG replay gap for `Proof by Cases ... (subproofs below)` inside a WLOG region was fixed by PR #110 (merged). PRs #111–#113 were also merged by the owner: first-order logic classics, core quantifier/scope red-team cases, and equivalence-class/partition proofs. Claude posted review comments on all three ([#111](https://github.com/axiomtutor/SyLoPy/pull/111#issuecomment-6309381566), [#112](https://github.com/axiomtutor/SyLoPy/pull/112#issuecomment-6309381845), [#113](https://github.com/axiomtutor/SyLoPy/pull/113#issuecomment-6309382063)); the fixes are queued as J19 and J20.

The named axiom rules are implemented. Retiring generic `(Axiom)` citations remains an owner decision. Arbitrary-property WLOG, `Mutatis mutandis`, and symbolic defining-property behavior remain deferred.

## Review follow-ups (2026-10-21)

- [PR #114](https://github.com/axiomtutor/SyLoPy/pull/114), J19 (J16/J18), merged: CI [#888](https://github.com/axiomtutor/SyLoPy/actions/runs/39629893268), tested head `8f3cc2a799b072e8d75915cb1cb8a0cf657d4436`; 1,582 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 230/230; informational 79/80. Sole failure is known deferred `Mutatis mutandis` at ZFC fixture line 5.3.
- [PR #115](https://github.com/axiomtutor/SyLoPy/pull/115), J20 (J17), merged: CI [#890](https://github.com/axiomtutor/SyLoPy/actions/runs/39630130647), tested head `935e6a714b5e521d8107c1eb114778bf4df980f5`; 1,589 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 235/235; informational 79/80. Same sole known deferred failure.
- Mutation-test requests for `MT-deny-antecedent`, `DE-concl-first`, `PbC-target-pos`, and `EE-outer` remain unanswered in the PR threads. Claude owns these runs and any kernel explanation/implementation changes.
- Final audit also found no direct regression test for `UniversalGeneralizationRule` rejecting a non-nullary/incorrect arbitrary-opening flag, although the guard exists in `source/ProofLogic.py`; Claude explicitly volunteered to add this kernel-side test. Keep it as Claude-owned follow-up rather than claiming J17 fully verified.
- [PR #116](https://github.com/axiomtutor/SyLoPy/pull/116) completes the remaining review gaps: adds valid controls for J16 cases #36/#37 with explicit parsed-conclusion assertions, and proves the full equal-or-disjoint equivalence-class theorem in case #10. Tested head `3464ed5b954ce5a7c245e46a4aad57ad28b85374`, CI [run #902](https://github.com/axiomtutor/SyLoPy/actions/runs/39636235256): 1,589 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 239/239, informational 79/80. The only failure is the known deferred `Mutatis mutandis` step at ZFC fixture line 5.3. The PR is ready for review. No kernel production files have been modified.

## Queue status (2026-10-21)

J16–J20 are merged (PRs #111–#115). PR #116 completes two remaining review gaps identified by Claude; it is not yet merged. The proposed jobs below remain explicitly gated on owner approval. Do not begin unrelated work just because the standing queue is empty.


## J8 — Negative set phrases (PR #100)

Merged into master after CI confirmed the new oracle cases pass. The change supports the 12 readings from [finding #93](https://github.com/axiomtutor/SyLoPy/issues/93) in `source/SetTheory.py` and `parse_oracle/negated_set_phrases.txt`, with no generic connective parser or kernel change.

## J9 — Union, intersection, and disjointness phrases (PR #101)

Merged into master: [PR #101](https://github.com/axiomtutor/SyLoPy/pull/101), tested head [`230a5a9`](https://github.com/axiomtutor/SyLoPy/commit/230a5a946ca5f942d30ce6200bf4cedb5f36df30), CI [run #39182587319](https://github.com/axiomtutor/SyLoPy/actions/runs/39182587319).

The change supports all 12 intended readings from [finding #94](https://github.com/axiomtutor/SyLoPy/issues/94) in `source/SetTheory.py` and `parse_oracle/set_operations_phrases.txt`. Phrases with conjunction-looking "and" are kept whole using the set-theory phrase-span path. The surface operations lower into ordinary logic; no set-operation terms or kernel behavior are added. The unchanged intended formulas all pass.

Verification: 1,491 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. All 12 J9 oracle cases pass. Sole failure: known deferred #75 `Mutatis mutandis` in `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. No existing test or proof fixture was weakened.

## Finding #95 — Nested bounded-quantifier variants (PR #102)

Merged into master: [PR #102](https://github.com/axiomtutor/SyLoPy/pull/102), tested head [`08c28b2`](https://github.com/axiomtutor/SyLoPy/commit/08c28b2d9fa9244b3699f845507109220d2338f5), CI [run #39183132098](https://github.com/axiomtutor/SyLoPy/actions/runs/39183132098).

The parser now recognizes the "for every" bounded-universal spelling, excludes an enclosing conditional's comma from the quantifier body, and accepts that comma before "then". Both oracle cases from the finding pass.

Verification: 1,493 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. Sole failure remains the known deferred #75 `MutatisMutandis` fixture.

## Finding #96 — Even and odd predicate phrases (PR #103)

Merged into master: [PR #103](https://github.com/axiomtutor/SyLoPy/pull/103), tested head [`8eab6dc`](https://github.com/axiomtutor/SyLoPy/commit/8eab6dcb60d0ec4be08d26ce9ed5d346689e67e7), CI [run #39183767233](https://github.com/axiomtutor/SyLoPy/actions/runs/39183767233).

The parser adds `n is even` / `n is odd` as uninterpreted unary predicates `Even(n)` / `Odd(n)`, declares the predicates in the number-theory vocabulary, and promotes the two pending oracle cases. No parity axioms are added. The ambiguous shorthand `n is even or odd` remains rejected.

Verification: 1,495 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. Both new parity oracle cases pass. The sole failure remains the known deferred #75 `MutatisMutandis` fixture.




## Parity disjunction parser fix (PR #104 and #106 merged; issue #105 closed)

The coverage-only follow-up recorded the smallest reproducer, `n is even or n is odd`, in [PR #104](https://github.com/axiomtutor/SyLoPy/pull/104) and [issue #105](https://github.com/axiomtutor/SyLoPy/issues/105). The parser fix was then merged in [PR #106](https://github.com/axiomtutor/SyLoPy/pull/106) at commit [`d5c1a8a`](https://github.com/axiomtutor/SyLoPy/commit/d5c1a8a74ee6c69173962700f01b3a32cf8296f8). The parser accepts repeated-subject parity disjunctions directly and falls back to ordinary connective parsing for surrounding formulas. The ambiguous shorthand `n is even or odd` remains rejected when parsed as a standalone formula.

Verification on tested head `e3ce24d3a9762c9fbe8cea218fe3b954e0f6cdea`: CI [run #39189983829](https://github.com/axiomtutor/SyLoPy/actions/runs/39189983829), 1,499 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. All four new parity-disjunction cases pass. The sole failure remains issue #75 (`Mutatis mutandis` in the informational ZFC fixture).


## Parity shorthand compound rejection coverage (PR #107)

The owner approved the proposed coverage task. [PR #107](https://github.com/axiomtutor/SyLoPy/pull/107) adds three loaded `REJECT` oracle cases for the ambiguous shorthand `n is even or odd` inside an implication, conjunction, and negation. The explicit repeated-subject contrast `n is even or n is odd` remains covered as accepted. The now-obsolete pending copy of that explicit case was removed because its behavior is implemented by PR #106.

Tested head: `bfb1a000f7d936dd0fef0c5903428fe9fd837be8`; CI [run #39194905832](https://github.com/axiomtutor/SyLoPy/actions/runs/39194905832): 1,502 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. All three new rejection cases pass. The only failure is issue #75 (`Mutatis mutandis` in the informational ZFC fixture).


## Parity composite-subject oracle coverage (PR #108)

[PR #108](https://github.com/axiomtutor/SyLoPy/pull/108) adds four loaded oracle cases: explicit disjunction with a compound subject `Plus(a, b)`, reversed `odd or even` order, a compound-subject conditional, and a disjunction under `forall`. No parser behavior changed.

Tested head: `1f87bf3729bb65310a2b15f74edfdca99d73dbf8`; CI [run #39195128146](https://github.com/axiomtutor/SyLoPy/actions/runs/39195128146): 1,506 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. All four new cases pass. The sole failure remains issue #75 (`Mutatis mutandis` in the informational ZFC fixture).

## Proposed next ChatGPT job — preserve shorthand rejection under quantifiers (awaiting owner approval)

Add one or two oracle `REJECT` cases showing that the intentionally ambiguous `n is even or odd` remains rejected beneath a universal and an existential quantifier (for example, `forall n, n is even or odd` and `exists n, n is even or odd`). Keep the accepted repeated-subject form unchanged. This is oracle-only unless a test reveals inconsistent behavior; await approval before creating a branch/PR.


## Proposed cleanup — make parser extension assembly explicit (awaiting owner approval)

`ProofParserPolicy.py` currently modifies several `ProofParser` functions at import time, and `LineBreakSyntax.install()` replaces additional parser functions. The package import order therefore determines the effective parser implementation, and related behavior is split among the parser, policy overlay, and line-break module.

A bounded refactor should replace this implicit installation with explicit, named extension points or one documented parser-assembly step, while preserving the public parser API and the current regression corpus. Keep the membership-characterization behavior unchanged for explicit `NUMBER_THEORY_ENVIRONMENT` callers: `pytest_tests/test_compound_declarations.py` currently asserts it, so moving that behavior into SetTheory alone would be a semantic change, not a cleanup.

**Done when:** parser import-contract tests, parser/oracle tests, line-broken declaration tests, compound-declaration tests, and full CI pass with no changed proof or oracle expectations. Do not begin until the owner approves the proposal.


## Proposed next ChatGPT job — expand informational relation and order proofs (awaiting owner approval)

The master TODO's §3 calls for expanding the proof corpus around algebraic and order-theoretic examples, while §4 asks for more user-facing proof patterns. The completed J16–J18 work adds new base-logic and equivalence-class coverage; the next bounded job could add a small batch of informational examples using only currently implemented relation and order rules.

Suggested scope: inspect the current `tests/testDiscreteMath/` corpus, identify specific textbook-level gaps, add roughly 8–12 short proofs in one new informational fixture, and add a test that reports every unexpected result. Do not add axioms, modify existing expected outcomes, edit kernel files, or treat a failure caused by unsupported mathematics as a reason to change the theory. File a smallest-example finding instead if an intended textbook proof is blocked by the current rule set.

This is a proposal only. Do not begin until the owner approves and it is added to `JOBS_FOR_CHATGPT.md`.
