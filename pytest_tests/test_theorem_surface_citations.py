"""Citing promoted theorems that have premises, from proof text.

A theorem is cited by its title the way a rule is: bare when it has no
premises, and with the lines that state its premises when it has some --
`(Title from 4, 5)` or `(Title, 4, 5)`, in the order the theorem's premises
were taken. The justification parser cannot tell a title from a misspelled rule
name, so whoever promotes the theorems tells the parser which titles exist
(`theorem_names`): the multi-proof runner gives it the titles of the file, and
`check_proof_text` the theorems among its `rules`. A name that is no rule and no
known title, followed by citations, is still an error at parse time.
"""

import pytest

from .support import mp, pl, pp


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
    assert second[2], f"premise-carrying theorem citation failed: {second[3]}"


# --------------------------------------------------------------------------
# The justification parser
# --------------------------------------------------------------------------

TITLES = ["Pair transport"]


@pytest.mark.parametrize("text", ["Pair transport from 4, 5", "Pair transport, 4, 5"])
def test_a_known_title_is_cited_with_its_lines_like_any_rule(text):
    kind, rule, refs = pp.parse_justification(text, TITLES)
    assert (kind, refs) == ("rule", ["4", "5"])
    assert isinstance(rule, pl.NamedRulePlaceholder)
    assert rule.name == "Pair transport"


@pytest.mark.parametrize(
    "text",
    ["pair TRANSPORT from 4", "Pair-transport, 4", "pair   transport", "Pair transport"],
)
def test_a_title_is_matched_like_a_rule_name_and_resolved_to_the_promoted_title(text):
    """The validator looks a placeholder up by the title the theorem was
    promoted under, so that is what the parser must hand it."""
    _kind, rule, _refs = pp.parse_justification(text, TITLES)
    assert rule.name == "Pair transport"


def test_without_titles_nothing_changes():
    with pytest.raises(ValueError, match="Unknown inference rule 'Pair transport'"):
        pp.parse_justification("Pair transport from 4, 5")
    _kind, rule, refs = pp.parse_justification("Pair transport")
    assert (rule.name, refs) == ("Pair transport", [])


def test_an_unknown_name_with_citations_is_still_an_error_when_titles_are_known():
    with pytest.raises(ValueError, match="Unknown inference rule 'Pair transprot'"):
        pp.parse_justification("Pair transprot from 4, 5", TITLES)
    with pytest.raises(ValueError, match="Unknown inference rule 'Pair transprot'"):
        pp.parse_justification("Pair transprot, 4, 5", TITLES)


def test_a_built_in_rule_name_is_never_taken_for_a_theorem_title():
    _kind, rule, refs = pp.parse_justification("Symmetry from 1", ["Symmetry"])
    assert isinstance(rule, pl.SymmetryRule)
    assert refs == ["1"]


def test_titles_that_differ_only_in_spelling_cite_nothing_unless_written_exactly():
    titles = ["Pair Transport", "pair transport"]
    assert pp.parse_justification("Pair Transport from 4", titles)[1].name == "Pair Transport"
    assert pp.parse_justification("pair transport from 4", titles)[1].name == "pair transport"
    with pytest.raises(ValueError, match="Unknown inference rule"):
        pp.parse_justification("PAIR TRANSPORT from 4", titles)


def test_a_lone_string_is_one_title_not_its_characters():
    assert pp.parse_justification("Pair transport from 4", "Pair transport")[1].name == "Pair transport"


# --------------------------------------------------------------------------
# Multi-proof files
# --------------------------------------------------------------------------

PAIR_TRANSPORT = """
# 1: Pair transport
## Proof that
### then P(a) and Q(a).

1. Let a be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(a). (Premise)
5. Q(a). (Premise)
6. P(a) and Q(a). (Conjunction Introduction from 4, 5)
"""


def _use_pair_transport(justification):
    return PAIR_TRANSPORT + f"""
# 2: Use pair transport
## Proof that
### then P(b) and Q(b).

1. Let b be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(b). (Premise)
5. Q(b). (Premise)
6. P(b) and Q(b). ({justification})
"""


