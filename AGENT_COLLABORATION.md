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

[PR #41](https://github.com/axiomtutor/SyLoPy/pull/41), branch `chatgpt/parameterized-rule-registration-audit`, head [`bfa4c5f`](https://github.com/axiomtutor/SyLoPy/commit/bfa4c5f28c2fbdc87fc178b50375dff419f035e6). Test-only; no kernel implementation changes.

- Probe 1: a direct `InductionRule("Nat", Zero, Succ)` citation is accepted although only `InductionRule("Int", ZeroInt, SuccInt)` is configured.
- Probe 2: a valid promoted theorem `P -> P` in the allowlist authorizes a different `TheoremRule` instance concluding arbitrary `Q`.
- Probe 3: an unregistered subclass of `ReiterationRule` overrides `applies` to assert arbitrary `Q` without premises and passes the direct-citation class check.
- Probe 4: a theorem that depends on the forged Reiteration subclass is accepted when the caller registers only the parent default rule and the theorem itself; this independently targets `RuleContext.allows_rule`.
- Probe 5: `Proof.__init__` discards one of two required Nat/Int `InductionRule` configs on elaboration metadata because it deduplicates by type/name. The parallel promotion dedup problem in `_promotion_requirements` is already in master's test `test_promotion_preserves_each_parameterized_rule_requirement`.
- Probe 6: the direct Pairing elaborator embeds `PairingAxiomRule(witness_name="Y")` in a line but exports only generic `PairingAxiomRule()` in `ElaboratedEntries.required_rules`; class matching masks this missing registration. The test requires that a future strict registration design explicitly authorize the generated configuration.
- Positive control: a distinct Nat induction object with identical `type_predicate`, `zero_term`, and `succ_symbol` parameters remains acceptable.
- CI [run #38345020383](https://github.com/axiomtutor/SyLoPy/actions/runs/38345020383): 1,069 passed, 9 xfailed, plus the known deferred ZFC fixture failure; coverage passed; enforced fixtures 79/79; informational fixtures 51/52. The added probes reproduce expected failures; the only ordinary failure is the deferred ZFC fixture.
- Implementation needs one consistent authorization/key helper used by `ProofValidator._rule_is_registered` and `RuleContext.allows_rule`, plus consistent semantic deduplication in `Proof.__init__` and `_promotion_requirements`. Design notes and Pairing fix suggestion are in [PR #41 comments](https://github.com/axiomtutor/SyLoPy/pull/41#issuecomment-6137881949) and [the later checklist](https://github.com/axiomtutor/SyLoPy/pull/41#issuecomment-6137918415).

### PR #42 — Refresh status, document and test Python API, record rule-registration gap

[PR #42](https://github.com/axiomtutor/SyLoPy/pull/42), branch `chatgpt/refresh-status-after-promotion-audit`, head [`ea3049b`](https://github.com/axiomtutor/SyLoPy/commit/ea3049bd7be72b11b35d7f8f5502a1aa237994d9). Documentation, fixtures and tests only; no kernel changes.

- Adds a “Recommended Python API” README section with standalone examples of surface proof checking, theorem promotion and theorem reuse, and core proof construction from `NAT_TYPE` resources.
- `pytest_tests/test_readme_python_api.py` executes all three marked README code examples in CI; they pass.
- `source/testProofs/theoremPromotion.txt` adds four passing proof blocks: identity theorem reuse across arbitrary objects, then equality symmetry via a discharged subproof and subsequent theorem reuse. README links to the fixture.
- `pytest_tests/test_theorem_surface_citations.py` adds a specific expected-failure test for a premise-carrying title cited as `Title from L`. Source theorem validates; parser fails on unknown title. Claude was notified in [PR #42 comment](https://github.com/axiomtutor/SyLoPy/pull/42#issuecomment-6137953966). Candidate fix: `ProofJustification._cited_rule` should preserve known built-in aliases but return `NamedRulePlaceholder(title)` for an otherwise-unknown title with explicit refs, leaving premise arity checking to the kernel.
- `todos.txt` now documents the full rule-registration issue: both allowlist checks and both deduplication sites, subclass substitution, and Pairing witness registration.
- CI [run #38344979754](https://github.com/axiomtutor/SyLoPy/actions/runs/38344979754) for this branch: 1,071 passed, 4 xfailed, one known deferred ZFC failure; coverage passed; enforced fixtures 79/79; informational fixtures 55/56; `source/testProofs` passes 43/43. Only the known ZFC fixture/informational proof fails.

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
