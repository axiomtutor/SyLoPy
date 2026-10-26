"""Mutatis mutandis repeats the argument of an earlier line for other names.

    5. Q(b). (Mutatis mutandis, 4)         repeats the argument of line 4
    5. Q(b). (Mutatis mutandis, 2 to 4)    the same, and line 2 must have a counterpart

The validator does not trust the line as a rule of its own. It expands it into
the argument it stands for -- line 4's justification and the subproofs below
it, with the names that make 4 say `Q(b)` replaced, and each line cited from
outside the argument replaced by the visible line that says the same of the new
names -- and validates that expansion like any other line. These tests check the
expansion itself (what is cited, what is kept), that the line is accepted exactly
when the argument written out would be, and the refusals that no proof text
can reach.

The refused uses that a proof file can show are pinned in
test_mutatis_mutandis_reasons.py, from the fixtures.
"""

import pytest

from .support import atom, c, fl, fn, mp, pl, pp, tl, v

BARE = dict(
    axioms=mp.BARE_PROOF_AXIOMS,
    rules=mp.BARE_PROOF_RULES,
    declarations=mp.BARE_PROOF_DECLARATIONS,
)


def _check_text(text):
    entries, _ = pp.parse_proof_text(text)
    return entries, pl.Proof(entries, **BARE).check_detailed()


def _accepted(text):
    _entries, (ok, err) = _check_text(text)
    assert ok, err


def _refused(text):
    _entries, (ok, err) = _check_text(text)
    assert not ok
    assert isinstance(err, pl.ValidationError), err
    return err


def _validated(text, label, monkeypatch):
    """The entries the validator validates for line `label`, with the outcome."""
    seen = []
    real = pl.ProofValidator._validate_line

    def spy(self, entry, *args, **kwargs):
        if entry.label == label:
            seen.append(entry)
        return real(self, entry, *args, **kwargs)

    monkeypatch.setattr(pl.ProofValidator, "_validate_line", spy)
    _entries, (ok, err) = _check_text(text)
    return seen, ok, err


def _a(name, *constants):
    return atom(name, *[c(constant) for constant in constants])


def _same(formulas, expected):
    """Formulas have no structural `==`: compare a list of them with `_ast_eq`."""
    return len(formulas) == len(expected) and all(pl._ast_eq(x, y) for x, y in zip(formulas, expected))


# --------------------------------------------------------------------------
# What the line expands to
# --------------------------------------------------------------------------

SWAP = """1. Let a and b be objects. (Declare)
2. Let R and T be predicates. (Declare)
3. R(a, b) -> T(a, b). (Premise)
4. R(b, a) -> T(b, a). (Premise)
5. R(a, b). (Premise)
6. R(b, a). (Premise)
7. T(a, b). (Modus Ponens from 3, 5)
8. T(b, a). (Mutatis mutandis, 7)
"""


def test_an_exchange_cites_the_lines_that_say_the_exchanged_thing(monkeypatch):
    seen, ok, err = _validated(SWAP, "8", monkeypatch)
    assert ok, err
    (entry,) = seen
    assert entry.label == "8"
    assert pl._ast_eq(entry.phi, _a("T", "b", "a"))
    assert entry.justification[0] == "rule"
    assert entry.justification[1].name == "ModusPonens"
    # line 3 became line 4 and line 5 became line 6
    assert entry.justification[2] == ["4", "6"]


def test_the_expansion_takes_the_label_and_statement_of_the_line_not_of_the_model(monkeypatch):
    seen, ok, err = _validated(SWAP, "8", monkeypatch)
    assert ok, err
    assert [entry.label for entry in seen] == ["8"]
    assert not pl._ast_eq(seen[0].phi, _a("T", "a", "b"))


def test_the_expansion_states_the_claim_as_it_was_written_down_to_the_name_of_a_bound_variable(monkeypatch):
    text = """1. Let a, b and c be objects and R be a predicate. (Declare)
2. R(c, a). (Premise)
3. R(c, b). (Premise)
4. exists x, R(x, a). (Existential Introduction from 2)
5. exists y, R(y, b). (Mutatis mutandis, 4)
"""
    seen, ok, err = _validated(text, "5", monkeypatch)
    assert ok, err
    (entry,) = seen
    assert entry.phi.var == "y"
    # and a later line cites it as the line was written, not as line 4 was
    _accepted(text + "6. exists y, R(y, b). (Reiteration from 5)\n")


def test_the_label_of_the_line_stands_for_its_statement_afterwards():
    text = SWAP + "9. T(b, a). (Reiteration from 8)\n"
    _accepted(text)
    # line 8 says T(b, a), not what line 7 says
    err = _refused(SWAP + "9. T(a, b). (Reiteration from 8)\n")
    assert err.label == "9"
    assert "'Reiteration' does not justify" in err.detail


def test_a_one_way_replacement_cites_the_unchanged_background_and_the_new_fact(monkeypatch):
    text = """1. Let a, b be objects and P, Q be predicates such that: forall x, (P(x) -> Q(x)). (Premise)
2. P(a). (Premise)
3. P(b). (Premise)
4. Q(a). (Universal Modus Ponens from 1, 2)
5. Q(b). (Mutatis mutandis, 4)
"""
    seen, ok, err = _validated(text, "5", monkeypatch)
    assert ok, err
    (entry,) = seen
    # line 1 says nothing of a or b, so it is cited as it is; line 2 became line 3
    assert entry.justification[2] == ["1", "3"]


def test_the_earliest_line_that_says_the_new_thing_is_cited(monkeypatch):
    text = """1. Let a and b be objects and P and Q be predicates. (Declare)
2. P(a) -> Q(a). (Premise)
3. P(a). (Premise)
4. P(b) -> Q(b). (Premise)
5. P(b). (Premise)
6. P(b) -> Q(b). (Premise)
7. P(b). (Premise)
8. Q(a). (Modus Ponens from 2, 3)
9. Q(b). (Mutatis mutandis, 8)
"""
    seen, ok, err = _validated(text, "9", monkeypatch)
    assert ok, err
    assert seen[0].justification[2] == ["4", "5"]


def test_inside_an_argument_with_a_subproof_only_the_outside_citations_change(monkeypatch):
    text = """1. Let a and b be objects. (Declare)
2. Let P, Q and R be predicates. (Declare)
3. P(a) -> Q(a). (Premise)
4. Q(a) -> R(a). (Premise)
5. P(b) -> Q(b). (Premise)
6. Q(b) -> R(b). (Premise)
7. P(a) -> R(a). (Conditional Introduction from subproof below)
begin subproof
 7.1. P(a). (Assumption for Conditional Introduction)
 7.2. Q(a). (Modus Ponens from 3, 7.1)
 7.3. R(a). (Modus Ponens from 4, 7.2)
end subproof
8. P(b) -> R(b). (Mutatis mutandis, 7)
"""
    seen, ok, err = _validated(text, "8", monkeypatch)
    assert ok, err
    (entry,) = seen
    assert entry.justification[0] == "rule_below"
    assert pl._ast_eq(entry.phi, fl.Implies(_a("P", "b"), _a("R", "b")))
    # the lines inside keep the labels they have in the argument that is repeated
    assert [item[0] for item in entry.nested_subproof] == ["7.1", "7.2", "7.3"]
    assert _same([item[1] for item in entry.nested_subproof],
                 [_a("P", "b"), _a("Q", "b"), _a("R", "b")])
    # outside citations became 5 and 6; the citations of lines inside the argument did not move
    assert entry.nested_subproof[1][2][2] == ["5", "7.1"]
    assert entry.nested_subproof[2][2][2] == ["6", "7.2"]


