"""Soundness regressions for equality-case WLOG region replay."""

from .support import pl, pp, tl


def _check(text):
    entries, _ = pp.parse_proof_text(text)
    return entries, pl.Proof(entries).check_detailed()


def _two_case_proof(*, include_second_case=True, conclusion="Q"):
    lines = [
        "1. Let a be any object. (Declaration)",
        "2. Let x be any object. (Declaration)",
        "3. Let y be any object. (Declaration)",
        "4. Let P be a predicate. (Declaration)",
        "5. Let Q be a closed formula. (Declaration)",
    ]
    px_label = len(lines) + 1
    lines.append(f"{px_label}. P(x). (Premise)")
    py_label = None
    if include_second_case:
        py_label = len(lines) + 1
        lines.append(f"{py_label}. P(y). (Premise)")
    px_implies_q_label = len(lines) + 1
    lines.append(f"{px_implies_q_label}. P(x) -> Q. (Premise)")
    if include_second_case:
        py_implies_q_label = len(lines) + 1
        lines.append(f"{py_implies_q_label}. P(y) -> Q. (Premise)")
    disjunction_label = len(lines) + 1
    wlog_label = disjunction_label + 1
    result_label = wlog_label + 1
    lines.extend([
        f"{disjunction_label}. a = x or a = y. (Premise)",
        f"{wlog_label}. a = x. (WLOG from {disjunction_label})",
    ])
    if conclusion == "Q":
        lines.append(
            f"{result_label}. Q. (Modus Ponens from {px_label}, {px_implies_q_label})"
        )
    else:
        lines.append(f"{result_label}. {conclusion}. (Reiteration from {px_label})")
    return "\n".join(lines), wlog_label, result_label


def test_two_case_wlog_replays_suffix_and_remaps_outer_citations():
    text, _wlog_label, result_label = _two_case_proof()
    entries, (ok, err) = _check(text)
    assert ok, err
    # The original chosen-case source remains unchanged after replay.
    assert entries[-1][2][2] == ["6", "8"]
    assert entries[-1][1] is not None


def test_three_case_wlog_checks_every_alternative():
    text = """1. Let a be any object. (Declaration)
2. Let x be any object. (Declaration)
3. Let y be any object. (Declaration)
4. Let z be any object. (Declaration)
5. Let P be a predicate. (Declaration)
6. Let Q be a closed formula. (Declaration)
7. P(x). (Premise)
8. P(y). (Premise)
9. P(z). (Premise)
10. P(x) -> Q. (Premise)
11. P(y) -> Q. (Premise)
12. P(z) -> Q. (Premise)
13. a = x or a = y or a = z. (Premise)
14. a = x. (WLOG from 13)
15. Q. (Modus Ponens from 7, 10)
"""
    _entries, (ok, err) = _check(text)
    assert ok, err


def test_wlog_fails_when_a_transformed_outer_citation_has_no_counterpart():
    text, wlog_label, result_label = _two_case_proof(include_second_case=False)
    _entries, (ok, err) = _check(text)
    assert not ok
    assert err is not None
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.label == str(result_label)
    assert "no visible counterpart" in err.detail
    assert wlog_label < result_label


def test_wlog_rejects_a_case_specific_final_conclusion():
    text, wlog_label, _result_label = _two_case_proof(conclusion="P(x)")
    _entries, (ok, err) = _check(text)
    assert not ok
    assert err is not None
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.label == str(wlog_label)
    assert "same final result" in err.detail


def test_wlog_rejects_non_disjunct_assertions():
    text = """1. Let a be any object. (Declaration)
2. Let x be any object. (Declaration)
3. Let y be any object. (Declaration)
4. Let Q be a closed formula. (Declaration)
5. a = x or a = y. (Premise)
6. Q. (WLOG from 5)
"""
    _entries, (ok, err) = _check(text)
    assert not ok
    assert err is not None
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.label == "6"
    assert "exactly one disjunct" in err.detail


def test_wlog_replay_transforms_structured_declaration_metadata():
    text = """
1. Let a be any object. (Declaration)
2. Let X be any set. (Declaration)
3. Let y be any object. (Declaration)
4. Let Q be a closed formula. (Declaration)
5. In(X, X). (Premise)
6. In(y, y). (Premise)
7. Q. (Premise)
8. a = X or a = y. (Premise)
9. a = X. (WLOG from 8)
10. Let R be a reflexive relation on X. (Declaration)
11. R(X, X). (Relation Reflexivity from 5)
12. Q. (Reiteration from 7)
"""
    entries, (ok, err) = _check(text)
    assert ok, err
    # Replay uses carrier y and the already-visible In(y,y) counterpart.
    # The source declaration itself must remain unchanged.
    relation = next(
        declaration
        for entry in entries
        for declaration in (
            entry[2][1] if isinstance(entry[2], tuple)
            and len(entry[2]) > 1 and isinstance(entry[2][1], list) else []
        )
        if declaration.name == "R"
    )
    assert dict(relation.metadata)["carrier"] == "X"


def test_wlog_metadata_substitution_preserves_descriptive_property_names():
    declaration = pl.Declaration(
        "R",
        pl.DeclarationKind.PREDICATE,
        arity=2,
        metadata=(("carrier", "x"), ("properties", ("reflexive", "symmetric"))),
    )
    transformed = pl._substitute_wlog_declaration(
        declaration, {"x": tl.ConstantTerm("y", "y")}
    )
    metadata = dict(transformed.metadata)
    assert metadata["carrier"] == "y"
    assert metadata["properties"] == ("reflexive", "symmetric")


def test_nested_subproof_can_use_wlog_when_its_conclusion_is_case_invariant():
    text = """1. Let a be any object. (Declaration)
2. Let x be any object. (Declaration)
3. Let y be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. Let H be a closed formula. (Declaration)
7. P(x). (Premise)
8. P(y). (Premise)
9. P(x) -> Q. (Premise)
10. P(y) -> Q. (Premise)
11. a = x or a = y. (Premise)
12. H -> Q. (Conditional Introduction from subproof below)
begin subproof
 12.1. H. (Assumption for Conditional Introduction)
 12.2. a = x or a = y. (Reiteration from 11)
 12.3. a = x. (WLOG from 12.2)
 12.4. Q. (Modus Ponens from 7, 9)
end subproof
"""
    _entries, (ok, err) = _check(text)
    assert ok, err


def test_wlog_replay_transforms_a_nested_subproof():
    text = """1. Let a be any object. (Declaration)
2. Let x be any object. (Declaration)
3. Let y be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. Let H be a closed formula. (Declaration)
7. P(x). (Premise)
8. P(y). (Premise)
9. P(x) -> Q. (Premise)
10. P(y) -> Q. (Premise)
11. a = x or a = y. (Premise)
12. a = x. (WLOG from 11)
13. H -> Q. (Conditional Introduction from subproof below)
begin subproof
 13.1. H. (Assumption for Conditional Introduction)
 13.2. Q. (Modus Ponens from 7, 9)
end subproof
"""
    _entries, (ok, err) = _check(text)
    assert ok, err
