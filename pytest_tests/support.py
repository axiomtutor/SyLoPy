


"""Shared imports and small AST constructors for the SyLoPy test suite.

The aliases are intentional: the current source mixes package-qualified imports
(`SyLoPy.source.FormulaLogic`) with top-level imports (`FormulaLogic`).  Binding
the top-level names to the package modules lets behavioral tests exercise one
coherent set of AST classes.  Separate import-contract tests run in clean
subprocesses and document the packaging defect without this compatibility layer.
"""
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

# Compatibility aliases for ProofParser's unqualified imports.
sys.modules["TermLogic"] = tl
sys.modules["FormulaLogic"] = fl
sys.modules["ProofLogic"] = pl
pp = importlib.import_module("SyLoPy.source.ProofParser")

# Compatibility aliases for MultiproofParser's erroneous SyLoPy.tests imports.
tests_pkg = importlib.import_module("SyLoPy.tests")
for name, module in (("TermLogic", tl), ("FormulaLogic", fl), ("ProofLogic", pl), ("ProofParser", pp)):
    setattr(tests_pkg, name, module)
    sys.modules[f"SyLoPy.tests.{name}"] = module
mp = importlib.import_module("SyLoPy.source.MultiproofParser")


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
    """`declarations`, extended with everything `pl.infer_declarations` can
    derive from `premises`, `axioms`, and every formula in `entries`, when
    `auto_declare` is set.

    `ProofLogic.Proof` requires every symbol to be declared unconditionally
    now (see `ProofValidator`) -- there is no `require_declared_constants`
    toggle to skip that check. Most of this suite is testing rule mechanics
    with bare propositions (`A`, `B`, ...), not declaration scoping itself
    (that has its own dedicated tests below), so `assert_valid`/
    `assert_invalid` auto-declare by default -- the equivalent of a real
    proof adding `(Declare)` lines for everything it uses. Tests that
    specifically exercise undeclared-symbol rejection pass
    `auto_declare=False` to keep constructing a `Proof` that hasn't had its
    symbols pre-declared.
    """
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




