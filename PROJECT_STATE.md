# SyLoPy project map

SyLoPy checks Fitch-style natural-deduction proofs. Its pipeline is:

```text
proof text -> surface AST -> theory elaboration -> core entries -> ProofLogic validation
```

## Document roles

| Need | Source of truth |
| --- | --- |
| User-facing behavior, Python API, and test commands | [README.md](README.md) |
| Proof syntax, rule citations, and worked examples | [docs/PROOF_FILE_FORMAT.md](docs/PROOF_FILE_FORMAT.md) |
| Where things stand, the plan and its open owner questions, invariants, and owner decisions | [todos.txt](todos.txt) |
| Stable collaboration rules | [AGENT_COLLABORATION.md](AGENT_COLLABORATION.md) |
| Active delegated jobs and concise dispositions | [JOBS_FOR_CHATGPT.md](JOBS_FOR_CHATGPT.md) |
| Parser, elaboration, kernel boundaries, and lowering contract | [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md) |
| Historical task specifications | [docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md) |
| Unimplemented refinement-type proposal | [TYPE_SYSTEM_DESIGN.md](TYPE_SYSTEM_DESIGN.md) |
| The set theory corpus: its layout, conventions and what has been checked | [SetTheoryCorpus/README_SetTheory.md](SetTheoryCorpus/README_SetTheory.md) |

`ELABORATION_ARCHITECTURE.md` remains as a compatibility pointer to `ARCHITECTURE_STATUS.md`. `todos.txt` is authoritative when status documents disagree. Archived specifications are not implementation authorization.

## Source map

- `source/TermLogic.py`, `source/FormulaLogic.py` — term and formula ASTs.
- `source/ProofParser.py` — public parser facade, surface parsing, and elaboration dispatch.
- `source/ProofParserPolicy.py`, `source/LineBreakSyntax.py` — installed parser-policy extensions.
- `source/FormulaTextScan.py` — shared lexical scans (bracket depths, top-level conditions) for embedded formula phrases.
- `source/ProofElaboration.py`, `source/ProofContext.py` — surface AST, source spans, elaborated entries, and lexical context.
- `source/ProofLogic.py` — independent kernel validation, scopes, inference rules, and theorem promotion.
- `source/ProofJustification.py` — justification and rule-alias parsing.
- `source/Definitions.py` — the definition facility: a `Definition` names a symbol by a sentence and carries the evidence that the thing exists; a theory registers its definitions and a proof cites one by its title (set theory's are `SET_DEFINITIONS` in `source/SetTheory.py`).
- `source/SetTheory.py`, `source/NatThry.py`, `source/NumberTheory.py`, `source/OrderTheory.py`, `source/DiscreteMath.py`, and `source/DiscreteMathCore.py` — theory extensions.
- `source/validate_all_proofs.py` — proof-fixture runner: files of several proofs, theorem promotion within a file, `Use NAME.` of another file, and the saved-results options.
- `source/SavedChecks.py` — saved results: a content-addressed store of what a run checked, so that a later run need not check it again.
- `source/test_runner_NatNum.py` — compatibility entry point for the natural-number fixture suite.
- `pytest_tests/` — Python unit and integration tests (`support.py` and `file_fixtures.py` hold shared helpers); `tests/` — proof fixtures; `parse_oracle/` — independent parser expectations.
- Informational proof examples: `source/testProofs/` and `tests/setTheoryProofs/`.
- `SetTheoryCorpus/` — the owner's set theory corpus; its README says what has been checked. No code or test reads it yet.
- `tools/mutation_check.py` — changes the code one line at a time and runs given tests, to show whether they notice.
- `completion/run_tests.bash` — shell completion for `run_tests.sh`.
- `.github/workflows/test.yml` — CI: `./run_tests.sh` on every pull request to master and on pushes to branches whose names have no `/` (master is one), except pushes that change only Markdown files or `todos.txt`; a `claude/...` or `chatgpt/...` branch is tested through its pull request.
- `job_seeds/` — verified seed proofs and cases supplied for the completed jobs J16 to J20 (see the archive); kept for provenance, read by nothing.

## Verification

```bash
./run_tests.sh                  # default Python suite + all proof fixtures
./run_tests.sh --suite extended # adversarial and audit tests
./run_tests.sh --suite all      # every Python suite + proof fixtures
./run_tests.sh --list-suites
```

Do not maintain test totals or coverage here; report them from CI or a fresh run for the exact commit.