def _run(text):
    results = mp.run_multi_proof_file(
        text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    return {number: (ok, message) for number, _expected, ok, message, _crashed in results}


@pytest.mark.parametrize(
    "justification",
    [
        "Pair transport from 4, 5",
        "Pair transport, 4, 5",
        "pair transport from 4, 5",
    ],
)
def test_a_theorem_is_cited_with_the_lines_that_state_its_premises(justification):
    outcome = _run(_use_pair_transport(justification))
    assert outcome["1"][0], outcome["1"]
    assert outcome["2"][0], outcome["2"]


@pytest.mark.parametrize(
    "justification, complaint",
    [
        # The lines go in the order the theorem's premises were taken.
        ("Pair transport from 5, 4", "does not justify"),
        # Lines that do not state the premises.
        ("Pair transport from 4, 4", "does not justify"),
        # A theorem with premises needs them all, and only them.
        ("Pair transport from 4", "requires exactly 2 candidate premise(s)"),
        ("Pair transport", "requires exactly 2 candidate premise(s)"),
        ("Pair transport from 4, 5, 4", "requires at most 2 cited line label(s)"),
    ],
)
def test_a_citation_that_does_not_supply_the_premises_is_refused(justification, complaint):
    ok, message = _run(_use_pair_transport(justification))["2"]
    assert not ok
    assert "Line 6" in message
    assert complaint in message


def test_a_misspelled_title_is_an_error_when_the_proof_is_parsed():
    ok, message = _run(_use_pair_transport("Pair transprot from 4, 5"))["2"]
    assert not ok
    assert "Unknown inference rule 'Pair transprot'" in message


def test_a_title_is_citable_only_once_its_proof_has_been_promoted():
    """Knowing a title lets a proof be parsed; the proof still has to have
    the theorem, and gets it only from a proof that was checked before it."""
    later = """
# 1: Cites a later proof
## Proof that
### then P(b) and Q(b).

1. Let b be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(b). (Premise)
5. Q(b). (Premise)
6. P(b) and Q(b). (Pair transport from 4, 5)
""" + PAIR_TRANSPORT.replace("# 1: Pair transport", "# 2: Pair transport")
    outcome = _run(later)
    assert not outcome["1"][0]
    assert "no rule named 'Pair transport'" in outcome["1"][1]
    assert outcome["2"][0], outcome["2"]

    unproved = PAIR_TRANSPORT.replace(
        "6. P(a) and Q(a). (Conjunction Introduction from 4, 5)",
        "6. P(a) and Q(a). (Conjunction Introduction from 4)",
    )
    use = _use_pair_transport("Pair transport from 4, 5").split("# 2: Use pair transport")[1]
    outcome = _run(unproved + "\n# 2: Use pair transport" + use)
    assert not outcome["1"][0]
    assert not outcome["2"][0]
    assert "no rule named 'Pair transport'" in outcome["2"][1]


def test_a_theorem_proved_from_a_cited_theorem_can_itself_be_cited():
    chain = _use_pair_transport("Pair transport from 4, 5") + """
# 3: Use it again
## Proof that
### then P(c) and Q(c).

1. Let c be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(c). (Premise)
5. Q(c). (Premise)
6. P(c) and Q(c). (Use pair transport from 4, 5)
"""
    outcome = _run(chain)
    assert all(ok for ok, _message in outcome.values()), outcome


# --------------------------------------------------------------------------
# The Python API
# --------------------------------------------------------------------------

USE_TEXT = """1. Let b be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(b). (Premise)
5. Q(b). (Premise)
6. P(b) and Q(b). (Pair transport from 4, 5)
"""


def _promoted_pair_transport():
    entries, _ = pp.parse_proof_text(
        PAIR_TRANSPORT.split("## Proof that\n### then P(a) and Q(a).\n")[1]
    )
    proof = pl.Proof(entries)
    ok, error = proof.check_detailed()
    assert ok, error
    return pl.promote_theorem("Pair transport", proof)


def test_check_proof_text_cites_the_theorems_among_its_rules():
    theorem = _promoted_pair_transport()
    ok, error = pp.check_proof_text(USE_TEXT, rules=pl.default_rules() + [theorem])
    assert ok, error


def test_parse_proof_text_cites_the_titles_it_is_given():
    theorem = _promoted_pair_transport()
    entries, _ = pp.parse_proof_text(USE_TEXT, theorem_names=[theorem.name])
    ok, error = pl.Proof(entries, rules=pl.default_rules() + [theorem]).check_detailed()
    assert ok, error


def test_a_title_the_proof_has_no_theorem_for_is_a_validation_error():
    ok, error = pp.check_proof_text(USE_TEXT, theorem_names=["Pair transport"])
    assert not ok
    assert error.label == "6"
    assert error.category == pl.CATEGORY_UNRECOGNIZED_RULE


def test_a_title_nobody_gave_is_a_parse_error_through_the_api():
    with pytest.raises(ValueError, match="Unknown inference rule 'Pair transport'"):
        pp.check_proof_text(USE_TEXT)
