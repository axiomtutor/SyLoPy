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
# Current-state recommendation: what should happen next

Current `master` is `2eb90309abd63e32fb8565be0ad5a535a6ecbc83`.
PR #3 (the 85-case parser oracle) and PR #2 (direct Pairing witness citations)
are both merged. The source therefore already supports the direct Pairing form
such as:

```text
1. Let a, b be any set. (Declaration)
2. There is a set Y = {a, b}. (Axiom of pairing)
```

The TODO and README on `master` have not yet caught up with those merges, and
the ProofContext decision is also not yet recorded on `master`. The immediate
documentation task should therefore be to refresh those documents before the
next feature branch is treated as the new baseline.

## Recommended next implementation

After the documentation catch-up, the next source feature should be to extend
the direct named-witness axiom pattern from Pairing to Union, Power Set, and
Infinity. This is preferable to jumping directly into WLOG: it is a small
extension of an implementation pattern that now exists and it completes the
four ordinary named axiom citations listed together in the TODO.

The semantic decision is:

- A named axiom citation is a zero-premise, shape-checking rule.
- A natural-language existential names the witness directly.
- The witness becomes an ordinary object declaration in the current lexical scope.
- The rule receives the witness name and checks the instantiated defining
  property, not an existential formula.
- Later reasoning can cite that defining property with `Set property`.
- Existing symbolic existential citations remain supported.

Use the same surface pattern already established by Pairing. Suggested examples:

```text
1. Let X be any set. (Declaration)
2. There is a set Y = {u: there exists v, (In(v, X) and In(u, v))}. (Axiom of union)

1. Let X be any set. (Declaration)
2. There is a set Y = {y: y subset X}. (Axiom of power set)

1. There is a set X such that
     In(EmptySet, X) and
     forall y, (In(y, X) ->
       exists S, (forall u, (In(u, S) iff (In(u, y) or u = y)) and In(S, X))).
   (Axiom of infinity)
```

The exact human-facing spelling of the three examples should be checked against
the parser oracle before implementation. The semantic core, not the typography
of the set display, is what the axiom rule should care about.

## Implementation pattern

The existing Pairing implementation should be generalized rather than copied
three more times. A usable starting point is:

```python
def _elaborate_named_axiom_witness(
    entry: SurfaceLine,
    context,
    *,
    citation: str,
    make_rule,
    error_example: str,
) -> Optional[tuple]:
    if entry.justification_text.strip().lower() != citation:
        return None

    surface = entry.formula_text.strip()
    if not re.match(r"^there\s+(?:is|exists)\b", surface, re.I):
        return None

    try:
        parsed = context.parse_core_formula(entry.formula_text)
    except (TypeError, ValueError) as exc:
        raise ElaborationError(str(exc), entry.span) from exc

    if not isinstance(parsed, fl.Exists):
        raise ElaborationError(
            f"'{citation}' witness syntax must introduce an existentially "
            f"named set, for example {error_example}",
            entry.span,
        )

    witness_name = parsed.var
    if context.lookup_declaration(witness_name) is not None:
        raise ElaborationError(
            f"{citation} witness '{witness_name}' is already declared "
            "in this proof or an enclosing scope",
            entry.span,
        )

    declaration = pl.Declaration(
        name=witness_name,
        kind=pl.DeclarationKind.OBJECT,
        type_name="set-theoretic witness",
    )
    witness_term = tl.ConstantTerm(witness_name, witness_name)
    defining_property = fl.substitute_in_formula(
        parsed.body, parsed.var, witness_term
    )

    rule = make_rule(witness_name)
    if not rule.applies([], defining_property):
        raise ElaborationError(
            f"{citation} witness syntax does not have a valid axiom instance; "
            f"expected {error_example}",
            entry.span,
        )

    context.register_declaration(declaration, entry.span)
    context.register_origin(entry.label, entry.span)
    return (entry.label, defining_property, ("rule", rule, [], [declaration]))
```

Then the theory-local elaborator can dispatch on the citation:

```python
_NAMED_AXIOM_WITNESSES = {
    "axiom of pairing": lambda name: PairingAxiomRule(witness_name=name),
    "axiom of union": lambda name: UnionAxiomRule(witness_name=name),
    "axiom of power set": lambda name: PowerSetAxiomRule(witness_name=name),
    "axiom of infinity": lambda name: InfinityAxiomRule(witness_name=name),
}

def elaborate_named_axiom_witness(entry: SurfaceLine, context) -> Optional[tuple]:
    citation = entry.justification_text.strip().lower()
    make_rule = _NAMED_AXIOM_WITNESSES.get(citation)
    if make_rule is None:
        return None
    return _elaborate_named_axiom_witness(
        entry, context, citation=citation, make_rule=make_rule,
        error_example=_WITNESS_EXAMPLES[citation],
    )
```

The three new rule classes should gain `witness_name` exactly as
`PairingAxiomRule` does and split `applies()` into the existing universal or
existential-instance checks plus a `_check_witness_form()` branch. The witness
branch should recognize the already-instantiated defining property:

```python
class UnionAxiomRule(pl.InferenceRule):
    name = "UnionAxiom"
    premise_arity = 0

    def __init__(self, witness_name=None):
        self.witness_name = witness_name

    def applies(self, candidates, phi):
        if candidates:
            return False
        if self.witness_name is not None:
            return self._check_witness_form(phi)
        return self._check_universal_form(phi)
```

The same structure applies to `PowerSetAxiomRule` and `InfinityAxiomRule`.
Do not replace their existing universal-form checking; direct witness syntax
should be an additional accepted form.

## Focused tests to add with the implementation

Use small proof-text tests rather than only testing `InferenceRule.applies()`
directly. At minimum:

```python
@pytest.mark.parametrize((
    "text", "rule_name",
), [
    (UNION_WITNESS_PROOF, "UnionAxiom"),
    (POWER_SET_WITNESS_PROOF, "PowerSetAxiom"),
    (INFINITY_WITNESS_PROOF, "InfinityAxiom"),
])
def test_named_axiom_witness_end_to_end(text, rule_name):
    entries, _ = pp.parse_proof_text(text)
    assert entries[1][2][1].name == rule_name
    ok, error = pp.check_proof_text(text)
    assert ok, error

def test_named_witness_rejects_reused_name():
    ...

def test_named_witness_respects_subproof_scope():
    ...

def test_named_witness_rejects_wrong_axiom_shape():
    ...
```

Also add oracle cases for the human-facing Union/Power-Set syntax if the
surface parser needs a new spelling. The oracle should describe the plain
formula and remain independent of the rule implementation.

## What should wait

Do not start WLOG implementation immediately after these three rules. The WLOG
design is settled at the semantic level but its citation-correspondence
invariants are still open. Before source changes there, create tiny structural
tests for:

- replaying a two-way equality disjunction;
- replaying a three-way disjunction;
- remapping a citation to an already-visible corresponding line;
- failure when that transformed counterpart is unavailable;
- transformed declarations;
- nested subproofs and scope boundaries;
- prevention of future-line and sibling-scope references.

Then implement WLOG as a proof-region replay mechanism, not as an ordinary
one-premise `InferenceRule`.

## Coordination instruction

This is a recommended next step, not a request to begin implementation
automatically. Before changing `SetTheory.py`, check for another active branch
or agent working there. If implementation begins, keep the generic witness
elaborator and each theory-specific shape check separate: the elaborator should
handle naming/scope/lowering, while each axiom rule should decide whether its
instantiated formula is actually a valid instance of that axiom.