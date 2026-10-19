# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This deliberately unmerged branch contains only changing coordination state; keep design rationale in the TODO, issue, or PR.

**Standing queue:** when you have no assigned task, take the next `todo` job in [`JOBS_FOR_CHATGPT.md`](JOBS_FOR_CHATGPT.md); the owner asked Claude to queue it. Keep this paragraph when condensing this file.

## Baseline and active follow-ups

- **Master:** [`cff0d18`](https://github.com/axiomtutor/SyLoPy/commit/cff0d1879fb4bb281d769bd2b9e9b2c66add8039). PRs #81–#92 (excluding issue-only numbers #93–#96), #97, and #99 are merged; #98 is an open issue.
- **Latest merged-code verification:** [PR #83](https://github.com/axiomtutor/SyLoPy/pull/83), CI [run #749](https://github.com/axiomtutor/SyLoPy/actions/runs/39081978883): 1,427 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 81/81; informational fixtures 69/70. The sole failure is issue #75.
- **[PR #84](https://github.com/axiomtutor/SyLoPy/pull/84), status/docs cleanup:** makes `todos.txt` the source for suite counts, removes stale README claims, and corrects next-work guidance. CI [run #758](https://github.com/axiomtutor/SyLoPy/actions/runs/39085002613) has only the known #75 failure.
- **[PR #85](https://github.com/axiomtutor/SyLoPy/pull/85), declaration consolidation:** removes the redundant `elaborate_typed_declaration` path and moves sequence-aware declaration-recipe dispatch into the active surface-AST path, with a two-clause recipe regression test. CI [run #760](https://github.com/axiomtutor/SyLoPy/actions/runs/39085118117): 1,428 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 69/70. The new test passes; only #75 fails.

## One known blocker

[Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) is the sole test failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. WLOG replay changes `x=a` to `x=b`, then wrongly substitutes the invariant pair characterization on line 3. Preserve an original visible citation when it remains valid, remapping only when necessary. **This touches Claude-owned `source/ProofLogic.py`; coordinate with Claude before editing.** Do not weaken tests or mask the failure.

The named axiom rules are implemented. Retiring generic `(Axiom)` citations remains an owner decision. Arbitrary-property WLOG, `Mutatis mutandis`, and symbolic defining-property behavior remain deferred.


## J8 — Negative set phrases (PR #100)

Merged into master after CI confirmed the new oracle cases pass. The change supports the 12 readings from [finding #93](https://github.com/axiomtutor/SyLoPy/issues/93) in `source/SetTheory.py` and `parse_oracle/negated_set_phrases.txt`, with no generic connective parser or kernel change.

## J9 — Union, intersection, and disjointness phrases (in progress)

Scope: support the 12 intended readings in [finding #94](https://github.com/axiomtutor/SyLoPy/issues/94), currently in `parse_oracle/pending/set_operations_phrases.txt`. Keep the operations as ordinary formulas: union membership is disjunction, intersection membership is conjunction, and disjointness is universal non-overlap. Protect full phrases from the generic connective splitter using the existing set-theory phrase-span mechanism. Do not add set-operation terms or change the kernel.

Done when all 12 intended readings pass the loaded oracle; CI has no new failures beyond known issue #75; the pending copy is removed only after the unchanged expected formulas pass.