def test_a_repeat_of_a_repeat_expands_the_repeat_that_was_checked(monkeypatch):
    text = """1. Let a, b, c be objects and P, Q be predicates such that: forall x, (P(x) -> Q(x)). (Premise)
2. P(a) -> Q(a). (Conditional Introduction from subproof below)
begin subproof
 2.1. P(a). (Assumption for Conditional Introduction)
 2.2. Q(a). (Universal Modus Ponens from 1, 2.1)
end subproof
3. P(b) -> Q(b). (Mutatis mutandis, 2)
4. P(c) -> Q(c). (Mutatis mutandis, 3)
"""
    seen, ok, err = _validated(text, "4", monkeypatch)
    assert ok, err
    (entry,) = seen
    assert pl._ast_eq(entry.phi, fl.Implies(_a("P", "c"), _a("Q", "c")))
    assert _same([item[1] for item in entry.nested_subproof], [_a("P", "c"), _a("Q", "c")])
    assert entry.nested_subproof[1][2][2] == ["1", "2.1"]


def test_an_existential_elimination_repeats_with_its_witness_and_cited_existence(monkeypatch):
    text = """1. Let a, b be objects and P, Q be predicates such that: exists x, P(x). (Premise)
2. forall x, (P(x) -> Q(a)). (Premise)
3. Let w be an object. (Declare)
4. Q(a). (Existential Elimination from 1, subproof below)
begin subproof
 4.1. P(w). (Assumption for Existential Elimination)
 4.2. P(w) -> Q(a). (Universal Instantiation from 2)
 4.3. Q(a). (Modus Ponens from 4.2, 4.1)
end subproof
5. forall x, (P(x) -> Q(b)). (Premise)
6. Q(b). (Mutatis mutandis, 4)
"""
    seen, ok, err = _validated(text, "6", monkeypatch)
    assert ok, err
    (entry,) = seen
    assert entry.justification[0] == "rule_hybrid"
    assert entry.justification[2] == ["1"]          # says nothing of a, cited as it is
    (block,) = entry.nested_subproof
    assert _same([item[1] for item in block][1:],
                 [fl.Implies(_a("P", "w"), _a("Q", "b")), _a("Q", "b")])
    assert block[1][2][2] == ["5"]                    # line 2 became line 5


# --------------------------------------------------------------------------
# Accepted exactly when the argument written out would be
# --------------------------------------------------------------------------

def _chain(premises, repeat):
    """The chain of conditionals for a, with the premises given, then `repeat`."""
    lines = ["1. Let a and b be objects. (Declare)", "2. Let P, Q and R be predicates. (Declare)"]
    lines.extend(f"{3 + index}. {premise} (Premise)" for index, premise in enumerate(premises))
    first, second = 3 + premises.index(PA_QA), 3 + premises.index(QA_RA)
    n = 3 + len(premises)
    lines += [
        f"{n}. P(a) -> R(a). (Conditional Introduction from subproof below)",
        "begin subproof",
        f" {n}.1. P(a). (Assumption for Conditional Introduction)",
        f" {n}.2. Q(a). (Modus Ponens from {first}, {n}.1)",
        f" {n}.3. R(a). (Modus Ponens from {second}, {n}.2)",
        "end subproof",
    ]
    lines += repeat(n)
    return "\n".join(lines) + "\n"


def _by_mutatis_mutandis(n):
    return [f"{n + 1}. P(b) -> R(b). (Mutatis mutandis, {n})"]


def _written_out(first, second):
    """The repeat as it would be written without Mutatis mutandis, citing the
    premise lines `first` and `second` for the facts about b."""
    def repeat(n):
        return [
            f"{n + 1}. P(b) -> R(b). (Conditional Introduction from subproof below)",
            "begin subproof",
            f" {n + 1}.1. P(b). (Assumption for Conditional Introduction)",
            f" {n + 1}.2. Q(b). (Modus Ponens from {first}, {n + 1}.1)",
            f" {n + 1}.3. R(b). (Modus Ponens from {second}, {n + 1}.2)",
            "end subproof",
        ]
    return repeat


PA_QA, QA_RA = "P(a) -> Q(a).", "Q(a) -> R(a)."
PB_QB, QB_RB = "P(b) -> Q(b).", "Q(b) -> R(b)."


@pytest.mark.parametrize("premises, written_first, written_second, accepted", [
    # the facts about b are there: the line and the written-out argument are both fine
    ([PA_QA, QA_RA, PB_QB, QB_RB], 5, 6, True),
    # they are there in another order: the line finds each where it is
    ([PB_QB, QB_RB, PA_QA, QA_RA], 3, 4, True),
    ([PA_QA, PB_QB, QA_RA, QB_RB], 4, 6, True),
    # one is missing: the argument cannot be written out, and the line is refused
    ([PA_QA, QA_RA, PB_QB], 5, 4, False),
    ([PA_QA, QA_RA, QB_RB], 3, 5, False),
    # neither is there
    ([PA_QA, QA_RA], 3, 4, False),
])
def test_the_line_is_accepted_exactly_when_the_argument_written_out_is(
        premises, written_first, written_second, accepted):
    by_the_line = _chain(premises, _by_mutatis_mutandis)
    written = _chain(premises, _written_out(written_first, written_second))
    _entries, (line_ok, line_err) = _check_text(by_the_line)
    _entries, (written_ok, written_err) = _check_text(written)
    assert line_ok == accepted, line_err
    assert written_ok == accepted, written_err
    if not accepted:
        assert line_err.category == pl.CATEGORY_BAD_REFERENCE
        assert line_err.detail.startswith("Mutatis mutandis cannot repeat line"), line_err


# --------------------------------------------------------------------------
# A name replaced by a term
# --------------------------------------------------------------------------

TERM_ARGUMENT = """1. Let a be an object and P, Q be predicates and f be a unary function such that: forall x, (P(x) -> Q(x)). (Premise)
2. P(a). (Premise)
3. P(f(a)). (Premise)
4. Q(a). (Universal Modus Ponens from 1, 2)
5. Q(f(a)). (Mutatis mutandis, 4)
"""


def test_a_term_is_stated_and_cited_where_the_name_was(monkeypatch):
    seen, ok, err = _validated(TERM_ARGUMENT, "5", monkeypatch)
    assert ok, err
    (entry,) = seen
    assert pl._ast_eq(entry.phi, atom("Q", fn("f", c("a"))))
    assert entry.justification[1].name == "UniversalModusPonens"
    # line 1 says nothing of a, so it is cited as it is; line 2 says P(a), and line 3 says P(f(a))
    assert entry.justification[2] == ["1", "3"]


SIMULTANEOUS = """1. Let a, b, c be objects and R be a predicate and g be a binary function such that: forall x, forall y, (R(x, y) -> R(g(x, y), x)). (Premise)
2. R(a, b) -> R(g(a, b), a). (Conditional Introduction from subproof below)
begin subproof
 2.1. R(a, b). (Assumption for Conditional Introduction)
 2.2. forall y, (R(a, y) -> R(g(a, y), a)). (Universal Instantiation from 1)
 2.3. R(a, b) -> R(g(a, b), a). (Universal Instantiation from 2.2)
 2.4. R(g(a, b), a). (Modus Ponens from 2.3, 2.1)
end subproof
3. R(g(a, b), c) -> R(g(g(a, b), c), g(a, b)). (Mutatis mutandis, 2)
"""


