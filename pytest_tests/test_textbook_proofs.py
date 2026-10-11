"""Focused regression checks for the five worked theory proofs.

The fixture corpus already checks these files as a group; keeping this small
focused test gives direct failure messages when one worked proof stops
validating.
"""

from SyLoPy.source import validate_all_proofs as fixture_validator


TEXTBOOK_PROOFS = (
    "tests/testProofsNat/successor_has_no_fixed_points.txt",
    "tests/testSetTheory/membership-equivalence-implies-set-equality.txt",
    "tests/testSetTheory/separation-produces-subset.txt",
    "tests/testNumberTheory/divisibility_closed_under_right_multiplication.txt",
    "tests/testDiscreteMath/transitive-irreflexive-implies-asymmetric.txt",
)


def test_textbook_proofs_validate_individually():
    for relative_path in TEXTBOOK_PROOFS:
        results = fixture_validator.check_file(fixture_validator.ROOT / relative_path)
        assert results and all(result.passed for result in results), (
            f"worked proof failed validation: {relative_path}: {results!r}"
        )
