# Collaboration Guide

The owner has final authority over priorities and mathematical semantics. This file contains stable working rules; current status and decisions belong in `todos.txt`.

## Before starting

- Inspect current `master` and relevant open PRs, branches, and issues. Treat old handoffs and status summaries as potentially stale.
- Read the status/known-issues section of `todos.txt`, then only the relevant subsection and reference documents. Use `PROJECT_STATE.md` for the project map.
- Consult the appropriate source of detail: `README.md` for public behavior and API, `docs/PROOF_FILE_FORMAT.md` for proof syntax, and the architecture documents for parser, elaboration, or validation design.
- Follow `JOBS_FOR_CHATGPT.md` for delegated work. Do not resume completed or archived jobs unless the owner re-queues them.

## Design and correctness

- Preserve the pipeline: proof text → surface AST → elaboration → core entries → independent `ProofLogic` validation.
- Keep `ProofContext` as the elaboration-time scope. Kernel `LabelScope` and `DeclarationScope` are separate validation-time authorities; do not merge them.
- Prefer theory-local syntax, parsers, declaration recipes, and surface sugar that lowers to existing formulas or proof steps. Add generic parser special cases or kernel primitives only when the feature genuinely requires them.
- Every fact used by a proof must be visible to validation as a premise, hypothesis, ordinary formula, or explicit declaration metadata. Do not create hidden routes around kernel checks.
- Do not infer authorization from an old proposal, archived task, or example. Follow the current owner decisions in `todos.txt`; raise semantic ambiguity rather than deciding it implicitly.

## Ownership and repository changes

- Check for concurrent work in the same subsystem. Use one small, isolated branch and PR per task.
- Never rewrite, rebase, force-push, or clean up another agent's branch.
- `source/ProofLogic.py` and `source/ProofJustification.py` are Claude-owned: coordinate before editing. Owner override (2026-11-01) permits this agent to implement or fix kernel code in the current workstream when needed; retain the same coordination, review, and test discipline.
- Do not start work marked as requiring owner approval without explicit approval.

## Parser and test discipline

- Add surface-syntax cases to `parse_oracle/` with the intended plain-logic reading specified independently of the parser. Keep malformed-input rejection cases; investigate disagreements instead of weakening expectations.
- Run `./run_tests.sh` for the default Python suite and all proof-fixture suites. Use `./run_tests.sh --suite extended` for red-team/audit tests and `./run_tests.sh --suite all` for every Python suite plus proof fixtures.
- Negative proofs must be refused at the intended rule or guard, not because of a parsing, declaration, or scope error. Preserve existing fixtures and expectations; never use `xfail` to hide a regression.
- Report the exact tested commit and CI run, actual Python test results, coverage, enforced and informational fixture results, and remaining failures. Do not claim counts or coverage without checking the run for that commit.

