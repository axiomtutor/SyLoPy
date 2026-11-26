"""Full-grid tests for the set-membership wording table (J37).

Expected formulas below are built directly from the core AST constructors. They
do not use the set-theory phrase parser to calculate their expected readings.
"""

import pytest

from .support import atom, c, fl, fn, pl, pp, st, v


def _in(element, set_term):
    return atom("In", element, set_term)


def _not_in(element, set_term):
    return fl.Not(_in(element, set_term))


def _subset(left, right):
    return fl.ForAll(
        "u",
        fl.Implies(_in(v("u"), left), _in(v("u"), right)),
    )


# Include bare names, each set operation, power sets, the new English
# operation terms, parenthesized nesting, and ordinary function applications.
SET_TERMS = [
    ("A", c("A")),
    ("A union B", fn("Union", c("A"), c("B"))),
    ("A intersection B", fn("Intersection", c("A"), c("B"))),
    ("A cross B", fn("CartesianProduct", c("A"), c("B"))),
    ("the power set of A", fn("PowerSet", c("A"))),
    ("the empty set", st.EMPTY_SET),
    ("the union of A and B", fn("Union", c("A"), c("B"))),
    ("the intersection of A and B", fn("Intersection", c("A"), c("B"))),
    ("the union of (A union B) and C",
     fn("Union", fn("Union", c("A"), c("B")), c("C"))),
    ("the intersection of A and (B union C)",
     fn("Intersection", c("A"), fn("Union", c("B"), c("C")))),
    ("(A union B) intersection C",
     fn("Intersection", fn("Union", c("A"), c("B")), c("C"))),
    ("f(A union B)", fn("f", fn("Union", c("A"), c("B")))),
    ("Union(A, B)", fn("Union", c("A"), c("B"))),
]

ELEMENT_TERMS = [
    ("x", v("x")),
    ("f(a)", fn("f", c("a"))),
    ("A union B", fn("Union", c("A"), c("B"))),
    ("(A intersection B)", fn("Intersection", c("A"), c("B"))),
]

# (wording, polarity, operand order). The order is semantic: "T contains x"
# puts the set first, whereas all the other forms put the element first.
MEMBERSHIP_PHRASES = [
    ("is in", True, "element-set"),
    ("is not in", False, "element-set"),
    ("belongs to", True, "element-set"),
    ("does not belong to", False, "element-set"),
    ("is an element of", True, "element-set"),
    ("is not an element of", False, "element-set"),
    ("is a member of", True, "element-set"),
    ("is not a member of", False, "element-set"),
    ("contains", True, "set-element"),
    ("does not contain", False, "set-element"),
]


def _parse_line(surface):
    return pp._ElaborationContext(st.SET_THEORY_ENVIRONMENT).parse_core_formula(surface)


def _assert_formula(surface, expected, *, nested=False):
    actual = pp.parse_formula(surface) if nested else _parse_line(surface)
    assert pl._alpha_eq(actual, expected), (
        f"{surface!r}\nparsed: {actual!r}\nexpected: {expected!r}"
    )


def test_every_membership_wording_uses_the_membership_atom_for_every_set_term():
    """A change from one table row to a Boolean expansion must fail this test."""
    for wording, positive, order in MEMBERSHIP_PHRASES:
        for element_text, element in ELEMENT_TERMS:
            for set_text, set_term in SET_TERMS:
                if order == "element-set":
                    surface = f"{element_text} {wording} {set_text}"
                else:
                    surface = f"{set_text} {wording} {element_text}"
                expected = _in(element, set_term) if positive else _not_in(element, set_term)
                _assert_formula(surface, expected)


def test_membership_phrases_compose_with_connectives_around_english_operation_terms():
    surface = (
        "P(x) and x belongs to the union of (A union B) and C "
        "and y is not an element of the intersection of A and B"
    )
    expected = fl.And(
        atom("P", v("x")),
        _in(v("x"), fn("Union", fn("Union", c("A"), c("B")), c("C"))),
        _not_in(v("y"), fn("Intersection", c("A"), c("B"))),
    )
    _assert_formula(surface, expected, nested=True)


@pytest.mark.parametrize(
    "surface,expected",
    [
        ("A set-in B", _subset(c("A"), c("B"))),
        ("A set-contains B", _subset(c("B"), c("A"))),
        ("A not set-in B", fl.Not(_subset(c("A"), c("B")))),
        ("A not set-contains B", fl.Not(_subset(c("B"), c("A")))),
    ],
)
def test_set_in_and_set_contains_are_subset_phrases(surface, expected):
    _assert_formula(surface, expected)


@pytest.mark.parametrize(
    "surface,expected",
    [
        ("A is the union of (B union C) and D",
         fl.Equals(c("A"), fn("Union", fn("Union", c("B"), c("C")), c("D")))),
        ("(A intersection B) is the intersection of C and (D union E)",
         fl.Equals(
             fn("Intersection", c("A"), c("B")),
             fn("Intersection", c("C"), fn("Union", c("D"), c("E"))),
         )),
    ],
)
def test_set_identity_phrases_define_operation_terms_by_equality(surface, expected):
    _assert_formula(surface, expected)


def test_empty_nonempty_and_disjointness_phrases_keep_their_existing_meanings():
    _assert_formula(
        "A and B are disjoint",
        fl.ForAll(
            "u",
            fl.Not(fl.And(_in(v("u"), c("A")), _in(v("u"), c("B")))),
        ),
    )
    _assert_formula(
        "the union of A and B is empty",
        fl.ForAll(
            "u",
            fl.Not(fl.Or(_in(v("u"), c("A")), _in(v("u"), c("B")))),
        ),
    )
    _assert_formula(
        "the intersection of A and B is nonempty",
        fl.Exists(
            "u",
            fl.And(_in(v("u"), c("A")), _in(v("u"), c("B"))),
        ),
    )


@pytest.mark.parametrize("surface", ["x lies in A", "A has x as an element"])
def test_unapproved_membership_phrases_remain_refused(surface):
    with pytest.raises(Exception):
        _parse_line(surface)
