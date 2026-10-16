"""Regression tests for citing promoted theorems from proof text."""

from .support import mp


def _run_surface_citation(citation: str):
    proof_text = f"""
# 1: Property Transport
## Proof that
### then P(a).

1. Let a be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. P(a). (Premise)
4. P(a). (Reiteration from 3)

# 2: Use Property Transport
## Proof that
### then P(b).

1. Let b be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. P(b). (Premise)
4. P(b). ({citation})
"""
    return mp.run_multi_proof_file(
        proof_text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )


def test_premise_carrying_theorem_can_be_cited_from_proof_text():
    """A titled theorem with a premise accepts a title followed by line refs."""
    results = _run_surface_citation("Property Transport from 3")
    assert len(results) == 2, results
    assert results[0][2], f"the theorem being promoted must validate: {results[0][3]}"
    assert results[1][2], f"premise-carrying theorem citation failed: {results[1][3]}"


def test_unknown_theorem_title_is_rejected_during_parsing():
    results = _run_surface_citation("Unknown Property from 3")
    assert len(results) == 2, results
    assert results[0][2], f"the source theorem must validate: {results[0][3]}"
    assert not results[1][2]
    assert "Unknown inference rule 'Unknown Property' in justification" in results[1][3]


def test_theorem_citation_rejects_undefined_premise_reference():
    results = _run_surface_citation("Property Transport from 99")
    assert len(results) == 2, results
    assert results[0][2], f"the source theorem must validate: {results[0][3]}"
    assert not results[1][2]
    assert "cites ['99']" in results[1][3]


def test_theorem_citation_rejects_malformed_reference_syntax():
    results = _run_surface_citation("Property Transport from line 3")
    assert len(results) == 2, results
    assert results[0][2], f"the source theorem must validate: {results[0][3]}"
    assert not results[1][2]
    assert "Invalid justification format" in results[1][3]
