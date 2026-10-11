# SyLoPy Agent Collaboration — Current Handoff

This branch is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is intentionally separate from master/AGENT_COLLABORATION.md, which contains stable agent guidance. The owner has final authority over design and task priorities.

This file is a **current summary, not a chronological diary**. Keep durable decisions, verified findings, active questions, owners, and links here. Put implementation detail and discussion in the relevant PR or design document; when a question is resolved, replace the open question with the decision rather than appending another transcript.

## 1. Working rules

- Before work, inspect current master, README.md, todos.txt, ARCHITECTURE_STATUS.md, relevant branches, and open PRs. Old summaries can be stale.
- Coordinate around active files and tasks. Prefer one bounded task per branch/PR. Do not rewrite or rebase another agent's branch.
- Distinguish **settled decisions**, **design proposals**, **unverified source-level suspicions**, and **observed test results**.
- The canonical test command is ./run_tests.sh. Report Python tests, coverage, enforced fixtures, and informational fixtures separately. Identify known pre-existing failures explicitly.
- For a negative proof test, ensure the proof reaches the intended rule and is rejected for the condition the test claims; parser errors or unrelated scope failures are not evidence that the rule guard works.
- ChatGPT and Copilot may add test-only probes for source/ProofLogic.py and source/ProofJustification.py, but must not patch those files. Send kernel findings, with a minimal reproducer and precise failing condition, to Claude/owner.
- Do not implement features that todos.txt explicitly defers pending owner approval.

## 2. Architecture and settled semantics

The intended pipeline is:

    surface proof text -> parsing / surface AST -> elaboration
                      -> core proof entries -> ProofLogic validation

- **Elaboration scope:** ProofContext is the lexical environment for source declarations, labels, assumptions, and arbitrary/fresh bindings.
- **Kernel scope:** ProofLogic.py independently validates elaborated entries using LabelScope and DeclarationScope. This is a deliberate trust boundary, not accidental duplication. Preserve the separation and test overlapping scope behavior.
- **Parser oracle:** parse_oracle/ specifies intended surface-to-core readings independently of parser implementation. Resolve oracle/parser disagreements; do not automatically weaken oracle cases.
- **Theory extensions:** prefer theory-local parsing, declaration recipes, and elaboration sugar that reduces to existing logic. Add kernel/AST primitives only for genuinely new logical constructs.
- **Relation properties:** the intended semantics treats relation atoms as carrier-restricted. Symmetry, antisymmetry, asymmetry, and transitivity need no separate membership citations when their premises already contain relation atoms. Rules deriving relation atoms from membership, including reflexivity, irreflexivity, and totality, must check the declared carrier.
- **Uniqueness:** the rule concludes ordinary logic, exists W, (B(W) and forall V, (B(V) -> V = W)). A candidate must be an appropriate arbitrary constant and must not be constrained by the existence line, hypotheses, witness declarations, rule-introduced declarations, or relevant declaration metadata. See the red-team fixture and the reason-checking test below.
- **Witness naming:** “Let Y be such a set. (Existence from L)” is elaboration sugar over an ordinary existential citation and a scoped declaration. The axiom citation does not itself name a witness. The older direct Pairing-witness form remains on master for compatibility but is not the design to extend to other axioms.
- **Deferred set theory:** no implementation of WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, or Infinity without explicit owner approval. The recorded WLOG model is a proof-region replay followed by ordinary revalidation, with citation remapping; it must not become an unchecked symmetry assertion.
- **Types:** types remain predicate-based and may overlap (Nat and Int); do not silently introduce disjoint many-sorted logic. Type checking is distinct from ordinary proof inference.

## 3. Current repository and regression status

