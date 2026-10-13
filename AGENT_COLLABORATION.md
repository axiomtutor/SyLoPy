# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. Keep detailed design decisions in `todos.txt`, implementation discussion in PRs, and this file focused on current coordination.

## Current baseline

- **Master:** [`d8b8d20`](https://github.com/axiomtutor/SyLoPy/commit/d8b8d20a8dce4f861756c455f1d914167c7ab830). PRs #38 (theorem-promotion audit) and #40 (status docs) are merged.
- **Validation:** [CI run #38341702058](https://github.com/axiomtutor/SyLoPy/actions/runs/38341702058): 1,068 passed, 3 xfailed, 1 known Python failure; coverage passed; enforced fixtures 79/79; informational fixtures 51/52.
- **Known ordinary failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, still blocked by the deferred WLOG / Mutatis mutandis features. Do not mask it with xfail or implement the deferred rules without owner approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. ChatGPT/Copilot may add focused regression tests and documentation but should not edit those files without coordination.

## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope or affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: `Let n be a natural number` asserts the ordinary citable `Nat(n)` fact; `Let X be an integer` asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) must enforce the declared carrier.
- `Let Y be such a set. (Existence from L)` names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Landed theorem-promotion contracts

- **Hypotheses reach rules that require arbitrary constants** (`e56c67d`). `Uniqueness`, `UniversalGeneralization`, and `ExistentialElimination` reject constants occurring in hypotheses at any depth or constrained by declaration structure.
- **Promotion carries assumptions** (`e56c67d`). A theorem carries every hypothesis the proof took for granted; promotion refuses proofs relying on declaration metadata no formula states.
- **Promotion records theory requirements** (`866c5e9`). A promoted theorem records cited axioms and nonstandard rule requirements, and validates explicit conclusions/generalized names. The regression tests are in `pytest_tests/test_hypotheses_and_promotion.py`, `pytest_tests/test_promotion_requirements.py`, and `pytest_tests/test_theorem_promotion_audit.py`.
- **New remaining issue:** rule authorization and requirement-merging are class/name-based. PR #41 covers parameter-mismatched induction citations, unregistered theorem instances, unregistered subclasses of default logical rules, and constructor merging that drops a distinct required induction configuration. Master already has a probe for dropped promotion requirements.

## Active pull requests

### PR #41 — Audit registered inference-rule instances

[PR #41](https://github.com/axiomtutor/SyLoPy/pull/41), branch `chatgpt/parameterized-rule-registration-audit`, head [`56f9a91`](https://github.com/axiomtutor/SyLoPy/commit/56f9a913ccb7f957b700b467f35b805150acd31d). Test-only; no kernel implementation changes.

- Probe 1 directly cites `InductionRule("Nat", Zero, Succ)` while registering only `InductionRule("Int", ZeroInt, SuccInt)`. The current validator accepts the parameter-mismatched instance via class-only `ProofValidator._rule_is_registered`.
- Probe 2 registers a legitimately promoted theorem for `P -> P`, then directly cites an unregistered `TheoremRule` with arbitrary conclusion `Q`. The current validator accepts it because another `TheoremRule` instance is registered.
- Probe 3 defines an unregistered subclass of default `ReiterationRule` whose overridden `applies` says arbitrary `Q) follows from no premises. Since `isinstance(forged, ReiterationRule)` passes, the current allowlist authorizes the subclass's changed inference behavior.
- Probe 4 isolates constructor-level deduplication: `Proof.__init__` drops one of two distinct Nat and Int `InductionRule` requirements carried by `ElaboratedEntries`, based only on type/name. Master already has `test_promotion_preserves_each_parameterized_rule_requirement` for the analogous deduplication in `_promotion_requirements`.
- Positive control: a matching registered Nat induction instance remains usable.
- CI [run #38343194694](https://github.com/axiomtutor/SyLoPy/actions/runs/38343194694): 1,069 passed, 7 xfailed, plus the known deferred ZFC fixture failure; coverage passed; enforced fixtures 79/79; informational fixtures 51/52. The subclass-substitution probe is reproduced as an expected failure.
- Implementation must address both authorization checks (`ProofValidator._rule_is_registered` and `RuleContext.allows_rule`) and both type/name deduplication sites (`Proof.__init__` and `_promotion_requirements`). Pairing trace: `SetTheory.elaborate_pairing_witness` embeds `PairingAxiomRule(witness_name=...)` directly in a line but does not add it to `context.extra_rules`; `ElaboratedEntries.required_rules` exports only environment rules plus `context.extra_rules`, and the environment has only generic `PairingAxiomRule()`. Class matching masks that it is not explicitly registered. A concrete suggested path was posted in [PR #41 comment](https://github.com/axiomtutor/SyLoPy/pull/41#issuecomment-6137881949): explicitly register the generated line rule (or collect it from elaborated entries) and preserve both generic and witness-specific configurations through semantic deduplication.

### PR #42 — Refresh status, document and test Python API, record rule-registration gap

[PR #42](https://github.com/axiomtutor/SyLoPy/pull/42), branch `chatgpt/refresh-status-after-promotion-audit`, head [`6a20fac`](https://github.com/axiomtutor/SyLoPy/commit/6a20facecfa0616f7b6cb876d4a9522f898193d7). Documentation and regression-test only; no production code or kernel semantics change.

- Refreshes README/TODO snapshot to master CI #38341702058 at d8b8d20.
- Adds the README's “Recommended Python API” section: self-contained examples for surface checking/subproofs, promoting a theorem about an arbitrary object and citing it in a second proof, and core proof construction from a fixed type's resources.
- Adds `pytest_tests/test_readme_python_api.py`, which executes the three marked README Python examples in CI. The snippets are tested independently, so undefined variables/imports or API behavior changes fail the suite.
- Adds informational fixture `source/testProofs/theoremPromotion.txt`, showing a titled theorem for an arbitrary object and a later proof citing that title for a different object; README links to this example.
- Marks the public API usage, theory-boundary documentation, and small end-to-end example TODOs checked off in `todos.txt`; the general goal of expanding informational examples remains open.
- Records PR #41's registered-rule soundness issue, including parameter mismatch, unregistered theorem instances / subclasses, requirement deduplication, and the Pairing witness authorization compatibility concern.
- Latest CI [run #38344187526](https://github.com/axiomtutor/SyLoPy/actions/runs/38344187526): 1,071 passed, 3 xfailed, one known deferred ZFC failure; coverage passed; enforced fixtures 79/79; informational fixtures 53/54. The source informational corpus passes 41/41 (including the added fixture); the only ordinary Python and informational-fixture failure remains the known `test_zfc_remaining_axioms_fixture_all_pass` / WLOG-Mutatis-mutandis blocker.

## Requests

- **Claude:** investigate/fix rule authorization in both `ProofValidator._rule_is_registered` and `RuleContext.allows_rule`, including subclass substitution, plus requirement/constructor deduplication that compares parameterized rules only by type and name. Preserve matching registered rules and give generated witness-specific rules an explicit authorization path.
- **Owner:** review PRs #41 and #42. No owner design decision is currently needed for the reproduced allowlist bypass.
- **Copilot:** unclaimed; avoid overlapping the kernel registration implementation until coordinated.

## Coordination rules

- Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` before nontrivial work. Inspect master and active PRs; old handoff snapshots may be stale.
- Do not modify, rebase, force-push, or clean up another agent's branch. Start new work from current master and isolate it in a branch/PR.
- Preserve the enforced proof corpus, and report Python tests, coverage, enforced fixtures, informational fixtures, and the known failure separately.
- Do not implement deferred set-theory features without explicit owner approval. Do not merge or close PRs without owner approval.
- The `chatgpt-agent-guidance` branch is deliberately unmerged: it is the live coordination channel. Preserve it during any branch cleanup.
