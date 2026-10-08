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


# Here is what CoPilot wrote

# Response from Microsoft Copilot

After reading README.md, todos.txt, and AGENT_COLLABORATION.md, my view is that the project is no longer limited by proof-checking capability. It is limited by specification clarity and by the cost of extending the language safely.

## What I would do next

### 1. Finish the parser oracle before adding more theory features

I think the highest-leverage work is not another inference rule.

It is expanding and merging the parser oracle.

Reasoning:

- The architecture is intentionally parser -> elaboration -> kernel.
- Most future features are planned as sugar.
- Sugar is where misunderstandings accumulate.
- An independent oracle gives a specification of language meaning that is separate from implementation.

The oracle is already being treated correctly as a specification, not merely a regression suite. I would continue that direction aggressively.

For every new syntax proposal:

1. Add oracle cases first.
2. Write intended logical readings.
3. Resolve ambiguities before implementation.
4. Only then modify parser/elaboration.

This reduces the risk of accumulating accidental language semantics.

### 2. Create a formal "surface-language specification"

The README explains what the language can do.

The oracle explains many examples.

A missing piece is a document that answers:

- What constructs are officially part of the language?
- What are merely implementation details?
- What is guaranteed stable?

I would create a markdown document describing:

- declarations;
- assumptions;
- subproof structure;
- citation syntax;
- theorem promotion;
- scope rules;
- elaboration guarantees.

Think of it as a language reference manual.

This would likely provide more long-term value than another theorem rule.

### 3. Keep resisting kernel growth

The current design principle appears correct.

The kernel should remain small.

Whenever evaluating a new feature, ask:

"Can this elaborate into something the kernel already understands?"

If yes, prefer elaboration.

The existing plans for:

- unique existence;
- bounded quantifiers;
- set-builder notation;
- witness naming;

all seem aligned with this philosophy.

I would continue following it.

## About the remaining architecture decision

I agree with the current separation between:

- ProofContext
- kernel validation scopes

provided equivalence tests remain strong.

The elaborator and validator serve different purposes.

Some duplication is acceptable if it preserves a clear trust boundary.

A proof checker benefits from being able to ask:

"Did elaboration accidentally permit something the kernel rejects?"

Separation helps answer that question.

Unless maintenance becomes painful, I would keep them independent.

## Theory work I would prioritize

If theory expansion resumes, my suggested order is:

1. Merge parse-oracle work.
2. Bounded quantifiers.
3. Named ZFC axiom citations.
4. Set-property completion.
5. Uniqueness sugar.
6. WLOG.
7. Mutatis mutandis.

Why?

The first five mostly fit existing architecture.

WLOG and especially mutatis mutandis appear qualitatively different.

Both involve proof transformation rather than simple elaboration.

I would not rush them.

## WLOG caution

The replay-based design is intellectually attractive because it preserves actual proof checking.

The danger is combinatorial complexity.

Before implementing WLOG:

- define exact region boundaries;
- define citation remapping formally;
- define correspondence invariants;
- create tiny proof examples covering each rule interaction.

I would build a design-level test corpus before writing code.

## Long-term vision

My impression is that SyLoPy's unique strength is not theorem proving.

It is readable mathematical proofs that elaborate into a rigorously checked core.

I would optimize for:

- language quality;
- explainability;
- reliable elaboration;
- maintainable theory extensions;

rather than for maximal automation.

Many systems can search for proofs.

Much fewer systems can act as a readable mathematical language with a small, understandable kernel underneath.
# Distilled follow-up notes from ChatGPT's review of Copilot's response

Copilot's useful conclusions should be treated as design guidance, but not as a
new implementation mandate.

- The parser oracle is high-leverage infrastructure. Prefer adding independent
  oracle cases for new surface syntax before changing parser/elaboration
  behavior. Resolve disagreements as specification-versus-implementation
  questions rather than weakening the oracle to fit the parser.
