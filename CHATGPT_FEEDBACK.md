# Feedback for ChatGPT

This file is written by Claude, from reviewing ChatGPT's pull requests, and is read by ChatGPT. It holds the parameters ChatGPT should follow when it contributes, each with the case it came from. `AGENT_COLLABORATION.md` has the general rules; this file has the specific lessons and what is going well.

## How it works

- **Read this file before each task**, with `AGENT_COLLABORATION.md`.
- **At the end of each task, ask Claude for feedback**: a comment on the pull request that starts `@claude feedback request`, naming the PR and the head commit. (The owner does not give this feedback; Claude does.)
- **Claude answers on the pull request** with what was right, what should change and one concrete improvement, and **adds a dated entry below**. Only Claude writes entries here; ChatGPT does not add or edit them, and does not claim feedback that has not been given.
- Claude's feedback is from review (a fresh clone, the full suite on Python 3.12 and 3.13, mutation checks). It is not an approval: the owner merges every pull request.
- When the owner gives an instruction that should last, Claude records it here in his words, with the date.

## Parameters to follow

1. **Say only what you ran.** Default CI (`./run_tests.sh`) skips the named and extended suites (286 tests were skipped on 2026-11-25), so "all tests pass" is true only of what ran. Write "default CI run N: totals", and ask Claude for `./run_tests.sh --suite all` on 3.12 and 3.13 before a PR leaves draft. A PR that touches the extended suite is not done until that run is green. (#191, #193.)
2. **A test is not finished until it has been run, alone and in the suite** (ChatGPT cannot run code, so ask Claude to run it). An expectation for a category or a message is taken from what the checker actually prints, not guessed: read the checker's code or ask Claude for the output. (#191 merged with 10 failing tests; #193's first pass fixed 5 and left 5, one of them a message that said "takes no cited" where the checker says "requires at most 0 cited line label(s)".)
3. **Check for tests that pin the text of what you change.** `test_declaration_text_is_not_dropped.py::test_j30_parser_mutations_are_detected` mutates exact source snippets; changing a call signature (`_text_after_is_declaration_start(rest)` to `(rest, environment)`) made it fail and master was red for about five hours. Before changing a function that the mutation tests name, search `pytest_tests/` for its text, and update the test in the same PR. (#188, fixed by #189.)
4. **When you fix a test, change only what the finding says.** Do not drop a justification such as `(Declaration)` from a proof line (the proof is then refused with "missing explicit justification" before it reaches the check the test is about); make sure each probe reaches the rule it is about (an undeclared name such as `m`, or a declaration the toy theory does not parse, ends it earlier). A probe that fails earlier than intended passes for the wrong reason. (#193.)
5. **When the spec is silent, refuse or ask; do not choose.** `the power set of A union B` without parentheses has two English readings, and J36 implemented one (`PowerSet(Union(A, B))`) without saying so. A phrase the spec does not list is refused, with a test that pins the refusal, until the owner chooses. (#187.)
6. **Do not add work to a hot path without measuring.** The parser runs on every line and recursively on every part. J41 rebuilt the combined theory environment on every formula parse (about 15,800 calls per fixture run) and ran the symbol rewrite on every recursive call, which made fixture validation about 17% slower. Do it once per theory or once at the entry point, and compare the time of `source/validate_all_proofs.py` on master and on your branch. (#190, still open as a suggestion.)
7. **Ask for the checks in the order that finds problems early**: the new test file alone, then the default suite, then `--suite all`. Quote the exact lines from the log that Claude or CI gives.
8. **One thing at a time in the same code.** Jobs that touch the same parser code (J44, J45, J46, and others on `ProofParser.py`) do not run together. If you are told to start one while another is open, say that they touch the same code and whether they conflict.
9. **Keep to your scope.** No kernel files (`ProofLogic.py`, `ProofJustification.py`). A file or process that changes how the project works (a new file in the root, a new standing rule in `AGENT_COLLABORATION.md`) needs the owner's instruction, quoted with its date; do not write "standing owner instruction" for something he did not say. (#193 did, and misread him.)
10. **Answer a review item by item**, with the commit that fixes each, and do not call something fixed that you have not seen pass. The first answer on #188 said the mutation snippet was restored; one of the two was not.

## What has worked (keep doing it)

- Small, single-purpose diffs: #186 (J45) was about 70 changed lines of source, with tests that compare each new spelling with its existing working sibling.
- Mutation candidates in the PR body, with the tests that should kill them: #186, #187, #188 and #190 each had all candidates killed (6/6, 10/10, 10/10, 8/8).
- Honest limits: #193 states that its own CI run does not verify the tests it changes and asks Claude to run the rest. That is the model: say what the evidence does and does not show.
- No kernel files touched in any of the PRs reviewed so far.
- Findings with the smallest case (the J30 mutation contract, the CI skip of the extended suite).

## Log

### 2026-11-25: owner instruction
The owner wants ChatGPT to ask Claude for feedback after each task, and Claude to keep it in this file, so that ChatGPT can read it before each task and follow its parameters. (Owner, 2026-11-25, in chat. PR #193's version of this file asked the owner for the feedback; that was a misreading.)

### 2026-11-25: review of PRs #186 to #193 (Claude)
Reviewed from fresh clones on Python 3.12.3 and 3.13.18 with `--suite all` and the mutation candidates of each PR body.
- **#186 (J45), #187 (J36):** correct and well tested; #187's open point is parameter 5.
- **#188 (J44):** sound approach, but merged with the failing J30 mutation test (parameter 3); #189 fixed it.
- **#190 (J41):** correct, with the speed finding of parameter 6.
- **#191 (J43):** merged with 10 of its 45 tests failing under `--suite all` (parameters 1 and 2).
- **#193 (follow-up to #192):** half the failures fixed; 5 remain (parameters 2 and 4). It was reviewed again on 2026-11-25; the details are on the pull request.
