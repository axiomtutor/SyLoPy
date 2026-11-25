import pytest

from .support import st


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
