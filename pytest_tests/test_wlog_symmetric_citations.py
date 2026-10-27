"""WLOG replay keeps a cited outside line that treats both cases alike (issue #75).

When WLOG replays its region for another case, a line cited from outside the
region is replaced by the visible line that says the same thing of the new case
(`P(x)` becomes `P(y)`). If no such line exists the replay used to fail on the
spot. That refused the usual proof: after `WLOG x = a` the pair characterization
`forall u, (In(u, Y) iff (u = a or u = b))` is cited, and the replay for
`x = b` needs that very line, not one saying `u = b or u = b`.

A cited line is now kept, and the replayed line is checked against it as
usual, when exchanging the two case constants leaves it unchanged (up to the
order of `and` and `or`): it is background that holds equally in both cases.
A line that is not like that, such as `P(a)` or `P(a) and R(b)`, still needs a
counterpart, and a line that is kept is still judged by the rule that cites it.
"""

from pathlib import Path

from .support import mp, pl, pp, st

PROJECT = Path(__file__).resolve().parents[1]


def _check(text):
    entries, _ = pp.parse_proof_text(text)
    return entries, pl.Proof(entries).check_detailed()


def _accepted(text):
    _entries, (ok, err) = _check(text)
    assert ok, err


def _refused(text):
    _entries, (ok, err) = _check(text)
    assert not ok
    assert err is not None
    return err


# --------------------------------------------------------------------------
# The pair characterization, which is what the issue reported
# --------------------------------------------------------------------------

PAIR_SET = """1. Let a be any set. (Declaration)
2. Let b be any set. (Declaration)
3. Let x be any set. (Declaration)
4. Let Y be any set. (Declaration)
5. forall u, (In(u, Y) iff (u = a or u = b)). (Premise)
6. x = a or x = b. (Premise)
7. x = a. (WLOG from 6)
8. In(x, Y). (Set property from 5, 7)
"""


def test_the_pair_characterization_is_cited_again_in_the_replay():
    entries, (ok, err) = _check(PAIR_SET)
    assert ok, err
    # The proof as written is not rewritten by the replay.
    assert entries[-1][2][2] == ["5", "7"]


def test_the_pair_characterization_is_cited_again_for_each_of_three_cases():
    _accepted("""1. Let a be any set. (Declaration)
2. Let b be any set. (Declaration)
3. Let c be any set. (Declaration)
4. Let x be any set. (Declaration)
5. Let Y be any set. (Declaration)
6. forall u, (In(u, Y) iff (u = a or u = b or u = c)). (Premise)
7. x = a or x = b or x = c. (Premise)
8. x = a. (WLOG from 7)
9. In(x, Y). (Set property from 6, 8)
""")


def test_a_set_that_leaves_out_one_of_three_cases_is_refused_at_that_case():
    # Y = {a, b} says as much of b as of a, so the replay for x = b is fine,
    # but it says nothing of c: the replay for x = c has no line to cite.
    err = _refused("""1. Let a be any set. (Declaration)
2. Let b be any set. (Declaration)
3. Let c be any set. (Declaration)
4. Let x be any set. (Declaration)
5. Let Y be any set. (Declaration)
6. forall u, (In(u, Y) iff (u = a or u = b)). (Premise)
7. x = a or x = b or x = c. (Premise)
8. x = a. (WLOG from 7)
9. In(x, Y). (Set property from 6, 8)
""")
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.label == "9"
    assert "no visible counterpart" in err.detail


def test_a_set_that_has_only_one_of_the_two_cases_is_refused():
    # Y = {a, c} has a but not b: exchanging a and b does not give the same
    # line, and nothing else states what the replay for x = b needs.
    err = _refused("""1. Let a be any set. (Declaration)
2. Let b be any set. (Declaration)
3. Let c be any set. (Declaration)
4. Let x be any set. (Declaration)
5. Let Y be any set. (Declaration)
6. forall u, (In(u, Y) iff (u = a or u = c)). (Premise)
7. x = a or x = b. (Premise)
8. x = a. (WLOG from 7)
9. In(x, Y). (Set property from 6, 8)
""")
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.label == "9"
    assert "no visible counterpart" in err.detail


# --------------------------------------------------------------------------
# Other lines that treat the cases alike
# --------------------------------------------------------------------------

# `P(a) and P(b)` becomes `P(b) and P(b)` when a is replaced by b, and no line
# says that; exchanging a and b gives `P(b) and P(a)`, which is the same line.
SYMMETRIC_PREMISES = """1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. Let H be a closed formula. (Declaration)
7. Let K be a closed formula. (Declaration)
8. P(a) and P(b). (Premise)
9. (P(a) and P(b)) -> Q. (Premise)
10. x = a or x = b. (Premise)
"""


def test_a_conjunction_that_the_exchange_leaves_alone_is_kept():
    _accepted(SYMMETRIC_PREMISES + """11. x = a. (WLOG from 10)
12. Q. (Modus Ponens from 8, 9)
""")


def test_a_kept_citation_inside_a_subproof_that_ends_a_line_of_the_region():
    _accepted(SYMMETRIC_PREMISES + """11. x = a. (WLOG from 10)
12. H -> Q. (Conditional Introduction from subproof below)
begin subproof
 12.1. H. (Assumption for Conditional Introduction)
 12.2. Q. (Modus Ponens from 8, 9)
end subproof
""")


