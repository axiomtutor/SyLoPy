#!/usr/bin/env python3
"""Validate SyLoPy's proof fixture corpora.

A fixture file may contain one proof or multiple ``# N`` proof blocks. The
proof parser remains the single proof-language parser; this module owns the
fixture-file container format and validation/reporting policy.
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
import SyLoPy.source.FormulaLogic as fl
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

_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)
_PROOF_HEADER_RE = re.compile(r"^#\s*(\d+)(?:\s*:\s*(.*?))?\s*$")
_VALIDITY_LINE_RE = re.compile(r"^##(?!#)\s*(.+?)\s*$")
_DESCRIPTION_LINE_RE = re.compile(r"^###\s*(.+?)\s*$")
_THEN_LINE_RE = re.compile(r"^then\b\s*(.*)$", re.I)
_DERIVED_TAGS = {"rule", "rule_below", "rule_hybrid"}


class ProofCase(NamedTuple):
    number: str
    expected_valid: bool
    description: List[str]
    stated_conclusion: Optional[fl.Formula]
    entries: list
    raw_lines: List[str]
    title: Optional[str] = None
    parse_error: Optional[str] = None


def _top_level_formulas(entries: list) -> List[fl.Formula]:
    result = []
    for entry in entries:
        parsed = pl._classify_entry(entry)
        if isinstance(parsed, str) or parsed.is_subproof_block:
            continue
        justification = parsed.justification
        if not isinstance(justification, tuple) or not justification or justification[0] not in _DERIVED_TAGS:
            continue
        phi = parsed.phi
        if isinstance(phi, list):
            result.extend(f for f in phi if isinstance(f, fl.Formula))
        elif isinstance(phi, fl.Formula):
            result.append(phi)
    return result


def conclusion_is_derived(entries, stated_conclusion):
    if stated_conclusion is None:
        return True
    return any(pl._ast_eq(stated_conclusion, formula) for formula in _top_level_formulas(entries))


def _split_header_block(block):
    expected_valid = True
    description = []
    body_start = 1
    for index in range(1, len(block)):
        stripped = block[index].strip()
        if not stripped:
            body_start = index + 1
            continue
        match = _VALIDITY_LINE_RE.match(stripped)
        if match:
            if "invalid" in match.group(1).lower():
                expected_valid = False
            body_start = index + 1
            continue
        match = _DESCRIPTION_LINE_RE.match(stripped)
        if match:
            description.append(match.group(1))
            body_start = index + 1
            continue
        break
    return expected_valid, description, body_start


def _stated_conclusion_from(description):
    for description_line in description:
        match = _THEN_LINE_RE.match(description_line.strip())
        if match:
            text = match.group(1).strip().rstrip(".").strip()
            if text:
                return pp.parse_formula(text)
    return None


def parse_multi_proof_file(text):
    """Parse a fixture file containing ``# N`` proof blocks."""
    text = _COMMENT_RE.sub(" ", text)
    lines = text.splitlines()
    positions = [index for index, line in enumerate(lines) if _PROOF_HEADER_RE.match(line.strip())]
    cases = []
    for position, start in enumerate(positions):
        end = positions[position + 1] if position + 1 < len(positions) else len(lines)
        block = lines[start:end]
        header = _PROOF_HEADER_RE.match(block[0].strip())
        expected, description, body_start = _split_header_block(block)
        body = "\n".join(block[body_start:])
        try:
            entries, raw_lines = pp.parse_proof_text(body) if body.strip() else ([], [])
            error = None
        except Exception as exc:
            entries, raw_lines = [], []
            error = f"{type(exc).__name__}: {exc}"
        title = header.group(2).strip() if header.group(2) and header.group(2).strip() else None
        cases.append(
            ProofCase(
                header.group(1),
                expected,
                description,
                _stated_conclusion_from(description),
                entries,
                raw_lines,
                title,
                error,
            )
        )
    return cases


def run_multi_proof_file(text, axioms=None, rules=None, declarations=None):
    """Parse and validate all proof blocks, promoting titled proofs in order."""
    cases = parse_multi_proof_file(text)
    results = []
    promoted = []
    seen = set()
    for case in cases:
        if case.number in seen:
            print(f"Warning: proof number '{case.number}' appears more than once in this file")
        seen.add(case.number)
        if case.parse_error:
            results.append((case.number, case.expected_valid, False, case.parse_error))
            continue
        try:
            proof = pl.Proof(
                case.entries,
                axioms=axioms or [],
                rules=(rules or pl.default_rules()) + promoted,
                declarations=declarations or [],
            )
            ok, message = proof.check()
            if ok and case.stated_conclusion is not None and not conclusion_is_derived(case.entries, case.stated_conclusion):
                ok = False
                message = (
                    "every line validated, but the proof never derived its stated "
                    f"conclusion {case.stated_conclusion!r}"
                )
            if ok and case.title:
                try:
                    promoted.append(pl.promote_theorem(case.title, proof))
                except ValueError as exc:
                    print(f"Warning: proof #{case.number} ({case.title!r}) was not promoted: {exc}")
        except Exception as exc:
            ok, message = False, f"parse/check error: {exc}"
        results.append((case.number, case.expected_valid, ok, message))
    return results


