#!/usr/bin/env python3
"""Validate SyLoPy's proof fixture corpora.

A fixture file may contain one proof or multiple ``# N`` proof blocks. The
proof parser remains the single proof-language parser; this module owns the
fixture-file container format and validation/reporting policy.
"""
from __future__ import annotations

import argparse
import atexit
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
# The code imports itself as ``SyLoPy.source...``. If the checkout directory
# has another name, expose it under that name through a temporary symlink.
if _REPOSITORY_ROOT.name == "SyLoPy":
    _IMPORT_PARENT = _REPOSITORY_ROOT.parent
else:
    _IMPORT_PARENT = Path(tempfile.mkdtemp(prefix="sylopy-alias-"))
    atexit.register(shutil.rmtree, _IMPORT_PARENT, ignore_errors=True)
    (_IMPORT_PARENT / "SyLoPy").symlink_to(_REPOSITORY_ROOT, target_is_directory=True)
sys.path.insert(0, str(_IMPORT_PARENT))

import SyLoPy.source.ProofParser as pp
import SyLoPy.source.ProofJustification as pj
import SyLoPy.source.ProofLogic as pl
import SyLoPy.source.FormulaLogic as fl
import SyLoPy.source.SavedChecks as sc
import SyLoPy.source.NatThry as nt
import SyLoPy.source.NumberTheory as num_theory
import SyLoPy.source.SetTheory as set_theory

ROOT = _REPOSITORY_ROOT
DEFAULT_SAVED_RESULTS = ROOT / ".saved_results"

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
    "source/testProofs",
]

_NAT_AXIOMS, _NAT_SCHEMA_RULES = pl.combine_types(nt.NAT_TYPE)
_NAT_DECLARATIONS = pl.combine_type_declarations(nt.NAT_TYPE)

_INT_AXIOMS, _INT_SCHEMA_RULES = pl.combine_types(num_theory.INT_TYPE)
_INT_DECLARATIONS = pl.combine_type_declarations(num_theory.INT_TYPE)

_SET_RULES = set_theory.SET_THEORY_ENVIRONMENT.rules

BARE_PROOF_RULES = (
    pl.default_rules() + _NAT_SCHEMA_RULES + _INT_SCHEMA_RULES + _SET_RULES
)
BARE_PROOF_AXIOMS = list(_NAT_AXIOMS) + list(_INT_AXIOMS)
BARE_PROOF_DECLARATIONS = list(_NAT_DECLARATIONS) + list(_INT_DECLARATIONS) + set_theory.SET_DECLARATIONS

_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)
_PROOF_HEADER_RE = re.compile(r"^#\s*(\d+)(?:\s*:\s*(.*?))?\s*$")
_VALIDITY_LINE_RE = re.compile(r"^##(?!#)\s*(.+?)\s*$")
_DESCRIPTION_LINE_RE = re.compile(r"^###\s*(.+?)\s*$")
_THEN_LINE_RE = re.compile(r"^then\b\s*(.*)$", re.I)
_DERIVED_TAGS = {"rule", "rule_below", "rule_hybrid"}
_USE_LINE_RE = re.compile(r"^use\s+(.+?)\.?$", re.I)

# What a `Use` line may name besides a file. Every file is checked in one
# environment that loads all of these, so naming one changes nothing (see
# docs/PROOF_FILE_FORMAT.md, "Theory directives").
THEORY_NAMES = frozenset({
    "discrete math",
    "discrete mathematics",
    "set theory",
    "number theory",
    "order theory",
})


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
    # Up to the names of bound variables: a stated "there exists a unique set ..."
    # and the proof's own `exists Y, ... forall X, ...` are the same statement.
    return any(pl._alpha_eq(stated_conclusion, formula) for formula in _top_level_formulas(entries))


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


