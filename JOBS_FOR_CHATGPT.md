# Delegated Jobs for ChatGPT

This file is the live queue and concise disposition ledger. Stable collaboration rules are in [`AGENT_COLLABORATION.md`](AGENT_COLLABORATION.md); current status and owner decisions are in [`todos.txt`](todos.txt). Full historical task specifications are preserved in [`docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md).

## Active queue: set theory

Owner direction of 2026-11-05: set theory is the priority until it is fully
functional. J36–J40 come from a probe of standard set-theory proofs against
[PR #167](https://github.com/axiomtutor/SyLoPy/pull/167), which gives `Union`,
`Intersection`, `PowerSet`, `CartesianProduct` and `Pair` their meaning (five
zero-premise rules cited as `Definition of union` and so on). The "Today"
entries were produced by running `pp.parse_formula` and the checker at that
commit; re-run a row before relying on it and report any that no longer hold.

Order: J36 and J37 may run in parallel (different parsers, separate oracle
files). J38 and J39 start after J36 has merged, J40 after J38 and J39. J36, J38,
J39 and J40 also need PR #167 merged; J37 does not. A job starts only after the
PR that adds it has merged, as below.

### J36 — Nested set-operation terms

**Goal:** A set-operation term may contain other terms, so that the laws of set
algebra can be written in proof text. `try_parse_set_term` (`source/SetTheory.py`;
the set theory's `term_parsers` entry, also called by every set phrase) reads only
a bare name, `∅`, `X union Y`, `X intersection Y`, `X cross Y`,
`the power set of X` and `pair(x, y)`, with bare names as operands.

| Surface text | Today |
| --- | --- |
| `x is in A union B union C` | refused: "Unrecognized formula syntax" |
| `x is in (A union B) intersection C` | refused |
| `A union (B union C) = (A union B) union C` | refused: "Unrecognized term syntax" |
| `x is in the power set of (A union B)` | refused |
| `x is in Union(A, B)`, `x is in f(A)` | refused, although `In(x, Union(A, B))` is accepted |
| `pair(a, pair(b, c)) = pair(d, e)` | the outer `pair` is not read as `Pair`; the proof is refused with "function 'pair' is used but has not been declared" (`Pair(a, Pair(b, c))` works) |

**Decisions already made** (do not reopen; if one cannot work, report it as a
finding):

1. Parentheses group. An operand is a name, `∅` or `the empty set`, a
   parenthesised set term, `the power set of <operand>`, `pair(<term>, <term>)`,
   or a function application `f(t1, ..., tn)` that the ordinary term parser
   accepts, so `Union(A, Union(B, C))` and `f(A)` are set terms in phrases too.
2. A chain of one operation, `A union B union C` or
   `A intersection B intersection C`, reads left-nested:
   `Union(Union(A, B), C)`.
3. A chain that mixes operations (`A union B intersection C`) and a chain of
   `cross` with more than two operands (`A cross B cross C`) are refused, with a
   message that contains the word "parenthes". There is no precedence between
   operations, and `A cross B cross C` is not read as triples.
4. `pair` reads as `Pair` whatever its arguments are.
5. A name bound by an enclosing quantifier is a variable and any other name a
   constant, as `_name_term` does today. No existing reading, oracle expectation
   or fixture changes.

**Allowed scope:** `source/SetTheory.py` (the term parser and its callers, not
the rules); new `parse_oracle/set_operations_nested.txt`,
`pytest_tests/test_set_operation_nesting.py` and enforced fixture
`tests/testSetTheory/set_operation_terms_nested.txt`; the set-operation paragraph
of `docs/PROOF_FILE_FORMAT.md`; the "cannot yet be nested" caveat in `todos.txt`.
Not `source/ProofLogic.py` or `source/ProofJustification.py`.

**Tests:** an oracle case for every row above (the reading written first, in plain
logic, such as `In(x, Union(Union(A, B), C))`); one each for a chain of
`intersection`, for a nested term under a bound variable (`forall x, ...`), and
`expect: REJECT` for a mixed chain, a `cross` chain, an unbalanced parenthesis and
`()`. The fixture has at least four valid proofs that apply the definition rules of
#167 to nested terms (union is associative, as two subset proofs; a three-fold
union unfolded; a member of the power set of a union; a nested pair) and four
invalid ones, each refused by a definition rule and not by a parse error. Run
`tools/mutation_check.py` over the new parser branches and report mutants made and
survivors.

**Done when:** every row reads as stated; the refusals carry the stated message;
the tests above pass; `./run_tests.sh` and `./run_tests.sh --suite extended` pass on
Python 3.12 and 3.13; the PR gives the tested commit, CI run and totals as
`AGENT_COLLABORATION.md` requires. If it passes about 400 changed lines, send the
fixture as a second PR.

Status: queued; needs PR #167 merged.

### J37 — Membership wordings: the missing halves

**Goal:** The membership phrases are a ragged grid: several have a positive form
without the negative one, or the reverse. Below, `S` is any set term other than
`A union B` and `A intersection B` (`A`, `A cross B`, `the power set of A`,
`the empty set`), `U` is `the union of A and B` and `I` is
`the intersection of A and B`. "ok" means accepted today (checked with
`pp.parse_formula` at #167); "add" means refused today and to be added; "stays"
means refused today and to stay refused.

| Phrase (`x …`) | `S` | `A union B` | `A intersection B` | `U` | `I` |
| --- | --- | --- | --- | --- | --- |
| `is in` | ok | ok | ok | ok | add |
| `is not in` | ok | ok | ok | add | ok |
| `belongs to` | add | ok | stays | add | ok |
| `does not belong to` | ok | ok | ok | add | add |
| `is an element of` | ok | ok | ok | add | add |
| `is not an element of` | add | add | add | add | add |
| `is a member of` | add | add | add | add | add |
| `is not a member of` | add | add | add | add | add |

**Decisions already made:**

1. Readings. With `S`, `A union B` or `A intersection B` a phrase reads
   `In(x, <term>)`, and a "not" or "does not" phrase reads its negation. With `U`
   it reads `In(x, A) or In(x, B)`, with `I` it reads `In(x, A) and In(x, B)`,
   negated for the "not" phrases. The one existing exception stays:
   `x belongs to A union B` is the disjunction (oracle case
   `j4-union-membership-nested`) although `x is in A union B` is
   `In(x, Union(A, B))`. Whether the two should agree now that PR #167 gives
   `Union` a meaning is an owner question; no existing reading changes in this job.
2. Refused on purpose: `x belongs to A intersection B` (its reading depends on that
   owner question), `A contains x` (it can mean "x is a subset of A"; `A does not
   contain x` stays as it is), `x lies in A`, and the Unicode forms `x ∈ A` and
   `x ∉ A` (a Unicode alias layer is an owner decision).
3. Implement the phrases as one table of (phrase, polarity) applied to the operand
   readings, not as one regular expression per cell, so that the grid cannot
   become ragged again.

**Allowed scope:** `source/SetTheory.py` (the membership phrase parsers); new
`parse_oracle/set_membership_wordings.txt`,
`pytest_tests/test_membership_wordings.py` and enforced fixture
`tests/testSetTheory/membership_wordings.txt`; the membership-phrase paragraph of
`docs/PROOF_FILE_FORMAT.md`; `todos.txt`. Not kernel files, existing fixtures or
existing oracle expectations.

**Tests:** an oracle case for every "add" cell (readings in plain logic), and
`expect: REJECT` cases for the forms of decision 2. The pytest module enumerates
all forty cells (phrase × operand) and compares each with a formula built from `fl`
and `st` independently of the parser: `ok` cells must keep their reading, `add` cells
must have the reading of decision 1, the `stays` cell and the forms of decision 2
must be refused. The fixture has one subset proof and one proof by cases that use
three of the new phrases, and two invalid proofs.

**Done when:** all forty cells behave as the table says; the oracle has a case for
each added cell; no existing expectation changed; both suites pass on Python 3.12
and 3.13; the PR report is as for J36.

Status: queued.

### J38 — Set difference

**Goal:** Add the relative difference as a declared operation with a definition
rule, following PR #167 rule for rule. Today `x is in A setminus B` and
`Difference(A, B)` are refused (there is no such symbol), and a difference exists
only as the theorem "The difference of two sets exists" in the informational
`tests/setTheoryProofs/set_operation_foundations.txt`, so `A setminus B subseteq A`
or De Morgan's laws cannot be stated in a proof.

**Decisions already made:**

1. The symbol is `Difference`, binary, declared in `SET_DECLARATIONS` beside
   `Union`. The surface infix is `A setminus B` (the same shape as `A union B`,
   and nestable after J36) and the function form is `Difference(A, B)`. Not
   `minus` (integer subtraction will want it, as `cross` is not `times`), not
   `\`, and no complement: an absolute complement needs a universe and ZF has
   none. The complement of B in A is `A setminus B`.
2. `(Definition of difference)`, also spelled `Difference definition` and
   `Set difference definition`, is a zero-premise rule cited for
   `forall u, (In(u, Difference(S, T)) iff (In(u, S) and not In(u, T)))`, for any
   terms, with or without leading `forall`s, with the biconditional in either
   order, and for nothing else. It has the acceptance policy, refusal message
   and `reason` text, and the soundness comment of the five rules of #167 (read
   `_OperationDefinitionRule` and the section comment above it first). It is
   conservative: ZF proves that exactly one set has the stated members
   (Separation, Extensionality).
3. Like the union and intersection rules it has no quantifier of its own, so it
   needs no capture condition.

**Allowed scope:** `source/SetTheory.py` (declaration, rule, registration, the
infix in the term parser); `source/ProofJustification.py` only for the new entries
of the citation `placeholders` table, exactly as #167 did (this paragraph is the
coordination the collaboration guide asks for there; nothing else in that file
changes); new `parse_oracle/set_difference.txt`,
`pytest_tests/test_set_difference_definition.py` and enforced fixture
`tests/testSetTheory/set_difference_definition.txt`; `docs/PROOF_FILE_FORMAT.md`
(the rule table and the table of definition sentences); `todos.txt`.

**Tests:** `pytest_tests/test_set_operation_definitions.py` is the model. Accepted:
the sentence with and without `forall`, in both biconditional orders, for any terms
(nested ones too) and any binder name. Refused, each with its own test: `or` for
`and`, `not` on the first operand, the operands swapped, one direction only, a
true sentence that is not the definition, a cited line. Also registration and
spelling tests, the refusal-message test, and a test that a proof cannot declare
`Difference` again (extend `SYMBOLS_OF_THE_DEFINITIONS` and its test in that
file). The fixture has at least five valid proofs (the definition in each accepted
form, `A setminus B subseteq A`, `A setminus A = EmptySet`, a promoted theorem
reused by title) and ten invalid ones, each refused by the definition rule. Run
`tools/mutation_check.py` over the new rule and report mutants made and survivors.

**Done when:** `x is in A setminus B` reads as `In(x, Difference(A, B))`; the rule
accepts and refuses exactly as listed; every invalid fixture proof is refused by the
definition rule; both suites pass on Python 3.12 and 3.13; the PR report is as for
J36.

Status: queued; needs PR #167 and J36 merged.

### J39 — Laws of set algebra, batch 1: union and intersection

**Goal:** The standard laws as proofs, each a promoted theorem that later proofs in
the same file cite by its title. One enforced multi-proof file,
`tests/testSetTheory/set_algebra_laws.txt`, using only the definition rules of #167,
`Set property`, `Set equality`, subset proofs and the ordinary rules, with each law
stated in the surface syntax (nested terms from J36):

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

**Findings:** if a law cannot be proved because of a checker limitation, do not
weaken it and do not leave a failing proof: file the focused issue that rule 5
asks for (smallest proof, exact message), leave that law out and list it in the PR.
One limitation is known: Conjunction Introduction takes exactly two lines, so a flat
`P and Q and R` cannot be derived (item 8 of Remaining work in `todos.txt`, once #167
has merged); nest the conjunction, `(P and Q) and R`, in the proof of a law.

**Allowed scope:** the new fixture, a new `pytest_tests/test_set_algebra_laws.py`
that asserts the exact list of titles and that every proof passes, and a short list
of the laws in `docs/PROOF_FILE_FORMAT.md`. No edits to `source/`.

**Tests:** besides the valid proofs, one invalid proof for each of these false
laws, refused at the step that would need the false fact and not for a parse,
declaration or scope reason: `A union (B intersection C) = (A union B) intersection
C`, `A intersection (B union C) = (A intersection B) union C`,
`A union B = A intersection B`, and `A subseteq B` iff `A union B = A`.

**Done when:** every listed law is a passing enforced proof under its own title, or a
finding with its issue; the pytest module asserts the titles; the invalid proofs are
refused as described; both suites pass on Python 3.12 and 3.13; the PR report is as
for J36.

Status: queued; needs PR #167 and J36 merged.

### J40 — Laws of set algebra, batch 2: difference, power set, product

**Goal:** The same, appended to `tests/testSetTheory/set_algebra_laws.txt` (the
numbering continues, so that these proofs can cite the laws of J39 by title) and to
the title list of `pytest_tests/test_set_algebra_laws.py`, for:

- `A setminus B subseteq A`; `A setminus A = EmptySet`; `A setminus EmptySet = A`;
- De Morgan's laws: `A setminus (B union C) = (A setminus B) intersection
  (A setminus C)` and `A setminus (B intersection C) = (A setminus B) union
  (A setminus C)`;
- `A setminus (A setminus B) = A intersection B`;
- `A subseteq B` implies `PowerSet(A) subseteq PowerSet(B)`, and
  `PowerSet(A intersection B) = PowerSet(A) intersection PowerSet(B)`;
- `Pair(a, b)` belongs to `A cross B` iff `a` is in `A` and `b` is in `B`.

**Allowed scope, tests, findings and done when:** as for J39, with the false laws
`A setminus (B setminus C) = (A setminus B) setminus C`,
`PowerSet(A union B) = PowerSet(A) union PowerSet(B)`, `A cross B = B cross A`, and
`A subseteq B` implies `PowerSet(B) subseteq PowerSet(A)` as the invalid proofs.

Status: queued; needs J38 and J39 merged.

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
are retained unchanged. The proof work has not begun; resume only when the
owner changes the priority or explicitly re-queues J35.

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
4. `source/ProofLogic.py` and `source/ProofJustification.py` are kernel-owned; do not edit them without coordination. Do not alter existing tests, fixtures, or parser-oracle expectations merely to make a change pass. Do not start items marked as requiring owner approval in `todos.txt`.
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
