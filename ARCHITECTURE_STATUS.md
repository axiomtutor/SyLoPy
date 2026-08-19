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
- term parsers;
- line elaborators;
- declaration recipes;
- inference rules;
- axioms;
- built-in declarations.

Adding a structure should therefore normally mean adding a recipe and core
rules to a theory module rather than modifying generic elaboration logic.

## Remaining consolidation work

The main remaining architectural work is to identify and remove any duplicated
parser/elaboration paths that are still reachable, then move additional
theory-specific syntax behind `TheoryEnvironment` and its declaration recipes.
The same pattern should be used for future order-theory and algebraic syntax.

An explicit proof context for declarations, assumptions, labels, theorem
visibility, and nested scopes remains a planned refinement. Declaration order
and scope rules should become explicit context operations rather than being
reconstructed independently by different stages.

The `Use discrete math.` directive is currently validated and accepted, while
the default environment remains backward-compatible and loads the available
theory modules. A future language-version change can make directives select
theory environments strictly after the existing proof corpus has been
updated.

The repository has `.gitignore` hygiene and GitHub Actions that run the same
complete test command used locally. Test counts are intentionally not
hard-coded into architecture documentation.