def _stated_conclusion_from(description, proof_number=None, warn_unparseable=True):
    """Parse the formula named by a `### then ...` description line, if any.

    Deliberately tolerant of a `parse_formula` failure here: this is only
    ever used for `conclusion_is_derived`'s extra "did the proof actually
    derive what it claims to" safety-net check, not for validating the
    proof itself, so an unparseable description (natural-language
    phrasing the current formula grammar doesn't support, e.g. "there
    exists an integer combination of x, y = (x, y)") should mean "skip
    that extra check for this one proof" -- printed as a warning, the
    same way an unpromotable theorem is -- not an uncaught exception.
    Before this, one proof block's unparseable description in an
    otherwise-fine multi-proof file would blow up `parse_multi_proof_file`
    entirely, before any of the file's *other* proofs were ever
    individually checked at all (`_check_multi_proof_file`'s own
    outer `except Exception` would catch it, but by then there was no
    per-case detail left to report -- every case in the file showed up
    as a single opaque `proof_id="?"` failure).
    """
    for description_line in description:
        match = _THEN_LINE_RE.match(description_line.strip())
        if match:
            text = match.group(1).strip().rstrip(".").strip()
            if text:
                try:
                    return pp.parse_formula(text)
                except Exception as exc:
                    if warn_unparseable:
                        label = f"#{proof_number} " if proof_number else ""
                        print(
                            f"Warning: proof {label}has a 'then' description "
                            f"({text!r}) that doesn't parse as a formula "
                            f"({type(exc).__name__}: {exc}) -- skipping the "
                            "stated-conclusion check for this proof"
                        )
                    return None
    return None


def proof_titles(text):
    """The titles on the proof headers of a multi-proof file, in order."""
    titles = []
    for line in _COMMENT_RE.sub(" ", text).splitlines():
        match = _PROOF_HEADER_RE.match(line.strip())
        if match and match.group(2) and match.group(2).strip():
            titles.append(match.group(2).strip())
    return titles


def parse_multi_proof_file(text, *, warn_unparseable_description=True, imported_titles=()):
    """Parse a fixture file containing ``# N`` proof blocks.

    `imported_titles` are the titles of the theorems of other files that the
    file may cite (see `check_file`)."""
    text = _COMMENT_RE.sub(" ", text)
    lines = text.splitlines()
    positions = [index for index, line in enumerate(lines) if _PROOF_HEADER_RE.match(line.strip())]
    # The titles of every proof in the file, so that one proof can cite another
    # with the lines that state its premises (`(Title from 3)`): the parser
    # cannot tell a title from a misspelled rule name. Parsing a citation does
    # not give the proof the theorem; `run_multi_proof_file` does, once the
    # earlier proof has been promoted, so citing a later or an unpromoted
    # proof fails when it is checked. The theorems of other files are cited the
    # same way.
    titles = proof_titles(text) + list(imported_titles)
    cases = []
    for position, start in enumerate(positions):
        end = positions[position + 1] if position + 1 < len(positions) else len(lines)
        block = lines[start:end]
        header = _PROOF_HEADER_RE.match(block[0].strip())
        expected, description, body_start = _split_header_block(block)
        body = "\n".join(block[body_start:])
        try:
            entries, raw_lines = (
                pp.parse_proof_text(body, theorem_names=titles) if body.strip() else ([], [])
            )
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
                _stated_conclusion_from(
                    description,
                    header.group(1),
                    warn_unparseable=warn_unparseable_description,
                ),
                entries,
                raw_lines,
                title,
                error,
            )
        )
    return cases