def test_a_kept_citation_inside_standalone_blocks_of_the_region():
    # Disjunction Elimination can take its cases as standalone subproof
    # blocks (labels 13 and 14), a different shape from the subproof that
    # ends a line, and the replay walks those as well.
    _accepted(SYMMETRIC_PREMISES + """11. H or K. (Premise)
12. x = a. (WLOG from 10)
13. begin subproof
 13.1. H. (Assumption)
 13.2. Q. (Modus Ponens from 8, 9)
end subproof
14. begin subproof
 14.1. K. (Assumption)
 14.2. Q. (Modus Ponens from 8, 9)
end subproof
15. Q. (Disjunction Elimination from 11, 13, 14)
""")


def test_a_counterpart_is_still_preferred_to_keeping_a_symmetric_line():
    # Line 7 treats both cases alike, and line 8 is also what it becomes when
    # a is replaced by b. The replay cites line 8, as it did before a line
    # could be kept: with line 7 kept instead, line 15 would be read against
    # `(P(b) and P(b)) -> R(b)`, whose antecedent is not `P(a) and P(b)`.
    _accepted("""1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let R be a predicate. (Declaration)
6. Let Q be a closed formula. (Declaration)
7. P(a) and P(b). (Premise)
8. P(b) and P(b). (Premise)
9. (P(a) and P(b)) -> R(a). (Premise)
10. (P(b) and P(b)) -> R(b). (Premise)
11. R(a) -> Q. (Premise)
12. R(b) -> Q. (Premise)
13. x = a or x = b. (Premise)
14. x = a. (WLOG from 13)
15. R(a). (Modus Ponens from 7, 9)
16. Q. (Modus Ponens from 15, 11)
""")


# --------------------------------------------------------------------------
# What is still refused
# --------------------------------------------------------------------------

def _refused_for_lack_of_a_counterpart(text, label):
    err = _refused(text)
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.label == label
    assert "no visible counterpart" in err.detail


def test_a_conjunction_that_favours_one_case_still_needs_its_counterpart():
    # `P(a) and R(b)` is not what `P(b) and R(a)` says, and no line says that.
    _refused_for_lack_of_a_counterpart("""1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let R be a predicate. (Declaration)
6. P(a) and R(b). (Premise)
7. x = a or x = b. (Premise)
8. x = a. (WLOG from 7)
9. P(a). (Conjunction Elimination from 6)
""", "9")


def test_a_conjunction_about_only_one_case_constant_still_needs_its_counterpart():
    # Exchanging a and b turns `P(a) and P(c)` into `P(b) and P(c)`.
    _refused_for_lack_of_a_counterpart("""1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let c be any object. (Declaration)
4. Let x be any object. (Declaration)
5. Let P be a predicate. (Declaration)
6. P(a) and P(c). (Premise)
7. x = a or x = b. (Premise)
8. x = a. (WLOG from 7)
9. P(a). (Conjunction Elimination from 6)
""", "9")


def test_a_citation_without_a_counterpart_is_refused_inside_a_subproof_that_ends_a_line():
    # The same decision is made inside the subproofs of the region.
    _refused_for_lack_of_a_counterpart("""1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. Let H be a closed formula. (Declaration)
7. P(a). (Premise)
8. P(a) -> Q. (Premise)
9. x = a or x = b. (Premise)
10. x = a. (WLOG from 9)
11. H -> Q. (Conditional Introduction from subproof below)
begin subproof
 11.1. H. (Assumption for Conditional Introduction)
 11.2. Q. (Modus Ponens from 7, 8)
end subproof
""", "11.2")


def test_a_citation_without_a_counterpart_is_refused_inside_standalone_blocks():
    _refused_for_lack_of_a_counterpart("""1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. Let H be a closed formula. (Declaration)
7. Let K be a closed formula. (Declaration)
8. P(a). (Premise)
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
""", "13.2")


def test_a_kept_citation_is_still_checked_by_the_rule_that_cites_it():
    # Line 12 is a good use of the symmetric line 9 in the case x = a. In the
    # replay for x = b the conjunction built on line 11 reads `P(b) and P(b)`,
    # which is not what line 9 needs, and Modus Ponens says so at line 12.
    err = _refused("""1. Let a be any object. (Declaration)
2. Let b be any object. (Declaration)
3. Let x be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. P(a). (Premise)
7. P(b). (Premise)
8. (P(a) and P(b)) -> Q. (Premise)
9. x = a or x = b. (Premise)
10. x = a. (WLOG from 9)
11. P(a) and P(b). (Conjunction Introduction from 6, 7)
12. Q. (Modus Ponens from 11, 8)
""")
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.label == "12"


# --------------------------------------------------------------------------
# The proof the issue is about, whole
# --------------------------------------------------------------------------

def test_unique_pairing_proved_with_wlog_in_each_inclusion():
    # tests/testSetTheory/unique_pairing_with_wlog.txt, also an enforced fixture.
    text = (PROJECT / "tests" / "testSetTheory" / "unique_pairing_with_wlog.txt").read_text()
    results = mp.run_multi_proof_file(
        text,
        axioms=st.SET_THEORY_ENVIRONMENT.axioms,
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules,
    )
    assert [(number, ok, msg) for number, _expected, ok, msg, _crashed in results] == [("1", True, None)]
