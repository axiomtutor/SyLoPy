# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This deliberately unmerged branch contains only changing coordination state; keep design rationale in the TODO, issue, or PR.

**Standing queue:** when you have no assigned task, take the next `todo` job in [`JOBS_FOR_CHATGPT.md`](JOBS_FOR_CHATGPT.md); the owner asked Claude to queue it. Keep this paragraph when condensing this file.

## Baseline and active follow-ups

- **Master:** [`97e71ee`](https://github.com/axiomtutor/SyLoPy/commit/97e71ee86fbeff2981999c9460e4280ee84e4605), merging PR #121. PRs #109–#121 are merged. PR #117 added parity-shorthand rejection coverage, PR #118 centralized parser-extension assembly, PR #119 added eight informational relation/order proofs, PR #120 corrected stale parser-installation documentation, and PR #121 (Claude) implemented `Mutatis mutandis` for names replaced by names (stage 1; kernel code in `source/ProofLogic.py`, 33 enforced fixture cases, 147 tests; described in `docs/PROOF_FILE_FORMAT.md`). Issues #75 and #98 remain open for the owner: #75's replay defect is fixed and its last red line now passes, and #98 records owner decisions about number-theory axioms.
- **Latest verification:** master CI [run #40011156926](https://github.com/axiomtutor/SyLoPy/actions/runs/40011156926), on `97e71ee86fbeff2981999c9460e4280ee84e4605`, concluded success (its log was not read, so its counts are not recorded here). Claude's own runs of the PR #121 tested head `ee45eb55a26174ed98b9c4747a550bf6c5e6fc55`, on Python 3.12 and 3.13: 1,743 passed, 1 xfailed; coverage passed; enforced fixtures 272/272; informational fixtures 88/88.
- **[PR #84](https://github.com/axiomtutor/SyLoPy/pull/84), status/docs cleanup:** makes `todos.txt` the source for suite counts, removes stale README claims, and corrects next-work guidance. CI [run #758](https://github.com/axiomtutor/SyLoPy/actions/runs/39085002613) has only the known #75 failure.
- **[PR #85](https://github.com/axiomtutor/SyLoPy/pull/85), declaration consolidation:** removes the redundant `elaborate_typed_declaration` path and moves sequence-aware declaration-recipe dispatch into the active surface-AST path, with a two-clause recipe regression test. CI [run #760](https://github.com/axiomtutor/SyLoPy/actions/runs/39085118117): 1,428 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 69/70. The new test passes; only #75 fails.

## No known failing test

`pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass` failed until [PR #121](https://github.com/axiomtutor/SyLoPy/pull/121) implemented `Mutatis mutandis` for names replaced by names; its proof stopped at line 5.3 after [PR #86](https://github.com/axiomtutor/SyLoPy/pull/86) (Claude's WLOG fix) had fixed #75's replay defect. The test and the fixture were not changed and it passes now, so a failing test in CI is new: explain it or fix it, and do not describe it as known. [Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) is still open for the owner to close.

The WLOG replay gap for `Proof by Cases ... (subproofs below)` inside a WLOG region was fixed by PR #110 (merged). PRs #111–#113 added first-order logic classics, quantifier/scope red-team cases, and equivalence-class/partition proofs. Claude reviewed all three ([#111](https://github.com/axiomtutor/SyLoPy/pull/111#issuecomment-6309381566), [#112](https://github.com/axiomtutor/SyLoPy/pull/112#issuecomment-6309381845), [#113](https://github.com/axiomtutor/SyLoPy/pull/113#issuecomment-6309382063)); the requested test fixes were completed in J19 and J20 (PRs #114 and #115).

The named axiom rules are implemented. Retiring generic `(Axiom)` citations remains an owner decision. Arbitrary-property WLOG, `Mutatis mutandis` beyond names (a name replaced by a term, relation or function symbols replaced), and symbolic defining-property behavior remain deferred. J24 and J25 in [`JOBS_FOR_CHATGPT.md`](JOBS_FOR_CHATGPT.md) are the follow-up to PR #121 that does not need an owner decision.

## Review follow-ups (updated 2026-10-22)

- [PR #114](https://github.com/axiomtutor/SyLoPy/pull/114), J19 (J16/J18), merged: CI [#888](https://github.com/axiomtutor/SyLoPy/actions/runs/39629893268), tested head `8f3cc2a799b072e8d75915cb1cb8a0cf657d4436`; 1,582 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 230/230; informational 79/80. Sole failure is known deferred `Mutatis mutandis` at ZFC fixture line 5.3.
- [PR #115](https://github.com/axiomtutor/SyLoPy/pull/115), J20 (J17), merged: CI [#890](https://github.com/axiomtutor/SyLoPy/actions/runs/39630130647), tested head `935e6a714b5e521d8107c1eb114778bf4df980f5`; 1,589 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 235/235; informational 79/80. Same sole known deferred failure.
- Mutation-test requests for `MT-deny-antecedent`, `DE-concl-first`, `PbC-target-pos`, and `EE-outer` remain unanswered in the PR threads. An additional request in PR #116 asks Claude to run these and a UG opening-flag mutant against the latest tests. Claude owns the mutation runs and any kernel explanation/implementation changes.
- PR #116 added direct `RuleContext` regression tests for `UniversalGeneralizationRule` rejecting both a non-nullary arbitrary-opening flag and a nullary flag with the wrong constant name. These passed in CI #911; they do not change Claude-owned kernel code. The corresponding mutant still needs an explicit mutation-check report from Claude.
- [PR #116](https://github.com/axiomtutor/SyLoPy/pull/116) is merged. It adds valid controls for J16 cases #36/#37 with parsed-conclusion assertions, the full equal-or-disjoint theorem in equivalence-class case #10, removes three unused lines from cases #4/#5, and adds direct UG arbitrary-opening flag regressions. Tested PR head `90da6ddf55773279f2e5cce1ce2529bbc69b4674`, PR CI [run #909](https://github.com/axiomtutor/SyLoPy/actions/runs/39640121821), and merge commit `f2a8f75` CI [run #911](https://github.com/axiomtutor/SyLoPy/actions/runs/39640477680) both report 1,591 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 239/239, informational 79/80. The only failure is the known deferred `Mutatis mutandis` step at ZFC fixture line 5.3. No kernel production files were modified.

## Queue status (2026-10-22, after PRs #117–#120)

J16–J20 and follow-up PR #116 remain merged (PRs #111–#116). Three subsequent authorized jobs are merged: parity-shorthand rejection coverage (PR #117), explicit parser-extension assembly (PR #118), and informational relation/order proofs (PR #119). PR #120 corrects two stale parser-installation descriptions without changing runtime behavior. All three queued jobs are recorded as merged in `JOBS_FOR_CHATGPT.md`. The remaining design items under “Not yet” are still gated on explicit owner approval.


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

## Parity shorthand rejection under quantifiers (PR #117 — merged)

The owner approved this oracle-only task. [PR #117](https://github.com/axiomtutor/SyLoPy/pull/117) added rejection cases for `forall n, n is even or odd` and `exists n, n is even or odd`, preserving the accepted repeated-subject form. Tested head `76b0ddd61765221e83b8358dbafbb10e01baf40d`; CI [run #914](https://github.com/axiomtutor/SyLoPy/actions/runs/39701720665): 1,593 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 239/239; informational fixtures 79/80. The only failure was the deferred `Mutatis mutandis` case.


## Explicit parser-extension assembly (PR #118 — merged)

Before PR #118, `ProofParserPolicy.py` modified several `ProofParser` functions at import time, while `LineBreakSyntax.install()` replaced additional parser functions. The package import order therefore determined the effective parser implementation, and related behavior was split among the parser, policy overlay, and line-break module. This was the motivation for the explicit assembly refactor.

The refactor preserved the public parser API and regression corpus. Membership-characterization behavior remains available to explicit `NUMBER_THEORY_ENVIRONMENT` callers, as required by `pytest_tests/test_compound_declarations.py`; it was not moved into SetTheory alone.

PR #118 centralizes the line-break, formula, declaration-normalization, and membership-characterization extensions in `install_parser_extensions`, called by `source/__init__.py`, and adds an idempotency regression test. No proof or oracle expectation changed. Tested head `f0435dfdf9cfbb44652ce07470928f606b4fd6c6`; CI [run #916](https://github.com/axiomtutor/SyLoPy/actions/runs/39702646324): 1,594 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 239/239; informational fixtures 79/80. The sole failure was the deferred `Mutatis mutandis` case.


## Informational relation and order proofs (PR #119 — merged)

The master TODO's §3 calls for expanding the proof corpus around algebraic and order-theoretic examples, while §4 asks for more user-facing proof patterns. [PR #119](https://github.com/axiomtutor/SyLoPy/pull/119) fulfilled this bounded follow-up with eight informational proofs using existing rules and a dedicated test that reports every unexpected result. No axioms, existing proof expectations, or kernel code changed. Tested head `1c85fb5f553cab0a221fef84784f399e032b5947`; CI [run #920](https://github.com/axiomtutor/SyLoPy/actions/runs/39703431049): 1,595 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 239/239; informational fixtures 87/88. All eight new proofs passed; the one suite failure was the deferred `Mutatis mutandis` case.
