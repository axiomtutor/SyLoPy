#!/usr/bin/env python3
"""Validate the project's proof fixture corpora."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

# This file lives in <repository>/source.  Put the repository's parent on
# sys.path so that the local SyLoPy package is imported, rather than any
# unrelated checkout or installed copy of the package.
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


def _check_bare_proof_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
    expected_valid = "invalid" not in path.stem.lower()
    try:
        entries, _ = pp.parse_proof_text(text)
        if not entries:
            return [ProofResult(path.name, "1", expected_valid, False, "file has no proof lines")]
        proof = pl.Proof(
            entries,
            axioms=BARE_PROOF_AXIOMS,
            rules=BARE_PROOF_RULES,
            declarations=BARE_PROOF_DECLARATIONS,
        )
        ok = proof.validate()
        return [ProofResult(path.name, "1", expected_valid, ok, None)]
    except Exception as exc:
        return [ProofResult(path.name, "1", expected_valid, False, f"{type(exc).__name__}: {exc}")]


def _check_multi_proof_file(path: Path) -> List[ProofResult]:
    text = path.read_text()
    results: List[ProofResult] = []
    try:
        proofs = mp.parse_multiproof_text(text)
    except Exception as exc:
        return [ProofResult(path.name, "?", True, False, f"{type(exc).__name__}: {exc}")]

    for proof_id, proof_text, expected_valid in proofs:
        try:
            entries, _ = pp.parse_proof_text(proof_text)
            proof = pl.Proof(
                entries,
                axioms=BARE_PROOF_AXIOMS,
                rules=BARE_PROOF_RULES,
                declarations=BARE_PROOF_DECLARATIONS,
            )
            ok = proof.validate()
            results.append(ProofResult(path.name, str(proof_id), expected_valid, ok, None))
        except Exception as exc:
            results.append(ProofResult(path.name, str(proof_id), expected_valid, False, f"{type(exc).__name__}: {exc}"))
    return results
