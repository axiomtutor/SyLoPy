"""WLOG replay transforms the case blocks of a `Proof by Cases` in its region.

A `Proof by Cases ... (subproofs below)` line carries one block of lines per
case. The replay for another case used to leave those blocks as written: their
formulas kept the chosen case's constant and their citations were not
remapped, so a case line that depends on the chosen case, such as
`P(a). (Substitution from 13, 8)` with line 13 reading `x = a`, was checked
against `x = b` and refused. The same reasoning written as standalone case
blocks for `Disjunction Elimination` was transformed and accepted.

The blocks are now transformed like every other part of the region, which also
means a case line is held to the same rule as any other line: a citation
outside the region needs a counterpart for the new case, or it must say the
same of both cases.

The last tests pin where a failure is placed when an entry written by hand has
no label, in each kind of subproof the replay walks.
"""

from .support import pl, pp


def _check(text):
    entries, _ = pp.parse_proof_text(text)
    return entries, pl.Proof(entries).check_detailed()


def _accepted(text):
    _entries, (ok, err) = _check(text)
    assert ok, err


def _refused_for_lack_of_a_counterpart(text, label):
    _entries, (ok, err) = _check(text)
    assert not ok
    assert err is not None
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.label == label
    assert "no visible counterpart" in err.detail


DECLARATIONS = """1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. Let H be a closed formula. (Declaration)
7. Let K be a closed formula. (Declaration)
"""


def test_a_case_line_that_depends_on_the_chosen_case_is_replayed():
    # Line 14.2.l reads `P(x)` off `x = a` (line 13) and `P(a)` (line 8). For
    # x = b it must read it off `x = b` and `P(b)` (line 9).
    _accepted(DECLARATIONS + """8. P(a). (Premise)
9. P(b). (Premise)
10. P(x) -> Q. (Premise)
11. x = a or x = b. (Premise)
12. H or K. (Premise)
13. x = a. (WLOG from 11)
14. Q. (Proof by Cases from 12, subproofs below)
begin subproof
 14.1.l. H. (Case)
 14.2.l. P(x). (Substitution from 13, 8)
 14.3.l. Q. (Modus Ponens from 14.2.l, 10)
end subproof
begin subproof
 14.1.r. K. (Case)
 14.2.r. P(x). (Substitution from 13, 8)
 14.3.r. Q. (Modus Ponens from 14.2.r, 10)
end subproof
""")


def test_the_formulas_of_a_case_line_are_substituted_as_well_as_its_citations():
    # `P(a)` becomes `P(b)` and line 9 becomes line 10, in both case blocks.
    _accepted(DECLARATIONS + """8. P(x). (Premise)
9. P(a) -> Q. (Premise)
10. P(b) -> Q. (Premise)
11. x = a or x = b. (Premise)
12. H or K. (Premise)
13. x = a. (WLOG from 11)
14. Q. (Proof by Cases from 12, subproofs below)
begin subproof
 14.1.l. H. (Case)
 14.2.l. P(a). (Substitution from 13, 8)
 14.3.l. Q. (Modus Ponens from 14.2.l, 9)
end subproof
begin subproof
 14.1.r. K. (Case)
 14.2.r. P(a). (Substitution from 13, 8)
 14.3.r. Q. (Modus Ponens from 14.2.r, 9)
end subproof
""")


def test_a_subproof_inside_a_case_block_is_replayed_too():
    _accepted(DECLARATIONS + """8. P(x). (Premise)
9. P(a) -> Q. (Premise)
10. P(b) -> Q. (Premise)
11. x = a or x = b. (Premise)
12. H or K. (Premise)
13. x = a. (WLOG from 11)
14. Q. (Proof by Cases from 12, subproofs below)
begin subproof
 14.1.l. H. (Case)
 14.2.l. H -> Q. (Conditional Introduction from subproof below)
 begin subproof
  14.2.1. H. (Assumption for Conditional Introduction)
  14.2.2. P(a). (Substitution from 13, 8)
  14.2.3. Q. (Modus Ponens from 14.2.2, 9)
 end subproof
 14.3.l. Q. (Modus Ponens from 14.1.l, 14.2.l)
end subproof
begin subproof
 14.1.r. K. (Case)
 14.2.r. P(a). (Substitution from 13, 8)
 14.3.r. Q. (Modus Ponens from 14.2.r, 9)
end subproof
""")


def test_a_case_line_citing_a_line_that_says_the_same_of_both_cases_keeps_it():
    # `P(a) and P(b)` is unchanged by trading a and b, so no counterpart is
    # needed. This holds before the case blocks were transformed as well; it
    # guards the transformation against refusing what it should keep.
    _accepted(DECLARATIONS + """8. P(a) and P(b). (Premise)
9. (P(a) and P(b)) -> Q. (Premise)
10. x = a or x = b. (Premise)
11. H or K. (Premise)
12. x = a. (WLOG from 10)
13. Q. (Proof by Cases from 11, subproofs below)
begin subproof
 13.1.l. H. (Case)
 13.2.l. Q. (Modus Ponens from 8, 9)
end subproof
begin subproof
 13.1.r. K. (Case)
 13.2.r. Q. (Modus Ponens from 8, 9)
end subproof
""")


