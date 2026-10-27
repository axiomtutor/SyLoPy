"""Exercise the mutation-check CLI against a toy repository only."""

import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MUTATION_CHECK_SCRIPT = REPOSITORY_ROOT / "tools" / "mutation_check.py"


def test_mutation_check_classifies_mutants_and_pattern_mismatches(tmp_path):
    toy_repository = tmp_path / "toy_repository"
    tools_directory = toy_repository / "tools"
    tests_directory = toy_repository / "tests"
    tools_directory.mkdir(parents=True)
    tests_directory.mkdir()
    (toy_repository / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(MUTATION_CHECK_SCRIPT, tools_directory / "mutation_check.py")

    (toy_repository / "subject.py").write_text(
        "def answer():\n"
        "    return 1\n"
        "\n"
        "def unused_value():\n"
        "    return 3\n",
        encoding="utf-8",
    )
    (tests_directory / "test_subject.py").write_text(
        "from SyLoPy.subject import answer\n"
        "\n"
        "def test_answer():\n"
        "    assert answer() == 1\n",
        encoding="utf-8",
    )

    spec_path = toy_repository / "mutants.json"
    spec_path.write_text(
        json.dumps(
            [
                {
                    "id": "detected-change",
                    "file": "subject.py",
                    "old": "return 1",
                    "new": "return 2",
                },
                {
                    "id": "missed-change",
                    "file": "subject.py",
                    "old": "return 3",
                    "new": "return 4",
                },
                {
                    "id": "duplicate-pattern",
                    "file": "subject.py",
                    "old": "return ",
                    "new": "pass",
                },
                {
                    "id": "absent-pattern",
                    "file": "subject.py",
                    "old": "this text is absent",
                    "new": "replacement",
                },
            ]
        ),
        encoding="utf-8",
    )

    test_command = (
        f"{shlex.quote(sys.executable)} -m pytest -q tests/test_subject.py"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(tools_directory / "mutation_check.py"),
            str(spec_path),
            "--tests",
            test_command,
            "--jobs",
            "2",
        ],
        cwd=toy_repository,
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
    )

    assert completed.returncode == 1, completed.stdout + completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0].startswith("KILLED detected-change"), completed.stdout
    assert lines[1].startswith("SURVIVED missed-change"), completed.stdout
    assert (
        "PATTERN duplicate-pattern (subject.py: expected one match, found 2)"
        in lines
    )
    assert (
        "PATTERN absent-pattern (subject.py: expected one match, found 0)"
        in lines
    )
    assert (
        "Summary: total=4 killed=1 survived=1 pattern=2 timeout=0 error=0"
        in lines
    )
