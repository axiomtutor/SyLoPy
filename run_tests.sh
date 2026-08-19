#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$(cd "$ROOT/.." && pwd)${PYTHONPATH:+:$PYTHONPATH}"

# Arguments are passed to the fixture validator.  Examples:
#   ./run_tests.sh --suite testDiscreteMath
#   ./run_tests.sh --suite testDiscreteMath --verbose
#   ./run_tests.sh --list-suites
if (( $# > 0 )); then
    python3 "$ROOT/source/validate_all_proofs.py" "$@"
    exit $?
fi

pytest_status=0
coverage_status=0
fixture_status=0
pytest_log="$(mktemp)"
trap 'rm -f "$pytest_log"' EXIT

# Keep the normal test run compact. Full pytest diagnostics remain available
# by running pytest directly; fixture suites have their own --verbose mode
# through this script.
python3 -m coverage run --source="$ROOT/source" -m pytest -q --tb=no pytest_tests >"$pytest_log" 2>&1
pytest_status=$?

if (( pytest_status == 0 )); then
    pytest_summary="$(grep -E '[0-9]+ passed' "$pytest_log" | tail -n 1)"
    echo "pytest:   PASS${pytest_summary:+ — $pytest_summary}"
else
    echo "pytest:   FAIL"
    grep -E '^FAILED |^[0-9]+ failed|^[0-9]+ passed' "$pytest_log" | tail -n 12 || tail -n 12 "$pytest_log"
fi

# Keep the normal run compact. For line-level coverage use:
#   python3 -m coverage report -m
python3 -m coverage report --format=total >/dev/null
coverage_status=$?
if (( coverage_status == 0 )); then
    echo "coverage: PASS"
else
    echo "coverage: FAIL"
fi

python3 "$ROOT/source/validate_all_proofs.py"
fixture_status=$?

if (( pytest_status != 0 || fixture_status != 0 || coverage_status != 0 )); then
    echo
echo "Test run failed."
exit 1
fi

echo ""
echo "All Python tests and all enforced proof fixtures passed."
exit 0
