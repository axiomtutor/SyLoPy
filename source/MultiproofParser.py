

"""Parser and validator support for multi-proof fixture files."""
import os
import re
import sys
from typing import List, NamedTuple, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.FormulaLogic as fl

_COMMENT_RE = re.compile(r'\(\*.*?\*\)', re.DOTALL)
_PROOF_HEADER_RE = re.compile(r'^#\s*(\d+)(?:\s*:\s*(.*?))?\s*$')
_VALIDITY_LINE_RE = re.compile(r'^##(?!#)\s*(.+?)\s*$')
_DESCRIPTION_LINE_RE = re.compile(r'^###\s*(.+?)\s*$')
_THEN_LINE_RE = re.compile(r'^then\b\s*(.*)$', re.I)
_DERIVED_TAGS = {'rule', 'rule_below', 'rule_hybrid'}

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
    for e in entries:
        parsed = pl._classify_entry(e)
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
    return any(pl._ast_eq(stated_conclusion, f) for f in _top_level_formulas(entries))

def _split_header_block(block):
    expected_valid = True
    description = []
    body_start = 1
    for j in range(1, len(block)):
        stripped = block[j].strip()
        if not stripped:
            body_start = j + 1
            continue
        m = _VALIDITY_LINE_RE.match(stripped)
        if m:
            if 'invalid' in m.group(1).lower():
                expected_valid = False
            body_start = j + 1
            continue
        m = _DESCRIPTION_LINE_RE.match(stripped)
        if m:
            description.append(m.group(1))
            body_start = j + 1
            continue
        break
    return expected_valid, description, body_start

def _stated_conclusion_from(description):
    for d in description:
        m = _THEN_LINE_RE.match(d.strip())
        if m:
            text = m.group(1).strip().rstrip('.').strip()
            if text:
                return pp.parse_formula(text)
    return None

def parse_multi_proof_file(text):
    text = _COMMENT_RE.sub(' ', text)
    lines = text.splitlines()
    positions = [i for i, line in enumerate(lines) if _PROOF_HEADER_RE.match(line.strip())]
    cases = []
    for k, start in enumerate(positions):
        end = positions[k + 1] if k + 1 < len(positions) else len(lines)
        block = lines[start:end]
        header = _PROOF_HEADER_RE.match(block[0].strip())
        expected, description, body_start = _split_header_block(block)
        body = '\n'.join(block[body_start:])
        try:
            entries, raw_lines = pp.parse_proof_text(body) if body.strip() else ([], [])
            error = None
        except Exception as exc:
            entries, raw_lines = [], []
            error = f"{type(exc).__name__}: {exc}"
        title = header.group(2).strip() if header.group(2) and header.group(2).strip() else None
        cases.append(ProofCase(header.group(1), expected, description,
                               _stated_conclusion_from(description), entries,
                               raw_lines, title, error))
    return cases

def run_multi_proof_file(text, axioms=None, rules=None, declarations=None):
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
            proof = pl.Proof(case.entries, axioms=axioms or [],
                             rules=(rules or pl.default_rules()) + promoted,
                             declarations=declarations or [])
            ok, msg = proof.check()
            if ok and case.stated_conclusion is not None and not conclusion_is_derived(case.entries, case.stated_conclusion):
                ok = False
                msg = f"every line validated, but the proof never derived its stated conclusion {case.stated_conclusion!r}"
            if ok and case.title:
                try:
                    promoted.append(pl.promote_theorem(case.title, proof))
                except ValueError as exc:
                    print(f"Warning: proof #{case.number} ({case.title!r}) was not promoted: {exc}")
        except Exception as exc:
            ok, msg = False, f'parse/check error: {exc}'
        results.append((case.number, case.expected_valid, ok, msg))
    return results

def main(path):
    with open(path) as f:
        results = run_multi_proof_file(f.read())
    failures = sum(expected != ok for _, expected, ok, _ in results)
    for number, expected, ok, msg in results:
        status = 'PASS' if expected == ok else 'FAIL'
        print(f"{status}: proof #{number} expected={expected} got={ok} {msg or ''}")
    print(f"\nTotal: {len(results)}  Passed: {len(results)-failures}  Failed: {failures}")
    return 0 if not failures else 2

if __name__ == '__main__':
    if len(sys.argv) > 1:
        raise SystemExit(main(sys.argv[1]))
    print("Run with a multi-proof text file as an argument.")
