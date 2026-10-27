# Live Collaboration Handoff

This branch carries task-specific handoff state, not the stable contribution rules. Use the [collaboration guide on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md) for stable rules, [`todos.txt` on master](https://github.com/axiomtutor/SyLoPy/blob/master/todos.txt) for current status and design decisions, and [`JOBS_FOR_CHATGPT.md` on this branch](https://github.com/axiomtutor/SyLoPy/blob/chatgpt-agent-guidance/JOBS_FOR_CHATGPT.md) for delegated work. PRs and issues hold implementation-specific discussion.

## Current handoff

- **No delegated jobs are currently queued.** Do not turn the TODO's general directions or owner-approval list into new work without an explicit owner request or a new queue item.
- The completed job definitions and verified proof patterns are preserved in the [historical archive](https://github.com/axiomtutor/SyLoPy/blob/chatgpt-agent-guidance/docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md). Archived task instructions are not current authorization.
- The latest consolidation, [PR #128](https://github.com/axiomtutor/SyLoPy/pull/128), merged after [CI run #954 passed](https://github.com/axiomtutor/SyLoPy/actions/runs/40432256483). The live queue now lists the completed job IDs and no active jobs.
- Claude owns kernel implementation in `source/ProofLogic.py` and `source/ProofJustification.py`. [Issue #122](https://github.com/axiomtutor/SyLoPy/issues/122) remains an open kernel-owned finding about a same-line `Mutatis mutandis` range. Do not edit either kernel file without coordination.

## When resuming

1. Recheck current master, open PRs, and CI; don't treat this handoff as an authoritative snapshot of source code.
2. Read the relevant `todos.txt` subsection and linked issues before changing behavior or proposing a new feature.
3. Work only on an explicit job or owner-assigned task, using a separate branch and a small PR.
