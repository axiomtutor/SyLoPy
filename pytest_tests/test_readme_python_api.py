"""Execute the runnable Python examples marked in README.md."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_README_PATH = Path(__file__).resolve().parents[1] / "README.md"
_MARKER_RE = re.compile(r"<!--\s*python-api-test:\s*([a-z-]+)\s*-->")
_EXPECTED_EXAMPLES = {
    "surface-check",
    "theorem-promotion",
    "core-type-resources",
}
_FENCE = chr(96) * 3


def _marked_python_examples():
    lines = _README_PATH.read_text(encoding="utf-8").splitlines()
    examples = {}
    for index, line in enumerate(lines):
        if "python-api-test:" not in line:
            continue

        match = _MARKER_RE.fullmatch(line.strip())
        assert match, f"{_README_PATH.name}:{index + 1}: malformed Python example marker"
        name = match.group(1)
        assert name in _EXPECTED_EXAMPLES, (
            f"{_README_PATH.name}:{index + 1}: unknown Python example {name!r}"
        )
        assert name not in examples, f"duplicate Python example marker {name!r}"
        assert index + 1 < len(lines) and lines[index + 1].startswith(_FENCE + "python"), (
            f"{_README_PATH.name}:{index + 1}: marker must precede a Python code fence"
        )
        closing = next(
            (j for j in range(index + 2, len(lines)) if lines[j].startswith(_FENCE)),
            None,
        )
        assert closing is not None, (
            f"{_README_PATH.name}:{index + 2}: unclosed Python code fence"
        )
        examples[name] = (index + 2, "\n".join(lines[index + 2:closing]))

    assert set(examples) == _EXPECTED_EXAMPLES, (
        f"README Python examples differ from expected set: found {sorted(examples)}"
    )
    return examples


@pytest.mark.parametrize("example_name", sorted(_EXPECTED_EXAMPLES))
def test_marked_readme_python_example_executes(example_name):
    examples = _marked_python_examples()
    opening_line, source = examples[example_name]
    namespace = {"__name__": "__readme_python_example__"}
    try:
        exec(compile(source, f"{_README_PATH.name}:{opening_line}", "exec"), namespace)
    except Exception as exc:
        pytest.fail(
            f"README Python example {example_name!r} at line {opening_line} failed: "
            f"{type(exc).__name__}: {exc}"
        )

    assert namespace.get("ok") is True, (
        f"README Python example {example_name!r} did not leave a successful ok result"
    )
    if example_name == "theorem-promotion":
        assert "identity" in namespace, "the theorem-promotion example must create its theorem"
