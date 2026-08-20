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

## Semantic context boundary

`ProofContext` is now the authoritative lexical environment used by the proof
validator. `ContextProofValidator` adapts the existing rule-validation logic
to one shared context, so labels and declarations are resolved from the same
scope. Recursive subproofs receive child contexts; local bindings therefore
do not leak into their parent.

`seen` remains separate from `ProofContext`: it is ordered proof history used
for temporal and freshness checks, not a namespace. This distinction avoids
turning the context into a catch-all proof-state object.

The old `ProofValidator` implementation and its `DeclarationScope`/`LabelScope`
classes remain in `ProofLogic.py` temporarily as migration scaffolding. The
package initialization layer installs `ContextProofValidator` as the
validator used by `Proof.check_detailed()`. The next consolidation step is to
move the context-backed implementation into `ProofLogic.py` itself and delete
the legacy scope machinery once the full test corpus confirms behavioral
parity.

## Remaining consolidation work

The next architectural work is therefore:

1. move the context-backed validator into the kernel module rather than
   activating it through the package initialization layer;
2. remove the obsolete `LabelScope` and `DeclarationScope` implementations;
3. make elaboration consume the same declaration/context boundary rather than
   maintaining a separate declaration environment;
4. identify and remove any duplicated parser/elaboration paths that are still
   reachable;
5. move additional theory-specific syntax behind `TheoryEnvironment` and its
   declaration recipes.

The same pattern should be used for future order-theory and algebraic syntax.

The `Use discrete math.` directive is currently validated and accepted, while
the default environment remains backward-compatible and loads the available
theory modules. A future language-version change can make directives select
theory environments strictly after the existing proof corpus has been
updated.

The repository has `.gitignore` hygiene and GitHub Actions that run the same
complete test command used locally. Test counts are intentionally not
hard-coded into architecture documentation.
