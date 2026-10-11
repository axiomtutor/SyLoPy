"""End-to-end coverage for proof promotion, subproofs, and rule shape-checking."""

from pathlib import Path

from .support import mp


_EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "setTheoryProofs"
    / "theorem_promotion_example.txt"
)


def test_theorem_promotion_example_validates_and_rejects_wrong_instance():
    results = mp.run_multi_proof_file(_EXAMPLE.read_text())

    assert [(number, expected, ok, crashed) for number, expected, ok, _message, crashed in results] == [
        ("1", True, True, False),
        ("2", True, True, False),
        ("3", False, False, False),
    ]


def test_theorem_promotion_example_states_checkable_conclusions():
    cases = mp.parse_multi_proof_file(_EXAMPLE.read_text())

    assert [case.title for case in cases] == [
        "Equality symmetry theorem",
        "Apply equality symmetry theorem",
        "Reject a wrong theorem instance",
    ]
    assert cases[0].stated_conclusion is not None
    assert cases[1].stated_conclusion is not None
