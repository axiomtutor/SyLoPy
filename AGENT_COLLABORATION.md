# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This deliberately unmerged branch contains only changing coordination state. Keep it short; detailed rationale belongs in the relevant TODO entry, issue, or PR.

## Baseline and current state

- **Master:** [`883dc9e`](https://github.com/axiomtutor/SyLoPy/commit/883dc9e39b751cd940c63b0b9e62f418e9d03182). [PR #82](https://github.com/axiomtutor/SyLoPy/pull/82) also updates stale status text in the README.
- **[PR #81](https://github.com/axiomtutor/SyLoPy/pull/81) merged:** the named ZFC axiom-citation rules now accept the intended Union and Power Set instance forms. It adds 202 rule tests and six informational proofs. The PR reports fresh-clone tests on Python 3.12 and 3.13: 1,425 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 81/81; informational fixtures 69/70. These are PR-reported results, not a claim that the merge commit has a green CI run.
- The named axiom-citation rules are no longer deferred. The remaining owner decision in `todos.txt` §5 is whether to retire generic `(Axiom)` citations; do not remove them without explicit approval. `Mutatis mutandis` remains deferred.

## One known blocker

[Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) tracks the sole reported test failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. WLOG replay changes `x=a` to `x=b`, then wrongly substitutes the invariant pair characterization on line 3. The bounded fix is to preserve an original visible citation when it remains valid, and remap only when substitution is necessary. **This touches Claude-owned `source/ProofLogic.py`; coordinate with Claude before editing it.** Do not weaken tests or mask the fixture failure.

## Next action

Coordinate with Claude before making any kernel change for issue #75. Keep other work small and isolated; do not broaden WLOG or start `Mutatis mutandis` without explicit owner approval.
