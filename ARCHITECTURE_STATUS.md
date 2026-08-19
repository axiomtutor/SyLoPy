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

`ProofParser` is now the public parser facade. The existing parsing machinery
is retained in `ProofParserLegacy` for compatibility while language-policy
components are extracted from it. In particular, justification names are
resolved by explicit aliases in `ProofJustification`, and formula parsing uses
conventional precedence (`not`, `and`, `or`, implication, biconditional).

Theory modules extend `TheoryEnvironment` with syntax and core resources.
Discrete mathematics now exposes its relation declaration interpretation as a
`RelationDeclarationRecipe`, rather than requiring the generic elaborator to
know the relation's semantic representation.

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
rules to a theory module rather than modifying the generic parser.

## Remaining consolidation work

The legacy parser still contains historical theory-specific surface parsing.
That code is retained deliberately while the corresponding theory recipes are
introduced and tested. The next refactor should move relation declaration
recognition itself behind the theory environment, then apply the same pattern
to future order-theory and algebraic syntax.

The `Use discrete math.` directive is currently validated and accepted, but
the default environment remains backward-compatible and loads the available
theory modules. A future language-version change can make directives select
theory environments strictly after the existing proof corpus has been updated.

The repository now has `.gitignore` hygiene and GitHub Actions that run both
pytest and the proof-fixture validator. Test counts are intentionally not
hard-coded into documentation.
