# SyLoPy proof-file format

Verified against origin/master commit `030c8a3d4f9e2280cc58237f4b306200f6cedfbf`.

This document describes the proof-file structure and proof-line forms that are
implemented on that commit. It is deliberately narrower than a description of
the entire surface language. In particular, it does not specify the currently
evolving set-display/set-builder syntax, natural-language existential syntax,
natural-language multi-subject declaration syntax, the newer comma/range
citation spellings, or the planned ZFC derived-rule syntax. Those areas should
be treated as implementation-specific until their designs settle.

The examples below are taken from existing fixtures, principally
`tests/testProofs/multiProof.txt`, `tests/setTheoryProofs/basic_theorems.txt`,
and `tests/setTheoryProofs/pairing_theorems.txt`.

## 1. File structure

There are two related formats:

1. a bare proof file containing one proof;
2. a multi-proof fixture containing several numbered proof cases.

The multi-proof fixture format is the format used by
`source/validate_all_proofs.py` for files containing several independent
proofs.

A multi-proof file has this general structure:

```text
# 1: Title of the first theorem
## Proof that
### If ...
### then ...

1. ...
2. ...

# 2: Title of the second theorem
## Invalid proof.
### ...
1. ...
2. ...
```

The fixture runner recognizes:

- `# N` as the beginning of proof case `N`;
- `# N: Title` as the beginning of proof case `N` with a title;
- `## Proof that` as an expected-valid proof;
- `## Invalid ...` as an expected-invalid proof;
- `### ...` lines as descriptive lines, including an optional `### then ...`
  stated conclusion.

The `# N`, `##`, and `###` headings belong to the fixture format. They
are not proof lines. `validate_all_proofs.py` removes comments and then splits
a multi-proof file at the `# N` headers before parsing each proof body.

A bare proof file does not need these headings. A file containing no
multi-proof header is parsed as one proof by `check_file()`.

### Titles

The title after `# N:` is optional. When a titled proof validates,
`validate_all_proofs.run_multi_proof_file()` promotes it to a theorem rule
before checking later proof cases in the same file.

For example:

```text
# 1: Subset is reflexive
## Proof that
### then X is a subset of X.

1. Let X be any set. (Declaration)
2. X is a subset of X. (Subset proof below)
 2.1. Let a in X. (Assumption for subset proof)
 2.2. a is in X. (Reiteration from 2.1)
```

The promoted rule is named by the title. Later proof cases in the same file
can therefore cite the theorem by that name if the corresponding rule name is
accepted by the justification resolver.

Promotion is local to the multi-proof file. It does not create a global
repository-wide theorem database.

## 2. Proof lines and labels

An ordinary proof line has the form

```text
LABEL. FORMULA. (JUSTIFICATION)
```

The final parenthesized group is the justification. A line without a final
parenthesized justification is rejected as a malformed proof line.

The parser's label syntax is:

```text
[0-9]+(.[A-Za-z0-9_]+)*.
```

Thus the fixtures use labels such as:

```text
1.
2.
2.1.
2.1.1.
2.1.case1.
```

A label identifies a proof entry and is what ordinary rule citations refer to.
Dotted labels also identify descendants of a parent proof line when an
implicit subproof is used.

The parser preserves the physical source line span of each proof line. This is
why validation errors can be reported against the original surface line even
when elaboration has generated synthetic core entries.

### Periods

The formula and justification are separated by the final parenthesized
justification, not by the first parenthesis in the line. Consequently ordinary
formula parentheses are allowed:

```text
2. (A or B) and not (C or D). (Premise)
```

A trailing period before the justification is optional in the parser's
formula portion; the existing fixtures commonly use it.

## 3. Comments

Comments use C-style parenthesis-star delimiters:

```text
(* This is a comment. *)
```

They may occur before a proof, between proof lines, or after a proof line.
They may also span physical lines.

The parser removes comments before constructing its logical source lines while
preserving the corresponding newlines. Existing examples include comments at
the beginning of `tests/testProofs/multiProof.txt`, comments between proof
lines, and comments after proof lines.

A `#` line is not a comment in the same sense: in a multi-proof fixture it is
a structural header. The parser also ignores `#`-prefixed headings when
preparing an individual proof body.

## 4. Explicit subproofs

A subproof can be written with explicit delimiters:

```text
2. A -> B. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption for conditional introduction)
 2.2. B. (Some rule from 2.1)
end subproof
```

The `begin subproof` / `end subproof` pair delimits the nested proof.

A rule whose justification says `from subproof below` consumes the following
subproof. The parser attaches that subproof to the rule line; the kernel then
checks the rule and the nested proof.

The currently supported base rules using this form are:

- Conditional Introduction
- Proof by Contradiction
- Universal Generalization

Other rules use the same subproof mechanism through their theory-specific
registration; see the rule table below and the existing fixtures.

### Hybrid subproofs

