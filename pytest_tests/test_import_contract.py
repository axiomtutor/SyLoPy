


import os
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_multiproof_parser_imports_as_package_without_aliases():
    result = run_clean_import("import SyLoPy.source.MultiproofParser")
    assert result.returncode == 0, result.stderr


def test_nat_test_runner_imports_the_existing_nat_module():
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
    assert "No module named 'NatTheory'" not in result.stderr


def test_core_package_modules_import_cleanly():
    result = run_clean_import(
        "import SyLoPy.source.TermLogic, "
        "SyLoPy.source.FormulaLogic, "
        "SyLoPy.source.ProofLogic, "
        "SyLoPy.source.NatThry, "
        "SyLoPy.source.SetTheory"
    )
    assert result.returncode == 0, result.stderr




