"""Ensure the proof-format reference covers built-in and theory rule names."""

import re
from pathlib import Path

from SyLoPy.source.ProofJustification import _ALIASES


_DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "PROOF_FILE_FORMAT.md"


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("-", " ")).strip()


def _document_text() -> str:
    return _normalized(_DOC_PATH.read_text(encoding="utf-8"))


def test_document_names_every_registered_builtin_rule() -> None:
    # _ALIASES contains all accepted spellings. Keep the first registered
    # spelling for each factory as the one canonical spelling documentation
    # promises to list.
    canonical_by_factory = {}
    for spelling, factory in _ALIASES.items():
        canonical_by_factory.setdefault(factory, spelling)

    document = _document_text()
    missing = sorted(
        spelling
        for spelling in canonical_by_factory.values()
        if _normalized(spelling) not in document
    )
    assert not missing, f"PROOF_FILE_FORMAT.md omits canonical built-in rule names: {missing}"


def test_document_names_every_theory_placeholder_spelling() -> None:
    # These names are the literal keys in ProofJustification._rule's
    # placeholders dict. Keep the list explicit so that a changed or added
    # resolver spelling requires a deliberate documentation/test update.
    placeholder_spellings = (
        "relation reflexivity",
        "relation irreflexivity",
        "relation symmetry",
        "relation antisymmetry",
        "relation asymmetry",
        "relation transitivity",
        "relation totality",
        "totality",
        "quotient defining property",
        "quotient definition",
        "quotient uniqueness",
        "set equality",
        "induction",
        "empty set property",
        "set property",
        "axiom of separation",
        "separation schema",
        "axiom schema of separation",
        "axiom of replacement",
        "replacement schema",
        "axiom schema of replacement",
        "axiom of pairing",
        "axiom of union",
        "axiom of power set",
        "power set axiom",
        "axiom of infinity",
        "wlog",
        "without loss of generality",
        "mutatis mutandis",
    )
    document = _document_text()
    missing = [
        spelling for spelling in placeholder_spellings
        if _normalized(spelling) not in document
    ]
    assert not missing, f"PROOF_FILE_FORMAT.md omits theory placeholder spellings: {missing}"
