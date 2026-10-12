"""Contract tests for the combined parse-and-check public API."""

from SyLoPy.source.ProofElaboration import TheoryEnvironment
from .support import fl, pl, pp, tl


def test_check_proof_text_merges_custom_environment_axioms_and_declarations():
    """The text API must validate with the resources used to parse the text."""
    axiom = fl.AtomicFormula(
        "ApiPredicate", [tl.ConstantTerm("apiObject", "apiObject")]
    )
    environment = pp.default_theory_environment().extended(
        TheoryEnvironment(
            name="check_proof_text API fixture",
            axioms=[axiom],
            declarations=[
                pl.Declaration("apiObject", pl.DeclarationKind.OBJECT),
                pl.Declaration(
                    "ApiPredicate", pl.DeclarationKind.PREDICATE, arity=1
                ),
            ],
        )
    )

    ok, error = pp.check_proof_text(
        "1. ApiPredicate(apiObject). (Axiom)\n",
        environment=environment,
    )

    assert ok, error
    assert error is None


def test_check_proof_text_preserves_structured_surface_error_location():
    """The convenience API should not turn a rule failure into a plain string."""
    text = """1. Let a, b be any set. (Declaration)
2. a = a. (Reflexivity)
3. a = b. (Symmetry from 2)
"""

    ok, error = pp.check_proof_text(text)

    assert not ok
    assert isinstance(error, pl.ValidationError)
    assert error.label == "3"
    assert error.category == pl.CATEGORY_RULE_MISMATCH
