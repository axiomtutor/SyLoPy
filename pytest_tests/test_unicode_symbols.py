"""J41 regression tests for mathematical symbols as input notation."""

from pathlib import Path

import pytest

from SyLoPy.source.Notation import rewrite_formula_symbols
from SyLoPy.source.ProofElaboration import TheoryEnvironment

from .support import mp, pl, pp, st
from .test_parse_oracle import load_cases


_ORACLE = Path(__file__).resolve().parents[1] / "parse_oracle" / "unicode_symbols.txt"
_CASES = load_cases(_ORACLE)


def _parse_surface(surface: str, context: str):
    if context == "line":
        return pp._ElaborationContext(pp.default_theory_environment()).parse_core_formula(surface)
    return pp.parse_formula(surface)


@pytest.mark.parametrize("case", _CASES, ids=[case["id"] for case in _CASES])
def test_symbolic_surface_has_the_word_form_reading(case):
    if case["expect"] == "REJECT":
        with pytest.raises((TypeError, ValueError)):
            _parse_surface(case["surface"], case["context"])
        return
    actual = _parse_surface(case["surface"], case["context"])
    expected = pp.parse_formula(case["expect"])
    assert pl._alpha_eq(actual, expected), (
        f"{case['id']}: {case['surface']!r}\n"
        f"parsed: {actual!r}\n"
        f"word form: {expected!r}\n"
        f"why: {case.get('why', '')}"
    )


def test_required_spacing_and_nesting_regressions_are_in_the_oracle():
    ids = {case["id"] for case in _CASES}
    assert {
        "unicode-no-spaces-membership",
        "unicode-no-spaces-connectives",
        "unicode-symbol-adjacent-to-word",
        "unicode-symbols-inside-quantifier",
    } <= ids



def test_notation_tables_with_conflicting_readings_cannot_be_combined():
    set_notation = TheoryEnvironment(
        name="set theory",
        notation_table={"×": "cross"},
    )
    arithmetic_notation = TheoryEnvironment(
        name="arithmetic",
        notation_table={"×": "times"},
    )

    with pytest.raises(ValueError, match=r"set theory.*arithmetic"):
        set_notation.extended(arithmetic_notation)


def test_identical_notation_readings_can_be_combined():
    first = TheoryEnvironment(name="first theory", notation_table={"×": "cross"})
    second = TheoryEnvironment(name="second theory", notation_table={"×": "cross"})

    combined = first.extended(second)

    assert combined.notation_table == {"×": "cross"}


def test_explicit_set_theory_environment_includes_base_and_set_notation():
    symbolic_connective = pp.parse_formula(
        "P ∧ Q", environment=st.SET_THEORY_ENVIRONMENT
    )
    word_connective = pp.parse_formula(
        "P and Q", environment=st.SET_THEORY_ENVIRONMENT
    )
    symbolic_membership = pp.parse_formula(
        "x∈A", environment=st.SET_THEORY_ENVIRONMENT
    )
    word_membership = pp.parse_formula(
        "x is in A", environment=st.SET_THEORY_ENVIRONMENT
    )

    assert pl._alpha_eq(symbolic_connective, word_connective)
    assert pl._alpha_eq(symbolic_membership, word_membership)


def test_symbol_rewriting_pads_tokens_and_preserves_bounded_quantifiers():
    notation = pp.default_theory_environment().notation_table

    assert rewrite_formula_symbols("x∈A", notation) == "x is in A"
    assert rewrite_formula_symbols("∀x∈A, P(x)", notation) == "forall x in A, P(x)"
    assert rewrite_formula_symbols("¬P(x)∧Q(x)", notation) == "not P(x) and Q(x)"


def test_unicode_fixture_proofs_match_their_word_form_rewrites():
    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "testSetTheory"
        / "unicode_symbols.txt"
    )
    source = fixture.read_text()
    environment = pp.default_theory_environment()
    word_source = rewrite_formula_symbols(source, environment.notation_table)

    symbol_cases = mp.parse_multi_proof_file(source)
    word_cases = mp.parse_multi_proof_file(word_source)

    assert len(symbol_cases) == len(word_cases) == 5
    assert [case.number for case in symbol_cases] == [
        case.number for case in word_cases
    ]
    for symbolic, words in zip(symbol_cases, word_cases):
        assert symbolic.stated_conclusion is not None
        assert words.stated_conclusion is not None
        assert symbolic.parse_error is None
        assert words.parse_error is None
        assert len(symbolic.entries) == len(words.entries)
        for symbolic_entry, word_entry in zip(symbolic.entries, words.entries):
            assert symbolic_entry[0] == word_entry[0]
            assert pl._alpha_eq(symbolic_entry[1], word_entry[1])
            assert symbolic_entry[2][0] == word_entry[2][0]

    results = mp.run_multi_proof_file(source)
    assert [(result[0], result[1], result[2]) for result in results] == [
        ("1", True, True),
        ("2", True, True),
        ("3", True, True),
        ("4", False, False),
        ("5", False, False),
    ]
    for case in symbol_cases[3:]:
        ok, error = pl.Proof(case.entries).check_detailed()
        assert not ok
        assert error is not None
        assert error.label == "3"
        assert error.category == pl.CATEGORY_RULE_MISMATCH
