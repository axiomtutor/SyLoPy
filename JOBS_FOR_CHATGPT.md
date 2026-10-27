# Delegated Jobs for ChatGPT

This is the concise delegated-work tracker. Stable collaboration rules live in [`AGENT_COLLABORATION.md`](AGENT_COLLABORATION.md); current feature status, invariants, design decisions, and owner-gated work live in [`todos.txt`](todos.txt). Use PRs and issues for implementation details and discussion.

Completed job specifications and their original task instructions are preserved in [`docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md`](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md). That file is historical context, not an active work queue.

## Current queue

Start a job only after the pull request that adds it has been merged: both read the rule as implemented there. Do not resume a completed or archived task unless the owner explicitly re-queues it or provides new direction.

| Job | Title | State |
| --- | --- | --- |
| J26 | Red-team Mutatis mutandis stages 2 and 3 | todo |
| J27 | Where Mutatis mutandis stops, second look | todo |

### J26. Red-team Mutatis mutandis stages 2 and 3

Why: stages 2 and 3 let a name be replaced by a term with no variable in it, and a predicate or function symbol by another with the same number of arguments. The kernel does not trust the line: it expands it into the repeated argument and validates that like any other line, so a mistake in the matching should only ever cause a wrong refusal. An independent pass finds what the author did not think of, and an accepted bad proof is finding (b), the worst kind.

Read first (read only): `docs/PROOF_FILE_FORMAT.md`, "Mutatis mutandis: the same argument for other names, terms and symbols"; the cases of `tests/testProofs/mutatis_mutandis.txt` (53), `tests/testProofs/red_team_mutatis_mutandis.txt` (23), `tests/testSetTheory/mutatis_mutandis_sets.txt` (5), `tests/testDiscreteMath/mutatis_mutandis_relations.txt` (5) and the two `tests/testNumberTheory/integer_closure_mutatis_mutandis*.txt` files (do not repeat any of them); `pytest_tests/test_mutatis_mutandis_reasons.py` and `pytest_tests/test_mutatis_mutandis_red_team_reasons.py` (the pinning shape); and in `source/ProofLogic.py` `_Replacement`, `_mm_align`, `_expand_mutatis_mutandis`, `_mm_blocked_line`, `_mm_counterpart`, `_mm_says`, `_transform_wlog_entry` and `_substitute_constants_in_formula`.

Do: at least 15 new cases in `tests/testProofs/red_team_mutatis_mutandis_terms_symbols.txt` (enforced), plus at most 5 each in `tests/testDiscreteMath/red_team_mutatis_mutandis_relations.txt` and `tests/testSetTheory/red_team_mutatis_mutandis_sets.txt` for the rules that read a relation's declaration or are about `In`. Each invalid case is refused for the reason its `## Invalid: <condition> — <why>` title names and has a valid twin that differs from it only in that condition. Pin each refusal (line, category, reason) in `pytest_tests/test_mutatis_mutandis_red_team_terms_symbols_reasons.py` (rule 5).

The replacement is a uniform, simultaneous substitution. It need not be idempotent or injective: a name may be replaced by a term that contains it, and two names or symbols may be replaced by one. A case is valid exactly when every step of the expanded argument, and every outside citation changed for the new names and symbols, is valid. So the job has two halves: proofs the rule must refuse, and valid controls it must accept. Give every refused case a valid twin, and write the controls as cases of their own.

Proofs the rule must refuse (accepting one is finding (b)):

1. Capture: the new term has a variable in it (one free in the line, or one that a quantifier binds where the term lands); it mentions the arbitrary constant of a `Universal Generalization` subproof, the witness of an `Existential Elimination`, or a name declared inside the argument.
2. Symbols that do not fit: a predicate replaced by a function symbol or the reverse; a symbol replaced by one with another number of arguments; `=`, a connective or a quantifier "replaced"; a symbol replaced in one place and kept in another, including inside a cited line; a compound term replaced as a whole.
3. Rules that read a declaration or are about one symbol: `Relation Reflexivity`, `Symmetry`, `Transitivity` and `Antisymmetry` with the new relation declared on another carrier, with other properties, or with the property only as a premise formula; two relations exchanged when only one has the property; `Set property`, `Set equality` and the axiom citations (Pairing, Union, Power Set, Separation) with `In` replaced, or with a set name replaced by a term.
4. Citations with no counterpart: a cited line that mentions a replaced name or symbol only inside a bundle premise, a quantified formula or a closed subproof, so that no visible line says the same of the new one; a bundle that states the needed fact for one symbol and the old fact for the other; an argument that needs counterparts for a replaced name and a replaced symbol at once and has only one; `A to B` where A has no counterpart for the new symbols.

