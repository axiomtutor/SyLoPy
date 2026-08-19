#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$(cd "$ROOT/.." && pwd)${PYTHONPATH:+:$PYTHONPATH}"

# With arguments, inspect the fixture corpus only.  Use --verbose for
# individual fixture results; the default is suite-level summary output.
if (( $# > 0 )); then
    python3 "$ROOT/source/validate_all_proofs.py" "$@"
    exit $?
fi

pytest_status=0
coverage_status=0
fixture_status=0

python3 -m coverage run --source="$ROOT/source" -m pytest -q pytest_tests
pytest_status=$?

# Keep the normal run compact.  For line-level coverage use:
#   python3 -m coverage report -m
python3 -m coverage report --format=total >/dev/null
coverage_status=$?

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
