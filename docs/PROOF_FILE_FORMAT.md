# SyLoPy proof-file format

Complete proof examples marked in this document are executed by the pytest suite; CI results identify the exact commit tested.

This reference describes the proof-file syntax and the implemented surface forms in the current repository. The parser and theory modules remain authoritative when a rule or phrase evolves. The document distinguishes supported input syntax from features that are explicitly deferred.

Examples are drawn from the current fixture corpus and include executable worked proofs below.
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

Promotion uses the proof's last top-level derived formula as its conclusion and,
by default, top-level object declarations as generalized names. Every
hypothesis the proof took for granted, at any depth, becomes a premise of the
theorem. A relation the proof declared (`Let R be a symmetric relation on X`) is
generalized like an object: the carrier and properties that the proof read from
its declaration are not formulas, so they become requirements on the declaration
of the relation the theorem is cited for (the same carrier, a set's name, and at
least those properties), and the premises are then said of that relation. The
theory's axioms the proof cited and the theory's rules it used are not premises
but requirements: a later proof in the same file has them, so it may cite the
theorem. See `ProofLogic.promote_theorem()` and
`tests/testDiscreteMath/promoted_relation_theorems.txt`.

### Citing a theorem

A promoted theorem is cited by its title, the way a rule is. A theorem with no
premises is cited bare, as in `(Subset is reflexive)`. A theorem with premises
is cited with the lines that state them, in the order the theorem took them, as
in `(Pair transport from 4, 5)`:

<!-- proof-format-test: valid-proof -->
```text
# 1: Pair transport
## Proof that
### then P(a) and Q(a).

1. Let a be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(a). (Premise)
5. Q(a). (Premise)
6. P(a) and Q(a). (Conjunction Introduction from 4, 5)

# 2: Use pair transport
## Proof that
### then P(b) and Q(b).

1. Let b be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(b). (Premise)
5. Q(b). (Premise)
6. P(b) and Q(b). (Pair transport from 4, 5)
```

The title is matched like a rule name (case-insensitively, hyphens as spaces),
but a title never replaces a built-in rule name. A title can be cited only once
its proof has been checked and promoted: citing one that is promoted later in
the file, or whose proof failed, is a validation error ("no rule named ...").
A name that is neither a rule nor a title in the file, followed by line numbers,
is a parse error, so a misspelled rule name is still reported as one. Through the
Python API, `check_proof_text` recognizes the theorems among its `rules`, and
`parse_proof_text` takes the titles as `theorem_names`.

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

Declarations support multiple names and ordinary typed/set-membership clauses, for example `Let X, Y be any set. (Declaration)`, `Let a be an integer. (Declaration)`, and `Let R be a reflexive relation on X. (Declaration)`. The names are available at that line and throughout its descendant scopes; declarations made in a closed subproof do not escape it.

Typed unary functions use `Let f: X -> Y be a unary function. (Declaration)`.
The domain and codomain names must already be declared sets; the declaration
records both names as function metadata. A set can also receive a symbolic
defining predicate with `Let Y be a set with defining property P. (Declaration)`;
`P` must already be a declared unary predicate, and this declaration adds the
ordinary formula `forall u, (In(u, Y) iff P(u))`.

`Let R be a reflexive relation on X` declares R as a relation on X in the usual sense, a subset of X × X, and the declaration line states that as a formula, the way `Let a be in X` states `In(a, X)`: `forall x, forall y, (R(x, y) -> (In(x, X) and In(y, X)))`, one for each relation the declaration names, at the place in the line where the relation is declared. It is the same however the relation is described, and wherever its carrier was declared (in the same statement, on an earlier line, or in an enclosing proof). A proof gets the memberships from a fact `R(a, b)` with the ordinary rules, for terms that were declared in no set at all:

```text
1. Let X be any set, R be a relation on X, a, b be objects, R(a,b). (Declaration)
2. forall y, (R(a,y) -> (In(a,X) and In(y,X))). (Universal Instantiation from 1)
3. In(a,X) and In(b,X). (Universal Modus Ponens from 2, 1)
```

The bound variables of that formula are the first two of `x, y, u, v, s, t` that are not the name of the relation or of its carrier, and a line that states or cites it writes those names. A relation declared through the API, with a carrier and properties as metadata and no declaration line, states nothing.

The relation rules read the declaration in scope, and what they need of X follows from that. `Relation Symmetry`, `Relation Antisymmetry`, `Relation Asymmetry` and `Relation Transitivity` start from lines `R(a, b)`, which put `a` and `b` in X, so they need only the declared property: no line saying that `a` is in X, and it does not matter which set `a` was declared in. `Relation Reflexivity`, `Relation Irreflexivity` and `Relation Totality` start from membership, so they cite the line saying that the term is in X, and X must be the carrier named in the declaration; a proof that has only `R(a, b)` derives the membership first, as above.

