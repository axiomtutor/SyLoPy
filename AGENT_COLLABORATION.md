# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on current coordination.

## Current baseline

- **Master:** [`87fab58`](https://github.com/axiomtutor/SyLoPy/commit/87fab582399f0824bb7b0dbcc0d75b430ae2a679). PRs #41 (rule-registration audit tests), #42 (API documentation and regression examples), #43 (informational relation proofs), #45 (nonzero quotient guard), and #46 (skip redundant documentation-only push CI) are merged.
- **Latest full validation:** [GitHub Actions run #643](https://github.com/axiomtutor/SyLoPy/actions/runs/38656453820), on `87fab58`: 1,104 passed, 12 xfailed, and one known failure; coverage passed; enforced fixtures 80/80; informational fixtures 58/59.
- **Known ordinary failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, blocked by the deferred WLOG / Mutatis mutandis features. Do not mask it with xfail or implement those deferred rules without owner approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. ChatGPT/Copilot should focus on independent tests, docs, fixtures, and handoff unless coordinated with Claude.
## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope or affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: `Let n be a natural number` asserts the ordinary citable `Nat(n)` fact; `Let X be an integer` asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) must enforce the declared carrier.
- `Let Y be such a set. (Existence from L)` names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- **Quotient uniqueness:** owner decision (2026-10-14): require the denominator `a` to satisfy `not (a = Zero)`. The zero case does not determine a unique integer quotient; PR #45 implements the guard in the axiom and the public rule.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Landed theorem-promotion contracts

- **Hypotheses reach rules that require arbitrary constants** (`e56c67d`). `Uniqueness`, `UniversalGeneralization`, and `ExistentialElimination` reject constants occurring in hypotheses at any depth or constrained by declaration structure.
- **Promotion carries assumptions** (`e56c67d`). A theorem carries every hypothesis the proof took for granted; promotion refuses proofs relying on declaration metadata no formula states.
- **Promotion records theory requirements** (`866c5e9`). A promoted theorem records cited axioms and nonstandard rule requirements, and validates explicit conclusions/generalized names. The regression tests are in `pytest_tests/test_hypotheses_and_promotion.py`, `pytest_tests/test_promotion_requirements.py`, and `pytest_tests/test_theorem_promotion_audit.py`.
- **New remaining issue:** rule authorization and requirement-merging are class/name-based. PR #41 covers parameter-mismatched induction citations, unregistered theorem instances, unregistered subclasses of default logical rules, and constructor merging that drops a distinct required induction configuration. Master already has a probe for dropped promotion requirements.

## Merged work and current priorities

### Priority 1 — Implement the registered-rule soundness fixes from PR #41

[PR #41](https://github.com/axiomtutor/SyLoPy/pull/41) is merged. Its test-only regression suite, `pytest_tests/test_parameterized_rule_registration.py`, now provides acceptance criteria for Claude's implementation.

The existing issue has distinct paths that must all be addressed:

1. `ProofValidator._rule_is_registered` accepts a rule by class/subclass rather than semantic configuration. This lets a differently parameterized `InductionRule`, an unregistered `TheoremRule`, or a behavior-overriding subclass of `ReiterationRule` pass direct citation authorization.
2. `RuleContext.allows_rule` repeats class-based authorization for rules used as dependencies of promoted theorems.
3. The `rule_below` and `rule_hybrid` subproof validators have separate authorization branches; the regressions ensure a fix to ordinary citations does not leave these branches open.
4. `Proof.__init__` and `_promotion_requirements` deduplicate rules by type/name and can discard parameter-distinct requirements. Preserve parameter-equal separate instances as equivalent, but keep parameter-distinct configurations separate.
5. Direct Pairing elaboration embeds `PairingAxiomRule(witness_name="Y")` in a line without exporting that witness-specific configuration through `ElaboratedEntries.required_rules`. Generated witness-specific rules need an explicit authorization path, not a broad class-based bypass.

The suite contains positive controls: a distinct `InductionRule` instance with identical semantic parameters must remain usable. Run the canonical `./run_tests.sh`; report the known WLOG/ZFC failure separately. The goal is for the new rule-registration xfails to become passing tests without introducing new failures. Do not weaken the negative tests or authorize arbitrary subclasses just to make generated rules work.

### Independent PR under review — #47

[PR #47](https://github.com/axiomtutor/SyLoPy/pull/47), branch `chatgpt/elaboration-binder-capture-audit`, tests and fixes three elaboration-time capture paths left unaudited after PR #44:

- Set-builder equality expansion when a builder variable shadows an enclosing variable used in the range set.
- Replacement-builder expansion where a generated existential binder captured an outer range variable.
- Universal/existential bounded quantifiers with a binder that shadows the variable used by the range set.

The three new test functions represent four cases and compare the parsed surface expression with its intended plain-logic reading. The unique-existence phrase was already safe because its competitor name avoids all names in the condition and surrounding scope; the `Existence from L` path substitutes a `ConstantTerm` witness and does not suffer variable capture.

CI [run #38657003495](https://github.com/axiomtutor/SyLoPy/actions/runs/38657003495) on this PR: 1,108 passed, 12 xfailed, one known deferred ZFC/WLOG failure; coverage passed; enforced fixtures 80/80; informational fixtures 58/59. All new regressions pass. PR #47 is independent of the rule-registration implementation; no kernel files were edited. It awaits owner review.

### Other merged work

- **PR #42 — [Python API docs and end-to-end examples](https://github.com/axiomtutor/SyLoPy/pull/42):** adds runnable README examples and `pytest_tests/test_readme_python_api.py`, plus `source/testProofs/theoremPromotion.txt`, `source/testProofs/quantifierReasoning.txt`, and `pytest_tests/test_theorem_surface_citations.py`. The last test intentionally xfails on the current limitation: a titled theorem with premises cannot yet be parsed as `Title from L`. This is a separate parser issue; coordinate before touching `ProofJustification.py`, which Claude owns.
- **PR #43 — [Informational relation-proof examples](https://github.com/axiomtutor/SyLoPy/pull/43):** adds `source/testProofs/equivalenceRelationChaining.txt`, covering equivalence-relation chaining and partial-order antisymmetry. The examples are intentionally not promoted to reusable theorems because declaration-only relation metadata is not yet carried into promoted theorem requirements.
- **PR #45 — [Nonzero quotient denominator](https://github.com/axiomtutor/SyLoPy/pull/45):** implements the owner-approved `a != 0` guard on quotient uniqueness and tests against deriving `Zero/Zero = m`.
- **PR #46 — [Skip docs-only push CI](https://github.com/axiomtutor/SyLoPy/pull/46):** skips redundant push-triggered runs for Markdown-only/`todos.txt` changes while preserving full PR validation.
- **PR #48 — [Refresh post-merge status docs](https://github.com/axiomtutor/SyLoPy/pull/48):** updates README/TODO test counts from stale pre-merge figures to master `87fab58` / CI #643, corrects the status of PR #41, and removes the already-fixed quotient-uniqueness issue from the open issue list. Docs-only; CI run #647 is pending/running at handoff update time.

### Requests

- **Claude:** prioritize the PR #41 rule-authorization and semantic-deduplication implementation, with all citation/subproof/dependency paths covered. Keep the theorem-title surface-citation limitation as a separate task.
- **Owner:** review [PR #47](https://github.com/axiomtutor/SyLoPy/pull/47) (elaboration-time variable-capture fixes) and [PR #48](https://github.com/axiomtutor/SyLoPy/pull/48) (post-merge status documentation). Decide whether to assign the separate premise-carrying theorem citation fix after the rule-registration work.
- **ChatGPT/Copilot:** do not overlap Claude's kernel edits. Continue independent documentation/status maintenance, narrow regression coverage, or fixture work only where it materially helps.

## Coordination rules

- Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` before nontrivial work. Inspect master and active PRs; old handoff snapshots may be stale.
- Do not modify, rebase, force-push, or clean up another agent's branch. Start new work from current master and isolate it in a branch/PR.
- Preserve the enforced proof corpus, and report Python tests, coverage, enforced fixtures, informational fixtures, and the known failure separately.
- Do not implement deferred set-theory features without explicit owner approval. Do not merge or close PRs without owner approval.
- The `chatgpt-agent-guidance` branch is deliberately unmerged: it is the live coordination channel. Preserve it during any branch cleanup.
