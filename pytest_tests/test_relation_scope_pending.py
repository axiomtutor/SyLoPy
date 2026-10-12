"""Pending regressions for scope-aware relation declarations.

The kernel task is owned by Claude. These tests specify the accepted semantics
without patching ProofLogic.py or ProofJustification.py. Until the kernel lookup
uses the declaration visible at the current proof line, the positive cases are
expected failures. The strict xfails deliberately become suite failures (XPASS)
once the behavior works, reminding us to remove the markers and make the cases
ordinary required regressions.
"""

import pytest

from .support import pp, pl


def check(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries).check_detailed()


_SCOPE_FIX_REASON = (
    "pending Claude's kernel fix for relation declarations in active proof scopes"
)


@pytest.mark.xfail(strict=True, reason=_SCOPE_FIX_REASON)
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

    # The local rule application must succeed; only the later out-of-scope use
    # should fail. Checking the exact label distinguishes the two behaviors.
    assert not ok
    assert err is not None
    assert err.label == "3"
    assert err.category == pl.CATEGORY_UNDECLARED_SYMBOL


@pytest.mark.xfail(strict=True, reason=_SCOPE_FIX_REASON)
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
    assert ok, err


@pytest.mark.xfail(strict=True, reason=_SCOPE_FIX_REASON)
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
    assert not ok
    assert err is not None
    assert err.label == "3.3"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert "'RelationReflexivity' does not justify" in err.detail


@pytest.mark.xfail(strict=True, reason=_SCOPE_FIX_REASON)
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
    assert ok, err
