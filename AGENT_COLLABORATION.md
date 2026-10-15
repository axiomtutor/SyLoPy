# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on current coordination.

## Current baseline

- **Master:** [`40630d9`](https://github.com/axiomtutor/SyLoPy/commit/40630d980d7c0fcb12d9a3d6a510ef7d900e799a), the merge of PR #48. PRs #41–#48 are merged; see below for notable changes.
- **Latest detailed test evidence:** PR #52 CI [run #651](https://github.com/axiomtutor/SyLoPy/actions/runs/38688488640), on branch `chatgpt/compound-declaration-membership-premise`: 1,112 passed, 12 xfailed, one known failure; coverage passed; enforced fixtures 80/80; informational fixtures 58/59. This validates the PR head, not master.
- **Known ordinary failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, blocked by deferred WLOG / Mutatis mutandis. Do not mask it with xfail or implement those deferred rules without owner approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. Avoid parallel edits there unless coordinated with Claude.

## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope or affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: `Let n be a natural number` asserts the ordinary citable `Nat(n)` fact; `Let X be an integer` asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) enforce the declared carrier.
- `Let Y be such a set. (Existence from L)` names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- **Quotient uniqueness:** owner decision (2026-10-14): require denominator `a` to satisfy `not (a = Zero)`. PR #45 implements the guard.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Landed theorem-promotion contracts

- **Hypotheses reach rules that require arbitrary constants** (`e56c67d`). `Uniqueness`, `UniversalGeneralization`, and `ExistentialElimination` reject constants occurring in hypotheses at any depth or constrained by declaration structure.
- **Promotion carries assumptions** (`e56c67d`). A theorem carries every hypothesis the proof took for granted; promotion refuses proofs relying on declaration metadata no formula states.
- **Promotion records theory requirements** (`866c5e9`). A promoted theorem records cited axioms and nonstandard rule requirements, and validates explicit conclusions/generalized names. Tests: `pytest_tests/test_hypotheses_and_promotion.py`, `pytest_tests/test_promotion_requirements.py`, and `pytest_tests/test_theorem_promotion_audit.py`.
- **Remaining soundness gap:** rule authorization and requirement merging are class/name-based. PR #41 adds regression probes; issues #49 and #50 split implementation and parameter-aware requirement tracking. A separate witness-specific Pairing requirement issue is #51.

## Merged work and open tasks

### Priority 1 — Registered-rule authorization: issue #49

[Issue #49](https://github.com/axiomtutor/SyLoPy/issues/49) is the central soundness task for Claude's kernel implementation. Start with merged [PR #41](https://github.com/axiomtutor/SyLoPy/pull/41) and its `pytest_tests/test_parameterized_rule_registration.py` regressions. It covers:
1. `ProofValidator._rule_is_registered` for direct citations.
2. `RuleContext.allows_rule` for promoted theorem dependencies.
3. The separate `rule_below` and `rule_hybrid` validator paths.
4. Parameter-aware authorization: semantically equivalent separate instances remain accepted, but a parameter-mismatched rule, an unregistered `TheoremRule`, or behavior-overriding unregistered subclass must not be authorized.
   
Do not weaken negative tests to make them pass. Keep parameter-distinct requirement deduplication (#50) and pairing-witness requirement tracking (#51) separately scoped, even though they interact with the overall soundness story.

### Separate requirement-tracking issues

- [Issue #50](https://github.com/axiomtutor/SyLoPy/issues/50): preserve semantically distinct parameterized rule requirements in `Proof.__init__` and `_promotion_requirements`, while still deduplicating equivalent rules.
- [Issue #51](https://github.com/axiomtutor/SyLoPy/issues/51): ensure elaboration exports the witness-specific `PairingAxiomRule` used in its line justification.

### Independent PR under review — #52

[PR #52](https://github.com/axiomtutor/SyLoPy/pull/52), branch `chatgpt/compound-declaration-membership-premise`, fixes an unrelated parser edge case recorded in `todos.txt`: in a coordinated declaration such as `Let X be any set, a in X`, the membership declaration was absorbed into the prior descriptor or parsed as unsupported formula syntax.

The current head:
- routes no-copula membership clauses through the existing membership-declaration path, so the element is declared and its membership formula is recorded as a premise;
- tests `a in X`, `a is in X`, `a is not in X`, and a relation descriptor followed by a membership declaration;
- updates the TODO ledger.

CI [run #651](https://github.com/axiomtutor/SyLoPy/actions/runs/38688488640) reports 1,112 passed, 12 xfailed, and only the pre-existing ZFC/WLOG failure; coverage passed; enforced fixtures 80/80; informational fixtures 58/59. The first PR run caught two new test failures; the current head fixes them. No kernel files changed. The PR is ready for owner review and should not be merged by an agent.

### Independent documentation PR — #53

[PR #53](https://github.com/axiomtutor/SyLoPy/pull/53) updates the rule-registration section of `todos.txt` so it matches the separate GitHub issues: #49 for authorization, #50 for parameter-aware requirement deduplication, and #51 for witness-specific pairing requirements. CI [run #654](https://github.com/axiomtutor/SyLoPy/actions/runs/38688771344) reports 1,108 passed, 12 xfailed, and only the established ZFC/WLOG failure; coverage and enforced fixtures passed. This is documentation-only and awaits owner review; no design or implementation changes.

[PR #55](https://github.com/axiomtutor/SyLoPy/pull/55) adds a fourth independent theorem to `tests/setTheoryProofs/basic_theorems.txt`: equality implies mutual subset inclusion, proved using the existing subset expansion and Leibniz substitution. The existing Python inventory checks were extended to include proof #4. CI [run #662](https://github.com/axiomtutor/SyLoPy/actions/runs/38689343525) reports 1,108 passed, 12 xfailed, and only the established ZFC/WLOG failure; coverage passed, enforced fixtures 80/80, informational fixtures 59/60. The new proof passes. The PR is ready for owner review and changes no production rules.

### Other separately tracked work

- **Issue #54** — [Allow surface citations of premise-carrying theorems](https://github.com/axiomtutor/SyLoPy/issues/54). The expected-failure probe from PR #42 shows that `Title from L` is not yet parsed for promoted theorems with premises, though the core API can express the citation. `source/ProofJustification.py` is still Claude-owned; coordinate before implementation.

### Other merged work

- **PR #42** — [Python API docs and end-to-end examples](https://github.com/axiomtutor/SyLoPy/pull/42). Its theorem-surface-citation regression remains an expected failure: a titled theorem with premise lines cannot yet be parsed as `Title from L`. Coordinate before touching `ProofJustification.py`.
- **PR #43** — [Informational relation-proof examples](https://github.com/axiomtutor/SyLoPy/pull/43), covering equivalence-relation chaining and partial-order antisymmetry.
- **PR #45** — [Nonzero quotient denominator](https://github.com/axiomtutor/SyLoPy/pull/45).
- **PR #46** — [Skip docs-only push CI](https://github.com/axiomtutor/SyLoPy/pull/46).
- **PR #44** — [Refuse variable capture in quantifier matching and schema instances](https://github.com/axiomtutor/SyLoPy/pull/44). Merged; adds variable-capture and schema side conditions.
- **PR #47** — [Prevent outer-variable capture in set syntax elaboration](https://github.com/axiomtutor/SyLoPy/pull/47). Merged; fixes set-builder equality, replacement-builder and bounded-quantifier capture cases.
- **PR #48** — [Refresh status docs after soundness audit merges](https://github.com/axiomtutor/SyLoPy/pull/48). Merged; refreshes the status snapshot and corrects the rule-registration issue description.

## Requests

- **Claude:** continue the registered-rule authorization implementation against issue #49 and PR #41 regressions. Coordinate the separate issues #50 and #51 rather than treating all three as one patch.
- **Owner:** review [PR #52](https://github.com/axiomtutor/SyLoPy/pull/52). No merge action has been taken.
- **ChatGPT/Copilot:** avoid Claude's kernel edits; work on isolated parser, regression, documentation, or test tasks that do not cross explicit approval boundaries.

## Coordination rules

- Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` before nontrivial work. Inspect master and active PRs; old handoff snapshots may be stale.
- Do not modify, rebase, force-push, or clean up another agent's branch. Start new work from current master and isolate it in a branch/PR.
- Preserve the enforced proof corpus, and report Python tests, coverage, enforced fixtures, informational fixtures, and the known failure separately.
- Do not implement deferred set-theory features without explicit owner approval. Do not merge or close PRs without owner approval.
- The `chatgpt-agent-guidance` branch is deliberately unmerged: it is the live coordination channel. Preserve it during any branch cleanup.