**Last confirmed master snapshot:** commit [62374be](https://github.com/axiomtutor/SyLoPy/commit/62374beb42378dc2e3ec89a0087c1b545594fb7c), checked by [CI run #38096042218](https://github.com/axiomtutor/SyLoPy/actions/runs/38096042218).

- Python tests: **896 total, 895 passed, 1 failed**.
- Coverage: passed.
- Enforced proof fixtures: **78/78 passed**.
- Informational fixtures: **51/52 passed**.
- The sole known failure is pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass, which reaches the deliberately deferred WLOG / Mutatis mutandis work. Do not mask it with an xfail absent owner approval. Treat any new failure separately.

The test count and fixture counts are snapshots, not invariants. Record the exact CI run for later changes.

### Merged audit and proof work

- [PR #18](https://github.com/axiomtutor/SyLoPy/pull/18): Uniqueness red-team cases, expanded to 19 cases with explicit refusal-reason checks.
- [PR #19](https://github.com/axiomtutor/SyLoPy/pull/19): scope/freshness audit.
- [PR #20](https://github.com/axiomtutor/SyLoPy/pull/20): number-theory quotient/divisibility and natural-number induction audit.
- [PR #21](https://github.com/axiomtutor/SyLoPy/pull/21): five textbook-style proof fixtures across Nat, set theory, number theory, and discrete math.
- [PR #22](https://github.com/axiomtutor/SyLoPy/pull/22): design-only refinement type-system proposal; no implementation authorization.
- [PR #23](https://github.com/axiomtutor/SyLoPy/pull/23) and [PR #24](https://github.com/axiomtutor/SyLoPy/pull/24): relation-rule coverage and property-gating tests.
- [PR #25](https://github.com/axiomtutor/SyLoPy/pull/25): design clarification separating symbol references in declaration metadata from descriptive labels.

Claude's Uniqueness review found and fixed real problems in witness-line hypothesis tracking and declaration metadata. Cases #5 and #14 were accepted by design under the currently shipped semantics: a typed descriptor like integer is inert until type descriptors are implemented, and a general Pairing schema instance is a theorem, not a witness assumption. Cases #16–19 exercise the actual witness/metadata constraints. See [Claude's fix commit](https://github.com/axiomtutor/SyLoPy/commit/6094678d6b8ec0eb6bb1bf51c6827600a8e68ee9) and pytest_tests/test_uniqueness_red_team_reasons.py.

### Open documentation PRs

- [PR #26 — Refresh regression status in project docs](https://github.com/axiomtutor/SyLoPy/pull/26) is open, documentation-only, and mergeable. It updates the stale test counts in README.md and todos.txt, links the CI snapshot, and fixes README numbering. Its CI run [#38096950873](https://github.com/axiomtutor/SyLoPy/actions/runs/38096950873) reports the same 895 passed / 1 known failure, coverage pass, enforced 78/78 and informational 51/52. No source files changed. This is a snapshot update, so refresh it again if its values are stale when merged.
- [PR #27 — Separate stable agent guidance from collaboration history](https://github.com/axiomtutor/SyLoPy/pull/27) is open and documentation-only. It trims the master copy of AGENT_COLLABORATION.md from a 454-line guidance/transcript mixture to 90 lines of stable policy and points readers to this live handoff. CI run [#38097847941](https://github.com/axiomtutor/SyLoPy/actions/runs/38097847941) completed with 895 passed, 1 known failure, coverage passed, enforced 78/78, informational 51/52. The failure is the established WLOG / Mutatis mutandis fixture and is unchanged by this documentation-only PR.

## 4. Active work and design recommendations

### A. Theorem-promotion audit — Copilot

Copilot was asked to work independently in pytest_tests/test_theorem_promotion_audit.py, without touching kernel code or existing promotion tests. The audit should determine:

1. What formulas/premises become part of a promoted TheoremRule, and whether any required premise is dropped.
2. Whether only eligible top-level object declarations are generalized; nested declarations, Fresh Variable flags, and Existence from L witnesses should not accidentally become arbitrary generalized constants.
3. Whether local validation can succeed while an undischarged assumption or non-surviving declaration leaks across the promotion boundary.
4. Whether promoted rules work on fresh instances and reject wrong shapes or missing premises.

Each negative case must reach the promotion/citation boundary for the intended reason. **No audit report is recorded in this handoff yet.** Check with Copilot before duplicating this task.

### B. Relation-rule scope — unverified candidate

Source inspection suggests a possible mismatch: relation rules appear to be constructed once from context.context.declarations_here() after subproof elaboration has restored the root context. A relation declaration introduced only inside a child ProofContext may therefore fail to register its specialized rule even when used in that subproof.

This is **not yet an observed bug**. First decide whether relation declarations are intended to be legal inside subproofs. If yes, write a minimal proof where a reflexive relation is declared and used inside one subproof; assert that the test reaches the relation-rule line. Do not add a test that assumes the answer before checking the language contract.

### C. Descriptive metadata collision — unverified candidate

ProofLogic._metadata_names appears to recursively treat all strings in declaration metadata as symbol names. Relation metadata also contains descriptive values such as "reflexive" and "transitive", not just symbol references such as the carrier name. Because the parser's identifier syntax appears to admit these words as object names, a same-named object may be conservatively excluded from Uniqueness generalization.

This is a suspected **over-rejection**, not an observed failure, and not an unsound acceptance. The design in PR #25 points toward typed metadata that distinguishes symbol references from descriptive labels. Reproduce the behavior on current master before requesting a kernel change; retain the test only if it demonstrates the intended boundary.

### D. Refinement types — design-only

The owner's latest direction is that “Let X be an integer” should eventually establish the ordinary predicate Int(X), but implementation is explicitly deferred pending approval. PR #22 lays out a separate type-checking judgment and source-mapped typing obligations.

Important hazards to test/design before implementation:

- A type fact introduced within a subproof must have an intentional scope lifetime; premise-tagged lines may be recorded in a global hypothesis list, so do not assume the ordinary premise mechanism is sufficient for local type facts.
- Surface divisibility a|b requires type obligations for **both operands**. Its current expansion exists m, (Int(m) and b = Times(a,m)) loses the source-level fact that b was an operand; checking only the Times signature is insufficient.
- Type.as_declaration_recipe() appears to distinguish typed-function targets but not tuple targets. If the grammar accepts “(a, b) be an integer”, the generic recipe may interpret the tuple members as separate integer declarations. Test tuple targets and preserve intended grouped-name behavior before enabling descriptors broadly.
- A local type assumption is not by itself typed universal quantification. A construct such as “forall integer n, P(n)” needs its own explicit semantics if desired.
- Source tracing corrected an earlier suspicion about “such that”: compound declarations appear to dispatch through declaration recipes in the normal surface syntax path. This was a code-path inspection, not an end-to-end test.

Do not begin implementation until the owner chooses a scope and explicitly authorizes it. A sensible initial slice would be tests and a formula-producing declaration recipe, but it must address scope first; full signature checking and divisibility obligations are distinct work.

## 5. Recommended order of work

1. Get Copilot's theorem-promotion audit report and resolve any soundness or specification issues it exposes.
2. Ask the owner to confirm the contract for relation declarations inside subproofs; if allowed, verify the candidate with a focused test.
3. Reproduce or dismiss the metadata-label collision with an end-to-end test; avoid kernel changes until the behavior is demonstrated and the metadata contract is settled.
4. Get an explicit owner decision on the initial type-system implementation scope. Before implementing it, test local type-fact scope and tuple-target handling.
5. Keep parser-oracle expansion and public language-reference documentation as useful follow-on work, but do not let documentation displace a demonstrated soundness issue.
6. Leave WLOG, Mutatis mutandis, named ZFC axiom citations, and other explicitly deferred set-theory work untouched until the owner authorizes implementation.

## 6. Requests for the next handoff

**Owner:** please confirm whether relation declarations are intended to work in subproofs, and whether the next type-system milestone should be (a) formula-producing typed declaration recipes only, or (b) that plus a tightly bounded first signature-checking slice. Neither is authorized yet.

**Copilot:** please post the theorem-promotion audit status, exact findings, and CI results. If it is not underway, confirm that before anyone duplicates it.

**Claude:** please flag any active work in relation-rule registration, metadata reference handling, or typing that overlaps the candidate tests above. For any source-level suspicion, state whether the behavior is intentional and point to the controlling contract.

**All agents:** name one concrete task that would materially reduce soundness risk or future maintenance cost, with the files you would touch and how you would test it. If no higher-priority work is active, ChatGPT's next independent task can be the relation-scope/metadata test investigation after the owner confirms the intended relation-scope semantics.
