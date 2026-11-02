# SyLoPy: state of the project

**Snapshot of 2026-11-01.** `master` is at `5efa1fc` (the merge of PR #150; PR
#149, which retired generic `(Axiom)` for set theory, merged a few seconds
earlier). One pull request is open, #148 (section 14). The figures in this file
were measured on that commit with the commands in section 17. Sections 11 and 14
go stale with every merge; the rest changes slowly.

This file is a map and a dated snapshot. It does not replace the documents it
points to. Where it disagrees with the code, or with the document that owns the
subject, the code and that document win, and this file should be corrected in
the same pull request that makes the difference visible.

| If you need | Read |
| --- | --- |
| What the checker accepts, and how to call it | `README.md`, `docs/PROOF_FILE_FORMAT.md` |
| Architecture invariants and extension points | `ARCHITECTURE_STATUS.md`, `ELABORATION_ARCHITECTURE.md` |
| Decisions, open design questions, owner approvals | `todos.txt` |
| Delegated work and the rules for it | `JOBS_FOR_CHATGPT.md`, `AGENT_COLLABORATION.md` |
| The proposed refinement type system (not implemented) | `TYPE_SYSTEM_DESIGN.md` |
| Everything in one place, as of the snapshot | this file |

Contents: 1 What SyLoPy is · 2 Who does what · 3 Status at a glance · 4 How a
proof is checked · 5 Source tree · 6 The kernel · 7 Inference rules ·
8 Theories · 9 The surface language · 10 Theorems, WLOG and Mutatis mutandis ·
11 Verification · 12 Workflow and conventions · 13 Decisions · 14 Work in
flight and what comes next · 15 Known limits · 16 Glossary · 17 Commands, and
how to resume.

## 1. What SyLoPy is

SyLoPy checks Fitch-style natural-deduction proofs. A proof is written as text
in a near-natural-language syntax (`3. C(a). (Modus Ponens from 1, 2)`,
`Let X be any set.`, `A is a subset of B.`). The text is parsed into a surface
syntax tree, elaborated into a small strict entry language, and validated line
by line by a kernel that knows nothing about text.

The owner's aim is a composable, mathematically serious verifier for many
subjects: basic logic, set theory, number theory, and later real analysis,
abstract algebra, topology and linear algebra. Each subject is a module that
extends the base and may import other modules (number theory imports set theory
and the natural numbers). Nothing about a subject is built into the kernel. A
theorem, once proved, becomes an inference rule that later proofs cite by
title, as in mathematical practice. New syntax and its meaning should be a
matter of registering them with a theory environment, not of editing the parser
or the kernel.

Commitments that shape the code:

- **Prefer sugar.** Surface syntax lowers to existing formulas, declarations and
  proof steps. The kernel or the formula AST changes only for a genuinely new
  logical behaviour. (`exists unique` is sugar, not a connective.)
- **Facts must be visible.** Whatever a proof relies on that says something
  about a symbol reaches validation as a hypothesis, an ordinary formula, or
  declaration metadata. No separate type or elaboration mechanism may justify a
  step by itself.
- **The kernel owns soundness.** Elaboration may refuse or rewrite text, but the
  kernel re-validates every line it receives. `Mutatis mutandis` and WLOG are
  expanded into ordinary lines and validated like any other, so a wrong
  alignment can only cause a refusal, never accept a false line.
- **Target proofs first.** Write the proof you want to be able to write, then
  implement the syntax and rules that make it pass.
- **Set theory is the root.** Number theory depends on set theory, not the other
  way round.
- **Interface stability is not a goal.** Proof-file format, entry shapes and
  function signatures change when the project needs it.
- **Multi-proof files share no lexical context.** Reuse across proofs is
  explicit: a titled proof is promoted to a theorem rule and cited by title.

## 2. Who does what

| Who | Role |
| --- | --- |
| Owner (Axiom, GitHub `axiomtutor`) | Final authority on priorities and semantics. Answers the owner-gated questions (section 13). Merges every pull request. |
| Claude (Claude Code sessions) | Owns the kernel, `source/ProofLogic.py` and `source/ProofJustification.py`. Designs and implements features in the order the owner approved, one at a time. Reviews other pull requests. Writes jobs for ChatGPT. Opens pull requests; never merges. |
| ChatGPT | Works from `JOBS_FOR_CHATGPT.md`: parser and elaboration maintenance, parse-oracle cases, fixture and red-team proofs, documentation housekeeping. Does not edit the kernel files without coordination, and does not change an existing test or fixture expectation to make something pass. |

All pull requests show `axiomtutor` as their author; the branch prefix says who
wrote the change (`claude/...` or `chatgpt/...`). Commits by Claude carry the
identity `Claude <noreply@anthropic.com>`.

## 3. Status at a glance

| Area | State | Where to look |
| --- | --- | --- |
| Propositional and first-order logic with equality | Implemented: 25 base rules (15 propositional, 6 quantifier, 4 equality). Arbitrary-object and freshness side conditions, substitution capture guards, source-mapped errors. Covered by classics and red-team jobs J3, J16, J17, J24 and J26. | `tests/testProofs` (235 cases), `pytest_tests/test_rules_*.py` |
| Surface language | Implemented: coordinated `Let` declarations with typed descriptors, explicit and inferred subproofs, comments, named and numbered citations, titled multi-proof files. | `docs/PROOF_FILE_FORMAT.md` |
| Set theory | Implemented: Pairing, Union, Power Set and Infinity cited by name and only by name (restating one with `(Axiom)` is refused, with the name to cite); Separation and Replacement schema rules; `Set property`, `Set equality`; unique existence; scoped witnesses; WLOG for equalities; `Mutatis mutandis`. Not yet: set operations as terms, functions, products, the finite/infinite semantics. | section 8.1 |
| Number theory and the naturals | Implemented, deliberately thin: `Int` and `Nat`, 12 axioms, divisibility and quotient notation, induction. No arithmetic beyond the documented laws; no type errors yet for divisibility. | section 8.2, issue #98 |
| Discrete mathematics | Implemented: relation declarations (a relation on X states `R ⊆ X × X`), seven relation-property rules, order and equivalence examples. | section 8.3 |
| Theorem reuse | Implemented within a file: a checked proof is promoted to a rule carrying its premises, required axioms and required rules. Promotion generalizes top-level object declarations only. | section 10 |
| Type system | Design proposal only (`TYPE_SYSTEM_DESIGN.md`). `Let n be an integer` states the formula `Int(n)`; nothing type-checks. | section 15 |
| Real analysis, abstract algebra, topology, linear algebra | Not started. The owner said "not right now, but later" (2026-10-30). | section 13 |

## 4. How a proof is checked

```text
proof text
  -> ProofParser.parse_proof_text      surface syntax tree with source spans
  -> elaboration                       theory environment: parsers, recipes, elaborators
  -> ElaboratedEntries                 a list of core entries + origin map + required rules/axioms/declarations
  -> ProofLogic.Proof(...).check_detailed()      (ok, ValidationError | None)
```

`ProofParser.check_proof_text(text, environment=..., premises=..., axioms=...,
rules=..., declarations=..., theorem_names=...)` runs all of it and returns
`(ok, error)`. The stages are also public: `parse_proof_text` returns
`(ElaboratedEntries, raw_lines)`; `Proof(entries, premises=, axioms=, rules=,
declarations=)` validates, merging the rules, axioms and declarations that the
elaborated entries require.

A small proof and what it becomes (output of `parse_proof_text`, shown
schematically):

