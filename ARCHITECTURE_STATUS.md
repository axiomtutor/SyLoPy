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

## Rules that look at the proof around them

A rule normally sees only the lines it cites. A rule that is sound only
relative to the rest of the proof can implement
`InferenceRule.applies_in_context(candidates, phi, context)` instead. The
validator passes a `RuleContext`: `hypotheses` (premises, cited axiom lines,
declarations that state a formula, and the open assumptions) and
`arbitrary_constants` (constants introduced by a plain declaration or as the
flag of a Fresh Variable subproof). Rules that do not opt in are unchanged.
`Uniqueness` is the first user; a rule asked without a context never applies.

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
