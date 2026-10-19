# Jobs for ChatGPT

The owner asked Claude to queue work that ChatGPT can do without Claude, to save Claude's time. Take jobs in order, one PR per job. Stable rules: [`AGENT_COLLABORATION.md` on master](https://github.com/axiomtutor/SyLoPy/blob/master/AGENT_COLLABORATION.md). Live status: `AGENT_COLLABORATION.md` on this branch. If this file conflicts with the owner or with master's guide, they win; say so in the PR.

Checked against master `3fbaf97`. Edit only the Status table; do not delete jobs.

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

States: `todo`, `in progress (PR #n)`, `waiting for owner (PR #n)`, `merged (PR #n)`, `blocked: <why>`. At most 3 PRs open. After J0 merges, J1 to J7 may run in parallel within that limit.

## Rules for every job

1. **Branch and PR.** Branch from current master as `chatgpt/<job>-<slug>`. One job per PR, small (about 15 proofs or 400 changed lines at most). Open it as a draft; mark it ready when CI shows what the job's "Done when" says. The owner merges.
2. **CI is your test run.** You cannot run code. Push early, read the run, fix, push again. Never state a result you did not read from a CI run. Every PR reports: tested commit, CI run link, Python tests (passed / failed / xfailed), coverage, enforced fixtures, informational fixtures, and the known failure of issue #75 listed separately.
3. **Off limits.** Do not edit `source/ProofLogic.py` or `source/ProofJustification.py`. Do not change an existing test, fixture or oracle case to make something pass. Do not start anything under "Not yet" below.
4. **A checker problem is a finding, not a failed job.** Four kinds: (a) a valid proof is rejected, (b) an invalid proof is accepted, (c) a crash, (d) a message that points at the wrong thing. File one issue per finding, titled `[finding] <short>`, with: the smallest proof text that shows it (fenced), the exact message or the wrong acceptance, the rule or file you suspect, and `Owner: Claude` when the kernel is involved. Keep the PR green: leave an (a) proof out of the fixtures (it lives in the issue); record a (b) as a pytest marked `@pytest.mark.xfail(strict=True, reason="issue #n")` that asserts the proof is rejected. Claude fixes the kernel and removes the marker. Before you file (a), compare the proof with "Verified patterns" and its pitfalls: a rejected proof is far more often a mistake in the proof than a gap in the checker. File only when you are confident the proof is valid, and say what you tried. This replaces the older "report holes in a draft PR" rule.
5. **Negative proofs fail for the intended reason.** A fixture marked invalid must be refused for the reason its title names, not for a parse error, an undeclared symbol or a scope slip. Pin the reason with a test that checks the refusal message, like `pytest_tests/test_uniqueness_red_team_reasons.py`.
6. **Fixture format.** `# N: Title`, then `## Proof that` (expected valid) or `## Invalid: <reason> — <why>` (expected invalid), then `### then <conclusion>`. The conclusion must appear as a derived line, up to renaming bound variables. A titled proof is promoted and later proofs in the same file may cite it by title. A single-proof file has no header lines and is expected to be refused when its file name contains `invalid`.
7. **Where proofs go.** Passing proofs go in the directory for their subject: set theory in `tests/setTheoryProofs/`; number theory in `tests/testNumberTheory/`; relations and order in `tests/testDiscreteMath/`. The last two are enforced suites: a failing proof there fails CI, so keep the PR a draft until green. `tests/setTheoryProofs/` is informational (CI does not fail on it), so for each file you add there also add a test that runs the file and fails with the `(number, message)` of every proof that did not behave as expected; see `test_union_and_power_set_theorems_fixture_all_pass` in `pytest_tests/test_axiom_citation_rules.py` for the shape, and put the messages in the assertion so J0's failure details show them. Expected-invalid proofs go in the enforced suite for their subject, with a pinned-reason test (rule 5).
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

## Not yet (needs owner approval; do not start)

`Mutatis mutandis`; WLOG for arbitrary properties; the symbolic defining property; the Infinity follow-up in `todos.txt` §5; retiring the generic `(Axiom)` citation; declaring function symbols in proof text and set operations as terms (no design yet); new theory modules such as abstract algebra or topology. If you think of a job that is not here, put it in the live handoff as a proposal and wait.

## What Claude does meanwhile

Issue #75 (WLOG replay, kernel), then the findings you file that involve the kernel, in the order filed. Claude reviews a job PR when you or the owner ask in the PR thread; otherwise the owner merges after CI. You do not need Claude for any job above.

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
