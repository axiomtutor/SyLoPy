from SyLoPy.source.ProofElaborationContext import root_context, subproof_context
from SyLoPy.source.ProofLogic import Declaration


def test_root_context_seeds_environment_declarations():
    declaration = Declaration("A", "object")
    context = root_context([declaration])

    assert context.lookup_declaration("A") is declaration


def test_subproof_context_inherits_but_does_not_leak_bindings():
    outer = root_context()
    outer.bind_arbitrary("x")

    inner = subproof_context(outer)
    inner.bind_arbitrary("y")

    assert inner.is_arbitrary("x")
    assert inner.is_arbitrary("y")
    assert not outer.is_arbitrary("y")