Valid controls (refusing one is finding (a), after you have compared it with the doc; state the facts each one needs):

5. Overlapping terms: a name replaced by a term that contains it (`a` by `f(a)`), and that repeated (`f(f(a))`); two names replaced by one term; `a` by `f(b)` together with `b` by `f(a)`; an identity replacement beside a real one; a term replacing a name inside an equation, a negation, a biconditional, or under a quantifier.
6. Symbols: two symbols exchanged; two replaced by one; one replaced in every place, including inside the cited lines; a name and a symbol replaced in the same line.
7. Chains and interplay: a repeat of a repeat whose symbols drift (`P` by `Q`, then `Q` by `R`); a repeat for a term followed by a repeat for a symbol of its result; a repeat inside a WLOG region and inside a case block of a `Proof by Cases`; a theorem proved with a repeat and cited later by its title.

If an invalid proof is accepted, that is finding (b): an issue with `Owner: Claude`, a strict xfail in your pins, and a note in the PR. If a valid proof is refused, compare it with the doc first: the repeated argument is checked like any line, a name or symbol is replaced only if it occurs in the statement of line B, a compound term is never replaced as a whole, and the lines between A and B are not replayed. A message that does not say why is finding (d). Do not edit the cases of J24 or the earlier fixtures.

Done when: every numbered point has a case or a sentence in the PR saying why it cannot be written, every refused case has a valid twin, none repeats an existing case, CI shows no failing test, and the PR lists every finding.

### J27. Where Mutatis mutandis stops, second look

Why: the owner has not decided whether the rule should also repeat a closed block of several lines (the first case of a proof by cases, one direction of a biconditional proved in its own subproof), or accept a counterpart line that differs only by the symmetry of `=` or `<->`. That decision needs examples from real proofs, and J25 was written before stages 2 and 3.

Do (read only, except the two new files): go through the proofs under `tests/` and `source/testProofs/` again and find places where a proof repeats an argument with other names, terms or symbols. For each place that the rule now expresses, write the shortened proof with `Mutatis mutandis` in the new informational file `tests/setTheoryProofs/mutatis_mutandis_terms_symbols_examples.txt`, with the file test of rule 7 in the new `pytest_tests/test_mutatis_mutandis_terms_symbols_examples.py`; skip a place that `tests/setTheoryProofs/mutatis_mutandis_examples.txt` already shortens. For each place it cannot express, say in the PR description which of three things is missing: (i) the repeated part is a closed block of several lines (say which kind, how many lines, whether the other block has exactly the same shape, and what is replaced); (ii) the counterpart line differs only by the symmetry of `=` or `<->` (give the two lines); (iii) the replaced name or symbol occurs only inside the argument, in neither statement. Leave the original proofs as they are.

Done when: at least 6 proofs shortened with the rule pass in CI (if the survey finds fewer places, the PR says so and lists them), the PR description has a table of the places where it was not enough (kind, file and proof number, number of lines, what is needed), and CI shows no failing test. The table is for the owner. Do not start anything the table suggests.

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

## Rules for new jobs

1. Add an explicit job before starting delegated work. Each job must state its goal, allowed scope/files, tests or fixtures to add, and an observable “Done when” condition.
2. Use one small branch and one PR per job; normally keep a PR to about 400 changed lines or fewer. Keep no more than three delegated PRs open at once. The owner merges.
3. Treat CI as the test run. Keep the PR a draft until its stated completion criteria pass. Report the exact tested commit, CI run, test totals, coverage, enforced fixtures, informational fixtures, and remaining failures; never infer results from an uninspected run.
4. `source/ProofLogic.py` and `source/ProofJustification.py` are kernel-owned; do not edit them without coordination. Do not alter existing tests, fixtures, or parser-oracle expectations merely to make a change pass. Do not start items marked as requiring owner approval in `todos.txt`.
5. A checker defect is a finding, not a reason to weaken a test. File a focused issue with the smallest proof, exact accepted/rejected behavior or message, suspected rule/file, and `Owner: Claude` when the kernel is involved. Include strict expected-failure regression coverage for an invalid proof that is incorrectly accepted, following the collaboration guide.
6. A job is complete only after its PR is merged and the status table above is updated. Preserve its full specification and task-specific notes in the archive rather than keeping completed instructions in this live tracker.

Historical note: this tracker replaces the former long-form queue. Archived job text is retained for provenance, but current repository guidance and explicit owner decisions take precedence.
