# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This deliberately unmerged branch contains only changing coordination state; keep design rationale in the TODO, issue, or PR.

**Standing queue:** when you have no assigned task, take the next `todo` job in [`JOBS_FOR_CHATGPT.md`](JOBS_FOR_CHATGPT.md); the owner asked Claude to queue it. Keep this paragraph when condensing this file.

## Baseline and active follow-ups

- **Master:** [`e3e96ad`](https://github.com/axiomtutor/SyLoPy/commit/e3e96adb3169858c578f4eec39ce79aac8c9b347). PRs #81–#92 (excluding issue-only numbers #93–#96), #97, #99, #100–#103 are merged; #98 remains an owner-decision issue; #75 remains a Claude-owned kernel issue; #105 is the open parity-disjunction parser finding. PR #104 is open and ready for review.
- **Latest merged-code verification:** [PR #103](https://github.com/axiomtutor/SyLoPy/pull/103), CI [run #39183767233](https://github.com/axiomtutor/SyLoPy/actions/runs/39183767233): 1,495 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. The sole failure remains known issue #75 (`MutatisMutandis`).
- **[PR #84](https://github.com/axiomtutor/SyLoPy/pull/84), status/docs cleanup:** makes `todos.txt` the source for suite counts, removes stale README claims, and corrects next-work guidance. CI [run #758](https://github.com/axiomtutor/SyLoPy/actions/runs/39085002613) has only the known #75 failure.
- **[PR #85](https://github.com/axiomtutor/SyLoPy/pull/85), declaration consolidation:** removes the redundant `elaborate_typed_declaration` path and moves sequence-aware declaration-recipe dispatch into the active surface-AST path, with a two-clause recipe regression test. CI [run #760](https://github.com/axiomtutor/SyLoPy/actions/runs/39085118117): 1,428 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 69/70. The new test passes; only #75 fails.

## One known blocker

[Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) is the sole test failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. WLOG replay changes `x=a` to `x=b`, then wrongly substitutes the invariant pair characterization on line 3. Preserve an original visible citation when it remains valid, remapping only when necessary. **This touches Claude-owned `source/ProofLogic.py`; coordinate with Claude before editing.** Do not weaken tests or mask the failure.

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


## Parity disjunction oracle coverage — finding recorded (PR #104; issue #105)

The owner approved the bounded follow-up. The explicit repeated-subject formula `n is even or n is odd` and three connective-composition probes were tested as loaded oracle cases. All failed from the same parser issue: `try_parse_parity_phrase` passes `n is even or n` to `parse_term`. Do not broaden parser semantics as part of the coverage-only task.

The smallest reproducer is recorded outside the loaded oracle in `parse_oracle/pending/parity_disjunction_composition.txt`; [issue #105](https://github.com/axiomtutor/SyLoPy/issues/105) records the exact error. The ambiguous shorthand `n is even or odd` remains rejected as intended.

[PR #104](https://github.com/axiomtutor/SyLoPy/pull/104) is ready for owner review. Tested head: `e7d60b7fe0f0e301169d92ab2aec6ce70bffb573`; CI [run #39188239080](https://github.com/axiomtutor/SyLoPy/actions/runs/39188239080): 1,495 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 140/140; informational fixtures 79/80. Sole failure is known issue #75 (`Mutatis mutandis` informational ZFC fixture).