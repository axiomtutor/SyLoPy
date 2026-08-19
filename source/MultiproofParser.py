


"""Parses a *multi-proof file*: several proofs in one text file, each
introduced by a small header block, rather than one proof per file (see
`ProofParser.py`/`run_tests.py`'s one-proof-per-`.txt` convention).

--------------------------------------------------------------------------
The file format
--------------------------------------------------------------------------
    (* a comment -- can appear anywhere, even mid-line, and is stripped
       before anything else is parsed *)
    # 1
    ## Proof that
    ### if A, B are closed formulas such that: A -> B.
    ### then B, given A.

    1. Let A, B be closed formulas such that: A -> B. (Premise)
    ...

    # 2
    ## Invalid proof.
    ### Invalid use of Some Rule.

    1. ...

  * `# N` -- starts a new proof, `N` an identifier (used only for
    reporting; need not be sequential or unique, though `run_multi_proof_file`
    warns if two blocks share one).
  * `## ...` -- validity marker. Contains "invalid" (case-insensitively)
    -> this proof is expected to fail `.check()`; otherwise expected to
    pass. Mirrors `run_tests.py`'s filename convention
    (`'invalid' in name`), just written inside the file instead of in a
    filename.
  * `### ...` -- free-form description lines, any number of them,
    collected verbatim for reporting and otherwise not parsed -- *except*
    that a line of the form "### then <formula>." has its `<formula>`
    parsed and checked against what the proof actually derives (see
    `_top_level_formulas`/`ProofCase.stated_conclusion` below). A
    "### if ..." line is documentation only, on the same footing as any
    other description line: the *actual* premises are whatever the body
    asserts, normally via a "Let ... such that: ..." line, and those are
    already fully checked by `ProofLogic.Proof` itself.
  * Everything from the first non-`#`/`##`/`###` line to the next `# N`
    (or end of file) is this proof's body, handed to
    `ProofParser.parse_proof_text` unchanged -- every existing proof-text
    feature (subproofs, bundled premises, hybrid subproof citations, ...)
    works inside a multi-proof file exactly as it does in a standalone
    `.txt` fixture.

Blank lines and comments are insignificant everywhere, per the format's
own description ("Additional white space beyond this is ignored").
"""
import os
import re
import sys
from typing import List, NamedTuple, Optional, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.FormulaLogic as fl

# A comment can start and end anywhere, including spanning several
# physical lines (the file's own leading formatting note is one such
# comment) -- DOTALL makes '.' match newlines so a single regex handles
# both the one-line and multi-line cases. Substituting with a single
# space (not '') means a comment sitting between two tokens that would
# otherwise run together ("P(a)(*..*)Q(b)") doesn't accidentally fuse
# them -- though every comment in practice sits on its own line, so this
# mostly just guards against an unusual edge case some future file might
# have.
_COMMENT_RE = re.compile(r'\(\*.*?\*\)', re.DOTALL)

# A bare "# N" delimiter line. Anchored so it can never also match a
# "## ..."/"### ..." line: right after the leading '#', this pattern
# requires only whitespace and digits to the end of the line, whereas a
# "##..."/"###..." line has a second/third literal '#' character there
# instead, which \s*\d*\s*$ cannot match.
_PROOF_HEADER_RE = re.compile(r'^#\s*(\d+)(?:\s*:\s*(.*?))?\s*$')
_VALIDITY_LINE_RE = re.compile(r'^##(?!#)\s*(.+?)\s*$')
_DESCRIPTION_LINE_RE = re.compile(r'^###\s*(.+?)\s*$')
_THEN_LINE_RE = re.compile(r'^then\b\s*(.*)$', re.I)


class ProofCase(NamedTuple):
    """One proof, parsed out of a multi-proof file.

    `entries` is exactly what `ProofParser.parse_proof_text` would
    produce for a standalone `.txt` fixture containing just this proof's
    body -- ready to hand to `ProofLogic.Proof(entries, ...)` unchanged.

    `title` is whatever follows "``# N:``" on the header line, or `None`
    for a bare "``# N``" with no title -- the name a validated proof gets
    promoted under (see `promote_theorems_across_cases` below), matching
    how proof text itself already cites a promoted theorem by that same
    title text (e.g. "``(The empty set subset theorem)``").
    """
    number: str
    expected_valid: bool
    description: List[str]
    stated_conclusion: Optional[fl.Formula]
    entries: list
    raw_lines: List[str]
    title: Optional[str] = None
    parse_error: Optional[str] = None