def test_the_names_are_replaced_at_once_so_a_term_is_not_replaced_again(monkeypatch):
    # a becomes g(a, b) and b becomes c: the a and b inside g(a, b) are what the term says, not names to replace
    seen, ok, err = _validated(SIMULTANEOUS, "3", monkeypatch)
    assert ok, err
    (entry,) = seen
    new_a = fn("g", c("a"), c("b"))
    assert [item[0] for item in entry.nested_subproof] == ["2.1", "2.2", "2.3", "2.4"]
    assert _same([item[1] for item in entry.nested_subproof], [
        atom("R", new_a, c("c")),
        fl.ForAll("y", fl.Implies(atom("R", new_a, v("y")), atom("R", fn("g", new_a, v("y")), new_a))),
        fl.Implies(atom("R", new_a, c("c")), atom("R", fn("g", new_a, c("c")), new_a)),
        atom("R", fn("g", new_a, c("c")), new_a),
    ])
    # the argument cites line 1 for what it says of every name, so line 1 is cited as it is
    assert entry.nested_subproof[1][2][2] == ["1"]


def test_a_repeat_for_a_term_can_be_repeated_for_a_term_of_that_term():
    _accepted("""1. Let a be an object and P be a predicate and f be a unary function such that: forall x, (P(x) -> P(f(x))). (Premise)
2. P(a) -> P(f(a)). (Conditional Introduction from subproof below)
begin subproof
 2.1. P(a). (Assumption for Conditional Introduction)
 2.2. P(f(a)). (Universal Modus Ponens from 1, 2.1)
end subproof
3. P(f(a)) -> P(f(f(a))). (Mutatis mutandis, 2)
4. P(f(f(a))) -> P(f(f(f(a)))). (Mutatis mutandis, 3)
""")


PA_QA_RA = [PA_QA, QA_RA]
PFA_QFA, QFA_RFA = "P(f(a)) -> Q(f(a)).", "Q(f(a)) -> R(f(a))."


def _chain_for_a_term(premises, repeat):
    """The chain of conditionals for a, with the premises given, then `repeat`."""
    lines = ["1. Let a be an object. (Declare)", "2. Let P, Q and R be predicates. (Declare)",
             "3. Let f be a unary function. (Declare)"]
    lines.extend(f"{4 + index}. {premise} (Premise)" for index, premise in enumerate(premises))
    first, second = 4 + premises.index(PA_QA), 4 + premises.index(QA_RA)
    n = 4 + len(premises)
    lines += [
        f"{n}. P(a) -> R(a). (Conditional Introduction from subproof below)",
        "begin subproof",
        f" {n}.1. P(a). (Assumption for Conditional Introduction)",
        f" {n}.2. Q(a). (Modus Ponens from {first}, {n}.1)",
        f" {n}.3. R(a). (Modus Ponens from {second}, {n}.2)",
        "end subproof",
    ]
    lines += repeat(n)
    return "\n".join(lines) + "\n"


def _term_by_mutatis_mutandis(n):
    return [f"{n + 1}. P(f(a)) -> R(f(a)). (Mutatis mutandis, {n})"]


def _term_written_out(first, second):
    def repeat(n):
        return [
            f"{n + 1}. P(f(a)) -> R(f(a)). (Conditional Introduction from subproof below)",
            "begin subproof",
            f" {n + 1}.1. P(f(a)). (Assumption for Conditional Introduction)",
            f" {n + 1}.2. Q(f(a)). (Modus Ponens from {first}, {n + 1}.1)",
            f" {n + 1}.3. R(f(a)). (Modus Ponens from {second}, {n + 1}.2)",
            "end subproof",
        ]
    return repeat


@pytest.mark.parametrize("premises, written_first, written_second, accepted", [
    # the facts about f(a) are there, in whatever order: the line and the written-out argument are both fine
    ([PA_QA, QA_RA, PFA_QFA, QFA_RFA], 6, 7, True),
    ([PFA_QFA, QFA_RFA, PA_QA, QA_RA], 4, 5, True),
    ([PA_QA, PFA_QFA, QA_RA, QFA_RFA], 5, 7, True),
    # one is missing, or both: the argument cannot be written out for the term, and the line is refused
    ([PA_QA, QA_RA, PFA_QFA], 6, 5, False),
    ([PA_QA, QA_RA, QFA_RFA], 4, 6, False),
    ([PA_QA, QA_RA], 4, 5, False),
])
def test_the_line_is_accepted_exactly_when_the_argument_written_out_for_the_term_is(
        premises, written_first, written_second, accepted):
    by_the_line = _chain_for_a_term(premises, _term_by_mutatis_mutandis)
    written = _chain_for_a_term(premises, _term_written_out(written_first, written_second))
    _entries, (line_ok, line_err) = _check_text(by_the_line)
    _entries, (written_ok, written_err) = _check_text(written)
    assert line_ok == accepted, line_err
    assert written_ok == accepted, written_err
    if not accepted:
        assert line_err.category == pl.CATEGORY_BAD_REFERENCE
        assert "with a by f(a):" in line_err.detail, line_err


def test_the_start_of_a_range_needs_a_counterpart_for_the_term():
    start = """1. Let a be an object and P, Q, S be predicates and f be a unary function such that: forall x, (P(x) -> Q(x)). (Premise)
2. P(a). (Premise)
3. S(a). (Premise)
4. P(f(a)). (Premise)
5. Q(a). (Universal Modus Ponens from 1, 2)
"""
    err = _refused(start + "6. Q(f(a)). (Mutatis mutandis, 3 to 5)\n")
    assert err.label == "6"
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.detail == ("Mutatis mutandis cannot start from line 3: it says S(a), and no visible line "
                          "says S(f(a)), which is what it says with a by f(a)")
    _accepted(start + "6. S(f(a)). (Premise)\n7. Q(f(a)). (Mutatis mutandis, 3 to 5)\n")


def test_a_term_that_is_not_ground_cannot_reach_the_expansion_by_any_proof_text():
    # a term with a variable is refused when the names are read off, before anything is repeated
    err = _refused("""1. Let a be an object and R be a predicate and g be a unary function. (Declare)
2. R(a, a). (Premise)
3. exists x, R(x, a). (Existential Introduction from 2)
4. exists x, R(x, g(x)). (Mutatis mutandis, 3)
""")
    assert err.label == "4"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert "which has the variable x in it" in err.detail


# --------------------------------------------------------------------------
# What is read from the statement, and what is not
# --------------------------------------------------------------------------

TWO_FACTS = """1. Let a, b, c be objects and P, T be predicates such that: forall x, (P(x) -> T(x, x)). (Premise)
2. P(a). (Premise)
3. P(b). (Premise)
4. T(a, a). (Universal Modus Ponens from 1, 2)
"""


def test_names_that_stay_the_same_are_not_reported_as_replaced():
    # R(a, b) becomes R(a, c): a stays, only b is replaced
    err = _refused("""1. Let a, b, c be objects and R, T be predicates. (Declare)
2. R(a, b) -> T(a, b). (Premise)
3. R(a, b). (Premise)
4. T(a, b). (Modus Ponens from 2, 3)
5. T(a, c). (Mutatis mutandis, 4)
""")
    assert err.label == "5"
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert "with b by c:" in err.detail and "a by a" not in err.detail


def test_a_name_is_replaced_by_one_name_wherever_it_occurs():
    # T(a, a) becomes T(b, b) in one line; in the next it would have to become T(c, a)
    err = _refused(TWO_FACTS + "5. T(b, b). (Mutatis mutandis, 4)\n6. T(c, a). (Mutatis mutandis, 4)\n")
    assert err.label == "6"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.detail == (
        "T(c, a) is not line 4, T(a, a), with names replaced: a would have to be replaced by both c and a")


