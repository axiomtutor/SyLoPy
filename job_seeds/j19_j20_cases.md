# Cases for J19 and J20

Every entry below was run on master `045de51` in the suite it belongs to: with all of them applied, `tests/testProofs` passes 122/122 and `tests/testDiscreteMath` 42/42, and the pin tests pass after the row changes the jobs describe. Copy the entries verbatim, including the `# N:` header line. Where an entry replaces a case, keep the number.

## J19 (J16 and J18 files)

### `fo35`: replaces `first_order_classics.txt` #35

The proof instantiates first and then denies the antecedent. The old #35 cited the bundled premises directly, and a valid Modus Tollens written that way is refused identically, so it never tested the fallacy. Refused at line 3.

```
# 35: Denying the antecedent
## Invalid: denying the antecedent — a false antecedent does not establish that the consequent is false.
### then not Q(a).

1. Let a be an object and P, Q be predicates such that: forall x, (P(x) -> Q(x)). not P(a). (Premise)
2. P(a) -> Q(a). (Universal Instantiation from 1)
3. not Q(a). (Modus Tollens from 2, 1)
```

### `fo38`: replaces `first_order_classics.txt` #38

Statement 5 of J16 exactly as the job gave it (two universal premises). Valid. #39 stays.

```
# 38: Symmetric and transitive predicates are reflexive wherever defined
## Proof that
### if R is a predicate such that: forall x, forall y, (R(x, y) -> R(y, x)). forall x, forall y, forall z, ((R(x, y) and R(y, z)) -> R(x, z)).
### then forall x, ((exists y, R(x, y)) -> R(x, x)).

1. Let R be a predicate such that: forall x, forall y, (R(x, y) -> R(y, x)). forall x, forall y, forall z, ((R(x, y) and R(y, z)) -> R(x, z)). (Premise)
2. forall x, ((exists y, R(x, y)) -> R(x, x)). (Universal Generalization from subproof below)
begin subproof
 2.0. let c be arbitrary. (Arbitrary)
 2.1. (exists y, R(c, y)) -> R(c, c). (Conditional Introduction from subproof below)
 begin subproof
  2.1.1. exists y, R(c, y). (Assumption for Conditional Introduction)
  2.1.2. Let w be an object. (Declare)
  2.1.3. R(c, c). (Existential Elimination from 2.1.1, subproof below)
  begin subproof
   2.1.3.1. R(c, w). (Assumption for Existential Elimination)
   2.1.3.2. forall y, (R(c, y) -> R(y, c)). (Universal Instantiation from 1)
   2.1.3.3. R(c, w) -> R(w, c). (Universal Instantiation from 2.1.3.2)
   2.1.3.4. R(w, c). (Modus Ponens from 2.1.3.3, 2.1.3.1)
   2.1.3.5. forall y, forall z, ((R(c, y) and R(y, z)) -> R(c, z)). (Universal Instantiation from 1)
   2.1.3.6. forall z, ((R(c, w) and R(w, z)) -> R(c, z)). (Universal Instantiation from 2.1.3.5)
   2.1.3.7. (R(c, w) and R(w, c)) -> R(c, c). (Universal Instantiation from 2.1.3.6)
   2.1.3.8. R(c, w) and R(w, c). (Conjunction Introduction from 2.1.3.1, 2.1.3.4)
   2.1.3.9. R(c, c). (Modus Ponens from 2.1.3.7, 2.1.3.8)
  end subproof
 end subproof
end subproof
```

### `fo41`: appended to `first_order_classics.txt` as #41

The valid sibling of #35.

```
# 41: Modus Tollens after instantiation (the valid sibling of #35)
## Proof that
### if a is an object and P, Q are predicates such that: forall x, (P(x) -> Q(x)). not Q(a).
### then not P(a).

1. Let a be an object and P, Q be predicates such that: forall x, (P(x) -> Q(x)). not Q(a). (Premise)
2. P(a) -> Q(a). (Universal Instantiation from 1)
3. not P(a). (Modus Tollens from 2, 1)
```

### `fo28` (optional): replaces `first_order_classics.txt` #28

```
# 28: Equality is symmetric
## Proof that
### if a and b are objects such that: a = b.
### then b = a.

1. Let a and b be objects such that: a = b. (Premise)
2. a = a. (Reflexivity)
3. b = a. (Substitution from 1, 2)
```