Some rules cite ordinary lines as well as one or more subproofs:

```text
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

This is the form used by proof-by-cases/disjunction-elimination in
`tests/testProofs/multiProof.txt`.

The exact citation spellings that are currently being changed should not be
copied from this document. Use the spellings already present in an existing
fixture when working in an affected area.

### Implicit dotted subproofs

When a rule line has a label and its next lines have labels beginning with that
label plus a dot, the parser can infer the subproof boundary without explicit
`begin subproof` / `end subproof` markers.

For example:

```text
2. X is a subset of X. (Subset proof below)
 2.1. Let a in X. (Assumption for subset proof)
 2.2. a is in X. (Reiteration from 2.1)
```

The parser recognizes `2.1` and `2.2` as descendants of `2` and attaches
them as the subproof below line 2. This is the format used by
`tests/setTheoryProofs/basic_theorems.txt`.

## 5. Declarations

A declaration is an ordinary proof line whose justification is
`Declaration` or `Declare`.

Existing fixtures use, for example:

```text
1. Let X be any set. (Declaration)
3. Let Y be an object. (Declare)
```

A declaration line introduces names into the proof's lexical declaration
context. The declaration is visible at its nesting level and in descendant
subproofs, but a declaration introduced in a closed subproof is not visible
outside that subproof.

The precise natural-language forms for multi-subject declarations are not
specified here because that parser area is under active development. Use the
forms already present in the current fixtures when writing proofs there.

An assumption is different from a declaration. For example:

```text
2.1. A. (Assumption for conditional introduction)
```

introduces a temporary formula assumption for the subproof; it does not
declare `A` as a symbol.

## 6. Stable justification forms

A justification is a parenthesized rule name, optionally followed by cited
line labels.

The established citation form is:

```text
Rule from 2, 3
```

For example:

```text
3. A and B. (Conjunction Introduction from 1, 2)
4. A. (Conjunction Elimination from 3)
5. C. (Modus Ponens from 2, 4)
```

The following zero-citation forms are also ordinary proof justifications:

```text
(Premise)
(Declaration)
(Declare)
(Assumption ...)
(Axiom)
(Reiteration)
(Reflexivity)
(Set property)
```

The exact meaning of `Assumption ...` depends on the enclosing subproof rule.
The bare `Assumption`/case forms are represented by the parser as the
ordinary assumption tag; the enclosing rule determines what opening a
subproof is permitted to do.

This document intentionally does not specify the newer comma-separated or
range citation spellings. Those are part of the evolving citation syntax and
are covered separately by parser tests/oracles.

## 7. Rule names and aliases

Rule names are resolved by the explicit alias table in
`source/ProofJustification.py`, rather than by substring matching.
Normalization is case-insensitive and treats hyphens as spaces.

The following table records the aliases in the base rule table on the verified
commit.

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

The aliases above are the aliases actually registered by
`ProofJustification._alias_map()`. They are not inferred from class names.

### Theory rules registered on the base/default proof environment

The default proof resources include the rules from the theory environments in
addition to `ProofLogic.default_rules()`. The relevant registered rule names
are:

| Theory | Registered rule |
|---|---|
| Set theory | EmptySetProperty |
| Set theory | SetProperty |
| Set theory | SetEquality |
| Set theory | SeparationSchema |
| Set theory | ReplacementSchema |
| Set theory | PairingAxiom |
| Set theory | UnionAxiom |
| Set theory | PowerSetAxiom |
| Set theory | InfinityAxiom |
| Natural numbers | Induction |
| Integer/number theory | QuotientDefiningProperty |
| Integer/number theory | QuotientUniqueness |
| Discrete mathematics | RelationReflexivity |
| Discrete mathematics | RelationIrreflexivity |
| Discrete mathematics | RelationSymmetry |
| Discrete mathematics | RelationAntisymmetry |
| Discrete mathematics | RelationAsymmetry |
| Discrete mathematics | RelationTransitivity |
| Discrete mathematics | RelationTotality |

The set-theory names above are the `name` attributes of the registered rule
objects in `source/SetTheory.py`. The number-theory names are the
corresponding `name` attributes in `source/NumberTheory.py`.

Discrete-math relation rules are constructed from the declarations in the
proof, so their availability is declaration-sensitive. Their rule names are
registered through `DiscreteMathCore.relation_rule_set()`.

`ProofLogic.default_rules()` itself contains the base rules, while theory
rules are supplied by the proof's elaborated theory environment or by the
fixture runner's configured rule set.

### Theory-rule aliases and placeholders

`ProofJustification.py` maps these additional names to named theory
placeholders:

| Accepted name | Internal rule name |
|---|---|
| Relation reflexivity | RelationReflexivity |
| Relation irreflexivity | RelationIrreflexivity |
| Relation symmetry | RelationSymmetry |
| Relation antisymmetry | RelationAntisymmetry |
| Relation asymmetry | RelationAsymmetry |
| Relation transitivity | RelationTransitivity |
| Relation totality | RelationTotality |
| Totality | RelationTotality |
| Quotient defining property | QuotientDefiningProperty |
| Quotient definition | QuotientDefiningProperty |
| Quotient uniqueness | QuotientUniqueness |
| Quotient uniqueness | QuotientUniqueness |
| Set equality | SetEquality |
| Induction | Induction |
| Empty set property | EmptySetProperty |
| Set property | EmptySetProperty when cited without line references |
| Axiom of separation | Separation |
| Separation schema | Separation |
| Axiom schema of separation | Separation |
| Axiom of replacement | Replacement |
| Replacement schema | Replacement |
| Axiom schema of replacement | Replacement |
| Axiom of pairing | PairingAxiom |
| Axiom of union | UnionAxiom |
| Axiom of power set | PowerSetAxiom |
| Power set axiom | PowerSetAxiom |
| Axiom of infinity | InfinityAxiom |
| Uniqueness | Uniqueness |
| WLOG | WLOG |
| Without loss of generality | WLOG |
| Mutatis mutandis | MutatisMutandis |

The last three are named placeholders only on this commit. They are not
implemented inference rules and are not documented here as usable proof
steps.

The distinction for `Set property` is intentional: with citations it
resolves to the general `SetProperty` rule; without citations, the existing
bare form resolves to `EmptySetProperty`.

## 8. Premises, axioms, and derived rules

A `Premise` line contributes a formula to the proof's premise context.
A line justified by `Axiom` must match one of the axioms supplied to the
proof.

For example, the set-theory fixture contains:

```text
2. Exists Y, forall u, (In(u, Y) iff (u = a or u = b)). (Axiom of pairing)
```

The named set-theory axiom spellings above are currently shape-checking rule
placeholders/rules in the source, but the direct witness-producing form is
part of the later set-theory design rather than a format feature documented
here. Use the exact forms already present in current fixtures.

A derived rule citation identifies a formula that must be justified from the
cited lines and/or attached subproofs. The kernel checks the rule rather than
treating a rule name as an unchecked assertion.

## 9. Stated conclusions

A multi-proof fixture can state a conclusion with a `### then ...` line.

