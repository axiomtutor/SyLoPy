from pathlib import Path

import pytest

from .support import mp, pl
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
    assert [(number, expected, ok) for number, expected, ok, _, _ in results] == [
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


class _ExplodingRule(pl.InferenceRule):
    """A rule that always raises from `applies`, for exercising the
    CATEGORY_RULE_RAISED path deliberately rather than waiting for a real
    rule to have a real bug. `premise_arity = 0` and a name with no
    existing meaning so it can be cited as a bare "(TestExploding)" --
    the same no-"from"-clause shape `ReflexivityRule` already uses --
    reaching it through `NamedRulePlaceholder` resolution exactly the way
    a real citation would, rather than injecting it some other way.
    """
    name = "TestExploding"
    premise_arity = 0

    def applies(self, candidates, phi):
        raise RuntimeError("boom")


def test_is_rule_crash_recognizes_only_category_rule_raised():
    raised = pl.ValidationError("Line 2", "2", pl.CATEGORY_RULE_RAISED, "'Exploding' raised an exception")
    genuine = pl.ValidationError("Line 2", "2", pl.CATEGORY_RULE_MISMATCH, "does not justify this line")
    assert validator._is_rule_crash(raised) is True
    assert validator._is_rule_crash(genuine) is False
    assert validator._is_rule_crash(None) is False


def test_run_multi_proof_file_flags_a_rule_crash_distinctly_from_a_genuine_rejection():
    # Two single-line proofs, deliberately shaped as similarly as possible
    # (a bare premise, then one more line) so the only difference between
    # them is *why* the second line fails: one genuinely doesn't follow
    # (an ordinary, correctly-reported rejection), the other crashes
    # outright. Both currently produce ok=False -- confirming that only
    # the crashing one is flagged as rule_crashed is the whole point:
    # before _is_rule_crash existed, these were indistinguishable to
    # anything that only looked at expected_valid == ok.
    text = """
# 1
## Invalid proof.
1. Let A, B be closed formulas such that: A. (Premise)
2. B. (Reiteration from 1)

# 2
## Invalid proof.
1. Let A, B be closed formulas such that: A. (Premise)
2. B. (TestExploding)
"""
    results = mp.run_multi_proof_file(text, rules=pl.default_rules() + [_ExplodingRule()])
    by_number = {number: (ok, rule_crashed) for number, _expected, ok, _message, rule_crashed in results}
    assert by_number["1"] == (False, False)  # genuinely doesn't follow -- a real rejection
    assert by_number["2"] == (False, True)   # the rule itself crashed -- not a real rejection

    # The distinction has to actually change something for a caller that
    # cares, not just be computed and ignored: a ProofResult built with
    # implementation_error=True is never "passed" regardless of whether
    # expected_valid happens to equal ok.
    crashed_result = validator.ProofResult("fixture.txt", "2", False, False, "boom", True)
    assert crashed_result.expected_valid == crashed_result.ok  # would look like a pass by that alone
    assert crashed_result.passed is False
