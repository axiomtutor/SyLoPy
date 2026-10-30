


import os
import subprocess
import sys
from pathlib import Path

from .support import PROJECT_PARENT


def run_clean_import(statement: str):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_PARENT)
    return subprocess.run(
        [sys.executable, "-c", statement],
        cwd=PROJECT_PARENT,
        env=env,
        text=True,
        capture_output=True,
    )


def test_proof_parser_imports_as_package_without_path_aliases():
    result = run_clean_import("import SyLoPy.source.ProofParser")
    assert result.returncode == 0, result.stderr


def test_nat_test_runner_delegates_to_shared_fixture_validator():
    script = PROJECT_PARENT / "SyLoPy" / "source" / "test_runner_NatNum.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_PARENT), str(PROJECT_PARENT / "SyLoPy" / "source")]
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "=== testProofsNat (enforced) ===" in result.stdout
    assert "6/6 proofs pass" in result.stdout


def test_core_package_modules_import_cleanly():
    result = run_clean_import(
        "import SyLoPy.source.TermLogic, "
        "SyLoPy.source.FormulaLogic, "
        "SyLoPy.source.ProofLogic, "
        "SyLoPy.source.NatThry, "
        "SyLoPy.source.SetTheory"
    )
    assert result.returncode == 0, result.stderr


def test_parser_extension_assembly_is_explicit_and_idempotent():
    result = run_clean_import(
        "from SyLoPy.source import ProofParser as parser, ProofParserPolicy as policy\n"
        "names = ('parse_formula', 'parse_surface_declaration_statement', "
        "'elaborate_compound_declaration', '_prepare_surface_lines', "
        "'split_declaration_clauses', '_split_compound_declaration_items')\n"
        "before = tuple(getattr(parser, name) for name in names)\n"
        "policy.install_parser_extensions(parser)\n"
        "after = tuple(getattr(parser, name) for name in names)\n"
        "assert after == before"
    )
    assert result.returncode == 0, result.stderr
