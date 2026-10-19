#!/usr/bin/env python3
"""Run small source mutations and check whether a test command detects them.

The repository is copied separately for each mutant. Mutants are classified as
KILLED when the test command exits nonzero, SURVIVED when it exits zero,
PATTERN when the requested old text does not occur exactly once, and TIMEOUT
when the test command exceeds the per-mutant timeout.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

DEFAULT_TIMEOUT_SECONDS = 120
IGNORED_COPY_PATTERNS = (
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".coverage",
    ".coverage.*",
)


@dataclass(frozen=True)
class Mutant:
    id: str
    file: str
    old: str
    new: str


@dataclass(frozen=True)
class Outcome:
    mutant_id: str
    status: str
    details: str = ""


def positive_int(value: str) -> int:
    """argparse type for a strictly positive integer."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def load_spec(spec_path: Path) -> list[Mutant]:
    """Read and validate the JSON list of source mutations."""
    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"could not read {spec_path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {spec_path}: {error}") from error

    if not isinstance(data, list):
        raise ValueError("the spec must be a JSON list")

    mutants: list[Mutant] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(data):
        location = f"spec item {index}"
        if not isinstance(item, dict):
            raise ValueError(f"{location} must be an object")
        missing = [key for key in ("id", "file", "old", "new") if key not in item]
        if missing:
            raise ValueError(f"{location} is missing: {', '.join(missing)}")

        raw_id = item["id"]
        if isinstance(raw_id, bool) or not isinstance(raw_id, (str, int)):
            raise ValueError(f"{location} id must be a non-empty string or integer")
        mutant_id = str(raw_id)
        if not mutant_id.strip():
            raise ValueError(f"{location} id must not be empty")
        if mutant_id in seen_ids:
            raise ValueError(f"duplicate mutant id: {mutant_id}")
        seen_ids.add(mutant_id)

        filename = item["file"]
        old = item["old"]
        new = item["new"]
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError(f"{location} file must be a non-empty string")
        relative_path = Path(filename)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"{location} file must be a repository-relative path")
        if not isinstance(old, str) or not old:
            raise ValueError(f"{location} old must be a non-empty string")
        if not isinstance(new, str):
            raise ValueError(f"{location} new must be a string")

        mutants.append(Mutant(mutant_id, filename, old, new))

    return mutants


def is_within(path: Path, directory: Path) -> bool:
    """Return whether path is directory itself or a descendant of it."""
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def run_mutant(
    repository_root: Path,
    mutant: Mutant,
    test_command: list[str],
) -> Outcome:
    """Test one mutation in an isolated copy of the repository."""
    try:
        with tempfile.TemporaryDirectory(prefix="mutation-check-") as temporary:
            temporary_root = Path(temporary).resolve()
            copied_repository = temporary_root / "SyLoPy"
            shutil.copytree(
                repository_root,
                copied_repository,
                ignore=shutil.ignore_patterns(*IGNORED_COPY_PATTERNS),
            )

            target = (copied_repository / mutant.file).resolve()
            if not is_within(target, copied_repository.resolve()):
                return Outcome(
                    mutant.id,
                    "PATTERN",
                    f"{mutant.file!r}: path resolves outside the copied repository "
                    "(found 0 matches)",
                )
            if not target.is_file():
                return Outcome(
                    mutant.id,
                    "PATTERN",
                    f"{mutant.file!r}: expected one match, found 0 (file missing)",
                )

            try:
                original = target.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                return Outcome(
                    mutant.id,
                    "ERROR",
                    f"could not read {mutant.file!r}: {error}",
                )

            count = original.count(mutant.old)
            if count != 1:
                return Outcome(
                    mutant.id,
                    "PATTERN",
                    f"{mutant.file!r}: expected one match, found {count}",
                )

            target.write_text(
                original.replace(mutant.old, mutant.new, 1),
                encoding="utf-8",
            )

            environment = os.environ.copy()
            # The package imported by tests is the copied project at
            # <temporary_root>/SyLoPy, so its parent must be on PYTHONPATH.
            environment["PYTHONPATH"] = str(temporary_root)
            try:
                completed = subprocess.run(
                    test_command,
                    cwd=copied_repository,
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                return Outcome(
                    mutant.id,
                    "TIMEOUT",
                    f"test command exceeded {DEFAULT_TIMEOUT_SECONDS} seconds",
                )
            except OSError as error:
                return Outcome(
                    mutant.id,
                    "ERROR",
                    f"could not start test command: {error}",
                )

            if completed.returncode == 0:
                return Outcome(mutant.id, "SURVIVED")
            return Outcome(mutant.id, "KILLED")
    except OSError as error:
        return Outcome(mutant.id, "ERROR", f"could not prepare mutation: {error}")


def render_outcome(outcome: Outcome) -> str:
    line = f"{outcome.status} {outcome.mutant_id}"
    if outcome.details:
        line += f" ({outcome.details})"
    return line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether a test command detects each source mutation."
    )
    parser.add_argument("spec", type=Path, help="JSON file containing mutation specs")
    parser.add_argument(
        "--tests",
        required=True,
        help="test command, for example: \"python3 -m pytest -q pytest_tests/test_example.py\"",
    )
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=1,
        help="number of mutations to test concurrently (default: 1)",
    )
    arguments = parser.parse_args(argv)

    try:
        mutants = load_spec(arguments.spec)
    except ValueError as error:
        parser.error(str(error))

    try:
        test_command = shlex.split(arguments.tests)
    except ValueError as error:
        parser.error(f"invalid --tests command: {error}")
    if not test_command:
        parser.error("--tests must contain a command")

    repository_root = Path(__file__).resolve().parents[1]
    outcomes: list[Outcome | None] = [None] * len(mutants)

    if arguments.jobs == 1 or len(mutants) < 2:
        outcomes = [
            run_mutant(repository_root, mutant, test_command)
            for mutant in mutants
        ]
    else:
        with ThreadPoolExecutor(max_workers=arguments.jobs) as executor:
            future_indices = {
                executor.submit(run_mutant, repository_root, mutant, test_command): index
                for index, mutant in enumerate(mutants)
            }
            for future in as_completed(future_indices):
                outcomes[future_indices[future]] = future.result()

    completed_outcomes = [outcome for outcome in outcomes if outcome is not None]
    for outcome in completed_outcomes:
        print(render_outcome(outcome))

    counts = {
        status: sum(outcome.status == status for outcome in completed_outcomes)
        for status in ("KILLED", "SURVIVED", "PATTERN", "TIMEOUT", "ERROR")
    }
    print(
        "Summary: "
        f"total={len(completed_outcomes)} "
        f"killed={counts['KILLED']} "
        f"survived={counts['SURVIVED']} "
        f"pattern={counts['PATTERN']} "
        f"timeout={counts['TIMEOUT']} "
        f"error={counts['ERROR']}"
    )

    # Only a test-detected mutation counts as success. Pattern mismatches,
    # surviving mutations, timeouts, and execution errors all fail the run.
    return 0 if len(completed_outcomes) == len(mutants) and all(
        outcome.status == "KILLED" for outcome in completed_outcomes
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
