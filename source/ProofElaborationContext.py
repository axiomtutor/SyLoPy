"""Helpers for constructing lexical contexts during proof elaboration.

The elaborator has two kinds of state that should remain distinct:
``TheoryEnvironment`` supplies the fixed theory resources available to a
proof, while ``ProofContext`` records names introduced by that proof.  This
module provides the small bridge between those layers while the elaborator
is migrated incrementally.
"""

from __future__ import annotations

from typing import Iterable, Any

from SyLoPy.source.ProofContext import ProofContext


def root_context(declarations: Iterable[Any] = ()) -> ProofContext:
    """Create the root lexical context and seed it with visible declarations.

    Declarations supplied by a ``TheoryEnvironment`` are part of the initial
    proof vocabulary, so they must be present before user proof lines are
    elaborated.  User declarations can then be added to this same context
    and are subject to the normal ``ProofContext`` duplicate-name rules.
    """
    context = ProofContext()
    for declaration in declarations:
        context.declare(declaration)
    return context


def subproof_context(context: ProofContext) -> ProofContext:
    """Create the lexical context for a nested subproof."""
    return context.enter_subproof()
