# Guidance for Coding Agents

This file is for Claude Code, Microsoft Copilot, and other coding agents working
on SyLoPy alongside the project owner and other agents. It is coordination
guidance, not a substitute for the README or the design decisions in
`todos.txt`.

## Before changing code

Read `README.md`, `todos.txt`, and `ARCHITECTURE_STATUS.md` first. Then
inspect the current `master` and any relevant open branches or pull requests.
Do not assume that an earlier description of the repository is still current:
another agent may have changed it since the last conversation.

Treat `todos.txt` as the living design record. Distinguish carefully between:

- decisions that are marked done;
- proposals that are written down but explicitly not approved for implementation;
- genuinely open design questions.

In particular, a TODO item saying not to start implementation without an
explicit go-ahead is a real coordination boundary. Do not turn a documented
design proposal into code merely because the implementation looks
straightforward.

## Preserve the architecture

The intended pipeline is:

```
surface proof text
    -> parsing / surface AST
    -> elaboration
    -> core proof entries
    -> ProofLogic validation
```

Keep theory-specific syntax and interpretation in the appropriate theory
environment and declaration recipes. Avoid adding special cases to generic
elaboration merely because they make one example easier.

Most applied mathematical notation is intended to be sugar over existing core
logic. Do not add an AST or kernel primitive for a convenience construct unless
the design explicitly calls for a genuinely new logical primitive.

`ProofContext` is the authoritative lexical environment during elaboration.
The kernel deliberately retains independent validation-time `LabelScope` and
`DeclarationScope` structures. Do not reunify them merely to remove similar
code; that separation is an intentional architecture decision.

## Coordinate before modifying active work

The repository is developed concurrently by multiple agents. Before taking on
a nontrivial implementation:

1. Check whether another branch or PR is already changing the same subsystem.
2. Prefer a small, isolated branch and commit when the work is independent.
3. Do not rewrite, rebase, force-push, or clean up another agent's branch.
4. Do not silently absorb another agent's design into your implementation.
   State the point of departure in the PR or commit description.
5. If the design is ambiguous, record the question in the design discussion or
   TODO instead of choosing a hidden interpretation that another agent may
   implement differently.

A useful rule is: **avoid sharing files, not just ideas**. If another agent is
actively changing `ProofParser.py`, `ProofLogic.py`, or a theory module,
prefer documentation, tests, oracle cases, or another independent piece of
work until the boundary is clear.

## Parser oracle

`parse_oracle/` is intended to describe the language independently of the
implementation. New surface-syntax cases should express the intended plain
logic in `expect`, not reproduce implementation details.

When an oracle case disagrees with the parser, treat the disagreement as one
of two possibilities: the parser is wrong, or the oracle's intended reading is
wrong. Do not automatically weaken the oracle to make the test pass.

## Set-theory work

Set theory is the current experimental theory frontier. The design backlog in
`todos.txt` is deliberately ahead of the implementation. That is useful:
the proof fixtures can expose missing language features without requiring an
agent to implement every future feature immediately.

Do not implement the ZFC axiom-citation/derived-rule backlog merely because a
fixture mentions it. Follow the explicit implementation-order and
go-ahead requirements in `todos.txt`.

For WLOG specifically, the current design proposal is authoritative only up
to the points it marks as settled. The proposed replay model is:

- WLOG is an ordinary assertion whose justification cites a disjunction;
- the WLOG region begins at that assertion and extends to the end of the
  current proof block;
- each other disjunct is checked by replaying that region under the required
  transformation;
- citations inside the replay must be remapped to corresponding replay lines;
- references outside the region may need to resolve to already-visible
  transformed counterparts;
- the exact line-correspondence algorithm and the future generalization from
  equality substitutions to arbitrary properties remain design work.

Do not replace that model with a simpler unchecked "symmetry" assertion.

## Tests and regressions

Preserve the enforced proof corpus as the minimum correctness gate. Informational
fixtures are valuable examples but are allowed to contain intentionally
unfinished theory work.

When a change affects a feature with an existing oracle or focused regression
suite, extend that coverage rather than relying only on a broad end-to-end
test. When a test fails because the specification changed, update the design
documentation and the test together; do not hide the change in test-specific
logic.

Be explicit about known pre-existing failures when reporting test status. A
change that leaves the known failure unchanged is different from a change that
introduces a new failure.

## Communication with the project owner

When reporting a substantial change, include:

- what architectural or language decision the implementation assumes;
- which files/subsystems were changed;
- what was deliberately left untouched because another agent may be working
  there;
- the relevant tests and their results;
- any design question that remains unresolved.

When a proposed implementation does not fit the existing design, stop and
describe the mismatch rather than quietly changing the design through code.

The goal is not for every coding agent to make independent progress as quickly
as possible. The goal is for their changes to compose without losing the
project's accumulated design decisions.