A witness obtained from an existing existential can be named with `Let Y be such a set. (Existence from L)`, where line `L` states an existential formula. This names a witness and states its existential body as a scoped declaration; it is not an axiom citation and does not replace one.

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

Citation lists accept forms such as `Modus Ponens from 2, 3`, `Modus Ponens, 2, 3`, `Modus Ponens from 2 and 3`, and ranges such as `Modus Ponens from 2 to 4`. A range supplies its two endpoint labels; it is not expanded into every label between them. See the registered rule's arity and the proof's scope for what those references mean.

## 7. Rule names and aliases

`source/ProofJustification.py` resolves ordinary logical rule names through an explicit, case-insensitive alias table. Hyphens are normalized to spaces. The following table gives one canonical spelling for each registered built-in rule; selected aliases are shown beside it.

| Canonical spelling | Other accepted aliases |
|---|---|
| Universal Instantiation | Universal Instantiation Rule |
| Universal Generalization | Universal Generalization Rule |
| Universal Modus Ponens | Universal Modus Ponens Rule |
| Uniqueness | Uniqueness Rule |
| Existential Introduction | Existential Introduction Rule; Existential Generalization |
| Existential Elimination | Existential Elimination Rule; Existential Instantiation |
| Conjunction Elimination | Conjunction Elimination Rule; And Elimination; And Elim |
| Conjunction Introduction | Conjunction Introduction Rule; And Introduction; And Intro |
| Disjunction Introduction | Disjunction Introduction Rule; Or Introduction; Or Intro; Addition |
| Disjunction Elimination | Disjunction Elimination Rule; Or Elimination; Or Elim; Proof by Cases; Cases |
| Biconditional Introduction | Biconditional Introduction Rule; Conditional Equivalence Introduction |
| Biconditional Elimination | Biconditional Elimination Rule; Conditional Elimination |
| Conditional Introduction | Conditional Introduction Rule; Conditional Intro |
| Proof by Contradiction | Proof by Contradiction Rule; Reductio; Reductio Ad Absurdum |
| Modus Ponens | Modus Ponens Rule |
| Modus Tollens | Modus Tollens Rule |
| Disjunctive Syllogism | Disjunctive Syllogism Rule |
| Hypothetical Syllogism | Hypothetical Syllogism Rule |
| Explosion | Explosion Rule; Ex Falso |
| Reiteration | Reiterate; Reiteration Rule |
| Substitution | Leibniz Substitution; Leibniz |
| Symmetry | Symmetry Rule |
| Transitivity | Transitivity Rule |
| Reflexivity | Reflexivity Rule |
| Algebra | Algebraic Manipulation |
| De Morgan | De Morgan's; De Morgans; De Morgan's Laws; Distribution; Distributivity; Double Negation; Propositional Equivalence; Logical Equivalence; Equivalence; Conditional Equivalence |

### Theory-rule names and placeholders

Set theory, number theory, natural-number reasoning, and discrete mathematics add named rules through the selected/default theory environment. The justification resolver recognizes the following surface spellings for theory rules. Some are aliases; the final column names the internal placeholder used before the active theory environment resolves it.

| Accepted spelling | Internal placeholder |
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
| Set equality | SetEquality |
| Induction | Induction |
| Empty set property | EmptySetProperty |
| Set property | EmptySetProperty when uncited; SetProperty when cited |
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
| Axiom of extensionality | ExtensionalityAxiom |
| Axiom of foundation | FoundationAxiom |
| Axiom of regularity | FoundationAxiom |
| Axiom of choice | ChoiceAxiom |
| WLOG | WLOG |
| Without loss of generality | WLOG |
| Mutatis mutandis | MutatisMutandis |

The general `Set property` form is selected when the citation supplies lines; the bare form denotes the empty-set property. `Set equality` checks the two subset directions. `Uniqueness` combines a cited existential witness/existence formula with a conditional that every object satisfying the defining property equals the witness.

WLOG replay is implemented for equality cases that differ in exactly one constant term and for arbitrary cases aligned structurally at the formula and term positions. Arbitrary alternatives may exchange one-to-one declared constant names; predicate names, formula structure, function symbols, quantifier structure, and bound-variable names must match. Replay checks each alternative and retains outside citations only when the exchange leaves the cited fact invariant (up to commutative ordering of `and`/`or`). `Mutatis mutandis` is implemented for names replaced by names or terms, and for predicate and function symbols replaced by others; see the next subsection.

For `Let Y be a set with defining property P. (Declaration)`, replay substitutes
the set name and symbolic predicate in both declaration metadata and the
generated `forall u, (In(u, Y) iff P(u))` formula. Replay citations still
require an exact visible counterpart; declarations themselves are not promoted
or silently assumed by either replay mechanism.

### Mutatis mutandis: the same argument for other names, terms and symbols

