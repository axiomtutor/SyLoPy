#!/usr/bin/env python3
"""Validate the project's proof fixture corpora.

Default output is suite-oriented. ``--suite`` selects one fixture suite,
``--verbose`` prints individual proof results, and ``--list-suites`` lists
available suites.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPOSITORY_ROOT.parent))

import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.MultiproofParser as mp
import SyLoPy.source.NatThry as nt

ROOT = _REPOSITORY_ROOT

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


def _validate_entries(entries) -> bool:
    proof = pl.Proof(
        entries,
        axioms=BARE_PROOF_AXIOMS,
        rules=BARE_PROOF_RULES,
        declarations=BARE_PROOF_DECLARATIONS,
    )
    return proof.validate()


def _check_bare_proof_file(path: Path) -> List[ProofResult]:
    expected_valid = "invalid" not in path.stem.lower()
    try:
        entries, _ = pp.parse_proof_text(path.read_text())
        if not entries:
            return [
                ProofResult(
                    path.name, "1", expected_valid, False, "file has no proof lines"
                )
            ]
        return [
            ProofResult(
                path.name,
                "1",
                expected_valid,
                _validate_entries(entries),
                None,
            )
        ]
    except Exception as exc:
        return [
            ProofResult(
                path.name,
                "1",
                expected_valid,
                False,
                f"{type(exc).__name__}: {exc}",
            )
        ]


def _check_multi_proof_file(path: Path) -> List[ProofResult]:
    """Validate a multi-proof file through the canonical multi-proof runner.

    This is deliberately the same execution path used by the multi-proof
    fixture tests. In particular, titled proofs are promoted before later
    cases are checked, so theorem citations have identical semantics here.
    """
    try:
        results = mp.run_multi_proof_file(
            path.read_text(),
            axioms=BARE_PROOF_AXIOMS,
            rules=BARE_PROOF_RULES,
            declarations=BARE_PROOF_DECLARATIONS,
        )
    except Exception as exc:
        return [
            ProofResult(
                path.name,
                "?",
                True,
                False,
                f"{type(exc).__name__}: {exc}",
            )
        ]

    converted = [
        ProofResult(
            path.name,
            str(proof_id),
            expected_valid,
            ok,
            message,
        )
        for proof_id, expected_valid, ok, message in results
    ]
    if not converted:
        converted.append(
            ProofResult(path.name, "?", True, False, "file contains no proof cases")
        )
    return converted


def check_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
    return _check_multi_proof_file(path) if _looks_like_multi_proof(text) else _check_bare_proof_file(path)


def run(directories: Sequence[str]) -> List[ProofResult]:
    results: List[ProofResult] = []
    for rel_dir in directories:
        directory = ROOT / rel_dir
        if directory.is_dir():
            for path in sorted(directory.glob("*.txt")):
                results.extend(check_file(path))
    return results


def _suite_name(rel_dir: str) -> str:
    return Path(rel_dir).name


def available_suites():
    return [("enforced", d) for d in ENFORCED_DIRS] + [
        ("informational", d) for d in INFORMATIONAL_DIRS
    ]


def _resolve_suite(name: str):
    name = name.rstrip("/")
    candidates = {d: c for c, d in available_suites()}
    if name in candidates:
        return candidates[name], name

    matches = [(c, d) for c, d in available_suites() if _suite_name(d) == name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(
            f"unknown suite {name!r}; available suites: "
            f"{', '.join(_suite_name(d) for _, d in available_suites())}"
        )
    raise ValueError(
        f"suite name {name!r} is ambiguous; use one of: "
        f"{', '.join(d for _, d in matches)}"
    )


def _print_selected_suite(rel_dir, results, enforced, verbose):
    failures = [r for r in results if not r.passed]
    print(f"=== {rel_dir} ({'enforced' if enforced else 'informational'}) ===")
    if verbose:
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            detail = f" {r.message}" if r.message else ""
            print(
                f"{status}: {r.file} #{r.proof_id} "
                f"expected={r.expected_valid} got={r.ok}{detail}"
            )
    elif failures:
        for r in failures:
            detail = f": {r.message}" if r.message else ""
            print(f"FAIL {r.file} #{r.proof_id}{detail}")
    print(f"{len(results) - len(failures)}/{len(results)} proofs pass")
    return len(failures) if enforced else 0


def _print_suite_summary(rel_dir, results, enforced):
    failures = sum(not r.passed for r in results)
    print(
        f"{'PASS' if failures == 0 else 'FAIL':<5} {rel_dir:<32} "
        f"{len(results) - failures}/{len(results)} proofs pass "
        f"({'enforced' if enforced else 'informational'})"
    )
    return failures if enforced else 0


def _list_suites():
    print("Enforced suites:")
    for d in ENFORCED_DIRS:
        print(f"  {_suite_name(d):<24} {d}")
    print("\nInformational suites:")
    for d in INFORMATIONAL_DIRS:
        print(f"  {_suite_name(d):<24} {d}")


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Validate SyLoPy proof fixtures by suite.")
    p.add_argument("--suite", metavar="NAME")
    p.add_argument("--list-suites", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
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
        return _print_selected_suite(
            rel_dir,
            run([rel_dir]),
            category == "enforced",
            args.verbose,
        )

    enforced_fails = 0
    print("=== Enforced fixture corpus ===")
    for d in ENFORCED_DIRS:
        enforced_fails += _print_suite_summary(d, run([d]), True)

    print("\n=== Informational fixture corpus ===")
    for d in INFORMATIONAL_DIRS:
        _print_suite_summary(d, run([d]), False)

    er = run(ENFORCED_DIRS)
    ir = run(INFORMATIONAL_DIRS)
    print(
        f"\nTotal proofs checked: {len(er) + len(ir)} "
        f"(enforced: {sum(r.passed for r in er)}/{len(er)}, "
        f"informational: {sum(r.passed for r in ir)}/{len(ir)})"
    )
    if enforced_fails:
        print(f"\n{enforced_fails} unexpected result(s) in the enforced fixture corpus.")
        return 1
    print("\nAll enforced proof fixtures behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
