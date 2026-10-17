# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on coordination.

## Current baseline and open work

- **Master:** [`5d519db`](https://github.com/axiomtutor/SyLoPy/commit/5d519db3a2d30ea50a24467c751bdddb8fbf8dc7), after PRs #72–#74 merged.
- **Active follow-up:** [PR #76](https://github.com/axiomtutor/SyLoPy/pull/76) refreshes README/TODO status after those merges and documents the WLOG failure's concrete cause. Its CI is the integrated-tree test for the changes from #72–#74 plus documentation.
- **Latest separate PR verification:** Run [#713](https://github.com/axiomtutor/SyLoPy/actions/runs/39039151188), for #73, reports 1,220 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 61/62. Run [#714](https://github.com/axiomtutor/SyLoPy/actions/runs/39039332234), for #74 on a merge ref based on the pre-#73 master, reports 1,219 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 62/63. The test regressions/examples added by #73 and #74 passed individually, but neither report by itself tests the final integrated master tree.
- **Known WLOG failure:** Tracked in [issue #75](https://github.com/axiomtutor/SyLoPy/issues/75). In `zfc_remaining_axioms.txt` line 5.2.4, WLOG replays `x = a` as `x = b`, with substitution `a -> b`. Current citation remapping applies that substitution to external line 3, changing the pair characterization `(u = a or u = b)` into `(u = b or u = b)`; this is not an established property of the existing pair set Y. The original line 3 should be preserved as an invariant outer citation when the transformed step is still justified by it; use a substituted counterpart where a cited fact genuinely needs substitution. Keep the ordinary rule check authoritative and retain negative scope/citation tests.
- **Ownership:** The failing remapping path is in `source/ProofLogic.py`, owned by Claude. Do not edit it before coordinating. The issue proposes a bounded fix and regressions without broadening WLOG to arbitrary properties.
- **Deferred work:** `Mutatis mutandis` and the named ZFC axiom-citation rules remain deferred pending explicit owner approval. No approval is implied by the existence of issue #75.
- **Coordination branch:** `chatgpt-agent-guidance` is deliberately unmerged and is the live coordination channel. Preserve it; update this handoff in place.

## Settled decisions and boundaries

- The owner has final authority over semantics and priority. Do not infer approval for a deferred feature from its presence in `todos.txt` or from a general instruction to continue working.
- Typed declaration option A is approved: `Let n be a natural number` asserts the ordinary citable `Nat(n)` fact; `Let X be an integer` asserts `Int(X)`. This is not refinement-type checking or typed-quantifier support.
- Declarations inside a subproof are visible in that scope and descendants, but do not escape to the enclosing scope or affect siblings. Root declarations remain visible in nested scopes.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) enforce the declared carrier.
- `Let Y be such a set. (Existence from L)` names a scoped existential witness. The axiom/premise alone does not introduce a named witness.
- Quotient uniqueness requires `not (a = Zero)`; PR #45 implements the guard.
- For issue #69, the owner chose option A: accept equality in either orientation in the existing Set property behavior, without adding a separate substitution form. PRs #70/#71 are the active work for this area; do not duplicate or broaden them.
- The checked WLOG equality-case replay implementation landed in PR #63. Do not describe WLOG as wholly unimplemented; the ZFC informational fixture still has the replay line-correspondence failure reported above. Any further WLOG or Mutatis mutandis changes require coordination and must not mask that failure.

## Architecture and ownership

The pipeline is proof text → surface parsing → elaboration → core proof entries → `ProofLogic.Proof`. `ProofContext` owns lexical scoping during elaboration. The kernel independently uses `LabelScope` and `DeclarationScope` for validation; their overlapping scope semantics are kept equivalent by tests.

Theory-specific syntax should normally be implemented behind `TheoryEnvironment` and declaration recipes, not as generic elaboration special cases. Prefer sugar lowering to existing core forms where it remains clear; document whether each feature is syntactic, derived, or axiomatic.

- **Claude owns kernel implementation** in `source/ProofLogic.py` and `source/ProofJustification.py`. Coordinate before editing either file.
- Avoid concurrent edits to a subsystem already covered by an active PR. Do not modify, rebase, force-push, or clean up another agent's branch.
- Start independent work from current master on a new isolated branch. Keep each task narrowly scoped to one reviewable change.

## Task selection and testing

Before nontrivial work, inspect current master, active branches/PRs, `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md`. This handoff and the status sections of the other docs can become stale; verify current PRs and CI rather than treating snapshots as authoritative.

- Do not weaken negative tests to make them pass. For rejection tests, verify the proof reaches the intended rule and fails for the intended reason.
- Preserve the enforced proof corpus. Report the exact commit tested, Python test totals, coverage, enforced fixtures, informational fixtures, and known failures separately.
- Open implementation questions and proposed deviations should be raised with the owner before changing agreed semantics.
- Keep agent handoffs concise and actionable: identify the current branch/PR, what is being changed, what is blocked, and one next action.

## Repo owner

Claude, is there anything that ChatGPT can implement so that you don't have to?
