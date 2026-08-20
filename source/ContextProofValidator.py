"""Proof validator backed by :mod:`ProofContext`.

This module is a compatibility layer while the legacy implementation in
``ProofLogic`` is being retired.  The important invariant is that the
validator receives *one* semantic environment for a block: the same
``ProofContext`` instance answers both declaration and proof-label queries.
``seen`` remains separate because it represents ordered proof history rather
than lexical visibility.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from .ProofContext import DuplicateBindingError, ProofContext, UnknownBindingError
from . import ProofLogic as pl


class _ContextAdapter:
    """Expose the old validator's two small scope protocols over one context.

    ``ProofValidator`` historically accepted a ``LabelScope`` and a separate
    ``DeclarationScope``.  Its rule implementation only relies on a small
    duck-typed interface, so both parameters can now be the same adapter.
    ``child()`` caches the child adapter: the legacy validator calls
    ``labels.child()`` and ``declarations.child()`` separately, and those two
    calls must nevertheless refer to the *same* lexical scope.
    """

    __slots__ = ("context", "_child")

    def __init__(self, context: ProofContext):
        self.context = context
        self._child: Optional[_ContextAdapter] = None

    def child(self) -> "_ContextAdapter":
        if self._child is None:
            self._child = _ContextAdapter(self.context.child())
        return self._child

    # DeclarationScope protocol -----------------------------------------

    def declare(self, declaration: Any) -> None:
        self.context.declare(declaration)

    def lookup(self, name: str) -> Any:
        return self.context.lookup_declaration(name)

    # LabelScope protocol ------------------------------------------------

    def __contains__(self, label: str) -> bool:
        return self.context.lookup_label(label) is not None

    def __getitem__(self, label: str) -> Any:
        return self.context.require_label(label).value

    def __setitem__(self, label: str, value: Any) -> None:
        self.context.bind_label(label, value)


class ProofValidator(pl.ProofValidator):
    """Legacy rule engine using ``ProofContext`` as its sole scope object."""

    def validate(
        self, entries: list
    ) -> Tuple[bool, Optional[pl.ValidationError], Optional[pl.SubproofRecord]]:
        seen: list = []
        context = ProofContext()
        scope = _ContextAdapter(context)

        for declaration in self.initial_declarations:
            try:
                context.declare(declaration)
            except DuplicateBindingError:
                existing = context.lookup_declaration(declaration.name)
                return False, pl._mk_error(
                    None,
                    None,
                    0,
                    pl.CATEGORY_DECLARATION_CONFLICT,
                    f"symbol '{declaration.name}' is already declared as "
                    f"{existing.kind if existing else 'another symbol kind'}",
                ), None

        # The inherited validator still has separate parameters named
        # ``labels`` and ``declarations``.  Supplying the exact same adapter
        # object for both makes them one semantic environment in practice.
        return self._validate_block(
            entries,
            None,
            seen,
            scope,
            scope,
            outer_context=seen,
        )

    def _validate_block(
        self,
        block_entries: list,
        block_label: Optional[str],
        seen: list,
        labels: _ContextAdapter,
        declarations: _ContextAdapter,
        outer_context: list,
        is_subproof: bool = False,
    ):
        """Use the legacy block/rule implementation with shared context.

        The base implementation is retained here deliberately so that the
        inference-rule semantics remain unchanged while scope ownership is
        moved to ``ProofContext``.  The only semantic adjustment is that
        declaration and label scopes are required to be the same adapter.
        """
        if labels is not declarations:
            raise TypeError("context-backed validation requires one shared scope")
        return super()._validate_block(
            block_entries,
            block_label,
            seen,
            labels,
            declarations,
            outer_context,
            is_subproof=is_subproof,
        )


__all__ = ["ProofValidator"]
