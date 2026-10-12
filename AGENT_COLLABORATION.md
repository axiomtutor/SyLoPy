# SyLoPy Agent Collaboration — Current Handoff

This branch is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is intentionally separate from master/AGENT_COLLABORATION.md, which contains stable agent guidance. The owner has final authority over design and task priorities.

This file is a **current summary, not a chronological diary**. Keep durable decisions, verified findings, active questions, owners, and links here. Put implementation detail and discussion in the relevant PR or design document; when a question is resolved, replace the open question with the decision rather than appending another transcript.


## Current owner decisions and implementation status (2026-10-12)

- **Current master:** [`5cf4073`](https://github.com/axiomtutor/SyLoPy/commit/5cf40731f9204105a51052429344b6a36293272d), after merges of PRs #28–31, #34, and #35. Master CI [#38191934773](https://github.com/axiomtutor/SyLoPy/actions/runs/38191934773) reports 920 passed and the one established failure, `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`, which is blocked on the deferred WLOG / Mutatis mutandis work.
- **Declaration scope contract confirmed; kernel ownership remains with Claude.** Declarations made inside a subproof are visible in that scope and descendants, not in sibling or enclosing scopes after closure. Claude owns changes to `source/ProofLogic.py` and `source/ProofJustification.py`. Closed PR #33 remains a code/test reference only.
- **Relation-scope regression PR #36:** [PR #36](https://github.com/axiomtutor/SyLoPy/pull/36) adds four strict expected-failure probes for local relations: use within scope without escape, inheritance into a nested subproof, sibling-property isolation, and local transitivity. CI [#38192198303](https://github.com/axiomtutor/SyLoPy/actions/runs/38192198303) reports 920 passed, 4 xfailed, and only the established ZFC fixture failure. These xfails describe behavior still awaiting Claude's kernel fix; they are not evidence that local relations work yet.
- **Typed-declaration follow-up PR #37:** [PR #37](https://github.com/axiomtutor/SyLoPy/pull/37) moves the Int/Nat declaration recipes into `NUMBER_THEORY_ENVIRONMENT`, makes base-language line elaboration available with an explicitly selected theory environment, adds a direct-environment regression, and restores the typing soundness invariant in `todos.txt`. Latest CI [#38192416287](https://github.com/axiomtutor/SyLoPy/actions/runs/38192416287) reports 921 passed and only the known ZFC fixture failure; the new regression passes.
- **Type design remains proposal-only:** PR #35 documents optional typed-quantifier sugar; it authorizes no parser or kernel implementation. Typed declarations state ordinary citable `Int(n)` / `Nat(n)` facts and are not a refinement type checker.
- **Cleanup limitation:** the available GitHub connection still exposes no branch-delete operation. Do not claim obsolete branches were deleted.

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

**Current master:** commit [`5cf40731f9204105a51052429344b6a36293272d`](https://github.com/axiomtutor/SyLoPy/commit/5cf40731f9204105a51052429344b6a36293272d). Master CI [#38191934773](https://github.com/axiomtutor/SyLoPy/actions/runs/38191934773) reports 920 passed and one failure: `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`. The fixture requires WLOG and Mutatis mutandis, both explicitly deferred pending authorization. Counts below are run-specific snapshots.

### Active pull requests and test evidence

- [PR #36 — Add pending tests for scoped relation declarations](https://github.com/axiomtutor/SyLoPy/pull/36) is test-only. Four strict xfails cover local declaration use, nested visibility, sibling isolation, and transitivity. CI [#38192198303](https://github.com/axiomtutor/SyLoPy/actions/runs/38192198303) reports 920 passed, 4 xfailed, plus only the known ZFC fixture failure. The tests should become ordinary required regressions after Claude's kernel implementation lands.
- [PR #37 — Register typed declaration recipes in number theory](https://github.com/axiomtutor/SyLoPy/pull/37) updates `NumberTheory.py`, parser base-elaborator dispatch, typed-declaration tests, and `todos.txt`. CI [#38192416287](https://github.com/axiomtutor/SyLoPy/actions/runs/38192416287) reports 921 passed plus the same single known ZFC failure; the new direct-environment regression passes. The first CI run exposed a missing generic line-elaborator path for explicitly selected theory environments; that was corrected before the current run.
- PRs [#28](https://github.com/axiomtutor/SyLoPy/pull/28), [#29](https://github.com/axiomtutor/SyLoPy/pull/29), [#30](https://github.com/axiomtutor/SyLoPy/pull/30), [#31](https://github.com/axiomtutor/SyLoPy/pull/31), [#34](https://github.com/axiomtutor/SyLoPy/pull/34), and [#35](https://github.com/axiomtutor/SyLoPy/pull/35) are merged. PR #31's two review follow-ups are now in PR #37; PR #34's root-relation scope guards remain merged and must stay passing.
- [PR #33](https://github.com/axiomtutor/SyLoPy/pull/33) is closed and unmerged; its scope-aware implementation and nested tests are reference material only. Nested probes on that closed PR were not run by CI.

### Merged audit and proof work

- [PR #18](https://github.com/axiomtutor/SyLoPy/pull/18): Uniqueness red-team cases with refusal-reason checks.
- [PR #19](https://github.com/axiomtutor/SyLoPy/pull/19): scope/freshness audit.
- [PR #20](https://github.com/axiomtutor/SyLoPy/pull/20): number-theory quotient/divisibility and natural-number induction audit.
- [PR #21](https://github.com/axiomtutor/SyLoPy/pull/21): textbook-style proof fixtures across Nat, set theory, number theory, and discrete math.
- [PR #22](https://github.com/axiomtutor/SyLoPy/pull/22): design-only refinement type-system proposal.
- [PR #23](https://github.com/axiomtutor/SyLoPy/pull/23) and [PR #24](https://github.com/axiomtutor/SyLoPy/pull/24): relation-rule coverage and property-gating tests.
- [PR #25](https://github.com/axiomtutor/SyLoPy/pull/25): metadata symbol-reference design clarification.
- [PR #26](https://github.com/axiomtutor/SyLoPy/pull/26) and [PR #27](https://github.com/axiomtutor/SyLoPy/pull/27): project-status and stable-agent-guidance documentation.

Claude's Uniqueness fix [commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f) added red-team case 20 and corrected over-rejection when a constant happens to share a relation-property label. Preserve both the positive property-label test and carrier-reference refusal tests.

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

This is a gap in the safe direction (an acceptance that is missing), not a soundness hole. The owner confirmed the scope contract on 2026-10-11; no further design decision is required. A flat table of all declarations keyed by relation name would be **unsound** because a sibling could inherit a property declared only in another sibling. The kernel fix remains Claude's task. ChatGPT's pending tests are isolated in [PR #36](https://github.com/axiomtutor/SyLoPy/pull/36); the four strict xfails are intentionally pending implementation, and their CI run is documented in §3.

### C. Descriptive metadata collision — fixed by Claude; regression closed

The over-rejection was reproduced by ChatGPT's test-only probe against master commit `62374be`: a constant named `reflexive` was rejected as non-arbitrary solely because the same string appeared as a relation's property label. A relation's `carrier="X"`, however, is a genuine symbol reference and must still constrain `X`.

Claude fixed this on master in [commit 5df7d5d](https://github.com/axiomtutor/SyLoPy/commit/5df7d5d7d04f81b5a8aa7febcb73786a4274000f):

- `source/ProofLogic.py` now defines `DESCRIPTIVE_METADATA_KEYS = frozenset({"properties"})`. `_metadata_names` skips values under this explicitly audited descriptive key but remains conservative for values under every unlisted key.
- The sound proof is added as red-team case 20 and accepted. The refusal-reason test now checks all 20 cases.
- Regression tests check that a property-label collision is accepted, a carrier remains restricted even when its spelling is `reflexive`, `symmetric`, `properties`, or `carrier`, nested metadata is traversed, unknown metadata keys remain conservative, and the proof-validator path also accepts the sound case.
- The commit reports 51 mutation checks caught, including four mutants for this change.

**CI evidence:** [run #38112685219](https://github.com/axiomtutor/SyLoPy/actions/runs/38112685219) on master reports **906 passed, 1 failed**, coverage passed, enforced fixtures **79/79**, informational fixtures **51/52**. The only failure is the known deferred `pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass`; no new failure is reported. The metadata regression is therefore considered fixed, not active work.

Do not reopen this fix or duplicate Claude's kernel change absent a counterexample. The longer-term `Declaration.symbol_references` schema remains a design possibility associated with the type-system work; Claude deliberately deferred that broader change rather than expanding kernel scope. The existing carrier-reference counter-tests must stay in place.

### D. Typed declarations — owner-authorized; implementation merged, follow-up in PR #37

The owner authorized option A on 2026-10-11: a typed declaration states the corresponding ordinary formula on its declaration line. “Let X be an integer” asserts Int(X); “Let n be a natural number” asserts Nat(n). This uses `Type.as_declaration_recipe()`; the type predicates remain ordinary citable formulas. It does not implement refinement type checking or typed quantifier sugar.

Claude approved PR #31's behavior but requested two changes: register the recipes in `NUMBER_THEORY_ENVIRONMENT` instead of mutating the default environment, and restore the typing soundness invariant in `todos.txt`. Both are in [PR #37](https://github.com/axiomtutor/SyLoPy/pull/37). While adding the direct-environment regression, CI exposed that generic line elaborators were only registered by `default_theory_environment()`; the parser now applies base-language line elaborators even when a caller supplies a specific theory environment. The latest CI reports 921 passed plus only the established WLOG / Mutatis mutandis fixture failure (§3).

The soundness invariant is explicit in `todos.txt`: every typing fact a proof relies on must reach the kernel as an ordinary recorded formula or explicit declaration metadata. A separate type checker may reject an ill-typed expression but must never independently justify an inference step.

## 6. Recommended order of work

1. **Claude:** implement the confirmed relation-scope semantics in the kernel. Relation properties must be read from the declaration visible at the line being validated; do not flatten declarations from different sibling scopes into one name-keyed table. PR #33 is a closed reference only.
2. **ChatGPT/Copilot:** keep work test-only around the kernel boundary. PR #36 supplies four pending scoped-relation probes; preserve PR #34's existing root-declaration guards. After the kernel fix lands, remove the xfail markers and expand the audit to Fresh Variable scopes and theorem promotion.
3. **Owner:** review PR #36 and PR #37. PR #37 includes Claude's two follow-ups to typed-declaration PR #31. This handoff does not authorize auto-merging.
4. Keep WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, Infinity, the full refinement type checker, and relativized quantifier sugar deferred absent separate owner authorization.

## 7. Requests for the next handoff

**Owner decisions already recorded:** typed declaration option A is authorized; declarations in subproofs are local to the subproof and descendants. No further design decision is needed for the relation-scope kernel fix.

**Claude:** implement the scoped relation-property lookup and preserve the existing guards in PR #34. PR #36 has CI evidence in §3: its four xfailed tests specify the behavior to enable. When they pass, the xfail markers should be removed rather than left in place.

**ChatGPT:** PR #37 contains the theory-local typed-declaration follow-ups and currently has only the known deferred fixture failure. Once Claude's kernel fix reaches master, update/rebase the test branch as needed, remove the xfail markers on PR #36, and add test-only probes for (1) a relation in a Fresh Variable subproof, (2) a relation declared in a nested child that must not escape to its parent or sibling, and (3) theorem promotion for a proof that used a local relation. For each refusal, assert the exact label and error category so an unrelated earlier failure does not masquerade as a successful guard.

**Copilot:** the theorem-promotion audit described in §5.A remains unclaimed: no audit report or remote Copilot branch is recorded. Claude should take it after prioritizing relation-scope work unless Copilot supplies the audit.

**All agents:** preserve the distinction between settled semantics, design proposals, and observed CI. The known ZFC fixture failure remains the deferred WLOG / Mutatis mutandis test; do not suppress it with an xfail or conflate it with new failures.
