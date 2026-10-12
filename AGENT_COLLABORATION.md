# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. The owner recently reset the local `chatgpt-agent-guidance` branch to `origin/chatgpt-agent-guidance`; this remote branch is the source of truth for the handoff.

## Current baseline

- **Master:** [`5cf4073`](https://github.com/axiomtutor/SyLoPy/commit/5cf40731f9204105a51052429344b6a36293272d).
- **Known baseline failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, caused by deferred WLOG / Mutatis mutandis support. Recent CI runs still show this one unrelated failure. Do not hide it with an xfail or implement the deferred rules without approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel changes in `source/ProofLogic.py` and `source/ProofJustification.py`. ChatGPT/Copilot may add focused tests against those behaviors, but must not edit those two files. Keep each agent's work isolated by branch/PR.

## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope and do not affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: “Let n be a natural number” asserts the ordinary citable `Nat(n)` fact; “Let X be an integer” asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) must enforce the declared carrier.
- “Let Y be such a set. (Existence from L)” names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Active pull requests

### PR #36 — Scoped relation declarations (test-only)

[PR #36](https://github.com/axiomtutor/SyLoPy/pull/36), branch `chatgpt/relation-scope-regressions`, latest head [`b8788a9`](https://github.com/axiomtutor/SyLoPy/commit/b8788a912f5b8298ad1e795172f835e1d9c949e5). It adds four probes:

1. A locally declared relation works inside its scope but is undeclared after that scope closes.
2. A relation declared in a parent subproof is visible in nested descendants.
3. A sibling's relation properties do not transfer to another sibling.
4. A locally declared transitive relation supports the two-premise transitivity rule.

Latest CI [#38196343710](https://github.com/axiomtutor/SyLoPy/actions/runs/38196343710): **920 passed, 4 xfailed, 1 failed**; the sole failure is the known deferred ZFC fixture. An intermediate CI run caught a missing test-helper argument; that was corrected in `b8788a9`. The xfails are now conditional on the exact in-scope line, rule mismatch, and rule name, so unrelated failures cannot be mistaken for the pending bug.

**Claude's next task: implement the kernel-side scope-aware relation-property lookup.** Source trace: `ProofParser.elaborate_proof` builds the relation-rule instances after elaboration from `context.context.declarations_here()`. Nested elaboration uses a child `ProofContext` and restores the parent, so locally declared relations are absent from that root snapshot. The kernel already threads the active `DeclarationScope` through validation. Use the declaration visible at the current rule application (metadata `carrier` and `properties`) rather than flattening every relation declaration into a global name map. A flat map could leak properties across siblings. Preserve PR #34's root-declaration carrier/property guards. No further owner design decision is needed.

Once the fix lands, rerun these four probes as ordinary passing regressions; do not retain xfails for behavior that now works. Add further tests for a relation declared inside a Fresh Variable subproof, nested-child non-escape, and theorem promotion after use of a local relation when appropriate.

### PR #37 — Theory-local typed declarations

[PR #37](https://github.com/axiomtutor/SyLoPy/pull/37), branch `chatgpt/theory-local-typed-declarations`, head [`38713de`](https://github.com/axiomtutor/SyLoPy/commit/38713de0037da9730601fa2231794a5c2a58b2c6). It registers Int/Nat declaration recipes in `NUMBER_THEORY_ENVIRONMENT`, makes base-language line elaborators available when a caller supplies an explicit theory environment, adds a direct-environment test, and restores the typing soundness invariant in `todos.txt`. Latest CI [#38192715595](https://github.com/axiomtutor/SyLoPy/actions/runs/38192715595) reports 921 passed and only the known ZFC fixture failure. Ready for owner review; do not auto-merge.

### PR #38 — Theorem-promotion audit (test-only)

[PR #38](https://github.com/axiomtutor/SyLoPy/pull/38), branch `chatgpt/theorem-promotion-audit`, head [`a80f68e`](https://github.com/axiomtutor/SyLoPy/commit/a80f68eb8d569b0a9ced90fcd24205d899faea31). The test-only audit covers retention of top-level premises, excluding nested assumptions/Fresh Variable flags from generalization, premise substitution and matching, and rejection of root assumptions. CI [#38195892220](https://github.com/axiomtutor/SyLoPy/actions/runs/38195892220) reports 926 passed, 1 xfailed, and the known ZFC fixture failure.

One policy question is deliberately recorded as a strict xfail: in a proof containing `Let Y be such a set. (Existence from 2)`, `Y` appears in the default generalized-name list when the checked proof is promoted to a theorem. The audit's intended expectation is that a witness constrained by an existential premise is not an arbitrary parameter. **Claude should assess this against the intended promotion semantics after prioritizing the relation-scope fix.** Treat it as a promotion-policy concern requiring verification, not as a demonstrated soundness hole.

## Other status and coordination rules

- PRs #28–31, #34, and #35 are merged. PR #33 is closed/unmerged and is reference material only.
- The over-rejection caused by relation-property words colliding with object names was fixed by Claude in [commit `5df7d5d`](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f); keep its tests for property-label collisions and real carrier references.
- Branch cleanup has **not** been performed. Older branch inventories in previous handoffs are snapshots, not current truth; refresh and compare refs with master before deleting anything. Preserve this live handoff branch and all active PR heads. The available connected GitHub operations do not expose branch deletion.
- Use `./run_tests.sh` as the canonical validation command. Report Python tests, coverage, enforced fixtures, and informational fixtures separately, and name the known ZFC failure explicitly.
- Keep `AGENT_COLLABORATION.md` for current assignments/decisions/evidence; `todos.txt` for backlog/deferred status; design documents for full semantics; PRs for detailed implementation discussion. Do not add every suspicion as a new task. Distinguish reproduced behavior from source-level hypotheses.
- Owner review is still needed for PRs #36, #37, and #38. Claude should first complete the agreed scope-aware kernel work; then evaluate the theorem-promotion witness finding. No additional design decisions are needed for the relation-scope fix.
