# Live Collaboration Handoff

Use the [stable agent guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for architecture, ownership, testing, and context-loading rules. This branch is deliberately unmerged and contains only current coordination state. Keep it short; detailed rationale belongs in the relevant TODO entry, issue, or PR.

## Baseline and open work

- **Master:** [`12dcf99`](https://github.com/axiomtutor/SyLoPy/commit/12dcf99cf28544e09776f78b4deb07186518c0d6). PRs #72–#77 are merged.
- **[PR #78](https://github.com/axiomtutor/SyLoPy/pull/78) — natural-number existential syntax.** Adds multi-word existential kinds through the theory's predicate parser and tests `there exists a natural number n such that P(n)` as `exists n, (Nat(n) and P(n))`. CI [#729](https://github.com/axiomtutor/SyLoPy/actions/runs/39052110870): 1,223 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 81/81; informational fixtures 63/64.
- **[PR #79](https://github.com/axiomtutor/SyLoPy/pull/79) — status-doc refresh.** Docs only. CI [#734](https://github.com/axiomtutor/SyLoPy/actions/runs/39052412599): 1,220 passed, 1 failed, 1 xfailed; coverage passed; enforced fixtures 81/81; informational fixtures 63/64.
- **[PR #80](https://github.com/axiomtutor/SyLoPy/pull/80) — agent context cleanup.** Shrinks stable `AGENT_COLLABORATION.md` from 91 to 44 lines, replaces read-everything guidance with targeted context loading, and corrects stale WLOG/Set property status. CI [#736](https://github.com/axiomtutor/SyLoPy/actions/runs/39053733128): 1,220 passed, 1 failed, 1 xfailed; coverage passed; enforced 81/81; informational 63/64. Only failure is issue #75.

## One known blocker

[Issue #75](https://github.com/axiomtutor/SyLoPy/issues/75) tracks the only failing fixture, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. WLOG replay changes `x=a` to `x=b`, then wrongly substitutes the invariant pair characterization on line 3. The intended bounded fix is to preserve an original visible citation when it remains valid, and substitute/remap only when necessary. **The fix touches Claude-owned `source/ProofLogic.py`; coordinate with Claude before editing it.** Do not weaken tests or mask the fixture failure.

`Mutatis mutandis` and the named ZFC axiom-citation rules remain explicitly deferred pending owner approval.

## Next action

First let the owner review PRs #78–#80. For implementation beyond them, coordinate on issue #75 before any kernel change. Preserve this branch as the live handoff; do not merge it as a substitute for the stable guide.
