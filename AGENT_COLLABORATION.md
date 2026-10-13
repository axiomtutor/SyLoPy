# SyLoPy Agent Collaboration — Current Handoff

This is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is a current summary, not a transcript. The owner has final authority over design and priorities. The owner recently reset the local `chatgpt-agent-guidance` branch to `origin/chatgpt-agent-guidance`; this remote branch is the source of truth for the handoff.

## Current baseline

- **Master:** [`866c5e9`](https://github.com/axiomtutor/SyLoPy/commit/866c5e9c3528677b95407461d2ccadcbdb00b6e6): Claude's theorem-promotion requirements change on top of the owner-merged PR #39 ([`63ca81d`](https://github.com/axiomtutor/SyLoPy/commit/63ca81d)).
- **Validation:** local `./run_tests.sh` at `866c5e9`: 1054 passed, 1 known Python failure; coverage passed; enforced fixtures **79/79**; informational fixtures 51/52. The known failure keeps every master CI run red, so compare the counts, not the colour. CI for `866c5e9`: [run #38340370578](https://github.com/axiomtutor/SyLoPy/actions/runs/38340370578).
- **Known Python failure:** `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, caused by deferred WLOG / Mutatis mutandis support. Do not hide it with an xfail or implement the deferred rules without approval.
- **Architecture:** proof text → surface parsing → elaboration → core entries → `ProofLogic.Proof`. `ProofContext` governs elaboration scope; the kernel independently enforces scope with `LabelScope` and `DeclarationScope`.
- **File ownership:** Claude owns kernel changes in `source/ProofLogic.py` and `source/ProofJustification.py`. ChatGPT/Copilot may add focused tests against those behaviors, but must not edit those two files. Keep each agent's work isolated by branch/PR.

## Owner-approved semantics and boundaries

- Declarations inside a subproof are visible there and in descendants, but do not escape to the enclosing scope and do not affect siblings. Root declarations remain visible in every nested scope.
- Typed declaration option A is approved: “Let n be a natural number” asserts the ordinary citable `Nat(n)` fact; “Let X be an integer” asserts `Int(X)`. This is not a refinement-type checker or typed-quantifier feature.
- Relation atoms are carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity act on relation premises; rules deriving relation atoms from membership (reflexivity, irreflexivity, totality) must enforce the declared carrier.
- “Let Y be such a set. (Existence from L)” names a scoped existential witness. The axiom/premise does not itself introduce a named witness.
- Still deferred absent owner approval: WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, full refinement checking, and relativized/typed quantifier sugar.

## Landed kernel contracts (Claude; details in `todos.txt` item 8)

- **Hypotheses reach every rule that treats a constant as arbitrary** (`e56c67d`). `Uniqueness`, `UniversalGeneralization` and `ExistentialElimination` refuse a constant that occurs in any hypothesis in force at any depth (a premise, a cited axiom, a formula-stating declaration, a witness line, an enclosing assumption) or that a declaration's structure names, such as a relation's carrier. Tests: `pytest_tests/test_hypotheses_and_promotion.py`.
- **Promotion carries what the proof assumed** (`e56c67d`). A promoted theorem's premises are every hypothesis the proof took for granted, at any depth. Promotion refuses a proof that relied on declaration structure no formula states (a relation declared symmetric); the multi-proof runner prints “was not promoted”.
- **A theorem is a theorem of the theory it was proved in** (`866c5e9`). The theory's axioms a proof cited and the rules it used beyond `default_rules()` are recorded as `required_axioms` / `required_rules` (plus what the theorems it cited required) and the theorem is citable only in a proof that lists those axioms and allows those rules. An explicit `conclusion=` must be a formula the proof derived at the top level, `generalized_names=` may name only objects it declared at its top level, and a required axiom may not mention a generalized constant. Inside a multi-proof file nothing changes for proofs written in the file's theories. Tests: `pytest_tests/test_promotion_requirements.py`.
- Mutation checks for both changes (20 and 29 mutants) are all caught by the tests.
- **Deferred, owner decision needed:** theorems *about declared relations* (needs generalizing over predicate symbols plus a requirement on the instance's declaration); citing a premise-carrying theorem from proof text; whether a witness named by an `Existence from L` line is generalized by default (today it is, and the theorem stays sound because its defining formula is a premise).

## Active pull request

### PR #38 — Theorem-promotion soundness audit (test-only, draft)

[PR #38](https://github.com/axiomtutor/SyLoPy/pull/38), branch `chatgpt/theorem-promotion-audit`, head [`4aeb4dd`](https://github.com/axiomtutor/SyLoPy/commit/4aeb4dd6efe638baf92c38975a79839e742ff02f), base `e00f3cc`; only `pytest_tests/test_theorem_promotion_audit.py` changes. Its probes found real holes, and Claude ran them against `866c5e9`: **12 pass, 1 xfails, 2 fail.**

| Probe | Result on `866c5e9` |
| --- | --- |
| Explicit `conclusion=` never derived | fixed: `ValueError` |
| `generalized_names` naming `EmptySet` | fixed: `ValueError` |
| Direct Pairing witness exported as a free constant | refused at the citing line, as `arity_mismatch` (the witness's defining formula is now a premise) — **fails only on its `rule_mismatch` assertion** |
| Top-level `Axiom`; nested `Axiom` | fixed: recorded as `required_axioms`; a citing proof without that axiom is refused |
| Nested `Premise` | fixed: carried as a premise; refused as `arity_mismatch` — **fails only on its `rule_mismatch` assertion** |
| Relation-property declaration dependency | fixed: promotion refused |
| Custom inference rule | fixed: recorded as `required_rules`; a citing proof without that rule is refused |
| Existence-witness generalization | still xfail: a policy question for the owner, not a soundness hole (see above) |

**Requests to ChatGPT for PR #38** (it is your branch; Claude will not touch it): (1) merge current master into it; (2) make the two probes above accept the refusal they actually get: assert that the citing line is refused (label `2` / `3`), and accept `CATEGORY_RULE_MISMATCH` or `CATEGORY_ARITY_MISMATCH`; (3) keep the Existence-witness xfail until the owner decides, or turn it into an assertion of today's behaviour with a comment pointing at `todos.txt` item 8; (4) then mark the PR ready for review. The owner decides whether to merge.

## Requests

- **ChatGPT / PR #38:** red-teaming remains test-only; Claude's kernel files stay untouched. Fixed two audit probes to accept either rule-mismatch or arity-mismatch as safe refusal, and added a parameterized `InductionRule` probe. It reproduces a requirement bypass: a theorem proved with `InductionRule("Nat", Zero, "Succ")` is accepted where only `InductionRule("Int", ZeroInt, "SuccInt")` is registered. The cause is class-only rule availability checking plus requirement deduplication by type/name; details and reproduction are in [the PR comment](https://github.com/axiomtutor/SyLoPy/pull/38#issuecomment-6137440847). Merged current master `866c5e9` into the audit branch with merge commit [`559f5bd`](https://github.com/axiomtutor/SyLoPy/commit/559f5bdeea5aaeeffbaa0ce487238426ffdfa5bf); comparison now shows 0 commits behind master and only `pytest_tests/test_theorem_promotion_audit.py` changed. The refreshed PR CI is [run #38341419745](https://github.com/axiomtutor/SyLoPy/actions/runs/38341419745): 1,068 passed, 2 xfailed, one known deferred ZFC fixture failure; coverage passed; enforced fixtures 79/79; informational 51/52. The new parameterized-induction xfail reproduces the bypass. Claude-facing findings and current CI results are in [the latest PR comment](https://github.com/axiomtutor/SyLoPy/pull/38#issuecomment-6137485029).
- **ChatGPT / PR #40:** opened [README/TODO test-snapshot refresh](https://github.com/axiomtutor/SyLoPy/pull/40) to record master CI run `#38340370578` at `866c5e9` (1,054 passed, one known failure; coverage passed; enforced 79/79; informational 51/52). Its CI [run #38341272987](https://github.com/axiomtutor/SyLoPy/actions/runs/38341272987) has only the known deferred ZFC fixture failure; coverage and fixture counts are unchanged.
- **Copilot:** unclaimed.
- **Owner:** review PR #38 after its current CI run completes; decide the Existence-witness policy; delete stale branches (see below).
- **Copilot:** unclaimed.
- **Owner:** review PR #38 when it is green; decide the Existence-witness policy; delete stale branches (see below).

## Other status and coordination rules

- PRs #28–31, #34, #35, #37, and #39 are merged. PR #36 was closed unmerged (superseded by the relation-scope coverage on master); PR #33 is closed/unmerged and is reference material only.
- The over-rejection caused by relation-property words colliding with object names was fixed by Claude in [commit `5df7d5d`](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f); keep its tests for property-label collisions and real carrier references.
- Branch cleanup has **not** been performed: agent sessions cannot delete remote branches. Older branch inventories in previous handoffs are snapshots, not current truth; refresh and compare refs with master before deleting anything, and preserve this live handoff branch and PR #38's head.
- Use `./run_tests.sh` as the canonical validation command. Report Python tests, coverage, enforced fixtures, and informational fixtures separately, and name the known ZFC failure explicitly.
- Keep `AGENT_COLLABORATION.md` for current assignments/decisions/evidence; `todos.txt` for backlog/deferred status; design documents for full semantics; PRs for detailed implementation discussion. Do not add every suspicion as a new task. Distinguish reproduced behavior from source-level hypotheses.
- Do not merge or close PRs without owner approval.
