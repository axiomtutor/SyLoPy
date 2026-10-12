"""Pending regressions for scope-aware relation declarations.

The kernel task is owned by Claude. These tests specify the accepted semantics
without patching ProofLogic.py or ProofJustification.py. Until the kernel lookup
uses the declaration visible at the current proof line, each test recognizes
only the specific, current-scope rule mismatch as an expected failure. Other
failures (including one at the wrong proof line) remain ordinary test failures.
"""

import pytest

from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


_SCOPE_FIX_REASON = (
    "pending Claude's kernel fix for relation declarations in active proof scopes"
)


def xfail_if_current_scope_bug(ok, err, label, rule_name):
    """Xfail only when this exact rule fails at the expected in-scope line."""
    if (
        not ok
        and err is not None
        and err.label == label
        and err.category == pl.CATEGORY_RULE_MISMATCH
        and f"'{rule_name}' does not justify" in err.detail
    ):
        pytest.xfail(_SCOPE_FIX_REASON)


def test_relation_declared_inside_subproof_works_there_but_does_not_escape():
    ok, err = check("""
1. Let X be any set, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a reflexive relation on X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 1)
 2.4. P. (Reiteration from 2.1)
end subproof
3. R(a,a). (Premise)
""")

    # Currently the local rule application fails because its declaration was
    # omitted from the proof-wide rule metadata. Only that exact mismatch is
    # expected to fail temporarily; after the fix, line 3 should be the error.
    xfail_if_current_scope_bug(ok, err, "2.3", "RelationReflexivity")
    assert not ok
    assert err is not None
    assert err.label == "3"
    assert err.category == pl.CATEGORY_UNDECLARED_SYMBOL


def test_relation_declared_in_parent_subproof_is_visible_in_nested_subproof():
    ok, err = check("""
1. Let X be any set, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a reflexive relation on X. (Declaration)
 2.3. P -> P. (Conditional Introduction from subproof below)
begin subproof
  2.3.1. P. (Assumption)
  2.3.2. R(a,a). (Relation Reflexivity from 1)
  2.3.3. P. (Reiteration from 2.3.1)
end subproof
 2.4. P. (Reiteration from 2.1)
end subproof
""")
    xfail_if_current_scope_bug(ok, err, "2.3.2", "RelationReflexivity")
    assert ok, err


def test_sibling_relation_declarations_do_not_transfer_properties():
    ok, err = check("""
1. Let X be any set, a be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a reflexive relation on X. (Declaration)
 2.3. R(a,a). (Relation Reflexivity from 1)
 2.4. P. (Reiteration from 2.1)
end subproof
3. P -> P. (Conditional Introduction from subproof below)
begin subproof
 3.1. P. (Assumption)
 3.2. Let R be a symmetric relation on X. (Declaration)
 3.3. R(a,a). (Relation Reflexivity from 1)
 3.4. P. (Reiteration from 3.1)
end subproof
""")

    # The first subproof must succeed, and the second must be rejected for
    # lacking the reflexivity property. An error at 2.3 exposes a missing
    # local-declaration implementation; an error elsewhere exposes a
    # different failure rather than the sibling-isolation contract.
    xfail_if_current_scope_bug(ok, err, "2.3", "RelationReflexivity")
    assert not ok
    assert err is not None
    assert err.label == "3.3"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert "'RelationReflexivity' does not justify" in err.detail


def test_local_transitivity_rule_works_from_two_premises_in_nested_subproof():
    ok, err = check("""
1. Let X be any set, a, b, c be in X, P be a closed formula. (Declaration)
2. P -> P. (Conditional Introduction from subproof below)
begin subproof
 2.1. P. (Assumption)
 2.2. Let R be a transitive relation on X. (Declaration)
 2.3. R(a,b). (Premise)
 2.4. R(b,c). (Premise)
 2.5. R(a,c). (Relation Transitivity from 2.3, 2.4)
 2.6. P. (Reiteration from 2.1)
end subproof
""")
    xfail_if_current_scope_bug(ok, err, "2.5", "RelationTransitivity")
    assert ok, err