# Tags whose formula was actually established by *inference*, as opposed
# to merely asserted (premise/axiom) or introduced as vocabulary
# (declare*). A stated "### then ..." conclusion is checked against only
# these -- proof #10-style fixtures that legitimately re-derive a premise
# via a genuine inference step (e.g. "A <-> B" both premised *and*
# re-derived through Biconditional Elimination + Introduction) still
# satisfy this; a conclusion that's never anything but a bare premise
# citation should not, on the theory that a proof "concluding" with
# exactly what it assumed, with no inference in between, hasn't proved
# anything.
_DERIVED_TAGS = {'rule', 'rule_below', 'rule_hybrid'}


def _top_level_formulas(entries: list) -> List[fl.Formula]:
    """Every Formula a top-level (non-subproof-block) entry in `entries`
    actually *derived* via inference (tag in `_DERIVED_TAGS`), in order.
    Expands a bundled `phi` (a list) into its individual formulas, and
    skips anything that isn't a Formula at all.

    Deliberately excludes premises, axioms, and declarations -- see
    `_DERIVED_TAGS`'s comment for why a proof's stated conclusion needs
    to be checked against what it actually established through
    inference, not against something it simply assumed and never did
    anything with. Also skips standalone labeled subproof blocks
    entirely: their formulas are conditional on an assumption, not part
    of the outer proof's unconditional conclusions.
    """
    result: List[fl.Formula] = []
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


def conclusion_is_derived(entries: list, stated_conclusion: Optional[fl.Formula]) -> bool:
    """True if `stated_conclusion` is `None` (nothing to check) or
    `_ast_eq`-matches some top-level formula the proof actually derived.
    """
    if stated_conclusion is None:
        return True
    return any(pl._ast_eq(stated_conclusion, f) for f in _top_level_formulas(entries))


def _split_header_block(block: List[str]) -> Tuple[bool, List[str], int]:
    """Parse `block[1:]`'s leading run of `##`/`###`/blank lines (`block[0]`
    is always the `# N` line itself), returning `(expected_valid,
    description_lines, body_start_index)` where `body_start_index` is
    the index (within `block`) of the first line that starts this
    proof's actual body.
    """
    expected_valid = True
    description: List[str] = []
    body_start = 1
    for j in range(1, len(block)):
        stripped = block[j].strip()
        if not stripped:
            body_start = j + 1
            continue
        m_valid = _VALIDITY_LINE_RE.match(stripped)
        if m_valid:
            if 'invalid' in m_valid.group(1).lower():
                expected_valid = False
            body_start = j + 1
            continue
        m_desc = _DESCRIPTION_LINE_RE.match(stripped)
        if m_desc:
            description.append(m_desc.group(1))
            body_start = j + 1
            continue
        break
    return expected_valid, description, body_start


def _stated_conclusion_from(description: List[str]) -> Optional[fl.Formula]:
    """Find a "### then <formula>." description line, if any, and parse
    its formula. Only the *first* such line is used -- the file format
    describes exactly one conclusion per proof, and nothing here stops a
    proof from having zero (many "Invalid proof" fixtures just describe
    what's wrong instead, and have no clean "then" line at all).
    """
    for d in description:
        m = _THEN_LINE_RE.match(d.strip())
        if m:
            concl_text = m.group(1).strip().rstrip('.').strip()
            if concl_text:
                return pp.parse_formula(concl_text)
    return None