def test_the_claim_may_name_a_bound_variable_differently_from_the_cited_line():
    # the model says exists z, the claim says exists u: a bound variable is not a name to replace
    _accepted("""1. Let a, b be objects and R be a predicate. (Declare)
2. R(a, a). (Premise)
3. R(b, b). (Premise)
4. exists z, R(z, a). (Existential Introduction from 2)
5. exists u, R(u, b). (Mutatis mutandis, 4)
""")


def test_a_constant_cannot_become_a_bound_variable():
    err = _refused("""1. Let a, b be objects and R be a predicate. (Declare)
2. R(a, a). (Premise)
3. R(b, b). (Premise)
4. exists x, R(x, a). (Existential Introduction from 2)
5. exists x, R(x, x). (Mutatis mutandis, 4)
""")
    assert err.label == "5"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.detail == (
        "(∃x. R(x, x)) is not line 4, (∃x. R(x, a)), with names replaced: "
        "a would have to be replaced by x, which is a variable: only a term without variables "
        "can replace a name")


def test_the_claim_is_checked_like_any_line_so_it_cannot_use_an_undeclared_name():
    err = _refused("""1. Let a be an object and P be a predicate. (Declare)
2. P(a) -> P(a). (Conditional Introduction from subproof below)
begin subproof
 2.1. P(a). (Assumption for Conditional Introduction)
 2.2. P(a). (Reiteration from 2.1)
end subproof
3. P(d) -> P(d). (Mutatis mutandis, 2)
""")
    assert err.label == "3"
    assert err.category == pl.CATEGORY_UNDECLARED_SYMBOL


def test_the_start_of_a_range_is_checked_even_when_the_argument_does_not_cite_it():
    unused = """1. Let a, b be objects and P, Q, S be predicates such that: forall x, (P(x) -> Q(x)). (Premise)
2. P(a). (Premise)
3. P(b). (Premise)
4. S(a). (Premise)
5. Q(a). (Universal Modus Ponens from 1, 2)
"""
    # one citation: only the argument of line 5 is repeated, and it never uses S(a)
    _accepted(unused + "6. Q(b). (Mutatis mutandis, 5)\n")
    # a range from line 4: S(a) must have a counterpart S(b), though line 5 does not use it
    err = _refused(unused + "6. Q(b). (Mutatis mutandis, 4 to 5)\n")
    assert err.label == "6"
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.detail.startswith("Mutatis mutandis cannot start from line 4: it says S(a), and no visible "
                                 "line says S(b)")
    # with S(b) given, the same range is fine
    _accepted("""1. Let a, b be objects and P, Q, S be predicates such that: forall x, (P(x) -> Q(x)). (Premise)
2. P(a). (Premise)
3. P(b). (Premise)
4. S(a). (Premise)
5. S(b). (Premise)
6. Q(a). (Universal Modus Ponens from 1, 2)
7. Q(b). (Mutatis mutandis, 4 to 6)
""")


def test_the_start_of_a_range_may_be_a_line_that_says_the_same_thing_of_the_new_names():
    # line 3 says it of a and b alike: the counterpart of 3, with a and b exchanged, is line 3
    _accepted("""1. Let a, b be objects and R, T be predicates. (Declare)
2. R(a, b) -> T(a, b). (Premise)
3. R(b, a) -> T(b, a). (Premise)
4. R(a, b). (Premise)
5. R(b, a). (Premise)
6. T(a, b). (Modus Ponens from 2, 4)
7. T(b, a). (Mutatis mutandis, 4 to 6)
""")


# --------------------------------------------------------------------------
# Uses of the line that no proof text can write
# --------------------------------------------------------------------------

def _entries_for(*lines):
    """Hand-built entries: a declaration, facts and then the given lines."""
    declarations = [
        pl.Declaration("a", pl.DeclarationKind.OBJECT),
        pl.Declaration("b", pl.DeclarationKind.OBJECT),
        pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Q", pl.DeclarationKind.PREDICATE, arity=1),
    ]
    base = [
        ("1", None, ("declare", declarations)),
        ("2", fl.ForAll("x", fl.Implies(atom("P", v("x")), atom("Q", v("x")))), ("premise",)),
        ("3", _a("P", "a"), ("premise",)),
        ("4", _a("P", "b"), ("premise",)),
        ("5", _a("Q", "a"), ("rule", pl.NamedRulePlaceholder("UniversalModusPonens"), ["2", "3"])),
    ]
    return base + list(lines)


MUTATIS_MUTANDIS = pl.NamedRulePlaceholder("MutatisMutandis")


def _run(entries):
    return pl.Proof(entries, **BARE).check_detailed()


def test_hand_built_entries_with_a_plain_repeat_are_accepted():
    ok, err = _run(_entries_for(("6", _a("Q", "b"), ("rule", MUTATIS_MUTANDIS, ["5"]))))
    assert ok, err


def test_a_line_without_a_label_can_repeat_a_labeled_line():
    ok, err = _run(_entries_for((_a("Q", "b"), ("rule", MUTATIS_MUTANDIS, ["5"]))))
    assert ok, err


def test_an_unlabeled_line_that_cannot_be_repeated_is_refused_without_a_label():
    entries = _entries_for((_a("Q", "b"), ("rule", MUTATIS_MUTANDIS, ["5"])))
    entries[3] = ("4", _a("P", "a"), ("premise",))      # no line says P(b) now
    ok, err = _run(entries)
    assert not ok
    assert err.label is None
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.detail.startswith("Mutatis mutandis cannot repeat line 5 with a by b: line 5 cites line 3,")


def test_a_line_inside_the_repeated_argument_without_a_label_is_named_as_such():
    # the unlabeled second line cites line 3 (P(a)) from outside the argument
    nested = [
        (_a("P", "a"), ("assume",)),
        (_a("Q", "a"), ("rule", pl.NamedRulePlaceholder("UniversalModusPonens"), ["2", "3"])),
    ]
    entries = _entries_for(
        ("6", fl.Implies(_a("P", "a"), _a("Q", "a")), ("rule_below", pl.ConditionalIntroductionRule()), nested),
    )
    # drop P(b): the repeat for b cannot cite anything for line 3
    entries[3] = ("4", _a("Q", "b"), ("premise",))
    entries.append(("7", fl.Implies(_a("P", "b"), _a("Q", "b")), ("rule", MUTATIS_MUTANDIS, ["6"])))
    ok, err = _run(entries)
    assert not ok
    assert err.label == "7"
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert "an unlabeled line cites line 3, which says P(a)" in err.detail


@pytest.mark.parametrize("justification, nested, detail", [
    # subproofs below the line
    (("rule", MUTATIS_MUTANDIS, ["5"]), [(_a("P", "b"), ("assume",))],
     "Mutatis mutandis cites lines and nothing else: it takes no subproofs and declares nothing"),
    # a declaration beside the citation
    (("rule", MUTATIS_MUTANDIS, ["5"], [pl.Declaration("w", pl.DeclarationKind.OBJECT)]), None,
     "Mutatis mutandis cites lines and nothing else: it takes no subproofs and declares nothing"),
    # the hybrid form, which is how a rule with subproofs below it is written
    (("rule_hybrid", MUTATIS_MUTANDIS, ["5"]), [[(_a("P", "b"), ("assume",))]],
     "Mutatis mutandis cites lines and nothing else: it takes no subproofs and declares nothing"),
])
def test_the_line_takes_no_subproofs_and_declares_nothing(justification, nested, detail):
    entry = ("6", _a("Q", "b"), justification) if nested is None else ("6", _a("Q", "b"), justification, nested)
    ok, err = _run(_entries_for(entry))
    assert not ok
    assert err.label == "6"
    assert err.category == pl.CATEGORY_MALFORMED_JUSTIFICATION
    assert err.detail == detail


