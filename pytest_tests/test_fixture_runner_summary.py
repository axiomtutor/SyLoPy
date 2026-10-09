"""Regression tests for the fixture runner's default summary path."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

from SyLoPy.source import validate_all_proofs as runner


def test_default_main_checks_each_suite_once_and_aggregates_results(monkeypatch):
    enforced_a = "tests/enforced_a"
    enforced_b = "tests/enforced_b"
    informational = "tests/informational"
    monkeypatch.setattr(runner, "ENFORCED_DIRS", [enforced_a, enforced_b])
    monkeypatch.setattr(runner, "INFORMATIONAL_DIRS", [informational])

    def passed(filename):
        return runner.ProofResult(filename, "1", True, True, None, False)

    results_by_suite = {
        enforced_a: [passed("a.txt"), passed("b.txt")],
        enforced_b: [passed("c.txt")],
        # Informational failures are reported, but do not fail the command.
        informational: [
            runner.ProofResult("info.txt", "1", False, True, None, False)
        ],
    }
    calls = []

    def fake_run(directories):
        calls.append(tuple(directories))
        assert len(directories) == 1, "each suite should be evaluated only once"
        return results_by_suite[directories[0]]

    monkeypatch.setattr(runner, "run", fake_run)
    output = StringIO()
    with redirect_stdout(output):
        status = runner.main([])

    assert status == 0
    assert calls == [(enforced_a,), (enforced_b,), (informational,)]
    assert (
        "Total proofs checked: 4 (enforced: 3/3, informational: 0/1)"
        in output.getvalue()
    )
