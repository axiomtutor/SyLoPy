


from pathlib import Path

from .support import mp, pl, fl, A, B, C


def sample_multi_text():
    return """
(* leading comment *)
# 1
## Proof that
### if A. A -> B.
### then B.

1. Let A, B be closed formulas such that: A. (Premise)
2. A -> B. (Premise)
3. B. (Modus Ponens from 1, 2)

# 2
## Invalid proof.
### Invalid reiteration.

1. A. (Premise)
2. B. (Reiteration from 1)
"""


def test_parse_multi_proof_file_metadata_and_bodies():
    cases = mp.parse_multi_proof_file(sample_multi_text())
    assert len(cases) == 2

    first, second = cases
    assert first.number == "1"
    assert first.expected_valid is True
    assert first.description == ["if A. A -> B.", "then B."]
    assert isinstance(first.stated_conclusion, fl.AtomicFormula)
    assert repr(first.stated_conclusion) == "B()"
    assert len(first.entries) == 3

    assert second.number == "2"
    assert second.expected_valid is False
    assert second.stated_conclusion is None
    assert len(second.entries) == 2


def test_comments_are_removed_even_midline_and_multiline():
    text = """
# 1
## Proof that
### then A.
1. A(* comment
continues *). (Reiteration from 2)
2. A. (Premise)
"""
    case = mp.parse_multi_proof_file(text)[0]
    assert repr(case.entries[0][1]) == "A()"


def test_header_without_validity_line_defaults_valid():
    case = mp.parse_multi_proof_file(
        "# 7\n### description only\n1. A. (Premise)\n"
    )[0]
    assert case.expected_valid is True
    assert case.description == ["description only"]


def test_then_line_uses_first_conclusion_only():
    result = mp._stated_conclusion_from(["then A.", "then B."])
    assert repr(result) == "A()"


def test_top_level_formulas_includes_only_inferred_formulas():
    entries = [
        ("1", A, ("premise",)),
        ("2", B, ("axiom",)),
        ("3", C, ("rule", pl.ReiterationRule(), ["1"])),
        ("4", "subproof", [("4.1", A, ("assume",))]),
    ]
    assert mp._top_level_formulas(entries) == [C]


def test_top_level_formulas_expands_bundled_formula_lists():
    entries = [
        ("1", [A, B], ("rule", pl.ReiterationRule(), ["0"])),
    ]
    assert mp._top_level_formulas(entries) == [A, B]


def test_conclusion_is_derived_is_structural():
    entries = [
        ("1", A, ("premise",)),
        ("2", fl.Or(A, B), ("rule", pl.DisjunctionIntroductionRule(), ["1"])),
    ]
    assert mp.conclusion_is_derived(entries, fl.Or(A, B))
    assert not mp.conclusion_is_derived(entries, fl.Or(B, A))
    assert mp.conclusion_is_derived(entries, None)


def test_run_multi_proof_file():
    results = mp.run_multi_proof_file(sample_multi_text())
    assert [(n, expected, ok) for n, expected, ok, _ in results] == [
        ("1", True, True),
        ("2", False, False),
    ]


def test_run_multi_detects_unproved_stated_conclusion():
    text = """
# 1
## Proof that
### then B.
1. Let A be a closed formula such that: A. (Premise)
"""
    result = mp.run_multi_proof_file(text)[0]
    assert result[2] is False
    assert "never derived" in result[3]


def test_run_multi_warns_about_duplicate_numbers(capsys):
    text = """
# 1
## Proof that
1. A. (Premise)
# 1
## Proof that
1. B. (Premise)
"""
    mp.run_multi_proof_file(text)
    assert "appears more than once" in capsys.readouterr().out


def test_multi_fixture_is_split_into_expected_cases():
    project = Path(__file__).resolve().parents[1]
    cases = mp.parse_multi_proof_file((project / "tests" / "testProofs" / "multiProof.txt").read_text())
    assert [case.number for case in cases] == ["1", "2", "3", "4", "5", "6", "7", "8"]
    expected = {case.number: case.expected_valid for case in cases}
    assert expected["1"] is True
    assert expected["5"] is False
    assert expected["8"] is False


def test_run_multi_works_without_compatibility_adapter():
    result = mp.run_multi_proof_file(sample_multi_text())
    assert result[0][2] is True


def test_main_returns_zero_when_all_expectations_match(tmp_path, capsys):
    path = tmp_path / "proofs.txt"
    path.write_text(sample_multi_text())
    assert mp.main(str(path)) == 0
    assert "Total: 2" in capsys.readouterr().out


def test_titled_set_theory_proof_runs_through_multiproof_pipeline():
    project = Path(__file__).resolve().parents[1]
    text = (project / "tests" / "setTheoryProofs" / "empty_set_subset.txt").read_text()
    cases = mp.parse_multi_proof_file(text)
    assert [case.number for case in cases] == ["1"]
    assert cases[0].description[-1] == "then the empty set is a subset of X"
    assert mp.run_multi_proof_file(text) == [
        ("1", True, True, None)
    ]


def test_malformed_proof_is_reported_as_a_failed_case_without_aborting_later_cases():
    text = '''
# 1
## Proof that
1. Let X be any set, R be a transitive relation on X, a, b, c be in X, and R(a,b) and R(b,c). (Declaration)
2. R(a,c). (Relation Transitivity from )

# 2
## Proof that
1. Let A be a closed formula. (Declaration)
'''
    results = mp.run_multi_proof_file(text)
    assert [(n, expected, ok) for n, expected, ok, _ in results] == [
        ('1', True, False),
        ('2', True, True),
    ]
    assert 'Malformed rule justification' in results[0][3]

