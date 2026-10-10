"""Each case in `tests/testProofs/uniqueness_red_team.txt` is decided for the
reason its title gives.

A fixture that is expected to fail proves nothing if it fails for some other
reason (a parse error, an undeclared name, a different condition than the one
in the title). The validator now says which side condition of `Uniqueness`
refused a line, so this test reads each title, finds the condition (or the
shape, or the scope) it names, and requires the refusal to name it too. The
cases are the file's own text, so a new case needs no change here.
"""

import re
from pathlib import Path

import pytest

import SyLoPy.source.validate_all_proofs as mp

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "testProofs" / "uniqueness_red_team.txt"

_CASE_HEADER = re.compile(r"^#\s*(\d+)\s*$")


def _titles(text):
    """{case number: the `## ...` line that follows its `# N` header}."""
    titles, number = {}, None
    for line in text.splitlines():
        header = _CASE_HEADER.match(line.strip())
        if header:
            number = header.group(1)
        elif number is not None and line.startswith("##") and not line.startswith("###"):
            titles.setdefault(number, line[2:].strip())
    return titles


def _results():
    text = FIXTURE.read_text()
    results = mp.run_multi_proof_file(
        text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    titles = _titles(text)
    return [(number, expected_valid, ok, message, titles[number])
            for number, expected_valid, ok, message, _crashed in results]


RESULTS = _results()
INVALID = [r for r in RESULTS if not r[1]]
VALID = [r for r in RESULTS if r[1]]


def test_the_file_is_read_whole():
    # Nineteen cases, none lost to a parse error (which would show as a
    # refusal for the wrong reason).
    assert [r[0] for r in RESULTS] == [str(n) for n in range(1, 20)]
    assert not [r for r in RESULTS if r[3] and r[3].startswith(("parse error", "parse/check error"))]


@pytest.mark.parametrize("number,expected_valid,ok,message,title", VALID, ids=[f"case{r[0]}" for r in VALID])
def test_the_cases_accepted_by_design_are_accepted(number, expected_valid, ok, message, title):
    assert ok, message
    assert title.lower().startswith("proof that")


@pytest.mark.parametrize("number,expected_valid,ok,message,title", INVALID, ids=[f"case{r[0]}" for r in INVALID])
def test_each_invalid_case_is_refused_for_the_reason_in_its_title(number, expected_valid, ok, message, title):
    assert not ok, f"case {number} is accepted: {title}"
    assert message, f"case {number} fails without a message"

    named_conditions = re.findall(r"condition (\d)", title)
    if named_conditions:
        for condition in named_conditions:
            assert f"condition {condition}:" in message, (
                f"case {number} should be refused for condition {condition}: {message}")
    elif "shape" in title:
        assert "unique-existence shape" in message, message
    elif "scope" in title:
        assert "not defined or not in scope" in message, message
    else:
        pytest.fail(f"case {number}'s title names no condition, shape or scope: {title}")


def test_a_case_that_names_two_conditions_is_refused_for_both():
    (case,) = [r for r in INVALID if "condition 3 and condition 4" in r[4]]
    assert "condition 3:" in case[3] and "condition 4:" in case[3]