def test_the_line_needs_a_formula_and_a_list_of_citations():
    for entry in (
        ("6", [_a("Q", "b")], ("rule", MUTATIS_MUTANDIS, ["5"])),
        ("6", _a("Q", "b"), ("rule", MUTATIS_MUTANDIS, "5")),
    ):
        ok, err = _run(_entries_for(entry))
        assert not ok
        assert err.category == pl.CATEGORY_MALFORMED_ENTRY, err
        assert err.detail == "Mutatis mutandis needs a formula and a list of cited lines"


def test_the_line_cites_at_least_one_line():
    ok, err = _run(_entries_for(("6", _a("Q", "b"), ("rule", MUTATIS_MUTANDIS, []))))
    assert not ok
    assert err.category == pl.CATEGORY_ARITY_MISMATCH
    assert err.detail.endswith("it was given []")


def test_a_premise_is_not_a_line_that_a_rule_derived_and_cannot_be_repeated():
    for model in ("2", "3", "4"):
        ok, err = _run(_entries_for(("6", _a("Q", "b"), ("rule", MUTATIS_MUTANDIS, [model]))))
        assert not ok
        assert err.label == "6"
        assert err.category == pl.CATEGORY_RULE_MISMATCH
        assert err.detail == (
            f"Mutatis mutandis repeats an argument, and line {model} is not a line that a rule derived "
            "from other lines")


def test_a_declaration_states_nothing_and_cannot_be_cited_at_all():
    ok, err = _run(_entries_for(("6", _a("Q", "b"), ("rule", MUTATIS_MUTANDIS, ["1"]))))
    assert not ok
    assert err.label == "6"
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.detail == (
        "Mutatis mutandis cites ['1'], which is not defined or not in scope at this point in the proof")


def test_an_assumption_of_an_enclosing_subproof_cannot_be_repeated():
    err = _refused("""1. Let a, b be objects and P be a predicate. (Declare)
2. P(a) -> P(b). (Conditional Introduction from subproof below)
begin subproof
 2.1. P(a). (Assumption for Conditional Introduction)
 2.2. P(b). (Mutatis mutandis, 2.1)
end subproof
""")
    assert err.label == "2.2"
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert err.detail == (
        "Mutatis mutandis repeats an argument, and line 2.1 is not a line that a rule derived from "
        "other lines")


# --------------------------------------------------------------------------
# Hypotheses are not repeated
# --------------------------------------------------------------------------

def _rule_line(label, phi, refs):
    return (label, phi, ("rule", pl.ModusPonensRule(), refs))


@pytest.mark.parametrize("inner, reason", [
    (("5.2", _a("Q", "a"), ("premise",)),
     "it is a premise (so is a witness named with 'Existence from')"),
    (("5.2", _a("Q", "a"), ("axiom",)), "it is an axiom"),
    (("5.2", _a("Q", "a"), ("mystery",)), "its justification 'mystery' is not one that can be repeated"),
    (("5.2", _a("Q", "a"), ("declare", [pl.Declaration("z", pl.DeclarationKind.OBJECT)])),
     "it declares names and states a fact about them"),
    (("5.2", _a("Q", "a"),
      ("rule", pl.ModusPonensRule(), ["5.1"], [pl.Declaration("z", pl.DeclarationKind.OBJECT)])),
     "it declares names and states a fact about them"),
    (("5.2", _a("Q", "a"),
      ("premise", [pl.Declaration("R2", pl.DeclarationKind.PREDICATE, arity=1,
                                  metadata=(("reflexive", True),))])),
     "it is a premise (so is a witness named with 'Existence from')"),
])
def test_a_repeated_argument_may_not_contain_a_hypothesis(inner, reason):
    err = pl._mm_blocked_line(("5", fl.Implies(_a("P", "a"), _a("Q", "a")),
                               ("rule_below", pl.ConditionalIntroductionRule()),
                               [("5.1", _a("P", "a"), ("assume",)), inner]))
    assert err == ("5.2", reason)


def test_a_declaration_with_structure_cannot_be_repeated():
    structured = pl.Declaration("R2", pl.DeclarationKind.PREDICATE, arity=2,
                                metadata=(("carrier", "X"), ("reflexive", True)))
    found = pl._mm_blocked_line(("5.2", None, ("declare", [structured])))
    assert found == ("5.2", "it declares structure")
    plain = pl.Declaration("w", pl.DeclarationKind.OBJECT)
    assert pl._mm_blocked_line(("5.2", None, ("declare", [plain]))) is None


def test_a_line_may_be_repeated_when_its_argument_only_derives():
    block = [
        ("5.1", _a("P", "a"), ("assume",)),
        ("5.2", _a("Q", "a"), ("rule", pl.ModusPonensRule(), ["2", "5.1"])),
        ("5.3", None, ("declare", [pl.Declaration("w", pl.DeclarationKind.OBJECT)])),
    ]
    assert pl._mm_blocked_line(
        ("5", fl.Implies(_a("P", "a"), _a("Q", "a")), ("rule_below", pl.ConditionalIntroductionRule()), block)
    ) is None


def test_the_hypothesis_is_found_in_a_nested_block_and_in_any_case_block():
    premise = ("6.1.1", _a("Q", "a"), ("premise",))
    inner_block = [("6.1", _a("P", "a"), ("assume",)),
                   ("6.2", _a("Q", "a"), ("rule_below", pl.ConditionalIntroductionRule()),
                    [("6.2.0", _a("P", "a"), ("assume",)), premise])]
    assert pl._mm_blocked_line(("6", _a("Q", "a"), ("rule_below", pl.ConditionalIntroductionRule()),
                                inner_block))[0] == "6.1.1"
    cases = [[("6.l", _a("P", "a"), ("assume",))], [("6.r", _a("Q", "a"), ("assume",)), premise]]
    assert pl._mm_blocked_line(
        ("6", _a("Q", "a"), ("rule_hybrid", pl.DisjunctionEliminationRule(), ["2"]), cases))[0] == "6.1.1"


def test_a_standalone_subproof_inside_the_argument_is_searched_too():
    block = ("5.3", "subproof", [("5.3.1", _a("P", "a"), ("assume",)), ("5.3.2", _a("Q", "a"), ("premise",))])
    found = pl._mm_blocked_line(block)
    assert found == ("5.3.2", "it is a premise (so is a witness named with 'Existence from')")


def test_a_standalone_subproof_inside_the_argument_that_only_derives_is_not_in_the_way():
    block = ("5.3", "subproof", [
        ("5.3.1", _a("P", "a"), ("assume",)),
        ("5.3.2", _a("Q", "a"), ("rule", pl.ModusPonensRule(), ["2", "5.3.1"])),
    ])
    assert pl._mm_blocked_line(block) is None
    # the same block with a premise in it is in the way, which is what the test above shows
    assert pl._mm_blocked_line(("5.3", "subproof", [block[2][0], ("5.3.2", _a("Q", "a"), ("premise",))])) is not None


def test_an_entry_that_is_not_an_entry_is_refused_with_the_reason_it_is_malformed():
    label, reason = pl._mm_blocked_line("not an entry")
    assert label is None
    assert reason == "invalid entry format"


