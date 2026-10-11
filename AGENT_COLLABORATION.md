# SyLoPy Agent Collaboration — Current Handoff

This branch is the live coordination record for the owner, Claude, ChatGPT, and Copilot. It is intentionally separate from master/AGENT_COLLABORATION.md, which contains stable agent guidance. The owner has final authority over design and task priorities.

This file is a **current summary, not a chronological diary**. Keep durable decisions, verified findings, active questions, owners, and links here. Put implementation detail and discussion in the relevant PR or design document; when a question is resolved, replace the open question with the decision rather than appending another transcript.


## Current owner decisions and implementation status (2026-10-11)

- **Typed declarations (owner-authorized; PR #31).** “Let n be an integer” asserts the ordinary, citable hypothesis Int(n); “Let n be a natural number” asserts Nat(n). This is not refinement type checking. Tests cover singular/plural forms, citation, subproof locality, comma-grouped declarations, and tuple-shaped targets. Latest CI is recorded below.
- **Declaration scope contract confirmed.** Every declaration introduced in a subproof is visible throughout that subproof and descendants, but not in siblings or outside the subproof after closure. Relation-property rules currently use a root-built table and therefore miss locally declared relations. The kernel fix must consult the declaration visible at the exact validation line.
- **Kernel ownership.** Changes to source/ProofLogic.py and source/ProofJustification.py are reserved for Claude. Closed PR #33 is an implementation/test reference, not a merge candidate. It includes unverified nested-scope probes. The independent passing guard tests are in PR #34.
- **Relation-scope guard PR #34.** Latest CI [#38147356859](https://github.com/axiomtutor/SyLoPy/actions/runs/38147356859): 910 passed, one established WLOG / Mutatis mutandis fixture failure; coverage passed, enforced fixtures 79/79, informational 51/52. Added a guard that a root relation property remains usable two subproof levels down.
- **Typed declaration PR #31.** The latest [CI run #38147129717](https://github.com/axiomtutor/SyLoPy/actions/runs/38147129717) reports 914 passed and only the established WLOG / Mutatis mutandis fixture failure; coverage passed, enforced fixtures 79/79, informational 51/52. The new theorem-promotion test confirms `Int(n)` remains a required premise and `n` is generalized when the proof is promoted.
- **Documentation cleanup PR #28.** The malformed commit URL has been corrected in README.md and todos.txt. [CI #38145947220](https://github.com/axiomtutor/SyLoPy/actions/runs/38145947220): 906 passed and only the established WLOG / Mutatis mutandis failure; coverage passed, enforced 79/79, informational 51/52.
- **Type-design PR #35.** PR #35 is documentation-only: it distinguishes explicit typed declarations from signature-derived typing and sketches optional quantifier sugar, including plural and negation cases. It grants no parser or kernel implementation authorization.
- **Other open work.** PRs #29 (surface sugar vs. specialized rules) and #30 (combined proof-text API tests) remain open; #30 CI run #38114301838 reports 908 passed and the same single deferred fixture failure.
- **Cleanup limitation.** The available GitHub connection still has no delete-ref action. Do not claim obsolete branches were deleted.

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

**Current master:** commit [00462c6a16289f513d1ddd7c949339507cccc3a5](https://github.com/axiomtutor/SyLoPy/commit/00462c6a16289f513d1ddd7c949339507cccc3a5). [CI run #38139410205](https://github.com/axiomtutor/SyLoPy/actions/runs/38139410205) has the known baseline result: 906 passed, 1 failed at pytest_tests/test_set_axioms.py::test_zfc_remaining_axioms_fixture_all_pass; coverage passed, enforced fixtures 79/79, informational fixtures 51/52. The failure is the deliberately deferred WLOG / Mutatis mutandis work. Test/fixture counts are snapshots, not invariants.

### Active pull requests and test evidence

- [PR #31 — Enable ordinary facts from typed declarations](https://github.com/axiomtutor/SyLoPy/pull/31). Adds Int(n) / Nat(n) as ordinary declaration-line facts, without a refinement type checker. Tests cover singular/plural forms, later citation, local citation and scope closure, comma-grouped and tuple-shaped forms, and theorem promotion preserving a typed declaration as a required premise. Latest CI [#38147129717](https://github.com/axiomtutor/SyLoPy/actions/runs/38147129717): 914 passed, one known deferred fixture failure; coverage passed; enforced 79/79, informational 51/52.
- [PR #34 — Add relation-property scope guard regressions](https://github.com/axiomtutor/SyLoPy/pull/34). Test-only: root relation declarations work in subproofs and two levels down; sibling reuse of R does not transfer properties in either sibling order. CI [#38147356859](https://github.com/axiomtutor/SyLoPy/actions/runs/38147356859): 910 passed, one known deferred fixture failure; coverage passed; enforced 79/79, informational 51/52.
- [PR #28 — Refresh regression counts](https://github.com/axiomtutor/SyLoPy/pull/28). Docs-only URL repair; the full commit link to 5df7d5d7d04f81b5a8aa7febcb73786a4274000f now resolves. CI [#38145947220](https://github.com/axiomtutor/SyLoPy/actions/runs/38145947220): 906 passed, one known deferred fixture failure; coverage passed; enforced 79/79, informational 51/52.
- [PR #35 — Clarify typed quantifier sugar as a separate proposal](https://github.com/axiomtutor/SyLoPy/pull/35). Documentation-only, no runtime change or implementation authorization.
- [PR #29 — Clarify surface sugar versus specialized inference rules](https://github.com/axiomtutor/SyLoPy/pull/29) is documentation-only. CI [#38113906840](https://github.com/axiomtutor/SyLoPy/actions/runs/38113906840): the same known failure, coverage passed, enforced 79/79, informational 51/52.
- [PR #30 — Test the combined proof-text checking API](https://github.com/axiomtutor/SyLoPy/pull/30) adds two contract tests for custom environments and structured validation errors. CI [#38114301838](https://github.com/axiomtutor/SyLoPy/actions/runs/38114301838): 908 passed plus the same known failure; coverage passed, enforced 79/79, informational 51/52.
- [PR #33](https://github.com/axiomtutor/SyLoPy/pull/33) is closed. Its local relation-property implementation and nested-scope tests are a review reference only; the nested tests were not run by CI because the PR was closed.

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

### D. Typed declarations — owner-authorized and implemented on PR #31

The owner authorized option A on 2026-10-11: a typed declaration states the corresponding ordinary formula on its declaration line. “Let X be an integer” asserts Int(X); “Let n be a natural number” asserts Nat(n). This uses Type.as_declaration_recipe(); the type predicates remain ordinary, citable formulas. The red-team case 5 is now correctly refused for conditions 3 and 4 because Int(X) is a hypothesis in force. CI evidence is recorded in §3.

This does not implement refinement type checking or typed quantifier sugar. PR #35 records the latter as a proposal only. The authorized declaration behavior must not be confused with a proposed type checker deriving typing judgments from function signatures.

## 6. Recommended order of work

1. **Claude:** implement the confirmed relation-scope semantics in the kernel. Relation properties must be read from the declaration visible at the line being validated; do not flatten declarations from different sibling scopes into one name-keyed table. PR #33 is a closed reference only.
2. **ChatGPT/Copilot:** add test-only probes and review tests, but do not modify source/ProofLogic.py or source/ProofJustification.py under the current ownership rule.
3. **Owner/Claude:** review open PRs #31, #34, #28, and #35, and PRs #29–#30 as convenient. Merge only after review; this handoff does not authorize auto-merging.
4. Keep WLOG, Mutatis mutandis, named ZFC axiom citations, Set property, Infinity, the full refinement type checker, and relativized quantifier sugar deferred absent separate owner authorization.

## 7. Requests for the next handoff

**Owner decisions already recorded:** typed declaration option A is authorized; declarations in subproofs are local to the subproof and descendants. No further design decision is needed before the relation-scope kernel fix.

**Claude:** please review PR #31's typed-declaration changes and own the kernel fix described in todos.txt item 7. The owner has confirmed the scope contract. PR #34 has passing guard tests for existing root-declaration behavior and sibling non-leakage; PR #33's local-declaration/nested tests are only an unverified reference. Please report results and identify any test needing adjustment.

**ChatGPT:** continue bounded test-only or documentation work that does not overlap kernel implementation. PR #34, the additional PR #31 tests, link repair in PR #28, and the quantifier-sugar design sketch in PR #35 are committed. The nested relation-scope regressions on closed PR #33 remain unverified; once Claude's implementation branch is available, add or adapt tests only if they fit that implementation without duplication.

**Copilot:** the handoff previously requested status for the theorem-promotion audit in §5.A. If no response arrives, Claude should take that audit after prioritizing the relation-scope fix.

**All agents:** preserve the distinction between settled semantics, design proposals, and observed CI. The one known fixture failure remains the deferred WLOG / Mutatis mutandis test; do not hide it with an xfail or conflate it with new failures.
