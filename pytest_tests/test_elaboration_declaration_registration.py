"""Every declaration emitted by elaboration is recorded in ProofContext.

The compound-declaration elaborator registers declarations incrementally so
later clauses on the same line can depend on earlier ones. Other elaboration
paths return the same core declaration payload but used to omit the lexical
context update. These tests cover the existence-witness and declaration-like
premise paths through a subsequent relation declaration, plus duplicate-name
rejection at the surface line that introduces the duplicate.
"""

import pytest

from .support import pl, pp


def _parse_and_check(text):
    entries, _ = pp.parse_proof_text(text)
    return entries, pl.Proof(entries).check_detailed()


def test_existence_witness_is_visible_to_a_later_carrier_declaration():
    entries, (ok, error) = _parse_and_check(
        "1. exists x, x = x. (Premise)\n"
        "2. Let X be such a set. (Existence from 1)\n"
        "3. Let R be a relation on X. (Declaration)\n"
    )

    assert ok, error
    witness_declarations = entries[1][2][1]
    relation_declarations = entries[2][2][1]
    assert [declaration.name for declaration in witness_declarations] == ["X"]
    assert [declaration.name for declaration in relation_declarations] == ["R"]
    assert dict(relation_declarations[0].metadata)["carrier"] == "X"


def test_such_that_premise_declaration_is_visible_to_a_later_carrier_declaration():
    entries, (ok, error) = _parse_and_check(
        "1. Let X be any set such that: X = X. (Premise)\n"
        "2. Let R be a relation on X. (Declaration)\n"
    )

    assert ok, error
    premise_declarations = entries[0][2][1]
    relation_declarations = entries[1][2][1]
    assert [declaration.name for declaration in premise_declarations] == ["X"]
    assert [declaration.name for declaration in relation_declarations] == ["R"]
    assert dict(relation_declarations[0].metadata)["carrier"] == "X"


def test_existence_witness_cannot_duplicate_a_visible_declaration():
    text = (
        "1. Let X be any set. (Declaration)\n"
        "2. exists x, x = x. (Premise)\n"
        "3. Let X be such a set. (Existence from 2)\n"
    )

    with pytest.raises(
        pp.ElaborationError,
        match=r"Line 3: symbol 'X' is already declared",
    ):
        pp.parse_proof_text(text)


def test_compound_declaration_remains_registered_once():
    entries, (ok, error) = _parse_and_check(
        "1. Let X be any set, R be a relation on X. (Declaration)\n"
    )

    assert ok, error
    declarations = entries[0][2][1]
    assert [declaration.name for declaration in declarations] == ["X", "R"]
    assert dict(declarations[1].metadata)["carrier"] == "X"
