


from pathlib import Path

import pytest

from .support import pl, fl, tl, pp, mp, st, c, v, atom


def test_has_no_elements_sugar_expands_to_universal_non_membership():
    formula = pp.parse_formula("X has no elements")
    assert isinstance(formula, fl.ForAll)
    assert repr(formula.body) == f"¬In({formula.var}, X)"


def test_set_equality_rule_accepts_antisymmetric_subset_pair_in_either_order():
    x, y = c("X"), c("Y")
    x_subset_y = st.subset_formula(x, y)
    y_subset_x = st.subset_formula(y, x)
    rule = st.SetEqualityRule()
    assert rule.applies([x_subset_y, y_subset_x], fl.Equals(x, y))
    assert rule.applies([y_subset_x, x_subset_y], fl.Equals(x, y))
    assert rule.applies([x_subset_y, y_subset_x], fl.Equals(y, x))


def test_set_equality_rule_rejects_non_matching_or_same_direction_pairs():
    x, y, z = c("X"), c("Y"), c("Z")
    rule = st.SetEqualityRule()
    # Both facts point the same direction -- no antisymmetry to conclude from.
    assert not rule.applies([st.subset_formula(x, y), st.subset_formula(x, y)], fl.Equals(x, y))
    # Subsets of two unrelated pairs.
    assert not rule.applies([st.subset_formula(x, y), st.subset_formula(z, x)], fl.Equals(x, y))


def test_extract_subset_operands_rejects_non_subset_shapes():
    assert st._extract_subset_operands(atom("P", c("a"))) is None
    assert st._extract_subset_operands(fl.ForAll("x", atom("P", v("x")))) is None


def test_promote_theorem_generalizes_over_top_level_declared_object():
    text = open(
        Path(__file__).resolve().parents[1] / "tests" / "setTheoryProofs" / "empty_set_subset.txt"
    ).read()
    entries, _ = pp.parse_proof_text(text)
    proof = pl.Proof(entries)
    assert proof.check()[0] is True

    theorem = pl.promote_theorem("The empty set subset theorem", proof)
    assert theorem.generalized_names == ["X"]
    assert theorem.premises == []
    assert isinstance(theorem.conclusion, fl.ForAll)

    # Cited for a *different* declared set, with no premises, exactly the
    # way basicSTProofs.txt's second proof cites it.
    cite_text = """
1. Let Y be any set. (Declaration)
2. The empty set is a subset of Y. (The empty set subset theorem)
"""
    cite_entries, _ = pp.parse_proof_text(cite_text)
    cite_proof = pl.Proof(cite_entries, rules=pl.default_rules() + [theorem])
    ok, err = cite_proof.check_detailed()
    assert ok, str(err)


def test_promoted_theorem_rejects_a_citation_with_the_wrong_shape():
    text = open(
        Path(__file__).resolve().parents[1] / "tests" / "setTheoryProofs" / "empty_set_subset.txt"
    ).read()
    entries, _ = pp.parse_proof_text(text)
    theorem = pl.promote_theorem("The empty set subset theorem", pl.Proof(entries))

    wrong_direction_text = """
1. Let Y be any set. (Declaration)
2. Y is a subset of the empty set. (The empty set subset theorem)
"""
    wrong_entries, _ = pp.parse_proof_text(wrong_direction_text)
    ok, err = pl.Proof(wrong_entries, rules=pl.default_rules() + [theorem]).check_detailed()
    assert not ok
    assert err.category == pl.CATEGORY_RULE_MISMATCH


def test_promote_theorem_rejects_an_unchecked_proof():
    entries = [("1", atom("A"), ("rule", pl.ReiterationRule(), ["missing"]))]
    with pytest.raises(ValueError, match="does not validate"):
        pl.promote_theorem("Bogus", pl.Proof(entries))


def test_theorem_citation_with_from_or_subproof_still_raises_instead_of_silently_deferring():
    # Guards the fallback added for bare theorem citations: text that still
    # contains "from"/"subproof" after every real citation shape has failed
    # to match is far more likely a malformed citation than a theorem
    # title, and must keep raising immediately.
    with pytest.raises(ValueError):
        pp.parse_justification("Conditional Introduction from subproof above")


def test_multiproof_file_promotes_a_titled_theorem_for_later_cases_to_cite():
    project = Path(__file__).resolve().parents[1]
    text = (project / "tests" / "testSetTheory" / "empty_set_subset_and_uniqueness.txt").read_text()
    results = mp.run_multi_proof_file(text)
    assert [(number, ok) for number, _expected, ok, _msg in results] == [
        ("1", True),
        ("2", True),
    ]


def test_multiproof_promotion_is_best_effort_not_fatal(capsys):
    # A titled proof that derives nothing at the top level (only a bare
    # declaration) can't be promoted -- confirm that is a warning, not a
    # failure of the whole file.
    text = """
# 1: Nothing to promote
## Proof that
1. Let A be a closed formula. (Declare)
"""
    results = mp.run_multi_proof_file(text)
    assert results == [("1", True, True, None)]
    assert "was not promoted" in capsys.readouterr().out




