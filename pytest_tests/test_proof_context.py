"""Unit tests for the standalone `ProofContext` module.

These tests cover the lexical API itself. Elaboration and `ProofValidator`
do not yet use `ProofContext`; they still maintain their own scope tables.
"""

import pytest

from SyLoPy.source.ProofContext import (
    ArbitraryBinding,
    AssumptionBinding,
    DuplicateBindingError,
    LabelBinding,
    ProofContext,
    TheoremBinding,
    UnknownBindingError,
)
from SyLoPy.source.ProofLogic import Declaration, DeclarationKind


def test_child_inherits_parent_bindings_without_mutating_parent():
    root = ProofContext()
    declaration = Declaration("A", DeclarationKind.CLOSED_FORMULA)
    root.declare(declaration)
    root.bind_label("1", "A")
    root.bind_theorem("T", "A")
    root.assume("A", label="a")

    child = root.child()

    assert child.parent is root
    assert child.depth == 1
    assert child.lookup_declaration("A") is declaration
    assert child.lookup_label("1").value == "A"
    assert child.lookup_theorem("T").value == "A"
    assert child.lookup_assumption("a").formula == "A"

    child.bind_label("2", "B")
    child.bind_theorem("U", "B")
    child.assume("B", label="b")

    assert root.lookup_label("2") is None
    assert root.lookup_theorem("U") is None
    assert root.lookup_assumption("b") is None


def test_nested_scopes_do_not_leak_local_bindings():
    root = ProofContext()
    child = root.child()
    grandchild = child.child()

    child.bind_arbitrary("x")
    grandchild.bind_label("3.1", "P")

    assert grandchild.is_arbitrary("x")
    assert not root.is_arbitrary("x")
    assert child.lookup_label("3.1") is None
    assert root.lookup_label("3.1") is None


def test_labels_are_explicitly_scoped():
    root = ProofContext()
    root.bind_label("1", "P")
    child = root.child()
    child.bind_label("1.1", "Q")

    assert root.lookup_label("1").value == "P"
    assert root.lookup_label("1.1") is None
    assert child.lookup_label("1").value == "P"
    assert child.lookup_label("1.1").value == "Q"


def test_visible_bindings_are_reported_nearest_scope_first():
    root = ProofContext()
    root.bind_label("1", "P")
    root.bind_theorem("T", "P")
    root.declare(Declaration("P", DeclarationKind.CLOSED_FORMULA))

    child = root.child()
    child.bind_label("2", "Q")
    child.bind_theorem("U", "Q")
    child.declare(Declaration("Q", DeclarationKind.CLOSED_FORMULA))

    assert [b.label for b in child.visible_labels()] == ["2", "1"]
    assert [b.name for b in child.visible_theorems()] == ["U", "T"]
    assert [d.name for d in child.visible_declarations()] == ["Q", "P"]


def test_duplicate_names_cannot_shadow_any_visible_binding():
    root = ProofContext()
    root.declare(Declaration("A", DeclarationKind.CLOSED_FORMULA))
    child = root.child()

    with pytest.raises(DuplicateBindingError):
        child.bind_label("A", "A")
    with pytest.raises(DuplicateBindingError):
        child.bind_theorem("A", "A")
    with pytest.raises(DuplicateBindingError):
        child.assume("A", label="A")
    with pytest.raises(DuplicateBindingError):
        child.bind_arbitrary("A")
    with pytest.raises(DuplicateBindingError):
        child.declare(Declaration("A", DeclarationKind.CLOSED_FORMULA))


def test_label_binding_and_theorem_binding_have_distinct_semantics():
    context = ProofContext()
    label = context.bind_label("1", "formula", kind="line")
    theorem = context.bind_theorem("T", "formula", kind="lemma")

    assert isinstance(label, LabelBinding)
    assert label.kind == "line"
    assert isinstance(theorem, TheoremBinding)
    assert theorem.kind == "lemma"
    assert context.lookup_label("1") is label
    assert context.lookup_theorem("T") is theorem


def test_assumptions_preserve_label_and_formula():
    context = ProofContext()
    assumption = context.assume("P", label="2.1", kind="case")

    assert isinstance(assumption, AssumptionBinding)
    assert assumption.label == "2.1"
    assert assumption.formula == "P"
    assert assumption.kind == "case"
    assert context.has_assumption("P")


def test_unlabelled_assumptions_are_still_tracked():
    context = ProofContext()
    context.assume("P")
    context.assume("Q")

    assert [a.formula for a in context.assumptions_here()] == ["P", "Q"]
    assert context.has_assumption("P")
    assert context.has_assumption("Q")


def test_arbitrary_bindings_are_explicit_and_inherited():
    context = ProofContext()
    binding = context.bind_arbitrary("x", value="x-value")
    child = context.child()

    assert isinstance(binding, ArbitraryBinding)
    assert child.lookup_arbitrary("x") is binding
    assert child.is_arbitrary("x")


def test_require_methods_distinguish_missing_bindings():
    context = ProofContext()

    with pytest.raises(UnknownBindingError):
        context.require_label("1")
    with pytest.raises(UnknownBindingError):
        context.require_theorem("T")
    with pytest.raises(UnknownBindingError):
        context.require_declaration("A")


def test_names_are_validated():
    context = ProofContext()

    with pytest.raises(ValueError):
        context.bind_label(" ", "P")
    with pytest.raises(ValueError):
        context.bind_theorem("", "P")
    with pytest.raises(ValueError):
        context.lookup_label("")
