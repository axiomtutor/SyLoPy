#!/usr/bin/env python3
"""Validate the project's proof fixture corpora."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

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
    return any(re.match(r"^\s*#\s*\d", line) for line in text.splitlines())


def _check_bare_proof_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
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


def run(directories: Sequence[str]) -> List[ProofResult]:
    results = []
    for rel_dir in directories:
        d = ROOT / rel_dir
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.txt")):
            results.extend(check_file(path))
    return results


def _suite_name(rel_dir: str) -> str:
    return Path(rel_dir).name


def available_suites() -> List[tuple[str, str]]:
    return [("enforced", d) for d in ENFORCED_DIRS] + [("informational", d) for d in INFORMATIONAL_DIRS]


def _resolve_suite(name: str) -> tuple[str, str]:
    normalized = name.rstrip("/")
    candidates = {d: category for category, d in available_suites()}
    if normalized in candidates:
        return candidates[normalized], normalized

    basename_matches = [(category, d) for category, d in available_suites() if _suite_name(d) == normalized]
    if len(basename_matches) == 1:
        return basename_matches[0]
    if not basename_matches:
        available = ", ".join(_suite_name(d) for _, d in available_suites())
        raise ValueError(f"unknown suite {name!r}; available suites: {available}")
    matches = ", ".join(d for _, d in basename_matches)
    raise ValueError(f"suite name {name!r} is ambiguous; use one of: {matches}")


def _print_suite_summary(rel_dir: str, results: List[ProofResult], enforced: bool) -> int:
    failures = sum(not r.passed for r in results)
    passed = len(results) - failures
    status = "PASS" if failures == 0 else "FAIL"
    qualifier = "enforced" if enforced else "informational"
    print(f"{status:<5} {rel_dir:<32} {passed}/{len(results)} proofs pass ({qualifier})")
    return failures if enforced else 0


def _print_selected_suite(rel_dir: str, results: List[ProofResult], enforced: bool, verbose: bool) -> int:
    failures = sum(not r.passed for r in results)
    passed = len(results) - failures
    print(f"\n=== {rel_dir} ({'enforced' if enforced else 'informational'}) ===")
    if verbose:
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            detail = f" {r.message}" if r.message else ""
            print(f"{status}: {r.file:45s} #{r.proof_id:4s} expected={r.expected_valid!s:5s} got={r.ok!s:5s}{detail}")
    print(f"{rel_dir}: {passed}/{len(results)} proofs pass")
    return failures if enforced else 0


def _list_suites() -> None:
    print("Enforced suites:")
    for rel_dir in ENFORCED_DIRS:
        print(f"  {_suite_name(rel_dir):24s} {rel_dir}")
    print("\nInformational suites:")
    for rel_dir in INFORMATIONAL_DIRS:
        print(f"  {_suite_name(rel_dir):24s} {rel_dir}")


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SyLoPy proof fixtures by suite.")
    parser.add_argument("--suite", metavar="NAME", help="run and report only the named proof-fixture suite")
    parser.add_argument("--list-suites", action="store_true", help="list available proof-fixture suites and exit")
    parser.add_argument("--verbose", action="store_true", help="show individual proof results")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)

    if args.list_suites:
        _list_suites()
        return 0

    if args.suite:
        try:
            category, rel_dir = _resolve_suite(args.suite)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return _print_selected_suite(rel_dir, run([rel_dir]), category == "enforced", args.verbose)

    enforced_fails = 0
    print("\n=== Enforced fixture corpus ===")
    for rel_dir in ENFORCED_DIRS:
        enforced_fails += _print_suite_summary(rel_dir, run([rel_dir]), True)

    print("\n=== Informational fixture corpus ===")
    for rel_dir in INFORMATIONAL_DIRS:
        _print_suite_summary(rel_dir, run([rel_dir]), False)

    enforced_results = run(ENFORCED_DIRS)
    informational_results = run(INFORMATIONAL_DIRS)
    total = len(enforced_results) + len(informational_results)
    enforced_passed = sum(r.passed for r in enforced_results)
    informational_passed = sum(r.passed for r in informational_results)
    print(f"\nTotal proofs checked: {total} (enforced: {enforced_passed}/{len(enforced_results)}, informational: {informational_passed}/{len(informational_results)})")
    if enforced_fails:
        print(f"\n{enforced_fails} unexpected result(s) in the enforced fixture corpus.")
        return 1
    print("\nAll enforced proof fixtures behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
