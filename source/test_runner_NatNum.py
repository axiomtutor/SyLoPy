


#!/usr/bin/env python3
"""Optional runner for ``tests/testProofsNat/*.txt``.

The canonical command is ``./run_tests.sh --suite testProofsNat`` (via
``validate_all_proofs.py``). This script is a standalone Nat-only check:
each proof is built with ``NatThry.NAT_TYPE`` axioms, induction, and
declarations combined in through ``ProofLogic.combine_types``.
"""
import glob
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.NatThry as nt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests'))
TESTDIR = os.path.join(ROOT, 'testProofsNat')

AXIOMS, SCHEMA_RULES = pl.combine_types(nt.NAT_TYPE)
DECLARATIONS = pl.combine_type_declarations(nt.NAT_TYPE)
RULES = pl.default_rules() + SCHEMA_RULES

files = sorted(glob.glob(os.path.join(TESTDIR, '*.txt')))

results = []
for f in files:
    name = os.path.basename(f)
    expected_valid = not ('invalid' in name)
    try:
        entries, raw = pp.parse_proof_text(open(f).read())
        proof = pl.Proof(
            entries,
            axioms=AXIOMS,
            rules=RULES,
            declarations=DECLARATIONS,
        )
        ok, msg = proof.check()
    except Exception as e:
        ok = False
        msg = f'parse/check error: {e}'
    results.append((name, expected_valid, ok, msg))

pass_count = 0
failures = []
for name, exp, ok, msg in results:
    status = 'PASS' if exp == ok else 'FAIL'
    print(f"{status}: {name}  expected={exp}  got={ok}  msg={msg}")
    if status == 'PASS':
        pass_count += 1
    else:
        failures.append((name, exp, ok, msg))

print('\nSummary:')
print(f"Total: {len(results)}, Passed: {pass_count}, Failed: {len(failures)}")
if failures:
    print('Failures:')
    for name, exp, ok, msg in failures:
        print(f' - {name}: expected {exp}, got {ok} -> {msg}')

raise SystemExit(0 if not failures else 2)




