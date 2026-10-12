# Architecture status

SyLoPy is organized as a small proof-language compiler with a proof-theoretic
kernel:

```text
proof text
    -> SurfaceProof
    -> elaboration
    -> ElaboratedEntries
    -> ProofLogic.Proof
```

`ProofParser` is the public parser facade. Parsing produces the surface
representation before elaboration converts it into the strict entry language
checked by `ProofLogic`. Source-origin metadata is retained through
elaboration so errors in generated core steps can still be reported against
the user's source.

Theory modules extend `TheoryEnvironment` with syntax and core resources.
Discrete mathematics exposes its relation declaration interpretation as a
`RelationDeclarationRecipe`, rather than requiring the generic elaborator to
construct the relation's semantic representation itself.

## Current theory boundary

A theory should provide, as appropriate:

- surface formula parsers;
- nested formula parsers;
- phrase parsers and phrase-span finders, for phrases that contain connective
  words ("x is a or b"), so the connective grammar cannot cut them apart;
- term parsers;
- line elaborators;
- declaration recipes;
- inference rules;
- axioms;
- built-in declarations.

Adding a structure should therefore normally mean adding a recipe and core
rules to a theory module rather than modifying generic elaboration logic.

## Surface sugar versus inference implementation

"Prefer sugar" is a design principle, not a claim that every mathematical
inference currently expands into primitive logical steps. Keep two questions
separate:

1. **Surface lowering:** what formula, term, declaration, or core proof entries
   does the user's notation become?
2. **Inference checking:** does the validator use ordinary logical rules and
   formulas, or a theory-specific `InferenceRule` / axiom implementation?

Examples from the current code:

| Feature | Surface/elaboration behavior | Inference implementation |
| --- | --- | --- |
| Divisibility, `a\|n` | Expands at parse time to `exists m, (Int(m) and n = a * m)`. | Ordinary existential introduction/elimination are used; there is no separate divisibility rule. |
| `Subset proof below` | Elaborates into universal generalization and conditional introduction, concluding `forall x, (In(x,S) -> In(x,T))`. | The generated core proof is validated using existing proof rules. |
| Relation declarations | `RelationDeclarationRecipe` creates predicate declarations carrying the relation's carrier and property metadata. | `DiscreteMathCore.py` provides specialized rules such as relation symmetry, transitivity, and reflexivity; they check the declared property and, where needed, the carrier. |
| Set equality | The conclusion is the ordinary formula `X = Y`. | `SetEqualityRule` directly checks for subset formulas in opposite directions; the current implementation does not expand this citation into a subproof of more primitive steps. |
| Uniqueness | The conclusion is ordinary first-order logic: `exists W, (B(W) and forall V, (B(V) -> V = W))`. | `UniquenessRule` is a specialized, context-sensitive rule because soundness depends on whether the candidate constant is genuinely arbitrary. It is not a new `ExistsUnique` connective. |
| Quotient notation, `n/a` | Parses as the term `Quotient(n, a)`. | Its mathematical behavior is governed by the theory's quotient defining-property and uniqueness axioms; the term itself is not expanded away into a formula. |

Thus, a feature can use surface sugar and still rely on a specialized theory
rule or axiom. Conversely, a specialized rule can conclude an ordinary core
formula without creating a new formula-AST connective.

When adding mathematical syntax or inference, document these points separately:
(a) its surface-to-core lowering, (b) the checking mechanism and side conditions,
and (c) whether its mathematical force is definitional, derived by existing
rules, or axiomatic. Prefer formula/proof-entry expansion when it remains clear
and efficient, but do not describe a specialized rule as "desugared to logic"
unless the implementation actually constructs and validates that derivation.

## Rules that look at the proof around them

A rule normally sees only the lines it cites. A rule that is sound only
relative to the rest of the proof can implement
`InferenceRule.applies_in_context(candidates, phi, context)` instead. The
validator passes a `RuleContext`: `hypotheses` (what the proof takes for
granted: premises, `(Axiom)` lines, declarations that state a formula,
witness lines such as `Existence from L` and the direct Pairing witness, and
the open assumptions) and `arbitrary_constants` (constants introduced by a
plain declaration or as the flag of a Fresh Variable subproof, minus any name
that a declaration's metadata refers to, such as a relation's carrier). Rules
that do not opt in are unchanged. A rule that refuses can also implement
`explain_in_context`, and the validator appends its reason to the message.
`Uniqueness`, `UniversalGeneralization` and `ExistentialElimination` use the
hypotheses to check that the constant they treat as arbitrary occurs in none of
them -- including a premise stated inside the subproof they consume, which no
earlier check could see -- and that no declaration's structure names it; the
relation rules read `declaration(name)`. `Uniqueness` never applies without a
context; the other two keep their context-free checks when asked directly.
Theorem promotion takes its premises from the same record the validator keeps
(`ProofValidator.own_givens`).

The invariant for such a rule: whatever the proof relies on that says
something about a constant must reach the context, as a recorded formula or as
declaration metadata. A fact a rule reads from somewhere else (a new kind of
declaration with hidden structure, a recipe that registers a rule about a
declared constant) must be made visible the same way, or the rule is unsound
for that constant. The two holes found so far -- the direct witness line and
the relation carrier -- are in `tests/testProofs/uniqueness_red_team.txt`.

## Remaining consolidation work

The main remaining architectural work is to identify and remove any duplicated
parser/elaboration paths that are still reachable, then move additional
theory-specific syntax behind `TheoryEnvironment` and its declaration recipes.
The same pattern should be used for future order-theory and algebraic syntax.

`ProofContext` is the lexical scope for declarations, assumptions, labels and
arbitrary bindings during elaboration; the elaborator no longer keeps a
parallel declaration scope.

The kernel's `LabelScope` and `DeclarationScope` in `ProofLogic.py` deliberately
remain separate validation-time scope structures. This preserves the compiler
boundary between elaboration and kernel validation: `ProofContext` manages
source-level bindings, while the kernel scopes operate only on elaborated
entries. Their overlapping lexical semantics are maintained by regression
tests.

The `Use discrete math.` directive is currently validated and accepted, while
the default environment remains backward-compatible and loads the available
theory modules. A future language-version change can make directives select
theory environments strictly after the existing proof corpus has been
updated.

The repository has `.gitignore` hygiene and GitHub Actions that run the same
complete test command used locally. Test counts are intentionally not
hard-coded into architecture documentation.
