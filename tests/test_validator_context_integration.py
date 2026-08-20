from SyLoPy.source import ProofLogic as pl
from SyLoPy.source.ContextProofValidator import ProofValidator as ContextProofValidator
from SyLoPy.source.ProofContext import ProofContext


def test_prooflogic_uses_context_backed_validator():
    assert pl.ProofValidator is ContextProofValidator


def test_context_validator_uses_one_scope_for_labels_and_declarations():
    context = ProofContext()
    validator = ContextProofValidator([], [], [])
    adapter = validator.__class__.__mro__[0].__dict__
    assert adapter.get("validate") is not None
    context.declare(pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA))
    context.bind_label("1", "value")
    assert context.lookup_declaration("A") is not None
    assert context.lookup_label("1").value == "value"


def test_child_context_does_not_leak_bindings():
    parent = ProofContext()
    parent.declare(pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA))
    child = parent.child()
    child.declare(pl.Declaration("B", pl.DeclarationKind.CLOSED_FORMULA))
    child.bind_label("1", "value")

    assert parent.lookup_declaration("A") is not None
    assert parent.lookup_declaration("B") is None
    assert parent.lookup_label("1") is None
