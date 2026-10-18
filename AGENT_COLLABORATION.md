# Live Collaboration Handoff

Use the [stable guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules; [PR #82](https://github.com/axiomtutor/SyLoPy/pull/82) proposes the needed status corrections after PR #81. This deliberately unmerged branch contains only changing coordination state. Keep rationale in the TODO, issue, or PR.

## Baseline and active follow-ups

- **Master:** [`883dc9e`](https://github.com/axiomtutor/SyLoPy/commit/883dc9e39b751cd940c63b0b9e62f418e9d03182).
- **[PR #81](https://github.com/axiomtutor/SyLoPy/pull/81) merged:** named Pairing, Union, Power Set, and Infinity axiom-citation rules now support intended instance forms. Reported fresh-clone tests on Python 3.12/3.13: 1,425 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 69/70. The sole failure is #75.
- **[PR #82](https://github.com/axiomtutor/SyLoPy/pull/82):** docs-only refresh of `README.md`, `AGENT_COLLABORATION.md`, and `todos.txt`. [CI run #753](https://github.com/axiomtutor/SyLoPy/actions/runs/39082070261) has only the known #75 fixture failure; no other test failed.
- **[PR #83](https://github.com/axiomtutor/SyLoPy/pull/83):** adds WLOG regression tests that future-line and closed-sibling references remain invalid. Does not touch kernel code; CI status pending at last check.

## One known blocker

[Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) is the sole reported test failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. WLOG replay changes `x=a` to `x=b`, then wrongly substitutes the invariant pair characterization on line 3. Preserve an original visible citation when it remains valid, remapping only when necessary. **The fix touches Claude-owned `source/ProofLogic.py`; coordinate with Claude before editing.** Do not weaken tests or mask the failure.

The named axiom rules are implemented. The remaining owner decision is whether to retire generic `(Axiom)` citations. `Mutatis mutandis` and the symbolic defining-property behavior remain unfinished; the latter needs a clear implementation model before changing semantics.
