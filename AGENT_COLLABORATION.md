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

**Current master snapshot:** commit [5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d04f81b5a8aa7febcb73786a4274000f), checked by [CI run #38112685219](https://github.com/axiomtutor/SyLoPy/actions/runs/38112685219).

- Python tests: **907 total, 906 passed, 1 failed**.
- Coverage: passed.
- Enforced proof fixtures: **79/79 passed**.
- Informational fixtures: **51/52 passed**.
- The sole failure remains pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass, which reaches the deliberately deferred WLOG / Mutatis mutandis work. Do not mask it with an xfail absent owner approval. Treat any new failure separately.

The test count and fixture counts are snapshots, not invariants. Record the exact CI run for later changes.

### Merged audit and proof work

- [PR #18](https://github.com/axiomtutor/SyLoPy/pull/18): Uniqueness red-team cases, expanded to 19 cases with explicit refusal-reason checks.
- [PR #19](https://github.com/axiomtutor/SyLoPy/pull/19): scope/freshness audit.
- [PR #20](https://github.com/axiomtutor/SyLoPy/pull/20): number-theory quotient/divisibility and natural-number induction audit.
- [PR #21](https://github.com/axiomtutor/SyLoPy/pull/21): five textbook-style proof fixtures across Nat, set theory, number theory, and discrete math.
- [PR #22](https://github.com/axiomtutor/SyLoPy/pull/22): design-only refinement type-system proposal; no implementation authorization.
- [PR #23](https://github.com/axiomtutor/SyLoPy/pull/23) and [PR #24](https://github.com/axiomtutor/SyLoPy/pull/24): relation-rule coverage and property-gating tests.
- [PR #25](https://github.com/axiomtutor/SyLoPy/pull/25): design clarification separating symbol references in declaration metadata from descriptive labels.

Claude's Uniqueness review found and fixed real problems in witness-line hypothesis tracking and declaration metadata. Cases #5 and #14 were accepted by design under the currently shipped semantics: a typed descriptor like integer is inert until type descriptors are implemented, and a general Pairing schema instance is a theorem, not a witness assumption. Cases #16–19 exercise the actual witness/metadata constraints. See [Claude's fix commit](https://github.com/axiomtutor/SyLoPy/commit/6094678d6b8ec0eb6bb1bf51c6827600a8e68ee9) and pytest_tests/test_uniqueness_red_team_reasons.py. Claude's later [commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d04f81b5a8aa7febcb73786a4274000f) adds case 20 for the opposite issue: a sound proof that was falsely rejected because a property label was treated as a symbol reference. That over-rejection is now fixed with targeted regression coverage.

### Recently merged documentation PRs

- [PR #26 — Refresh regression status in project docs](https://github.com/axiomtutor/SyLoPy/pull/26) merged at [commit b23d959](https://github.com/axiomtutor/SyLoPy/commit/b23d959e0b5a741a4e782314d6ce0df4c8d29abc). It refreshed the stale test counts and links in README.md and todos.txt, and fixed README numbering.
- [PR #27 — Separate stable agent guidance from collaboration history](https://github.com/axiomtutor/SyLoPy/pull/27) merged at [commit 71e0515](https://github.com/axiomtutor/SyLoPy/commit/71e051514e41fa83ebd438e953bfc800e1821524). It reduced the master copy of AGENT_COLLABORATION.md to stable policy and points readers to this live handoff.

The latest CI snapshot above includes these documentation merges and Claude's Uniqueness fix. Its one test failure is the established WLOG / Mutatis mutandis fixture; the fixture itself remains deferred.

## 4. Coordination hygiene

Use one source of truth for each kind of information:

- `AGENT_COLLABORATION.md` on this live branch: current assignments, active questions, verified findings, and links to work. It is a handoff, not a transcript.
- `todos.txt`: the backlog and explicit status of design decisions (approved, deferred, proposed, or awaiting owner decision).
- The relevant design document: full semantics, algorithms, tradeoffs, and examples.
- PRs and CI runs: implementation discussion, review history, and test evidence.

For every active task, keep the record to: owner, scope, status, files/subsystem, evidence/tests, and next action. When resolved, replace the active entry with the conclusion and a link, or remove it from the active section if the historical detail is not needed. Never keep an old status/count just because it appeared in a previous handoff.

Before starting work, check open PRs and active branches for overlap. After merges, inventory branches and remove only those verified to be fully merged and no longer needed; preserve the live handoff branch and do not delete uncertain branches merely because they look old. Prefer one bounded PR per task and avoid parallel agents editing the same files.

Use explicit evidence labels:
- **Observed/reproduced** — a focused test or trace demonstrates the behavior.
- **Source-level suspicion** — plausible from inspection, not yet reproduced.
- **Design question** — requires a language or architecture decision.
- **Deferred/unauthorized** — do not implement until the owner approves.

Do not expand the active backlog by promoting every suspicion to a task. First decide whether the behavior is in scope, reproduce it, and close it if it is not a bug.

### Branch inventory audit

A previous read-only audit found 24 ChatGPT-named branches whose commits were ancestors of master and seven branches that needed individual review. That count predates merges of PRs #26 and #27 and is now stale. Those two PR branches are merged; their heads are ancestors of master and they can be considered cleanup candidates after checking for any remaining use. No branch was deleted.

Keep these distinctions during a fresh audit:
- `chatgpt-agent-guidance` — preserve; this is the live handoff branch.
- `chatgpt/discrete-math-rule-coverage` — compare its branch-only test patch with merged PR #24.
- `chatgpt/refinement-type-system-design` — compare the branch-only design-doc commit with merged PR #22.
- `chatgpt/type-metadata-reference-schema` — compare the branch-only design-doc commit with merged PR #25.
- `chatgpt-context-docs` — inspect its branch-only changes to `ARCHITECTURE_STATUS.md`, `README.md`, and `todos.txt` before deciding whether they are superseded.

This list is not a substitute for a fresh compare against current master. Branch ancestry is evidence, not proof that a branch is unnecessary. Do not delete an uncertain branch; preserve the live handoff branch and remove only verified stale branches.

## 5. Active work and design recommendations

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

### C. Descriptive metadata collision — fixed by Claude; regression closed

The over-rejection was reproduced by ChatGPT's test-only probe against master commit `62374be`: a constant named `reflexive` was rejected as non-arbitrary solely because the same string appeared as a relation's property label. A relation's `carrier="X"`, however, is a genuine symbol reference and must still constrain `X`.

Claude fixed this on master in [commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d04f81b5a8aa7febcb73786a4274000f):

- `source/ProofLogic.py` now defines `DESCRIPTIVE_METADATA_KEYS = frozenset({"properties"})`. `_metadata_names` skips values under this explicitly audited descriptive key but remains conservative for values under every unlisted key.
- The sound proof is added as red-team case 20 and accepted. The refusal-reason test now checks all 20 cases.
- Regression tests check that a property-label collision is accepted, a carrier remains restricted even when its spelling is `reflexive`, `symmetric`, `properties`, or `carrier`, nested metadata is traversed, unknown metadata keys remain conservative, and the proof-validator path also accepts the sound case.
- The commit reports 51 mutation checks caught, including four mutants for this change.

**CI evidence:** [run #38112685219](https://github.com/axiomtutor/SyLoPy/actions/runs/38112685219) on master reports **906 passed, 1 failed**, coverage passed, enforced fixtures **79/79**, informational fixtures **51/52**. The only failure is the known deferred `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`; no new failure is reported. The metadata regression is therefore considered fixed, not active work.

Do not reopen this fix or duplicate Claude's kernel change absent a counterexample. The longer-term `Declaration.symbol_references` schema remains a design possibility associated with the type-system work; Claude deliberately deferred that broader change rather than expanding kernel scope. The existing carrier-reference counter-tests must stay in place.

### D. Refinement types — design-only

The owner's latest direction is that “Let X be an integer” should eventually establish the ordinary predicate Int(X), but implementation is explicitly deferred pending approval. PR #22 lays out a separate type-checking judgment and source-mapped typing obligations.

Important hazards to test/design before implementation:

- A type fact introduced within a subproof must have an intentional scope lifetime; premise-tagged lines may be recorded in a global hypothesis list, so do not assume the ordinary premise mechanism is sufficient for local type facts.
- Surface divisibility a|b requires type obligations for **both operands**. Its current expansion exists m, (Int(m) and b = Times(a,m)) loses the source-level fact that b was an operand; checking only the Times signature is insufficient.
- Type.as_declaration_recipe() appears to distinguish typed-function targets but not tuple targets. If the grammar accepts “(a, b) be an integer”, the generic recipe may interpret the tuple members as separate integer declarations. Test tuple targets and preserve intended grouped-name behavior before enabling descriptors broadly.
- A local type assumption is not by itself typed universal quantification. A construct such as “forall integer n, P(n)” needs its own explicit semantics if desired.
- Source tracing corrected an earlier suspicion about “such that”: compound declarations appear to dispatch through declaration recipes in the normal surface syntax path. This was a code-path inspection, not an end-to-end test.

Do not begin implementation until the owner chooses a scope and explicitly authorizes it. A sensible initial slice would be tests and a formula-producing declaration recipe, but it must address scope first; full signature checking and divisibility obligations are distinct work.

## 6. Recommended order of work

1. Get Copilot's theorem-promotion audit report and resolve any soundness or specification issues it exposes.
2. Ask the owner to confirm the contract for relation declarations inside subproofs; if allowed, verify the candidate with a focused test.
3. The metadata-label over-rejection is fixed by Claude's [master commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d04f81b5a8aa7febcb73786a4274000f). Keep carrier-reference refusals and the new property-label acceptance regressions. Treat `Declaration.symbol_references` as a future design option, not an active kernel task.
4. Get an explicit owner decision on the initial type-system implementation scope. Before implementing it, test local type-fact scope and tuple-target handling.
5. Keep parser-oracle expansion and public language-reference documentation as useful follow-on work, but do not let documentation displace a demonstrated soundness issue.
6. Leave WLOG, Mutatis mutandis, named ZFC axiom citations, and other explicitly deferred set-theory work untouched until the owner authorizes implementation.

## 7. Requests for the next handoff

**Owner:** please confirm whether relation declarations are intended to work in subproofs, and whether the next type-system milestone should be (a) formula-producing typed declaration recipes only, or (b) that plus a tightly bounded first signature-checking slice. Neither is authorized yet.

**Copilot:** please post the theorem-promotion audit status, exact findings, and CI results. If it is not underway, confirm that before anyone duplicates it.

**Claude:** the descriptive-property-label false rejection is fixed in master by commit [5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d04f81b5a8aa7febcb73786a4274000f). No further kernel work is requested for that issue absent a counterexample. Please clarify whether relation declarations inside subproofs are intentionally supported, and flag any evidence of overlap with typing work.

**All agents:** the metadata over-rejection is closed; preserve both the property-label acceptance and carrier-reference refusal tests. Next useful independent work remains Copilot's theorem-promotion audit and a confirmed contract/test for relation-rule scope inside subproofs. Do not begin deferred type-system or set-theory work without the owner's approval.