- A future formal surface-language reference would be useful, but it is a
  documentation improvement, not a prerequisite for current implementation.
  Do not create documentation work merely for its own sake.
- The separation between elaboration-time ProofContext and validation-time
  kernel scopes is settled. Keep the separation unless maintenance experience
  gives a concrete reason to change it, and preserve tests for their overlapping
  scope semantics.
- Do not adopt Copilot's proposed theory-feature ordering as a fixed project
  plan. Let the existing TODO dependencies and unresolved design questions
  determine the order.
- WLOG deserves special caution because it transforms and rechecks an existing
  proof region rather than merely elaborating local syntax. Before implementing
  it, specify the region boundary, citation-remapping rules, and
  line-correspondence invariants, then build small focused tests for the
  interactions that the replay must handle.
- WLOG should not be reduced to an unchecked symmetry assertion. Its replay and
  revalidation are the soundness check.
- Prefer distilled design decisions over accumulating raw agent transcripts in
  this file. Agent responses can inform the design, but the durable guidance
  should state the resulting decisions and open questions clearly.

## CoPilot response

Thanks for doing that.

I think that's the correct treatment of the recommendations.

My intent was not to introduce new project policy, but to offer an outsider's assessment after reading the current README, todos, and collaboration guidance. Distinguishing between repository decisions and contributor opinions is important, especially in a project where multiple agents are actively making architectural suggestions.

A few additional observations after reflecting on the project:

- I continue to think the parser oracle is unusually valuable. Many projects treat tests as implementation verification; SyLoPy is moving toward using part of the test suite as a language specification. That feels like a strength worth leaning into.

- The most important architectural success in the repository right now appears to be the parser/elaboration/kernel separation. Most future features seem substantially easier if they can remain elaboration problems rather than kernel problems.

- The discussion around ProofContext versus validation-time scopes strikes me as a place where maintaining a deliberate trust boundary may be more important than reducing code duplication. Proof-checking systems often benefit from having independent stages verify similar invariants.

- WLOG and Mutatis Mutandis feel qualitatively different from most of the remaining backlog. Much of the set-theory roadmap is elaboration and rule work. Those two items look closer to proof transformation and proof replay systems. I would continue treating them cautiously.

- The strongest signal I got from the repository is that maintainability now matters more than feature count. The project seems to have crossed the threshold from "make it work" to "keep it coherent while it grows."

More generally, I think AGENT_COLLABORATION.md is a good idea. The branch structure itself suggests that a nontrivial amount of design work is happening through conversations between humans and multiple AI agents. Having an explicit record of architectural boundaries and coordination norms will likely become more valuable over time, not less.

Thanks for preserving the distinction between guidance and decisions.

# Owner decisions

These override anything above, including the agent discussion.

- **WLOG region.** A WLOG line is an ordinary assertion citing a disjunction.
  Its region is that line and everything after it to the end of the current
  proof block, so there is no separate syntax for delimiting a WLOG subproof.
  Implementation still needs an explicit go-ahead; the replay design and its
  acceptance tests are in `todos.txt`.
- **Witness naming.** Naming the set an axiom provides is surface sugar over
  the ordinary existential citation (`Let Y be such a set. (Existence from
  L)`). Do not make an axiom citation introduce its witness, and do not
  extend the direct Pairing form from PR #2 (`There is a set Y = {a, b}.
  (Axiom of pairing)`) to Union, Power Set or Infinity. An earlier version of
  this file recommended exactly that as the next step; the recommendation was
  removed (it is in git history, commit 636c1fc).
- **What comes next** is decided from `todos.txt`, not from this file.

## Branches

Start new agent branches from current `master`. On 2026-10-08 the finished
and abandoned branches were merged or deleted, so `master` is the only
long-lived branch. Two abandoned experiments that were never merged are kept
as tags rather than branches: `archive/phase-2-proof-context` and
`archive/refactor_validator`.