`P'. (Mutatis mutandis, B)` says that line `B` was derived by an argument that works just as well for other names or other symbols, and that `P'` is what `B` says with those. `P'. (Mutatis mutandis, A to B)` says the same and names the line `A` where the argument starts. What is replaced is read off the two statements, each wherever it occurs:

- a name in `B` is replaced by a name or by a term with no variable in it: `Q(a)` repeated as `Q(b)` or as `Q(f(a))`, or `Int(Plus(a, b))` repeated as `Int(Plus(Plus(a, b), c))`, which replaces `a` by `Plus(a, b)` and `b` by `c`;
- a predicate or function symbol in `B` is replaced by another that takes the same number of arguments: `Q(a)` repeated as `S(a)`, `P(f(a))` as `P(g(a))`, or `R(a, c)` as `S(a, c)`.

Everything is replaced at once. Two names may be exchanged (`T(a, b)` repeated as `T(b, a)`), and so may two predicates; a term that replaces a name is what it says, and is not replaced again. A name or symbol has one replacement, and two may be replaced by the same one. Nothing else may change: the connectives, the quantifiers, `=`, the shape of the formula and the free variables stay, and bound variables may be named differently as long as they correspond.

The checker does not take the line on trust. It writes out the argument that is being repeated -- the justification of line `B` and the subproofs below it, with the names and symbols replaced -- and checks that like any other line, so a refusal is an ordinary refusal at the `Mutatis mutandis` line, saying which line of the argument failed. Three things follow from that, and none needs a rule of its own:

- A term that replaces a name has no variable in it, so no quantifier of the line it is put into can capture it. A term that mentions the witness of an existential elimination in the argument is refused by the usual freshness check, as it would be if written out.
- There is no table of which rules of one relation correspond to which rules of another. A rule that reads what a relation is declared to be (`Relation Transitivity`, `Relation Symmetry`) reads the declaration of the new relation at this line: it accepts when that relation is declared with the property and refuses, by the rule, when it is not. A rule that is about one symbol (`Set property`, cited with lines, is about `In`) refuses another predicate with its own message.
- What the expansion has to arrange is the lines that the argument cites from outside. A cited line that says something about a name or symbol being replaced (`P(a)` when `a` becomes `b`, or the closure axiom for `Plus` when `Plus` becomes `Times`) is replaced by the earliest visible line that says it of the new one; a cited line that says nothing about those (a general fact) is cited as it is. A premise written as one bundle (`Let P, Q be predicates such that: A. B. (Premise)`) stands for a line it states every fact of, and so does a declaration line: `Let R be a relation on X` states the formula of Section 5 for `R`, so an argument that cites it, repeated for a relation `S`, needs a visible line that states the same formula for `S`, as a declaration of `S` on the same carrier does; with `S` on another set there is no such line and the repetition is refused. The range `A to B` asks that line `A` have such a counterpart and structurally replay-checks the ordinary derived lines in the closed range after substitution and citation remapping. Assumptions, declarations, premises, and standalone subproof blocks are not treated as derivation lines in the replay closure.