### Retitles: `first_order_classics.txt` #36 and #37

Change only the `## Invalid:` line; the proofs stay.

- #36: `## Invalid: wrong-rule citation — Universal Instantiation yields an instance of the cited body, which (forall x, P(x)) or (forall x, Q(x)) is not.`
- #37: `## Invalid: wrong-rule citation — the cited line is existential, and forall x, P(x) is not an instance of its body.`

### `equivalence_classes.txt`: conclusions

Add these lines directly after the `### if` line of the case:

- #3: `### then C = D.`
- #4: `### then R(a, b).`
- #5: `### then C = D.`

### `ec6`: replaces `equivalence_classes.txt` #6

The `### then` is balanced, and line 4 of the old proof (a Universal Generalization that restated line 3) is gone.

```
# 6: Every object in the carrier belongs to a named equivalence class
## Proof that
### then exists C, ((forall u, (In(u, C) iff (In(u, X) and R(a, u)))) and In(a, C)).

1. Let X be any set, R be an equivalence relation on X, and a be in X. (Declaration)
2. exists C, forall u, (In(u, C) iff (In(u, X) and R(a, u))). (Separation)
3. Let C be such a set. (Existence from 2)
4. R(a, a). (Relation Reflexivity from 1)
5. In(a, X) and R(a, a). (Conjunction Introduction from 1, 4)
6. In(a, C). (Set property from 3, 5)
7. (forall u, (In(u, C) iff (In(u, X) and R(a, u)))) and In(a, C). (Conjunction Introduction from 3, 6)
8. exists C, ((forall u, (In(u, C) iff (In(u, X) and R(a, u)))) and In(a, C)). (Existential Introduction from 7)
```

## J20 (J17 files)

### `de6`: appended to `red_team_DisjunctionElimination.txt` as #6

```
# 6: The first case block must end in the requested conclusion
## Invalid: case-conclusion mismatch — the first block ends in S, not R.
### then R.

1. Let P, Q, R, S be closed formulas such that: P or Q. if P then S. if Q then R. (Premise)
2. R. (Proof by Cases from 1, subproofs below)
begin subproof
 2.1.case1. P. (Case)
 2.2.case1. S. (Modus Ponens from 1, 2.1.case1)
end subproof
begin subproof
 2.1.case2. Q. (Case)
 2.2.case2. R. (Modus Ponens from 1, 2.1.case2)
end subproof
```

### `pbc4` and `pbc5`: appended to `red_team_ProofByContradiction.txt` as #4 and #5

```
# 4: Proof by contradiction from a positive assumption concludes its negation
## Invalid: target mismatch — a contradiction under A does not establish not B.
### then not B.

1. Let A and B be closed formulas such that: A. not A. (Premise)
2. not B. (Proof by Contradiction from subproof below)
begin subproof
 2.1. A. (Assumption for Contradiction)
 2.2. A and not A. (Conjunction Introduction from 2.1, 1)
end subproof
```

```
# 5: Proof by contradiction from a positive assumption (the valid sibling of #4)
## Proof that
### then not A.

1. Let A be a closed formula such that: not A. (Premise)
2. not A. (Proof by Contradiction from subproof below)
begin subproof
 2.1. A. (Assumption for Contradiction)
 2.2. A and not A. (Conjunction Introduction from 2.1, 1)
end subproof
```

### `ee6` and `ee7`: appended to `red_team_ExistentialElimination.txt` as #6 and #7

```
# 6: The witness cannot occur in a line visible before the subproof
## Invalid: outer-context freshness — w occurs in line 3, which is visible before the subproof opens, though no hypothesis mentions w.
### then exists x, P(x).

1. Let P be a predicate such that: exists x, P(x). (Premise)
2. Let w be an object. (Declare)
3. w = w. (Reflexivity)
4. exists x, P(x). (Existential Elimination from 1, subproof below)
begin subproof
 4.1. P(w). (Assumption for Existential Elimination)
 4.2. exists x, P(x). (Existential Introduction from 4.1)
end subproof
```

