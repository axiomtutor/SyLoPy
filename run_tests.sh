#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$(cd "$ROOT/.." && pwd)${PYTHONPATH:+:$PYTHONPATH}"

# Arguments are passed to the fixture validator unless they are test-runner
# options.  Examples:
#   ./run_tests.sh --suite testDiscreteMath
#   ./run_tests.sh --suite testDiscreteMath --verbose
#   ./run_tests.sh --list-suites
#   ./run_tests.sh --list-batches
#   ./run_tests.sh --suite default
#   ./run_tests.sh --suite extended
#   ./run_tests.sh --extended
if (( $# == 1 )) && [[ "$1" == "--help" || "$1" == "-h" ]]; then
    cat <<'EOF'
Usage: ./run_tests.sh [options]

Python test suite options:
  --suite default     Run the current default Python suite
  --suite extended    Run the named extended Python suite
  --suite all         Run every Python suite
  --extended          Compatibility alias for --suite all
  --list-batches      List named Python test suites

Proof fixture options:
  --suite NAME        Run one proof fixture suite
  --list-suites       List proof fixture suite names
  --verbose           Show proof-level fixture output
EOF
    exit 0
fi

if (( $# == 1 )) && [[ "$1" == "--list-batches" ]]; then
    cat <<'EOF'
default  - current Python tests, run by default
extended - red-team, audit, and mutation-tool Python tests
all      - every Python test suite
EOF
    exit 0
fi

if (( $# == 1 )) && [[ "$1" == "--suite" || "$1" == "--extended" ]]; then
    if [[ "$1" == "--suite" ]]; then
        echo "Missing suite name. Use --list-batches or --list-suites." >&2
        exit 2
    fi
fi

if (( $# == 2 )) && [[ "$1" == "--suite" ]]; then
    case "$2" in
        default)
            python3 -m coverage run --source="$ROOT/source" -m pytest -q --suite default pytest_tests
            status=$?
            python3 -m coverage report --format=total >/dev/null
            coverage_status=$?
            python3 "$ROOT/source/validate_all_proofs.py"
            fixture_status=$?
            if (( status != 0 || coverage_status != 0 || fixture_status != 0)); then
                exit 1
            fi
            exit 0
            ;;
        extended)
            python3 -m coverage run --source="$ROOT/source" -m pytest -q --suite extended pytest_tests
            status=$?
            python3 -m coverage report --format=total >/dev/null
            coverage_status=$?
            python3 "$ROOT/source/validate_all_proofs.py"
            fixture_status=$?
            if (( status != 0 || coverage_status != 0 || fixture_status != 0)); then
                exit 1
            fi
            exit 0
            ;;
        all)
            python3 -m coverage run --source="$ROOT/source" -m pytest -q --suite all pytest_tests
            status=$?
            python3 -m coverage report --format=total >/dev/null
            python3 "$ROOT/source/validate_all_proofs.py"
            fixture_status=$?
            if (( status != 0 || fixture_status != 0)); then
                exit 1
            fi
            exit 0
            ;;
    esac
fi

if (( $# == 1 )) && [[ "$1" == "--extended" ]]; then
    python3 -m coverage run --source="$ROOT/source" -m pytest -q --suite all pytest_tests
    status=$?
    python3 -m coverage report --format=total >/dev/null
    fixture_status=0
    python3 "$ROOT/source/validate_all_proofs.py"
    fixture_status=$?
    if (( status != 0 || fixture_status != 0)); then
        exit 1
    fi
    exit 0
fi

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
python3 -m coverage run --source="$ROOT/source" -m pytest -q --tb=no --suite default pytest_tests >"$pytest_log" 2>&1
pytest_status=$?

if (( pytest_status == 0 )); then
    pytest_summary="$(grep -E '[0-9]+ passed' "$pytest_log" | tail -n 1)"
    echo "pytest:   PASS${pytest_summary:+ — $pytest_summary}"
else
    echo "pytest:   FAIL"
    grep -E '^FAILED |^[0-9]+ failed|^[0-9]+ passed' "$pytest_log" | tail -n 12 || tail -n 12 "$pytest_log"
    echo
    echo "=== Failure details ==="
    python3 -m pytest -q --tb=short --lf pytest_tests 2>&1 | tail -n 150
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