<!-- proof-format-test: valid-proof -->
```text
# 1: The same argument for b, citing the facts about b
## Proof that
### if P, Q and R are predicates such that: P(a) -> Q(a). Q(a) -> R(a). P(b) -> Q(b). Q(b) -> R(b).
### then (P(a) -> R(a)) and (P(b) -> R(b)).

1. Let a and b be objects. (Declare)
2. Let P, Q and R be predicates. (Declare)
3. P(a) -> Q(a). (Premise)
4. Q(a) -> R(a). (Premise)
5. P(b) -> Q(b). (Premise)
6. Q(b) -> R(b). (Premise)
7. P(a) -> R(a). (Conditional Introduction from subproof below)
begin subproof
 7.1. P(a). (Assumption for Conditional Introduction)
 7.2. Q(a). (Modus Ponens from 3, 7.1)
 7.3. R(a). (Modus Ponens from 4, 7.2)
end subproof
8. P(b) -> R(b). (Mutatis mutandis, 3 to 7)
9. (P(a) -> R(a)) and (P(b) -> R(b)). (Conjunction Introduction from 7, 8)

# 2: Two names exchanged
## Proof that
### if R and T are predicates such that: R(a, b) -> T(a, b). R(b, a) -> T(b, a). R(a, b). R(b, a).
### then T(a, b) and T(b, a).

1. Let a and b be objects. (Declare)
2. Let R and T be predicates. (Declare)
3. R(a, b) -> T(a, b). (Premise)
4. R(b, a) -> T(b, a). (Premise)
5. R(a, b). (Premise)
6. R(b, a). (Premise)
7. T(a, b). (Modus Ponens from 3, 5)
8. T(b, a). (Mutatis mutandis, 7)
9. T(a, b) and T(b, a). (Conjunction Introduction from 7, 8)

# 3: A name replaced by a term
## Proof that
### Int(a), Int(b) and Int(c) imply Int(Plus(Plus(a, b), c))

1. Let a, b, c be objects. (Declaration)
2. Int(a). (Premise)
3. Int(b). (Premise)
4. Int(c). (Premise)
5. forall x, forall y, ((Int(x) and Int(y)) -> Int(Plus(x, y))). (Axiom)
6. (Int(a) and Int(b)) -> Int(Plus(a, b)). (Conditional Introduction from subproof below)
begin subproof
 6.1. Int(a) and Int(b). (Assumption for Conditional Introduction)
 6.2. forall y, ((Int(a) and Int(y)) -> Int(Plus(a, y))). (Universal Instantiation from 5)
 6.3. (Int(a) and Int(b)) -> Int(Plus(a, b)). (Universal Instantiation from 6.2)
 6.4. Int(Plus(a, b)). (Modus Ponens from 6.3, 6.1)
end subproof
7. Int(a) and Int(b). (Conjunction Introduction from 2, 3)
8. Int(Plus(a, b)). (Modus Ponens from 6, 7)
9. (Int(Plus(a, b)) and Int(c)) -> Int(Plus(Plus(a, b), c)). (Mutatis mutandis, 6)
10. Int(Plus(a, b)) and Int(c). (Conjunction Introduction from 8, 4)
11. Int(Plus(Plus(a, b), c)). (Modus Ponens from 9, 10)

# 4: A function symbol replaced by another
## Proof that
### if P is a predicate and f and g are functions such that: forall x, P(f(x)). forall x, P(g(x)).
### then P(f(a)) and P(g(a)).

1. Let a be an object and P be a predicate and f, g be unary functions such that: forall x, P(f(x)). (Premise)
2. forall x, P(g(x)). (Premise)
3. P(f(a)). (Universal Instantiation from 1)
4. P(g(a)). (Mutatis mutandis, 3)
5. P(f(a)) and P(g(a)). (Conjunction Introduction from 3, 4)

# 5: A relation replaced by another that is declared to have the same property
## Proof that
### if R and S are equivalence relations on X, R(a,b), R(b,c), S(a,b) and S(b,c),
### then R(a, c) and S(a, c).

1. Let X be any set,
 R and S be equivalence relations on X,
 a, b, c be in X,
 R(a,b) and R(b,c) and S(a,b) and S(b,c). (Declaration)
2. R(a,c). (Relation Transitivity from 1, 1)
3. S(a,c). (Mutatis mutandis, 2)
4. R(a,c) and S(a,c). (Conjunction Introduction from 2, 3)
```

In the last example `S` is declared an equivalence relation, so `Relation Transitivity` accepts the repeated step for `S`. Had `S` been declared only symmetric, line 3 would be refused by that rule: `Mutatis mutandis cannot repeat line 2 with R by S: 'RelationTransitivity' does not justify S(a, c) from the cited line(s) ['1', '1']`.

The line is refused, with the reason, when:

- line `B` was not derived by a rule from other lines (a premise, an assumption or a declaration has no argument to repeat), or is a WLOG step (an argument that contains a WLOG step can be repeated);
- the argument contains a hypothesis -- a premise, an axiom, a witness named with `Existence from`, a declaration that states a fact or records structure -- since repeating it would add a hypothesis that nobody wrote;
- the new statement is not line `B` with names and symbols replaced (a different connective, shape, free variable or quantifier, or an equation against a relation), replaces nothing, replaces one name or symbol by two, replaces a symbol by one that takes another number of arguments, or replaces a name by a term that has a variable in it;
- a line of the argument cites a line for which no visible line says the same of the new names and symbols, or `A` has no such counterpart;
- more than `B` or `A to B` is cited, the range runs backwards or starts and ends at the same line (to repeat a line alone, cite just that line), or a cited line is not visible (a line inside a subproof that has ended is not);
- the repeated argument is itself wrong for the new names and symbols, and the rule of the step that fails refuses it: the new name is the witness the argument introduces, the new relation is not declared to have the property that a rule of the argument reads, or a rule about one symbol meets another.

Limits of this form: a name is replaced by a name or a term, and a predicate or function symbol by one symbol that takes the same number of arguments. A compound term is never replaced as a whole (`P(f(a))` as `P(c)` is refused, though `P(f(a))` as `P(g(b))` is not), and a symbol is never replaced by a term. Only a name or symbol that occurs in the statement of `B` is replaced, so the names and symbols that the argument uses only inside (a witness, a bound variable) are not changed. A repeated argument is one line with the subproofs attached to it, so a closed block of several lines (the first case of a proof by cases, say) cannot be repeated for the second as a whole. A repeated argument containing a premise, an axiom or a witness line is refused rather than repeated. The matching that finds a counterpart line also ignores the order of `and` and `or` and the names of bound variables, which WLOG's replay now does too.

## 8. Premises, axioms, and conclusions

