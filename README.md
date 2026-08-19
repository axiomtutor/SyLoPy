# SyLoPy

SyLoPy is a source-located natural-deduction proof checker. Proof files use a
natural surface language; the parser produces a surface proof AST, elaboration
removes syntactic sugar, and `ProofLogic` validates the resulting core proof
representation.

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

The elaborator does not rewrite the user's file and then reparse it. Generated
core steps are AST objects, and source origins are retained for diagnostics.

## Implemented surface language

The set-theory environment supports natural membership notation and subset
proofs:

```text
1. Let X be any set. (Declaration)
2. The empty set is a subset of X. (Subset proof below)
 2.1. Let a in the empty set. (Assumption for subset proof)
 2.2. a is not in the empty set. (Set property)
 2.3. a is in X. (Explosion from 2.1 and 2.2)
```

`NumberTheory.py` extends the natural-number and set-theory layers with `Int`,
closure under `Plus`/`Times`/`Neg`, quotient notation, and divisibility.

### Discrete mathematics: relations

`DiscreteMath.py` provides declaration-sensitive relation properties. For
example:

```text
1. Let X be any set,
    R be a reflexive, antisymmetric, transitive relation on X,
    a, b, c be in X,
    and R(a,b) and R(b,c). (Declaration)
2. R(a,a). (Relation Reflexivity from 1)
3. R(a,c). (Relation Transitivity from 1, 1)
```

Supported primitive properties are reflexive, irreflexive, symmetric,
antisymmetric, asymmetric, transitive, and total/connected. Standard
descriptors expand to equivalence relations, partial orders, strict partial
orders, total orders, and linear orders.

Relation semantics are declaration-sensitive: rules are generated from the
relations actually declared in the proof.

### Theorem-to-rule promotion

`ProofLogic.promote_theorem(name, proof)` turns an already-checked proof into
an inference rule later proofs can cite by name. `MultiproofParser` can promote
validated titled proofs automatically for later cases in the same file.

## Parser architecture

`ProofParser.py` is the public parser facade. The historical implementation is
retained in `ProofParserLegacy.py` while language-policy components are being
moved behind explicit extension boundaries.

`ProofJustification.py` resolves rule names through explicit aliases rather
than substring matching. This makes phrases such as `Conditional Equivalence`
unambiguous instead of allowing a generic `equiv` match to shadow the intended
rule.

Formula parsing uses conventional logical precedence:

```text
not > and > or > implication > biconditional
```

Parentheses remain available for explicit grouping.

Theory modules extend `TheoryEnvironment` with syntax, declaration recipes,
rules, axioms, and built-in declarations. Discrete mathematics now exposes a
`RelationDeclarationRecipe` through that interface.

See `ELABORATION_ARCHITECTURE.md` and `ARCHITECTURE_STATUS.md` for the extension
contract and current consolidation plan.

## Main APIs

```python
from SyLoPy.source import ProofParser as pp
from SyLoPy.source import ProofLogic as pl

text = open("tests/setTheoryProofs/empty_set_subset.txt").read()
entries, raw_lines = pp.parse_proof_text(text)
ok, error = pl.Proof(entries).check_detailed()
print(pp.format_core_proof(entries))
```

`parse_proof_text` retains its historical `(entries, raw_lines)` return shape.
`entries` is an `ElaboratedEntries` list subclass containing origin and theory
metadata.

For a single source-aware operation:

```python
ok, error = pp.check_proof_text(text)
```

## Project structure

- `source/ProofElaboration.py` — surface AST, source spans, theory environments,
  and elaborated-entry metadata.
- `source/ProofParser.py` — public parser facade and language grammar policy.
- `source/ProofParserLegacy.py` — retained parser/elaborator implementation
  during the architectural migration.
- `source/ProofJustification.py` — deterministic justification-name resolver.
- `source/SetTheory.py` — set notation and subset/set-equality reasoning.
- `source/NatThry.py` — natural-number vocabulary and induction.
- `source/NumberTheory.py` — integer, divisibility, and quotient reasoning.
- `source/DiscreteMath.py` — relation vocabulary, declaration recipe, and
  declaration-sensitive relation rules.
- `source/ProofLogic.py` — core inference rules, validator, and theorem
  promotion.
- `source/MultiproofParser.py` — multi-proof files and theorem promotion.
- `source/validate_all_proofs.py` — proof-fixture validator.
- `tests/testDiscreteMath/` — positive and negative relation-property fixtures.

## Tests

```bash
python -m pip install -r requirements-test.txt
./run_tests.sh
```

`run_tests.sh` has two independent validation stages:

1. the Python/pytest suite, run once under coverage;
2. `source/validate_all_proofs.py`, which scans the enforced proof fixture
   corpus, including `tests/testDiscreteMath/`.

The repository deliberately does not hard-code a test count in documentation;
current results are determined by the test runner and CI.

GitHub Actions runs the same `run_tests.sh` entry point on pushes and pull
requests.
