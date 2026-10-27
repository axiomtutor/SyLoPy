# Collaboration Guide

This file contains stable collaboration rules. The [TODO](todos.txt) is the current-state/design ledger; [JOBS_FOR_CHATGPT.md on the coordination branch](https://github.com/axiomtutor/SyLoPy/blob/chatgpt-agent-guidance/JOBS_FOR_CHATGPT.md) records delegated jobs; PRs and issues hold implementation details and discussion. The owner has final authority over priorities and semantics.

## Load only relevant context

Do not read the full TODO and every architecture document for each task. Start here, inspect current master plus relevant open PRs/branches, and check the project-status/known-issues section at the top of `todos.txt`. Then read only the TODO subsection and reference docs needed for the task.

- Read `README.md` for user-facing behavior or API/documentation work.
- Read `ARCHITECTURE_STATUS.md` for architecture, parser/elaboration boundaries, or validation-context work.
- Read `ELABORATION_ARCHITECTURE.md` or `TYPE_SYSTEM_DESIGN.md` only when working in those areas.
- Prefer targeted search or line-range reads over loading long design-history sections. Recheck PR state and CI; handoffs and status snapshots can become stale.

The intended pipeline is surface proof text → parsing/surface AST → elaboration → core proof entries → `ProofLogic` validation. `ProofContext` owns elaboration-time lexical scope; kernel `LabelScope` and `DeclarationScope` remain separate validation-time trust boundaries.

Keep theory-specific syntax and interpretation in theory environments and declaration recipes. Prefer surface sugar over new AST/kernel primitives unless a genuinely new logical primitive is required. Do not add generic parser/elaboration special cases to rescue one example.

## Coordinate and respect ownership

- Check for active work in the same subsystem before editing. Use one small, isolated branch per task.
- Never rewrite, rebase, force-push, or clean up another agent's branch.
- Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. Coordinate before changing either file.
- If semantics are ambiguous or conflict with an owner decision, stop and raise the question; do not decide implicitly in code.

## Keep work status in one place

- `todos.txt` is the source of truth for feature status, correctness invariants, design decisions, and owner-approval requirements. Do not duplicate that feature inventory here; read the relevant subsection before touching WLOG, `Mutatis mutandis`, axiom citations, witness handling, or theorem promotion.
- `JOBS_FOR_CHATGPT.md` is the delegated-work tracker. Completed task specifications are preserved in `docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md` for historical context only; an archived specification is not current authorization to work.
- Do not start an item marked as requiring owner approval in `todos.txt` without explicit approval.

## Parser and test discipline

- New surface-syntax cases belong in `parse_oracle/`, with `expect` written as the intended plain-logic reading. Investigate disagreements rather than automatically weakening the oracle.
- Run `./run_tests.sh` for full verification. Preserve the enforced fixture corpus and report known failures separately from regressions.
- Negative proof tests must fail for the intended rule/guard, not due to parsing, undeclared symbols, or unrelated scope errors.
- Report the exact tested commit/CI run, Python test totals, coverage, enforced fixtures, informational fixtures, and any remaining failures.

The aim is composable, reviewable changes that preserve the project's accumulated decisions, not maximum independent activity.