def run_multi_proof_file(
    text,
    axioms=None,
    rules=None,
    declarations=None,
    *,
    imported=(),
    exported=None,
    warn_on_unpromoted=True,
    warn_unparseable_description=True,
    warn_duplicate_number=True,
):
    """Parse and validate all proof blocks, promoting titled proofs in order.

    Each result is `(number, expected_valid, ok, message, rule_crashed)`.
    `rule_crashed` is True exactly when `ok=False` came from some rule's
    own `applies()` raising (`CATEGORY_RULE_RAISED`; see `_is_rule_crash`)
    rather than a genuine semantic rejection -- so a caller can tell "the
    proof really is invalid" apart from "something in this checker
    crashed while looking at it" even on the cases where both happen to
    produce the same `ok` value.

    `imported` are theorems that other files proved: every proof here may
    cite them by title, from its first line on. `exported`, if given, is a
    list that receives the theorems this file promotes, for the files that
    cite it. Neither is checked here: see `check_file`.
    """
    imported = list(imported)
    cases = parse_multi_proof_file(
        text,
        warn_unparseable_description=warn_unparseable_description,
        imported_titles=[theorem.name for theorem in imported],
    )
    results = []
    promoted = []
    seen = set()
    for case in cases:
        if case.number in seen and warn_duplicate_number:
            print(f"Warning: proof number '{case.number}' appears more than once in this file")
        seen.add(case.number)
        if case.parse_error:
            results.append((case.number, case.expected_valid, False, case.parse_error, False))
            continue
        rule_crashed = False
        try:
            proof = pl.Proof(
                case.entries,
                axioms=axioms or [],
                rules=(rules or pl.default_rules()) + imported + promoted,
                declarations=declarations or [],
            )
            ok, err = proof.check_detailed()
            message = str(err) if err is not None else None
            rule_crashed = _is_rule_crash(err)
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
                    if warn_on_unpromoted:
                        print(f"Warning: proof #{case.number} ({case.title!r}) was not promoted: {exc}")
        except Exception as exc:
            ok, message, rule_crashed = False, f"parse/check error: {exc}", False
        results.append((case.number, case.expected_valid, ok, message, rule_crashed))
    if exported is not None:
        exported.extend(promoted)
    return results


def _is_rule_crash(err) -> bool:
    """True when a validation failure happened because some rule's own
    `applies()` raised (`ProofLogic.CATEGORY_RULE_RAISED`), not because
    the proof is genuinely semantically invalid.

    `ProofValidator` deliberately converts a raised exception into an
    ordinary `(False, ValidationError)` return -- see `_validate_rule`'s
    `except Exception as raised` -- specifically so one bad rule can't
    crash the whole check. The cost is that it never reaches an `except
    Exception:` clause anywhere upstream, so nothing flags it as an
    implementation bug unless something checks `.category` explicitly.
    An "invalid" fixture that only fails this way isn't actually
    exercising the rejection its filename/description claims; it just
    happens to also produce `ok=False`, for the wrong reason. Every
    caller that turns a `check_detailed()` result into a `ProofResult`
    ORs this into `implementation_error`, regardless of `expected_valid`.
    """
    return err is not None and getattr(err, "category", None) == pl.CATEGORY_RULE_RAISED


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
    ok, err = proof.check_detailed()
    return ok, (str(err) if err is not None else None), _is_rule_crash(err)


def _check_bare_proof_file(path: Path, text: Optional[str] = None) -> List[ProofResult]:
    expected_valid = "invalid" not in path.stem.lower()
    try:
        if text is None:
            text = path.read_text()
        entries, _ = pp.parse_proof_text(text)
        if not entries:
            return [ProofResult(path.name, "1", expected_valid, False, "file has no proof lines", True)]
        ok, message, rule_crashed = _validate_entries(entries)
        return [ProofResult(path.name, "1", expected_valid, ok, message, rule_crashed)]
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