```
# 7: The witness cannot occur in a premise stated inside its own subproof
## Invalid: hypothesis in force — R(w) is a premise of the whole proof, so what the subproof derived may depend on it.
### then exists x, R(x).

1. Let P and R be predicates such that: exists x, P(x). (Premise)
2. Let w be an object. (Declare)
3. exists x, R(x). (Existential Elimination from 1, subproof below)
begin subproof
 3.1. P(w). (Assumption for Existential Elimination)
 3.2. R(w). (Premise)
 3.3. exists x, R(x). (Existential Introduction from 3.2)
end subproof
```

### `scope2`: replaces `red_team_Scope.txt` #2

The old #2 was the same proof as `red_team_Reiteration.txt` #3. This one cites the closed line with a different rule.

```
# 2: A label from a closed subproof is not visible afterward
## Invalid: closed-scope reference — line 2.1 is local to the closed subproof.
### if A is a closed formula.
### then A and A.

1. Let A be a closed formula. (Declaration)
2. A -> A. (Conditional Introduction from subproof below)
begin subproof
 2.1. A. (Assumption for Conditional Introduction)
 2.2. A. (Reiteration from 2.1)
end subproof
3. A and A. (Conjunction Introduction from 2.1, 2.1)
```

### `scope4` and `scope5`: appended to `red_team_Scope.txt` as #4 and #5

Both are refused by elaboration, so they have no refusing line: pin `case.parse_error`.

```
# 4: A label cannot be defined twice in one scope
## Invalid: duplicate label — line 2 is defined twice.
### if P is a closed formula such that: P.
### then P and P.

1. Let P be a closed formula such that: P. (Premise)
2. P. (Reiteration from 1)
2. P and P. (Conjunction Introduction from 1, 2)
```

```
# 5: A label inside a subproof cannot shadow a visible label
## Invalid: shadowed label — line 1 of the subproof reuses the label of the visible line 1.
### if A is a closed formula.
### then A -> A.

1. Let A be a closed formula. (Declaration)
2. A -> A. (Conditional Introduction from subproof below)
begin subproof
 1. A. (Assumption for Conditional Introduction)
 2.2. A. (Reiteration from 1)
end subproof
```

### Direct test for the witness in the cited existential

No end-to-end case can isolate this condition (the cited line is itself an outer line), and no test pins it directly today. Add beside the other `RuleContext` tests in `pytest_tests/test_core_red_team_reasons.py`; it fails when the check is removed.

```python
def test_existential_elimination_refuses_a_witness_named_in_the_cited_existential():
    existential = fl.Exists("x", atom("R", v("x"), c("w")))
    assumption = atom("R", c("w"), c("w"))
    conclusion = atom("Q", c("a"))
    subproof = pl.SubproofRecord(
        assumption,
        [assumption, conclusion],
        outer_context_ref=[],
        boundary_index=0,
    )
    reason = pl.ExistentialEliminationRule().explain_in_context(
        [existential, subproof], conclusion, pl.RuleContext()
    )
    assert reason is not None
    assert "occurs in the existential formula" in reason
```

## Refusal messages, as of master `045de51` with the entries above applied

