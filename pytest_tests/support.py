"""Shared imports and small AST constructors for the SyLoPy test suite."""
from __future__ import annotations

import atexit
import importlib
import shutil
import sys
import tempfile
from pathlib import Path


def _find_project_parent() -> Path:
    """Return a directory that contains the project as a package named ``SyLoPy``.

    The code imports itself as ``SyLoPy.source...``, so some directory on
    ``sys.path`` must contain an entry called ``SyLoPy``. Normally that is the
    parent of the checkout. If the checkout has any other name (``sylopy``,
    ``SyLoPy-main``, a CI workspace, ...), a temporary directory holding a
    ``SyLoPy`` symlink to the real root is used instead.
    """
    root = next(
        (c for c in Path(__file__).resolve().parents if (c / "source" / "ProofLogic.py").exists()),
        None,
    )
    if root is None:
        raise RuntimeError("Could not locate source/ProofLogic.py above pytest_tests/")
    if root.name == "SyLoPy":
        return root.parent
    alias_parent = Path(tempfile.mkdtemp(prefix="sylopy-alias-"))
    atexit.register(shutil.rmtree, alias_parent, ignore_errors=True)
    (alias_parent / "SyLoPy").symlink_to(root, target_is_directory=True)
    return alias_parent


PROJECT_PARENT = _find_project_parent()
if str(PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(PROJECT_PARENT))

tl = importlib.import_module("SyLoPy.source.TermLogic")
fl = importlib.import_module("SyLoPy.source.FormulaLogic")
pl = importlib.import_module("SyLoPy.source.ProofLogic")
nt = importlib.import_module("SyLoPy.source.NatThry")
numt = importlib.import_module("SyLoPy.source.NumberTheory")
st = importlib.import_module("SyLoPy.source.SetTheory")
pp = importlib.import_module("SyLoPy.source.ProofParser")

# The fixture runner owns the #N multi-proof container format. There is no
# second parser module; the proof language itself is parsed only by ProofParser.
mp = importlib.import_module("SyLoPy.source.validate_all_proofs")


def c(name: str, value=None):
    return tl.ConstantTerm(name, name if value is None else value)


def v(name: str):
    return tl.VariableTerm(name)


def fn(name: str, *args):
    return tl.FunctionTerm(name, list(args))


def atom(name: str, *args):
    return fl.AtomicFormula(name, list(args))


def prop(name: str):
    return atom(name)


A = prop("A")
B = prop("B")
C = prop("C")
D = prop("D")
P = prop("P")
Q = prop("Q")
R = prop("R")
S = prop("S")


def _with_auto_declarations(entries, premises, axioms, declarations, auto_declare):
    """Extend declarations with symbols inferred from the proof formulas."""
    if not auto_declare:
        return declarations
    formulas = list(premises or []) + list(axioms or []) + pl.collect_formulas_from_entries(entries)
    self_declared = pl.self_declared_names_in_entries(entries)
    inferred = [d for d in pl.infer_declarations(formulas) if d.name not in self_declared]
    explicit = list(declarations or [])
    explicit_names = {d.name for d in explicit}
    return explicit + [d for d in inferred if d.name not in explicit_names]


def assert_valid(entries, *, premises=None, axioms=None, rules=None, declarations=None, auto_declare=True):
    proof = pl.Proof(
        entries,
        premises=premises,
        axioms=axioms,
        rules=rules,
        declarations=_with_auto_declarations(entries, premises, axioms, declarations, auto_declare),
    )
    ok, err = proof.check_detailed()
    assert ok, str(err)
    assert err is None


def assert_invalid(entries, category: str, *, label=None, premises=None, axioms=None, rules=None, declarations=None, auto_declare=True):
    proof = pl.Proof(
        entries,
        premises=premises,
        axioms=axioms,
        rules=rules,
        declarations=_with_auto_declarations(entries, premises, axioms, declarations, auto_declare),
    )
    ok, err = proof.check_detailed()
    assert not ok
    assert err is not None
    assert err.category == category
    if label is not None:
        assert err.label == label
    return err