def _check_multi_proof_file(
    path: Path,
    text: Optional[str] = None,
    checked: Optional["CheckedFiles"] = None,
    exported: Optional[list] = None,
    saved: Optional[sc.SavedChecks] = None,
) -> List[ProofResult]:
    try:
        if text is None:
            text = path.read_text()
        imported, problem = imported_theorems(path, text, {} if checked is None else checked, saved)
        if problem is not None:
            return [ProofResult(path.name, "?", True, False, problem, True)]
        results = run_multi_proof_file(
            text,
            axioms=BARE_PROOF_AXIOMS,
            rules=BARE_PROOF_RULES,
            declarations=BARE_PROOF_DECLARATIONS,
            imported=imported,
            exported=exported,
            warn_on_unpromoted=False,
            warn_unparseable_description=False,
            warn_duplicate_number=False,
        )
    except Exception as exc:
        return [ProofResult(path.name, "?", True, False, f"{type(exc).__name__}: {exc}", True)]

    converted = []
    for proof_id, expected_valid, ok, message, rule_crashed in results:
        implementation_error = rule_crashed or bool(
            message and (message.startswith("parse/check error:") or message.startswith("parse error:"))
        )
        converted.append(ProofResult(path.name, str(proof_id), expected_valid, ok, message, implementation_error))
    if not converted:
        converted.append(ProofResult(path.name, "?", True, False, "file contains no proof cases", True))
    return converted


# ---------------------------------------------------------------------------
# Using other files
# ---------------------------------------------------------------------------
#
# A multi-proof file may begin with `Use NAME.` lines, before its first `# N`
# header. NAME is a theory of the checker, which changes nothing (see
# THEORY_NAMES), or the name of a file next to this one without `.txt`. A
# proof of the file may then cite the theorems of that file by title, as it
# cites the ones its own earlier proofs promoted.
#
# The checker never checks a file because another file cites it: checking each
# file a file cites is the user's job. A run keeps what it has checked
# (`CheckedFile`), and a file may cite only files the run checked before it
# that passed, so a cited theorem always has a checked proof behind it, in the
# same environment. `Use` is not transitive: a file sees the theorems of the
# files it names and not of the files those use.


class CheckedFile(NamedTuple):
    """What a run keeps of a file it has checked: whether every proof in it
    behaved as expected, and the theorems it promoted."""
    passed: bool
    theorems: Tuple[pl.TheoremRule, ...] = ()


CheckedFiles = Dict[Path, CheckedFile]


def parse_uses(text: str) -> List[str]:
    """The names on the `Use ...` lines before the first proof header of a
    multi-proof file, in order, as written."""
    names = []
    for line in _COMMENT_RE.sub(" ", text).splitlines():
        stripped = line.strip()
        if _PROOF_HEADER_RE.match(stripped):
            break
        match = _USE_LINE_RE.match(stripped)
        if match:
            names.append(match.group(1).strip())
    return names


def _is_theory_name(name: str) -> bool:
    return re.sub(r"\s+", " ", name.strip().lower()) in THEORY_NAMES


def _resolve_use(path: Path, name: str) -> Tuple[Optional[Path], Optional[str]]:
    """What the `Use` line `name` of the file `path` stands for: `(None, None)`
    for a theory, `(file, None)` for a file next to `path`, or `(None, reason)`
    if the line is refused. The one place that decides it, for the theorems a
    file gets and for the key of its saved result."""
    file_name = f"{name}.txt"
    candidate = path.parent / file_name
    is_file = Path(name).name == name and candidate.is_file()
    if _is_theory_name(name):
        if is_file:
            return None, (f"Use {name}.: {name} is the name of a theory of the checker and of the file "
                          f"{file_name}; rename the file")
        return None, None
    if not is_file:
        return None, f"Use {name}.: there is no theory of that name and no file {file_name} next to this one"
    if candidate.resolve() == path.resolve():
        return None, f"Use {name}.: a file cannot use itself"
    return candidate, None


