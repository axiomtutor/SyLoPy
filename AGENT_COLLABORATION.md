# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This deliberately unmerged branch contains only changing coordination state; keep design rationale in the TODO, issue, or PR.

**Standing queue:** when you have no assigned task, take the next `todo` job in [`JOBS_FOR_CHATGPT.md`](JOBS_FOR_CHATGPT.md); the owner asked Claude to queue it. Keep this paragraph when condensing this file.

## Baseline and active follow-ups

- **Master:** [`928ffda`](https://github.com/axiomtutor/SyLoPy/commit/928ffda268e9f6a7bba5f91508262a6f06f9afd3). PRs #81–#92 (excluding issue-only numbers #93–#96), #97, #99, #100–#104, #106, and #107 are merged; issues #93–#96 and #105 are closed; #98 remains an owner-decision issue; #75 is fixed by PR #86 (Claude) and left open for the owner; see "One known failing test". PR #108 is open and ready for review.
- **Latest merged-code verification:** [PR #107](https://github.com/axiomtutor/SyLoPy/pull/107), merge commit [`928ffda`](https://github.com/axiomtutor/SyLoPy/commit/928ffda268e9f6a7bba5f91508262a6f06f9afd3), tested head `bfb1a000f7d936dd0fef0c5903428fe9fd837be8`; CI [run #39194905832](https://github.com/axiomtutor/SyLoPy/actions/runs/39194905832): 1,502 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. All three ambiguous-shorthand rejection cases pass. The sole CI failure remains known issue #75 (`MutatisMutandis`).
- **[PR #84](https://github.com/axiomtutor/SyLoPy/pull/84), status/docs cleanup:** makes `todos.txt` the source for suite counts, removes stale README claims, and corrects next-work guidance. CI [run #758](https://github.com/axiomtutor/SyLoPy/actions/runs/39085002613) has only the known #75 failure.
- **[PR #85](https://github.com/axiomtutor/SyLoPy/pull/85), declaration consolidation:** removes the redundant `elaborate_typed_declaration` path and moves sequence-aware declaration-recipe dispatch into the active surface-AST path, with a two-clause recipe regression test. CI [run #760](https://github.com/axiomtutor/SyLoPy/actions/runs/39085118117): 1,428 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 69/70. The new test passes; only #75 fails.

## One known failing test

`pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass` is the sole test failure, and since [PR #86](https://github.com/axiomtutor/SyLoPy/pull/86) (Claude's WLOG fix, merged) it no longer fails because of #75's WLOG replay: the proof passes line 5.2.4 and stops at line 5.3, which uses `Mutatis mutandis`, deferred pending owner approval. The test stays red; do not weaken it, change the fixture or mask the failure. [Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) is still open for the owner to close.

One more WLOG gap is logged in `todos.txt` under Known issues: a `Proof by Cases ... (subproofs below)` inside a WLOG region is replayed untransformed. It is in Claude-owned `source/ProofLogic.py`, and **Claude is taking it; do not edit that file.**

The named axiom rules are implemented. Retiring generic `(Axiom)` citations remains an owner decision. Arbitrary-property WLOG, `Mutatis mutandis`, and symbolic defining-property behavior remain deferred.


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
