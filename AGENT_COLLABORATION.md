# Guidance for Coding Agents

This file contains stable collaboration rules. The current task handoff is kept on the [coordination branch](https://github.com/axiomtutor/SyLoPy/blob/chatgpt-agent-guidance/AGENT_COLLABORATION.md); the [TODO](todos.txt) is the design ledger, and PRs/issues hold implementation details. The owner has final authority over priorities and semantics.

## Load only relevant context

Do not read the full TODO and every architecture document for each task. Start here, inspect current master plus relevant open PRs/branches, and check the project-status/known-issues section at the top of `todos.txt`. Then read only the TODO subsection and reference docs needed for the task.

- Read `README.md` for user-facing behavior or API/documentation work.
- Read `ARCHITECTURE_STATUS.md` for architecture, parser/elaboration boundaries, or validation-context work.
- Read `ELABORATION_ARCHITECTURE.md` or `TYPE_SYSTEM_DESIGN.md` only when working in those areas.
- Prefer targeted search or line-range reads over loading long design-history sections. Recheck PR state and CI; handoffs and status snapshots can become stale.

## Preserve the architecture

The intended pipeline is surface proof text → parsing/surface AST → elaboration → core proof entries → `ProofLogic` validation. `ProofContext` owns elaboration-time lexical scope; kernel `LabelScope` and `DeclarationScope` remain separate validation-time trust boundaries.

Keep theory-specific syntax and interpretation in theory environments and declaration recipes. Prefer surface sugar over new AST/kernel primitives unless a genuinely new logical primitive is required. Do not add generic parser/elaboration special cases to rescue one example.

## Coordinate and respect ownership

- Check for active work in the same subsystem before editing. Use one small, isolated branch per task.
- Never rewrite, rebase, force-push, or clean up another agent's branch.
- Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. Coordinate before changing either file.
- If semantics are ambiguous or conflict with an owner decision, stop and raise the question; do not decide implicitly in code.

## Current constraints

- Equality-case WLOG replay is implemented (PR #63); it is not a new feature to implement from scratch. The outstanding citation-remapping failure is tracked in [issue #75](https://github.com/axiomtutor/SyLoPy/issues/75). Do not mask the failure, weaken negative tests, or expand WLOG to arbitrary properties.
- The general `Set property` rule is implemented. Do not follow obsolete notes that describe it as wholly deferred.
- The named Pairing, Union, Power Set, and Infinity axiom-citation rules are implemented, including the Union/Power Set instance forms (PR #81). The remaining owner decision is whether to retire generic `(Axiom)` citations; see `todos.txt` §5.
- `Mutatis mutandis` remains deferred pending explicit owner approval.
- The scoped witness form `Let Y be such a set. (Existence from L)` names a witness from an existing existential; the axiom citation itself does not introduce one. Do not extend the older direct Pairing-witness form to other axioms.

For the full rationale and current open work, consult only the relevant entries in `todos.txt` and the linked issue/PR; avoid copying that history into this guide.

## Parser and test discipline

- New surface-syntax cases belong in `parse_oracle/`, with `expect` written as the intended plain-logic reading. Investigate disagreements rather than automatically weakening the oracle.
- Run `./run_tests.sh` for full verification. Preserve the enforced fixture corpus and report known failures separately from regressions.
- Negative proof tests must fail for the intended rule/guard, not due to parsing, undeclared symbols, or unrelated scope errors.
- Report the exact tested commit/CI run, Python test totals, coverage, enforced fixtures, informational fixtures, and any remaining failures.

The aim is composable, reviewable changes that preserve the project's accumulated decisions, not maximum independent activity.