def imported_theorems(
    path: Path, text: str, checked: CheckedFiles, saved: Optional[sc.SavedChecks] = None,
) -> Tuple[Optional[List[pl.TheoremRule]], Optional[str]]:
    """The theorems that the `Use` lines of the file `path` (whose text is
    `text`) bring in, as `(theorems, None)`, or `(None, reason)` if it cannot
    have them.

    A file may cite the theorems of a file that `checked` has and that passed,
    and of no other: a file that was not checked, or did not pass, is refused,
    and nothing here ever checks it. With `saved`, a file that an earlier run
    checked, and that has not changed since (nor anything it uses), counts as
    checked. Two theorems whose titles are the same title, or the title of a
    proof of this file, would make a citation ambiguous, so that is refused as
    well (titles are the same up to case, hyphens and spacing, as in a
    citation)."""
    own = {pj._normalize(title) for title in proof_titles(text)}
    holders: Dict[str, str] = {}
    cited: set = set()
    theorems: List[pl.TheoremRule] = []
    for name in parse_uses(text):
        file_name = f"{name}.txt"
        candidate, problem = _resolve_use(path, name)
        if problem is not None:
            return None, problem
        if candidate is None:
            continue
        key = candidate.resolve()
        if key in cited:
            continue
        cited.add(key)
        record = checked.get(key)
        if record is None and saved is not None:
            record = _saved_record(candidate, saved)
            if record is not None:
                checked[key] = record
        if record is None:
            if saved is None:
                return None, (f"Use {name}.: {file_name} has not been checked in this run. A file is never "
                              f"checked because another cites it, so check {file_name} first")
            return None, (f"Use {name}.: {file_name} has not been checked in this run, and no saved result "
                          f"is for its present text. A file is never checked because another cites it, "
                          f"so check {file_name} first")
        if not record.passed:
            return None, (f"Use {name}.: {file_name} did not pass, so its theorems cannot be cited; "
                          f"fix {file_name} first")
        for theorem in record.theorems:
            title = pj._normalize(theorem.name)
            if title in holders:
                return None, (f"Use {name}.: the title {theorem.name!r} is also the title of a theorem of "
                              f"{holders[title]}, so citing it would be ambiguous")
            if title in own:
                return None, (f"Use {name}.: this file has a proof titled like the theorem {theorem.name!r} "
                              f"of {file_name}, so citing it would be ambiguous")
            holders[title] = file_name
            theorems.append(theorem)
    return theorems, None


def _dependency_order(paths: Sequence[Path], texts: Dict[Path, str]) -> Tuple[List[Path], Dict[Path, str]]:
    """`paths` with each file after the files of the list that it names on its
    `Use` lines (otherwise in the order given), and the files that take part in
    a cycle of `Use` lines, each with a description of the cycle, left out.

    This only puts the files a run was asked to check in an order in which a
    file can cite the ones before it. It never adds a file."""
    stems = {path.stem: path for path in paths}
    uses: Dict[Path, List[Path]] = {}
    for path in paths:
        names = parse_uses(texts[path]) if _looks_like_multi_proof(texts[path]) else []
        uses[path] = [stems[name] for name in names if name in stems and stems[name] != path]
    order: List[Path] = []
    cycles: Dict[Path, str] = {}
    done: set = set()

    def visit(path: Path, stack: List[Path]) -> None:
        if path in done:
            return
        if path in stack:
            loop = stack[stack.index(path):] + [path]
            description = " -> ".join(member.name for member in loop)
            for member in loop:
                cycles.setdefault(member, description)
            return
        stack.append(path)
        for used in uses[path]:
            visit(used, stack)
        stack.pop()
        done.add(path)
        if path not in cycles:
            order.append(path)

    for path in paths:
        visit(path, [])
    return order, cycles


# ---------------------------------------------------------------------------
# Saved results
# ---------------------------------------------------------------------------
#
# With a `SavedChecks` (source/SavedChecks.py) a file that passed is not
# checked again while nothing it depends on has changed. The key of a file is
# made of everything its check depends on: its text, the keys of the files its
# `Use` lines name (so a change below it changes its key), and, for a file of
# one proof, whether its name says the proof is invalid. A file whose `Use`
# lines are refused, or that is part of a cycle of them, has no key and is
# always checked. Finding a key only reads files: it never checks one.


