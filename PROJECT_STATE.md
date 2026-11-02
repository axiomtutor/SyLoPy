# SyLoPy project state

## Purpose

SyLoPy is a proof-language checker for Fitch-style natural deduction. It
accepts natural-language proof syntax, elaborates it into strict core entries,
and validates those entries with a separate proof kernel.

```text
surface proof text
    -> parser / surface AST
    -> theory elaboration
    -> core proof entries
    -> ProofLogic validation
```

## Current document roles

| Need | Document |
| --- | --- |
| User-facing behavior and test commands | `README.md` |
| Proof syntax and semantics | `docs/PROOF_FILE_FORMAT.md` |
| Current feature status and decisions | `todos.txt` |
| Stable collaboration rules | `AGENT_COLLABORATION.md` |
| Delegated work that is not yet complete | `JOBS_FOR_CHATGPT.md` |
| Architecture and trust boundaries | `ARCHITECTURE_STATUS.md` |
| Elaboration design | `ELABORATION_ARCHITECTURE.md` |
| Proposed type system | `TYPE_SYSTEM_DESIGN.md` |

`todos.txt` is authoritative when another document disagrees. Detailed
historical specifications are preserved under `docs/archive/`; they are not
authorization to implement old work.

## Source map

- `source/FormulaLogic.py` - formula and term AST types
- `source/ProofParser.py` - public parser facade and top-level dispatch
- `source/ProofElaboration.py` - elaboration passes and proof context
- `source/ProofJustification.py` - source justification and rule metadata
- `source/ProofLogic.py` - kernel validation, declarations, scopes, and promotion
- `source/SetTheory.py` - set-theory environment and set declarations
- `source/NatThry.py` - natural-number environment
- `source/NumberTheory.py` - integer and divisibility environment
- `source/DiscreteMath.py` - relation and discrete-mathematics environment
- `source/validate_all_proofs.py` - fixture suite discovery and validation
- `pytest_tests/` - Python unit and integration tests
- `tests/` - enforced proof fixtures
- `source/testProofs/`, `tests/setTheoryProofs/` - informational fixtures
- `parse_oracle/` - independent parser cases

## Set-theory cardinality status

Set theory supports exact finite cardinalities through `Cardinality(A, n)`.
Cardinal values are nonnegative metatheoretic integers, not object-language
terms. The implementation provides finite-set closure and cardinal arithmetic
for subsets, unions, Cartesian products, power sets, disjoint unions, and
bijection transfer.

## Architecture invariants

- Surface elaboration may change syntax into core formulas and entries, but it
  does not replace kernel soundness checks.
- `ProofContext` owns elaboration scope. `LabelScope` and `DeclarationScope`
  remain validation-time kernel authorities.
- Theory-specific syntax belongs in theory environments, declaration recipes,
  phrase parsers, or rule implementations rather than generic parser branches.
- Every fact used for a proof step must be visible as a premise, hypothesis,
  declaration metadata, or ordinary formula.
- The substitution, capture, scope, theorem-promotion, and replay paths must
  share the same freshness and rule-configuration rules.
- A theorem's required axioms and parameterized rules travel with the promoted
  theorem and are checked again at each citation.

## Verification

Run the default batch:

```bash
./run_tests.sh
# equivalent named suite
./run_tests.sh --suite default
```

Run only the standard Python tests:

```bash
python3 -m pytest -q -m default pytest_tests
./run_tests.sh --suite default
```

Run only extended adversarial tests or the complete suite:

```bash
python3 -m pytest -q -m extended pytest_tests
./run_tests.sh --suite extended

Run every Python suite:

```bash
python3 -m pytest -q --suite all pytest_tests
./run_tests.sh --suite all
./run_tests.sh --extended  # compatibility alias for --suite all
```

List suites with:

```bash
./run_tests.sh --list-batches
```
```

List and run fixture suites:

```bash
./run_tests.sh --list-suites
./run_tests.sh --suite testProofsDeclared --verbose
```

Do not report coverage or pass counts without a fresh run on the exact commit.
Verification details belong in the PR, CI result, or terminal output that
measured them, not in permanent architecture documents.

## Resume checklist

1. Read `AGENT_COLLABORATION.md`.
2. Read the relevant subsection of `todos.txt`.
3. Check the current branch, working tree, open issues, and open pull requests.
4. Read only the reference documents needed for the subsystem.
5. Make a small testable change and run the smallest relevant suite.
6. Run `./run_tests.sh`, or state why the full run could not be completed.
