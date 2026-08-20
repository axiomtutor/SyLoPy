from SyLoPy.source import ProofLogic as pl
from SyLoPy.source.ContextProofValidator import ProofValidator as ContextProofValidator
from SyLoPy.source.ProofContext import ProofContext


def test_public_proof_validator_is_context_backed():
    assert pl.ProofValidator is ContextProofValidator


def test_context_adapter_uses_one_child_for_both_legacy_scope_views():
    # The legacy validator asks the label and declaration arguments for a
    # child independently.  The adapter must make those requests identify
    # the same lexical environment.
    from SyLoPy.source.ContextProofValidator import _ContextAdapter

    root = _ContextAdapter(ProofContext())
    assert root.child() is root.child()
    assert root.child().context.parent is root.context


def test_validator_keeps_declarations_and_labels_in_one_namespace():
    declaration = pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA)
    validator = pl.ProofValidator([], [], [], [declaration])

    # A proof line cannot reuse a declaration's name as a label: both are
    # bindings in the same ProofContext.
    phi = pl.fl.AtomicFormula("A", [])
    entries = [("A", phi, ("premise",))]
    ok, error, _ = validator.validate(entries)

    assert not ok
    assert error is not None
    assert error.category == pl.CATEGORY_DECLARATION_CONFLICT