def test_a_case_line_citing_a_line_that_favours_one_case_needs_its_counterpart():
    # As in a standalone case block: `P(a)` has no `P(b)` to stand for it.
    _refused_for_lack_of_a_counterpart(DECLARATIONS + """8. P(a). (Premise)
9. P(a) -> Q. (Premise)
10. x = a or x = b. (Premise)
11. H or K. (Premise)
12. x = a. (WLOG from 10)
13. Q. (Proof by Cases from 11, subproofs below)
begin subproof
 13.1.l. H. (Case)
 13.2.l. Q. (Modus Ponens from 8, 9)
end subproof
begin subproof
 13.1.r. K. (Case)
 13.2.r. Q. (Modus Ponens from 8, 9)
end subproof
""", "13.2.l")


def test_the_second_case_block_is_replayed_as_well_as_the_first():
    # Only the second block depends on the chosen case here.
    _refused_for_lack_of_a_counterpart(DECLARATIONS + """8. P(a). (Premise)
9. P(a) -> Q. (Premise)
10. H -> Q. (Premise)
11. x = a or x = b. (Premise)
12. H or K. (Premise)
13. x = a. (WLOG from 11)
14. Q. (Proof by Cases from 12, subproofs below)
begin subproof
 14.1.l. H. (Case)
 14.2.l. Q. (Modus Ponens from 14.1.l, 10)
end subproof
begin subproof
 14.1.r. K. (Case)
 14.2.r. Q. (Modus Ponens from 8, 9)
end subproof
""", "14.2.r")


def test_an_unlabeled_case_line_is_located_by_its_position_in_its_case_block():
    # Entries written by hand may have no label; the failure is then placed by
    # position within the block, as for any other unlabeled entry.
    entries, _ = pp.parse_proof_text(DECLARATIONS + """8. P(a). (Premise)
9. P(a) -> Q. (Premise)
10. x = a or x = b. (Premise)
11. H or K. (Premise)
12. x = a. (WLOG from 10)
13. Q. (Proof by Cases from 11, subproofs below)
begin subproof
 13.1.l. H. (Case)
 13.2.l. Q. (Modus Ponens from 8, 9)
end subproof
begin subproof
 13.1.r. K. (Case)
 13.2.r. Q. (Modus Ponens from 8, 9)
end subproof
""")
    label, phi, justification, blocks = entries[-1]
    _line_label, line_phi, line_justification = blocks[0][1]
    blocks[0][1] = (line_phi, line_justification)
    entries[-1] = (label, phi, justification, blocks)

    ok, err = pl.Proof(entries).check_detailed()
    assert not ok
    assert err.label is None
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.location == "the unlabeled entry at position 1 of the subproof at line 13"


def _without_label(entry):
    _label, phi, justification = entry
    return (phi, justification)


def test_an_unlabeled_line_in_the_block_below_a_line_is_located_by_its_position():
    entries, _ = pp.parse_proof_text(DECLARATIONS + """8. P(a). (Premise)
9. P(a) -> Q. (Premise)
10. x = a or x = b. (Premise)
11. x = a. (WLOG from 10)
12. H -> Q. (Conditional Introduction from subproof below)
begin subproof
 12.1. H. (Assumption for Conditional Introduction)
 12.2. Q. (Modus Ponens from 8, 9)
end subproof
""")
    label, phi, justification, block = entries[-1]
    block[1] = _without_label(block[1])
    entries[-1] = (label, phi, justification, block)

    ok, err = pl.Proof(entries).check_detailed()
    assert not ok
    assert err.label is None
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.location == "the unlabeled entry at position 1 of the subproof at line 12"


def test_an_unlabeled_line_in_a_standalone_block_is_located_by_its_position():
    entries, _ = pp.parse_proof_text(DECLARATIONS + """8. P(a). (Premise)
9. P(a) -> Q. (Premise)
10. H or K. (Premise)
11. x = a or x = b. (Premise)
12. x = a. (WLOG from 11)
13. begin subproof
 13.1. H. (Assumption)
 13.2. Q. (Modus Ponens from 8, 9)
end subproof
14. begin subproof
 14.1. K. (Assumption)
 14.2. Q. (Modus Ponens from 8, 9)
end subproof
15. Q. (Disjunction Elimination from 10, 13, 14)
""")
    label, marker, block = entries[-3]
    assert marker == "subproof"
    block[1] = _without_label(block[1])
    entries[-3] = (label, marker, block)

    ok, err = pl.Proof(entries).check_detailed()
    assert not ok
    assert err.label is None
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.location == "the unlabeled entry at position 1 of the subproof at line 13"
