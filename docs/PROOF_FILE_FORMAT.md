# SyLoPy proof-file format

Verified against origin/master commit `030c8a3d4f9e2280cc58237f4b306200f6cedfbf`.

This is a reference for the proof-file structure verified on that commit. It
deliberately omits evolving set-display/set-builder syntax, natural-language
existential and multi-subject declaration syntax, newer comma/range citation
syntax, and planned ZFC derived-rule syntax. Existing fixtures and source are
authoritative for those areas.

Examples are drawn from `tests/testProofs/multiProof.txt`,
`tests/setTheoryProofs/basic_theorems.txt`, and
`tests/setTheoryProofs/pairing_theorems.txt`.

## 1. Multi-proof files

A multi-proof fixture is divided into numbered cases:

```text
# 1: Title of the first theorem
## Proof that
### If ...
### then ...

1. ...
2. ...

# 2: Another proof
## Invalid proof.
### ...
1. ...
2. ...
```

`source/validate_all_proofs.py` recognizes:

- `# N` or `# N: Title` as a proof-case header;
- `## Proof that` as expected-valid;
- `## Invalid ...` as expected-invalid;
- `### ...` as descriptive text;
- `### then ...` as an optional stated conclusion.

A file without a `# N` header is checked as one proof. The headings are
fixture syntax, not proof lines.

### Titled proofs

A valid titled proof is promoted by
`validate_all_proofs.run_multi_proof_file()` before later cases are checked.
The theorem rule is named by the title and promotion is local to that file.

For example, `tests/setTheoryProofs/basic_theorems.txt` contains:

<!-- proof-format-test: valid-proof -->
```text
# 1: Subset is reflexive
## Proof that
### then X is a subset of X.

1. Let X be any set. (Declaration)
2. X is a subset of X. (Subset proof below)
 2.1. Let a in X. (Assumption for subset proof)
 2.2. a is in X. (Reiteration from 2.1)
```

Promotion uses the proof's top-level derived formulas as its conclusion and,
by default, top-level object declarations as generalized names. See
`ProofLogic.promote_theorem()`.

## 2. Proof lines and labels

An ordinary proof line has the form:

```text
LABEL. FORMULA. (JUSTIFICATION)
```

The final parenthesized group is the justification. A missing final
justification is a parse error.

The label pattern in `ProofParser.py` is:

```text
[0-9]+(\.[A-Za-z0-9_]+)*.
```

Examples are `1.`, `2.1.`, `2.1.1.`, and `2.1.case1.`. Labels are the
names used by rule citations. Dotted descendants also delimit implicit
subproofs.

The parser preserves physical source spans, so validation errors can be mapped
back to the original surface line even when elaboration generates synthetic
core entries.

The formula/justification split uses the final matching parenthesized group,
so formula parentheses are allowed:

```text
2. (A or B) and not (C or D). (Premise)
```

## 3. Comments

Comments use:

```text
(* This is a comment. *)
```

They may span lines and occur anywhere in a proof. The parser removes them
while preserving newlines for source locations. This is exercised by
`tests/testProofs/multiProof.txt`.

Lines beginning with `#` are structural headings in a multi-proof fixture;
they are also ignored when the proof parser prepares an individual proof body.

## 4. Subproofs

Explicit subproofs use:

<!-- proof-format-test: valid-proof -->
```text
# 1: Conditional introduction from an explicit subproof
## Proof that
### then A -> B.

1. Let A, B be closed formulas such that: A -> B. (Premise)
2. A -> B. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption for conditional introduction)
 2.2. B. (Modus Ponens from 1, 2.1)
end subproof
```

A rule whose justification ends in `from subproof below` consumes the attached
subproof. The base rules using this form include Conditional Introduction,
Proof by Contradiction, and Universal Generalization.

Rules can also consume cited lines plus subproofs. The existing case-analysis
fixture uses:

