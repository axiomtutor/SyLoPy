"""Helpers for constructing lexical contexts during proof elaboration.

The elaborator has two kinds of state that should remain distinct:
``TheoryEnvironment`` supplies the fixed theory resources available to a
proof, while ``ProofContext`` records names introduced by that proof.  This
module provides the small bridge between those layers while the elaborator
is migrated incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from SyLoPy.source.ProofContext import ProofContext


@dataclass
class ElaborationLexicalState:
    """Lexical state owned by one elaboration pass.

    This is deliberately a thin adapter rather than a second scope system.
    ``context`` is the sole authority for proof-local visibility. The adapter
    exists so ``ProofParser._ElaborationContext`` can acquire the context
    without coupling ``ProofContext`` to theory-environment details.
    """

    context: ProofContext

    def child(self) -> "ElaborationLexicalState":
        """Return the lexical state for a nested subproof."""
        return ElaborationLexicalState(self.context.enter_subproof())

    def register_declaration(self, declaration: Any) -> None:
        """Register a proof declaration in the current lexical scope."""
        self.context.declare(declaration)

    def lookup_declaration(self, name: str) -> Optional[Any]:
        """Look up a declaration using lexical visibility rules."""
        return self.context.lookup_declaration(name)

    def bind_label(
        self,
        label: str,
        value: Any,
        *,
        kind: str = "line",
        source: Any = None,
    ) -> Any:
        """Register a proof-line label in the current lexical scope."""
        return self.context.bind_label(label, value, kind=kind, source=source)

    def lookup_label(self, label: str) -> Optional[Any]:
        """Look up a proof-line label using lexical visibility rules."""
        return self.context.lookup_label(label)


def root_context(declarations: Iterable[Any] = ()) -> ProofContext:
    """Create the root lexical context and seed it with visible declarations.

    Declarations supplied by a ``TheoryEnvironment`` are part of the initial
    proof vocabulary, so they must be present before user proof lines are
    elaborated. User declarations can then be added to this same context and
    are subject to the normal ``ProofContext`` duplicate-name rules.
    """
    context = ProofContext()
    for declaration in declarations:
        context.declare(declaration)
    return context


def root_lexical_state(declarations: Iterable[Any] = ()) -> ElaborationLexicalState:
    """Create the lexical state for a root elaboration pass."""
    return ElaborationLexicalState(root_context(declarations))


def root_context_from_environment(environment: Any) -> ProofContext:
    """Create the root lexical context from a theory environment.

    This is deliberately a small adapter rather than making ``ProofContext``
    depend on ``TheoryEnvironment``. The two objects have different roles:
    the environment supplies fixed theory resources, while the context owns
    lexical visibility during elaboration.
    """
    return root_context(getattr(environment, "declarations", ()))


def subproof_context(context: ProofContext) -> ProofContext:
    """Create the lexical context for a nested subproof."""
    return context.enter_subproof()
