#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONPATH="$(cd "$ROOT/.." && pwd)${PYTHONPATH:+:$PYTHONPATH}"

# Proof-fixture inspection commands are intentionally separate from the full
# validation run. --suite and --list-suites are useful for inspecting the
# fixture corpus without rerunning the Python implementation tests.
if (( $# > 0 )); then
    python3 "$ROOT/source/validate_all_proofs.py" "$@"
    exit $?
fi

pytest_status=0
coverage_status=0
fixture_status=0

# Run the Python test suite once under coverage. Do not stop here if it
# fails: the proof-fixture corpus must still be checked so one failure does
# not hide another.
python3 -m coverage run --source="$ROOT/source" -m pytest -q pytest_tests
pytest_status=$?

# Coverage reporting is diagnostic; preserve a real test failure as the
# eventual exit status.
python3 -m coverage report -m
coverage_status=$?

# Validate the actual proof files, including tests/testDiscreteMath.
# This is deliberately a separate stage from pytest: pytest tests the
# implementation, while this stage tests the proof corpus against it.
python3 "$ROOT/source/validate_all_proofs.py"
fixture_status=$?

if (( pytest_status != 0 || fixture_status != 0 || coverage_status != 0 )); then
    echo
    echo "Test run failed."
    echo "  pytest:   $pytest_status"
    echo "  coverage: $coverage_status"
    echo "  fixtures: $fixture_status"
    exit 1
fi

echo
echo "All Python tests and all enforced proof fixtures passed."
exit 0
