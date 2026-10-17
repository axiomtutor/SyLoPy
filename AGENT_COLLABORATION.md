# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on coordination.

## Current baseline and open work

- **Master:** [`6a52744`](https://github.com/axiomtutor/SyLoPy/commit/6a527446c3db8053556704e9f49dcc4bd2a6f02d), following PR #68.
- **Open PRs:** [#70](https://github.com/axiomtutor/SyLoPy/pull/70) fixes unsound directions in `SetPropertyRule`; [#71](https://github.com/axiomtutor/SyLoPy/pull/71) adds the owner-approved equality-orientation behavior for Set property. #71 contains #70's commit and depends on #70; merge #70 first.
- **PR #70 scope:** `source/SetTheory.py` and `pytest_tests/test_set_property.py`. It makes the equality-disjunct case one-way only where required by soundness.
- **PR #71 scope:** the same files plus `todos.txt`. It allows an equality to be read in either orientation in the narrowly defined Set property cases; it does not add general substitution.
- **Latest reported verification:** #71 reports 1,219 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 81/81; informational fixtures 61/62. The one failure is `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, at WLOG replay: no visible counterpart for cited line '3' after substituting the chosen case. PR #70 reports 1,211 passed with the same single failure and 81/81 enforced fixtures. These are PR-reported results, not a claim that a new run was performed during this handoff refresh.
- **Master comparison:** PR #71 reports master `6a52744` at 1,200 passed, 1 failed, 1 xfailed. The README and `todos.txt` snapshots are stale; use current PR reports and CI for status rather than copying their old figures.
- **Branch discipline:** `chatgpt-agent-guidance` is deliberately unmerged and is the live coordination channel. Preserve it; update this handoff in place rather than merging or recreating the branch.

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