A `Premise` line supplies a formula to the proof's premise context. An
`Axiom` line must match an axiom supplied to the proof: a formula that the
theory (or the caller) lists, restated exactly. A proof that is given no axioms
at all takes any formula as an axiom, as a bare proof does. A theory whose
axioms are all cited by name has nothing to list, and closes its axiom list so
that having none means that none can be cited this way: set theory does (its four
axioms are cited as `Axiom of pairing` and so on, see section 5), so there an
`Axiom` line is refused whatever it states. A refused `Axiom` line also says
which rules of the proof justify the formula outright, when some do, so that
restating one of the four set axioms is answered with the name to cite instead
(`cite it by name instead: (Axiom of pairing)`).

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

Runnable proof examples above are checked by `pytest_tests/test_proof_format_doc.py`; current implementation details are linked to their source files and fixture examples.

## 11. Theory directives and set-theory syntax

The currently accepted theory directives are `Use discrete math.` and `Use discrete mathematics.` They are validated at the start of a proof file. Today the default theory environment remains backward-compatible and includes the available theory modules, so the directive is not a strict environment selector.

Set-theory surface forms elaborate into ordinary first-order formulas. In particular:

- `X subseteq Y` and “X is a subset of Y” express `forall u, (In(u, X) -> In(u, Y))`. `Subset proof below` introduces an arbitrary member of the left set and proves that it belongs to the right set.
- A membership characterization such as `forall u, (In(u, Y) iff (u = a or u = b))` can be used with `Set property` and a cited formula to infer membership in or non-membership in `Y`.
- Bare `(Set property)` invokes the empty-set property and proves that an arbitrary object is not in the empty set. When references are supplied, `(Set property, L, P)` uses the cited characterization `L` and property `P` to derive the required instance.
- `Set equality` concludes equality from two subset proofs. `Uniqueness` concludes the corresponding exists-unique formula from an existence formula and a conditional uniqueness proof.

Pairing, Union, Power Set, Infinity, Extensionality, Foundation/Regularity, and Choice have named axiom-citation rules: `Axiom of pairing`, `Axiom of union`, `Axiom of power set`, `Axiom of infinity`, `Axiom of extensionality`, `Axiom of foundation`, and `Axiom of choice`. Regularity and Foundation are aliases of the same named rule. These are the only named ways to cite these axioms: a line that restates one with bare `Axiom` is refused in closed set theory. The rules do not introduce witnesses by themselves. Pairing, Union, Power Set, and Infinity check the shape of their formula, and Union and Power Set accept a formula instantiated for a particular set, e.g. `Exists Y, forall u, (In(u, Y) iff (exists v, (In(v, S) and In(u, v)))). (Axiom of union)` and `Exists Y, forall u, (In(u, Y) iff u subset S). (Axiom of power set)`. Infinity has no set parameter. Pairing's instance is `Exists Y, forall u, (In(u, Y) iff (u = a or u = b)). (Axiom of pairing)`.

Extensionality, Foundation/Regularity, and Choice are different: each is cited for one sentence, compared up to the names of its bound variables and with nothing else, so that citing one is never a way to state some other sentence. They take no cited lines.

- `(Axiom of extensionality)` cites `forall x, forall y, ((forall z, (In(z, x) iff In(z, y))) -> x = y)`, with the biconditional in either order.
- `(Axiom of foundation)`, or `(Axiom of regularity)`, cites `forall x, ((exists y, In(y, x)) -> exists y, (In(y, x) and not (exists z, (In(z, y) and In(z, x)))))`. The form with `not (x = EmptySet)` for "has a member" is not cited by name: a proof derives it from this sentence, `(Axiom of extensionality)` and `(Set property)`, as proof 17 of `tests/testSetTheory/zfc_axioms_exact.txt` does.
- `(Axiom of choice)` cites Zermelo's form, that a set of nonempty, pairwise disjoint sets has a set that meets each of them in exactly one element: `forall X, (((forall A, (In(A, X) -> exists a, In(a, A))) and (forall A, forall B, ((In(A, X) and In(B, X) and not (A = B)) -> not (exists c, (In(c, A) and In(c, B)))))) -> exists C, forall A, (In(A, X) -> exists a, (In(a, A) and In(a, C) and forall b, ((In(b, A) and In(b, C)) -> b = a))))`. It needs only `In` and `=`; a form with a choice function needs function application, which set theory does not have yet.
- The quantifier of a parenthesized part must itself be parenthesized, or it reaches over the arrow: `(forall z, (...)) -> x = y`.
- Renaming a bound variable throughout is the same sentence. A bound variable that another quantifier binds again is not: `forall x, forall y, ((forall y, (In(y, x) iff In(y, y))) -> x = y)` says that the empty set is every set, and is refused.
- Equivalent sentences are refused too; a proof derives them from the axiom. A refused line is told the sentence to cite.

After an axiom citation states an existential, name its witness with `Let Y be such a set. (Existence from L)`. The older direct Pairing-witness surface form—`There is a set Y = {a, b}. (Axiom of pairing)`—remains accepted for compatibility, but it is legacy rather than the design to extend. Do not use it as the template for Union, Power Set, or Infinity.

