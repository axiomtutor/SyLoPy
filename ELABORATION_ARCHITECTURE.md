


# Surface Proof Elaboration Architecture

## 1. Separation of responsibilities

SyLoPy uses three representations:

### Text

The text layer contains the notation written by the user, including natural phrases such as:

```text
The empty set is a subset of X. (Subset proof below)
```

### Surface AST

`ProofParser.parse_surface_proof` produces:

- `SurfaceProof`
- `SurfaceLine`
- `SurfaceSubproof`
- `SourceSpan`

The surface AST preserves formula text, justification text, explicit or implicit subproof boundaries, proof labels, physical source lines, and original text. Public formula parsing (`ProofParser.parse_formula`) uses conventional connective precedence, installed by `ProofParserPolicy`.

### Core entries

`ProofParser.elaborate_proof` produces `ElaboratedEntries`, whose elements use the tuple mini-language consumed by `ProofLogic.ProofValidator`.

`ElaboratedEntries` also stores:

- `origin_by_label`
- `surface_proof`
- `required_rules`
- `required_axioms`
- `required_declarations`

`ProofLogic.Proof` automatically merges those theory resources before validation.

## 2. Subset proof expansion

The surface proof:

```text
2. S is a subset of T. (Subset proof below)
 2.1. Let a in S. (Assumption for subset proof)
 ...
 2.n. a is in T. (...)
```

is lowered to a core proof equivalent to:

```text
2. forall x, In(x, S) -> In(x, T).
   (UniversalGeneralization from subproof below)
begin subproof
  2.__arbitrary. a. (arbitrary)
  2.__conditional. In(a, S) -> In(a, T).
      (ConditionalIntroduction from subproof below)
  begin subproof
    2.1. In(a, S). (assume)
    ...
    2.n. In(a, T). (...)
  end subproof
end subproof
```

The internal labels are synthetic and never inserted into the user's file.

## 3. Error mapping

Each core label maps to a `CoreOrigin` containing:

- the original `SourceSpan`
- the surface construct name
- whether the core step was synthetic

If validation fails at `2.__conditional`, `Proof.check_detailed()` reports the failure at surface line `2`, with a detail beginning with `Invalid subset proof: conditional introduction`.

Errors detected before core validation, such as a subset proof beginning with an assumption about the wrong set, raise `ElaborationError` directly at the relevant surface line.

## 4. Theory extension contract

A `TheoryEnvironment` may contribute:

- `formula_parsers` -- consulted only at the top of a single proof line (by `_ElaborationContext.parse_surface_expression`); return a `SurfaceExpression`, which may carry extra structure (e.g. SetTheory's raw subset operands) a line elaborator later needs.
- `nested_formula_parsers` / `term_parsers` -- consulted by `ProofParser.parse_formula`/`parse_term` themselves, so theory syntax is also recognized in *nested* positions (inside `and`/`or`/`if...then`/etc., e.g. NumberTheory's `a|n` inside `if a|n then b`), not only when a formula consists of nothing else. `nested_formula_parsers` is checked *after* every connective the base grammar splits on, not before -- a theory phrase containing a connective-looking substring must not be given the chance to swallow more than intended before the grammar gets to split around it. Return a plain `Formula`/`Term` directly (no wrapper).
- `line_elaborators`
- core `rules`
- core `axioms`
- built-in `declarations`

Set theory registers:

- natural membership, subset, and "has no elements" syntax
- `EmptySetPropertyRule`, `SetEqualityRule`
- declarations for `EmptySet` and the binary predicate `In`
- the `Subset proof below` elaborator

Number theory (`NumberTheory.py`, extending both `NatThry.py` and `SetTheory.py`) registers:

- `n/a` (`Quotient`) as term-level sugar, and `a|n`/divisibility, `TERM is an integer` as nested-formula-level sugar
- `QuotientDefiningPropertyRule`, `QuotientUniquenessRule`
- declarations for `Int`, `Plus`, `Times`, `Neg`, `Quotient` (plus Nat's own, combined in)

To add another proof form, create a line elaborator with this shape:

```python
def elaborate_some_construct(line, context):
    if not matches(line):
        return None

    # Validate the surface contract.
    # Generate one core entry, possibly containing nested core entries.
    # Register origins for synthetic labels.
    return core_entry
```

Then add it to a `TheoryEnvironment.line_elaborators` list.

The elaborator should lower the construct to existing core rules whenever possible. A genuinely theory-specific axiom or primitive property can be supplied as a core rule through the environment.

## 5. Inspecting the elaboration

```python
entries, _ = ProofParser.parse_proof_text(text)
print(ProofParser.format_core_proof(entries))
```

This formatter is diagnostic only. The checker validates the AST in memory; it does not parse the formatted output again.