def open_saved_results(directory=DEFAULT_SAVED_RESULTS) -> sc.SavedChecks:
    """Saved results in `directory`, for the rules this runner checks with."""
    return sc.SavedChecks(directory, BARE_PROOF_RULES)


def saved_key(
    path: Path, text: str, saved: sc.SavedChecks, memo: Optional[Dict[Path, Optional[str]]] = None,
) -> Optional[str]:
    """The key under which the result of checking the file `path` (whose text
    is `text`) is saved, or None if the file has none."""
    if memo is None:
        memo = {}
    where = path.resolve()
    if where in memo:
        return memo[where]
    memo[where] = None  # reached again while its own key is made: a cycle
    description: Dict[str, object] = {"text": sc.text_digest(text)}
    if _looks_like_multi_proof(text):
        description["kind"] = "proofs"
        uses = []
        for name in parse_uses(text):
            candidate, problem = _resolve_use(path, name)
            if problem is not None:
                return None
            if candidate is None:
                continue
            try:
                used_text = candidate.read_text()
            except (OSError, ValueError):
                return None
            used_key = saved_key(candidate, used_text, saved, memo)
            if used_key is None:
                return None
            uses.append([name, used_key])
        description["uses"] = uses
    else:
        description["kind"] = "bare"
        description["expected_valid"] = "invalid" not in path.stem.lower()
    key = saved.key(description)
    memo[where] = key
    return key


def _saved_record(path: Path, saved: sc.SavedChecks) -> Optional[CheckedFile]:
    """What an earlier run saved of the file `path`, if there is a saved result
    for its present text and for what it uses."""
    try:
        text = path.read_text()
    except (OSError, ValueError):
        return None
    key = saved_key(path, text, saved)
    found = saved.load(key) if key is not None else None
    return None if found is None else CheckedFile(True, found.theorems)


def check_file(
    path: Path,
    checked: Optional[CheckedFiles] = None,
    text: Optional[str] = None,
    saved: Optional[sc.SavedChecks] = None,
) -> List[ProofResult]:
    """Check one fixture file.

    `checked` is what the run has checked so far, keyed by resolved path: the
    file may cite the theorems of the files in it that its `Use` lines name
    (see `imported_theorems`), and what this check finds is added to it for
    the files after this one. Without it the file stands alone, and a `Use`
    line that names a file is refused. `text` is the file's source if the
    caller has read it already.

    With `saved`, a file that an earlier run checked and that passed, and that
    has not changed since (nor anything it uses, nor the checker), is not
    checked again: the results of that check are returned and its theorems
    kept for the files that cite it. A file that passes here is saved."""
    if text is None:
        text = path.read_text()
    if checked is None:
        checked = {}
    key = saved_key(path, text, saved) if saved is not None else None
    if key is not None:
        found = saved.load(key)
        if found is not None:
            checked[path.resolve()] = CheckedFile(True, found.theorems)
            saved.replayed.append(path.name)
            return [ProofResult(path.name, *entry) for entry in found.results]
    # The same source text is used to distinguish the container format and
    # then parse it. Pass it through rather than reopening every fixture file.
    exported: list = []
    if _looks_like_multi_proof(text):
        results = _check_multi_proof_file(path, text, checked, exported, saved)
    else:
        results = _check_bare_proof_file(path, text)
    passed = all(result.passed for result in results)
    checked[path.resolve()] = CheckedFile(passed, tuple(exported))
    if key is not None and passed:
        stored = saved.save(key, [tuple(result)[1:] for result in results], exported)
        (saved.stored if stored else saved.not_stored).append(path.name)
    return results


