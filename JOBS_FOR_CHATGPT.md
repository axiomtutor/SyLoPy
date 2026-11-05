# Delegated Jobs for ChatGPT

This is the concise delegated-work tracker. Stable collaboration rules live in [`AGENT_COLLABORATION.md`](AGENT_COLLABORATION.md); current feature status, invariants, design decisions, and owner-gated work live in [`todos.txt`](todos.txt). Use PRs and issues for implementation details and discussion.

Completed job specifications and their original task instructions are preserved in [`docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md). That file is historical context, not an active work queue.

## Current queue

Start a job only after the pull request that adds it has been merged, so the instructions and implementation can be read together. Do not resume a completed or archived task unless the owner explicitly re-queues it or provides new direction.

### J31 — Red-team "a relation on X is a subset of X × X"

**Goal:** `Let R be a ... relation on X` now states `forall x, forall y, (R(x, y) -> (In(x, X) and In(y, X)))` as a formula of its line (owner decision of 2026-10-29). Find out whether a proof can derive more than that, or less. Read first (read only): `source/DiscreteMath.py` (`relation_subset_formula` and the recipe), `docs/PROOF_FILE_FORMAT.md` section 5 and the note on declaration lines in the Mutatis mutandis section, `tests/testDiscreteMath/relation_subset.txt` (10 cases), `pytest_tests/test_relation_subset_sugar.py`.

**Do:** at most 16 cases in the new `tests/testDiscreteMath/red_team_relation_subset.txt` (enforced). Each invalid case has a valid twin that differs from it only in the condition its title names, and is pinned by line, category and reason in the new `pytest_tests/test_red_team_relation_subset_reasons.py`, in the manner of `pytest_tests/test_mutatis_mutandis_red_team_terms_symbols_reasons.py`. Areas:

1. Scope: the formula cited after the subproof that declared the relation has ended; two sibling subproofs that declare `R` on different carriers; `R` declared again in a nested subproof on another carrier (say in the PR whether the checker accepts that, and what the formula of each line then says).
2. Names: a relation or a carrier named `x`, `y`, `u` or `v` (the bound variables are then others, see `relation_subset_formula`); the formula written with other bound variable names, or with the conjuncts swapped, is a different formula and is refused.
3. Which fact: several relations in one declaration, with the formula of the wrong one cited; membership derived in another set; a conclusion about a term that nothing relates; a term related only by a derived fact (`Relation Symmetry`, `Relation Transitivity`) rather than a declared one; a plain binary predicate (`Let P be a binary predicate`) states nothing about any set.
4. Where the carrier is declared: in the same statement, on an earlier line, in an enclosing proof, and after the relation (refused: "has not been declared yet").
5. Mutatis mutandis: an argument that cites a relation declaration, repeated for a relation on the same carrier (accepted), for a relation on another carrier (refused, `bad_reference`), and with the carrier itself replaced by another set that has its own relation declared (say in the PR whether it is accepted, and whether that is right).
6. Promotion: the fixture runner prints "was not promoted" for the proofs of `relation_subset.txt`, because their relation declarations record a carrier (`todos.txt`, item 8; promotion over declared structure is owner-gated). Check that the refusal is the same whether or not a relation rule is used in the proof, and whether the same derivation promotes, and applies to another relation, when `R` is a plain binary predicate and the formula is an explicit premise. Report what happens; change nothing.

**Allowed scope:** the two new files and this tracker. A defect is a finding, not a reason to change a test: file an issue as rule 5 says (`Owner: Claude` if the kernel is involved) and add the strict expected-failure case.

**Done when:** every invalid case is refused at its pinned line for its pinned reason, every twin is accepted, each finding has an issue, the PR description says what areas 1, 5 and 6 turned out to accept, and CI passes.

Status: current master has baseline coverage in `relation_subset.txt` and the focused relation-subset pytest modules. The dedicated J31 red-team expansion is in draft PR #148 and is not merged.

### J32 — Proofs that use the relation-subset fact

**Goal:** Show the new declaration fact in use, in the order and equivalence proofs where a membership premise was written only because `R(a, b)` did not give it.

**Do:** in the new informational file `tests/testDiscreteMath/relation_subset_examples.txt`, at least 5 proofs, each a theorem a textbook states about a relation on X for terms known only through `R`, and each using the formula (Universal Instantiation, Universal Modus Ponens, Conjunction Elimination) where the older fixtures state `a, b be in X` for no other reason. Examples: from `R(a, b)` for an equivalence relation, `R(a, a)` and `R(b, b)` with `a` and `b` declared as objects; the same for a partial order; `R(a, b)` and `R(b, c)` for a transitive relation put `c` in X; for a symmetric relation, `R(a, b)` puts `b` in X. Survey `tests/testDiscreteMath/*.txt` and `tests/setTheoryProofs/*.txt` for proofs that declare `a, b be in X` only to feed `Relation Reflexivity`, and list them in the PR with the shorter proof written for each (leave the originals as they are). Say how many of the proofs would be shorter by a rule that instantiates both variables of the formula and applies it in one step (today it takes Universal Instantiation and then Universal Modus Ponens); the owner decides whether to ask for that, and nothing here starts it.

**Allowed scope:** the new file, a file test in the new `pytest_tests/test_relation_subset_examples.py` that runs it and asserts every proof passes (as `pytest_tests/test_mutatis_mutandis_terms_symbols_examples.py` does), and this tracker.

**Done when:** at least 5 proofs pass in CI, the PR lists the older proofs that could be shortened and gives the count asked for above, and CI shows no failing test.

Status: implemented with `tests/setTheoryProofs/relation_subset_examples.txt`
and `pytest_tests/test_relation_subset_examples.py`.

### J33 — Target proofs for arbitrary-property WLOG

**Goal:** The owner approved WLOG for arbitrary properties on 2026-10-30. Today the cited disjunction must be equalities that differ in one constant (`x = a or x = b`, as in `tests/testSetTheory/unique_pairing_with_wlog.txt`). The next version will accept a disjunction whose alternatives are the chosen case with names exchanged, for example `a <= b or b <= a`, and replay the rest of the block with the names exchanged. Write the proofs you would want to be able to write before the rule exists (target files come first in this project).

**Do:** read first (read only): the WLOG parts of `docs/PROOF_FILE_FORMAT.md` and `todos.txt`, and the cases of `tests/testSetTheory/unique_pairing_with_wlog.txt` and `tests/setTheoryProofs/zfc_remaining_axioms.txt`. Then write, in the new file `tests/targets/wlog_arbitrary_properties.txt` (a new directory the fixture runner does not scan; add a two-line `tests/targets/README.md` saying so), the following in the existing syntax (`N. <the chosen disjunct>. (WLOG, M)`):

1. 8 to 12 valid target proofs, each a theorem a textbook proves "without loss of generality", each citing a disjunction that is not a list of equalities differing in one constant: two names exchanged in a relation or predicate (`a <= b or b <= a`, `P(a, b) or P(b, a)`); membership in two sets (`In(x, A) or In(x, B)`) with a conclusion symmetric in `A` and `B`; two pairs exchanged at once; three alternatives; the chosen disjunct in the middle of the disjunction.
2. 6 to 8 invalid targets, each with a valid twin that differs only in the condition its title names: a step that uses a fact about `a` that has no exchanged counterpart about `b`; a conclusion that mentions `a` but not `b`; an alternative that is not the chosen case with names exchanged (`a <= b or b < a`); an exchange that would capture a bound variable; an exchanged name that is not declared; a WLOG line whose formula is not one of the disjuncts.

To make the targets trustworthy, write for each valid target a twin with the other cases proved by hand (the same proof, no WLOG), in the new informational file `tests/setTheoryProofs/wlog_arbitrary_properties_twins.txt`. Every twin must pass today; it is the proof that the replay the target relies on is a real proof. Add `pytest_tests/test_wlog_arbitrary_properties_twins.py`, in the manner of `pytest_tests/test_mutatis_mutandis_terms_symbols_examples.py`, asserting that every twin passes.

**Allowed scope:** the three new files, the new test, and this tracker. Do not edit source files. If a target already passes, or an invalid target is accepted by the checker as it is, that is a finding: file an issue (rule 5).

**Done when:** the numbers above are met, every twin passes in CI, and the PR description says, for each target, which reading of "the rest of the block is replayed with the names exchanged" it relies on (a swap of two names, or any one-to-one renaming of names; whether symbols may be exchanged too), so the owner and Claude can choose the semantics. CI shows no failing test.

Status: implementation complete; focused arbitrary-property WLOG coverage exists
in the WLOG test modules. Standalone target-fixture expansion remains optional.

### J34 — Red-team "an `(Axiom)` line in set theory states nothing"

**Goal:** Set theory now lists no axiom for `(Axiom)` and closes its axiom list (`TheoryEnvironment.axioms_closed`; owner decision of 2026-10-30), so an `(Axiom)` line is refused in every set-theory proof and the four set axioms are cited by name (`Axiom of pairing`, `Axiom of union`, `Axiom of power set`, `Axiom of infinity`). A refusal says which rules of the proof justify the formula outright (`cite it by name instead: (...)`). Find out whether an `(Axiom)` line can still be accepted in set theory, or whether the pointer can be wrong. Read first (read only): `pytest_tests/test_closed_axiom_list.py`, `tests/testSetTheory/axioms_cited_by_name.txt`, section 8 of `docs/PROOF_FILE_FORMAT.md`, and the comments on `ProofValidator.axioms_closed` and `ProofValidator._cited_by_name` in `source/ProofLogic.py`.

**Do:** at most 12 cases in the new `tests/testSetTheory/red_team_closed_axiom_list.txt` (enforced). Each invalid case has a valid twin that differs from it only in the condition its title names, and is pinned by line, category and reason in the new `pytest_tests/test_red_team_closed_axiom_list_reasons.py`, in the manner of `pytest_tests/test_mutatis_mutandis_red_team_terms_symbols_reasons.py`. Areas:

1. Where the line is: inside a subproof, in a `Proof by Cases` case, in a WLOG case block and in the suffix that WLOG replays, and in an argument that `Mutatis mutandis` repeats (an `(Axiom)` line is a hypothesis, so the repetition must be refused; say what the message is).
2. Disguises: an axiom written with other bound-variable names, with the conjuncts or disjuncts swapped, with set-builder or enumeration sugar that elaborates to the axiom's formula, and an instance of an axiom (Union or Power Set at a declared set) cited with `(Axiom)`. Each is refused; say what the pointer says.
3. The pointer: a formula that one rule justifies is pointed to it, and following the pointer is accepted; a formula that two rules justify names both, once each; a formula that a promoted theorem states names the theorem's title; a formula that nothing justifies has no pointer.
4. Combined theories: in the default environment a number-theory axiom is still cited with `(Axiom)` and a set axiom is not; a proof checked with `check_proof_text(text, axioms=[F])` accepts `(Axiom)` for `F` and for nothing else.
5. Promotion: a theorem proved from axioms cited by name requires rules, not axioms (`required_rules`, `required_axioms` empty); it cannot be cited in a proof that does not allow those rules. Report what happens; change nothing.

**Allowed scope:** the two new files and this tracker. A defect is a finding, not a reason to change a test: file an issue as rule 5 says (`Owner: Claude`, since the kernel is involved) and add the strict expected-failure case.

**Done when:** every invalid case is refused at its pinned line for its pinned reason, every twin is accepted, each finding has an issue, the PR description says what areas 1 and 5 turned out to accept, and CI passes.

Status: implementation and focused closed-axiom coverage exist; standalone
fixture red-team expansion remains optional.



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

Status: queued. Do not begin implementation until the PR adding this job is merged.

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
