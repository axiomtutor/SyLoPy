"""J44 regression tests: declaration-vs-formula is decided by the active parsers.

The phrase parser tests deliberately go through parse_proof_text, not the
lower-level formula parser: the defect is in the proof-line declaration
dispatch, before formula parsing would ordinarily begin.
"""

import pytest

from .support import mp, pl, pp


@pytest.mark.parametrize(
    "phrase, symbolic",
    [
        ("A and B are equal", "A = B"),
        ("A and B are not equal", "not (A = B)"),
        ("A and B are different", "not (A = B)"),
        ("A and B are distinct", "not (A = B)"),
    ],
)
def test_are_equality_phrases_are_premises_not_declarations(phrase, symbolic):
    entries, _ = pp.parse_proof_text(
        "1. Let A, B be sets. (Declaration)\n"
        f"2. {phrase}. (Premise)\n"
    )
    expected, _ = pp.parse_proof_text(
        "1. Let A, B be sets. (Declaration)\n"
        f"2. {symbolic}. (Premise)\n"
    )

    actual_line = entries[1]
    expected_line = expected[1]
    assert actual_line[2] == ("premise",)
    assert repr(actual_line[1]) == repr(expected_line[1])
    assert repr(actual_line[1]) == (
        "A = B" if phrase.endswith("equal") and "not equal" not in phrase
        else "¬A = B"
    )


def test_equality_formula_can_follow_a_compound_let_declaration():
    entries, _ = pp.parse_proof_text(
        "1. Let A and B be sets, and A and B are equal. (Declaration)\n"
    )

    label, formula, justification = entries[0]
    assert label == "1"
    assert repr(formula) == "A = B"
    assert justification[0] == "premise"
    assert [declaration.name for declaration in justification[1]] == ["A", "B"]


def test_are_unknown_descriptor_remains_a_declaration():
    entries, _ = pp.parse_proof_text(
        "1. A and B are integers. (Declaration)\n"
    )

    _label, formula, justification = entries[0]
    assert formula is None
    assert justification[0] == "declare"
    assert [(d.name, d.kind, d.type_name) for d in justification[1]] == [
        ("A", pl.DeclarationKind.OBJECT, "integers"),
        ("B", pl.DeclarationKind.OBJECT, "integers"),
    ]


def test_undeclared_equality_phrase_fails_at_its_own_line_as_a_formula():
    entries, _ = pp.parse_proof_text("1. A and B are equal. (Premise)\n")
    ok, error = pl.Proof(entries).check_detailed()

    assert not ok
    assert error is not None
    assert error.label == "1"
    assert error.category == pl.CATEGORY_UNDECLARED_SYMBOL
    assert error.detail == "constant 'A' is used but has not been declared"


def test_multi_proof_runner_reports_undeclared_equality_at_line_one():
    source = """# 1: An equality premise does not declare its names
## Invalid: the names A and B have not been declared
### then A = B.

1. A and B are equal. (Premise)
2. A = B. (Reiteration from 1)
"""
    [result] = mp.run_multi_proof_file(source)

    assert result[0] == "1"
    assert result[1] is False
    assert result[2] is False
    assert "Line 1" in result[3]
    assert "constant 'A' is used but has not been declared" in result[3]
    assert "cites ['1']" not in result[3]


@pytest.mark.parametrize(
    "text",
    [
        "1. A is equal to B. (Premise)\n",
        "1. A equals B. (Premise)\n",
    ],
)
def test_unapproved_equality_wordings_remain_refused(text):
    with pytest.raises(pp.ElaborationError, match="Unrecognized formula syntax"):
        pp.parse_proof_text(text)
