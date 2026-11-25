import pytest

from .support import st, tl


@pytest.mark.parametrize(
    "term",
    [
        "A union B intersection C",
        "A intersection B union C",
        "A cross B cross C",
    ],
)
def test_ambiguous_unparenthesized_operation_chains_require_parentheses(term):
    with pytest.raises(ValueError, match="parenthes"):
        st.try_parse_set_term(term)


@pytest.mark.parametrize(
    ("surface", "symbol"),
    [
        ("A UNION B", "Union"),
        ("A InTeRsEcTiOn B", "Intersection"),
        ("A CrOsS B", "CartesianProduct"),
    ],
)
def test_set_operation_words_are_case_insensitive(surface, symbol):
    expected = tl.FunctionTerm(
        symbol,
        [tl.ConstantTerm("A", "A"), tl.ConstantTerm("B", "B")],
    )
    assert st.try_parse_set_term(surface) == expected


def test_non_ascii_identifier_characters_are_rejected_without_crashing():
    assert st.try_parse_set_term("Å union B") is None


def test_one_operator_table_drives_infix_recognition_and_symbol_mapping(monkeypatch):
    # J38 should be able to add an infix operator by adding one table entry.
    st._try_parse_set_term_cached.cache_clear()
    monkeypatch.setitem(st._SET_OPERATION_SYMBOLS, "difference", "Difference")
    try:
        expected = tl.FunctionTerm(
            "Difference",
            [tl.ConstantTerm("A", "A"), tl.ConstantTerm("B", "B")],
        )
        assert st.try_parse_set_term("A difference B") == expected
        assert st.try_parse_set_term("difference") is None
    finally:
        st._try_parse_set_term_cached.cache_clear()
