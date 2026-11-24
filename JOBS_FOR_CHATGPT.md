# Delegated Jobs for ChatGPT

This file is the live queue and concise disposition ledger. Stable collaboration rules are in [`AGENT_COLLABORATION.md`](AGENT_COLLABORATION.md); current status and owner decisions are in [`todos.txt`](todos.txt). Full historical task specifications are preserved in [`docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md).

## Active queue: set theory

Owner direction of 2026-11-05: set theory is the priority until it is fully
functional. J36–J43 follow the owner's decisions of 2026-11-09 about definitions,
which [PR #167](https://github.com/axiomtutor/SyLoPy/pull/167) implements:

- A set has a defining property, and its elements are the objects that satisfy it.
  `x is in A union B` is a statement of its own, the atom `In(x, Union(A, B))`;
  that it is `x is in A or x is in B` is what `Definition of union` says, and a proof
  cites that to get there. Every membership phrase, set displays included, is to be
  such an atom (J37 now, displays later).
- A definition checks that the thing exists, names it, and adds no axiom. #167 adds
  `source/Definitions.py`, the facility, and three set definitions: `Definition of
  union`, `Definition of intersection`, `Definition of power set`. Each is an entry of
  `SET_DEFINITIONS` in `source/SetTheory.py`, made by `set_definition(title, symbol,
  parameters, defining_property, evidence)`. The evidence is an axiom rule (`ByRule`)
  or a proof from the axioms (`ByProof`); the facility reads off what it has to show,
  that some set has exactly those members, and checks it. Adding an entry declares its
  symbol, makes `(Definition of …)` citable and gives the proof its sentence; no other
  file has to change. Read the docstring of `source/Definitions.py`, the section
  "Definitions of the declared set operations" of `source/SetTheory.py` and
  `pytest_tests/test_set_operation_definitions.py` first.
- The ordered pair will be `{{a}, {a, b}}` with readable syntax. The abstract `Pair`
  and `CartesianProduct` are declared and not defined until then.
- Symbols (`∈`, `∪`, `∀`, …) are accepted as input by the owner (J41).

The "Today" entries were produced by running `pp.parse_formula` and the checker at
commit 742d2d3 of #167; re-run a row before relying on it and report any that no
longer holds.

Queue state (2026-11-23): #167 merged on 2026-11-15 and #168, which adds J36–J43,
on 2026-11-18. None of J36–J46 has started, and no ChatGPT pull request is open. The
owner directed on 2026-11-21 that the corpus (`SetTheoryCorpus/`) is developed first
(`todos.txt`, Current status). Claude's recommendation: begin with J36, J41 and J43,
which do not depend on the corpus, then J37 and J39, and hold J38, J42 and J40 until
the owner has decided whether the set operations are defined in the corpus or in Python
(`todos.txt`, The plan, part 3 and question 4), because they add definitions to the
Python module. J44, J45 and J46 fix the findings #169, #170, #171 and #181; the owner
approved their directions in comments on the issues on 2026-11-23. They are small, and
they change the declaration code, not the term parsers of J36–J43.

Dependencies: every job needs #167 merged, because its fixtures cite the definitions
(it has). J36, J41, J43, J44, J45 and J46 need nothing else. J37, J38 and J39 need J36.
J42 needs J38, and J40 needs J38 and J39. J38 and J42 both change the tests that pin
the list of definitions, so they must not run together, and J44, J45 and J46 change the
same declaration code and recipes, so they must not run together either. Start the jobs
that are unblocked in this order, within the limit of three open PRs: J45, J44, J36,
J41, J43, J46, J38, J37, J39, J42, J40. J45 is first because `Let P be a proposition.`
is the first thing a new user writes. A job starts only after the PR that adds it has
merged, as below.

### J36 — Nested set-operation terms

**Goal:** A set-operation term may contain other terms, so that the laws of set
algebra can be written in proof text. `try_parse_set_term` (`source/SetTheory.py`;
the set theory's `term_parsers` entry, also called by every set phrase) reads only a
bare name, `∅` or `the empty set`, `X union Y`, `X intersection Y`, `X cross Y`,
`the power set of X` and `pair(x, y)`, all with bare names as operands.

| Surface text | Today | Reads |
| --- | --- | --- |
| `x is in A union B union C` | refused: "Unrecognized formula syntax" | `In(x, Union(Union(A, B), C))` |
| `x is in (A union B) intersection C` | refused | `In(x, Intersection(Union(A, B), C))` |
| `A union (B union C) = (A union B) union C` | refused: "Unrecognized term syntax" | `Union(A, Union(B, C)) = Union(Union(A, B), C)` |
| `x is in the power set of (A union B)` | refused | `In(x, PowerSet(Union(A, B)))` |
| `x is in Union(A, B)` | refused, although `In(x, Union(A, B))` is accepted | `In(x, Union(A, B))` |
| `x is in f(A union B)` | refused | `In(x, f(Union(A, B)))` |
| `x is in A union B intersection C` | refused, as above | refused, with "parenthes" in the message |
| `x is in A cross B cross C` | refused, as above | refused, with "parenthes" in the message |

**Decisions already made** (do not reopen; if one cannot work, report it as a
finding):

1. An operand is a name, `∅` or `the empty set`, a parenthesised set term,
   `the power set of <operand>`, or a function application `f(t1, ..., tn)` whose
   arguments the ordinary term parser reads (so `Union(A, B)` and `f(A)` are set terms
   in phrases too). The existing `pair(x, y)` reading, for bare names only, stays
   exactly as it is: the abstract `Pair` is going away, so nothing is added for it.
2. A chain of one operation, `A union B union C` or `A intersection B intersection C`,
   reads left-nested: `Union(Union(A, B), C)`.
3. A chain that mixes operations (`A union B intersection C`), and a chain of `cross`
   with more than two operands, are refused with a message containing "parenthes".
   There is no precedence between operations. Raise `ValueError` from the term
   parser for this: a prototype showed that the message reaches the user unchanged.
4. The operators are one table, word to symbol (`union`, `intersection`, `cross`), so
   that J38 adds `setminus` with one entry. Matching stays case-insensitive. An
   operator word is not a name (`x is in union B` stays refused).
5. A name bound by an enclosing quantifier is a variable and any other name a
   constant, as `_name_term` does today. No existing reading, oracle expectation or
   fixture changes.

**Allowed scope:** `source/SetTheory.py` (the term parser, not the rules); new
`parse_oracle/set_operations_nested.txt`, `pytest_tests/test_set_operation_nesting.py`
and enforced fixture `tests/testSetTheory/set_operation_terms_nested.txt`; the
set-operation paragraph of `docs/PROOF_FILE_FORMAT.md`; the nesting caveat in
`todos.txt`. Not `source/ProofLogic.py` or `source/ProofJustification.py`.

**Tests:** an oracle case for every row above (the reading written first, in plain
logic); one each for a chain of `intersection`, a nested term under a bound variable
(`forall x, x is in (A union B) intersection C`) and a nested term inside a larger
formula (`P(x) and x is in A union (B intersection C)`); `expect: REJECT` for a mixed
chain, a `cross` chain, an unbalanced parenthesis, `()` and `x is in A union`. The
pytest module also checks that both refusal messages contain "parenthes". The fixture
has at least four valid proofs that apply the definitions of #167 to nested terms
(union is associative, as two subset proofs; a three-fold union unfolded; a member of
the power set of a union; an intersection of a union) and four invalid ones, each
refused by a definition rule and not by a parse error. Run `tools/mutation_check.py`
over the new parser code and report mutants made and survivors.

**Done when:** every row reads as stated; the refusals carry the stated message; the
tests above pass; `./run_tests.sh` and `./run_tests.sh --suite extended` pass on
Python 3.12 and 3.13; the PR report is as rule 3 below requires (the tested commit,
the CI run, the totals); the later jobs say "the PR report is as for J36" for this. If
this one passes about 400 changed lines, send the fixture as a second PR.

Status: queued; unblocked (#167 has merged); not started.

### J37 — Every membership phrase is a membership

**Goal:** Today the membership phrases are a ragged grid, and a few of them read as a
disjunction or a conjunction. The owner has decided that every membership phrase is
the atom `In(x, T)` (or its negation), and the corpus note in
`SetTheoryCorpus/Chapter1_Axioms.txt` says that "in" and "contains" mean member, not
subset. Below, `S` is a set term of J36 other than the two English forms, `U` is
`the union of A and B` and `I` is `the intersection of A and B`. "ok" is accepted
today and reads `In(x, T)` (negated for the "not" phrases); "ok*" is accepted today
but reads as the disjunction (for `U` and for `belongs to A union B`) or as the
conjunction (for `I`), negated for a "not" phrase; "add" is refused today.

| Phrase (`x …`) | `S` | `A union B` | `A intersection B` | `U` | `I` |
| --- | --- | --- | --- | --- | --- |
| `is in` | ok | ok | ok | ok* | add |
| `is not in` | ok | ok | ok | add | ok* |
| `belongs to` | add | ok* | add | add | ok* |
| `does not belong to` | ok | ok | ok | add | add |
| `is an element of` | ok | ok | ok | add | add |
| `is not an element of`, `is a member of`, `is not a member of` | add | add | add | add | add |
| `T contains x` | add | add | add | add | add |
| `T does not contain x` | ok | ok | ok | add | add |

**Decisions already made:**

1. After this job every cell is accepted and reads `In(x, T)` or `not In(x, T)`, with
   `U` as the term `Union(A, B)` and `I` as `Intersection(A, B)`. The phrases never
   read as a disjunction or a conjunction; that is what `Definition of union` and
   `Definition of intersection` are for. `T contains x` is the membership `In(x, T)`
   (set first, as "contains" is), so `A contains B` reads `In(B, A)`.
2. The phrases are one table of (phrase, polarity, order) applied to any set term of
   J36, not one regular expression per cell, so that the grid cannot become ragged
   again. `the union of X and Y` and `the intersection of X and Y` become terms
   (`Union(X, Y)`, `Intersection(X, Y)`, operands names or parenthesised terms), so
   they are recognised wherever a set term is. A phrase that contains one is still
   protected from the connective grammar as `find_set_operation_spans` does today:
   `x is in the union of A and B and y is in C` is a conjunction of two memberships.
3. The identity phrases read as equations (the owner, on #168): `A is the union of
   B and C` is `A = Union(B, C)`, and `A is the intersection of B and C` is
   `A = Intersection(B, C)` (the owner gave the union; the intersection has the same
   shape, so it follows the same rule). They no longer read as the characterization
   `forall u, (In(u, A) iff (In(u, B) or In(u, C)))`; a proof gets that from
   `Definition of union` and the equation. Not changed: `the union of A and B is
   empty`, `the intersection of A and B is nonempty` and the disjointness phrases keep
   their readings (they are not identity phrases), and `A contains exactly a and b`
   stays the display sugar.
4. `A set-in B` reads as `A subseteq B`, `A set-contains B` as `B subseteq A`, and
   `A not set-in B`, `A not set-contains B` negate them, wherever `subseteq` is
   accepted today (the owner's corpus spelling). A bare `A in B` is not a subset.
5. Still refused: `x lies in A`, `A has x as an element`. Symbols (`∈`) are J41.

**Allowed scope:** `source/SetTheory.py` (the membership phrase parsers, the
identity-phrase branch that reads `X is the union of Y and Z`, and span protection);
`parse_oracle/set_operations_phrases.txt`, only the seven cases
`j4-union-membership`, `j4-union-membership-nested`, `j4-intersection-membership`,
`j4-intersection-membership-negated`, `j4-union-nested-consequence`,
`j4-union-defines-set` and `j4-intersection-defines-set`, whose expected readings
change as decided (the owner's decision is the authority for this exception to
rule 4; the `why` of the last two says "contains exactly the elements", which stops
being the reading, so rewrite it), and the last sentence of the `why` of
`definition-term-union-membership`, which says the change is planned; new
`parse_oracle/set_membership_wordings.txt`, `pytest_tests/test_membership_wordings.py`
and enforced fixture `tests/testSetTheory/membership_wordings.txt`;
`docs/PROOF_FILE_FORMAT.md`; `todos.txt` (item 8a). No enforced fixture or pytest
module uses the old readings (checked at 742d2d3); if one turns out to, report it.

**Tests:** an oracle case for every "add" and "ok*" cell and for `contains`,
`set-in` and `set-contains`. The pytest module enumerates the whole grid (every
phrase, both orders, every operand kind including nested terms and function
applications) against formulas built from `fl` and `st` independently of the parser,
and checks that the two identity phrases of decision 3 read as the equations (with
nested operands too), that the other phrases it lists keep their readings, and that
the refusals of decision 5 are unchanged. The fixture
has one subset proof, one proof by cases that cites `Definition of union` to get from
`x is in the union of A and B` to the disjunction, and two invalid proofs, one of
which takes the disjunction without the definition (refused at that line).

**Done when:** all cells behave as decided, and the two identity phrases read as
equations; the seven oracle expectations (five membership, two identity) are the only
ones changed; both suites pass on Python 3.12 and 3.13; the PR report is as for J36.

Status: queued; needs J36 (#167 has merged); not started.

### J38 — Set difference

**Goal:** Define the relative difference `Difference(A, B)` with the definition
facility. Today `x is in A setminus B` and `x is in Difference(A, B)` are refused
(there is no such symbol), and a difference exists only as the theorem "The difference
of two sets exists" (proof 4 of the informational
`tests/setTheoryProofs/set_operation_foundations.txt`), so `A setminus B subseteq A`
or De Morgan's laws cannot be stated in a proof.

**Decisions already made:**

1. One new entry in `SET_DEFINITIONS`: `set_definition("Definition of difference",
   "Difference", ("A", "B"), <In(u, A) and not In(u, B)>, ByRule(SeparationSchemaRule()))`.
   Checked in a scratch copy at 742d2d3: the facility accepts this evidence, and the
   claim it derives is `exists Y, forall u, (In(u, Y) iff (In(u, A) and not In(u, B)))`.
   The entry declares `Difference`, registers the rule and makes
   `(Definition of difference)` citable; this job adds no rule class and does not touch
   `source/ProofJustification.py`.
2. Surface: `A setminus B` (one entry in the operator table of J36, so it nests) and
   `Difference(A, B)`. Not `minus` (integer subtraction will want it, as `cross` is not
   `times`), not `\`, and no complement: an absolute complement needs a universe and ZF
   has none. The complement of B in A is `A setminus B`.

**Allowed scope:** `source/SetTheory.py` (the entry and the operator-table entry);
`pytest_tests/test_set_operation_definitions.py`: add an `Operation` for the difference
(and its entry in `NEAR_MISSES` and `SYMBOLS_OF_THE_DEFINITIONS`), so that its generic
parametrised tests cover the new definition, and update the tests that pin the exact
list of definitions on purpose, so that adding one is a decision:
`test_set_theory_defines_the_union_the_intersection_and_the_power_set`,
`test_each_definition_is_the_sentence_that_says_which_objects_are_members`,
`test_each_definition_shows_that_there_is_a_set_with_exactly_those_members`,
`test_the_evidence_for_each_definition_is_an_axiom_or_a_proof_from_the_axioms` (it
unpacks exactly three) and
`test_the_product_and_the_ordered_pair_are_declared_and_have_no_definition_yet`; new
`parse_oracle/set_difference.txt`, `pytest_tests/test_set_difference.py`, enforced
fixture `tests/testSetTheory/set_difference_definition.txt`; the definitions table in
`docs/PROOF_FILE_FORMAT.md`; `todos.txt`.

**Tests:** the generic tests accept the sentence with and without `forall`, in both
biconditional orders, for any terms, and refuse a cited line. Add near misses for the
difference (each its own test): `or` for `and`, `not` on the first operand, the
operands swapped, one direction only, and a true sentence that is not the definition
(`In(x, Difference(A, B)) iff (not In(x, B) and In(x, A))`). Also the oracle cases for
`A setminus B` and `Difference(A, B)` in phrases, and a test that a proof cannot
declare `Difference` again. The fixture has at least five valid proofs (the
definition in each accepted form, `A setminus B subseteq A`, `A setminus A = EmptySet`,
a promoted theorem reused by title) and ten invalid ones, each refused by the
definition rule. Run `tools/mutation_check.py` over the new code.

**Done when:** `x is in A setminus B` reads `In(x, Difference(A, B))`; the rule accepts
and refuses as listed; every invalid fixture proof is refused by the definition rule;
both suites pass on Python 3.12 and 3.13; the PR report is as for J36.

Status: queued; needs J36 (#167 has merged); not started. Held until the owner has
decided whether the set operations are defined in the corpus or in Python (`todos.txt`,
The plan, question 4).

### J39 — Laws of set algebra, batch 1: union and intersection

**Goal:** The standard laws as proofs, each a promoted theorem that later proofs in
the same file cite by its title. One enforced multi-proof file,
`tests/testSetTheory/set_algebra_laws.txt`, using only the definitions of #167,
`Set property`, `Set equality`, subset proofs and the ordinary rules, with each law
stated in the surface syntax (nested terms from J36) and memberships written with
`is in` and `is not in`:

- `A intersection B = B intersection A`;
- `A union (B union C) = (A union B) union C` and the same for intersection;
- `A union A = A` and `A intersection A = A`;
- `A union EmptySet = A` and `A intersection EmptySet = EmptySet`;
- both distributive laws;
- both absorption laws, `A union (A intersection B) = A` and
  `A intersection (A union B) = A`;
- `A subseteq B` iff `A union B = B`, and `A subseteq B` iff
  `A intersection B = A`.

A law whose proof needs another cites it by title (distributivity needs
commutativity, for example) rather than repeating the argument.

**Findings:** if a law cannot be proved because of a checker limitation, do not weaken
it and do not leave a failing proof: file the focused issue that rule 5 asks for
(smallest proof, exact message), leave that law out and list it in the PR. One
limitation is known: Conjunction Introduction takes exactly two lines, so a flat
`P and Q and R` cannot be derived (item 9 of Remaining work in `todos.txt`); nest the
conjunction, `(P and Q) and R`, in the proof of a law.

**Allowed scope:** the new fixture, a new `pytest_tests/test_set_algebra_laws.py` that
asserts the exact list of titles and that every proof passes, and a short list of the
laws in `docs/PROOF_FILE_FORMAT.md`. No edits to `source/`.

**Tests:** besides the valid proofs, one invalid proof for each of these false laws,
refused at the step that would need the false fact and not for a parse, declaration or
scope reason: `A union (B intersection C) = (A union B) intersection C`,
`A intersection (B union C) = (A intersection B) union C`,
`A union B = A intersection B`, and `A subseteq B` iff `A union B = A`.

**Done when:** every listed law is a passing enforced proof under its own title, or a
finding with its issue; the pytest module asserts the titles; the invalid proofs are
refused as described; both suites pass on Python 3.12 and 3.13; the PR report is as
for J36.

Status: queued; needs J36 (#167 has merged; J37 is not needed: the laws use only
`is in` and `is not in`); not started.

### J40 — Laws of set algebra, batch 2: difference and power set

**Goal:** The same, appended to `tests/testSetTheory/set_algebra_laws.txt` (the
numbering continues, so that these proofs can cite the laws of J39 by title) and to the
title list of `pytest_tests/test_set_algebra_laws.py`, for:

- `A setminus B subseteq A`; `A setminus A = EmptySet`; `A setminus EmptySet = A`;
- De Morgan's laws: `A setminus (B union C) = (A setminus B) intersection
  (A setminus C)` and `A setminus (B intersection C) = (A setminus B) union
  (A setminus C)`;
- `A setminus (A setminus B) = A intersection B`;
- `A subseteq B` implies `PowerSet(A) subseteq PowerSet(B)`, and
  `PowerSet(A intersection B) = PowerSet(A) intersection PowerSet(B)`.

Laws of the product wait until `CartesianProduct` has a definition (see Planned).

**Allowed scope, tests, findings and done when:** as for J39, with the false laws
`A setminus (B setminus C) = (A setminus B) setminus C`,
`PowerSet(A union B) = PowerSet(A) union PowerSet(B)`, and `A subseteq B` implies
`PowerSet(B) subseteq PowerSet(A)` as the invalid proofs.

Status: queued; needs J38 and J39 (#167 has merged); not started. Held with J38 (see
there).

### J41 — Symbols as input

**Goal:** A proof may be written with the usual symbols, each read as the word form it
stands for, so that every reading, rule and message that exists for the words applies
unchanged. The owner accepted this on 2026-11-09. Measured at 742d2d3, every symbol
below is refused today ("Unrecognized formula syntax") except `↔`, which is already
read (as is `∅`, which stays as it is); `a != b` and `a ≠ b` are refused and have no
ASCII equivalent yet.

| Written | Read as | From |
| --- | --- | --- |
| `P ∧ Q`, `P ∨ Q`, `¬P` | `P and Q`, `P or Q`, `not P` | base logic |
| `P → Q`, `P ↔ Q` | `P -> Q`, `P <-> Q` | base logic |
| `∀x, P(x)` and `∀x P(x)`; `∃x, P(x)` | `forall x, P(x)`; `exists x, P(x)` | base logic |
| `∀x ∈ A, P(x)`; `∃x ∈ A, P(x)` | `forall x in A, P(x)`; `exists x in A, P(x)` | set theory |
| `a ≠ b` and `a != b` | `not (a = b)` | base logic |
| `x ∈ A`, `x ∉ A` | `x is in A`, `x is not in A` | set theory |
| `A ⊆ B` | `A subseteq B` | set theory |
| `A ∪ B`, `A ∩ B`, `A × B` | `A union B`, `A intersection B`, `A cross B` | set theory |
| `A ∖ B` (U+2216) | `A setminus B` | set theory, when J38 has merged |

**Decisions already made:**

1. The symbols are a notation table that belongs to the theory environment (a new
   field of `TheoryEnvironment`, merged like `term_parsers`): the base logic holds the
   logical symbols, set theory the set symbols, and a later module adds its own. If two
   theories in one environment give one symbol different readings, assembling the
   environment is an error that names both (`×` will want to mean something else in
   number theory).
2. The rewriting is textual, once, on the text of a formula before any other parsing,
   at the entry that proof lines and `parse_formula` share. Each replacement is padded
   with spaces, so `x∈A` and `¬P(x)∧Q(x)` work. The bounded forms are written out first
   (`∈` directly after a quantified variable becomes `in`: `forall x is in A, P(x)` is
   refused today). The connectives keep the precedence the words have, which is the
   standard one (checked: `not P and Q` reads `(not P) and Q`).
3. `a ≠ b` and `a != b` are new syntax in the formula grammar next to `=`: they read
   `not (a = b)`. This is the only grammar change in the job.
4. Left refused, because they are ambiguous or not wanted yet: `⊂`, `⊊`, `⊃`, `⊇`, and
   every symbol not in the table (such as `⊕`, `≤`, `∣`, `ℕ`), with today's refusal.
   Number theory stays paused, so it gets no table now.
5. Error messages may quote the text after rewriting.

**Allowed scope:** `source/ProofElaboration.py` (the field and its merge),
`source/ProofParser.py` and `source/ProofParserPolicy.py` (the call of the rewrite and
the `≠` grammar), `source/SetTheory.py` and the base environment (the tables), a new
`source/Notation.py` if it helps; new `parse_oracle/unicode_symbols.txt`,
`pytest_tests/test_unicode_symbols.py` and enforced fixture
`tests/testSetTheory/unicode_symbols.txt`; the section on symbols in
`docs/PROOF_FILE_FORMAT.md`; item 8(f) of `todos.txt`. Not kernel files.

**Tests:** one oracle case per row (line and nested context; `expect` written in the
word form); the pytest module parses every row and its word form and compares them
with `pl._alpha_eq`, also with no spaces, with a symbol next to a word (`x ∈ A and
P(x)`), inside a quantifier body and in a nested formula; a test that two theories with
different readings of one symbol fail to merge and that the same reading twice does
not; refusal tests for `⊂`, `⊕` and an unterminated `∀`. The fixture has three valid
proofs written only with symbols (a bounded-quantifier proof, `A ⊆ A ∪ B`, a De Morgan
step) and two invalid ones; a test checks that each fixture proof, rewritten back to
words, parses to the same entries. Run `tools/mutation_check.py` over the rewriting.

**Done when:** every row reads as its word form in line and nested context and in a
fixture proof; the merge conflict is an error; no existing reading changes; both suites
pass on Python 3.12 and 3.13; the PR report is as for J36. If J38 has not merged, leave
`∖` out and add it with J38 (whichever merges second adds the entry).

Status: queued; unblocked (#167 has merged); not started.

### J42 — The singleton and the unordered pair

**Goal:** Define the singleton `{a}` and the unordered pair `{a, b}` as sets, with the
Axiom of pairing behind them: `Singleton(a)` and `UnorderedPair(a, b)`. They are the
first two steps to the ordered pair `{{a}, {a, b}}`, which is the owner's decision for
`(a, b)`. This job gives them meaning and nothing more; `{a}` and `{a, b}` as terms
come later (see Planned).

**Decisions already made:**

1. `set_definition("Definition of unordered pair", "UnorderedPair", ("a", "b"),
   <u = a or u = b>, ByRule(PairingAxiomRule()))`. Checked in a scratch copy at
   742d2d3: the facility accepts this evidence.
2. `set_definition("Definition of singleton", "Singleton", ("a",), <u = a>,
   ByProof(SINGLETON_EXISTENCE_PROOF))`. `PairingAxiomRule` refuses the claim
   `exists Y, forall u, (In(u, Y) iff u = a)` (checked), so the evidence is a proof
   from Pairing with `b := a`. The facility accepted this proof (checked); use it as it
   is. It is also the first proof of the new fixture (the theorem is its last line,
   `exists Y, forall x, (In(x, Y) iff x = a)`), and a test pins that the evidence is that
   proof, as `test_the_evidence_for_the_union_is_the_proof_that_the_union_of_two_sets_exists`
   does for the union:

```text
1. Let a be any set. (Declaration)
2. Exists P, forall u, (In(u, P) iff (u = a or u = a)). (Axiom of pairing)
3. Let P be such a set. (Existence from 2)
4. forall x, (In(x, P) iff x = a). (Universal Generalization from subproof below)
begin subproof
 4.0. let c be arbitrary. (Arbitrary)
 4.1. In(c, P) -> c = a. (Conditional Introduction from subproof below)
  4.1.1. In(c, P). (Assumption for Conditional Introduction)
  4.1.2. c = a or c = a. (Set property, 3, 4.1.1)
  4.1.3. c = a. (Proof by Cases from 4.1.2, subproofs below)
  begin subproof
   4.1.3.1. c = a. (Case)
  end subproof
  begin subproof
   4.1.3.1. c = a. (Case)
  end subproof
 4.2. c = a -> In(c, P). (Conditional Introduction from subproof below)
  4.2.1. c = a. (Assumption for Conditional Introduction)
  4.2.2. c = a or c = a. (Disjunction Introduction from 4.2.1)
  4.2.3. In(c, P). (Set property, 3, 4.2.2)
 4.3. In(c, P) iff c = a. (Biconditional Introduction from 4.1, 4.2)
end subproof
5. Exists Y, forall x, (In(x, Y) iff x = a). (Existential Introduction from 4)
```

3. Both go in `SET_DEFINITIONS`. There is no new surface syntax: `Singleton(a)` and
   `UnorderedPair(a, b)` are ordinary function terms. `Pair` and `pair(...)` are not
   touched. The owner approved the names on #168 (2026-11-17: "Your names are good.").

**Allowed scope:** `source/SetTheory.py` (the two entries and the proof text);
`pytest_tests/test_set_operation_definitions.py`: `Operation` entries for both (with
`NEAR_MISSES` and `SYMBOLS_OF_THE_DEFINITIONS`) and the tests that pin the list of
definitions, which J38 names (by now they list four definitions); new
`pytest_tests/test_singleton_and_pair.py`, enforced fixture
`tests/testSetTheory/singleton_and_pair_definitions.txt`; the definitions table in
`docs/PROOF_FILE_FORMAT.md`; `todos.txt` (item 8b).

**Tests:** as for J38: the generic tests cover the sentences, and near misses are added
(the pair's sentence with `and`; the singleton's with `or`; the second element dropped;
operands swapped for the pair). The fixture has at least six valid proofs
(`a is in Singleton(a)`; `x is in UnorderedPair(a, b)` implies `x = a or x = b`;
`Singleton(a) = UnorderedPair(a, a)`; `UnorderedPair(a, b) = UnorderedPair(b, a)`;
`Singleton(a) subseteq UnorderedPair(a, b)`; `Union(Singleton(a), Singleton(b)) =
UnorderedPair(a, b)`) and six invalid ones, among them `Singleton(a) = Singleton(b)`
for constants with no premise, `a is in Singleton(b)` and
`UnorderedPair(a, b) = Singleton(a)`. Mutation-check the new code.

**Done when:** both definitions are citable by title and refuse what the tests list; the
fixture proofs pass and fail as stated; both suites pass on Python 3.12 and 3.13; the PR
report is as for J36.

Status: queued; needs J38 (#167 has merged; both change the tests that pin the list of
definitions); not started. Held with J38 (see there).

### J43 — Red-team the definition facility

**Goal:** Try to break `source/Definitions.py` and the three set definitions the way J3,
J17, J24 and J26 broke other rules: adversarial proofs and unit probes aimed at (i) a
citation accepted that should be refused, (ii) a sentence accepted as a definition that
is not one, (iii) a definition that adds an axiom (a sentence about old symbols that is
provable only with the definition), and (iv) a refusal with a wrong or missing reason.

Cover each class with at least one probe, and report the classes in which nothing was
found:

1. Citation forms: sentences near a definition (operands swapped, an extra conjunct,
   another quantifier order, vacuous `forall`s), bound-variable clashes (names `Y`,
   `Y_1`, `u`, `w` as constants, variables and function arguments), a cited line, a
   citation for something that is not a sentence.
2. Capture: terms that contain the bound variable of the power set's subset clause.
3. Promotion and titles: a theorem that cites a definition, promoted and cited later; a
   theorem titled like a definition. Known: the rule wins and the theorem cannot be
   cited under that title (`# 1: Definition of union` with a trivial proof, then
   `(Definition of union)` cited for the theorem's statement is refused), which is
   safe but a trap; pin the behaviour and recommend, do not fix.
4. `Mutatis mutandis`: repeating a line that cites a definition, with symbols or names
   replaced. Known: `Intersection` to `Union`, `In` to a predicate `R` and `Union` to a
   declared `f` are refused by the rule, and other terms in place of the names are
   accepted; cover the rest (a name replaced by a term that contains a bound name, two
   names exchanged, a range of lines).
5. `WLOG` replay and proofs by cases over a line that cites a definition.
6. Evidence: a theory without the axiom the evidence needs, a `ByProof` that cites the
   definition it is evidence for, a proof with a premise, a declaration that adds a
   fact or a witness line that is a hypothesis, a claim derived below the top level.
7. Declarations: declaring a defined symbol again as a function, relation, constant or
   object, at the top level and inside a subproof, and under another spelling of the
   name.
8. The derived existence claim (`Definition.existence_claim()`): toy definitions built
   as in `pytest_tests/test_definitions.py` whose sentence would be an axiom in
   disguise (a symbol defined by a property no set bounds, a function defined by an
   equation that has no unique solution, a sentence in which the defined symbol also
   appears in the definiens).

Known limitations, do not report: a definition whose evidence or sentence uses another
defined symbol is not supported yet, and a proof file cannot define a symbol (item 8 of
`todos.txt`).

**Allowed scope:** new `pytest_tests/test_definition_red_team.py` and enforced fixture
`tests/testSetTheory/definition_red_team.txt` (each invalid proof says its reason in
its `## Invalid:` line). No edits to `source/`.

**Findings:** a defect is a finding, not a reason to weaken a probe: file the issue
rule 5 asks for with `Owner: Claude` (it is mine), and add a strict expected-failure
test for an invalid proof that is accepted.

**Done when:** every class has probes in the fixture or the pytest module; every
refusal asserts its reason, not only the refusal; the PR lists the classes with their
numbers of probes and what each found; both suites pass on Python 3.12 and 3.13; the
PR report is as for J36.

Status: queued; unblocked (#167 has merged); not started.

### J44 — Declaration or formula: decide by what follows `are` ([#169](https://github.com/axiomtutor/SyLoPy/issues/169))

**Goal:** A premise line, or a clause of a compound `Let`, of the shape
`NAME and NAME are ...` is a declaration or a formula according to what follows `are`,
decided by a rule. Today one word list decides it: `_looks_like_disjointness_formula`
(`source/ProofParser.py`, made for #151) is asked by the plain `X and Y are ...`
declaration step, by `_text_after_is_declaration_start` and by the split of a
coordinated `Let` body. Any other word after `are` is read as a descriptor, so the
clause declares the two names. The owner's decision (comment on #169, 2026-11-23:
"Decide s declaration by what follows `are`.", read as "a declaration") makes it a rule.

| Text | Today | Reads |
| --- | --- | --- |
| `A and B are equal.` after `Let A, B be sets.` | refused: "symbol 'A' is already declared as object" | `A = B` |
| `A and B are not equal.`, `A and B are different.`, `A and B are distinct.` | the same | `not (A = B)` |
| `A and B are equal.` with `A` and `B` not declared | accepted as a declaration of two objects described as "equal", which states no formula | `A = B`, refused as `A = B. (Premise)` is: "constant 'A' is used but has not been declared" |
| `Let A and B be sets, and A and B are equal.` | refused: "symbol 'A' is already declared as object" | the declaration, then the premise `A = B` (as `are disjoint` is read there today) |
| `A and B are disjoint.`, `A and B are not disjoint.`, `A is disjoint from B.` | formulas, since #151 | unchanged, by the rule and not by the list |
| `A and B are sets.`, `A and B are integers.`, `A and B are relations on X.` | declarations | unchanged |

The "Today" entries were produced by running the checker at master `6d91cef`; re-run a
row before relying on it and report any that no longer holds.

**Decisions already made** (do not reopen; if one cannot work, report it as a finding):

1. The rule: what follows `are` decides. The clause is a formula when a formula parser
   of the base logic or of an active theory reads the whole text, and a declaration
   otherwise, as today. A descriptor that nothing reads stays an ordinary typed object
   (`A and B are integers.`, `Let a be an integer.`).
2. The words belong to the theory that owns them. `equal`, `not equal`, `different` and
   `distinct` are equality's, so the base logic's; `disjoint` is set theory's, whose
   phrase patterns already exist and stay there. No list of such words remains in
   `source/ProofParser.py`: `_looks_like_disjointness_formula` goes away, and its three
   users ask the rule.
3. A text that a recipe reads as a declaration and a formula parser reads as a formula
   is a finding, not a choice made silently. None is known.
4. Not in this job: `A is equal to B` and `A equals B`, which are refused today with
   "Unrecognized formula syntax" (the safe direction). Phrases for them are a separate
   request.

**Allowed scope:** `source/ProofParser.py` (the decision, and the base phrases for
equality); `source/SetTheory.py` only so that `disjoint` is read through the rule; the
paragraph of `docs/PROOF_FILE_FORMAT.md` on premises and declarations; the entry for
#169 in `todos.txt`; new `pytest_tests/test_declaration_or_formula.py` and enforced
fixture `tests/testSetTheory/premises_that_are_formulas.txt`. Not `source/ProofLogic.py`
or `source/ProofJustification.py`.

**Tests:** the parse oracle calls the line parsers directly and cannot see this step,
so the cases are at the proof-line level: every row through `pp.parse_proof_text` (the
justification kind, the formula's `repr` and the declarations, as
`pytest_tests/test_compound_declarations.py` does for `disjoint`), and the refusal of
the undeclared row pinned by line, category and message through
`validate_all_proofs.run_multi_proof_file`. The symbolic twin of each reading (`A = B`,
`not (A = B)`) gives the same entry; the existing `disjoint` cases are unchanged; `are`
followed by a descriptor that nothing reads still declares. The fixture has at least
four valid proofs (each reading as a premise after `Let A, B be sets.`, and one in a
compound `Let`) and four invalid ones, each refused for its reason and not for a parse
or declaration error (for example `A = B` claimed from `A and B are different.`). Run
`tools/mutation_check.py` over the new decision code and report mutants made and
survivors.

**Done when:** every row reads as stated; the refusal carries the stated message; no
list of formula words remains in `source/ProofParser.py` (say how you checked); the
tests above pass; `./run_tests.sh` and `./run_tests.sh --suite extended` pass on Python
3.12 and 3.13; the PR report is as for J36.

Status: queued; the owner approved the direction on 2026-11-23; unblocked; not started.

### J45 — Declaration phrases that give the name its kind ([#170](https://github.com/axiomtutor/SyLoPy/issues/170))

**Goal:** Three natural declaration phrases declare the name as a plain `object`, so the
first line that uses it as a statement, a relation or a function is refused by the
kernel's kind check: accurate, but at the use, and without saying that the phrase is the
cause. Give each the kind its working sibling gets. The first row matters most:
propositional logic is the base of every theory, and `Let P be a proposition.` is the
first thing a new user writes.

| Declaration | Later line | Today | Reads |
| --- | --- | --- | --- |
| `Let P be a proposition.` (also `Let P, Q be propositions.`, `a statement`, `statements`, `a propositional variable`, `propositional variables`) | `P or not P. (Premise)` | "symbol 'P' is declared as object, but is used as a proposition" | `P` is a 0-ary predicate, as `Let P be a predicate.` makes it (`docs/PROOF_FILE_FORMAT.md`) |
| `Let X be any set, R be a strict order on X, a, b be in X.` | `R(a, b). (Premise)` | "symbol 'R' is declared as object, but is used as a predicate" | a relation on X with carrier X, as `a strict partial order on X` is read today (`strict order` is another spelling of it) |
| `Let A, B be any set, f be a bijection from A to B, a be in A.` | `f(a) = f(a). (Reflexivity)` | "symbol 'f' is declared as object, but is used as a function" | the typed bijection that `f: A -> B be a bijection` makes |

The "Today" entries were produced by running the checker at master `6d91cef`; re-run a
row before relying on it and report any that no longer holds.

**Decisions already made** (owner, comment on #170, 2026-11-23: "Agreed", to the
suggested direction of the issue; do not reopen):

1. Recipes, not special cases: `proposition`, `statement` and `propositional variable`,
   singular and plural, among the base declaration recipes; `strict order` beside
   `partial order` and `total order` (`RelationDeclarationRecipe` in
   `source/DiscreteMath.py`, or wherever `strict partial order` is registered); and
   `bijection from A to B` beside the typed-bijection recipe (`BijectionDeclarationRecipe`
   in `source/SetTheory.py`).
2. A descriptor that no recipe knows stays an ordinary typed object: `Let a be an
   integer.` keeps working. This job does not refuse unknown descriptors.
3. What the working siblings state does not change, and nothing is renamed. (What the
   corpus's `partial ordering` means is the owner's open question 5 in `todos.txt`.)

**Allowed scope:** the recipes named above and the code they register through;
`docs/PROOF_FILE_FORMAT.md` (the declaration phrases); the entry for #170 in
`todos.txt`; new `pytest_tests/test_declaration_phrase_kinds.py` and enforced fixtures
`tests/testProofs/proposition_declarations.txt` (the base logic) and
`tests/testSetTheory/declaration_phrase_kinds.txt`. Not `source/ProofLogic.py` or
`source/ProofJustification.py`.

**Tests:** every row through `pp.parse_proof_text` (the declared kind and arity, and the
facts the line states) and through the full pipeline; each new spelling gives the same
declarations as its working sibling (`predicate`, `strict partial order`, the
`f: A -> B` form); `Let a be an integer.` still declares an object. The fixtures have
valid proofs that use each name as the kind it was declared (a statement in `P or not P`
and in a proof by cases, a relation `R(a, b)`, a function `f(a)`) and invalid ones, each
refused for its reason and not for a declaration error (a proposition applied to an
argument; a relation used as a term). Run `tools/mutation_check.py` over the new recipe
code and report mutants made and survivors.

**Done when:** every row reads as stated and the siblings are unchanged; the tests above
pass; `./run_tests.sh` and `./run_tests.sh --suite extended` pass on Python 3.12 and
3.13; the PR report is as for J36.

Status: queued; the owner agreed on 2026-11-23; unblocked; not started.

### J46 — Declarations that state their facts: `nonempty`, `family of subsets`, plural `finite` ([#171](https://github.com/axiomtutor/SyLoPy/issues/171), [#181](https://github.com/axiomtutor/SyLoPy/issues/181))

**Goal:** A declaration that says something states it, as J30 made membership
declarations do. Today the first three rows below state no formula, so a proof must
restate what its own declaration said and is refused with a message ("cites ['1'],
which is not defined or not in scope") that does not point at the declaration; and the
plural forms of the finite and infinite declarations state nothing, although the singular
states its fact.

| Declaration | Today | States |
| --- | --- | --- |
| `Let A be a nonempty set.` | no formula | `exists u, In(u, A)` (so that `Existence from 1` opens it) |
| `Let A, B be nonempty sets.` | no formula | the same for each name |
| `Let F be a family of subsets of A.` | no formula | `forall S, (In(S, F) -> S subseteq A)` |
| `Let A, B be finite sets.`, `Let A and B be finite sets.` | no formula | `Finite(A)` and `Finite(B)` |
| `Let A, B be infinite sets.` | no formula | `Infinite(A)` and `Infinite(B)` |
| `Let A, B be finite sets of cardinality 3.` | no formula | `Finite(A)` and `Cardinality(A, 3)`, and the same for `B` |

The singular `finite set`, `infinite set` and `finite set of cardinality n` declarations
state `Finite(A)`, `Infinite(A)` and `[Finite(A), Cardinality(A, n)]` today and do not
change. The "Today" entries were produced at master `6d91cef`; re-run a row before
relying on it and report any that no longer holds.

**Decisions already made** (do not reopen; if one cannot work, report it as a finding):

1. `nonempty` and `family of subsets` state their facts (owner, comment on #171,
   2026-11-23: "Confirmed.", to the request of the issue). The plural forms of a
   descriptor that states its fact in the singular state it for each name; that is
   #181 and needs no decision.
2. A clause with several names states the facts of each, as `Let a, b be in X.` states
   `[In(a, X), In(b, X)]`; a declaration of several clauses states the facts of every
   clause.
3. The two proofs of #171 are accepted: `exists u, In(u, A)` and
   `forall S, (In(S, F) -> S subseteq A)`, each by `Reiteration from 1`. If the kernel's
   `Reiteration` needs the names of bound variables to be those of the issue, state the
   facts with `u` and `S`, and report it.
4. Not in this job: the typed function `f: X -> Y` (the third item of #171; how a
   function is represented in set theory is the owner's open question 7 in `todos.txt`),
   and `a partition of A` and `a set of sets`, which #171 says are in the same state and
   about which the owner has not been asked. Report in the PR what each of the three
   states today, and change nothing.

**Allowed scope:** `source/SetTheory.py` (`FiniteInfiniteSetDeclarationRecipe`, which
already loops over the names of a clause, and the new recipes), and the clause parser in
`source/ProofParser.py` only as far as the plural descriptors need it to reach a recipe;
`docs/PROOF_FILE_FORMAT.md` (the declaration phrases); the entries for #171 and #181 in
`todos.txt`; new `pytest_tests/test_declaration_facts.py` and enforced fixture
`tests/testSetTheory/declaration_facts.txt`. Not `source/ProofLogic.py` or
`source/ProofJustification.py`.

**Tests:** every row through `pp.parse_proof_text` (the formulas the line states), with
its singular or sibling twin; the two proofs of #171 and the proof of #181 through the
full pipeline; a declaration with several clauses (`Let A, B be sets, C be a nonempty
set.`). The fixture has at least four valid proofs that use the stated facts (an element
of a nonempty set named by `Existence from 1`; a member of a family used as a subset;
`Finite(B)` for the second name of a plural declaration) and four invalid ones, each
refused for its reason and not for a parse error (`exists u, In(u, B)` from
`Let A be a nonempty set.`; `A` nonempty from `Let A be a set.`; `Finite(B)` from
`Let A be a finite set, B be a set.`). Run `tools/mutation_check.py` over the new recipe
code and report mutants made and survivors.

**Done when:** every row states what it says; the three declarations that #171 leaves
open are reported and unchanged; the tests above pass; `./run_tests.sh` and
`./run_tests.sh --suite extended` pass on Python 3.12 and 3.13; the PR report is as for
J36.

Status: queued; the owner confirmed `nonempty` and `family of subsets` on 2026-11-23;
unblocked; not started.

### Planned, not yet specified

Each waits for the jobs named, and is specified when they have merged:

- **Set displays as terms** (after J37 and J42): `{a}` and `{a, b}` read
  `Singleton(a)` and `UnorderedPair(a, b)`, so that `x is in {a, b}` is the atom
  `In(x, UnorderedPair(a, b))` and no longer `x = a or x = b`, and `Y = {a, b}` reads
  `Y = UnorderedPair(a, b)`. Three or more elements and the builders
  `{u in X: P(u)}` need a decision first (nested unions of singletons; a binder term,
  which is a kernel change).
- **The ordered pair** (after J42): `(a, b)` reads `{{a}, {a, b}}`, the theorem
  `(a, b) = (c, d) iff a = c and b = d` is proved, and the abstract `Pair` and
  `pair(...)` go away.
- **The Cartesian product**: the facility must first allow evidence and sentences that
  use earlier definitions (item 8(d) of `todos.txt`; mine), and the ordered pair must
  exist. Then `A cross B` is defined by Separation over a power set, and its laws are
  added to the library of J39 and J40.
- **Owner questions, not jobs:** definitions written in proof files, functions as sets
  of pairs or as symbols, and what the declarations of a typed function, `a partition of
  A` and `a set of sets` state (`todos.txt`, The plan, Open owner questions).

## Deferred queue

Set theory is the current development priority until it is fully functional.
J35 remains in this file with its full specification, but is paused during that
work. Do not begin it unless the owner changes the priority or explicitly
re-queues it.

Start a job only after the pull request that adds it has merged, so the
instructions and implementation can be read together. Do not resume completed
or archived tasks unless the owner re-queues them.

### J35 — Basic divisibility identity proofs

**Goal:** Add checked proof examples for four elementary divisibility facts using only the
integer laws already present in `source/NumberTheory.py`:

1. If `Int(a)`, then `a|a`.
2. If `Int(a)`, then `One|a`.
3. If `Int(a)`, then `a|Zero`.
4. If `Int(a)` and `a|b`, then `a|Neg(b)`.

These correspond to the four candidates in [issue #98](https://github.com/axiomtutor/SyLoPy/issues/98).
The missing laws listed there are now present in `INT_AXIOMS`: left/right multiplicative
identity, left/right zero annihilation, and compatibility of multiplication with additive
inversion. This job is proof coverage only; it does not authorize new axioms.

**Do:** add one enforced fixture, `tests/testNumberTheory/divisibility_basic_properties.txt`,
with one proof for each result, and a focused runner test
`pytest_tests/test_divisibility_basic_properties.py` that asserts all four proofs pass.
Use the existing integer axioms and ordinary inference rules, making the witnesses explicit.
The final proof should obtain `Neg(b)` with witness `Neg(m)` from a witness `m` for
`a|b`.

**Allowed scope:** the new fixture, the new focused pytest module, and this tracker.
Do not edit `source/NumberTheory.py`, alter existing fixtures, add axioms, or change
the meaning of divisibility. A failure that reveals a checker defect is a finding; do
not weaken the proof or tests to hide it.

**Done when:** all four proofs pass under the fixture runner; the focused pytest test
asserts the exact four proof numbers and reports any failure; the default CI suite and
all proof-fixture suites pass; and the PR confirms no production code or existing
expectations changed.

Status: Deferred by owner direction of 2026-11-05 while set theory is the
current development priority. The full job specification and proof-only scope
are retained unchanged. No pull request has been opened for it. A ChatGPT branch,
`chatgpt/j35-divisibility-basic-identities` (two commits of 2026-11-03; 89 commits
behind master on 2026-11-22), holds the two files named above; it has never been
reviewed or run by Claude, and nobody touches it. Resume only when the owner changes
the priority or explicitly re-queues J35.

## Recent dispositions

- **J31:** PR #148 closed without merge; the dedicated red-team expansion is not active.
- **J32:** relation-subset examples and their focused runner are implemented.
- **J33:** arbitrary-property WLOG implementation and focused coverage are complete; optional standalone target/twin fixtures remain.
- **J34:** closed-axiom implementation and focused coverage are complete; optional standalone red-team fixtures remain.

Original specifications and their final dispositions are preserved in the archive.

## Completed jobs

| Job | Title | Result |
| --- | --- | --- |
| J0 | CI shows why a fixture or test failed | merged ([PR #87](https://github.com/axiomtutor/SyLoPy/pull/87)) |
| J1 | Set-theory proofs, batch 1 | merged ([PR #88](https://github.com/axiomtutor/SyLoPy/pull/88)) |
| J2 | Refresh proof-format documentation | merged ([PR #89](https://github.com/axiomtutor/SyLoPy/pull/89)) |
| J3 | Red-team the set-theory rules | merged ([PR #90](https://github.com/axiomtutor/SyLoPy/pull/90)) |
| J4 | Parse oracle: more phrases | merged ([PR #91](https://github.com/axiomtutor/SyLoPy/pull/91)) |
| J5 | Order and relation proofs | merged ([PR #92](https://github.com/axiomtutor/SyLoPy/pull/92)) |
| J6 | Number-theory proofs and a missing-axiom list | merged ([PR #97](https://github.com/axiomtutor/SyLoPy/pull/97)) |
| J7 | Mutation-check tool | merged ([PR #99](https://github.com/axiomtutor/SyLoPy/pull/99)) |
| J8 | Negative set phrases in the parser | merged ([PR #100](https://github.com/axiomtutor/SyLoPy/pull/100)) |
| J9 | Union, intersection, and disjointness phrases | merged ([PR #101](https://github.com/axiomtutor/SyLoPy/pull/101)) |
| J16 | First-order logic classics | merged ([PR #111](https://github.com/axiomtutor/SyLoPy/pull/111)) |
| J17 | Red-team the quantifier and scope rules | merged ([PR #112](https://github.com/axiomtutor/SyLoPy/pull/112)) |
| J18 | Equivalence classes and partitions | merged ([PR #113](https://github.com/axiomtutor/SyLoPy/pull/113)) |
| J19 | Fix the J16 and J18 review findings | merged ([PR #114](https://github.com/axiomtutor/SyLoPy/pull/114)) |
| J20 | Fix the J17 review findings | merged ([PR #115](https://github.com/axiomtutor/SyLoPy/pull/115)) |
| J21 | Reject ambiguous parity shorthand under quantifiers | merged ([PR #117](https://github.com/axiomtutor/SyLoPy/pull/117)) |
| J22 | Centralize parser extension assembly | merged ([PR #118](https://github.com/axiomtutor/SyLoPy/pull/118)) |
| J23 | Expand informational relation and order proofs | merged ([PR #119](https://github.com/axiomtutor/SyLoPy/pull/119)) |
| J24 | Red-team Mutatis mutandis | merged ([PR #123](https://github.com/axiomtutor/SyLoPy/pull/123)) |
| J25 | Where stage 1 of Mutatis mutandis stops | merged ([PR #124](https://github.com/axiomtutor/SyLoPy/pull/124)) |
| J26 | Red-team Mutatis mutandis stages 2 and 3 | merged ([PR #135](https://github.com/axiomtutor/SyLoPy/pull/135)) |
| J27 | Where Mutatis mutandis stops, second look | merged ([PR #139](https://github.com/axiomtutor/SyLoPy/pull/139)) |
| J28 | Register every elaborated declaration in ProofContext | merged ([PR #142](https://github.com/axiomtutor/SyLoPy/pull/142)) |
| J29 | Consolidate the legacy natural-number fixture runner | merged ([PR #143](https://github.com/axiomtutor/SyLoPy/pull/143)) |
| J30 | Declaration lines must not drop or absorb text | merged ([PR #146](https://github.com/axiomtutor/SyLoPy/pull/146)) |


## Rules for new jobs

1. Add an explicit job before starting delegated work. Each job must state its goal, allowed scope/files, tests or fixtures to add, and an observable “Done when” condition.
2. Use one small branch and one PR per job; normally keep a PR to about 400 changed lines or fewer. Keep no more than three delegated PRs open at once. The owner merges.
3. Treat CI as the test run. Keep the PR a draft until its stated completion criteria pass. Report the exact tested commit, CI run, test totals, coverage, enforced fixtures, informational fixtures, and remaining failures; never infer results from an uninspected run.
4. `source/ProofLogic.py` and `source/ProofJustification.py` are kernel-owned: ChatGPT does not edit them (owner, 2026-11-18), and a kernel defect is a finding for Claude. Do not alter existing tests, fixtures, or parser-oracle expectations merely to make a change pass. Do not start items marked as requiring owner approval in `todos.txt`.
5. A checker defect is a finding, not a reason to weaken a test. File a focused issue with the smallest proof, exact accepted/rejected behavior or message, suspected rule/file, and `Owner: Claude` when the kernel is involved. Include strict expected-failure regression coverage for an invalid proof that is incorrectly accepted, following the collaboration guide.
6. A job is complete only after its PR is merged and the status table above is updated. Preserve its full specification and task-specific notes in the archive rather than keeping completed instructions in this live tracker.

Historical note: this tracker replaces the former long-form queue. Archived job text is retained for provenance, but current repository guidance and explicit owner decisions take precedence.

## Current project infrastructure

- The default CI/local project run is named `default`; it runs the standard
  Python tests and all proof fixture suites.
- The slower audit/adversarial tests are named `extended`; they are not run by
  `./run_tests.sh` unless `--suite extended`, `--suite all`, or the compatibility
  flag `--extended` is requested.
- There are currently no active pytest `xfail` tests or strict expected-failure
  cases. Standalone J33/J34 fixture expansion remains optional coverage work
  rather than an unresolved correctness blocker.
