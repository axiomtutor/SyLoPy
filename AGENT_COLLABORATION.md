# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on current coordination.

## Current baseline

- **Master:** [`bc990e5`](https://github.com/axiomtutor/SyLoPy/commit/bc990e57ce71f9e607ff8e227399a6921289d40a), the merge of PR #56 (rule authorization by configuration).
- **Pull requests:** none open at this inspection. Recent merges: #52 (coordinated membership declarations), #53 (TODO bookkeeping), #55 (set-equality example), and #56 (rule-authorization soundness fix).
- **CI:** PR #56's tested head reported no new failures, but I have not independently verified a full run on the merge commit. Do not present the older counts in `README.md` or `todos.txt` as current-master results.
- **Known failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, blocked by deferred WLOG / Mutatis mutandis. Do not mask it or implement those rules without explicit owner approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. Coordinate before editing either file.

## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope or affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: `Let n be a natural number` asserts the ordinary citable `Nat(n)` fact; `Let X be an integer` asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) enforce the declared carrier.
- `Let Y be such a set. (Existence from L)` names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- **Quotient uniqueness:** owner decision (2026-10-14): require denominator `a` to satisfy `not (a = Zero)`. PR #45 implements the guard.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Current work and coordination

- **Open issue #54:** [Allow surface citations of premise-carrying theorems](https://github.com/axiomtutor/SyLoPy/issues/54). The core API supports the citation, but surface syntax such as `Property Transport from 3` is still an expected-failure regression. `source/ProofJustification.py` is Claude-owned; coordinate before touching it.
- **Resolved soundness work:** PR #56 implements configuration-based rule authorization and closes issues #49–#51 (authorization, parameter-aware requirement merging, and witness-specific Pairing registration). Do not treat these as outstanding tasks.
- **Recent merged work:** #52 fixes coordinated membership declarations; #53 aligns TODO tracking with the soundness issues; #55 adds the set-equality-implies-mutual-subsets example; #56 fixes rule authorization. No open PR currently requires review.
- **Testing:** preserve the enforced proof corpus. Report Python tests, coverage, enforced fixtures, informational fixtures, and the known WLOG failure separately. State which exact commit a test run covers.
- **Task selection:** check current `master`, active branches/PRs, `todos.txt`, and owner direction before taking work. The owner has final authority; never infer approval for deferred features from their presence in the TODO ledger.

## Coordination rules

- Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` before nontrivial work. Inspect master and active PRs; this handoff can become stale.
- Do not modify, rebase, force-push, or clean up another agent's branch. Start independent work from current master and isolate it in a branch/PR.
- Avoid concurrent edits to the same subsystem. If Claude owns a kernel file, prefer an independent test, parser-oracle, documentation, or other isolated task until coordinated.
- Do not weaken negative tests to make them pass. For a rejection test, verify the proof reaches the intended rule and fails for the intended reason.
- The `chatgpt-agent-guidance` branch is deliberately unmerged and is the live coordination channel. Preserve it during branch cleanup.
## Coordination rules

- Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` before nontrivial work. Inspect master and active PRs; old handoff snapshots may be stale.
- Do not modify, rebase, force-push, or clean up another agent's branch. Start new work from current master and isolate it in a branch/PR.
- Preserve the enforced proof corpus, and report Python tests, coverage, enforced fixtures, informational fixtures, and the known failure separately.
- Do not implement deferred set-theory features without explicit owner approval. Do not merge or close PRs without owner approval.
- The `chatgpt-agent-guidance` branch is deliberately unmerged: it is the live coordination channel. Preserve it during any branch cleanup.