For the second assertion of the pin tests. Pin the prefix (rule, formula and cited lines) and, where the last column has text, that reason too. Several cases print the same prefix (for example DE #2, #4 and #6, or UG #2 and #3): the prefix guards the line, rule, formula and cited lines, not the reason; the reasons need kernel explanations, which are Claude's to add.

### First-order classics (J16)

| Case | Line | Category | Prefix to pin | Reason text (pin too, if present) |
| --- | --- | --- | --- | --- |
| first_order_classics #14 | `6.2` | `rule_mismatch` | `'ExistentialElimination' does not justify (∃x. (P(x) ∧ Q(x))) from the cited line(s) ['4'] and attached subproofs` | `the witness w occurs in P(w), which was visible before the subproof opened; the witness w occurs in a hypothesis in force, P(w), so what the subproof derived may depend on it` |
| first_order_classics #15 | `3.2` | `rule_mismatch` | `'ExistentialElimination' does not justify R(c, b) from the cited line(s) ['3.1'] and attached subproofs` | `the witness b occurs in the conclusion` |
| first_order_classics #16 | `6` | `rule_mismatch` | `'ModusPonens' does not justify P(a) from the cited line(s) ['5', '4']` |  |
| first_order_classics #17 | `3` | `rule_mismatch` | `'UniversalInstantiation' does not justify (∃y. ¬y = y) from the cited line(s) ['2']` |  |
| first_order_classics #18 | `4` | `rule_mismatch` | `'ExistentialIntroduction' does not justify (∃x. R(x, x)) from the cited line(s) ['3']` |  |
| first_order_classics #34 | `2.1.5` | `rule_mismatch` | `'ModusPonens' does not justify P(c) from the cited line(s) ['2.1.4', '2.1.3']` |  |
| first_order_classics #35 | `3` | `rule_mismatch` | `'ModusTollens' does not justify ¬Q(a) from the cited line(s) ['2', '1']` |  |
| first_order_classics #36 | `2` | `rule_mismatch` | `'UniversalInstantiation' does not justify ((∀x. P(x)) ∨ (∀x. Q(x))) from the cited line(s) ['1']` |  |
| first_order_classics #37 | `2` | `rule_mismatch` | `'UniversalInstantiation' does not justify (∀x. P(x)) from the cited line(s) ['1']` |  |

### Red-team files (J17)

| Case | Line | Category | Prefix to pin | Reason text (pin too, if present) |
| --- | --- | --- | --- | --- |
| ConditionalIntroduction #2 | `2` | `rule_mismatch` | `'ConditionalIntroduction' does not justify (A() → B()) from the subproof immediately below this line` |  |
| ConditionalIntroduction #3 | `2` | `rule_mismatch` | `'ConditionalIntroduction' does not justify (A() → B()) from the subproof immediately below this line` |  |
| DisjunctionElimination #2 | `2` | `rule_mismatch` | `'DisjunctionElimination' does not justify R() from the cited line(s) ['1'] and attached subproofs` |  |
| DisjunctionElimination #3 | `(parse)` | `parse_error` | `ElaborationError: Line 2: this rule requires 2 subproof(s) below` |  |
| DisjunctionElimination #4 | `2` | `rule_mismatch` | `'DisjunctionElimination' does not justify R() from the cited line(s) ['1'] and attached subproofs` |  |
| DisjunctionElimination #5 | `2.2.case2` | `bad_reference` | `cites ['2.2.case1'], which is not defined or not in scope at this point in the proof` |  |
| DisjunctionElimination #6 | `2` | `rule_mismatch` | `'DisjunctionElimination' does not justify R() from the cited line(s) ['1'] and attached subproofs` |  |
| ExistentialElimination #2 | `4` | `rule_mismatch` | `'ExistentialElimination' does not justify Q(a) from the cited line(s) ['1'] and attached subproofs` |  |
| ExistentialElimination #3 | `4` | `rule_mismatch` | `'ExistentialElimination' does not justify Q(a) from the cited line(s) ['1'] and attached subproofs` |  |
| ExistentialElimination #4 | `4` | `rule_mismatch` | `'ExistentialElimination' does not justify Q(a) from the cited line(s) ['3'] and attached subproofs` |  |
| ExistentialElimination #5 | `3` | `rule_mismatch` | `'ExistentialElimination' does not justify a = a from the cited line(s) ['1'] and attached subproofs` | `the witness w occurs in the existential formula; the witness w occurs in (∃x. R(x, w)), which was visible before the subproof opened; the witness w occurs in a hypothesis in force, (∃x. R(x, w)), so what the subproof derived may depend on it` |
| ExistentialElimination #6 | `4` | `rule_mismatch` | `'ExistentialElimination' does not justify (∃x. P(x)) from the cited line(s) ['1'] and attached subproofs` | `the witness w occurs in w = w, which was visible before the subproof opened` |
| ExistentialElimination #7 | `3` | `rule_mismatch` | `'ExistentialElimination' does not justify (∃x. R(x)) from the cited line(s) ['1'] and attached subproofs` | `the witness w occurs in a hypothesis in force, R(w), so what the subproof derived may depend on it` |
| ExistentialIntroduction #2 | `2` | `rule_mismatch` | `'ExistentialIntroduction' does not justify (∃x. P(x)) from the cited line(s) ['1']` |  |
| ExistentialIntroduction #3 | `2` | `rule_mismatch` | `'ExistentialIntroduction' does not justify (∃x. P(x)) from the cited line(s) ['1']` |  |
| LeibnizSubstitution #2 | `5` | `rule_mismatch` | `'Substitution' does not justify Q(a) from the cited line(s) ['3', '4']` |  |
| LeibnizSubstitution #3 | `5` | `rule_mismatch` | `'Substitution' does not justify Q(c) from the cited line(s) ['3', '4']` |  |
| LeibnizSubstitution #4 | `5` | `rule_mismatch` | `'Substitution' does not justify R(b) from the cited line(s) ['3', '4']` |  |
| ProofByContradiction #2 | `2` | `rule_mismatch` | `'ProofByContradiction' does not justify A() from the subproof immediately below this line` |  |
| ProofByContradiction #3 | `2` | `rule_mismatch` | `'ProofByContradiction' does not justify B() from the subproof immediately below this line` |  |
| ProofByContradiction #4 | `2` | `rule_mismatch` | `'ProofByContradiction' does not justify ¬B() from the subproof immediately below this line` |  |
| Reiteration #2 | `3` | `rule_mismatch` | `'Reiteration' does not justify Q() from the cited line(s) ['2']` |  |
| Reiteration #3 | `3` | `bad_reference` | `cites ['2.1'], which is not defined or not in scope at this point in the proof` |  |
| Scope #2 | `3` | `bad_reference` | `cites ['2.1', '2.1'], which are not defined or not in scope at this point in the proof` |  |
| Scope #3 | `2` | `bad_reference` | `cites ['3'], which is not defined or not in scope at this point in the proof` |  |
| Scope #4 | `(parse)` | `parse_error` | `ElaborationError: Line 2: label '2' is already used earlier in this proof or an enclosing scope` |  |
| Scope #5 | `(parse)` | `parse_error` | `ElaborationError: Line 1: label '1' is already used earlier in this proof or an enclosing scope` |  |
| UniversalGeneralization #2 | `2` | `rule_mismatch` | `'UniversalGeneralization' does not justify (∀x. P(x)) from the subproof immediately below this line` |  |
| UniversalGeneralization #3 | `2` | `rule_mismatch` | `'UniversalGeneralization' does not justify (∀x. P(x)) from the subproof immediately below this line` |  |
| UniversalGeneralization #4 | `2` | `rule_mismatch` | `'UniversalGeneralization' does not justify (∀x. (∃y. P(y))) from the subproof immediately below this line` |  |
| UniversalGeneralization #5 | `2` | `rule_mismatch` | `'UniversalGeneralization' does not justify (∀x. P(x)) from the subproof immediately below this line` | `the generalized constant c occurs in a hypothesis in force, P(c), so what the subproof derived may depend on it` |
| UniversalGeneralization #6 | `3` | `rule_mismatch` | `'UniversalGeneralization' does not justify (∀x. P(x)) from the subproof immediately below this line` | `the generalized constant c occurs in a hypothesis in force, (∀u. (In(u, Y) ↔ (In(u, X) ∧ u = c))), so what the subproof derived may depend on it` |
| UniversalInstantiation #2 | `2` | `rule_mismatch` | `'UniversalInstantiation' does not justify R(a, b) from the cited line(s) ['1']` |  |
| UniversalInstantiation #3 | `2` | `rule_mismatch` | `'UniversalInstantiation' does not justify Q(a) from the cited line(s) ['1']` |  |
| UniversalInstantiation #4 | `2` | `rule_mismatch` | `'UniversalInstantiation' does not justify P(a) from the cited line(s) ['1']` |  |

### Equivalence classes (J18)

| Case | Line | Category | Prefix to pin | Reason text (pin too, if present) |
| --- | --- | --- | --- | --- |
| equivalence_classes #7 | `3` | `rule_mismatch` | `'RelationSymmetry' does not justify R(b, a) from the cited line(s) ['2']` |  |
| equivalence_classes #8 | `7.6` | `rule_mismatch` | `'RelationTransitivity' does not justify R(b, u) from the cited line(s) ['2', '7.5']` |  |
| equivalence_classes #9 | `7.8` | `rule_mismatch` | `'SetProperty' does not justify In(u, D) from the cited line(s) ['6', '7.7']` | `the cited instance must match the full defining property or a permitted disjunct in the allowed direction` |