def test_a_line_with_no_justification_cannot_be_repeated():
    assert pl._mm_blocked_line(("5.2", _a("Q", "a"), ())) == ("5.2", "it has no justification")


# --------------------------------------------------------------------------
# Reading the names off the two statements
# --------------------------------------------------------------------------

def _align(model, claim):
    sigma = {}
    pl._mm_align(model, claim, sigma, {}, {}, 0)
    return {old: repr(new) for old, new in sigma.items()}


def _refuses_to_align(model, claim):
    with pytest.raises(ValueError) as raised:
        _align(model, claim)
    return str(raised.value)


def test_a_constant_is_replaced_by_a_constant():
    assert _align(_a("P", "a"), _a("P", "b")) == {"a": "b"}


def test_two_constants_can_be_exchanged():
    assert _align(_a("R", "a", "b"), _a("R", "b", "a")) == {"a": "b", "b": "a"}


def test_a_constant_that_stays_is_recorded_as_replaced_by_itself():
    assert _align(_a("R", "a", "b"), _a("R", "a", "c")) == {"a": "a", "b": "c"}


def test_a_constant_that_occurs_twice_is_replaced_by_the_same_constant_each_time():
    assert _align(_a("R", "a", "a"), _a("R", "b", "b")) == {"a": "b"}
    assert _refuses_to_align(_a("R", "a", "a"), _a("R", "b", "c")) == (
        "a would have to be replaced by both b and c")


def test_two_constants_may_be_replaced_by_the_same_constant():
    # each name still has one replacement, and the repeated argument is checked like any other
    assert _align(_a("R", "a", "b"), _a("R", "c", "c")) == {"a": "c", "b": "c"}


def test_a_different_predicate_is_not_a_change_of_names():
    message = _refuses_to_align(_a("P", "a"), _a("Q", "a"))
    assert message == "only names may change, but P(a) would have to become Q(a)"


def test_a_different_arity_is_not_a_change_of_names():
    assert "only names may change" in _refuses_to_align(_a("P", "a"), _a("P", "a", "b"))


def test_a_different_connective_is_not_a_change_of_names():
    model = fl.And(_a("P", "a"), _a("Q", "a"))
    claim = fl.Or(_a("P", "b"), _a("Q", "b"))
    assert "only names may change" in _refuses_to_align(model, claim)


def test_the_parts_of_a_connective_are_aligned_in_order():
    model = fl.And(_a("P", "a"), _a("Q", "b"))
    assert _align(model, fl.And(_a("P", "b"), _a("Q", "a"))) == {"a": "b", "b": "a"}
    assert "only names may change" in _refuses_to_align(model, fl.And(_a("Q", "b"), _a("P", "a")))


def test_a_function_term_is_aligned_by_its_arguments():
    model = atom("P", fn("f", c("a"), c("b")))
    assert _align(model, atom("P", fn("f", c("b"), c("a")))) == {"a": "b", "b": "a"}
    assert "only names may change" in _refuses_to_align(model, atom("P", fn("g", c("a"), c("b"))))
    assert "only names may change" in _refuses_to_align(model, atom("P", fn("f", c("a"))))


def test_a_variable_must_stay_the_same_when_free():
    free_x, free_y = atom("P", v("x")), atom("P", v("y"))
    assert _align(free_x, free_x) == {}
    assert "only names may change" in _refuses_to_align(free_x, free_y)


def test_a_constant_is_replaced_by_a_term_without_variables():
    assert _align(_a("P", "a"), atom("P", fn("f", c("b")))) == {"a": "f(b)"}
    assert _align(_a("P", "a"), atom("P", fn("f", fn("g", c("b")), c("c")))) == {"a": "f(g(b), c)"}
    # a term may mention the name it replaces, or the other names that are replaced
    assert _align(_a("R", "a", "b"), atom("R", fn("f", c("a"), c("b")), c("c"))) == {"a": "f(a, b)", "b": "c"}


def test_a_name_is_replaced_by_one_term_wherever_it_occurs():
    assert _refuses_to_align(_a("R", "a", "a"), atom("R", fn("f", c("b")), fn("f", c("c")))) == (
        "a would have to be replaced by both f(b) and f(c)")
    assert _refuses_to_align(_a("R", "a", "a"), atom("R", fn("f", c("b")), c("b"))) == (
        "a would have to be replaced by both f(b) and b")


def test_a_constant_cannot_become_a_term_that_has_a_variable_in_it():
    message = _refuses_to_align(_a("P", "a"), atom("P", fn("f", c("b"), fn("g", v("x")))))
    assert message == ("a would have to be replaced by f(b, g(x)), which has the variable x in it: "
                       "only a term without variables can replace a name")
    # with several, the first in alphabetical order is named, wherever it stands in the term
    message = _refuses_to_align(_a("P", "a"), atom("P", fn("f", fn("g", v("y")), v("x"))))
    assert message == ("a would have to be replaced by f(g(y), x), which has the variable x in it: "
                       "only a term without variables can replace a name")


def test_a_constant_cannot_become_a_variable():
    message = _refuses_to_align(_a("P", "a"), atom("P", v("x")))
    assert message == ("a would have to be replaced by x, which is a variable: only a term without "
                       "variables can replace a name")


def test_a_term_is_not_replaced_by_a_constant_or_by_a_term_of_another_shape():
    assert "only names may change" in _refuses_to_align(atom("P", fn("f", c("a"))), _a("P", "a"))
    assert "only names may change" in _refuses_to_align(atom("P", fn("f", c("a"))), atom("P", fn("g", c("a"))))
    assert "only names may change" in _refuses_to_align(atom("P", fn("f", c("a"))), atom("P", fn("f", c("a"), c("b"))))


def test_bound_variables_may_have_different_names_but_must_correspond():
    one = fl.ForAll("z", fl.Implies(atom("In", v("z"), c("X")), atom("P", v("z"))))
    other = fl.ForAll("u", fl.Implies(atom("In", v("u"), c("Y")), atom("P", v("u"))))
    assert _align(one, other) == {"X": "Y"}

    # forall x, forall y, R(x, y) against forall x, forall y, R(y, x): the variables do not correspond
    nested = fl.ForAll("x", fl.ForAll("y", atom("R", v("x"), v("y"))))
    crossed = fl.ForAll("x", fl.ForAll("y", atom("R", v("y"), v("x"))))
    assert "only names may change" in _refuses_to_align(nested, crossed)
    # a bound variable is not a free one of the same name
    bound = fl.ForAll("x", atom("P", v("x")))
    assert "only names may change" in _refuses_to_align(bound, fl.ForAll("x", atom("P", c("x"))))


def test_a_quantifier_is_not_another_quantifier():
    body = atom("P", v("x"))
    assert "only names may change" in _refuses_to_align(fl.ForAll("x", body), fl.Exists("x", body))


def test_a_variable_bound_in_only_one_of_the_two_lines_is_not_a_change_of_names():
    bound = fl.ForAll("x", atom("P", v("x")))
    free_y = fl.ForAll("x", atom("P", v("y")))
    # the claim has a free variable where the cited line has a bound one, and the other way round
    assert "only names may change" in _refuses_to_align(bound, free_y)
    assert "only names may change" in _refuses_to_align(free_y, bound)
    # the cited line's x is bound; the claim's x is not, because the claim binds y
    assert "only names may change" in _refuses_to_align(bound, fl.ForAll("y", atom("P", v("x"))))


