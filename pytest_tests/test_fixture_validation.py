from pathlib import Path

from .support import mp
from SyLoPy.source import validate_all_proofs as validator


def test_discrete_math_fixture_corpus_is_enforced():
    assert "tests/testDiscreteMath" in validator.ENFORCED_DIRS


def test_malformed_expected_valid_discrete_math_proof_fails_and_later_proofs_run():
    text = """
Use discrete math.

# 1
## Proof that
1. Let X be any set, R be a transitive relation on X, a, b, c be in X, and R(a,b) and R(b,c). (Declaration)
2. R(a,c). (Relation Transitivity from )

# 2
## Proof that
1. Let X be any set, R be a symmetric relation on X, a, b be in X, and R(a,b). (Declaration)
2. R(b,a). (Relation Symmetry from 1)
"""
    results = mp.run_multi_proof_file(text)
    assert [(number, expected, ok) for number, expected, ok, _ in results] == [
        ("1", True, False),
        ("2", True, True),
    ]
    assert "Malformed rule justification" in results[0][3]


def test_fixture_validator_preserves_cross_case_theorem_promotion():
    project = Path(__file__).resolve().parents[1]
    path = project / "tests" / "testSetTheory" / "empty_set_subset_and_uniqueness.txt"
    results = validator.check_file(path)
    assert [(result.proof_id, result.passed) for result in results] == [
        ("1", True),
        ("2", True),
    ]


def test_current_discrete_math_fixture_is_valid():
    project = Path(__file__).resolve().parents[1]
    results = validator.check_file(
        project / "tests" / "testDiscreteMath" / "relation_properties.txt"
    )
    assert all(result.passed for result in results), results