<!-- proof-format-test: valid-proof -->
```text
# 1: Proof by cases with two explicit subproofs
## Proof that
### then R.

1. Let P, Q, R be closed formulas such that: P or Q. if P then R. Q -> R. (Premise)
2. R. (Proof by Cases from 1, subproofs below)
begin subproof
 2.1.case1. P. (Case)
 2.2.case1. R. (Modus Ponens from 1, 2.1.case1)
end subproof
begin subproof
 2.1.case2. Q. (Case)
 2.2.case2. R. (Modus Ponens from 1, 2.1.case2)
end subproof
```

A rule line followed by dotted descendant labels can omit the explicit
begin/end markers. This is the form used for `Subset proof below` in
`tests/setTheoryProofs/basic_theorems.txt`.

## 5. Declarations

A declaration line uses the `Declaration` or `Declare` justification:

```text
1. Let X be any set. (Declaration)
3. Let Y be an object. (Declare)
```

Declarations are lexical: a name is visible at its nesting level and in
descendant subproofs, but a declaration made inside a closed subproof is not
visible outside it.

The natural-language declaration grammar itself is intentionally not specified
here because multi-subject declarations are being changed.

An assumption is different from a declaration:

```text
2.1. A. (Assumption for conditional introduction)
```

It introduces a temporary formula for the subproof.

## 6. Stable justifications

The established citation form is:

```text
Rule from 2, 3
```

Examples:

```text
3. A and B. (Conjunction Introduction from 1, 2)
4. A. (Conjunction Elimination from 3)
5. C. (Modus Ponens from 2, 4)
```

Zero-citation forms include `Premise`, `Declaration`, `Declare`,
`Assumption ...`, `Axiom`, `Reiteration`, and `Reflexivity`.
Bare `Set property` is also supported in the current set-theory rules.

This document intentionally does not specify the newer comma-separated or
range citation spellings.

## 7. Rule names and aliases

`source/ProofJustification.py` uses an explicit alias table. Matching is
case-insensitive; hyphens are normalized to spaces.

| Rule | Accepted aliases |
|---|---|
| Universal Instantiation | Universal Instantiation; Universal Instantiation Rule |
| Universal Generalization | Universal Generalization; Universal Generalization Rule |
| Universal Modus Ponens | Universal Modus Ponens; Universal Modus Ponens Rule |
| Existential Introduction | Existential Introduction; Existential Introduction Rule; Existential Generalization |
| Existential Elimination | Existential Elimination; Existential Elimination Rule; Existential Instantiation |
| Conjunction Elimination | Conjunction Elimination; Conjunction Elimination Rule; And Elimination; And Elim |
| Conjunction Introduction | Conjunction Introduction; Conjunction Introduction Rule; And Introduction; And Intro |
| Disjunction Introduction | Disjunction Introduction; Disjunction Introduction Rule; Or Introduction; Or Intro; Addition |
| Disjunction Elimination | Disjunction Elimination; Disjunction Elimination Rule; Or Elimination; Or Elim; Proof by Cases; Cases |
| Biconditional Introduction | Biconditional Introduction; Biconditional Introduction Rule; Conditional Equivalence Introduction |
| Biconditional Elimination | Biconditional Elimination; Biconditional Elimination Rule; Conditional Elimination |
| Conditional Introduction | Conditional Introduction; Conditional Introduction Rule; Conditional Intro |
| Proof by Contradiction | Proof by Contradiction; Proof by Contradiction Rule; Reductio; Reductio Ad Absurdum |
| Modus Ponens | Modus Ponens; Modus Ponens Rule |
| Modus Tollens | Modus Tollens; Modus Tollens Rule |
| Disjunctive Syllogism | Disjunctive Syllogism; Disjunctive Syllogism Rule |
| Hypothetical Syllogism | Hypothetical Syllogism; Hypothetical Syllogism Rule |
| Explosion | Explosion; Explosion Rule; Ex Falso |
| Reiteration | Reiteration; Reiterate; Reiteration Rule |
| Substitution | Substitution; Leibniz Substitution; Leibniz |
| Symmetry | Symmetry; Symmetry Rule |
| Transitivity | Transitivity; Transitivity Rule |
| Reflexivity | Reflexivity; Reflexivity Rule |
| Algebra | Algebra; Algebraic Manipulation |
| Propositional Equivalence | De Morgan; De Morgan's; De Morgans; De Morgan's Laws; Distribution; Distributivity; Double Negation; Propositional Equivalence; Logical Equivalence; Equivalence; Conditional Equivalence |

