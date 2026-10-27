> **Historical archive.** Snapshot captured on 2026-10-26 when all jobs in this queue had merged. The detailed job definitions, rules, and verified proof patterns below are preserved for provenance only; they are not authorization to restart work. For authoritative current guidance, use the [master delegated-job tracker](https://github.com/axiomtutor/SyLoPy/blob/master/JOBS_FOR_CHATGPT.md), [master collaboration guide](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md), [master TODO ledger](https://github.com/axiomtutor/SyLoPy/blob/master/todos.txt), and current PRs/issues.

---

# Jobs for ChatGPT

The owner asked Claude to queue work that ChatGPT can do without Claude, to save Claude's time. Take jobs in order, one PR per job. Stable rules: [`AGENT_COLLABORATION.md` on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md). Live status: `AGENT_COLLABORATION.md` on this branch. If this file conflicts with the owner or with master's guide, they win; say so in the PR.

Checked against master `3fbaf97`; J16 to J18 against master `fec7051`; J19 and J20 against master `045de51`; J24 and J25 against master `97e71ee`. Edit only the Status table; do not delete jobs.

## Status

| Job | Title | State |
| --- | --- | --- |
| J0 | CI shows why a fixture or test failed | merged (PR #87) |
| J1 | Set-theory proofs, batch 1 | merged (PR #88) |
| J2 | Refresh `docs/PROOF_FILE_FORMAT.md` | merged (PR #89) |
| J3 | Red-team the set-theory rules | merged (PR #90) |
| J4 | Parse oracle: more phrases | merged (PR #91; findings #93–#96) |
| J5 | Order and relation proofs | merged (PR #92) |
| J6 | Number-theory proofs and a missing-axiom list | merged (PR #97; finding #98) |
| J7 | Mutation-check tool | merged (PR #99) |
| J8 | Negative set phrases in the parser | merged (PR #100; finding #93) |
| J9 | Union, intersection, and disjointness phrases | merged (PR #101; finding #94) |
| J16 | First-order logic classics | merged (PR #111; review follow-ups #114 and #116) |
| J17 | Red-team the quantifier and scope rules | merged (PR #112; review follow-ups #115 and #116) |
| J18 | Equivalence classes and partitions | merged (PR #113; review follow-ups #114 and #116) |
| J19 | Fix the J16 and J18 review findings | merged (PR #114) |
| J20 | Fix the J17 review findings | merged (PR #115) |
| J21 | Reject ambiguous parity shorthand under quantifiers | merged (PR #117) |
| J22 | Centralize parser extension assembly | merged (PR #118) |
| J23 | Expand informational relation and order proofs | merged (PR #119) |
| J24 | Red-team Mutatis mutandis | merged (PR #123) |
| J25 | Where stage 1 of Mutatis mutandis stops | merged (PR #124) |

States: `todo`, `in progress (PR #n)`, `waiting for owner (PR #n)`, `merged (PR #n)`, `blocked: <why>`. At most 3 PRs open. After J0 merges, J1 to J7 may run in parallel within that limit.

## Rules for every job

1. **Branch and PR.** Branch from current master as `chatgpt/<job>-<slug>`. One job per PR, small (about 15 proofs or 400 changed lines at most). Open it as a draft; mark it ready when CI shows what the job's "Done when" says. The owner merges.
2. **CI is your test run.** You cannot run code. Push early, read the run, fix, push again. Never state a result you did not read from a CI run. Every PR reports: tested commit, CI run link, Python tests (passed / failed / xfailed), coverage, enforced fixtures and informational fixtures. Since PR #121 no test is known to fail (see "No known failing test" in the live handoff), so a failure in your PR is yours to explain or fix; list it separately, never as known.
3. **Off limits.** Do not edit `source/ProofLogic.py` or `source/ProofJustification.py`. Do not change an existing test, fixture or oracle case to make something pass. Do not start anything under "Not yet" below.
4. **A checker problem is a finding, not a failed job.** Four kinds: (a) a valid proof is rejected, (b) an invalid proof is accepted, (c) a crash, (d) a message that points at the wrong thing. File one issue per finding, titled `[finding] <short>`, with: the smallest proof text that shows it (fenced), the exact message or the wrong acceptance, the rule or file you suspect, and `Owner: Claude` when the kernel is involved. Keep the PR green: leave an (a) proof out of the fixtures (it lives in the issue); record a (b) as a pytest marked `@pytest.mark.xfail(strict=True, reason="issue #n")` that asserts the proof is rejected. Claude fixes the kernel and removes the marker. Before you file (a), compare the proof with "Verified patterns" and its pitfalls: a rejected proof is far more often a mistake in the proof than a gap in the checker. File only when you are confident the proof is valid, and say what you tried. This replaces the older "report holes in a draft PR" rule.
5. **Negative proofs fail for the intended reason.** A fixture marked invalid must be refused for the reason its title names, not for a parse error, an undeclared symbol or a scope slip. Pin the reason with a test that checks the refusal message, like `pytest_tests/test_uniqueness_red_team_reasons.py`.
6. **Fixture format.** `# N: Title`, then `## Proof that` (expected valid) or `## Invalid: <reason> — <why>` (expected invalid), then `### then <conclusion>`. The conclusion must appear as a derived line, up to renaming bound variables. A titled proof is promoted and later proofs in the same file may cite it by title. A single-proof file has no header lines and is expected to be refused when its file name contains `invalid`.
7. **Where proofs go.** Passing proofs go in the directory for their subject: set theory in `tests/setTheoryProofs/`; number theory in `tests/testNumberTheory/`; relations and order in `tests/testDiscreteMath/`; base logic (propositional and first-order) in `tests/testProofs/`. The last three are enforced suites: a failing proof there fails CI, so keep the PR a draft until green. `tests/setTheoryProofs/` is informational (CI does not fail on it), so for each file you add there also add a test that runs the file and fails with the `(number, message)` of every proof that did not behave as expected; see `test_union_and_power_set_theorems_fixture_all_pass` in `pytest_tests/test_axiom_citation_rules.py` for the shape, and put the messages in the assertion so J0's failure details show them. Expected-invalid proofs go in the enforced suite for their subject, with a pinned-reason test (rule 5).
8. **Keep it short.** No new files outside the places a job names, no changes to `todos.txt` unless the owner asks. Design rationale goes in the PR description, not in repo docs.

## J0. CI shows why a fixture or test failed

Why: `./run_tests.sh` prints only pass counts per suite, and pytest runs with `--tb=no`. From a CI log you cannot tell which proof failed or why. Every proof-writing job needs this, and you cannot run anything yourself.

Do, in two small changes:

1. `source/validate_all_proofs.py`, `main()`, the default run (no `--suite`). After the existing `Total proofs checked` line, print `=== Fixtures that did not behave as expected ===` and one line per proof that did not pass, enforced or informational: `FAIL <suite directory>/<file> #<id> (enforced|informational): <full message, newlines collapsed to one space>`. Print `none` when there are none. Change no existing output line and no exit status (only enforced failures fail the run).
2. `run_tests.sh`. When pytest fails, rerun only the failed tests with `python3 -m pytest -q --tb=short --lf pytest_tests` (no coverage) and print the last 150 lines under a `=== Failure details ===` heading. When pytest passes, the output must stay byte-for-byte what it is today.

Tests: extend `pytest_tests/test_fixture_runner_summary.py` (it already monkeypatches `runner.run`): one case with a failing enforced result and a failing informational one (both listed with their messages, exit status 1), one with all passing (`none`, exit status 0).

Done when: the CI log of your PR lists exactly one fixture, the unique-pairing proof `tests/setTheoryProofs/zfc_remaining_axioms.txt #1` (issue #75: "WLOG replay has no visible counterpart for cited line '3'"), and the failure details show the traceback of `test_zfc_remaining_axioms_fixture_all_pass`.

## J1. Set-theory proofs, batch 1

Goal: exercise the named axiom rules, `Set property`, `Set equality`, subset proofs, `Uniqueness`, universal generalization, existential elimination and cases the way a textbook does. A proof that still fails after you have fixed your own mistakes is a finding (rule 4); finding those is part of the point.

Where: new files in `tests/setTheoryProofs/`, at most 8 proofs each, plus the file test from rule 7. Do not repeat what `basic_theorems.txt`, `pairing_theorems.txt`, `union_and_power_set_theorems.txt` and `zfc_remaining_axioms.txt` already prove.

Seeds, verified on master `3fbaf97` under the informational suite's configuration: the two proofs in "Verified patterns" at the end. Start your first file with them. Copy the syntax exactly; do not improvise rule names.

Statements to take, in order (union, intersection and difference are not terms in this system, so each theorem says "there exists a set such that ..." or is given a set with that membership property as a premise):

1. No set of all sets (seed). For every set A there is a set that is not in A (Separation on `u not in u`).
2. The union of two sets exists (seed). The intersection and the difference of two sets exist (Separation).
3. Any two sets with the membership property of the union of A and B are equal (`Set equality`). The same for intersection.
4. Given U with the union property: A is a subset of U and B is a subset of U. Given I with the intersection property: I is a subset of A and of B.
5. Idempotence and commutativity: the union of A and A is A; the union of A and B equals the union of B and A.
6. If A is a subset of B then the union of A and B is B, and the intersection of A and B is A.
7. Absorption: given U with the union property of A and B, and I with `In(x, I) iff (In(x, A) and In(x, U))`, then I = A.
8. If A is a subset of B then P(A) is a subset of P(B) (given the power sets as premises, or cite the Power Set instance for each).
9. The union of the power set of A is A (Union instance for the power set; Power Set instance for A).
10. The union of the pair {A, B} (Pairing, then Union) has the membership property of the union of A and B.
11. Stretch: Kuratowski ordered pairs, built with Pairing only: if {{a}, {a, b}} = {{c}, {c, d}} then a = c and b = d.

Done when: at least 10 proofs pass in CI; every proof that does not pass has an issue. Report which.

## J2. Refresh `docs/PROOF_FILE_FORMAT.md`

The doc is stale: it says "Verified against ... 030c8a3", calls WLOG a placeholder (equality-case WLOG is implemented), and lacks the named axiom rules, the Union and Power Set instance forms, `Let Y be such a set. (Existence from L)`, the `Set property` forms, `Uniqueness`, `Set equality`, subset proofs, explicit Existential Elimination with `Let v be an object. (Declare)`, `Proof by Cases`, `Substitution`, titled proofs that later proofs cite, and the `Use <theory>.` directives.

Do: read the doc, `pytest_tests/test_proof_format_doc.py`, the fixtures under `tests/`, and the alias map in `source/ProofJustification.py` (read only). Bring the text up to date. Every new example is a complete proof marked `<!-- proof-format-test: valid-proof -->` (the only marker kind) so the doc test runs it. Add the two seeds as worked examples. Say plainly what is deferred: arbitrary-property WLOG, `Mutatis mutandis`, and the older direct Pairing-witness form.

Add `pytest_tests/test_proof_format_doc_covers_rules.py`: every user-facing rule name that `ProofJustification._ALIASES` accepts (one canonical name per rule is enough) appears in the doc, and so does each name in the placeholder table inside `_rule`. Import `_ALIASES` for the first; hard-code the second list in the test with a comment saying where it comes from. A new rule then cannot be added without the doc noticing.

Done when: the doc test and the new test pass in CI, and the "Verified against" line names the commit CI ran.

## J3. Red-team the set-theory rules

Targets, all in `source/SetTheory.py`: `SeparationSchemaRule`, `ReplacementSchemaRule`, `SetPropertyRule`, `SetEqualityRule`, `EmptySetPropertyRule`, and the subset-proof elaboration `elaborate_subset_proof`.

Do: for each rule, list its side conditions from its docstring and then from its code (the code is the truth). For each side condition write the smallest proof that violates only that condition, as an expected-invalid case in `tests/testSetTheory/red_team_<rule>.txt` whose `## Invalid: <condition> — <why>` title names the condition. Pin each refusal with `pytest_tests/test_set_theory_red_team_reasons.py` (rule 5). Add at least one valid near-miss per rule that is accepted by design, titled `## Proof that`, to mark the boundary.

Starting points that matter most, because accepting them is unsound: Separation where `Y` is free in B (`u not in Y`), where X mentions `u` or `Y`, or where `u` and `Y` share a name; Replacement without the functionality hypothesis, with `C` or `z` free in B, with a bounding set that mentions `x`, or with a uniqueness clause that is not B(x, z); `Set equality` with one inclusion missing or the two inclusions about different sets; `Set property` citing a one-directional conditional, a characterization of a different set, or a line inside a closed subproof; a subset proof that concludes membership in a different set than it set out to show.

If an invalid proof is accepted, that is finding (b): issue, strict xfail, and tell the owner in the PR. If the refusal message does not name the condition, that is finding (d).

Done when: every side condition has its own case, none is a rephrasing of another, and CI shows only the known #75 failure.

## J4. Parse oracle: more phrases

`parse_oracle/*.txt` holds independent surface-to-plain-logic cases; `pytest_tests/test_parse_oracle.py` checks the parser against them (format in that file's docstring). The existing files are `set_theory_phrases`, `set_theory_edge_cases`, `bounded_quantifiers`, `logical_contexts`, `malformed_connectives`, `number_theory`, `number_theory_edge_cases`.

Do: write 20 to 40 new cases per PR in new files by topic: negated set phrases ("is not a subset of", "does not belong to", "is not empty"), disjointness and nonemptiness, union and intersection phrasing, nested bounded quantifiers ("for every x in A there is y in B such that ..."), divisibility and parity phrasing. The test parses with the default environment (base logic, set theory, number theory), so leave out discrete-math relation phrases. Stay close to the phrasing the existing oracle files, the README and the fixtures use; do not invent exotic English. Write `expect` from the intended mathematical reading in plain logic, before and without reading the parser. Include `REJECT` cases for malformed phrases. Every case has a `why`.

If a case fails because the parser lacks the phrase, that is finding (a): put the failing cases in `parse_oracle/pending/<topic>.txt` (the test does not load subdirectories), open one issue per topic (not per case) listing them with the parser's actual output, and keep the passing cases in the loaded file so CI stays green. If you think the oracle misread the intent, say so in the PR and let the owner decide; never loosen `expect` to match the parser.

Done when: the loaded cases pass in CI and every pending case is in an issue.

## J5. Order and relation proofs

Where: `tests/testDiscreteMath/`, files starting `Use discrete math.`; follow the four files already there. Use the relation rules the fixtures already use (`Relation reflexivity`, `Relation antisymmetry`, and so on) and stay inside the vocabulary they use. If a declaration you need does not exist, that is finding (a); do not invent syntax.

Statements: the least element of a partially ordered set is unique, and so is the greatest; a least element is minimal; an equivalence relation satisfies "R(a, b) and R(a, c) imply R(b, c)"; a symmetric antisymmetric relation relates only equal elements; an asymmetric relation is antisymmetric (the hypothesis is contradictory, use `Explosion`); a total relation is reflexive; in an antisymmetric relation, R(a, b) and a != b give not R(b, a); the strict relation `S(x, y) iff R(x, y) and x != y` of a partial order R is irreflexive and transitive (state the definition of S as a premise). Add the invalid twin of each (same proof with the key step unjustified), refused for the intended reason (rule 5).

Done when: 8 or more valid proofs and their invalid twins pass in CI.

## J6. Number-theory proofs and a missing-axiom list

Where: `tests/testNumberTheory/`; follow the files already there, which state the ring axioms they use as `(Axiom)` lines. Read the header comment of `source/NumberTheory.py` first: it lists which ring facts the module has (closure, `Times` associativity, left distributivity, the quotient axioms) and which it lacks (for example `Plus` associativity and commutativity). Existing files cover transitivity, closure under right multiplication, sums, and the quotient characterization; do not repeat them. Candidates: `a|a`, `1|a`, `a|0`, `a|b` gives `a|Neg(b)`, `a|b` and `a|c` give `a|Plus(Times(b, m), Times(c, n))` for integers m and n, `a|b` and `b|c` and `c|d` give `a|d`. Several will need a fact the module lacks; that is expected.

Do not add axioms. When a proof is blocked by a missing ring fact, stop it and add an entry to one issue `[finding] number theory: axioms the next proofs need`: the proof you wanted, the fact it needs, and where that fact would go in `NumberTheory.py`. That issue is the owner's decision list.

Done when: 6 or more proofs pass in CI and the issue lists every blocked proof.

## J7. Mutation-check tool (low priority)

Claude checks that a new test discriminates by mutating the code under test and requiring a test to fail. That harness lives in a scratch folder and is lost between sessions. Write `tools/mutation_check.py` (standard library only).

Spec: `python3 tools/mutation_check.py SPEC.json --tests "<pytest command>" [--jobs N]`. `SPEC.json` is a list of `{"id": ..., "file": ..., "old": ..., "new": ...}`. For each mutant: copy the repository (without `.git`, `__pycache__`, `.pytest_cache`, `.coverage`) to `<tmp>/SyLoPy` (the package is imported as `SyLoPy`), require `old` to occur exactly once in `file` (otherwise report `PATTERN` with the count), replace it, run the test command there with `PYTHONPATH=<tmp>`, and classify `KILLED` (nonzero exit), `SURVIVED` (zero exit), `PATTERN` or `TIMEOUT`. Print one line per mutant and a summary. Exit 0 only when nothing survived and no pattern failed.

Tests: `pytest_tests/test_mutation_check_tool.py` builds a toy package in `tmp_path` (never the real repository) with one function and one test, and a spec with one killed mutant, one surviving mutant, one pattern that occurs twice and one that occurs zero times; assert the classification and the exit status.

Done when: the new test passes in CI.

## J16. First-order logic classics

Why: base logic has 8 enforced proofs (`tests/testProofs/multiProof.txt`), and the quantifier laws appear only in part in the informational `source/testProofs/propLogTests.txt` (#16, #17, #26, #35, #37 to #39). Everything else here rests on these rules, and the owner's textbook chapters use them. A valid classic that is refused is finding (a); a fallacy that is accepted is finding (b), the worst kind.

Where: `tests/testProofs/first_order_classics.txt` (enforced: a failing proof fails CI, so keep the PR a draft until green) and `pytest_tests/test_first_order_classics_reasons.py` (rule 5; the shape is `test_uniqueness_red_team_reasons.py`).

Seeds: `job_seeds/first_order_logic.txt` on this branch is the first 18 entries of your file: 13 valid proofs and 5 invalid twins. Copy it unchanged; the copied seeds do not count toward rule 1's size limit, your additions do. Every entry was run on master `fec7051` in `tests/testProofs` and behaves as its header says (53/53 in that suite with the file added). The seeds settle three things you need not guess. `Explosion` takes the two contradictory lines (`Explosion from 2.3.1, 2.3.2`), not their conjunction. An existential witness is declared with `Let w be an object. (Declare)` before its `Existential Elimination` line, and that line's conclusion must not mention it. Only `### then` is checked by the runner; `### if` is descriptive, so make the premise lines say what the header says.

What the five twins are refused with, for the pinned-reason test (assert substrings, plus line, rule and category `pl.CATEGORY_RULE_MISMATCH`):

- #14, line `6.2`: `'ExistentialElimination' does not justify`; `the witness w occurs in a hypothesis in force`
- #15, line `3.2`: `the witness b occurs in the conclusion`
- #16, line `6`: `'ModusPonens' does not justify P(a)`
- #17, line `3`: `'UniversalInstantiation' does not justify`
- #18, line `4`: `'ExistentialIntroduction' does not justify`

#17 and #18 name only the rule; the kernel does not say why. If you think the message should say more, that is finding (d), not a reason to loosen the test.

Statements to add, in order, one proof each (each is a theorem, so each must pass):

1. From `forall x, (P(x) -> Q(x))` and `exists x, P(x)`: `exists x, Q(x)`.
2. From `forall x, (P(x) -> Q(x))`: `(forall x, P(x)) -> (forall x, Q(x))`, and `(exists x, P(x)) -> (exists x, Q(x))`.
3. From `(forall x, P(x)) or (forall x, Q(x))`: `forall x, (P(x) or Q(x))`.
4. From `exists x, forall y, R(x, y)`: `forall y, exists x, R(x, y)` (informational #35 has it; leave that one alone).
5. From `forall x, forall y, (R(x, y) -> R(y, x))` and `forall x, forall y, forall z, ((R(x, y) and R(y, z)) -> R(x, z))`: `forall x, ((exists y, R(x, y)) -> R(x, x))`.
6. For a closed formula A: from `A -> (forall x, P(x))`, `forall x, (A -> P(x))`; and from `exists x, (A and P(x))`, `A and (exists x, P(x))`, and the converse.
7. Equality: from `a = b`, `f(a) = f(b)` (Substitution); from `a = b`, `b = a`; and `exists x, x = a`.
8. Syllogisms with predicates `P`, `M`, `S`: Barbara (`forall x, (M(x) -> P(x))` and `forall x, (S(x) -> M(x))` give `forall x, (S(x) -> P(x))`), Celarent (`M(x) -> not P(x)` and `S(x) -> M(x)` give `S(x) -> not P(x)`), Darii (`forall x, (M(x) -> P(x))` and `exists x, (S(x) and M(x))` give `exists x, (S(x) and P(x))`), Ferio (`forall x, (M(x) -> not P(x))` and `exists x, (S(x) and M(x))` give `exists x, (S(x) and not P(x))`).
9. Stretch: the drinker paradox, `exists x, (D(x) -> forall y, D(y))`, with an object `a` declared. Use excluded middle on `forall y, D(y)` as informational #37 does, then cases; the second case uses the argument of seed 3.

Invalid twins to add, at least 4: the textbook fallacies, each written as its natural flawed derivation and refused for the flaw its title names. Candidates: undistributed middle (from `forall x, (P(x) -> M(x))` and `forall x, (S(x) -> M(x))`, `forall x, (S(x) -> P(x))`); denying the antecedent (from `forall x, (P(x) -> Q(x))` and `not P(a)`, `not Q(a)`); `forall x, (P(x) or Q(x))` to `(forall x, P(x)) or (forall x, Q(x))`; `exists x, P(x)` to `forall x, P(x)`; `forall y, exists x, R(x, y)` to `exists x, forall y, R(x, y)`. If the flawed step cannot be written without a naming slip, leave that fallacy out and say so in the PR: `symbol 'c' is already declared as object` is a scope slip, not the fallacy, and the kernel's universal generalization makes several of these unwritable.

Done when: at least 10 new valid proofs and 4 new invalid twins pass in CI together with the seeds, the pinned-reason test passes, and every refused valid proof or accepted fallacy has an issue. Report which.

## J17. Red-team the quantifier and scope rules

Why: J3 did this for the set-theory rules. The core rules, where an accepted bad proof matters most, have had no systematic pass of this kind. Claude audited variable capture and schema side conditions on 2026-10-14 (`todos.txt`, "Soundness audit"); this job is the other families.

Targets, all in `source/ProofLogic.py` (read only): `UniversalGeneralizationRule`, `ExistentialEliminationRule`, `ExistentialIntroductionRule`, `UniversalInstantiationRule`, `ConditionalIntroductionRule`, `ProofByContradictionRule`, `DisjunctionEliminationRule`, `LeibnizSubstitutionRule`, `ReiterationRule`, and how labels and declarations are seen from inside and outside a subproof (`LabelScope`, `DeclarationScope`).

Do: as J3. For each rule list its side conditions from its docstring, then from its code (the code is the truth). For each condition write the smallest proof that violates only that condition, as an expected-invalid case in `tests/testProofs/red_team_<rule>.txt` whose `## Invalid: <condition> — <why>` title names it, and pin each refusal in `pytest_tests/test_core_red_team_reasons.py` (rule 5; the shape is `pytest_tests/test_capture_and_schema_side_conditions.py`: the refusing line, the rule, the category). Add at least one valid near-miss per rule, titled `## Proof that`, to mark the boundary. Do not repeat the variable-capture cases or J16's twins #14 to #18.

Starting points, because accepting any of them is unsound:

- Universal generalization: the arbitrary constant occurs in a premise, in an assumption of an enclosing subproof, in a `Let ... such that:` hypothesis, in a witness line (`Let Y be such a set.`) or in an `(Axiom)` line; a `(Premise)` or `(Assumption)` line about the constant inside the subproof (refused today with "occurs in a hypothesis in force"); the last line is not an instance of the generalized body, or generalizes a different variable; the first line is not `let c be arbitrary. (Arbitrary)`.
- Existential elimination: the witness occurs in a premise, in an enclosing assumption or in the cited existential; it was declared earlier for another purpose; the assumption is not the body instantiated with the witness; the subproof's last line is not the line concluded; the cited line is not existential.
- Existential introduction and universal instantiation: a different term in different places; a line that is not an instance of the cited body; instantiating an existential line; introducing from a universal one.
- Conditional introduction and proof by contradiction: the subproof does not open with the assumption the rule needs, or end with the consequent or a contradiction; a line of the closed subproof cited from outside.
- Disjunction elimination and proof by cases: a case missing, or repeated; cases that do not cover the cited disjunction; a case block citing the other block's lines; case conclusions that differ.
- Substitution: no actual replacement; replacing a term the equality does not state; an equality between non-matching terms.
- Scope: citing a label defined later or twice, a label inside a closed subproof, a label that shadows another, `Reiteration` across a closed subproof.

If an invalid proof is accepted, that is finding (b): an issue with `Owner: Claude`, a strict xfail, and a note to the owner in the PR. If a refusal's message does not name the condition, that is finding (d).

Done when: every listed condition has its own case, none a rephrasing of another, and CI shows only the one known failing test.

## J18. Equivalence classes and partitions

Why: the owner's textbook proves these, and they need sets and relations together, which is where gaps in what can be written show. A proof you cannot write is finding (a), but compare it with the seeds first.

Where: `tests/testDiscreteMath/equivalence_classes.txt` (enforced; first line `Use discrete math.`), with the invalid twins in the same file, and `pytest_tests/test_equivalence_classes_reasons.py` (rule 5).

Seeds: `job_seeds/equivalence_classes.txt` on this branch has two proofs, run on master `fec7051` in `tests/testDiscreteMath` (35/35 with the file added). Copy them unchanged as entries 1 and 2. A class is a set made by Separation, `exists C, forall u, (In(u, C) iff (In(u, X) and R(a, u)))`, and named with `Let C be such a set. (Existence from L)`. Set-builder notation is not a term here (see "Not yet"), so do not try to write `[a]`.

Statements to add, in order:

3. If `R(a, b)` then the class of a equals the class of b (both inclusions, then `Set equality`).
4. If the class of a equals the class of b then `R(a, b)` (a is in its own class by seed 1, so a is in the class of b; then `Set property` and symmetry).
5. Two classes are equal or have no element in common: if some u is in both, then `R(a, b)`, so by 3 they are equal.
6. Every element of X lies in some class, with the class named.

Invalid twins, at least 3, refused for the intended reason: `Relation Symmetry` cited for a relation declared only reflexive and transitive; the subset proof of seed 2 with the direction of the equivalence reversed (`R(b, a)` where `R(a, b)` is needed); a subset proof that concludes membership in the class without `In(u, X)`.

Done when: the seeds, at least 4 new valid proofs and 3 invalid twins pass in CI, and every proof you could not write is an issue (rule 4) with the smallest text that shows it.

## J19. Fix the J16 and J18 review findings

Why: the owner asked Claude to review PRs #111 and #113 ([#111 review](https://github.com/axiomtutor/SyLoPy/pull/111#issuecomment-6309381566), [#113 review](https://github.com/axiomtutor/SyLoPy/pull/113#issuecomment-6309382063)). The findings are about your own files, and every text you need is already run: `job_seeds/j19_j20_cases.md` holds the entries (keys below) and the exact refusal messages. Each entry was run on master `045de51` in the suite it belongs to; with J19 and J20 applied, `tests/testProofs` passes 122/122 and `tests/testDiscreteMath` 42/42. This job edits your J16 and J18 cases, which rule 3 would otherwise forbid, and only as listed; the seeds stay byte for byte (J16 #1 to #18, J18 #1 and #2).

Where: `tests/testProofs/first_order_classics.txt`, `tests/testDiscreteMath/equivalence_classes.txt`, `pytest_tests/test_first_order_classics_reasons.py`, `pytest_tests/test_equivalence_classes_reasons.py`.

Do:

1. J16 #35 is refused for a different reason than its title: it cites the bundled premises without instantiating, and a valid Modus Tollens written the same way is refused identically. Replace its proof with `fo35` (same number and title; refused at line 3).
2. J16 #36 and #37 are refused by Universal Instantiation's generic checks, not by the fallacies they name. Keep the proofs and change each `## Invalid:` line to the one under "Retitles". In the PR, say which of the five fallacies you could not write in their natural form; the job asked for that.
3. J16 #38 restates seed #15. Replace it with `fo38` (statement 5 exactly as J16 gave it; valid) and drop its row from `_EXPECTED_REFUSALS`. Append `fo41` as #41, the valid sibling of #35. Keep #39. Optional: replace #28 with `fo28` (symmetry by Substitution rather than a `Symmetry` citation).
4. J18: add the three `### then` lines listed under "`equivalence_classes.txt`: conclusions", and replace #6 with `ec6`. In `test_all_equivalence_class_proofs_match_their_declared_validity`, assert `case.stated_conclusion is not None` for cases 3 to 6, so a malformed `### then` cannot silently switch the check off again.
5. Pins, both test files: replace the second assertion (`detail in error.detail` repeats `does not justify` for most rows) with the prefix from the message table (rule, formula and cited lines), and keep the reason fragments the table lists (J16 #14 and #15, J18 #9). Pin J16 #35 at line 3.
6. Optional: remove the uncited lines (J18 #4's line 11, #5's lines 8 and 10) and renumber; a slip shows up as a bad citation in CI.

Done when: CI shows only the known failing test and the PR says, per item, what changed. Claude then runs the J7 tool on your branch: `python3 tools/mutation_check.py job_seeds/j19_mutants.json --tests "python3 -m pytest -q -x -p no:cacheprovider pytest_tests/test_first_order_classics_reasons.py pytest_tests/test_equivalence_classes_reasons.py pytest_tests/test_core_red_team_reasons.py -k 'not refuses and not scope_keeps'"`. `MT-deny-antecedent` must be KILLED; on master it survives, because the old #35 is refused under the mutant too.

## J20. Fix the J17 review findings

Why: the owner asked Claude to review PR #112 ([review](https://github.com/axiomtutor/SyLoPy/pull/112#issuecomment-6309381845)). Claude mutated `source/ProofLogic.py` one side condition at a time (30 mutants): three survive every test, and 22 of the 25 rule-level pins assert only `does not justify`. The entries and messages are in `job_seeds/j19_j20_cases.md`, run as for J19. The edits below to your J17 files are authorized; rule 3 still covers everything else.

Where: `tests/testProofs/red_team_*.txt` and `pytest_tests/test_core_red_team_reasons.py`.

Do:

1. Add `de6` (DisjunctionElimination #6), `pbc4` and `pbc5` (ProofByContradiction #4 and its valid sibling #5), `ee6` and `ee7` (ExistentialElimination #6 and #7), `scope4` and `scope5` (Scope #4 and #5). Add rows to `REFUSALS` for `de6`, `pbc4`, `ee6` and `ee7`; `scope4` and `scope5` are refused by elaboration, so pin `case.parse_error` with the message in the table.
2. Remove duplicates. Reiteration #3 and Scope #2 are the same proof: replace Scope #2 with `scope2`, which cites the closed line by a different rule. Delete ConditionalIntroduction #4 (it is #2 and #3 at once) and its `REFUSALS` row.
3. Pins: in `test_invalid_core_rule_cases_fail_at_the_intended_line_and_rule`, replace the second assertion (`detail_fragment` is `does not justify` for 22 of 25 rows) with the prefix from the message table, and keep the reason fragments the table lists. Several cases print the same prefix, so this pins the line, rule, formula and cited lines, not the reason; reasons need kernel explanations, which are Claude's to add (the pins get upgraded then). Say so in the PR.
4. Layer pins: replace `test_sibling_case_cannot_cite_a_closed_line_from_another_case` and `test_closed_subproof_reference_is_refused_at_the_visibility_boundary` with checker-level pins and delete their parse-error branches, which never run today: DE #5 at `2.2.case2`, Scope #2 and Reiteration #3 at `3`, category `CATEGORY_BAD_REFERENCE`, the cited label in the detail.
5. Add the direct test for the witness in the cited existential (snippet in the seeds file); no test pins that condition directly today.

Done when: CI shows only the known failing test and the PR says, per item, what changed. Claude then runs the J7 tool as in J19: `DE-concl-first`, `PbC-target-pos` and `EE-outer` must be KILLED (all three survive on master).

## J24. Red-team Mutatis mutandis

Why: PR #121 added a kernel feature that repeats an argument for other names by expanding it and validating the expansion like any other line. Claude wrote 33 fixture cases and mutation-tested it, but an independent pass finds what its author did not think of, and an accepted bad proof is finding (b), the worst kind.

Read first (read only): `docs/PROOF_FILE_FORMAT.md`, "Mutatis mutandis: the same argument for other names"; the header and the 30 cases of `tests/testProofs/mutatis_mutandis.txt` and the 3 of `tests/testSetTheory/mutatis_mutandis_sets.txt` (do not repeat their cases); `pytest_tests/test_mutatis_mutandis_reasons.py` (the pinning shape); and in `source/ProofLogic.py` `_expand_mutatis_mutandis`, `_mm_align`, `_mm_blocked_line`, `_mm_counterpart` and `_transform_wlog_entry`.

Do: at least 15 new cases in `tests/testProofs/red_team_mutatis_mutandis.txt` (enforced). Each invalid case is refused for the reason its `## Invalid: <condition> — <why>` title names and has a valid twin that differs from it only in that condition. Pin each refusal (line, category, reason) in `pytest_tests/test_mutatis_mutandis_red_team_reasons.py` (rule 5). Starting points, because accepting any of them is unsound:

1. The new name is one the argument itself makes arbitrary or fresh: the arbitrary constant of a `Universal Generalization` subproof, the witness of an `Existential Elimination`, a name declared inside the argument.
2. The new name occurs in a hypothesis in force where the line stands (a premise, an enclosing assumption) that the argument's generalization or elimination needs it not to occur in.
3. The argument cites a line that mentions a replaced name only inside a bundle premise, a quantified formula or a standalone subproof; a bundle that states the needed fact for one name but the old fact for the other.
4. A hypothesis hidden in the argument: `Existence from`, a `Let ... such that` line, a declaration that states a fact, an axiom citation, at any depth and in each case block of a `Proof by Cases`.
5. Replacements that are not names or not one-to-one in the way the doc says: two names to one (accepted), one name to two, a constant to a variable or a function term, a free variable renamed, a bound variable that does not correspond, another predicate or connective, an `and` or `or` with another number of parts, `A -> B` against `B -> A`.
6. Citations: `A to B` with A after B, A not visible, A the same line as B; B a premise, a declaration or a WLOG step; three citations; a line inside a closed subproof; a line citing itself.
7. Chains and interplay: a repeat of a repeat whose names drift (a by b, then b by c); three names rotated; a repeat inside a subproof of a line outside it, and the reverse; a repeat inside a WLOG region; two repeats of the same line with different names (both must be accepted).
8. Equality and function terms: `Substitution` repeated for other names; a function term whose argument is replaced; an equation whose sides are exchanged.

If an invalid proof is accepted, that is finding (b): an issue with `Owner: Claude`, a strict xfail in your pins, and a note in the PR. If a valid proof is refused, compare it with the doc first: the repeated argument is checked like any line, a name is replaced only if it occurs in both statements, and the lines between A and B are not replayed. A message that does not say why is finding (d).

Done when: every point above has a case or a sentence in the PR saying why it cannot be written, none repeats an existing case, CI shows no failing test, and the PR lists every finding.

## J25. Where stage 1 of Mutatis mutandis stops

Why: the owner has not decided whether to extend the rule to a name replaced by a term (stage 2) or to relation and function symbols (stage 3). That decision needs examples from real proofs.

Do (read only, except the new file): go through the proofs under `tests/` and `source/testProofs/` and find places where a proof repeats an argument with other names, objects or symbols: a second inclusion that is the first with the sets exchanged, a second case of a case split, the other half of a biconditional, a lemma used twice. For each place that stage 1 can express, write the shortened proof with `Mutatis mutandis` in the new informational file `tests/setTheoryProofs/mutatis_mutandis_examples.txt`, with the file test of rule 7 in the new `pytest_tests/test_mutatis_mutandis_examples.py`. For each place it cannot, say in the PR description which of three things is missing: (i) the replaced name occurs only inside the argument, in neither statement; (ii) a name must be replaced by a term; (iii) a relation or function symbol must be replaced (name both symbols and the rules that correspond). Leave the original proofs as they are.

Done when: at least 6 proofs shortened with the rule pass in CI (if the survey finds fewer places that stage 1 can express, the PR says so and lists them), the PR description has a table of the places where it was not enough (kind, file and proof number, what is needed), and CI shows no failing test. The table is for the owner. Do not start stage 2 or 3.

## Not yet (needs owner approval; do not start)

`Mutatis mutandis` beyond names replaced by names (a name replaced by a term; relation or function symbols replaced); WLOG for arbitrary properties; the symbolic defining property; the Infinity follow-up in `todos.txt` §5; retiring the generic `(Axiom)` citation; declaring function symbols in proof text and set operations as terms (no design yet); new theory modules such as abstract algebra or topology. If you think of a job that is not here, put it in the live handoff as a proposal and wait.

## What Claude does meanwhile

A soundness audit of the kernel rules not covered on 2026-10-14, then the findings you file that involve the kernel, in the order filed. (Issue #75's replay defect and the case-block gap are fixed: PRs #86 and #110.) Claude reviews a job PR when you or the owner ask in the PR thread; otherwise the owner merges after CI. You do not need Claude for any job above. After the J16 to J18 reviews Claude takes the kernel side: refusal messages that say why for the rules that do not explain themselves (Universal Instantiation, Existential Introduction, Modus Ponens and Tollens, Conditional Introduction, Proof by Contradiction, Disjunction Elimination, Substitution, Reiteration, the relation rules), and a direct kernel test for Universal Generalization's nullary flag.

## Verified patterns

Both proofs below were run on master `3fbaf97` in the informational set-theory suite and pass. A nested line's label extends its enclosing line's label (`12`, `12.1`, `12.1.4`, `12.1.4.5.1`); the first line of a universal-generalization subproof is `let c be arbitrary. (Arbitrary)`.

```
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

Pitfalls found while verifying them:

- `Let y be such a set. (Existence from L)` is rejected anywhere inside a universal-generalization subproof when the witness's property mentions the generalized constant `c`: "the generalized constant c occurs in a hypothesis in force". Witness lines stay in force for the whole proof, which is conservative by design. Use the explicit form above instead: `Let v be an object. (Declare)`, then Existential Elimination with a subproof whose first line assumes the body. Use the witness sugar only at the top level of a proof.
- `Biconditional Elimination` takes one cited line and gives one conditional per use; use it twice and then `Modus Ponens`.
- `Proof by Contradiction` from an assumption `A` concludes `not A`; from `not A` it concludes `A`. The last line of its subproof is a contradiction `P and not P`.
- `Substitution` takes the equality and the formula in either order, and only closed terms: declared objects, witnesses and an arbitrary `c`, never a bound variable.
- Cite Union and Power Set for a particular set of the proof exactly as in `tests/setTheoryProofs/union_and_power_set_theorems.txt` (binder names all different, and for Union the conjuncts in the order `In(v, S) and In(u, v)`).
- A proof whose lines all check but which never derives its stated `### then` conclusion fails with "every line validated, but the proof never derived its stated conclusion".