def parse_multi_proof_file(text: str) -> List[ProofCase]:
    """Split `text` into one `ProofCase` per `# N` block."""
    text = _COMMENT_RE.sub(' ', text)
    lines = text.splitlines()

    header_positions = [idx for idx, line in enumerate(lines) if _PROOF_HEADER_RE.match(line.strip())]

    cases = []
    for pos_idx, start in enumerate(header_positions):
        end = header_positions[pos_idx + 1] if pos_idx + 1 < len(header_positions) else len(lines)
        block = lines[start:end]
        header_match = _PROOF_HEADER_RE.match(block[0].strip())
        number = header_match.group(1)
        title = header_match.group(2).strip() if header_match.group(2) and header_match.group(2).strip() else None

        expected_valid, description, body_start = _split_header_block(block)
        stated_conclusion = _stated_conclusion_from(description)

        body_raw = [ln for ln in block[body_start:] if ln.strip()]
        body_text = '\n'.join(block[body_start:])
        parse_error = None
        try:
            entries, raw_lines = pp.parse_proof_text(body_text) if body_text.strip() else ([], [])
        except Exception as exc:
            # A malformed proof must be recorded as a failed case rather
            # than aborting parsing of the entire multi-proof file. This
            # lets the test runner continue and report every proof.
            entries, raw_lines = [], []
            parse_error = f"{type(exc).__name__}: {exc}"

        cases.append(ProofCase(number=number, expected_valid=expected_valid, description=description,
                                stated_conclusion=stated_conclusion, entries=entries, raw_lines=raw_lines,
                                title=title, parse_error=parse_error))
    return cases


def run_multi_proof_file(text: str, axioms: Optional[list] = None, rules: Optional[list] = None,
                          declarations: Optional[list] = None) -> List[tuple]:
    """Parse and check every proof case in `text`, returning
    `(number, expected_valid, ok, msg)` for each -- the same shape
    `run_tests.py.run_suite` returns, so both can share one reporting
    loop if desired.

    A case that validates (`ok=True`) but never actually derives its
    stated "### then ..." conclusion is reported as `ok=False` with a
    message saying so -- from the checker's point of view every *line*
    was justified, but the proof didn't prove what it claimed to.

    Theorem promotion: a case whose header names a title (``# N: Title``)
    that goes on to validate is promoted, via `ProofLogic.promote_theorem`,
    into a rule every *later* case in this same file may cite by that
    title -- see `ELABORATION_ARCHITECTURE.md` and `NumberTheory.py`'s
    module docstring for why proof text never has to spell out a separate
    "definition" rule for something already established this way.
    Promotion is best-effort: a titled proof whose shape
    `promote_theorem` can't generalize (e.g. it derives nothing at the
    top level to promote as a conclusion) is simply not promoted, with a
    warning printed, rather than failing the whole file over a theorem
    nothing later necessarily needs to cite.
    """
    cases = parse_multi_proof_file(text)

    seen_numbers = set()
    for case in cases:
        if case.number in seen_numbers:
            print(f"Warning: proof number '{case.number}' appears more than once in this file")
        seen_numbers.add(case.number)

    results = []
    promoted_rules: list = []
    for case in cases:
        if case.parse_error is not None:
            results.append((case.number, case.expected_valid, False, case.parse_error))
            continue
        try:
            proof = pl.Proof(
                case.entries,
                axioms=axioms or [],
                rules=(rules or pl.default_rules()) + promoted_rules,
                declarations=declarations or [],
            )
            ok, msg = proof.check()
            if ok and case.stated_conclusion is not None and not conclusion_is_derived(case.entries, case.stated_conclusion):
                ok = False
                msg = f"every line validated, but the proof never derived its stated conclusion {case.stated_conclusion!r}"
            if ok and case.title:
                try:
                    promoted_rules.append(pl.promote_theorem(case.title, proof))
                except ValueError as promotion_error:
                    print(f"Warning: proof '{case.title}' (#{case.number}) was not promoted: {promotion_error}")
        except Exception as e:
            ok, msg = False, f'parse/check error: {e}'
        results.append((case.number, case.expected_valid, ok, msg))
    return results


def main(path: str) -> int:
    with open(path) as f:
        text = f.read()
    results = run_multi_proof_file(text)
    fails = []
    for number, expected, ok, msg in results:
        status = 'PASS' if expected == ok else 'FAIL'
        print(f"{status}: proof #{number:6s} expected={expected!s:5s} got={ok!s:5s} {msg or ''}")
        if status == 'FAIL':
            fails.append((number, expected, ok, msg))
    print(f"\nTotal: {len(results)}  Passed: {len(results) - len(fails)}  Failed: {len(fails)}")
    return 0 if not fails else 2


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        raise SystemExit(main(sys.argv[1]))
    else:
        print("Run with a multi-proof text file as an argument.")




