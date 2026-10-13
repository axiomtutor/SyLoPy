"""Regression probe for citing promoted theorems with premises in proof text."""

import pytest

from .support import mp


def test_premise_carrying_theorem_can_be_cited_from_proof_text():
    """A titled theorem with a premise should accept a title followed by line refs.

    The first proof promotes a rule P(a) |- P(a), generalizing over a.
    The second proof supplies P(b) and should be able to cite the title for
    the instance P(b). The direct core-API equivalent is already supported.
    """
    proof_text = """
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
4. P(b). (Property Transport from 3)
"""

    results = mp.run_multi_proof_file(
        proof_text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    assert len(results) == 2, results
    first = results[0]
    assert first[2], f"the theorem being promoted must validate: {first[3]}"

    second = results[1]
    if (
        not second[2]
        and "Unknown inference rule 'Property Transport' in justification" in second[3]
    ):
        pytest.xfail(
            "parse_justification recognizes from-lines only for built-in rule "
            "names, so it cannot parse a titled theorem cited with its premise lines"
        )

    assert second[2], f"premise-carrying theorem citation failed: {second[3]}"
