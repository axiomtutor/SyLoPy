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

`ProofParser.py` is the public parser facade. It parses into the surface AST and
then elaborates that representation into core entries. Remaining architectural
work is tracked in `ARCHITECTURE_STATUS.md`; the staged parser/elaborator
pipeline is the canonical implementation path.

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

## Test runner

`run_tests.sh` runs the Python tests and enforced proof-fixture corpus. Fixture
suites can be selected by name:

```bash
./run_tests.sh --list-suites
./run_tests.sh --suite testProofsDeclared --verbose
```

The suite list is defined by `validate_all_proofs.py`; `--list-suites` exposes
that same list for tools such as shell completion, so suite names do not need
to be duplicated in completion configuration.

For Bash completion, source `completion/run_tests.bash` once per shell:

```bash
source completion/run_tests.bash
```

To enable it automatically, add that `source` command to `~/.bashrc`.

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
- `source/ProofParser.py` — public parsing and elaboration facade.
- `source/ProofLogic.py` — core proof representation, rules, axioms, and
  validation.
- `source/MultiproofParser.py` — sequential multi-proof parsing and theorem
  promotion.
- `source/validate_all_proofs.py` — enforced and informational fixture runner.
- `completion/run_tests.bash` — Bash completion for test-runner options and
  dynamically discovered suite names.