Separation and Replacement are schema citations. For axiom-instance and `Set property` examples that are more representative of set-theory work, see the complete proofs below and the fixtures in `tests/setTheoryProofs/`.

Finite sets can be declared with `Let A be a finite set. (Declaration)` or
with an exact cardinality: `Let A be a finite set of cardinality 3.
(Declaration)`. The equivalent formula forms are `A is finite`,
`A has cardinality 3`, `A has 3 elements`, and `Cardinality(A, 3)`.
Cardinality arguments are metatheoretic nonnegative integers; they are not
proof variables or first-order object terms. The set-theory rules cover
empty-set cardinality, cardinality-to-finiteness, finite subsets, unions,
finite products and power sets, cardinal transfer under bijections, and
cardinal arithmetic for products, power sets, and disjoint unions.

Features explicitly deferred:

- `Mutatis mutandis` beyond names, terms and symbols: repeating a closed block of several lines (the first case of a proof by cases, say), and counterpart lines that differ by the symmetry of `=` or `<->` (not planned for now: owner decision of 2026-10-30).
- Extending the older direct Pairing-witness form to other axiom rules. The form remains for compatibility, but is not the supported design.
- Definitions of `CartesianProduct` and `Pair`, which are declared and not yet defined (see Definitions below).

### Definitions

A definition names something and says what it is. It checks that the thing exists, then names it, and adds no axiom: a sentence that does not mention the new symbol is provable with the definition only if it was provable without it. In set theory a set is named by a property: its members are the objects that have the property, and the definition is the sentence that says so. The mechanism is one facility for every theory (`source/Definitions.py`), so that a module for algebra can define a cyclic group, and one for number theory a divisibility relation, the way set theory defines the union. A theory registers its definitions, and a proof cites one by its title, as it cites a theorem (matched like a rule name: case-insensitively, hyphens as spaces).

Set theory registers three, each cited for one sentence:

| Cited | For the sentence |
| --- | --- |
| `(Definition of union)` | `forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B)))` |
| `(Definition of intersection)` | `forall u, (In(u, Intersection(A, B)) iff (In(u, A) and In(u, B)))` |
| `(Definition of power set)` | `forall u, (In(u, PowerSet(A)) iff u subseteq A)`, that is, `forall u, (In(u, PowerSet(A)) iff forall w, (In(w, u) -> In(w, A)))` |

- `u`, `A` and `B` stand for any terms. The line may be the sentence with its `forall` as above (the form `Set property` reads), the instance for particular terms (`x is in A union B iff (x is in A or x is in B)`), or the sentence closed over all its variables (`forall S, forall T, forall u, ...`); the biconditional may be written either way round. A definition takes no cited lines.
- Nothing else is accepted. A true sentence about an operation, such as `x is in A union B iff x is in B union A`, is derived from the definition (proof 4 of `tests/testSetTheory/set_operation_definitions.txt` derives that union commutes) and is not cited as it. The terms must agree on the two sides, and so must the order of the sets in the disjunction or the conjunction. A refused line is told the sentence to cite.
- The quantifier of the power set's subset clause must not capture a variable of a term. With `w` as the element or as the set, the clause would say something else (that every set that is not a member of itself is in the power set), so the line is refused. Renaming the bound variable gives the sentence for the same terms, and a constant spelled like a bound variable is another term and is not captured.
- `x is in A union B` is a statement of its own, the membership `In(x, Union(A, B))`: that `x` has the property that defines the set. That it is the disjunction `x is in A or x is in B` is what the definition says, and a proof cites it to get from the one to the other (proof 9 of the same file). The phrases `x belongs to A union B` and `x is in the union of A and B` are still read as the disjunction itself; making them memberships like the others is planned (`todos.txt`).
- A definition adds no axiom, and the facility checks that it does not. Before a set is named, the definition shows that some set has exactly the members the sentence gives it: by an axiom that says so (Separation for the intersection, Power Set for the power set) or by a proof from the axioms (Pairing and Union for the union: the proof that the union of two sets exists, proof 2 of `tests/setTheoryProofs/set_operation_foundations.txt`). Extensionality gives that there is only one such set. A definition whose evidence fails is refused, and so is every line that cites it. A property that no set bounds, such as "the objects that are not members of `A`", names no set, since nothing says that there is one; it can be defined as a property, and not as a set.
- `CartesianProduct` and `Pair` are declared but not defined, so no proof can cite a definition of them. The ordered pair will be `{{a}, {a, b}}` with readable syntax for it, and the product a set of such pairs; both wait for the singleton and the unordered pair to be terms (`todos.txt`).

## 12. Worked set-theory proofs

The first two examples are foundational worked proofs. They are complete proof files and are run by the documentation test, along with the additional examples in this section.