def test_a_negation_is_aligned_by_what_it_negates():
    assert _align(fl.Not(_a("P", "a")), fl.Not(_a("P", "b"))) == {"a": "b"}
    assert "only names may change" in _refuses_to_align(fl.Not(_a("P", "a")), fl.Not(_a("Q", "a")))


def test_both_sides_of_a_biconditional_are_aligned():
    iff = fl.Iff(_a("P", "a"), _a("Q", "b"))
    # each side fixes one of the two names, so an exchange needs both
    assert _align(iff, fl.Iff(_a("P", "b"), _a("Q", "a"))) == {"a": "b", "b": "a"}
    assert "only names may change" in _refuses_to_align(iff, fl.Iff(_a("R", "b"), _a("Q", "a")))
    assert "only names may change" in _refuses_to_align(iff, fl.Iff(_a("P", "b"), _a("R", "a")))


def test_both_sides_of_an_equation_are_aligned():
    equation = fl.Equals(c("a"), c("b"))
    assert _align(equation, fl.Equals(c("b"), c("a"))) == {"a": "b", "b": "a"}
    # a name may become a term on either side, but a term is not replaced by a name
    assert _align(equation, fl.Equals(fn("f", c("a")), c("a"))) == {"a": "f(a)", "b": "a"}
    assert _align(equation, fl.Equals(c("b"), fn("f", c("a")))) == {"a": "b", "b": "f(a)"}
    assert "only names may change" in _refuses_to_align(fl.Equals(fn("f", c("a")), c("b")), equation)
    assert "only names may change" in _refuses_to_align(fl.Equals(c("a"), fn("f", c("b"))), equation)


def test_the_parts_of_a_connective_must_be_as_many_as_in_the_cited_line():
    both, only = fl.And(_a("P", "a"), _a("Q", "a")), fl.And(_a("P", "b"))
    assert "only names may change" in _refuses_to_align(both, only)
    assert "only names may change" in _refuses_to_align(only, both)
    either, one = fl.Or(_a("P", "a"), _a("Q", "a")), fl.Or(_a("P", "b"))
    assert "only names may change" in _refuses_to_align(either, one)
    assert "only names may change" in _refuses_to_align(one, either)


def test_arguments_that_are_not_terms_have_to_be_equal_as_they_are():
    def raw(value):
        return fl.AtomicFormula("P", [value])

    assert _align(raw(1), raw(1)) == {}
    assert "only names may change" in _refuses_to_align(raw(1), raw(2))
    assert "only names may change" in _refuses_to_align(raw(1), atom("P", c("a")))
    assert "only names may change" in _refuses_to_align(atom("P", c("a")), raw(1))


def test_a_kind_of_formula_that_is_not_known_is_refused_unless_it_is_the_same_object():
    class Odd(fl.Formula):
        def __repr__(self):
            return "Odd"

    one = Odd()
    assert _align(one, one) == {}
    assert "only names may change" in _refuses_to_align(one, Odd())


def test_a_line_that_states_no_fact_is_described_as_a_subproof_in_a_message():
    record = pl.SubproofRecord(_a("P", "a"), [_a("Q", "a")])
    assert pl._mm_show(record) == "a subproof"
    assert pl._mm_show([_a("P", "a"), record]) == "P(a); a subproof"
    assert pl._mm_show(_a("P", "a")) == "P(a)"


def test_the_replacement_is_described_in_words():
    sigma = {"a": c("b")}
    assert pl._mm_renaming(sigma) == "a by b"
    assert pl._mm_renaming({"a": c("b"), "b": c("a")}) == "a by b and b by a"
    assert pl._mm_renaming({"a": c("b"), "b": c("c"), "c": c("a")}) == "a by b, b by c and c by a"
    assert pl._mm_renaming({"a": fn("Plus", c("a"), c("b")), "b": c("c")}) == "a by Plus(a, b) and b by c"


# --------------------------------------------------------------------------
# Finding the line to cite in place of a line outside the argument
# --------------------------------------------------------------------------

def _scope(**lines):
    scope = pl.LabelScope()
    for label, value in lines.items():
        scope[label.replace("_", ".")] = value
    return scope


def test_the_facts_of_a_line_are_the_formula_or_the_members_of_the_bundle():
    p, q = _a("P", "a"), _a("Q", "a")
    assert pl._mm_facts(p) == [p]
    assert pl._mm_facts([p, q]) == [p, q]
    record = pl.SubproofRecord(p, [q])
    assert pl._mm_facts(record) is None
    assert pl._mm_facts([p, record]) is None


def test_a_bundle_says_each_of_its_facts_and_a_fact_does_not_say_a_bundle():
    p, q, r = _a("P", "b"), _a("Q", "b"), _a("R", "b")
    bundle = [p, q, r]
    assert pl._mm_says(bundle, p, pl._mm_facts(p))
    assert pl._mm_says(bundle, [r, p], pl._mm_facts([r, p]))
    assert pl._mm_says(bundle, bundle, pl._mm_facts(bundle))
    assert not pl._mm_says(p, bundle, pl._mm_facts(bundle))
    assert not pl._mm_says(bundle, [p, _a("S", "b")], pl._mm_facts([p, _a("S", "b")]))


def test_a_bundle_says_a_fact_that_it_states_up_to_the_order_of_and_and_the_names_of_bound_variables():
    stated = fl.ForAll("z", fl.Or(atom("In", v("z"), c("Y")), atom("P", v("z"))))
    wanted = fl.ForAll("u", fl.Or(atom("P", v("u")), atom("In", v("u"), c("Y"))))
    assert pl._mm_says([_a("P", "a"), stated], wanted, pl._mm_facts(wanted))


def test_a_subproof_is_said_only_by_the_same_subproof():
    p, q = _a("P", "a"), _a("Q", "a")
    record = pl.SubproofRecord(p, [q])
    same = pl.SubproofRecord(p, [q])
    other = pl.SubproofRecord(p, [_a("R", "a")])
    assert pl._mm_says(record, same, pl._mm_facts(same))
    assert not pl._mm_says(record, other, pl._mm_facts(other))
    assert not pl._mm_says([p, q], same, pl._mm_facts(same))
    # a subproof does not say a fact, not even one of the facts it derived
    assert not pl._mm_says(record, q, pl._mm_facts(q))


def test_the_counterpart_is_the_earliest_visible_line_that_says_it():
    p, q = _a("P", "b"), _a("Q", "b")
    scope = _scope(L1=_a("P", "a"), L2=[q, p], L3=p)
    assert pl._mm_counterpart(scope, p) == "L2"
    assert pl._mm_counterpart(scope, q) == "L2"
    assert pl._mm_counterpart(scope, _a("R", "b")) is None


def test_the_counterpart_is_found_in_an_enclosing_scope():
    outer = _scope(A=_a("P", "b"))
    inner = outer.child()
    inner["B"] = _a("Q", "b")
    assert pl._mm_counterpart(inner, _a("P", "b")) == "A"
    assert pl._mm_counterpart(inner, _a("Q", "b")) == "B"
    assert pl._mm_counterpart(outer, _a("Q", "b")) is None


def test_an_empty_bundle_is_not_said_by_every_line():
    scope = _scope(A=_a("P", "b"))
    assert pl._mm_counterpart(scope, []) is None


# --------------------------------------------------------------------------
# The record of where each line came from
# --------------------------------------------------------------------------

def test_a_label_remembers_the_entry_it_was_validated_from():
    scope = pl.LabelScope()
    scope["4"] = _a("P", "a")
    entry = ("4", _a("P", "a"), ("assume",))
    scope.set_source("4", entry)
    assert scope.source_of("4") is entry


