# Guidance for Coding Agents

This file contains **stable collaboration and architecture rules**, not a running task log. For current agent assignments, findings, open questions, and recent CI status, see the [live collaboration handoff](https://github.com/axiomtutor/SyLoPy/blob/chatgpt-agent-guidance/AGENT_COLLABORATION.md). Do not append agent transcripts here; record settled outcomes and links in the handoff, and keep the detailed design ledger in todos.txt.

The owner has final authority over design and task priorities.

## Before changing code

Read README.md, todos.txt, and ARCHITECTURE_STATUS.md first. Inspect current master and relevant branches or open pull requests before starting work. An earlier conversation or handoff may be stale.

Treat todos.txt as the living design record. Distinguish decisions marked done, proposals explicitly awaiting approval, and genuinely open questions. A requirement for explicit owner approval is a coordination boundary, not a suggestion.

## Preserve the architecture

The intended pipeline is:

    surface proof text
        -> parsing / surface AST
        -> elaboration
        -> core proof entries
        -> ProofLogic validation

Keep theory-specific syntax and interpretation in the appropriate theory environment and declaration recipes. Avoid adding special cases to generic elaboration just to make one example work.

Most applied mathematical notation should be sugar over existing core logic. Do not add an AST or kernel primitive for a convenience construct unless the design explicitly calls for a genuinely new logical primitive.

ProofContext is the authoritative lexical environment during elaboration. The kernel deliberately retains its own validation-time LabelScope and DeclarationScope structures. Do not reunify them just to remove similar code: their separation is an intentional trust boundary.

## Coordinate before modifying active work

The repository is developed concurrently by multiple agents. Before nontrivial implementation:

1. Check whether another branch or PR is already changing the same subsystem.
2. Prefer a small, isolated branch and commit when work is independent.
3. Do not rewrite, rebase, force-push, or clean up another agent's branch.
4. State the relevant design assumptions in the PR or commit description; do not silently absorb another agent's proposal into code.
5. If the design is ambiguous, record the question in the design discussion or TODO rather than choosing a hidden interpretation.

Avoid sharing files, not merely ideas. If another agent is working in ProofParser.py, ProofLogic.py, or a theory module, prefer independent tests, documentation, parser-oracle cases, or another subsystem until the boundary is clear.

## Parser oracle

parse_oracle/ describes the intended language independently of its implementation. New surface-syntax cases should specify the intended plain-logic reading, not reproduce implementation details.

When the oracle disagrees with the parser, investigate whether the parser is wrong or the intended reading is wrong. Do not automatically weaken the oracle to make a test pass.

## Set-theory work and owner decisions

The design backlog in todos.txt may intentionally run ahead of implementation so proof fixtures can expose missing features without forcing immediate implementation.

The following decisions override older agent proposals:

- **WLOG region:** a WLOG line is an ordinary assertion citing a disjunction. Its region is that line and everything after it to the end of the current proof block; no separate surface syntax delimits a WLOG subproof. Implementation requires explicit owner approval. The intended design is proof-region replay and ordinary revalidation, with citation remapping—not an unchecked symmetry assertion.
- **Witness naming:** “Let Y be such a set. (Existence from L)” is surface sugar over an ordinary existential citation and a scoped declaration. The axiom citation itself does not introduce its witness. Do not extend the old direct Pairing-witness syntax to Union, Power Set, or Infinity.
- **Deferred set-theory features:** do not implement WLOG, Mutatis mutandis, named ZFC axiom-citation rules, Set property, or Infinity without explicit owner approval. Follow the implementation order and open design questions in todos.txt.
- **Next task selection:** todos.txt and the owner's explicit direction take precedence over feature orderings suggested in agent discussions.

## Tests and regressions

Use ./run_tests.sh as the canonical full test command.

Preserve the enforced proof corpus as the minimum correctness gate. Informational fixtures are useful examples and may intentionally expose features that are not implemented yet.

When a change affects a feature with an existing oracle or focused regression suite, extend that coverage rather than relying only on a broad end-to-end test. If a specification change requires changing a test, update the design documentation and test together; do not hide the change in test-specific logic.

For negative proof tests, verify that the case reaches the intended inference rule and is rejected for the intended reason. A parse error, undeclared symbol, or unrelated scope error does not demonstrate that a rule's guard works.

Report known pre-existing failures explicitly. A change that leaves an established failure unchanged is different from one that introduces a regression. Report Python tests, coverage, enforced fixtures, informational fixtures, and the exact CI run separately.

## Communicating a substantial change

Include:

- the architectural or language decision the implementation assumes;
- the changed files and subsystems;
- what was deliberately left untouched because another agent may be working there;
- relevant tests and exact results;
- unresolved design questions or follow-up work.

If an implementation conflicts with the existing design, stop and describe the mismatch rather than changing the design implicitly through code.

## Branch hygiene

Start new agent branches from current master. Do not modify or delete another agent's branch. After the owner merges work, delete branches that are no longer needed, following the repository's normal workflow.

The chatgpt-agent-guidance branch is deliberately not merged: it is the live coordination channel. The old phase-2-proof-context branch (tip a11ec09) and refactor_validator branch (tip 59bd9e5) were abandoned; those approaches are unnecessary or rejected. Do not revive them without a new explicit reason.

## Guiding principle

The goal is not for every agent to make independent progress as quickly as possible. The goal is for their changes to compose without losing the project's accumulated design decisions.
