# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on coordination.

## Current baseline and open work

- **Master:** [`5d519db`](https://github.com/axiomtutor/SyLoPy/commit/5d519db3a2d30ea50a24467c751bdddb8fbf8dc7), after PRs #72–#74 merged.
- **Active PRs:**
  - [#76](https://github.com/axiomtutor/SyLoPy/pull/76) refreshes README/TODO status and records the WLOG failure cause. Integrated-tree workflow [#720](https://github.com/axiomtutor/SyLoPy/actions/runs/39051347643): 1,220 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 62/63. Only failure is the known informational ZFC/WLOG fixture.
  - [#77](https://github.com/axiomtutor/SyLoPy/pull/77) adds a worked partial-order cycle proof. Workflow [#722](https://github.com/axiomtutor/SyLoPy/actions/runs/39051441796): 1,220 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 63/64. The new proof passes.
- **Merged work:** [PR #72](https://github.com/axiomtutor/SyLoPy/pull/72) refreshed status after #70/#71; [PR #73](https://github.com/axiomtutor/SyLoPy/pull/73) added a surface uniqueness regression; [PR #74](https://github.com/axiomtutor/SyLoPy/pull/74) added an equivalence-relation proof.
- **Known WLOG failure:** tracked in [issue #75](https://github.com/axiomtutor/SyLoPy/issues/75). In `zfc_remaining_axioms.txt` line 5.2.4, replaying `x=a` as `x=b` substitutes `a -> b` into external line 3, changing its pair characterization `(u=a or u=b)` to `(u=b or u=b)`. That stronger property is not established for the existing set Y. Preserve the original outer citation when it still justifies the transformed line; use a substituted counterpart when a cited fact genuinely needs substitution. The replay implementation is in Claude-owned `source/ProofLogic.py`; coordinate before editing it.
- **Deferred work:** `Mutatis mutandis` and named ZFC axiom-citation rules remain deferred pending explicit owner approval.
- **Coordination branch:** `chatgpt-agent-guidance` remains deliberately unmerged. Preserve it and update this handoff in place.

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