These are the aliases actually registered by `_alias_map()`; they are not
inferred from class names.

### Registered theory rules

| Theory | Rule name |
|---|---|
| Set theory | EmptySetProperty, SetProperty, SetEquality |
| Set theory | SeparationSchema, ReplacementSchema |
| Set theory | PairingAxiom, UnionAxiom, PowerSetAxiom, InfinityAxiom |
| Natural numbers | Induction |
| Number theory | QuotientDefiningProperty, QuotientUniqueness |
| Discrete mathematics | RelationReflexivity, RelationIrreflexivity |
| Discrete mathematics | RelationSymmetry, RelationAntisymmetry |
| Discrete mathematics | RelationAsymmetry, RelationTransitivity, RelationTotality |

These names are the registered rule `name` attributes in
`SetTheory.py`, `NatThry.py`, `NumberTheory.py`, and
`DiscreteMathCore.py`.

The justification resolver also has theory placeholders for these names and
for the following spellings:

| Accepted spelling | Internal name |
|---|---|
| Relation reflexivity / irreflexivity / symmetry | RelationReflexivity / RelationIrreflexivity / RelationSymmetry |
| Relation antisymmetry / asymmetry / transitivity | RelationAntisymmetry / RelationAsymmetry / RelationTransitivity |
| Relation totality / Totality | RelationTotality |
| Quotient defining property / Quotient definition | QuotientDefiningProperty |
| Quotient uniqueness | QuotientUniqueness |
| Set equality | SetEquality |
| Induction | Induction |
| Empty set property | EmptySetProperty |
| Set property | EmptySetProperty when uncited; SetProperty when cited |
| Axiom of separation / Separation schema | Separation |
| Axiom of replacement / Replacement schema | Replacement |
| Axiom of pairing | PairingAxiom |
| Axiom of union | UnionAxiom |
| Axiom of power set / Power set axiom | PowerSetAxiom |
| Axiom of infinity | InfinityAxiom |

`Uniqueness`, `WLOG`, and `Mutatis mutandis` are named placeholders on
this commit, not implemented inference rules.

## 8. Premises, axioms, and conclusions

A `Premise` line supplies a formula to the proof's premise context. An
`Axiom` line must match an axiom supplied to the proof.

Derived rule lines are checked by the kernel against their cited lines and
attached subproofs; a rule name is not an unchecked assertion.

A multi-proof case may state a conclusion with `### then ...`. The fixture
runner checks that the stated formula is actually among the top-level formulas
derived by inference. It currently compares formulas up to renaming of bound
variables. The evolving surface syntax of the conclusion itself is not
specified here.

## 9. Minimal templates

Standalone proof:

```text
1. Let X be any set. (Declaration)
2. P(X). (Premise)
3. Q(X). (Some rule from 2)
```

Multi-proof fixture:

```text
# 1: Theorem title
## Proof that
### If ...
### then ...

1. ...
2. ...
```

Explicit subproof:

```text
1. P. (Premise)
2. Q. (Conditional Introduction from subproof below)
begin subproof
 2.1. R. (Assumption for conditional introduction)
 2.2. Q. (Rule from 1)
end subproof
```

These are structural templates only; the cited formulas must satisfy the
actual rule.

## 10. Source and fixture references

The implementation is primarily in:

- `source/ProofParser.py` — labels, source lines, and subproof boundaries;
- `source/ProofJustification.py` — rule-name/alias resolution;
- `source/ProofLogic.py` — core validation and theorem promotion;
- `source/validate_all_proofs.py` — fixture headers and titled-proof promotion;
- `source/ProofElaboration.py` — surface/core data structures and theory environments.

Concrete examples are in:

- `tests/testProofs/multiProof.txt`;
- `tests/setTheoryProofs/basic_theorems.txt`;
- `tests/setTheoryProofs/pairing_theorems.txt`;
- `tests/testDiscreteMath/invalid_relation_properties.txt`.

No existing repository file was modified for this contribution.
