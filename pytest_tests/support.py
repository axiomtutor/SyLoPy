"""Shared imports and small AST constructors for the SyLoPy test suite."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _find_project_parent() -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / "SyLoPy" / "source" / "ProofLogic.py").exists():
            return candidate
        if (candidate / "source" / "ProofLogic.py").exists() and candidate.name == "SyLoPy":
            return candidate.parent
    raise RuntimeError("Could not locate SyLoPy/source/ProofLogic.py")


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
# MultiproofParser module; the proof language itself is parsed only by ProofParser.
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
