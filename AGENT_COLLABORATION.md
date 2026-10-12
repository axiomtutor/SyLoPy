# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. The owner recently reset the local `chatgpt-agent-guidance` branch to `origin/chatgpt-agent-guidance`; this remote branch is the source of truth for the handoff.

## Current baseline

- **Master:** [`e00f3cc`](https://github.com/axiomtutor/SyLoPy/commit/e00f3ccc888f4053cc3760493926bd24888b2d2f), committed 2026-10-12.
- **Master CI:** [run #38206384301](https://github.com/axiomtutor/SyLoPy/actions/runs/38206384301): 979 passed, 1 known failure, coverage passed; enforced fixtures 79/79 and informational fixtures 51/52.
- **Known baseline failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, caused by deferred WLOG / Mutatis mutandis support. Do not hide it with an xfail or implement the deferred rules without approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel changes in `source/ProofLogic.py` and `source/ProofJustification.py`. ChatGPT/Copilot may add focused tests against those behaviors, but must not edit those two files. Keep each agent's work isolated by branch/PR.

## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope and do not affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: “Let n be a natural number” asserts the ordinary citable `Nat(n)` fact; “Let X be an integer” asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) must enforce the declared carrier.
- “Let Y be such a set. (Existence from L)” names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Active pull requests

### PR #36 — Scoped relation declarations (test-only; superseded)

[PR #36](https://github.com/axiomtutor/SyLoPy/pull/36), branch `chatgpt/relation-scope-regressions`, head [`b8788a9`](https://github.com/axiomtutor/SyLoPy/commit/b8788a912f5b8298ad1e795172f835e1d9c949e5). This branch added four narrow probes for relation declarations in subproofs.

Claude's relation-scope implementation has since landed directly on `master` in [`e00f3cc`](https://github.com/axiomtutor/SyLoPy/commit/e00f3ccc888f4053cc3760493926bd24888b2d2f). It adds `pytest_tests/test_relation_scope_rules.py` and `pytest_tests/test_rule_context_declarations.py`, covering the seven relation rules, metadata/carrier checks, nested inheritance, sibling and closed-scope non-leakage, shadowing, proof-by-cases, Fresh Variable subproofs, and all three rule-citation paths. Master CI [#38206384301](https://github.com/axiomtutor/SyLoPy/actions/runs/38206384301) reports 979 passed plus the known deferred ZFC failure and coverage pass.

The four pending probes in PR #36 are superseded by master coverage. ChatGPT commented that the owner should close this stale test-only PR rather than merge it against its pre-fix base. It remains open pending owner action; do not merge it.

### PR #37 — Theory-local typed declarations

[PR #37](https://github.com/axiomtutor/SyLoPy/pull/37), branch `chatgpt/theory-local-typed-declarations`, head [`9d7d8c0`](https://github.com/axiomtutor/SyLoPy/commit/9d7d8c0c19d1279fc6aba50f9352a8c13ca59268), base `e00f3cc`. It registers Int/Nat declaration recipes in `NUMBER_THEORY_ENVIRONMENT`, makes base-language line elaborators available when an explicit theory environment is passed, adds a direct-environment regression, refreshes the README/TODO test snapshot, restores the typing soundness invariant, and marks the landed relation-scope TODO complete.

The branch was refreshed from current master, preserving Claude's `ProofParser.py` relation-scope change rather than clobbering it. Its CI [#38208787315](https://github.com/axiomtutor/SyLoPy/actions/runs/38208787315) reports **980 passed, 1 known failure** (the deferred ZFC fixture), with coverage passing and 79/79 enforced fixtures. It is ready for owner review; do not auto-merge.

### PR #38 — Theorem-promotion soundness audit (test-only)

[PR #38](https://github.com/axiomtutor/SyLoPy/pull/38), branch `chatgpt/theorem-promotion-audit`, head [`930ed3c`](https://github.com/axiomtutor/SyLoPy/commit/930ed3c4dfdfa664210bc9f7954780abbfb894ed), base `e00f3cc`. Only `pytest_tests/test_theorem_promotion_audit.py` is changed; Claude's reserved kernel files are untouched. The branch is still draft.

Latest CI [#38209668349](https://github.com/axiomtutor/SyLoPy/actions/runs/38209668349): **985 passed, 8 xfailed, 1 failed**; coverage passed. The only failing test is the known deferred ZFC fixture. Seven of the eight xfails are conditional reproductions of unsafe theorem-promotion behavior; the other is the unresolved Existence-witness generalization policy probe.

Six concrete soundness/dependency-loss categories are covered:

1. An explicit `conclusion=` can name a formula the checked proof never derived.
2. The public `generalized_names` override can include fixed vocabulary such as `EmptySet`, generalizing a fact beyond the proof's eligible object declarations.
3. A direct Pairing witness is represented as a `rule` entry with declarations in justification slot 4. Promotion drops the witness's defining membership formula and overlooks its declaration.
4. A top-level `Axiom` line is recorded by validation as a global hypothesis but omitted from promoted premises.
5. A plain `Premise` or `Axiom` used only inside a consumed subproof is a global dependency, not the subproof's discharged assumption; the top-level-only collector misses it. Both variants are tested.
6. A relation-property inference depends on proof-local declaration metadata (e.g. `R` is reflexive), which is not represented in the promoted theorem's formula premises. The same predicate name can be redeclared with weaker properties in a later proof, and the promoted theorem still applies.

Tests check the source proof first and xfail only if each attack actually succeeds; safe refusal of promotion is accepted where supported, and unrelated parse/setup errors remain failures. The Existence-from-line witness test remains a policy concern rather than a demonstrated soundness hole: its defining formula is retained as a premise in that case.

The suggested kernel-side approach, already described in PR comments: (a) require an explicit conclusion to match a top-level derived formula, (b) preserve global premise and axiom dependencies, including nested ordinary premise/axiom lines while keeping discharged assumptions and local existential witnesses scoped, (c) handle direct rule-created witnesses, (d) constrain `generalized_names` to eligible declared objects, and (e) encode declaration-metadata requirements or conservatively refuse promotions that depend on non-exportable metadata. **Claude owns these kernel changes.** No reply from Claude to the latest PR comments had appeared at the last review check; continue coordinating in PR #38 and do not edit kernel files independently.

## Other status and coordination rules

- PRs #28–31, #34, and #35 are merged. PR #33 is closed/unmerged and is reference material only.
- The over-rejection caused by relation-property words colliding with object names was fixed by Claude in [commit `5df7d5d`](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f); keep its tests for property-label collisions and real carrier references.
- Branch cleanup has **not** been performed. Older branch inventories in previous handoffs are snapshots, not current truth; refresh and compare refs with master before deleting anything. Preserve this live handoff branch and all active PR heads. The available connected GitHub operations do not expose branch deletion.
- Use `./run_tests.sh` as the canonical validation command. Report Python tests, coverage, enforced fixtures, and informational fixtures separately, and name the known ZFC failure explicitly.
- Keep `AGENT_COLLABORATION.md` for current assignments/decisions/evidence; `todos.txt` for backlog/deferred status; design documents for full semantics; PRs for detailed implementation discussion. Do not add every suspicion as a new task. Distinguish reproduced behavior from source-level hypotheses.
- Owner review is still needed for PRs #36, #37, and #38. PR #36 is superseded and should not be merged; PR #37 is ready for owner review; PR #38 remains draft because it exposes unresolved soundness boundaries. Do not merge or close PRs without owner approval.

