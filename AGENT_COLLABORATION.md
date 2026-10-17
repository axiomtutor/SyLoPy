# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on coordination.

## Current baseline and open work

- **Master:** [`12deb44`](https://github.com/axiomtutor/SyLoPy/commit/12deb44456737faf08c14248e3a27445aad69698), the merge of PR #71 on 2026-10-17, after PR #70 ([merge commit](https://github.com/axiomtutor/SyLoPy/commit/5793661f590f8793c640bf47777e7e85a533c68e)).
- **Open PRs / issues:** none returned by the repository's GitHub searches on 2026-10-17. The recent feature branches `claude/set-property-disjunct-direction` and `claude/set-property-equality-orientation` are merged.
- **Latest reported verification:** PR #71's exact head [`3955a39`](https://github.com/axiomtutor/SyLoPy/commit/3955a396197be00676252ee261f2fe34b914f693) reports 1,219 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 81/81; informational fixtures 61/62. Python 3.12 and 3.13 reportedly agree. The known failure is `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`: WLOG replay has no visible counterpart for cited line '3' after substituting the chosen case (line 5.2.4).
- **Verification caveat:** this is a PR-head report, not a fresh run at merge commit `12deb44`. The combined-status endpoint returned no status records for that merge commit, and the workflow-run lookup available here only returns pull-request-triggered runs; therefore post-merge CI is not independently confirmed here. Do not describe this as a newly passing master run.
- **Design boundary:** WLOG equality-case replay landed in PR #63 and is implemented; its citation-remapping failure above remains. `Mutatis mutandis` and the named ZFC axiom-citation rules remain deferred pending explicit owner go-ahead.
- **Coordination branch:** `chatgpt-agent-guidance` remains deliberately unmerged and is the live coordination channel. Preserve it and update this handoff in place.

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
