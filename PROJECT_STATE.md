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
| Current status, invariants, and owner decisions | [todos.txt](todos.txt) |
| Stable collaboration rules | [AGENT_COLLABORATION.md](AGENT_COLLABORATION.md) |
| Active delegated jobs and concise dispositions | [JOBS_FOR_CHATGPT.md](JOBS_FOR_CHATGPT.md) |
| Parser, elaboration, kernel boundaries, and lowering contract | [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md) |
| Historical task specifications | [docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md](docs/archive/JOBS_FOR_CHATGPT_ARCHIVE.md) |
| Unimplemented refinement-type proposal | [TYPE_SYSTEM_DESIGN.md](TYPE_SYSTEM_DESIGN.md) |

`ELABORATION_ARCHITECTURE.md` remains as a compatibility pointer to `ARCHITECTURE_STATUS.md`. `todos.txt` is authoritative when status documents disagree. Archived specifications are not implementation authorization.

## Source map

- `source/FormulaLogic.py` — formula and term ASTs.
- `source/ProofParser.py` — public parser facade, surface parsing, and elaboration dispatch.
- `source/ProofParserPolicy.py`, `source/LineBreakSyntax.py` — installed parser-policy extensions.
- `source/ProofElaboration.py`, `source/ProofContext.py` — surface AST, source spans, elaborated entries, and lexical context.
- `source/ProofLogic.py` — independent kernel validation, scopes, inference rules, and theorem promotion.
- `source/ProofJustification.py` — justification and rule-alias parsing.
- `source/SetTheory.py`, `source/NatThry.py`, `source/NumberTheory.py`, `source/OrderTheory.py`, `source/DiscreteMath.py`, and `source/DiscreteMathCore.py` — theory extensions.
- `source/validate_all_proofs.py` — proof-fixture runner and theorem promotion.
- `pytest_tests/` — Python unit and integration tests; `tests/` — proof fixtures; `parse_oracle/` — independent parser expectations.
- Informational proof examples: `source/testProofs/` and `tests/setTheoryProofs/`.

## Verification

```bash
./run_tests.sh                  # default Python suite + all proof fixtures
./run_tests.sh --suite extended # adversarial and audit tests
./run_tests.sh --suite all      # every Python suite + proof fixtures
./run_tests.sh --list-suites
```

Do not maintain test totals or coverage here; report them from CI or a fresh run for the exact commit.
