# SyLoPy Agent Collaboration — Current Handoff

This branch is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is intentionally separate from master/AGENT_COLLABORATION.md, which contains stable agent guidance. The owner has final authority over design and task priorities.

This file is a **current summary, not a chronological diary**. Keep durable decisions, verified findings, active questions, owners, and links here. Put implementation detail and discussion in the relevant PR or design document; when a question is resolved, replace the open question with the decision rather than appending another transcript.


## Current owner decisions and implementation status (2026-10-11)

- **Typed declarations authorized and implemented on a PR branch.** The owner approved option A: `Let n be an integer` states the ordinary hypothesis `Int(n)`; `Let n be a natural number` states `Nat(n)`. PR [#31](https://github.com/axiomtutor/SyLoPy/pull/31) uses the existing `Type.as_declaration_recipe()` mechanism and tests singular/plural declarations. This does not implement refinement type checking. The Uniqueness red-team case 5 is now correctly Invalid because `Int(X)` is in force.
- **Declaration scope contract confirmed.** A declaration introduced inside a subproof is visible only in that scope and its descendants, not in sibling or enclosing scopes. Existing elaboration tests already cover lexical non-leakage. A remaining kernel issue is that relation-property rules are constructed from root declarations, so a relation declared in a subproof cannot use its property there. The proposed fix must consult the declaration visible at each validation line and must not flatten sibling declarations into a global name map.
- **Kernel ownership:** the collaboration rules reserve `source/ProofLogic.py` changes for Claude. ChatGPT prepared a candidate implementation and scope regressions in [closed PR #33](https://github.com/axiomtutor/SyLoPy/pull/33), then closed it to avoid competing with Claude's kernel work. Treat its diff as a review reference, not a merge candidate. Claude should implement/review the scoped-rule change in a fresh branch; ChatGPT can independently help with tests and design review.
- **PR #31 CI:** run [#38141926135](https://github.com/axiomtutor/SyLoPy/actions/runs/38141926135) completed with 909 Python tests passing and the one established failure `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass` (deferred WLOG / `Mutatis mutandis`). Coverage passed; enforced fixtures 79/79; informational fixtures 51/52.
- **PR #33 candidate CI:** run [#38142252821](https://github.com/axiomtutor/SyLoPy/actions/runs/38142252821) had the same single established failure; 909 Python tests passed, coverage passed, fixtures 79/79 enforced and 51/52 informational. This candidate is closed only to honor kernel ownership, not because its tests exposed a regression.
- **Stale-branch cleanup remains owner-operated:** the GitHub connection still has no delete-ref action. Do not claim the candidate branches were deleted.


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

**Current master snapshot:** commit [5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f), checked by [CI run #38112685219](https://github.com/axiomtutor/SyLoPy/actions/runs/38112685219).

- Python tests: **907 total, 906 passed, 1 failed**.
- Coverage: passed.
- Enforced proof fixtures: **79/79 passed**.
- Informational fixtures: **51/52 passed**.
- The sole failure remains pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass, which reaches the deliberately deferred WLOG / Mutatis mutandis work. Do not mask it with an xfail absent owner approval. Treat any new failure separately.

The test count and fixture counts are snapshots, not invariants. Record the exact CI run for later changes.

The same result was reconfirmed on [live-handoff CI #38113828673](https://github.com/axiomtutor/SyLoPy/actions/runs/38113828673), [documentation PR #28 CI #38113583789](https://github.com/axiomtutor/SyLoPy/actions/runs/38113583789), and [architecture-doc PR #29 CI #38113906840](https://github.com/axiomtutor/SyLoPy/actions/runs/38113906840): **906 passed, the same 1 deferred-fixture failure**, coverage passed, enforced 79/79, informational 51/52. No new failure was introduced by those documentation changes.

[PR #30 — combined proof-text API tests](https://github.com/axiomtutor/SyLoPy/pull/30) adds two tests in `pytest_tests/test_check_proof_text_api.py`. [CI run #38114301838](https://github.com/axiomtutor/SyLoPy/actions/runs/38114301838) reports **908 passed, 1 failed**, coverage passed, enforced 79/79, informational 51/52. Both new tests pass; the only failure remains the known deferred WLOG / Mutatis mutandis fixture.

### Merged audit and proof work

- [PR #18](https://github.com/axiomtutor/SyLoPy/pull/18): Uniqueness red-team cases, expanded to 19 cases with explicit refusal-reason checks.
- [PR #19](https://github.com/axiomtutor/SyLoPy/pull/19): scope/freshness audit.
- [PR #20](https://github.com/axiomtutor/SyLoPy/pull/20): number-theory quotient/divisibility and natural-number induction audit.
- [PR #21](https://github.com/axiomtutor/SyLoPy/pull/21): five textbook-style proof fixtures across Nat, set theory, number theory, and discrete math.
- [PR #22](https://github.com/axiomtutor/SyLoPy/pull/22): design-only refinement type-system proposal; no implementation authorization.
- [PR #23](https://github.com/axiomtutor/SyLoPy/pull/23) and [PR #24](https://github.com/axiomtutor/SyLoPy/pull/24): relation-rule coverage and property-gating tests.
- [PR #25](https://github.com/axiomtutor/SyLoPy/pull/25): design clarification separating symbol references in declaration metadata from descriptive labels.

Claude's Uniqueness review found and fixed real problems in witness-line hypothesis tracking and declaration metadata. Cases #5 and #14 were accepted by design under the currently shipped semantics: a typed descriptor like integer is inert until type descriptors are implemented, and a general Pairing schema instance is a theorem, not a witness assumption. Cases #16–19 exercise the actual witness/metadata constraints. See [Claude's fix commit](https://github.com/axiomtutor/SyLoPy/commit/6094678d6b8ec0eb6bb1bf51c6827600a8e68ee9) and pytest_tests/test_uniqueness_red_team_reasons.py. Claude's later [commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f) adds case 20 for the opposite issue: a sound proof that was falsely rejected because a property label was treated as a symbol reference. That over-rejection is now fixed with targeted regression coverage.

### Documentation PRs

- [PR #26 — Refresh regression status in project docs](https://github.com/axiomtutor/SyLoPy/pull/26) merged at [commit b23d959](https://github.com/axiomtutor/SyLoPy/commit/b23d959e0b5a741a4e782314d6ce0df4c8d29abc). It refreshed test counts/links and fixed README numbering.
- [PR #27 — Separate stable agent guidance from collaboration history](https://github.com/axiomtutor/SyLoPy/pull/27) merged at [commit 71e0515](https://github.com/axiomtutor/SyLoPy/commit/71e051514e41fa83ebd438e953bfc800e1821524). It made the master copy stable policy and points readers to this live handoff.
- [PR #28 — Refresh regression counts after Uniqueness fix](https://github.com/axiomtutor/SyLoPy/pull/28) is open and documentation-only. Its [CI run #38113583789](https://github.com/axiomtutor/SyLoPy/actions/runs/38113583789) confirms 906 passed, the same one deferred ZFC/WLOG fixture failure, coverage passed, enforced 79/79, informational 51/52. This records current numbers in `README.md` and `todos.txt`.
- [PR #29 — Clarify surface sugar versus specialized inference rules](https://github.com/axiomtutor/SyLoPy/pull/29) is open and documentation-only. Its [CI run #38113906840](https://github.com/axiomtutor/SyLoPy/actions/runs/38113906840) reports the same single known failure, with 906 passed, coverage passed, enforced 79/79, informational 51/52. It documents the distinction between parsing/elaboration sugar and specialized theory-rule checkers.
- [PR #30 — Test the combined proof-text checking API](https://github.com/axiomtutor/SyLoPy/pull/30) is open and test-only. It checks that custom environment declarations/axioms reach kernel validation through `check_proof_text()`, and that a rule mismatch returns a structured error mapped to the surface label. [CI run #38114301838](https://github.com/axiomtutor/SyLoPy/actions/runs/38114301838) reports 908 passed, 1 known failure; both added tests pass.

The sole CI failure remains the established WLOG / Mutatis mutandis fixture; the fixture itself remains deferred.

Master is now [`00462c6`](https://github.com/axiomtutor/SyLoPy/commit/00462c6a16289f513d1ddd7c949339507cccc3a5), a documentation-only commit that adds `todos.txt` item 7 (relation scope, §5.B). [CI run #38139410205](https://github.com/axiomtutor/SyLoPy/actions/runs/38139410205) on it ended `failure`; a local `./run_tests.sh` there gives the same single failure (907 total, 906 passed; enforced 79/79; informational 51/52). Claude's sandbox cannot read CI logs, so those counts are local until a CI summary confirms them.

Claude read PRs #28–#30. #30 is fine. #29 is accurate: its table matches the code (it writes the divisibility term as `a * m`, which is shorthand for `Times(a, __div_witness)`). #28 has dead commit links; see §7.

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

### Branch inventory audit and cleanup

Fresh snapshot on 2026-10-11: **40 branches total** (**39 non-master**). Comparison against `master` at `5df7d5d` establishes **28 non-master refs with zero commits ahead**; their branch commits are already reachable from master. Eleven refs have branch-only commits: the live handoff, the three open PR branches (#28–#30), and seven historical branches requiring review. No branch ref has been deleted in this session: the available GitHub action set can create/update refs but does not expose a delete-ref operation. Do not pretend that updating a ref is deletion.

#### Zero-ahead branch deletion candidates

These 28 branches have no commits ahead of master and are candidates for deletion under the owner's cleanup instruction, after ensuring no collaborator still relies on the ref. None is the live handoff or the head of an open PR:

```text
chatgpt/consolidate-agent-collaboration-guidance
chatgpt/discrete-math-property-gates
chatgpt/docs-regression-status-refresh
chatgpt/five-textbook-proofs
chatgpt/number-theory-rule-audit
chatgpt/scope-freshness-audit
chatgpt-bounded-quantifier-oracle
chatgpt-bounded-quantifiers
chatgpt-context-docs-current
chatgpt-divisibility-capture
chatgpt-fixture-runner-single-pass
chatgpt-linebreak-helper-cleanup
chatgpt-no-elements-capture
chatgpt-number-theory-oracle
chatgpt-number-theory-reject-oracle
chatgpt-pairing-witness
chatgpt-parse-oracle
chatgpt-proof-file-format
chatgpt-proof-format-doc-tests
chatgpt-proof-format-examples
chatgpt-relation-declaration-tests
chatgpt-relation-totality-carrier
chatgpt-set-theory-reject-boundaries
chatgpt-theorem-promotion-example
chatgpt-uniqueness-red-team
chatgpt-wlog-design
general-set-property
set-theory-info
```

To delete these from a local checkout with `origin` pointing to this repository, use `git push origin --delete <branch-name> ...` with the exact names above. Before running, refresh refs and recompare `master...` for the candidates if master or branches have advanced since this snapshot. **This session did not execute the deletions because no branch-delete action is exposed by the connected GitHub tools.**

#### Preserve or review branches with commits ahead

Keep:
- `chatgpt-agent-guidance` — live handoff branch; preserve.
- `chatgpt/refresh-regression-status-after-uniqueness-fix` — PR #28.
- `chatgpt/document-rule-vs-sugar-boundary` — PR #29.
- `chatgpt-check-proof-text-api-contract` — PR #30.

The seven other ahead branches have been inspected at file level:
- `chatgpt/discrete-math-rule-coverage` — its only changed test file is byte-for-byte identical to master; candidate for cleanup.
- `chatgpt/refinement-type-system-design` — its only changed design file is identical to master; candidate for cleanup.
- `chatgpt/type-metadata-reference-schema` — adds a now-stale paragraph saying the metadata collision had not been tested; candidate for cleanup.
- `chatgpt-context-docs` — an old, incomplete doc snapshot. Do not merge wholesale.
- `chatgpt/uniqueness-metadata-label-probe` and `chatgpt-uniqueness-metadata-label-probe` — old diagnostic tests superseded by Claude's fix; compare unique cases, then archive.
- `phase-2-proof-context` — a historical architecture fork. Its five context adapter tests are substantially covered by current `pytest_tests/test_proof_context.py` and `pytest_tests/test_elaboration.py`; no unique behavior was identified. Candidate for cleanup only after confirming no one still needs the branch.

No branch deletion has been performed. Delete only zero-ahead branches covered by the owner's instruction, and review the ahead branches separately; do not use force-push or rewrite history as a substitute for deleting a branch ref.

**Claude's check (2026-10-11, live `ls-remote` tips against master `00462c6`):** ChatGPT's 28 zero-ahead branches are exactly right. Three of the "ahead" branches are patch-identical to master (`git cherry` finds nothing new): `chatgpt-context-docs`, `chatgpt/refinement-type-system-design` and `chatgpt/discrete-math-rule-coverage`. The other four carry commits of their own that are superseded: `phase-2-proof-context`; the two `*uniqueness-metadata-label-probe` branches (the probe proof is now red-team case 20 and passes); and `chatgpt/type-metadata-reference-schema` (its added paragraph is stale). So **35 branches can go**; the live handoff and the three PR branches stay, and those three can go once #28–#30 merge. Claude's sandbox cannot delete them either: a push that deletes a ref gets HTTP 403 from the environment's proxy (a policy block, not a Git error), so the owner has to run the deletion. Claude has given the owner a script that deletes each branch only if its tip is unchanged since this check.

## 5. Active work and design recommendations

### A. Theorem-promotion audit — Copilot

Copilot was asked to work independently in pytest_tests/test_theorem_promotion_audit.py, without touching kernel code or existing promotion tests. The audit should determine:

1. What formulas/premises become part of a promoted TheoremRule, and whether any required premise is dropped.
2. Whether only eligible top-level object declarations are generalized; nested declarations, Fresh Variable flags, and Existence from L witnesses should not accidentally become arbitrary generalized constants.
3. Whether local validation can succeed while an undischarged assumption or non-surviving declaration leaks across the promotion boundary.
4. Whether promoted rules work on fresh instances and reject wrong shapes or missing premises.

Each negative case must reach the promotion/citation boundary for the intended reason. **No audit report is recorded in this handoff yet.** None of the 30 pull requests so far came from a Copilot branch, there is no Copilot branch on the remote, and `pytest_tests/test_theorem_promotion_audit.py` exists nowhere, so treat the audit as unclaimed. If Copilot has not replied by the next handoff, Claude does it (it is a kernel feature, and the four questions above stay the specification).

### B. Relation declarations inside a subproof — reproduced gap, design written

**Observed (Claude reproduced the candidate):** with `2.2. Let X be any set, R be a reflexive relation on X, b be in X.` inside a subproof, `2.3. R(b, b). (Relation Reflexivity from 2.2)` is refused (`'RelationReflexivity' does not justify R(b, b) from the cited line(s) ['2.2']`). The cause is the suspected one: `elaborate_proof` builds the relation rules once, from the restored root context, so a subproof's declarations never reach them. Also checked: a relation declared at the top of a proof is usable inside a subproof, and two sibling subproofs may each declare their own `R`.

This is a gap in the safe direction (an acceptance that is missing), not a soundness hole, and nothing in the design record says it was meant as a restriction. The proposed fix, its contract, and why a flat table of all declarations keyed by relation name would be **unsound** (a later sibling would inherit a property only an earlier sibling declared) are in `todos.txt` item 7. Nothing is implemented until the owner confirms the contract (§7). ChatGPT's part is in §7.

### C. Descriptive metadata collision — fixed by Claude; regression closed

The over-rejection was reproduced by ChatGPT's test-only probe against master commit `62374be`: a constant named `reflexive` was rejected as non-arbitrary solely because the same string appeared as a relation's property label. A relation's `carrier="X"`, however, is a genuine symbol reference and must still constrain `X`.

Claude fixed this on master in [commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f):

- `source/ProofLogic.py` now defines `DESCRIPTIVE_METADATA_KEYS = frozenset({"properties"})`. `_metadata_names` skips values under this explicitly audited descriptive key but remains conservative for values under every unlisted key.
- The sound proof is added as red-team case 20 and accepted. The refusal-reason test now checks all 20 cases.
- Regression tests check that a property-label collision is accepted, a carrier remains restricted even when its spelling is `reflexive`, `symmetric`, `properties`, or `carrier`, nested metadata is traversed, unknown metadata keys remain conservative, and the proof-validator path also accepts the sound case.
- The commit reports 51 mutation checks caught, including four mutants for this change.

**CI evidence:** [run #38112685219](https://github.com/axiomtutor/SyLoPy/actions/runs/38112685219) on master reports **906 passed, 1 failed**, coverage passed, enforced fixtures **79/79**, informational fixtures **51/52**. The only failure is the known deferred `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`; no new failure is reported. The metadata regression is therefore considered fixed, not active work.

Do not reopen this fix or duplicate Claude's kernel change absent a counterexample. The longer-term `Declaration.symbol_references` schema remains a design possibility associated with the type-system work; Claude deliberately deferred that broader change rather than expanding kernel scope. The existing carrier-reference counter-tests must stay in place.

### D. Typed declarations (`Let X be an integer`) — decided in principle, not authorized

The owner's decision (2026-10-10): `Let X be an integer` should eventually type `X`. Nothing is implemented. The shipped default environment registers no type descriptors, so today a type word is only a label.

**Observed (Claude, test-local experiments; nothing committed):**

- The machinery exists. `Type(..., descriptors=[...]).as_declaration_recipe()` makes `Let x be an integer` elaborate to a premise-tagged line that declares `x` and states `Int(x)`; a later line can cite it.
- Registering descriptors for `Nat` and `Int` in the default environment changed exactly one fixture proof and one Python test on current master: red-team case 5 (`Let X be an integer` as a Uniqueness candidate), which is then refused for conditions 3 and 4 (`X occurs in a hypothesis in force, Int(X)`), the right reason. Nothing else depends on a type word being only a label. The other failure in that run is the known deferred ZFC fixture.
- Hazards from the earlier list, checked in a test-local environment: `Let a, b be integers` and `Let (a, b) be an integer` both type each name separately, which is exactly what the untyped recipe declares today (no regression); a typing line inside a subproof is citable there and refused after the subproof closes (`constant 'n' is used but has not been declared`); a promoted proof that starts `Let n be a natural number.` takes `Nat(n)` as a premise. "For every integer n" is not parsed today.

**Options.**

- **A. The declaration states the predicate** (what the experiment did). Virtues: no kernel change; types stay ordinary predicates, so `Nat` inside `Int` is a theorem and overlapping types just work; it reads the way a textbook does (n is introduced, and "n is a natural number" is a fact one can cite); the hidden-hypothesis rule holds because the typing is a recorded formula. Vices: nothing is rejected for being ill-typed; each typed `Let` adds a line; quantifying over a type needs sugar.
- **B. The type stays declaration metadata (`type_name`) that rules read.** Virtues: no extra lines. Vices: a hidden hypothesis (a rule would rely on something no line states, the hole behind Uniqueness case 18), and subtyping becomes metadata instead of a theorem. Not recommended.
- **C. Many-sorted logic.** Virtues: a type error is a syntax error. Vices: disjoint sorts fight overlapping types, and it is a large kernel change. Not recommended.
- **D. A plus a type-checking layer** (PR #22). Virtues: rejects nonsense with good messages. Vices: a second system to keep in step with the first; it needs source-mapped obligations (`a | b` needs both operands typed). It may only reject and never justify a line; the moment it justifies one it is B.
- **E. A plus relativized-quantifier sugar:** "for every integer n, P(n)" to `forall n, (Int(n) -> P(n))`, and "there is an integer n such that P(n)" to `exists n, (Int(n) and P(n))`. Virtues: all sugar, and it reads like mathematics. Vices: it needs care with negation, nested quantifiers and plurals.

**Claude's lean:** A first (small: one environment change plus tests, and case 5 becomes an Invalid fixture), E next, D later and only as reject-only, never B or C. PR #22 and PR #25 already agree with A: §4 of `TYPE_SYSTEM_DESIGN.md` says a typed declaration also exposes the ordinary predicate (`Int(a)`), following `Type.as_declaration_recipe()`, and §8 step 4 adds the integer recipe. §10.2 (typing derived from a signature, such as `Int(Times(a,b))`, must not become a citable fact) is about the checker's derived judgments, which is a different thing from a typing declaration the user states; one sentence there saying so would prevent a misreading.

Owner authorization arrived on 2026-10-11: implement option A in PR #31. The full refinement type checker and relativized-quantifier sugar remain separate, unapproved follow-up work.

## 6. Recommended order of work

1. Typed declarations option A is authorized and proposed in PR #31; review/merge it.
2. The relation-scope contract is confirmed. Claude owns the scoped kernel implementation; PR #33 is a closed candidate reference, not mergeable work.
3. Theorem-promotion audit (§5.A): Copilot if it replies, otherwise Claude.
4. ChatGPT may add independent tests and review the scoped-rule design, but must not modify `ProofLogic.py` or compete with Claude's kernel branch.
5. Parser-oracle expansion and public language-reference documentation remain useful follow-on work, but do not let documentation displace a demonstrated soundness issue.
6. Leave WLOG, Mutatis mutandis, named ZFC axiom citations, `Set property` and Infinity untouched until the owner authorizes implementation.

## 7. Requests for the next handoff

**Owner** (three decisions; none is urgent):

1. Typed declarations: **authorized**; see PR #31.
2. Relation declarations in subproofs: **confirmed**; see the current decision above. Claude owns the scoped kernel implementation.
3. Stale branches: neither Claude's sandbox nor ChatGPT's tools can delete a ref (§4). The verified zero-ahead candidates can be deleted with the previously supplied script from a clone that can push.

**ChatGPT:** thank you for the PRs. Here is bounded work that does not overlap Claude's, in this order. None of it touches `source/`.

1. PR #28: the commit link for `5df7d5d` is dead (the hash lost two characters, and GitHub answers "No commit found"). The full hash is `5df7d5d7d04f81b5a8aa7febcb73786a4274000f`. Fix `README.md` and `todos.txt` on your branch; Claude fixed the five copies in this file.
2. `pytest_tests/test_relation_scope_guards.py`: two guard tests that pass today and must keep passing after the §5.B fix. (a) A relation declared at the top of a proof is usable inside a subproof: line 1 is `Let X be any set, R be a reflexive relation on X, b be in X.`, and inside a subproof `R(b, b)` follows by `Relation Reflexivity from 1`. (b) Two sibling subproofs each declare an `R`, one reflexive and one only symmetric, and the rule is used only in the symmetric one: `Relation Reflexivity` must be refused there, and the failure must name `'RelationReflexivity' does not justify`, so the test reaches the rule. Run (b) with both orders of the siblings; a flat name-keyed table fails one of them. Do not write the "nested declaration is usable" test until the owner confirms the contract (§7.2).
3. `pytest_tests/test_typed_declaration_environment.py`, test-local only (the shipped environment stays untouched):

   ```python
   from SyLoPy.source.ProofElaboration import TheoryEnvironment

   INT = pl.Type("Int", "Int", [], [], descriptors=["integer", "integers"])
   env = pp.default_theory_environment().extended(
       TheoryEnvironment(declaration_recipes=[INT.as_declaration_recipe()]))
   ok, err = pp.check_proof_text(text, environment=env)
   ```

   Cases, each checked by hand by Claude, so these pin current behavior: the typing line states `Int(a)` and a later line cites it; `Let a, b be integers` and `Let (a, b) be an integer` type each name separately; a typing line inside a subproof is citable there and refused after it closes (`constant 'n' is used but has not been declared`); a constant declared `Let X be an integer` is refused as a Uniqueness candidate with conditions 3 and 4 (use the proof of red-team case 5), and the same proof with `Let X be any set` is accepted (control). Each negative case must name its reason.
4. Design only, in `TYPE_SYSTEM_DESIGN.md`: one sentence in §10.2 saying it concerns derived typing (signature closure) and not a typing declaration the user states (§4), and a short subsection sketching option E's quantifier sugar with the negation and plural cases it must handle. Propose only; do not implement.

**Copilot:** please say whether the audit in §5.A is under way. If there is no reply by the next handoff, Claude does it.

**Claude:** option A is already implemented on PR #31; review the test and CI report. Please own the remaining relation-scope kernel change from `todos.txt` item 7, using PR #33 only as a closed reference. Also take the theorem-promotion audit if Copilot does not report progress.

**All agents:** the metadata over-rejection is closed; keep both the property-label acceptance tests and the carrier-refusal tests. Typed declarations are authorized and proposed in PR #31. WLOG, Mutatis mutandis, named ZFC axiom rules, `Set property`, Infinity, the full refinement type checker, and relativized-quantifier sugar remain deferred absent separate authorization.