```text
1. Let P, Q be closed formulas. (Declaration)     declare   P, Q   (closed_formula)
2. P -> Q. (Premise)                              premise   (P → Q)
3. P. (Premise)                                   premise   P
4. Q. (Modus Ponens from 2, 3)                    rule      ModusPonensRule, cites 2, 3
```

Citing the wrong lines (`from 3, 3`) is refused with category `rule_mismatch`:
`Line 4: 'ModusPonens' does not justify Q() from the cited line(s) ['3', '3']`.
(A zero-argument formula prints as `Q()`.)

Two kinds of error exist. An `ElaborationError` is raised while the text is
translated and carries a source span ("Line 3: Unrecognized formula syntax:
..."). A `ValidationError` comes from the kernel and has a bare line `label`, a
`category` (the `CATEGORY_*` constants, section 6) and a message; because the
origin map survives elaboration, an error on a synthetic core step is reported
against the surface line that produced it.

## 5. Source tree

`source/` is 14,111 lines. At import time the dependencies run downward: the
kernel imports only `FormulaLogic` and `TermLogic`, and the theory modules
import the kernel and `ProofElaboration`, not the parser. Two imports go the
other way, lazily and inside functions, to avoid a circular import:
`NatThry` and `NumberTheory` import `ProofParser` when they build their
parsers, and `ProofParser` imports `SetTheory` when it builds the default
environment.

| File | Lines | Role |
| --- | ---: | --- |
| `TermLogic.py` | 141 | Terms: `ConstantTerm`, `VariableTerm`, `FunctionTerm`. |
| `FormulaLogic.py` | 385 | Formulas: `AtomicFormula`, `And`, `Or`, `Not`, `Implies`, `Iff`, `Equals`, `ForAll`, `Exists`. Formula `==` is object identity; structural comparison is `ProofLogic._ast_eq`. |
| `ProofLogic.py` | 5,812 | **The kernel** (Claude owns it): entry language, `InferenceRule` and every base rule, `ProofValidator`, `Proof`, declarations and scopes, `TheoremRule` and `promote_theorem`, WLOG and `Mutatis mutandis` expansion, `ValidationError`. |
| `ProofJustification.py` | 239 | **Kernel-owned.** Turns justification text (`Modus Ponens from 2, 3`) into a rule citation, through alias tables and placeholders for theory rules and theorem titles. |
| `ProofElaboration.py` | 272 | Data types shared by parser and theories: surface AST, `SourceSpan`, `ElaboratedEntries`, `ElaborationError`, `TheoryEnvironment`. |
| `ProofContext.py` | 350 | Elaboration-time lexical scope (declarations, labels, assumptions, arbitrary bindings). The kernel does not use it. |
| `ProofParser.py` | 2,017 | Parser and elaborator; the public entry points (`parse_proof_text`, `check_proof_text`, `elaborate_proof`, `default_theory_environment`). |
| `ProofParserPolicy.py`, `LineBreakSyntax.py` | 636, 125 | Language-policy and line-break syntax extensions installed on the parser. |
| `SetTheory.py` | 2,396 | Set vocabulary (`In`, `EmptySet`), set syntax and sugar, set rules, the four axiom citations. |
| `NatThry.py` | 176 | The naturals as the first `Type`: `Nat`, `Zero`, `Succ`, induction. |
| `NumberTheory.py` | 520 | Integers on top of `NatThry` and `SetTheory`: `Int`, `Plus`, `Times`, `Neg`, `Quotient`, divisibility and parity sugar, two quotient rules. |
| `DiscreteMath.py`, `DiscreteMathCore.py` | 138, 346 | Relation declaration recipe, and the seven relation-property rules. |
| `validate_all_proofs.py` | 520 | The fixture runner: multi-proof files, theorem promotion in order, reporting. |
| `test_runner_NatNum.py` | 26 | Compatibility command that delegates to the fixture runner. |

Outside `source/`:

| Path | Contents |
| --- | --- |
| `pytest_tests/` | 73 test files, about 18,100 lines; the Python test suite. |
| `tests/` | Enforced proof fixtures (six suites) and the informational `tests/setTheoryProofs`. |
| `source/testProofs/` | Informational fixtures (five files). |
| `parse_oracle/` | 15 files, 245 cases: surface text and the plain-logic formula it must elaborate to, with a `why`. Checked by `pytest_tests/test_parse_oracle.py`. |
| `job_seeds/` | Seed proofs and a mutant spec that jobs J16, J18, J19 and J20 started from (cited in `docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`). Historical. |
| `tools/mutation_check.py` | Mutation checker: applies small source mutations and reports which a test command fails to detect. |
| `docs/` | `PROOF_FILE_FORMAT.md` (executed by tests) and `docs/archive/` (finished job specifications; history, not guidance). |
| `run_tests.sh`, `completion/` | Test runner and Bash completion. |
| `.github/workflows/test.yml` | CI (section 11). |

## 6. The kernel

### 6.1 Entries and justifications

A `Proof` is a list of entries. An entry is a line `(label, formula, justification)`,
a line that opens an inline subproof `(label, formula, justification, nested_entries)`,
or a standalone subproof block `(label, 'subproof', nested_entries)`. The module
docstring of `source/ProofLogic.py` is the authoritative description. The
justification tags are:

| Tag | Meaning |
| --- | --- |
| `('premise',)`, `('premise', [declarations])` | The formula is taken as a premise. The second form is a declaration line that also states a formula (`Let n be an integer` states `Int(n)`; `Let R be a relation on X` states `R ⊆ X × X`). |
| `('axiom',)` | The formula is cited as an axiom (section 6.3). |
| `('declare', [declarations])` | Symbols are introduced; no formula is stated. |
| `('assume',)`, `('arbitrary',)` | Opens a subproof: an assumption or case, or a fresh arbitrary object. Must be the first line of its subproof. |
| `('rule', rule, [labels])` | Derived by `rule` from the cited earlier lines. An optional fourth item lists declarations made visible at that line. |
| `('rule_below', rule)` | Derived from the subproof written immediately below: Conditional Introduction, Proof by Contradiction, Universal Generalization. |
| `('rule_hybrid', rule, [labels])` | Derived from cited lines plus the subproofs below: Proof by Cases, Existential Elimination. |

### 6.2 Validation

`ProofValidator` walks the entries top to bottom. It keeps a `LabelScope`
(label to formula or `SubproofRecord`; a closed subproof's labels disappear, as
in Fitch) and a `DeclarationScope` (lexical; a declaration is visible at its
level and in descendant subproofs; shadowing is forbidden). Every symbol used
must be declared, with the declared kind and arity; an undeclared symbol, a kind
mismatch and an arity mismatch are refused. (A symbol declared without an arity,
such as `Let f be a function`, accepts any number of arguments.)

An `InferenceRule` has one required method, `applies(candidates, phi)`, a pure
predicate over formulas the validator has already accepted. A rule that is sound
only relative to the rest of the proof implements `applies_in_context` instead
and receives a `RuleContext`: `hypotheses` (premises, `(Axiom)` lines,
formula-stating declarations, witness lines and the open assumptions),
`arbitrary_constants`, `declaration(name)`, `lists_axiom` and `allows_rule`. It
may also implement `explain_in_context`, whose reason is appended to the refusal.
`Uniqueness`, `Universal Generalization` and `Existential Elimination` use the
context to check that the constant they treat as arbitrary occurs in no
hypothesis in force and is not named by any declaration's metadata. The
invariant, from `ARCHITECTURE_STATUS.md`: whatever the proof relies on that says
something about a constant must reach the context, as a recorded formula or as
declaration metadata; a fact a rule reads from anywhere else makes that rule
unsound for the constant.

Authorization of a rule compares its configuration, not its class or name
(`InferenceRule.same_configuration`): induction over `Int` is not induction over
`Nat`, and an unregistered subclass is not its parent. `Proof` and promotion
merge rule lists by the same test.

### 6.3 Premises, axioms, declarations

- A `Proof` may be given `premises`, `axioms`, `rules` and `declarations`; the
  required rules, axioms and declarations carried by `ElaboratedEntries` are
  merged in. Conflicting built-in declarations for one symbol raise `ValueError`.
- An `(Axiom)` line may state only what the proof's axiom list holds, and a
  non-empty list closes itself. **A proof given no axioms at all accepts any
  formula as an axiom** (a bare proof), unless its theory closed the list:
  `TheoryEnvironment.axioms_closed` is carried through `ElaboratedEntries` and
  `Proof` to `ProofValidator`, where `axioms_closed` is the one place the question
  is answered (the axiom check, the record of which axioms a proof used, and the
  validators that replay a WLOG block). Set theory lists no axiom for `(Axiom)`
  and closes the list, so in set theory an `(Axiom)` line is refused whatever it
  states, and the four set axioms are cited by name (PR #149, merged
  2026-11-01). A refused `(Axiom)` line says which rules of the proof justify the
  formula outright (`cite it by name instead: (Axiom of pairing)`; a rule's
  `citation` is the phrase a proof writes when it differs from the rule's
  `name`). A theory that extends another does not reopen a closed list. The
  default environment lists 12 axioms (the naturals and integers, section 8.2)
  and is closed.
- Declarations carry `name`, `kind` (`object`, `predicate`, `closed_formula`,
  `function`), `arity`, a descriptive `type_name` and structure `metadata` (a
  relation's carrier and properties). The kernel does not interpret metadata,
  but it reads which names it mentions when it decides what may be generalized.

### 6.4 Errors

`check_detailed()` returns `(ok, ValidationError | None)`; `check()` returns
`(ok, message)`. A `ValidationError` has the bare offending `label`, a
`location`, a message and one of 19 categories:

| Group | Categories |
| --- | --- |
| Structure of the entries | `malformed_entry`, `not_closed`, `unknown_tag`, `wrong_position`, `bad_opening`, `empty_subproof`, `missing_subproof` |
| Justifications and citations | `malformed_justification`, `unrecognized_rule`, `arity_mismatch`, `bad_reference`, `label_shadowing`, `unregistered_formula` |
| Rules | `rule_mismatch` (a real rule that does not license the line), `rule_raised` (the rule crashed; the fixture runner reports it as an implementation error) |
| Vocabulary | `undeclared_symbol`, `declaration_conflict`, `declaration_kind_mismatch`, `declaration_arity_mismatch` |

Tests pin refusals by line, category and reason fragment, so a negative test
fails for the reason it names and not for an unrelated one.

## 7. Inference rules

Forty-five distinct rule names are available in the default environment.

| Group | Rules |
| --- | --- |
| Propositional (15) | Conjunction Introduction, Conjunction Elimination, Disjunction Introduction, Disjunction Elimination (Proof by Cases), Biconditional Introduction, Biconditional Elimination, Conditional Introduction, Modus Ponens, Modus Tollens, Disjunctive Syllogism, Hypothetical Syllogism, Proof by Contradiction, Explosion, Reiteration, Propositional Equivalence (De Morgan, double negation, distribution and similar) |
| Quantifier (6) | Universal Instantiation, Universal Generalization, Universal Modus Ponens (instantiation and modus ponens in one step), Existential Introduction, Existential Elimination, Uniqueness |
| Equality (4) | Reflexivity, Symmetry, Transitivity, Substitution (Leibniz) |
| Decision procedure (1) | Algebra: finds a chain of equalities among cited lines by congruence closure |
| Set theory (9) | Empty set property (bare `Set property`), Set property (general, with cited lines), Set equality, Axiom of pairing, Axiom of union, Axiom of power set, Axiom of infinity, Axiom schema of separation, Axiom schema of replacement |
| Naturals (1) | Induction |
| Number theory (2) | Quotient defining property, Quotient uniqueness |
| Discrete mathematics (7) | Relation reflexivity, irreflexivity, symmetry, antisymmetry, asymmetry, transitivity, totality |

Also citable, but not entries in the rule registry: `WLOG` and `Mutatis mutandis`
(the validator expands and re-validates them, section 10); a promoted theorem's
title; and two surface sugars, `Subset proof below` (elaborated into Universal
Generalization and Conditional Introduction) and `Let Y be such a set.
(Existence from L)` (a scoped witness declaration). Canonical spellings and
aliases are in `docs/PROOF_FILE_FORMAT.md`, section 7; a test
(`test_proof_format_doc_covers_rules.py`) fails when a rule is missing from it.

## 8. Theories

### 8.0 Theory environments

A `TheoryEnvironment` (`source/ProofElaboration.py`) bundles what a subject adds:
formula parsers, nested-formula parsers, phrase parsers and phrase-span finders
(for phrases containing connective words, "x is a or b"), term parsers, line
elaborators, declaration recipes, rules, axioms and declarations. `extended()`
composes environments; adding a structure should normally mean adding a recipe
and rules to a theory module, not changing generic elaboration.

| Environment | Adds |
| --- | --- |
| `SET_THEORY_ENVIRONMENT` | 9 rules (four are the axiom citations), `In` and `EmptySet`, set syntax. No axiom for `(Axiom)`, and the list is closed |
| `NUMBER_THEORY_ENVIRONMENT` | includes set theory; 12 own axioms, 3 rules, `Int`, `Nat`, `Even`, `Odd`, `Plus`, `Times`, `Neg`, `Quotient`, `Succ`, `Zero`, two declaration recipes |
| `DISCRETE_MATH_ENVIRONMENT` | 7 rules and the relation declaration recipe |
| `default_theory_environment()` (used when none is passed) | all of the above, 12 axioms, closed. Its name shows how it is composed: base logic + set theory + number theory + set theory + discrete mathematics + base logic. The lists therefore hold repeats (29 rule objects, 20 distinct); `Proof` merges duplicates by configuration, so behaviour is unaffected. The function also tries to import an `OrderTheory` module that does not exist and swallows the `ImportError` |

The `Use discrete math.` directive is validated and accepted, but it does not
select an environment: the default environment still loads every theory. Making
directives strict needs the corpus updated first (`ARCHITECTURE_STATUS.md`).

### 8.1 Set theory

- **Vocabulary.** `In` and `EmptySet`. The only set terms are names and `∅` /
  "the empty set". There is no term for a union, a pair, a power set or a
  product.
- **ZFC coverage.** Pairing, Union, Power Set and Infinity are cited by name and
  only by name (`Axiom of pairing`, `Axiom of union`, `Axiom of power set`,
  `Axiom of infinity`); each rule checks the shape of the instance the proof
  writes (the Union and Power Set instance forms are supported), and does not
  introduce a witness by itself. Separation and Replacement are schema
  rules (the property ranges over formulas, which the theory cannot quantify
  over). Extensionality's substantive direction is `Set equality` (two subset
  proofs give `X = Y`); the other direction is equality's substitution.
  Foundation and Choice have no rule.
- **Sugar.** All of it lowers to ordinary formulas: `A is a subset of B`,
  `X subseteq Y`, displays (`{a, b}`, `{u in X: P(u)}`, `{y: P(y)}`,
  `{F(x): x in X}`) next to a relation (`Y = {a, b}`, `x is in {a, b}`),
  `x is a or b`, `S contains exactly a, b and c`, bounded quantifiers
  (`forall a in X, P(a)`), negative forms such as `x is not in A`,
  `there exists a unique set ...`, and a fixed list of union, intersection and
  disjointness phrases (`x is in the union of A and B`, `x belongs to A union B`,
  `x belongs to the intersection of A and B`, `A is the union of B and C`,
  `A is disjoint from B`, `A and B are disjoint`; the last is refused as a whole
  premise line, issue #151). A display is not a term and is accepted nowhere else
  (as a function argument, say). The code's stated reason is that a function
  symbol for "the pair of a and b" has to wait until a proof has derived the
  pair's existence and uniqueness and promoted it; the owner's decision to declare
  function symbols and make set operations terms (2026-10-30) is what will lift
  this restriction (section 14.5).
- **Reasoning tools.** `Set property` uses a set's membership characterization
  and an explicitly matching instance (the checker never guesses the target
  term); `Set equality`; `Uniqueness`; scoped witnesses (`Existence from L`);
  WLOG and `Mutatis mutandis`.
- **Not yet.** A symbolic defining property for a set with no explicit
  characterization; the finite/infinite semantics for the Infinity axiom (owner
  intent: the set `I` has an abstract membership property, being infinite is a
  separate fact about `I`, finite means a bijection with `{0, ..., n-1}`);
  functions; ordered pairs and products.
- **Fixtures.** `tests/testSetTheory` (59 cases, including the nine of
  `axioms_cited_by_name.txt`), `tests/setTheoryProofs` (44, informational;
  includes `zfc_remaining_axioms.txt`, the worked ZFC proofs).

### 8.2 Number theory and the naturals

- **Vocabulary.** Predicates `Int`, `Nat`, `Even`, `Odd`; functions `Plus/2`,
  `Times/2`, `Neg/1`, `Quotient/2`, `Succ/1`; constant `Zero`.
- **Twelve axioms.** `Nat` is inside `Int`; `Int` is closed under `Plus`, `Times`
  and `Neg`; the quotient's defining property and uniqueness; associativity of
  `Times`; left distributivity of `Times` over `Plus`; `Nat(Zero)`, closure of
  `Nat` under `Succ`, `Succ(x) ≠ Zero`, `Succ` injective. Each of the two ring laws
  was added because a specific proof needed it. Number theory deliberately
  supplies only its documented laws: no commutativity, multiplicative identity,
  annihilator or `Neg`-`Times` law. Issue #98 lists the proofs this blocks and is
  an owner decision list, not authorization to add axioms.
- **Sugar.** `a|b` becomes `exists m, (Int(m) and b = Times(a, m))`; `n/a` becomes
  `Quotient(n, a)`; parity phrases for `Even` and `Odd` (compound subjects
  accepted, ambiguous shorthand under quantifiers refused); typed declarations
  (`Let n be an integer` states `Int(n)`, `a natural number` states `Nat(n)`).
- **Notation.** There is no infix arithmetic: a sum is written `Plus(a, b)`.
- **Rules.** `Induction` (configured per type), the two quotient rules, `Algebra`.
- **Fixtures.** `tests/testNumberTheory` (16), `tests/testProofsNat` (6),
  `tests/testProofsDeclared` (12).

### 8.3 Discrete mathematics

`Let R be a (reflexive, symmetric, ...) relation on X` declares `R` as a binary
predicate whose declaration records its carrier and property labels as metadata,
and states `forall x, forall y, (R(x, y) -> (In(x, X) and In(y, X)))` as a formula
of the line (owner decision, 2026-10-29: a relation is a subset of `X × X`). The
descriptors `equivalence relation`, `partial order` (`poset`), `strict partial
order`, `total order` (`linear order`) and the seven property words are
recognized. The rules that start from a fact `R(a, b)` (symmetry, antisymmetry,
asymmetry, transitivity) read only the declared property; the rules that start
from membership (reflexivity, irreflexivity, totality) also require the declared
carrier. A known gap: in a comma list the words `irreflexive`, `asymmetric` and
`total` are refused after the first word, so `a transitive, asymmetric relation`
cannot be declared (issue #152). Fixtures: `tests/testDiscreteMath` (65 cases,
including equivalence classes, partitions and order proofs).

## 9. The surface language

The complete reference is `docs/PROOF_FILE_FORMAT.md`, whose complete examples are
executed by tests. In outline:

- A line is `LABEL. FORMULA. (JUSTIFICATION)`. Labels are dotted
  (`2.1.case1.`); dotted descendants delimit implicit subproofs, and explicit
  subproofs use `begin subproof` / `end subproof`. Comments are `(* ... *)`.
- Justifications: `Premise`, `Axiom`, `Declaration` / `Declare`,
  `Assumption ...`, `Reiteration`, `Reflexivity`, a rule name with citations
  (`Modus Ponens from 2, 3`, `Modus Ponens, 2, 3`, `from 2 and 3`, `from 2 to 4`),
  `from subproof below`, `from 2, subproofs below`, a named theory rule with no
  citation (`Axiom of pairing`), or a theorem title with the lines that state its
  premises. A range supplies its two endpoint labels only.
- Formulas: `and`, `or`, `not`, `->`, `<->` / `iff`, `forall`, `exists` (several
  variables with `such that:`), equality, bounded quantifiers.
- Declarations: coordinated clauses (`Let X be any set, a be in X, R be a
  relation on X.`) elaborated by registered declaration recipes. A declaration
  line is one sentence; two `Let` sentences on one line are refused (job J30).
- Fixture files: `# N: title` starts a case, `## Proof that` marks it
  expected-valid, `## Invalid ...` expected-invalid, `### then ...` states the
  conclusion the proof must derive. A file with no `# N` header is one bare
  proof, expected invalid when its file name contains "invalid".

## 10. Theorems, WLOG and Mutatis mutandis

### 10.1 Theorem promotion

`ProofLogic.promote_theorem(name, proof, ...)` turns a checked proof into a
`TheoremRule` that later proofs cite by title. The theorem carries every
hypothesis its proof took for granted (premise lines at any depth, declarations
that state a formula, witness lines) as premises; it records the axioms the proof
cited and the non-standard rules it used (`required_axioms`, `required_rules`)
and can be cited only where the citing proof lists those axioms and allows those
rules. An explicit conclusion must have been derived at the top level.
**Generalized names are the objects the proof declared at its top level.** A
witness named by a top-level `Existence from L` is generalized by default, with
its defining formula carried as a premise (owner decision of 2026-10-31: no
change). Promotion refuses a proof that relies on structure recorded in a
declaration and stated by no formula (a relation declared symmetric): state the
property as a premise formula instead (the warning cites `todos.txt` item 8, which
no longer exists; the topic is owner decision 6, section 14.4). The fixture runner
promotes each valid titled proof in order, locally to its file, and prints
"was not promoted" with the reason when it cannot. A theorem rule can be passed
to `check_proof_text(rules=...)`, but nothing stores or imports promoted
theorems across files or modules. Function and predicate symbols are not
generalized (section 15).

### 10.2 WLOG

`N. <the chosen disjunct>. (WLOG, M)` cites a disjunction `M`. The checker
validates the proof for the chosen case, then replays the rest of the current
block with the case's constant exchanged for each alternative, re-validating
every line and remapping citations without mutating the original; nested case
blocks are included. Outside citations need a visible counterpart unless
exchanging the constants leaves the cited fact invariant (up to commutative
ordering of `and` / `or`). **Only equality alternatives that differ in exactly
one constant are supported** (`x = a or x = b`). Extending it to arbitrary
properties (`a <= b or b <= a`) is approved and is the next feature (section 14.4).

### 10.3 Mutatis mutandis

`P'. (Mutatis mutandis, B)` and `P'. (Mutatis mutandis, A to B)` say that line `B`
(started at line `A`) was derived by an argument that works as well for other
names, terms or symbols, and that `P'` is what `B` says with them. The checker
reads what is replaced off the two statements, expands the argument, and
validates the expansion like any other lines. Stage 1 replaces a name by a name; stage 2 a name
by a term with no variable in it; stage 3 a predicate or function symbol by
another of the same arity (never `=`, a connective or a quantifier). Premises,
assumptions, witness lines, axiom citations, structure declarations and
unsupported justifications cannot be repeated. A refused substitution that would
capture a variable is `_UnsafeSubstitution`; there is no alpha-renaming. **Not
supported, and not wanted for now (owner, 2026-10-30):** repeating a closed block
of several lines, and counterparts that differ by the symmetry of `=` or `<->`.

### 10.4 Existence, uniqueness, witnesses

`Uniqueness` combines an existence formula with a conditional that every object
with the property equals the witness; the result is the ordinary formula
`exists W, (B(W) and forall V, (B(V) -> V = W))`, and the rule is context-sensitive
because soundness depends on `c` being genuinely arbitrary. A witness is named by
`Let Y be such a set. (Existence from L)`, which declares `Y` and states the
existential body in scope; it is not an axiom citation. The older direct Pairing
witness form remains for compatibility and must not be extended.

## 11. Verification

### 11.1 What runs

`./run_tests.sh` is the one command. It runs, in order: the pytest suite under
coverage (`pytest_tests/`, 73 test files), a coverage gate, and the fixture validator
`source/validate_all_proofs.py`; it exits 0 only if all three pass.
`./run_tests.sh --list-suites` and `./run_tests.sh --suite NAME [--verbose]` pass
their arguments to the fixture validator. The code imports itself as
`SyLoPy.source...`; the runner and `pytest_tests/support.py` make that work
whatever the checkout directory is called.

CI (`.github/workflows/test.yml`) runs on every pull request to `master` and on
pushes to branches whose name has no slash (the pattern is `'*'`, which does not
match `/`); a push that changes only `*.md` files or `todos.txt` is skipped. The
`claude/...` and `chatgpt/...` branches therefore run on their pull request only:
of the 100 most recent runs, 91 are pull-request runs on such branches and 9 are
pushes to `master`. It is one job on `ubuntu-latest` that installs
`requirements-test.txt` (`pytest>=8`, `coverage>=7`) and runs `./run_tests.sh`.
There is no version matrix: CI uses the runner's default `python3`. Local
verification of a change uses Python 3.12 and 3.13.

### 11.2 The proof corpus

Every fixture case is a proof with an expectation (valid, or invalid for a named
reason). The runner parses each file with the default theory environment and
validates each case with the base rules, the set, `Nat` and `Int` rules, and the
`Nat` and `Int` axioms and declarations; titled valid proofs are promoted in
order, so later cases can cite them. **Enforced** suites must behave as expected
or the run fails. **Informational** suites are reported and never fail the
runner, and each needs a pytest test that reports every unexpected result.

| Suite | Cases | Valid | Invalid | Notes |
| --- | ---: | ---: | ---: | --- |
| `tests/testProofs` (enforced) | 235 | 121 | 114 | propositional and first-order logic, quantifier and scope red-teaming, equivalence classes, `Mutatis mutandis`, uniqueness |
| `tests/testDiscreteMath` (enforced) | 65 | 37 | 28 | relations, order and equivalence, the relation-subset fact |
| `tests/testSetTheory` (enforced) | 59 | 22 | 37 | set rules, red-team cases, WLOG pairing proofs, axioms cited by name |
| `tests/testNumberTheory` (enforced) | 16 | 14 | 2 | closure, divisibility, composition |
| `tests/testProofsDeclared` (enforced) | 12 | 6 | 6 | declarations |
| `tests/testProofsNat` (enforced) | 6 | 2 | 4 | naturals and induction |
| `tests/setTheoryProofs` (informational) | 44 | 43 | 1 | worked set-theory proofs, including `zfc_remaining_axioms.txt` |
| `source/testProofs` (informational) | 56 | 43 | 13 | older examples |
| **Total** | **493** | **288** | **205** | enforced 393, informational 100 |

The `parse_oracle/` files (245 cases) pin the surface-to-formula step
independently of the parser: each case has `surface:`, `expect:` (the intended
plain-logic reading) and `why:`. A disagreement is investigated, not resolved by
weakening the oracle.

### 11.3 Practices that a change is expected to follow

- **Negative tests must fail for the reason they name.** A refusal is pinned by
  line, category and a reason fragment in a `*_reasons.py` test, never only by
  "does not justify". Every invalid case has a valid twin that differs from it
  only in the condition its title names.
- **Mutation checks.** New tests are checked with `tools/mutation_check.py SPEC.json
  --tests "..."`, where the spec lists `{id, file, old, new}` mutations (`old`
  must occur exactly once). Outcomes are KILLED, SURVIVED, PATTERN or TIMEOUT. A
  survivor gets a test, or the pull request says why the mutant is equivalent.
- **Findings, not weakened tests.** A checker defect found while writing tests is
  filed as an issue with the smallest proof, the exact accepted or rejected
  behaviour, the suspect rule and file, and `Owner: Claude` when the kernel is
  involved; an invalid proof that is accepted gets a strict expected-failure
  case. Existing tests, fixtures and oracle expectations are not changed to make
  a change pass.
- **Verification record in the pull request.** The tested commit; local suite
  totals on 3.12 and 3.13 (and that the tested tree is the committed tree); the
  CI run number on the PR head; enforced and informational fixture totals; any
  remaining failure. Do not report totals from a run that was not inspected. A CI
  run on a PR head is not a run on the merge commit.

### 11.4 Snapshot (2026-11-01)

Measured on `master` at `5efa1fc` plus this file, with the commands in section 17.

| Measure | Value | Source |
| --- | --- | --- |
| Python tests | 2,148 collected; 2,147 pass, 1 expected failure | `./run_tests.sh` on Python 3.12.3 (126 s) and 3.13.16 (95 s); `pytest --collect-only` |
| Coverage gate | passes; 91% of 6,282 statements in `source/` | Python 3.13.16, same tree |
| Coverage by file | `ProofLogic` 93%, `ProofJustification` 99%, `SetTheory` 92%, `NumberTheory` 96%, `ProofParser` 88%, `DiscreteMath` 96%, `DiscreteMathCore` 97%, `validate_all_proofs` 77%, `NatThry` 68%, `test_runner_NatNum` 0% (a compatibility entry point) | `coverage report` |
| Fixtures | 493 proofs; enforced 393/393, informational 100/100 | `./run_tests.sh` |
| Oracle cases | 245 in 15 files | `parse_oracle/` |
| Promotion warnings | 50 "was not promoted" lines in the fixture runner's output: 47 because the proof relies on structure recorded in a declaration (all relation declarations), 3 because the proof derives nothing at the top level to promote | `source/validate_all_proofs.py` |
| Last CI on `master` | run #1080 (push to `master` at `c00bdb8`, the merge of #149) passed; the merge of #150 changed only `todos.txt`, so it had no push run | Actions |
| The one expected failure | `test_existence_witness_is_not_a_default_generalized_parameter` (`test_theorem_promotion_audit.py`) marks as "for review" the behaviour the owner decided on 2026-10-31 to keep | section 14.6 |

## 12. Workflow and conventions

- **One small branch and one pull request per task**, named `claude/...` or
  `chatgpt/...`. Never rewrite, rebase, force-push or clean up another agent's
  branch. When a base moves, merge it into the branch.
- **The owner merges.** Agents open pull requests and keep them green; they do not
  merge, and do not treat a comment on GitHub as approval.
- **Ownership.** `source/ProofLogic.py` and `source/ProofJustification.py` are the
  kernel; edit them only in coordination with Claude.
- **Owner-gated work.** Anything marked "owner approval required" in `todos.txt`
  is not started without an explicit answer. If semantics are ambiguous or
  conflict with a decision, stop and ask; do not decide implicitly in code.
- **Design before code for a new feature.** Write the target proofs first (J33
  does this for arbitrary-property WLOG), give the owner a short note with the few
  choices that matter, and implement after the answer. One feature at a time.
- **Delegation.** Work that does not need the kernel is written up as a job in
  `JOBS_FOR_CHATGPT.md` (goal, allowed scope, tests, a "Done when" that can be
  observed). A job starts only after the pull request that adds it has merged; at
  most three delegated pull requests are open at once, normally about 400 changed
  lines or fewer; a delegated PR stays a draft until its criteria pass. A job is
  complete when its PR has merged and the tracker is updated; its specification
  then moves to `docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`.
- **Documents.** `todos.txt` is the source of truth for status, invariants,
  decisions and approvals; `README.md` and `docs/PROOF_FILE_FORMAT.md` change
  alongside any user-visible behaviour (tests execute the examples in both);
  test counts are not hard-coded into architecture documents.
- **Sugar and extension points.** New syntax goes into a theory environment
  (parsers, phrase parsers, declaration recipes, rules), not into a generic
  parser special case written to rescue one example.
- **Environment note.** In the cloud sessions Claude works from, GitHub is reached
  through its REST API (pull requests are created and patched with `gh api`),
  and a pushed branch may not appear as a remote-tracking ref locally; check it
  with the API.

## 13. Decisions

Owner decisions, newest last. Quotations are the owner's words.

| Date | Decision |
| --- | --- |
| 2026-10-17 | Standing: "Leave instructions to chatgpt to implement any job you can give it, so that it saves you time." |
| 2026-10-24 | `Mutatis mutandis` stages 2 and 3 approved: a name replaced by a term, a symbol replaced by another. |
| 2026-10-29 | A relation on X is a subset of X × X. Declaring one states that as a formula by sugar (issue #136 settled as no defect). Standing: "Feel free to do any cleaning and communicate feedback and request work from ChatGPT." |
| 2026-10-30 | Answers to the owner-gated list: retire generic `(Axiom)` for the four set axioms, "This is fine." (done: PR #149, merged 2026-11-01); a symbolic defining property for sets, yes; WLOG for arbitrary properties, yes; the broader Infinity and finite-set semantics, yes; declaring function symbols in proof text and making set operations terms, "Yes, declare everything."; extending `Mutatis mutandis` beyond names, terms and symbols, "Not right now. ... if I ever do then I'll bring it up later."; major theory modules such as abstract algebra or topology, "Not right now, but later." |
| 2026-10-31 | After explanation, the owner agreed with both recommendations. Promoted theorems over relation symbols and their declared structure: yes, after the declared-function work. Witness policy: no change (a top-level `Existence from L` witness stays generalized, its defining formula carried as a premise). |

Standing decisions without a single date, recorded in `todos.txt`, the module
docstrings and `TYPE_SYSTEM_DESIGN.md`:

- Number theory supplies only its documented arithmetic laws; an axiom is added
  when a specific proof needs it and the owner agrees (issue #98 is the open list).
- Divisibility `a|b` is meant to be accepted only when both operands are known to
  be integers, with a type error otherwise. This is the motivating case of the
  type-system proposal and is not implemented.
- A multi-proof file shares no lexical context; reuse is by promotion and title.
- An axiom citation stays an ordinary formula; naming its witness is surface sugar
  (`Let Y be such a set.`) that elaborates to a declaration, the membership
  characterization and an Existential Elimination wrapper, with no kernel change.
- WLOG's region is the WLOG line to the end of the current block.
- Set theory is the root and does not depend on number theory.
- The substitution guard for `Mutatis mutandis` lives in the substitution path
  itself; strict binder matching stays, with no alpha-renaming.

## 14. Work in flight and what comes next

### 14.1 Open pull requests

| PR | What it is | State |
| --- | --- | --- |
| #148 | ChatGPT's J31: a test-only red team of the relation-subset declaration fact. It adds `tests/testDiscreteMath/red_team_relation_subset.txt` (16 enforced cases, seven of them invalid, each with a valid twin) and `pytest_tests/test_red_team_relation_subset_reasons.py`, which pins every refusal by line, category and reason, and it edits the J31 status line. No production code. | Draft. CI run #1077 passed on its head `6f89b75`; its description reports 2,091 tests passed with 1 expected failure, and 400/400 enforced and 100/100 informational fixtures. Claude's independent review was asked for on 2026-10-31 and is not yet answered. The branch predates #149 and merges into `master` without conflicts (checked with `git merge-tree`). |

The owner merged #149 (generic `(Axiom)` retired for set theory) and #150 (the
owner's answers of 2026-10-30 and 2026-10-31, recorded in `todos.txt`) on
2026-11-01.

### 14.2 Open issues

| Issue | Subject | State |
| --- | --- | --- |
| #98 | Number theory: the axioms that the next proofs need | An owner decision list, not authorization to add axioms. |
| #144 | ChatGPT's proposal to share one dispatch for top-level theory formula parsers (it is written twice, in `_ElaborationContext.parse_surface_expression` and `_parse_premise_part`) | Review only. Claude's reply has been outstanding since 2026-10-30. |
| #151 | A premise line `A and B are disjoint.` is read as a declaration | Filed 2026-11-01. Parser; can be delegated (section 15). |
| #152 | `irreflexive`, `asymmetric` and `total` are refused after a comma in a relation declaration | Filed 2026-11-01. Parser; can be delegated (section 8.3). |

Recently closed: #75 (WLOG replay of outside citations; fixed, closed
2026-10-31), #136 (relation-property rules and the declared carrier; no defect,
2026-10-29), #69 (general `Set property` equality substitution; an explicit
`Substitution` step does the replacement, 2026-10-16).

### 14.3 Delegated jobs

`JOBS_FOR_CHATGPT.md` is the tracker; J28 to J30 (merged in #142, #143 and #146)
are archived in `docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`. At most three
delegated pull requests are open at once; one is.

| Job | Subject | State |
| --- | --- | --- |
| J31 | Red-team the relation-subset fact | PR #148, draft, waiting for Claude's review. |
| J32 | Proofs that use the relation-subset fact (an informational file of at least 5) | Ready to start. |
| J33 | Target proofs for arbitrary-property WLOG, in a new `tests/targets/` that the runner does not scan, with hand-proved twins | Ready to start. First step of feature 2 below. Its pull request must say which reading of "exchange" each target relies on. |
| J34 | Red-team the closed axiom list (`(Axiom)` in set theory, the pointer in the refusal, promotion) | Ready to start; it was added by #149, which has merged. |

### 14.4 The approved order of features

The owner approved these on 2026-10-30 and 2026-10-31 (`todos.txt`, "Owner
decisions"). One at a time, each with its target proofs first.

| # | Feature | Status |
| --- | --- | --- |
| 1 | Retire generic `(Axiom)` for the four set axioms | Done (PR #149). |
| 2 | WLOG for arbitrary properties (`a <= b or b <= a`) | Next. J33 writes the target proofs first. The semantics is a choice for the owner and Claude, taken when J33's pull request says what each target relies on: whether "the names exchanged" is a swap of two names or any one-to-one renaming, and whether symbols may be exchanged too. |
| 3 | Declared function symbols in proof text; set operations as terms | No agreed design. A short design note with the few choices goes to the owner **before any code** (14.5). |
| 4 | A symbolic defining property for a set with no stated characterization | Designed together with 3. |
| 5 | Infinity and finite-set semantics (a bijection is a function) | After 3. |
| 6 | Promoted theorems over relation symbols and declared structure ("any equivalence relation", later "any group") | After 3. |

### 14.5 Design in progress: declared functions and set operations

What the checker does today (each row was run on `master` at `5efa1fc`):

| Input | Result |
| --- | --- |
| `Let A, B be sets, f: A -> B be a function.` | Declares `A` and `B` (kind `object`) and `f` (kind `function`, no arity, empty metadata): the domain and codomain written in `f: A -> B` are recorded nowhere. **States no formula**: the core entry is `<declarations only>`. |
| `f(a, b) = f(a, b)` and `f(a) = f(a)` with `f` declared that way | Both accepted: a function declared without an arity takes any number of arguments. |
| `f(b) = f(b)` for a `b` outside `A` | Accepted: there is no domain check. |
| `In(f(a), B)` from `In(a, A)` | Not derivable: nothing says that `f` maps `A` into `B`. |
| `In(x, union(A, B))` | `union(A, B)` is an ordinary function term; the kernel refuses it as an undeclared symbol (`undeclared_symbol`). |
| `A union B = B union A` | Refused at elaboration: "Unrecognized term syntax: 'A union B'". |
| `x belongs to A union B` | Accepted, as sugar for `In(x, A) or In(x, B)`: a phrase, not a term. Only a fixed list of such phrases exists (section 8.1). |
| `(a, b) in R`, `In((a, b), R)` | Refused at elaboration: a pair is not a term. |
| `Let R be a relation on X.` | States `forall x, forall y, (R(x, y) -> (In(x, X) and In(y, X)))`. This is the model to follow: a declaration states what it means as an ordinary formula. |

The direction, which follows from the owner's "Yes, declare everything." (no
code until the owner has answered the note):

- A declared function symbol is a declaration plus the formulas it states, as
  `Let n be an integer` states `Int(n)` and `Let R be a relation on X` states
  `R ⊆ X × X`. For `f: A -> B` the formula is
  `forall x, (In(x, A) -> In(f(x), B))`. The kernel does not change.
- A set operation (`A union B`, `A intersect B`, `A minus B`, the power set, a
  pair, a product) becomes a function symbol of the set-theory module whose
  defining formula is a visible fact.
- A symbolic defining property for a set (feature 4) is the same mechanism: the
  defining formula of a declared symbol.

The few choices for the owner, each with Claude's recommendation (not yet put
to the owner):

1. **How much now.** Symbols with an arity and their typing formulas now, or a
   type system (`TYPE_SYSTEM_DESIGN.md`) first. Recommended: symbols now.
2. **Where an operation's meaning comes from.** Derived (proved from the axioms
   by existence and uniqueness, then promoted) or stated by the module as an
   axiom. Recommended: derived, because set theory is the root and facts must be
   visible. It needs the first built-in theorems, which do not exist yet (there
   is no theorem library).
3. **Notation.** `A union B`, `A intersect B` in words and the function form
   `union(A, B)`, both elaborating to the same term; symbols such as `∪` later.
   Recommended: words and the function form first.
4. **Application outside the domain.** Whether `f(b)` for a `b` not known to lie
   in `A` is allowed. Recommended: allow it for now (the typing formula is a fact
   about members only); a domain check can be added later without breaking proofs
   that already establish membership.

### 14.6 Cleanup candidates

Each was checked on `master` at `5efa1fc`. The tracker move (J28 to J30) and
the stale `todos.txt` entry for issue #75 are corrected in the pull request that
adds this file.

- **The expected failure.** `test_existence_witness_is_not_a_default_generalized_parameter`
  pins as "for review" the behaviour the owner decided on 2026-10-31 to keep.
  Convert it into a test of the decided policy. (It changes an existing
  expectation because the owner's decision changed it, so it is done by Claude
  and says so in its pull request.)
- **`default_theory_environment()`.** It composes set theory and base logic twice
  (its name reads `base logic + set theory + number theory + set theory +
  discrete mathematics + base logic`; 29 rule objects, 20 distinct) and tries to
  import an `OrderTheory` module that does not exist in this repository. The
  comments in `ProofParser.py` and `ProofLogic.py` and a sentence in `README.md`
  still refer to it. Compose each theory once and drop the dead import.
- **Defects in the "was not promoted" warning.** For a relation with no
  properties it ends "and properties ." (7 of the 50 warnings), and it points to
  `todos.txt` item 8, which no longer exists (the lists were renumbered; the topic
  is owner decision 6). The text is in `ProofLogic.py` and tests may pin it.
- **One theory's vocabulary in the generic parser.** `descriptor_words` in
  `_split_compound_declaration_items` names relation property words (issue #152),
  against the rule that theory syntax lives in a theory environment. The
  duplicated parser dispatch (#144) belongs to the same tidy-up.
- **Structural note.** `ProofLogic.py` is one file of 5,812 lines (entry
  language, every base rule, the validator, declarations, promotion, WLOG and
  `Mutatis mutandis`). It is the part to change least; a split is possible and is
  not planned.

### 14.7 Owner-gated: not started without an answer

- Extending `Mutatis mutandis` beyond names, terms and symbols: "Not right now."
- Major theory modules (abstract algebra, topology, real analysis, linear
  algebra): "Not right now, but later."
- Which arithmetic laws to add for the divisibility proofs that issue #98 lists.
- The answers to the design note of 14.5 (feature 3), and the choice of
  "exchange" semantics for WLOG (feature 2).

## 15. Known limits

Each limit below was reproduced or read from the code on `master` at `5efa1fc`.

**The language**

- Function declarations carry no typing: `f: A -> B` states no formula and
  records neither the domain nor the codomain, a function without an arity takes
  any number of arguments, and applying `f` outside `A` is not checked (14.5).
- Set operations are not terms. There are phrases for membership in a union or an
  intersection and displays next to a relation, and nothing else. There are no
  pair terms, ordered pairs or products: `(a, b) in R` is refused at elaboration.
- There is no infix arithmetic: `a + b` is "Unrecognized term syntax"; a sum is
  `Plus(a, b)`.
- `a|b` is accepted for any two objects. There are no type errors yet; the
  proposal is `TYPE_SYSTEM_DESIGN.md`.
- A premise line that begins `A and B are disjoint` is read as a declaration
  (issue #151), and a comma list of relation properties refuses `irreflexive`,
  `asymmetric` and `total` after the first word (issue #152).
- Formula `==` in Python is object identity. Structural comparison is
  `ProofLogic._ast_eq`; code that compares formulas with `==` is a bug.
- The checker reports the first error only.

**The theories**

- Number theory supplies its 12 axioms and no more: no commutativity,
  multiplicative identity, annihilator or `Neg`-`Times` law (issue #98).
- Foundation (regularity) and Choice have no rule. The informational ZFC fixture
  states all nine axioms as headings and proves only unique pairing.
- The finite/infinite semantics for Infinity and a symbolic defining property for
  sets are approved and not implemented (14.4).
- `Set property` has no equality-substitution mode; an explicit `Substitution`
  step is the decided way (issue #69).
- The `Use discrete math.` directive is accepted and selects nothing: the default
  environment loads every theory.

**Reuse and shortcuts**

- Promotion generalizes top-level object declarations only. Function and
  predicate symbols are not generalized, and a proof that relies on a relation
  declaration's recorded carrier or properties is not promoted (47 of the 50
  "was not promoted" warnings in the fixture runner). Both are approved, after
  feature 3.
- There is no theorem library: promoted theorems live in the file or call that
  made them. A theorem rule can be passed to `check_proof_text(rules=...)`, and
  nothing stores or imports one across files or modules.
- WLOG is equality-only: alternatives that differ in exactly one constant.
- `Mutatis mutandis` never replaces a compound term as a whole or a symbol by a
  term, cannot repeat a closed block of several lines, does not match
  counterparts that differ by the symmetry of `=` or `<->`, and cannot repeat a
  premise, an assumption, a witness line, an axiom citation or a structure
  declaration (10.3).

## 16. Glossary

- **Arbitrary object.** A constant introduced by `let c be arbitrary`, or by the
  subproof of Universal Generalization. It must occur in no hypothesis in force.
- **Axiom list (open, closed).** What an `(Axiom)` line may state. A non-empty list
  closes itself. An empty one is open (any formula is accepted, a bare proof)
  unless the theory closed it (`axioms_closed`), as set theory does.
- **Citation.** The part of a justification that names a rule and the lines it
  uses: `(Modus Ponens from 2, 3)`.
- **Core entry.** A line of the kernel's entry language after elaboration, a tuple
  of label, formula and justification (section 6.1).
- **Declaration.** A symbol introduced with a kind (`object`, `predicate`,
  `closed_formula`, `function`), an arity, a descriptive type and metadata.
  *Declaration sugar* is a declaration line that also states formulas.
- **Elaboration.** The translation of the surface syntax tree into core entries by
  the theory environment's parsers, recipes and elaborators.
- **Enforced and informational suites.** Fixture suites whose unexpected results
  fail the run, and ones that are only reported.
- **Fixture, case.** A proof file in `tests/` or `source/testProofs/`, and one
  `# N: title` proof in it, with its expected outcome.
- **Job (J-number).** A unit of delegated work for ChatGPT in
  `JOBS_FOR_CHATGPT.md`.
- **Kernel.** `source/ProofLogic.py` and `source/ProofJustification.py`, which
  validate entries and know nothing about text.
- **Mutation check.** `tools/mutation_check.py`: apply small source mutations and
  see whether the named tests fail.
- **Owner-gated.** Marked "owner approval required" in `todos.txt`; not started
  without an explicit answer.
- **Parse oracle.** `parse_oracle/` cases that pin surface text to the plain-logic
  formula it must elaborate to, independently of the parser.
- **Promotion.** Turning a checked proof into a `TheoremRule` that later proofs
  cite by title (section 10.1).
- **Rule configuration.** What distinguishes two instances of one rule class
  (induction over `Int` and over `Nat`); `InferenceRule.same_configuration`.
- **Surface proof.** The syntax tree of the text with source spans, before
  elaboration.
- **Target proof.** A proof written before the feature that should make it pass
  exists; the project writes these first.
- **Theory environment.** The bundle of parsers, recipes, rules, axioms and
  declarations that one subject adds (section 8.0).
- **Twin (valid twin).** For an invalid test case, a valid case that differs only
  in the condition its title names, so the refusal is for that reason.
- **Witness.** A name for an object whose existence a proof has shown, written
  `Let Y be such a set. (Existence from L)`.
- **WLOG, Mutatis mutandis.** The two shortcuts the validator expands into
  ordinary lines and validates (section 10).

## 17. Commands, and how to resume

### 17.1 Reproducing the figures

Run these from the repository root. `./run_tests.sh` sets `PYTHONPATH` itself;
for an ad-hoc script that imports `SyLoPy.source...`, put the directory that
contains a checkout named `SyLoPy` on `PYTHONPATH` (and do not use `python3 -I`,
which ignores it).

| Figure | Command |
| --- | --- |
| Everything that must pass | `./run_tests.sh` (exit 0 only if pytest, the coverage gate and the fixtures all pass) |
| One fixture suite | `./run_tests.sh --list-suites`, `./run_tests.sh --suite testDiscreteMath --verbose` |
| Number of tests | `python3 -m pytest pytest_tests --collect-only -q \| tail -1` |
| Coverage by file | `python3 -m coverage report` after `./run_tests.sh` (`-m` adds the missed lines) |
| Fixture totals and promotion warnings | `python3 source/validate_all_proofs.py` (`\| grep -c 'was not promoted'` counts the warnings) |
| Oracle cases | `cat parse_oracle/*.txt \| grep -c '^id:'` |
| Source size | `wc -l source/*.py` |
| Number of distinct rule names | `python3 -c "import SyLoPy.source.ProofLogic as pl, SyLoPy.source.ProofParser as pp; print(len({r.name for r in pl.default_rules()} \| {r.name for r in pp.default_theory_environment().rules}))"` |
| One proof | `python3 -c "import SyLoPy.source.ProofParser as pp; print(pp.check_proof_text(open('proof.txt').read()))"` |
| Elaborated entries of a proof | `pp.format_core_proof(pp.parse_proof_text(text)[0])` |
| Mutation check | `python3 tools/mutation_check.py SPEC.json --tests "python3 -m pytest -q pytest_tests/test_x.py"` (`--jobs N` runs mutations concurrently) |
| CI on `master` and on pull requests | `gh api repos/axiomtutor/SyLoPy/actions/runs --jq '.workflow_runs[0:6][] \| "#\(.run_number) \(.event) \(.head_branch) \(.head_sha[0:7]) \(.conclusion)"'` |
| Open pull requests and issues | `gh api 'repos/axiomtutor/SyLoPy/issues?state=open' --jq '.[] \| "#\(.number) \(.title)"'` |

### 17.2 Resuming work

1. Check the open pull requests and issues, and any comment that asks Claude for a
   review. ChatGPT's requests arrive as comments from `axiomtutor` that begin
   `@claude`; they ask for explicit agreement or a concrete correction.
2. Read this file, `AGENT_COLLABORATION.md`, and the "Owner decisions" at the end of
   `todos.txt`. Then only the subsection the task needs.
3. Check the CI runs on `master` and on the open pull requests (the command in
   17.1). A run on a pull-request head is not a run on the merge commit.
4. Work in a worktree per branch, branched from the current `master` and named
   `claude/<topic>-<date>`. Never touch another agent's branch.
5. Write the target proofs first. Take one feature at a time, in the order of
   14.4. Stop at an owner-gated question and write the note with the few choices.
6. Verify the committed tree on Python 3.12 and 3.13 with `./run_tests.sh`. A
   negative test is pinned by line, category and reason, with a valid twin; new
   tests are mutation-checked.
7. Open the pull request with a verification block (the tested commit, local
   totals on both Python versions, fixture totals) and patch the CI run number in
   after CI has finished. Do not merge. End the description with the Claude Code
   line and the session link.
8. After the owner merges: update `todos.txt` and the job tracker, and correct
   sections 11 and 14 of this file in the next pull request that touches them.
