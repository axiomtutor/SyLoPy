# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on current coordination.

## Current baseline

- **Master:** [`bc990e5`](https://github.com/axiomtutor/SyLoPy/commit/bc990e57ce71f9e607ff8e227399a6921289d40a), following PR #56.
- **Open PRs:** #57 parser-oracle scope coverage; #58 set-theory proof examples; #59 remove superseded parser paths; #60 asymmetric-relation example; #61 reject trailing separators; #63 WLOG replay; #65 equality-disjunct Set property; #67 premise-carrying theorem citations; #68 README status refresh.
- **Closed PRs:** #62 is superseded by #67, which includes its implementation; #66's TODO changes are also included in #67; #64 is closed.
- **CI baseline:** PR #67 records a comparison against master `bc990e5`: 1,138 passed, 1 failed, and 2 xfailed; coverage passed and all 80 enforced fixtures passed. PR #68's run #692 on its merge ref reproduced the same counts and known failure, with 59/60 informational fixtures passing. Treat these as recorded runs against their stated commits, not as a claim about a later `master`.
- **Known failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, blocked by deferred WLOG / Mutatis mutandis. Do not mask it.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. Coordinate before editing either file.
## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope or affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: `Let n be a natural number` asserts the ordinary citable `Nat(n)` fact; `Let X be an integer` asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) enforce the declared carrier.
- `Let Y be such a set. (Existence from L)` names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- **Quotient uniqueness:** owner decision (2026-10-14): require denominator `a` to satisfy `not (a = Zero)`. PR #45 implements the guard.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Landed soundness contracts

- Arbitrary-constant rules (`Uniqueness`, `UniversalGeneralization`, `ExistentialElimination`) account for hypotheses at any depth and declaration constraints.
- Theorem promotion carries all assumptions, rejects unstated structural metadata, validates explicit conclusions/generalized names, and records required axioms and nonstandard rules.
- PR #56 now authorizes rules by configuration; issues #49–#51 are resolved. Regression coverage includes direct, subproof, hybrid, and promoted-theorem paths.

## Current work and coordination

- **Theorem citations / TODO status:** PR #67 implements premise-carrying theorem citations and includes the resolved-soundness TODO updates formerly proposed in #66. PRs #62 and #66 are closed to prevent duplicate review and merge work. Do not duplicate #67's work or begin another change in Claude-owned `ProofJustification.py` without coordination.
- **Independent cleanup/docs:** PR #59 removes dead parser paths; #68 refreshes the README status snapshot.
- **Examples and parser regressions:** PR #57 adds parser-oracle scope cases, #58 expands set-theory examples, #60 adds an asymmetric-relation theorem, and #61 rejects trailing separators. Review their CI and avoid duplicating the same cases.
- **Deferred feature PRs:** #63 implements WLOG replay and #65 extends Set property. The TODO and design rules explicitly require owner approval for these features; do not treat a general instruction to continue work as authorization to expand their scope or merge them.
- **Resolved soundness work:** PR #56 implements configuration-based rule authorization and closes issues #49–#51. Do not treat these as outstanding tasks.
- **Testing:** preserve the enforced proof corpus. Report Python tests, coverage, enforced fixtures, informational fixtures, and the known WLOG failure separately. State which exact commit a test run covers.
- **Task selection:** check current `master`, active branches/PRs, `todos.txt`, and owner direction before taking work. The owner has final authority; never infer approval for deferred features from their presence in the TODO ledger.
## Coordination rules

- Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` before nontrivial work. Inspect master and active PRs; this handoff can become stale.
- Do not modify, rebase, force-push, or clean up another agent's branch. Start independent work from current master and isolate it in a branch/PR.
- Avoid concurrent edits to the same subsystem. If Claude owns a kernel file, prefer an independent test, parser-oracle, documentation, or other isolated task until coordinated.
- Do not weaken negative tests to make them pass. For a rejection test, verify the proof reaches the intended rule and fails for the intended reason.
- The `chatgpt-agent-guidance` branch is deliberately unmerged and is the live coordination channel. Preserve it during branch cleanup.

# Repo owner

Claude, is there anything that ChatGPT can implement so that you don't have to?