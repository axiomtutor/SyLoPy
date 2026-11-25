"""J44 regression tests: declaration-vs-formula is decided by the active parsers.

The phrase parser tests deliberately go through parse_proof_text, not the
lower-level formula parser: the defect is in the proof-line declaration
dispatch, before formula parsing would ordinarily begin.
"""

from pathlib import Path

import pytest

from SyLoPy.source.ProofElaboration import TheoryEnvironment

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


@pytest.mark.parametrize(
    "phrase, expected",
    [
        ("A and B are equal", "A = B"),
        ("A and B are not equal", "¬A = B"),
        ("A and B are different", "¬A = B"),
        ("A and B are distinct", "¬A = B"),
    ],
)
def test_equality_formula_can_follow_a_compound_let_declaration(phrase, expected):
    entries, _ = pp.parse_proof_text(
        "1. Let A and B be sets, and " + phrase + ". (Declaration)\n"
    )

    label, formula, justification = entries[0]
    assert label == "1"
    assert repr(formula) == expected
    assert justification[0] == "premise"
    assert [declaration.name for declaration in justification[1]] == ["A", "B"]

@pytest.mark.parametrize("descriptor", ["sets", "integers"])
def test_unrecognized_descriptors_remain_declarations(descriptor):
    entries, _ = pp.parse_proof_text(
        f"1. A and B are {descriptor}. (Declaration)\n"
    )

    _label, formula, justification = entries[0]
    assert formula is None
    assert justification[0] == "declare"
    assert [(d.name, d.kind, d.type_name) for d in justification[1]] == [
        ("A", pl.DeclarationKind.OBJECT, descriptor),
        ("B", pl.DeclarationKind.OBJECT, descriptor),
    ]



def test_base_equality_phrase_is_available_in_an_explicit_theory_environment():
    environment = TheoryEnvironment(name="bare test theory")
    entries, _ = pp.parse_proof_text(
        "1. Let A and B be sets, and A and B are equal. (Declaration)\n",
        environment=environment,
    )

    _label, formula, justification = entries[0]
    assert repr(formula) == "A = B"
    assert justification[0] == "premise"
    assert [declaration.name for declaration in justification[1]] == ["A", "B"]


def test_relation_descriptor_remains_a_declaration():
    entries, _ = pp.parse_proof_text(
        "1. Let X be a set. (Declaration)\\n"
        "2. A and B are relations on X. (Declaration)\\n"
    )

    _label, formula, justification = entries[1]
    assert formula is None
    assert justification[0] == "declare"
    assert [declaration.name for declaration in justification[1]] == ["A", "B"]


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



@pytest.mark.parametrize(
    "phrase",
    [
        "A and B are disjoint",
        "A and B are not disjoint",
        "A is disjoint from B",
    ],
)
def test_existing_set_theory_disjointness_phrases_remain_premises(phrase):
    entries, _ = pp.parse_proof_text(
        "1. Let A, B be sets. (Declaration)\n"
        f"2. {phrase}. (Premise)\n"
    )

    assert entries[1][2] == ("premise",)
    assert entries[1][1] is not None


def test_premises_that_are_formulas_fixture_has_grounded_valid_and_invalid_proofs():
    project = Path(__file__).resolve().parents[1]
    source = (
        project / "tests" / "testSetTheory" / "premises_that_are_formulas.txt"
    ).read_text()
    cases = mp.parse_multi_proof_file(source)

    assert [case.number for case in cases] == [str(number) for number in range(1, 11)]
    assert all(case.stated_conclusion is not None for case in cases)
    assert all(case.parse_error is None for case in cases)

    results = mp.run_multi_proof_file(source)
    assert [result[0] for result in results] == [case.number for case in cases]
    assert all(result[1] == result[2] and not result[4] for result in results), [
        result for result in results if result[1] != result[2] or result[4]
    ]

    for case in cases:
        if case.expected_valid:
            continue
        ok, error = pl.Proof(case.entries).check_detailed()
        assert not ok
        assert error is not None
        if case.number == "10":
            assert error.label == "1"
            assert error.category == pl.CATEGORY_UNDECLARED_SYMBOL
            assert error.detail == "constant 'A' is used but has not been declared"
        else:
            assert error.label == "3"
            assert error.category == pl.CATEGORY_RULE_MISMATCH
