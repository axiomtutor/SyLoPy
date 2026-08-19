


#!/usr/bin/env python3
"""Validate every proof `.txt` file in the project and report a clear,
per-proof PASS/FAIL -- the thing `./run_tests.sh` was missing.

Why this exists
----------------------------------------------------------------------
`run_tests.sh` running the pytest suite checks the *checker's own code*
(does `parse_formula` do the right thing, does `AlgebraRule` accept and
reject the right things, ...). It was never checking *proof fixture
files themselves* -- a handful of them are individually loaded by name
in a handful of tests (e.g. `test_theorem_promotion_and_set_theory.py`
loads one specific file from `tests/testSetTheory/`), and two fixture
*directories* are fully scanned (`tests/testProofsNat/`,
`tests/testNumberTheory/`, both via `Path.glob("*.txt")` in
`test_nat_theory.py`/`test_number_theory.py`), but most of the proof
files in this project -- including `tests/setTheoryProofs/
basicSTProofs.txt` -- were reachable by nothing at all. Appending a
bare `# 3` with no body to that file and running `./run_tests.sh`
correctly reported nothing wrong, because nothing was looking at it.

(Separately, and independently of this gap: that specific case --
a proof header with zero lines under it -- used to be *silently
accepted as valid* by the checker itself, an unrelated, real bug now
fixed in `ProofLogic.py`'s `_validate_block` -- an empty subproof was
already rejected via `CATEGORY_EMPTY_SUBPROOF`; an empty *top-level*
proof wasn't, since the check was gated behind `is_subproof`. This
script exists for the first problem -- coverage -- not the second.)

Two established file conventions, detected automatically
----------------------------------------------------------------------
* **Multi-proof format** (a `# N` header line is present somewhere):
  parsed with `MultiproofParser.run_multi_proof_file`, which reads each
  proof's own expected validity from its `## Proof that` / `## Invalid
  proof that`-style header -- no filename convention needed, the file
  states its own expectation.
* **Bare single-proof format** (no `# N` header): the whole file is one
  proof, parsed with `ProofParser.parse_proof_text`. There's no header
  to read an expectation from, so this project's own established
  convention applies instead (already used by `test_nat_theory.py`/
  `test_number_theory.py`): a filename starting with `invalid_` is
  expected to fail; anything else is expected to validate.

Enforced vs informational directories
----------------------------------------------------------------------
Every directory listed in `ENFORCED_DIRS` is a "real" fixture corpus --
a mismatch there is a build failure. `source/ntProofs/`, `source/
setProofs/`, `source/test_ntProofs/`, and `source/testProofs/` hold
work-in-progress *drafts* (e.g. `source/ntProofs/basicNT.txt`'s
Bezout/GCD sketch, which cites placeholder rule names like "WLOG" and
"Well Ordered Principle" that were never meant to exist yet -- see
NumberTheory.py's module docstring). Their own headers claim
`expected_valid=True` the same as any other proof, even though they're
known, deliberately incomplete. Enforcing them here would fail the
build on drafts that were never supposed to pass; silently skipping
their directories entirely would recreate exactly the blind spot this
script exists to close. So they're still run and still reported -- just
under INFORMATIONAL, not counted toward the exit code -- so a genuine
regression in one is still visible without a false-alarm build failure
over a sketch that was already known-incomplete before this script
existed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.MultiproofParser as mp
import SyLoPy.source.NatThry as nt

ROOT = Path(__file__).resolve().parents[1]

ENFORCED_DIRS = [
    "tests/testSetTheory",
    "tests/testProofsDeclared",
    "tests/testProofsNat",
    "tests/testNumberTheory",
    "tests/testProofs",
    "tests/testDiscreteMath",
]

INFORMATIONAL_DIRS = [
    "tests/setTheoryProofs",
    "tests/testNT",
    "source/ntProofs",
    "source/setProofs",
    "source/test_ntProofs",
    "source/testProofs",
]

# A generous, combined set of resources for BARE single-proof files,
# covering every theory this project currently has, so this script
# doesn't need to guess which one a given fixture file happens to need
# -- matching `test_nat_theory.py`'s explicit-supply approach (rather
# than relying only on the automatic required_rules/axioms/declarations
# metadata `ElaboratedEntries` carries from parsing, which covers
# surface-sugar-triggered resources like NumberTheory's but not
# NatThry's bare-prefix `Nat(...)`/`Succ(...)` vocabulary -- see this
# module's own docstring above for why bare files need this explicitly).
_NAT_AXIOMS, _NAT_SCHEMA_RULES = pl.combine_types(nt.NAT_TYPE)
_NAT_DECLARATIONS = pl.combine_type_declarations(nt.NAT_TYPE)
BARE_PROOF_RULES = pl.default_rules() + _NAT_SCHEMA_RULES
BARE_PROOF_AXIOMS = list(_NAT_AXIOMS)
BARE_PROOF_DECLARATIONS = list(_NAT_DECLARATIONS)


class ProofResult(NamedTuple):
    file: str
    proof_id: str
    expected_valid: bool
    ok: bool
    message: Optional[str]

    @property
    def passed(self) -> bool:
        return self.expected_valid == self.ok


def _looks_like_multi_proof(text: str) -> bool:
    import re
    return any(re.match(r'^\s*#\s*\d', line) for line in text.splitlines())


def _check_bare_proof_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
    # "invalid" anywhere in the stem, not just as a strict prefix --
    # testProofsNat/testNumberTheory use "invalid_foo.txt", but
    # testProofsDeclared uses "foo_invalid_bar.txt" for the same
    # convention (e.g. "exintro_invalid_missing_declarations.txt").
    expected_valid = "invalid" not in path.stem.lower()
    try:
        entries, _ = pp.parse_proof_text(text)
        if not entries:
            return [ProofResult(path.name, "1", expected_valid, False, "file has no proof lines")]
        proof = pl.Proof(
            entries,
            rules=BARE_PROOF_RULES,
            axioms=BARE_PROOF_AXIOMS,
            declarations=BARE_PROOF_DECLARATIONS,
        )
        ok, msg = proof.check()
    except Exception as e:
        ok, msg = False, f"{type(e).__name__}: {e}"
    return [ProofResult(path.name, "1", expected_valid, ok, msg)]


def _check_multi_proof_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
    try:
        results = mp.run_multi_proof_file(text)
    except Exception as e:
        return [ProofResult(path.name, "?", True, False, f"{type(e).__name__}: {e}")]
    return [ProofResult(path.name, number, expected, ok, msg) for number, expected, ok, msg in results]


def check_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
    if _looks_like_multi_proof(text):
        return _check_multi_proof_file(path)
    return _check_bare_proof_file(path)


def run(directories: List[str]) -> List[ProofResult]:
    results = []
    for rel_dir in directories:
        d = ROOT / rel_dir
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.txt")):
            results.extend(check_file(path))
    return results


def _print_results(title: str, results: List[ProofResult], enforced: bool) -> int:
    print(f"\n=== {title} ({'enforced' if enforced else 'informational -- not counted toward exit code'}) ===")
    fails = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if not r.passed:
            fails += 1
        print(f"{status}: {r.file:45s} #{r.proof_id:4s} expected={r.expected_valid!s:5s} got={r.ok!s:5s} {r.message or ''}")
    print(f"{title}: {len(results)} proof(s) checked, {fails} unexpected result(s)")
    return fails if enforced else 0


def main() -> int:
    enforced_results = run(ENFORCED_DIRS)
    informational_results = run(INFORMATIONAL_DIRS)

    enforced_fails = _print_results("Enforced fixture corpus", enforced_results, enforced=True)
    _print_results("Informational (work-in-progress drafts)", informational_results, enforced=False)

    total = len(enforced_results) + len(informational_results)
    print(f"\nTotal proofs checked: {total}  (enforced: {len(enforced_results)}, informational: {len(informational_results)})")
    if enforced_fails:
        print(f"\n{enforced_fails} unexpected result(s) in the enforced fixture corpus -- see FAIL lines above.")
        return 1
    print("\nAll enforced proof fixtures behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




