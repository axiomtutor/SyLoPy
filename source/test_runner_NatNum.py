


#!/usr/bin/env python3
"""Runs testProofsNat/*.txt the same way test_runner.py runs testProofs/*.txt,
with one difference: these proofs rely on Nat's axioms and/or Induction, so
each `Proof` here is built with `NAT_TYPE`'s axioms and schema rules combined
in, via `ProofLogic.combine_types` -- exactly the configuration
`NatTheory.py`'s own `__main__` self-check uses.

test_runner.py itself is intentionally left unmodified: every fixture in
testProofs/ (including the new equality ones -- Reflexivity, Symmetry,
Transitivity, Substitution are all in `default_rules()` now, so they need no
special configuration at all) runs with a bare `Proof(entries)`, same as
before. Only fixtures that specifically need a *Type* combined in (Nat's own
axioms, or a citation of "Induction") get their own runner here, kept in a
separate directory rather than mixed into testProofs/, so it's obvious at a
glance which fixtures need which configuration -- and so that a future
theory's fixtures (Int, Set, ...) each get their own directory and runner the
same way, without this one growing an increasing number of special cases.
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




