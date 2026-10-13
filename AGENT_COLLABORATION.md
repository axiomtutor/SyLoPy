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

[PR #41](https://github.com/axiomtutor/SyLoPy/pull/41), branch `chatgpt/parameterized-rule-registration-audit`, head [`301ffb3`](https://github.com/axiomtutor/SyLoPy/commit/301ffb3a9b3e43eff174143ff1106927e18e31e6). Test-only; no kernel implementation changes.

- Probe 1 directly cites `InductionRule("Nat", Zero, Succ)` while registering only `InductionRule("Int", ZeroInt, SuccInt)`. Current class-only `ProofValidator._rule_is_registered` accepts the mismatch.
- Probe 2 registers a validated theorem for `P -> P`, then cites a separate, unregistered `TheoremRule` concluding arbitrary `Q`; class-level matching accepts it.
- Probe 3 defines an unregistered subclass of default `ReiterationRule` whose overridden `applies` accepts arbitrary `Q) with no premises. It passes the `isinstance` allowlist.
- Probe 4 shows `Proof.__init__` discarding one of two different Nat/Int `InductionRule` configurations provided through `ElaboratedEntries.required_rules`, due to type/name deduplication. Master already has `test_promotion_preserves_each_parameterized_rule_requirement` for analogous loss in `_promotion_requirements`.
- Positive semantic-equivalence control was strengthened: the line cites a Nat induction rule object distinct from the registered object but with identical `type_predicate`, `zero_term`, and `succ_symbol`. A sound fix should allow equivalent configuration while rejecting distinct parameters.
- The latest test run before that control update is [CI #38343194694](https://github.com/axiomtutor/SyLoPy/actions/runs/38343194694): 1,069 passed, 7 xfailed, one known deferred ZFC fixture failure; coverage passed; enforced fixtures 79/79; informational fixtures 51/52. CI for head `301ffb3` is queued at [#38344704748](https://github.com/axiomtutor/SyLoPy/actions/runs/38344704748).
- Implementation must handle both authorization checks (`ProofValidator._rule_is_registered` and `RuleContext.allows_rule`) and both type/name deduplication sites (`Proof.__init__` and `_promotion_requirements`). Pairing trace: `SetTheory.elaborate_pairing_witness` embeds `PairingAxiomRule(witness_name=...)` in the line justification but does not add it to `context.extra_rules`; the environment exports only generic `PairingAxiomRule()`. Class-based authorization masks that it is not explicitly registered. See [PR #41 comment](https://github.com/axiomtutor/SyLoPy/pull/41#issuecomment-6137881949) for a concrete registration path.

### PR #42 — Refresh status, document and test Python API, record rule-registration gap

[PR #42](https://github.com/axiomtutor/SyLoPy/pull/42), branch `chatgpt/refresh-status-after-promotion-audit`, head [`234ff18`](https://github.com/axiomtutor/SyLoPy/commit/234ff1842d18ef517ea628a57ae9fcf4adaccf14). Documentation, fixtures, and regression tests only; no production/kernel changes.

- Refreshes README/TODO snapshot to master CI #38341702058 at d8b8d20.
- Adds the README's “Recommended Python API” section with self-contained examples for surface proof checking/subproofs, promoting an identity theorem over an arbitrary object and citing it in a second proof, and direct core proof construction from `NAT_TYPE` resources.
- Adds `pytest_tests/test_readme_python_api.py`, which executes all three marked README Python examples in CI.
- Adds informational fixture `source/testProofs/theoremPromotion.txt` with four proof blocks: reuse an identity theorem for another object, then prove equality symmetry with a discharged subproof and cite that theorem for different objects.
- Adds `pytest_tests/test_theorem_surface_citations.py::test_premise_carrying_theorem_can_be_cited_from_proof_text`, a specific expected-failure probe for the TODO that a titled theorem with premises cannot yet be cited as `Title from L`. It checks the source theorem validates and xfails only on the current unknown-title parse error. Claude was notified in [PR #42 comment](https://github.com/axiomtutor/SyLoPy/pull/42#issuecomment-6137953966); likely fix is in `ProofJustification._cited_rule`: for explicit refs, preserve built-in aliases but route an unknown theorem title to `NamedRulePlaceholder(title)`, leaving arity and premise checks to the kernel. ChatGPT did not edit `ProofJustification.py`.
- Marks the public-API/theory-boundary documentation and small end-to-end-example TODOs complete; general growth of informational examples and surface support for premise-carrying theorems remain open.
- Records PR #41's rule-registration soundness findings: parameter-mismatched induction, an unregistered theorem instance, and an unregistered subclass of a default rule are all accepted by class-based authorization; constructor deduplication also drops one of two distinct required induction configurations. The promotion deduplication analogue is already covered in master tests.
- CI [run #38344485519](https://github.com/axiomtutor/SyLoPy/actions/runs/38344485519) on this head: 1,071 passed, 4 xfailed, one known deferred ZFC failure; coverage passed; enforced 79/79; informational 55/56. The source informational proof corpus passes 43/43, including the four added theorem-promotion/subproof examples. The new surface-citation regression is the fourth xfail. The only ordinary test and informational fixture failure remains the known deferred WLOG/Mutatis mutandis ZFC case.

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