<!-- proof-format-test: valid-proof -->
```text
# 1: There is no set of all sets
## Proof that
### then not (exists V, forall x, In(x, V)).

1. not (exists V, forall x, In(x, V)). (Proof by Contradiction from subproof below)
 1.1. exists V, forall x, In(x, V). (Assumption for contradiction)
 1.2. Let V be such a set. (Existence from 1.1)
 1.3. exists Y, forall u, (In(u, Y) iff (In(u, V) and not In(u, u))). (Separation)
 1.4. Let Y be such a set. (Existence from 1.3)
 1.5. In(Y, Y) iff (In(Y, V) and not In(Y, Y)). (Universal Instantiation from 1.4)
 1.6. In(Y, V). (Universal Instantiation from 1.2)
 1.7. In(Y, Y) -> (In(Y, V) and not In(Y, Y)). (Biconditional Elimination from 1.5)
 1.8. (In(Y, V) and not In(Y, Y)) -> In(Y, Y). (Biconditional Elimination from 1.5)
 1.9. not In(Y, Y). (Proof by Contradiction from subproof below)
  1.9.1. In(Y, Y). (Assumption for contradiction)
  1.9.2. In(Y, V) and not In(Y, Y). (Modus Ponens from 1.7, 1.9.1)
  1.9.3. not In(Y, Y). (Conjunction Elimination from 1.9.2)
  1.9.4. In(Y, Y) and not In(Y, Y). (Conjunction Introduction from 1.9.1, 1.9.3)
 1.10. In(Y, V) and not In(Y, Y). (Conjunction Introduction from 1.6, 1.9)
 1.11. In(Y, Y). (Modus Ponens from 1.8, 1.10)
 1.12. In(Y, Y) and not In(Y, Y). (Conjunction Introduction from 1.11, 1.9)
```


<!-- proof-format-test: valid-proof -->
```text
# 2: The union of two sets exists
## Proof that
### If A and B are sets
### then there exists U such that forall x, (In(x, U) iff (In(x, A) or In(x, B))).

1. A and B are sets. (Declaration)
2. Exists P, forall u, (In(u, P) iff (u = A or u = B)). (Axiom of pairing)
3. Let P be such a set. (Existence from 2)
4. Exists Y, forall u, (In(u, Y) iff (exists v, (In(v, P) and In(u, v)))). (Axiom of union)
5. Let Y be such a set. (Existence from 4)
6. A = A. (Reflexivity)
7. A = A or A = B. (Disjunction Introduction from 6)
8. In(A, P). (Set property from 3, 7)
9. B = B. (Reflexivity)
10. B = A or B = B. (Disjunction Introduction from 9)
11. In(B, P). (Set property from 3, 10)
12. forall x, (In(x, Y) iff (In(x, A) or In(x, B))). (Universal Generalization from subproof below)
begin subproof
 12.0. let c be arbitrary. (Arbitrary)
 12.1. In(c, Y) -> (In(c, A) or In(c, B)). (Conditional Introduction from subproof below)
  12.1.1. In(c, Y). (Assumption for Conditional Introduction)
  12.1.2. Exists v, (In(v, P) and In(c, v)). (Set property, 5, 12.1.1)
  12.1.3. Let v be an object. (Declare)
  12.1.4. In(c, A) or In(c, B). (Existential Elimination from 12.1.2, subproof below)
  begin subproof
   12.1.4.1. In(v, P) and In(c, v). (Assumption for Existential Elimination)
   12.1.4.2. In(v, P). (Conjunction Elimination from 12.1.4.1)
   12.1.4.3. In(c, v). (Conjunction Elimination from 12.1.4.1)
   12.1.4.4. v = A or v = B. (Set property, 3, 12.1.4.2)
   12.1.4.5. In(c, A) or In(c, B). (Proof by Cases from 12.1.4.4, subproofs below)
   begin subproof
    12.1.4.5.1. v = A. (Case)
    12.1.4.5.2. In(c, A). (Substitution from 12.1.4.5.1, 12.1.4.3)
    12.1.4.5.3. In(c, A) or In(c, B). (Disjunction Introduction from 12.1.4.5.2)
   end subproof
   begin subproof
    12.1.4.5.1. v = B. (Case)
    12.1.4.5.2. In(c, B). (Substitution from 12.1.4.5.1, 12.1.4.3)
    12.1.4.5.3. In(c, A) or In(c, B). (Disjunction Introduction from 12.1.4.5.2)
   end subproof
  end subproof
 12.2. (In(c, A) or In(c, B)) -> In(c, Y). (Conditional Introduction from subproof below)
  12.2.1. In(c, A) or In(c, B). (Assumption for Conditional Introduction)
  12.2.2. In(c, Y). (Proof by Cases from 12.2.1, subproofs below)
  begin subproof
   12.2.2.1. In(c, A). (Case)
   12.2.2.2. In(A, P) and In(c, A). (Conjunction Introduction from 8, 12.2.2.1)
   12.2.2.3. Exists v, (In(v, P) and In(c, v)). (Existential Introduction from 12.2.2.2)
   12.2.2.4. In(c, Y). (Set property, 5, 12.2.2.3)
  end subproof
  begin subproof
   12.2.2.1. In(c, B). (Case)
   12.2.2.2. In(B, P) and In(c, B). (Conjunction Introduction from 11, 12.2.2.1)
   12.2.2.3. Exists v, (In(v, P) and In(c, v)). (Existential Introduction from 12.2.2.2)
   12.2.2.4. In(c, Y). (Set property, 5, 12.2.2.3)
  end subproof
 12.3. In(c, Y) iff (In(c, A) or In(c, B)). (Biconditional Introduction from 12.1, 12.2)
end subproof
13. Exists U, forall x, (In(x, U) iff (In(x, A) or In(x, B))). (Existential Introduction from 12)
```

