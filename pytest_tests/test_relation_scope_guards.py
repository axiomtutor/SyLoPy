"""Regression guards for relation-property rules and lexical scopes.

These tests encode behavior that already works before support for relation
rules attached to local declarations is implemented. They must remain passing
after the scope-aware rule lookup is added.
"""

import pytest

from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


def test_root_relation_property_remains_available_in_a_subproof():
    ok, err = check("""
1. Let X be any set, R be a reflexive relation on X, b be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. R(b,b). (Relation Reflexivity from 1)
 2.3. P. (Reiteration from 2.1)
end subproof
""")
    assert ok, err


@pytest.mark.parametrize(
    ("first_property", "second_property", "expected_label"),
    [
        ("reflexive", "symmetric", "3.3"),
        ("symmetric", "reflexive", "2.3"),
    ],
)
def test_sibling_relation_declarations_do_not_share_properties(
    first_property, second_property, expected_label
):
    # The reflexivity rule is intentionally attempted only in the sibling
    # whose R is merely symmetric. Swapping sibling order prevents a global
    # relation-name table from accidentally borrowing the other sibling's
    # metadata.
    text = f"""
1. Let X be any set, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a {first_property} relation on X. (Declaration)
 2.3. {"R(a,a). (Relation Reflexivity from 1)" if first_property == "symmetric" else "P. (Reiteration from 2.1)"}
end subproof
3. P -> P. (Conditional Introduction from subproof below)
begin subproof
 3.1. P. (Assumption)
 3.2. Let R be a {second_property} relation on X. (Declaration)
 3.3. {"R(a,a). (Relation Reflexivity from 1)" if second_property == "symmetric" else "P. (Reiteration from 3.1)"}
end subproof
"""
    ok, err = check(text)

    assert not ok
    assert err is not None
    assert err.label == expected_label
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert "'RelationReflexivity' does not justify" in err.detail


def test_root_relation_property_remains_available_two_subproof_levels_down():
    ok, err = check("""
1. Let X be any set, R be a reflexive relation on X, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. P -> P. (Conditional Introduction from subproof below)
begin subproof
  2.2.1. P. (Assumption)
  2.2.2. R(a,a). (Relation Reflexivity from 1)
  2.2.3. P. (Reiteration from 2.2.1)
end subproof
 2.3. P. (Reiteration from 2.1)
end subproof
""")
    assert ok, err
