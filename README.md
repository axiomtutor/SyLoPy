


# SyLoPy

SyLoPy is a source-located natural-deduction proof checker. Proof files may use a small natural surface language; the parser converts that language to a surface proof AST, an elaboration stage removes syntactic sugar, and `ProofLogic` validates only the resulting core proof representation.

## Proof-processing pipeline

```text
natural proof text
        ↓
SurfaceProof AST with SourceSpan metadata
        ↓
elaboration / desugaring
        ↓
ElaboratedEntries (core proof + origin map)
        ↓
ProofLogic.ProofValidator
```

The elaborator does not rewrite the user's file and then reparse it. Generated core steps are AST objects. Every generated label records the surface line that produced it, so errors in synthetic steps are translated back to the user's proof.

## Implemented surface sugar

The set-theory environment currently supports natural membership notation and subset proofs:

```text
1. Let X be any set. (Declaration)
2. The empty set is a subset of X. (Subset proof below)
 2.1. Let a in the empty set. (Assumption for subset proof)
 2.2. a is not in the empty set. (Set property)
 2.3. a is in X. (Explosion from 2.1 and 2.2)
```

Line 2 elaborates to:

1. Universal generalization over an arbitrary object `a`.
2. Conditional introduction from `a ∈ ∅` to `a ∈ X`.
3. The definitionally expanded core formula `forall x, In(x, EmptySet) -> In(x, X)`.

Both explicit `begin subproof` / `end subproof` blocks and implicit dotted-label blocks are accepted for this form.

`SetTheory.py` also supports `X has no elements` (-> `forall y, not(y in X)`) and a `SetEqualityRule` for concluding `X = Y` from `X` and `Y` being subsets of each other in both directions.

`NumberTheory.py` extends `NatThry.py` (naturals) and `SetTheory.py` with `Int`, closure under `Plus`/`Times`/`Neg`, and partial division: `n/a` (`Quotient(n, a)`) and `a|n` (divisibility, definitional sugar for `exists m, Int(m) and n = a * m` -- not a primitive, the same way subset isn't) both parse as ordinary infix notation, including nested inside other connectives (`if n/a is an integer then a|n`). See its module docstring for the two axioms governing `Quotient` and why an old "Algebra" placeholder citation was retired in favor of naming them directly (`Quotient Defining Property`, `Quotient Uniqueness`).

### Discrete mathematics: relations

`DiscreteMath.py` provides declaration-sensitive relation properties. Compound declarations can say:

```text
1. Let X be any set,
    R be a reflexive, antisymmetric, transitive relation on X,
    a, b, c be in X,
    and R(a,b) and R(b,c). (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
3. R(a,c). (Relation Transitivity from 1, 1)
```

Supported primitive properties are reflexive, irreflexive, symmetric, antisymmetric, asymmetric, transitive, and total/connected. Standard descriptors expand automatically to their component properties: equivalence relation, partial order, strict partial order, total order, and linear order. Relation rules are generated from the declarations in the current proof, so a property declared for `R` cannot be applied to an unrelated relation `S`.

The enforced fixture corpus includes positive and negative relation-property proofs in `tests/testDiscreteMath/`.

### Theorem-to-rule promotion

`ProofLogic.promote_theorem(name, proof)` turns an already-checked `Proof` into an `InferenceRule` later proofs can cite by that name -- generalizing over whatever the theorem declared "for any X" at its top level (default: every top-level `OBJECT` declaration), and requiring the same substitution to satisfy the theorem's own premises, if it has any. `MultiproofParser.run_multi_proof_file` does this automatically: a validated, titled (`# N: Title`) proof is promoted for every later case in the same file to cite by that title, with no further wiring needed. See `tests/testSetTheory/empty_set_subset_and_uniqueness.txt` for a full example (the empty-set-subset theorem, cited by name to prove the empty set is unique).

## Main APIs

```python
from SyLoPy.source import ProofParser as pp
from SyLoPy.source import ProofLogic as pl

text = open("tests/setTheoryProofs/empty_set_subset.txt").read()

surface = pp.parse_surface_proof(text)
entries, raw_lines = pp.parse_proof_text(text)

ok, error = pl.Proof(
    entries,
).check_detailed()

print(pp.format_core_proof(entries))
```

`parse_proof_text` retains its historical `(entries, raw_lines)` return shape. `entries` is now an `ElaboratedEntries` list subclass containing origin and theory metadata.

For a single source-aware operation:

```python
ok, error = pp.check_proof_text(text)
```

## Project structure

- `source/ProofElaboration.py` — surface AST, source spans, theory environments (including `term_parsers`/`nested_formula_parsers`, the extension points that let a theory's syntax be recognized in nested positions, not just at the top of a line), elaborated-entry metadata.
- `source/ProofParser.py` — formula/term parsing, surface proof parsing, generic elaboration, core rendering.
- `source/SetTheory.py` — set notation, empty-set property, set equality, and the subset-proof elaborator.
- `source/NumberTheory.py` — integers, divisibility, and quotient notation, built on `NatThry.py` and `SetTheory.py`.
- `source/ProofLogic.py` — trusted core rules, proof validator, and theorem-to-rule promotion (`promote_theorem`/`TheoremRule`).
- `source/MultiproofParser.py` — files containing multiple `# N` or `# N: title` proofs, with automatic theorem promotion across cases in the same file.
- `tests/setTheoryProofs/empty_set_subset.txt` — working natural subset-proof fixture.
- `tests/testSetTheory/empty_set_subset_and_uniqueness.txt` — the above plus a second proof citing it by name.
- `tests/testNumberTheory/` — divisibility and Int-closure fixtures.

See `ELABORATION_ARCHITECTURE.md` for the extension contract and the exact generated core proof.

## Tests

```bash
python -m pip install -r requirements-test.txt
./run_tests.sh
```

Verified result:

```text
290 passed
```

The test suite covers the original term, formula, rule, parser, validator, declaration, natural-number, and multiproof behavior, plus the surface AST, implicit subproof parsing, subset elaboration, core rendering, source-mapped synthetic errors, integer/divisibility reasoning, set equality, and theorem-to-rule promotion.





### Test runner contract

`run_tests.sh` has two independent validation stages:

1. the Python/pytest suite, run once under coverage;
2. `source/validate_all_proofs.py`, which scans every enforced proof fixture,
   including `tests/testDiscreteMath/`, and compares each proof's actual result
   with its declared expected result.

The stages do not short-circuit one another. If pytest fails, the proof corpus
is still checked. A malformed expected-valid proof therefore causes the overall
runner to fail even when the Python unit tests themselves pass.