def check_files(paths: Iterable[Path], saved: Optional[sc.SavedChecks] = None) -> List[ProofResult]:
    """Check the files in the order given, each able to cite the theorems of
    the files before it that it names. A file that cites one the list does not
    have before it is refused: the user checks each file that is cited, unless
    an earlier run did, and `saved` has its results."""
    checked: CheckedFiles = {}
    results: List[ProofResult] = []
    for path in paths:
        results.extend(check_file(Path(path), checked, None, saved))
    return results


def run(directories: Sequence[str], saved: Optional[sc.SavedChecks] = None) -> List[ProofResult]:
    results: List[ProofResult] = []
    checked: CheckedFiles = {}
    for rel_dir in directories:
        directory = ROOT / rel_dir
        if directory.is_dir():
            paths = sorted(directory.glob("*.txt"))
            texts = {path: path.read_text() for path in paths}
            order, cycles = _dependency_order(paths, texts)
            for path in sorted(cycles):
                checked[path.resolve()] = CheckedFile(False)
                results.append(ProofResult(path.name, "?", True, False, f"Use cycle: {cycles[path]}", True))
            for path in order:
                results.extend(check_file(path, checked, texts[path], saved))
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
    p.add_argument(
        "--saved-results",
        nargs="?",
        const=str(DEFAULT_SAVED_RESULTS),
        metavar="DIR",
        help="do not check a file again that an earlier run checked, if nothing it depends on has changed; "
             "results are saved in DIR (default: .saved_results)",
    )
    return p.parse_args(argv)


def _print_saved_summary(saved: Optional[sc.SavedChecks]) -> None:
    if saved is None:
        return
    line = (f"saved results in {saved.directory}: {len(saved.replayed)} files not checked again, "
            f"{len(saved.stored)} checked and saved")
    if saved.not_stored:
        line += f", {len(saved.not_stored)} passed but could not be saved"
    print(line)


def main(argv=None):
    args = _parse_args(argv)
    saved = open_saved_results(args.saved_results) if args.saved_results else None
    if args.list_suites:
        _list_suites()
        return 0
    if args.suite:
        try:
            category, rel_dir = _resolve_suite(args.suite)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        failures = _print_selected_suite(rel_dir, run([rel_dir], saved), category == "enforced", args.verbose)
        _print_saved_summary(saved)
        return failures

    enforced_fails = 0
    enforced_results = []
    informational_results = []
    fixture_failures = []

    print("=== Enforced fixture corpus ===")
    for directory in ENFORCED_DIRS:
        suite_results = run([directory], saved)
        enforced_results.extend(suite_results)
        fixture_failures.extend(
            (directory, "enforced", result)
            for result in suite_results
            if not result.passed
        )
        enforced_fails += _print_suite_summary(directory, suite_results, True)

    print("\n=== Informational fixture corpus ===")
    for directory in INFORMATIONAL_DIRS:
        suite_results = run([directory], saved)
        informational_results.extend(suite_results)
        fixture_failures.extend(
            (directory, "informational", result)
            for result in suite_results
            if not result.passed
        )
        _print_suite_summary(directory, suite_results, False)

    print(
        f"\nTotal proofs checked: {len(enforced_results) + len(informational_results)} "
        f"(enforced: {sum(r.passed for r in enforced_results)}/{len(enforced_results)}, "
        f"informational: {sum(r.passed for r in informational_results)}/{len(informational_results)})"
    )
    _print_saved_summary(saved)
    print("\n=== Fixtures that did not behave as expected ===")
    if not fixture_failures:
        print("none")
    else:
        for directory, category, result in fixture_failures:
            message = result.message or "no diagnostic message"
            message = re.sub(r"\s*[\r\n]+\s*", " ", message).strip()
            print(
                f"FAIL {directory}/{result.file} #{result.proof_id} "
                f"({category}): {message}"
            )

    if enforced_fails:
        print(f"\n{enforced_fails} unexpected result(s) in the enforced fixture corpus.")
        return 1
    print("\nAll enforced proof fixtures behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