def test_an_unbound_label_has_no_source_and_cannot_be_given_one():
    scope = pl.LabelScope()
    scope.set_source("7", ("7", _a("P", "a"), ("assume",)))
    assert scope.source_of("7") is None
    assert "7" not in scope


def test_a_source_is_visible_inside_a_subproof_but_not_outside_it():
    outer = pl.LabelScope()
    outer["1"] = _a("P", "a")
    outer.set_source("1", "outer entry")
    inner = outer.child()
    inner["1.1"] = _a("Q", "a")
    inner.set_source("1.1", "inner entry")
    assert inner.source_of("1") == "outer entry"
    assert inner.source_of("1.1") == "inner entry"
    assert outer.source_of("1.1") is None


def test_a_cloned_scope_keeps_the_sources_of_every_level():
    outer = pl.LabelScope()
    outer["1"] = _a("P", "a")
    outer.set_source("1", "outer entry")
    inner = outer.child()
    inner["1.1"] = _a("Q", "a")
    inner.set_source("1.1", "inner entry")
    clone = pl._clone_label_scope(inner)
    assert clone.source_of("1") == "outer entry"
    assert clone.source_of("1.1") == "inner entry"
    clone.set_source("1.1", "changed")
    assert inner.source_of("1.1") == "inner entry"


# --------------------------------------------------------------------------
# Naming a visible line that says the same thing
# --------------------------------------------------------------------------

def test_a_bound_variable_may_be_named_differently_in_the_line_that_stands_in():
    assert pl._wlog_formula_matches(
        fl.ForAll("z", atom("P", v("z"))), fl.ForAll("u", atom("P", v("u"))))


def test_bound_variables_must_correspond_not_just_be_renamed():
    nested = fl.ForAll("x", fl.ForAll("y", atom("R", v("x"), v("y"))))
    crossed = fl.ForAll("x", fl.ForAll("y", atom("R", v("y"), v("x"))))
    assert not pl._wlog_formula_matches(nested, crossed)
    assert pl._wlog_formula_matches(nested, fl.ForAll("p", fl.ForAll("q", atom("R", v("p"), v("q")))))


def test_a_free_variable_is_not_renamed_with_the_bound_ones():
    free_y = fl.ForAll("x", atom("R", v("x"), v("y")))
    assert pl._wlog_formula_matches(free_y, fl.ForAll("z", atom("R", v("z"), v("y"))))
    assert not pl._wlog_formula_matches(free_y, fl.ForAll("z", atom("R", v("z"), v("w"))))
    assert not pl._wlog_formula_matches(free_y, fl.ForAll("z", atom("R", v("z"), v("z"))))


def test_conjuncts_and_disjuncts_may_come_in_another_order_even_below_a_quantifier():
    left = fl.ForAll("u", fl.Iff(atom("In", v("u"), c("Y")),
                                 fl.Or(fl.Equals(v("u"), c("a")), fl.Equals(v("u"), c("b")))))
    right = fl.ForAll("z", fl.Iff(atom("In", v("z"), c("Y")),
                                  fl.Or(fl.Equals(v("z"), c("b")), fl.Equals(v("z"), c("a")))))
    assert pl._wlog_formula_matches(left, right)
    both = fl.And(_a("P", "a"), _a("Q", "a"))
    assert pl._wlog_formula_matches(both, fl.And(_a("Q", "a"), _a("P", "a")))


def test_a_conditional_and_a_biconditional_are_not_read_in_the_other_direction():
    forward = fl.Implies(_a("P", "a"), _a("Q", "a"))
    backward = fl.Implies(_a("Q", "a"), _a("P", "a"))
    assert not pl._wlog_formula_matches(forward, backward)
    assert not pl._wlog_formula_matches(
        fl.Iff(_a("P", "a"), _a("Q", "a")), fl.Iff(_a("Q", "a"), _a("P", "a")))


def test_a_negation_is_matched_by_what_it_negates_in_the_same_way():
    pq = fl.And(_a("P", "a"), _a("Q", "a"))
    qp = fl.And(_a("Q", "a"), _a("P", "a"))
    assert pl._wlog_formula_matches(fl.Not(pq), fl.Not(qp))
    assert not pl._wlog_formula_matches(fl.Not(pq), fl.Not(_a("P", "a")))


def test_formulas_with_different_shapes_or_quantifiers_do_not_match():
    body = atom("P", v("x"))
    assert not pl._wlog_formula_matches(fl.ForAll("x", body), fl.Exists("x", body))
    assert not pl._wlog_formula_matches(fl.Not(_a("P", "a")), _a("P", "a"))
    assert not pl._wlog_formula_matches(fl.And(_a("P", "a")), fl.And(_a("P", "a"), _a("Q", "a")))


# --------------------------------------------------------------------------
# WLOG is not changed by it
# --------------------------------------------------------------------------

# After `a = b` is chosen, the replay for `a = c` replaces b by c. The line that
# is cited, `Q(b)`, has to be said again as `Q(c)`.
WLOG_CITING_LINES = """1. Let a, b, c be objects and P be a predicate such that: a = b or a = c. (Premise)
2. Let Q be a predicate such that: Q(b). (Premise)
3. Q(c). (Premise)
4. a = b. (WLOG, 1)
5. Q(b). (Reiteration from 2)
6. exists y, Q(y). (Existential Introduction from 5)
"""

# The same, with both facts stated on one line: a bundle that states Q(c), among
# other things, though not a line that says Q(c).
WLOG_CITING_A_BUNDLE = """1. Let a, b, c be objects and P be a predicate such that: a = b or a = c. (Premise)
2. Let Q be a predicate such that: Q(b). Q(c). (Premise)
3. a = b. (WLOG, 1)
4. Q(b). (Reiteration from 2)
5. exists y, Q(y). (Existential Introduction from 4)
"""


def test_wlog_replays_a_line_that_cites_a_fact_stated_on_a_line_of_its_own():
    _accepted(WLOG_CITING_LINES)


def test_wlog_still_needs_a_line_that_says_what_the_cited_line_says_not_a_bundle_that_states_it():
    # Mutatis mutandis takes a bundle for the line it needs when the bundle
    # states every fact the line does (case 21 of the fixture); WLOG has not
    # been taught that and keeps refusing, as it did.
    err = _refused(WLOG_CITING_A_BUNDLE)
    assert err.label == "4"
    assert err.category == pl.CATEGORY_BAD_REFERENCE
    assert err.detail == ("WLOG replay has no visible counterpart for cited line '2' "
                          "after substituting the chosen case")


# --------------------------------------------------------------------------
# A theorem proved with it
# --------------------------------------------------------------------------

def _promoted(text):
    entries, _ = pp.parse_proof_text(text)
    return pl.promote_theorem("T", pl.Proof(entries, **BARE))


def test_a_proof_that_repeats_a_line_is_promoted_to_the_theorem_the_same_proof_written_out_gives():
    written_out = SWAP.replace("8. T(b, a). (Mutatis mutandis, 7)", "8. T(b, a). (Modus Ponens from 4, 6)")
    assert written_out != SWAP
    repeated, written = _promoted(SWAP), _promoted(written_out)
    assert _same(repeated.premises, written.premises)
    assert len(repeated.premises) == 4
    assert pl._ast_eq(repeated.conclusion, written.conclusion)
    assert repeated.generalized_names == written.generalized_names == ["a", "b"]
    assert _same(repeated.required_axioms, written.required_axioms)
    assert len(repeated.required_rules) == len(written.required_rules)
