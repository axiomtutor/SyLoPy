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

[PR #41](https://github.com/axiomtutor/SyLoPy/pull/41), branch `chatgpt/parameterized-rule-registration-audit`, head [`571af93`](https://github.com/axiomtutor/SyLoPy/commit/571af93289af7d56784c47f0a9a560995519e0c2). Test-only; no kernel implementation changes.

- Probe 1: a direct `InductionRule("Nat", Zero, Succ)` citation is accepted although only `InductionRule("Int", ZeroInt, SuccInt)` is configured.
- Probe 2: a valid promoted theorem `P -> P` in the allowlist authorizes a different `TheoremRule` instance concluding arbitrary `Q`.
- Probe 3: an unregistered subclass of `ReiterationRule` overrides `applies` to assert arbitrary `Q` without premises and passes direct-citation class authorization.
- Probe 4: a theorem that depends on the forged Reiteration subclass is accepted when the caller registers only the parent default rule and the theorem itself; this exposes class-only `RuleContext.allows_rule`.
- Probes 5–6 cover the separate `rule_below` and `rule_hybrid` validator paths; both accept an unregistered subclass of a parent rule whose overridden `applies` asserts arbitrary Q. This prevents an implementation that tightens only ordinary `rule` citations.
- Probe 7: `Proof.__init__` discards one of two required Nat/Int `InductionRule` configs on elaboration metadata because it deduplicates by type/name. The analogous promotion dedup bug in `_promotion_requirements` is already represented in master test `test_promotion_preserves_each_parameterized_rule_requirement`.
- Probe 8: direct Pairing elaboration embeds `PairingAxiomRule(witness_name="Y")` in a line but exports only generic `PairingAxiomRule()` in `ElaboratedEntries.required_rules`. The test requires the witness-specific config to be exported and both generic and witness-specific configurations to survive the final `Proof.rules` merge.
- Positive control: a distinct Nat induction object with identical `type_predicate`, `zero_term`, and `succ_symbol` parameters remains acceptable.
- CI [run #38345530284](https://github.com/axiomtutor/SyLoPy/actions/runs/38345530284): 1,069 passed, 11 xfailed, plus the known deferred ZFC fixture failure; coverage passed; enforced fixtures 79/79; informational fixtures 51/52. All added probes reproduce expected failures; the only ordinary failure is the known ZFC fixture.
- Implementation needs consistent authorization in `ProofValidator._rule_is_registered` and `RuleContext.allows_rule`, plus semantic deduplication in `Proof.__init__` and `_promotion_requirements`. Pairing path and key design are documented in [PR #41 comments](https://github.com/axiomtutor/SyLoPy/pull/41#issuecomment-6137881949) and [the key-design suggestion](https://github.com/axiomtutor/SyLoPy/pull/41#issuecomment-6137918415).

### PR #42 — Refresh status, document and test Python API, record rule-registration gap

[PR #42](https://github.com/axiomtutor/SyLoPy/pull/42), branch `chatgpt/refresh-status-after-promotion-audit`, head [`824d180`](https://github.com/axiomtutor/SyLoPy/commit/824d1801efd4a712d71020f3ad0b33ba405021bb). Documentation, fixtures and tests only; no kernel changes.

- Adds a “Recommended Python API” README section with standalone examples for surface proof checking, theorem promotion plus reuse, and core proof construction from `NAT_TYPE` resources.
- `pytest_tests/test_readme_python_api.py` executes all three marked README examples in CI; all pass.
- `source/testProofs/theoremPromotion.txt` adds four passing blocks for reusing a theorem about an arbitrary object, and proving/citing equality symmetry via a discharged subproof.
- `source/testProofs/quantifierReasoning.txt` demonstrates instantiating universally quantified premises at an arbitrary object, applying modus ponens, and generalizing. README links to both fixture files.
- `pytest_tests/test_theorem_surface_citations.py` adds an expected-failure regression for the TODO that a premise-carrying theorem cannot be cited as `Title from L`. The first theorem validates; parsing fails on the unknown title. Claude was notified in [PR #42 comment](https://github.com/axiomtutor/SyLoPy/pull/42#issuecomment-6137953966). Suggested fix: `ProofJustification._cited_rule` should preserve known built-in aliases but return `NamedRulePlaceholder(title)` for an otherwise-unknown title with explicit refs, letting the kernel check premise arity. ChatGPT did not edit `ProofJustification.py`.
- `todos.txt` documents the complete rule-registration issue: both class-only authorization sites, both deduplication sites, subclass substitution, the positive semantic-equivalence control, and Pairing witness-specific registration.
- Public-API/theory-boundary docs and the small end-to-end-example item are checked off. Broader informational-example growth remains open.
- CI [run #38345715696](https://github.com/axiomtutor/SyLoPy/actions/runs/38345715696): 1,071 passed, 4 xfailed, one known deferred ZFC failure; coverage passed; enforced fixtures 79/79; informational 56/57; `source/testProofs` 44/44 including both new files. The only ordinary pytest failure and remaining informational miss are the same WLOG/Mutatis mutandis blocker.

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