### General Set property: naming a pair set

<!-- proof-format-test: valid-proof -->
```text
# 5: A pair set contains both generators (witness named with "Let Y be such a set")
## Proof that
### there exists Y such that In(a, Y) and In(b, Y).

1. Let a, b be any set. (Declaration)
2. Exists Y, forall u, (In(u, Y) iff (u = a or u = b)). (Axiom of pairing)
3. Let Y be such a set. (Existence from 2)
4. a = a. (Reflexivity)
5. a = a or a = b. (Disjunction Introduction from 4)
6. In(a, Y). (Set property from 3, 5)
7. b = b. (Reflexivity)
8. b = a or b = b. (Disjunction Introduction from 7)
9. In(b, Y). (Set property from 3, 8)
10. In(a, Y) and In(b, Y). (Conjunction Introduction from 6, 9)
11. Exists Y, (In(a, Y) and In(b, Y)). (Existential Introduction from 10)
```

### Bare Set property: the empty set

<!-- proof-format-test: valid-proof -->
```text
# 1: The empty set has no members
## Proof that
### then a is not in the empty set.

1. Let a be any set. (Declaration)
2. a is not in the empty set. (Set property)
```

### Set equality from mutual inclusion

<!-- proof-format-test: valid-proof -->
```text
# 5: Mutual inclusion implies equality
## Proof that
### If X is a subset of Y and Y is a subset of X
### then X = Y.

1. Let X and Y be any sets. (Declaration)
2. X is a subset of Y. (Premise)
3. Y is a subset of X. (Premise)
4. X = Y. (Set Equality from 2, 3)
```

### Uniqueness: the power set of a set

<!-- proof-format-test: valid-proof -->
```text
# 6: Unique power set
## Proof that
### If A is a set,
### then there exists a unique set Y such that for all u, In(u, Y) iff u subset A.

1. Let A be any set. (Declaration)
2. Exists Y, forall u, (In(u, Y) iff u subset A). (Axiom of power set)
3. Let Y be such a set. (Existence from 2)
4. Let X be any set. (Declaration)
5. If (forall z, (In(z, X) iff z subset A)) then X = Y. (Conditional Introduction from subproof below)
 5.1. Forall z, (In(z, X) iff z subset A). (Assumption for Conditional Introduction)
 5.2. X subseteq Y. (Subset proof below)
  5.2.1. Let x in X. (Assumption for subset proof)
  5.2.2. x subset A. (Set property, 5.1, 5.2.1)
  5.2.3. In(x, Y). (Set property, 3, 5.2.2)
 5.3. Y subseteq X. (Subset proof below)
  5.3.1. Let y in Y. (Assumption for subset proof)
  5.3.2. y subset A. (Set property, 3, 5.3.1)
  5.3.3. In(y, X). (Set property, 5.1, 5.3.2)
 5.4. X = Y. (Set equality, 5.2, 5.3)
6. Exists Y, ((forall u, (In(u, Y) iff u subset A)) and (forall X, ((forall z, (In(z, X) iff z subset A)) -> X = Y))). (Uniqueness, 2, 5)
```

### Definitions of the set operations

<!-- proof-format-test: valid-proof -->
```text
# 7: A union contains its first set
## Proof that
### If A and B are sets
### then A is a subset of A union B.

1. Let A, B be any set. (Declaration)
2. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)
3. A is a subset of A union B. (Subset proof below)
 3.1. Let x in A. (Assumption for subset proof)
 3.2. In(x, A) or In(x, B). (Disjunction Introduction from 3.1)
 3.3. In(x, A union B). (Set property from 2, 3.2)
```

<!-- proof-format-test: valid-proof -->
```text
# 8: A member of a union is a member of one of its sets
## Proof that
### If x is in A union B then x is in A or x is in B.

1. Let A, B be any set, and x be any object. (Declaration)
2. x is in A union B. (Premise)
3. forall u, (In(u, Union(A, B)) iff (In(u, A) or In(u, B))). (Definition of union)
4. x is in A or x is in B. (Set property from 3, 2)
```