For a valid proof, the fixture runner checks that the stated conclusion is
among the formulas actually derived by top-level inference steps. It does not
merely check that the final source line happens to resemble the conclusion.

The runner currently compares formulas up to renaming of bound variables when
performing this check.

This feature is intentionally documented only at the fixture level. The
surface syntax used to express evolving theory phrases in a `then` line is
not specified here.

## 10. Recommended minimal template

For an ordinary standalone proof:

```text
1. Let X be any set. (Declaration)
2. P(X). (Premise)
3. Q(X). (Some rule from 2)
```

For a multi-proof fixture:

```text
# 1: Theorem title
## Proof that
### If ...
### then ...

1. ...
2. ...

# 2: Another theorem
## Proof that
### If ...
### then ...

1. ...
2. ...
```

For an explicit subproof:

```text
1. P. (Premise)
2. Q. (Conditional Introduction from subproof below)
begin subproof
 2.1. R. (Assumption for conditional introduction)
 2.2. Q. (Rule from 1)
end subproof
```

The examples above are structural templates only. Every cited line and every
rule must satisfy the actual rule's premises and conclusion shape.

## 11. What this document does not specify

The following are intentionally outside this reference because they are under
active development on the verified commit:

- set enumeration, set-builder, and related natural-language set phrases;
- natural-language existential and unique-existence phrases;
- the evolving declaration grammar for multi-subject declarations;
- comma-separated and range-style citation spellings;
- the stated-conclusion syntax beyond the fixture-level checking behavior;
- planned ZFC witness-introduction, WLOG, Uniqueness, and Mutatis mutandis
  surface forms.

For those areas, the source and the current tests/oracles are the authoritative
references until their syntax is settled.

## 12. Source references

The format described here is implemented primarily by:

- `source/ProofParser.py` — source-line preparation, labels, subproof
  boundaries, and conversion to surface proof entries;
- `source/ProofJustification.py` — deterministic rule-name and alias
  resolution;
- `source/ProofLogic.py` — core entries, rule validation, lexical validation,
  and theorem promotion;
- `source/validate_all_proofs.py` — multi-proof headers, validity markers,
  stated-conclusion checks, and titled-proof promotion;
- `source/ProofElaboration.py` — surface/core data structures and theory
  environments.

Existing concrete examples are in:

- `tests/testProofs/multiProof.txt`;
- `tests/setTheoryProofs/basic_theorems.txt`;
- `tests/setTheoryProofs/pairing_theorems.txt`;
- `tests/testDiscreteMath/invalid_relation_properties.txt`.

No claim in this document should be read as defining syntax that is absent
from those implementations or fixtures.
