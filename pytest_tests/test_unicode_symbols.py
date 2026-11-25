"""J41 regression tests for mathematical symbols as input notation."""

from pathlib import Path

import pytest

from .support import pl, pp
from .test_parse_oracle import load_cases


_ORACLE = Path(__file__).resolve().parents[1] / "parse_oracle" / "unicode_symbols.txt"
_CASES = load_cases(_ORACLE)


def _parse_surface(surface: str, context: str):
    if context == "line":
        return pp._ElaborationContext(pp.default_theory_environment()).parse_core_formula(surface)
    return pp.parse_formula(surface)


@pytest.mark.parametrize("case", _CASES, ids=[case["id"] for case in _CASES])
def test_symbolic_surface_has_the_word_form_reading(case):
    if case["expect"] == "REJECT":
        with pytest.raises((TypeError, ValueError)):
            _parse_surface(case["surface"], case["context"])
        return
    actual = _parse_surface(case["surface"], case["context"])
    expected = pp.parse_formula(case["expect"])
    assert pl._alpha_eq(actual, expected), (
        f"{case['id']}: {case['surface']!r}\n"
        f"parsed: {actual!r}\n"
        f"word form: {expected!r}\n"
        f"why: {case.get('why', '')}"
    )


def test_required_spacing_and_nesting_regressions_are_in_the_oracle():
    ids = {case["id"] for case in _CASES}
    assert {
        "unicode-no-spaces-membership",
        "unicode-no-spaces-connectives",
        "unicode-symbol-adjacent-to-word",
        "unicode-symbols-inside-quantifier",
    } <= ids
