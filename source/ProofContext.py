"""Lexical semantic context for Fitch-style proofs.

The context is deliberately independent of parsing and inference-rule
implementation. It owns the names and bindings that are visible at a point
in a proof and provides child contexts for nested proof scopes.

A child context inherits the parent's declarations, labels, theorems,
and assumptions. Bindings created in the child never become visible in the
parent. The context uses explicit namespaces rather than treating every
identifier as one global namespace:

* declarations form the vocabulary namespace;
* theorem/lemma names form the theorem namespace;
* arbitrary bindings form the term-variable namespace;
* proof-line labels and labeled assumptions share the proof-reference
  namespace.

This namespace policy is deliberately explicit so that elaboration can rely
on the context for visibility without accidentally imposing cross-category
name collisions. Declaration validation remains the responsibility of the
owner of the declaration type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional


class ContextError(Exception):
    """Base class for invalid context operations."""


class DuplicateBindingError(ContextError):
    """Raised when a name is already visible in its namespace."""


class UnknownBindingError(ContextError):
    """Raised when an explicitly required binding is not visible."""


@dataclass(frozen=True)
class LabelBinding:
    """A validated proof-line binding."""

    label: str
    value: Any
    kind: str = "line"
    source: Any = None


@dataclass(frozen=True)
class TheoremBinding:
    """A named theorem or lemma made available to later proof work."""

    name: str
    value: Any
    kind: str = "theorem"
    source: Any = None


@dataclass(frozen=True)
class AssumptionBinding:
    """An assumption introduced by a particular proof scope."""

    label: Optional[str]
    formula: Any
    kind: str = "assume"
    source: Any = None


@dataclass(frozen=True)
class ArbitraryBinding:
    """A variable/object introduced as fresh and arbitrary in a scope."""

    name: str
    value: Any = None
    kind: str = "arbitrary"
    source: Any = None


class ProofContext:
    """Lexical environment for one point in a proof.

    ``ProofContext`` is mutable within its own scope but has no operation that
    mutates an ancestor. ``child()`` and ``enter_subproof()`` therefore give
    elaboration an explicit scope transition: bindings created in the child
    disappear when that child is discarded.
    """

    __slots__ = (
        "_parent",
        "_declarations",
        "_labels",
        "_theorems",
        "_assumptions",
        "_assumption_labels",
        "_arbitrary",
    )

    def __init__(self, parent: Optional["ProofContext"] = None) -> None:
        self._parent = parent
        self._declarations: Dict[str, Any] = {}
        self._labels: Dict[str, LabelBinding] = {}
        self._theorems: Dict[str, TheoremBinding] = {}
        self._assumptions: List[AssumptionBinding] = []
        self._assumption_labels: Dict[str, AssumptionBinding] = {}
        self._arbitrary: Dict[str, ArbitraryBinding] = {}

    @property
    def parent(self) -> Optional["ProofContext"]:
        return self._parent

    @property
    def depth(self) -> int:
        depth = 0
        context = self._parent
        while context is not None:
            depth += 1
            context = context._parent
        return depth

    def child(self) -> "ProofContext":
        """Create an empty child scope inheriting this context."""
        return ProofContext(parent=self)

    def enter_subproof(self) -> "ProofContext":
        """Create the context for a nested proof scope."""
        return self.child()

    def _visible(self, table_name: str, name: str) -> Any:
        context: Optional[ProofContext] = self
        while context is not None:
            table = getattr(context, table_name)
            value = table.get(name)
            if value is not None:
                return value
            context = context._parent
        return None

    def _visible_assumption_label(self, label: str) -> Optional[AssumptionBinding]:
        context: Optional[ProofContext] = self
        while context is not None:
            binding = context._assumption_labels.get(label)
            if binding is not None:
                return binding
            context = context._parent
        return None

    def _declaration_name_available(self, name: str) -> bool:
        return self.lookup_declaration(name) is None

    def _label_name_available(self, name: str) -> bool:
        return self.lookup_label(name) is None and self.lookup_assumption(name) is None

    def _theorem_name_available(self, name: str) -> bool:
        return self.lookup_theorem(name) is None

    def _arbitrary_name_available(self, name: str) -> bool:
        return self.lookup_arbitrary(name) is None

    def _require_name(self, name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("context names must be non-empty strings")
        return name.strip()

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def declare(self, declaration: Any) -> None:
        """Add a declaration to this scope.

        Declarations may not shadow another declaration, including one in an
        ancestor scope. Other namespaces are intentionally independent.
        """
        if declaration is None or not hasattr(declaration, "name"):
            raise TypeError("declaration must expose a name")
        name = self._require_name(declaration.name)
        if not self._declaration_name_available(name):
            raise DuplicateBindingError(
                f"declaration name {name!r} is already visible"
            )
        self._declarations[name] = declaration

    def lookup_declaration(self, name: str) -> Any:
        return self._visible("_declarations", self._require_name(name))

    def declarations_here(self) -> List[Any]:
        return list(self._declarations.values())

    def visible_declarations(self) -> Iterator[Any]:
        seen = set()
        context: Optional[ProofContext] = self
        while context is not None:
            for name, declaration in context._declarations.items():
                if name not in seen:
                    seen.add(name)
                    yield declaration
            context = context._parent

    # ------------------------------------------------------------------
    # Proof-line labels
    # ------------------------------------------------------------------

    def bind_label(
        self,
        label: str,
        value: Any,
        *,
        kind: str = "line",
        source: Any = None,
    ) -> LabelBinding:
        label = self._require_name(label)
        if not self._label_name_available(label):
            raise DuplicateBindingError(
                f"proof-reference label {label!r} is already visible"
            )
        binding = LabelBinding(label, value, kind, source)
        self._labels[label] = binding
        return binding

    def lookup_label(self, label: str) -> Optional[LabelBinding]:
        return self._visible("_labels", self._require_name(label))

    def labels_here(self) -> List[LabelBinding]:
        return list(self._labels.values())

    def visible_labels(self) -> Iterator[LabelBinding]:
        seen = set()
        context: Optional[ProofContext] = self
        while context is not None:
            for name, binding in context._labels.items():
                if name not in seen:
                    seen.add(name)
                    yield binding
            context = context._parent

    # ------------------------------------------------------------------
    # Theorems / lemmas
    # ------------------------------------------------------------------

    def bind_theorem(
        self,
        name: str,
        value: Any,
        *,
        kind: str = "theorem",
        source: Any = None,
    ) -> TheoremBinding:
        name = self._require_name(name)
        if not self._theorem_name_available(name):
            raise DuplicateBindingError(
                f"theorem name {name!r} is already visible"
            )
        binding = TheoremBinding(name, value, kind, source)
        self._theorems[name] = binding
        return binding

    def lookup_theorem(self, name: str) -> Optional[TheoremBinding]:
        return self._visible("_theorems", self._require_name(name))

    def theorems_here(self) -> List[TheoremBinding]:
        return list(self._theorems.values())

    def visible_theorems(self) -> Iterator[TheoremBinding]:
        seen = set()
        context: Optional[ProofContext] = self
        while context is not None:
            for name, binding in context._theorems.items():
                if name not in seen:
                    seen.add(name)
                    yield binding
            context = context._parent

    # ------------------------------------------------------------------
    # Assumptions
    # ------------------------------------------------------------------

    def assume(
        self,
        formula: Any,
        *,
        label: Optional[str] = None,
        kind: str = "assume",
        source: Any = None,
    ) -> AssumptionBinding:
        """Record an assumption, optionally under a proof-reference label."""
        if label is not None:
            label = self._require_name(label)
            if not self._label_name_available(label):
                raise DuplicateBindingError(
                    f"proof-reference label {label!r} is already visible"
                )
        binding = AssumptionBinding(label, formula, kind, source)
        self._assumptions.append(binding)
        if label is not None:
            self._assumption_labels[label] = binding
        return binding

    def lookup_assumption(self, label: str) -> Optional[AssumptionBinding]:
        return self._visible_assumption_label(self._require_name(label))

    def assumptions_here(self) -> List[AssumptionBinding]:
        return list(self._assumptions)

    def visible_assumptions(self) -> Iterator[AssumptionBinding]:
        contexts: List[ProofContext] = []
        context: Optional[ProofContext] = self
        while context is not None:
            contexts.append(context)
            context = context._parent
        for context in contexts:
            yield from context._assumptions

    def has_assumption(self, formula: Any) -> bool:
        return any(
            binding.formula == formula for binding in self.visible_assumptions()
        )

    # ------------------------------------------------------------------
    # Arbitrary/fresh objects
    # ------------------------------------------------------------------

    def bind_arbitrary(
        self,
        name: str,
        value: Any = None,
        *,
        kind: str = "arbitrary",
        source: Any = None,
    ) -> ArbitraryBinding:
        name = self._require_name(name)
        if not self._arbitrary_name_available(name):
            raise DuplicateBindingError(
                f"arbitrary name {name!r} is already visible"
            )
        binding = ArbitraryBinding(name, value, kind, source)
        self._arbitrary[name] = binding
        return binding

    def lookup_arbitrary(self, name: str) -> Optional[ArbitraryBinding]:
        return self._visible("_arbitrary", self._require_name(name))

    def is_arbitrary(self, name: str) -> bool:
        return self.lookup_arbitrary(name) is not None

    # ------------------------------------------------------------------
    # Diagnostics / introspection
    # ------------------------------------------------------------------

    def contains(self, name: str) -> bool:
        """Return whether *name* occurs in any visible namespace."""
        name = self._require_name(name)
        return (
            self.lookup_declaration(name) is not None
            or self.lookup_label(name) is not None
            or self.lookup_theorem(name) is not None
            or self.lookup_assumption(name) is not None
            or self.lookup_arbitrary(name) is not None
        )

    def require_label(self, label: str) -> LabelBinding:
        binding = self.lookup_label(label)
        if binding is None:
            raise UnknownBindingError(f"unknown proof label {label!r}")
        return binding

    def require_declaration(self, name: str) -> Any:
        declaration = self.lookup_declaration(name)
        if declaration is None:
            raise UnknownBindingError(f"undeclared name {name!r}")
        return declaration

    def require_theorem(self, name: str) -> TheoremBinding:
        binding = self.lookup_theorem(name)
        if binding is None:
            raise UnknownBindingError(f"unknown theorem {name!r}")
        return binding

    def local_bindings(self) -> Dict[str, List[Any]]:
        """Return a diagnostic snapshot of bindings owned by this scope."""
        return {
            "declarations": list(self._declarations.values()),
            "labels": list(self._labels.values()),
            "theorems": list(self._theorems.values()),
            "assumptions": list(self._assumptions),
            "arbitrary": list(self._arbitrary.values()),
        }