class ProofResult(NamedTuple):
    file: str
    proof_id: str
    expected_valid: bool
    ok: bool
    message: Optional[str]
    implementation_error: bool = False

    @property
    def passed(self) -> bool:
        return not self.implementation_error and self.expected_valid == self.ok


def _looks_like_multi_proof(text: str) -> bool:
    return any(_PROOF_HEADER_RE.match(line.strip()) for line in text.splitlines())


def _validate_entries(entries):
    proof = pl.Proof(
        entries,
        axioms=BARE_PROOF_AXIOMS,
        rules=BARE_PROOF_RULES,
        declarations=BARE_PROOF_DECLARATIONS,
    )
    return proof.check()


def _check_bare_proof_file(path: Path) -> List[ProofResult]:
    expected_valid = "invalid" not in path.stem.lower()
    try:
        entries, _ = pp.parse_proof_text(path.read_text())
        if not entries:
            return [ProofResult(path.name, "1", expected_valid, False, "file has no proof lines", True)]
        ok, message = _validate_entries(entries)
        return [ProofResult(path.name, "1", expected_valid, ok, message, False)]
    except pp.ElaborationError as exc:
        return [
            ProofResult(
                path.name,
                "1",
                expected_valid,
                False,
                f"{type(exc).__name__}: {exc}",
                expected_valid,
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
                True,
            )
        ]


def _check_multi_proof_file(path: Path) -> List[ProofResult]:
    try:
        results = run_multi_proof_file(
            path.read_text(),
            axioms=BARE_PROOF_AXIOMS,
            rules=BARE_PROOF_RULES,
            declarations=BARE_PROOF_DECLARATIONS,
        )
    except Exception as exc:
        return [ProofResult(path.name, "?", True, False, f"{type(exc).__name__}: {exc}", True)]

    converted = []
    for proof_id, expected_valid, ok, message in results:
        implementation_error = bool(
            message and (message.startswith("parse/check error:") or message.startswith("parse error:"))
        )
        converted.append(ProofResult(path.name, str(proof_id), expected_valid, ok, message, implementation_error))
    if not converted:
        converted.append(ProofResult(path.name, "?", True, False, "file contains no proof cases", True))
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
    return [("enforced", d) for d in ENFORCED_DIRS] + [("informational", d) for d in INFORMATIONAL_DIRS]


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
            f"unknown suite {name!r}; available suites: {', '.join(_suite_name(d) for _, d in available_suites())}"
        )
    raise ValueError(
        f"suite name {name!r} is ambiguous; use one of: {', '.join(d for _, d in matches)}"
    )


def _print_selected_suite(rel_dir, results, enforced, verbose):
    failures = [r for r in results if not r.passed]
    print(f"=== {rel_dir} ({'enforced' if enforced else 'informational'}) ===")
    if verbose:
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            detail = f" {r.message}" if r.message else ""
            print(f"{status}: {r.file} #{r.proof_id} expected={r.expected_valid} got={r.ok}{detail}")
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
        return _print_selected_suite(rel_dir, run([rel_dir]), category == "enforced", args.verbose)

    enforced_fails = 0
    print("=== Enforced fixture corpus ===")
    for directory in ENFORCED_DIRS:
        enforced_fails += _print_suite_summary(directory, run([directory]), True)

    print("\n=== Informational fixture corpus ===")
    for directory in INFORMATIONAL_DIRS:
        _print_suite_summary(directory, run([directory]), False)

    enforced = run(ENFORCED_DIRS)
    informational = run(INFORMATIONAL_DIRS)
    print(
        f"\nTotal proofs checked: {len(enforced) + len(informational)} "
        f"(enforced: {sum(r.passed for r in enforced)}/{len(enforced)}, "
        f"informational: {sum(r.passed for r in informational)}/{len(informational)})"
    )
    if enforced_fails:
        print(f"\n{enforced_fails} unexpected result(s) in the enforced fixture corpus.")
        return 1
    print("\nAll enforced proof fixtures behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
