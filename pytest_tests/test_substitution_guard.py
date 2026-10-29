"""The substitution refuses a replacement term that has a variable in it.

`Mutatis mutandis`, the replay of WLOG and the citation of a promoted theorem
rewrite formulas with `_substitute_constants_in_formula`: every occurrence of a
name is replaced by a term. The routine puts the term where the name stood, as
it is -- it never renames a bound variable -- so a term with a variable in it
can only be put there unsafely. Under a quantifier that binds the variable it is
captured (`a` replaced by `x` in `forall x, R(a, x)` gives `forall x, R(x, x)`);
anywhere else the result has a free variable, which a proof line cannot have.
The routine refuses (`_UnsafeSubstitution`) rather than build either, whatever
its caller has already checked.

`Mutatis mutandis` has already refused such a term earlier (`_mm_align` names the
variable and never offers one) and WLOG replaces a name by a name, so no proof
text reaches the refusal. These tests call the routine directly, and call the
rules with their own check taken away, to see that each reports the refusal at
the line, as an ordinary refusal, and that nothing is accepted. What the routine
does for a replacement without a variable is not changed, and every refusal is
paired with a control that differs only in the variable.
"""

import pytest

from .support import atom, c, fl, fn, mp, pl, pp, v

BARE = dict(
    axioms=mp.BARE_PROOF_AXIOMS,
    rules=mp.BARE_PROOF_RULES,
    declarations=mp.BARE_PROOF_DECLARATIONS,
)


def _substitute(formula, mapping):
    return pl._substitute_constants_in_formula(formula, mapping)


def _refused(formula, mapping):
    with pytest.raises(pl._UnsafeSubstitution) as caught:
        _substitute(formula, mapping)
    return caught.value


def _same(left, right):
    return pl._ast_eq(left, right)


# --------------------------------------------------------------------------
# What is refused, in every kind of formula
# --------------------------------------------------------------------------

# The name `a` replaced in each place a name can stand, under `forall x` (or
# the quantifiers named), where `t` is whatever replaces it.
SHAPES = {
    "an atom": lambda t: fl.ForAll("x", atom("R", t, v("x"))),
    "under exists": lambda t: fl.Exists("x", atom("R", t, v("x"))),
    "under not": lambda t: fl.ForAll("x", fl.Not(atom("R", t, v("x")))),
    "first of and": lambda t: fl.ForAll("x", fl.And(atom("R", t, v("x")), atom("P", c("b")))),
    "second of and": lambda t: fl.ForAll("x", fl.And(atom("P", c("b")), atom("R", t, v("x")))),
    "first of or": lambda t: fl.ForAll("x", fl.Or(atom("R", t, v("x")), atom("P", c("b")))),
    "second of or": lambda t: fl.ForAll("x", fl.Or(atom("P", c("b")), atom("R", t, v("x")))),
    "antecedent": lambda t: fl.ForAll("x", fl.Implies(atom("R", t, v("x")), atom("P", c("b")))),
    "consequent": lambda t: fl.ForAll("x", fl.Implies(atom("P", c("b")), atom("R", t, v("x")))),
    "left of iff": lambda t: fl.ForAll("x", fl.Iff(atom("R", t, v("x")), atom("P", c("b")))),
    "right of iff": lambda t: fl.ForAll("x", fl.Iff(atom("P", c("b")), atom("R", t, v("x")))),
    "left of an equation": lambda t: fl.ForAll("x", fl.Equals(t, v("x"))),
    "right of an equation": lambda t: fl.ForAll("x", fl.Equals(v("x"), t)),
    "inside a function": lambda t: fl.ForAll("x", atom("R", fn("g", c("b"), t), v("x"))),
    # the binder is the outer quantifier, and the inner one is exists
    "outer forall, inner exists": lambda t: fl.ForAll("x", fl.Exists("y", atom("R", t, v("y")))),
    # ... and the other way round, so that each kind of quantifier is the inner
    "outer exists, inner forall": lambda t: fl.Exists("x", fl.ForAll("y", atom("R", t, v("y")))),
}


@pytest.mark.parametrize("shape", SHAPES)
def test_a_term_with_a_variable_that_a_quantifier_binds_is_refused_as_captured(shape):
    build = SHAPES[shape]
    error = _refused(build(c("a")), {"a": fn("f", v("x"))})
    assert (error.name, error.variable, error.captured) == ("a", "x", True)
    # the control: the same formula takes the term without the variable
    assert _same(_substitute(build(c("a")), {"a": fn("f", c("b"))}), build(fn("f", c("b"))))


@pytest.mark.parametrize("shape", SHAPES)
def test_a_term_with_a_variable_that_no_quantifier_binds_is_refused_as_free(shape):
    build = SHAPES[shape]
    # the quantifiers of the shapes bind x, and y in two of them; none binds z
    error = _refused(build(c("a")), {"a": fn("f", v("z"))})
    assert (error.name, error.variable, error.captured) == ("a", "z", False)
    assert _same(_substitute(build(c("a")), {"a": fn("f", c("z"))}), build(fn("f", c("z"))))


def test_a_variable_as_the_replacement_is_refused_like_a_term_with_one():
    error = _refused(atom("P", c("a")), {"a": v("y")})
    assert (error.name, error.variable, error.captured) == ("a", "y", False)
    error = _refused(fl.ForAll("y", atom("P", c("a"), v("y"))), {"a": v("y")})
    assert (error.name, error.variable, error.captured) == ("a", "y", True)


def test_nothing_is_refused_that_has_no_variable_in_it():
    formula = fl.ForAll("x", fl.Exists("y", fl.And(atom("R", c("a"), v("x")), atom("R", c("b"), v("y")))))
    # a name by a name, a name by a term, and two names by each other at once
    assert _same(_substitute(formula, {"a": c("b")}),
                 fl.ForAll("x", fl.Exists("y", fl.And(atom("R", c("b"), v("x")), atom("R", c("b"), v("y"))))))
    assert _same(_substitute(formula, {"a": fn("f", c("a"), c("b"))}),
                 fl.ForAll("x", fl.Exists("y", fl.And(atom("R", fn("f", c("a"), c("b")), v("x")),
                                                       atom("R", c("b"), v("y"))))))
    assert _same(_substitute(formula, {"a": c("b"), "b": c("a")}),
                 fl.ForAll("x", fl.Exists("y", fl.And(atom("R", c("b"), v("x")), atom("R", c("a"), v("y"))))))


def test_a_name_spelled_like_a_bound_variable_is_not_captured_because_it_is_not_that_variable():
    # The guard is about variables. The constant `x` and the variable `x` are different
    # things in a formula (`_ast_eq` tells them apart), so the constant put under
    # `forall x` stays the constant and nothing is refused; it only prints like the variable.
    formula = fl.ForAll("x", atom("R", c("a"), v("x")))
    result = _substitute(formula, {"a": c("x")})
    assert _same(result, fl.ForAll("x", atom("R", c("x"), v("x"))))
    assert not _same(result, fl.ForAll("x", atom("R", v("x"), v("x"))))


def test_the_replacement_is_refused_only_where_it_would_be_put():
    # a name that does not occur is not replaced, so what would replace it is not looked at
    formula = fl.ForAll("x", atom("R", c("z"), v("x")))
    assert _same(_substitute(formula, {"a": fn("f", v("x"))}), formula)
    # and it is refused at the one place where the name does occur
    both = fl.And(atom("R", c("z"), c("z")), fl.ForAll("x", atom("R", c("a"), v("x"))))
    assert _refused(both, {"a": fn("f", v("x"))}).captured


def test_the_variable_a_quantifier_binds_is_reported_before_one_that_it_does_not():
    # b sorts before x, but only x is captured
    error = _refused(fl.ForAll("x", atom("R", c("a"), v("x"))), {"a": fn("g", v("b"), v("x"))})
    assert (error.variable, error.captured) == ("x", True)


def test_the_first_variable_in_alphabetical_order_is_the_one_named():
    both_bound = fl.ForAll("z", fl.ForAll("x", atom("R", c("a"), v("x"), v("z"))))
    for term in (fn("g", v("z"), v("x")), fn("g", v("x"), v("z"))):
        assert _refused(both_bound, {"a": term}).variable == "x"
    for term in (fn("g", v("z"), v("b")), fn("g", v("b"), v("z"))):
        error = _refused(atom("P", c("a")), {"a": term})
        assert (error.variable, error.captured) == ("b", False)


def test_the_term_level_routine_takes_the_variables_the_quantifiers_around_it_bind():
    term = fn("f", c("a"))
    replacement = {"a": fn("g", v("y"))}
    with pytest.raises(pl._UnsafeSubstitution) as free:
        pl._substitute_constants_in_term(term, replacement)
    assert (free.value.variable, free.value.captured) == ("y", False)
    with pytest.raises(pl._UnsafeSubstitution) as captured:
        pl._substitute_constants_in_term(term, replacement, ("y",))
    assert (captured.value.variable, captured.value.captured) == ("y", True)
    assert repr(pl._substitute_constants_in_term(term, {"a": fn("g", c("b"))})) == "f(g(b))"


def test_the_refusal_says_what_was_to_be_replaced_and_why():
    error = _refused(fl.ForAll("x", atom("R", c("a"), v("x"))), {"a": fn("f", v("x"))})
    assert str(error) == ("a cannot be replaced by f(x): the variable x in it would be captured "
                          "by the quantifier that binds x around a")
    error = _refused(atom("P", c("a")), {"a": fn("f", v("y"))})
    assert str(error) == ("a cannot be replaced by f(y): the variable y in it would be free in the "
                          "result, and a proof line has no free variable")
    assert (error.name, repr(error.replacement)) == ("a", "f(y)")


def test_the_symbols_of_a_replacement_do_not_excuse_a_term_with_a_variable():
    sigma = pl._Replacement()
    sigma["a"] = fn("f", v("y"))
    sigma.functions["f"] = "g"
    sigma.predicates["P"] = "Q"
    assert _refused(atom("P", c("a")), sigma).variable == "y"
    # the symbols alone, or with a name replaced by a closed term, go through
    sigma["a"] = fn("f", c("b"))
    assert _same(_substitute(atom("P", c("a")), sigma), atom("Q", fn("f", c("b"))))


def test_the_names_that_wlog_replaces_are_replaced_exactly_as_before():
    # WLOG replaces a name by a name, and trades the two case names at once
    formula = fl.ForAll("x", fl.Exists("y", fl.Or(
        fl.And(atom("R", c("a"), v("x"), c("b")), fl.Not(fl.Equals(c("a"), v("y")))),
        fl.Implies(atom("P", fn("f", c("b"), v("y"))), fl.Iff(atom("P", c("a")), atom("P", c("b")))))))
    replaced = fl.ForAll("x", fl.Exists("y", fl.Or(
        fl.And(atom("R", c("b"), v("x"), c("b")), fl.Not(fl.Equals(c("b"), v("y")))),
        fl.Implies(atom("P", fn("f", c("b"), v("y"))), fl.Iff(atom("P", c("b")), atom("P", c("b")))))))
    exchanged = fl.ForAll("x", fl.Exists("y", fl.Or(
        fl.And(atom("R", c("b"), v("x"), c("a")), fl.Not(fl.Equals(c("b"), v("y")))),
        fl.Implies(atom("P", fn("f", c("a"), v("y"))), fl.Iff(atom("P", c("b")), atom("P", c("a")))))))
    assert _same(_substitute(formula, {"a": c("b")}), replaced)
    assert _same(_substitute(formula, {"a": c("b"), "b": c("a")}), exchanged)


# --------------------------------------------------------------------------
# Mutatis mutandis does not depend on its alignment to be safe
# --------------------------------------------------------------------------

def _check(text, **options):
    entries, _ = pp.parse_proof_text(text)
    return pl.Proof(entries, **options).check_detailed()


def _accepted(text, **options):
    ok, err = _check(text, **options)
    assert ok, err


def _refused_line(text, **options):
    ok, err = _check(text, **options)
    assert not ok
    assert isinstance(err, pl.ValidationError), err
    return err


def _offering(**replacements):
    """An alignment that finds `replacements` whatever the two lines say: the
    mistake that the substitution has to refuse without help."""
    def align(model, claim, sigma, env_model, env_claim, depth):
        sigma.update(replacements)
    return align


EXISTS = """1. Let a, b be objects and R be a predicate such that: R(a, a). R(b, b). (Premise)
2. exists x, R(a, x). (Existential Introduction from 1)
3. exists x, R(b, x). (Mutatis mutandis, {cite})
"""

ARBITRARY = """1. Let a and b be objects and P and Q be predicates such that: forall y, Q(y). (Premise)
2. forall y, (P(a) -> Q(y)). (Universal Generalization from subproof below)
begin subproof
 2.0. Let c be arbitrary. (Arbitrary)
 2.1. P(a) -> Q(c). (Conditional Introduction from subproof below)
 begin subproof
  2.1.1. P(a). (Assumption for Conditional Introduction)
  2.1.2. Q(c). (Universal Instantiation from 1)
 end subproof
end subproof
3. forall t, (P(b) -> Q(t)). (Mutatis mutandis, 2)
"""

SAME_STATEMENT = """1. Let a, b be objects and R be a predicate such that: R(a, a). R(b, b). (Premise)
2. exists x, R(b, x). (Existential Introduction from 1)
3. exists x, R(b, x). (Mutatis mutandis, 2)
"""


def test_a_line_whose_own_statement_would_capture_the_term_is_refused_at_the_line(monkeypatch):
    for cite in ("2", "1 to 2"):
        _accepted(EXISTS.format(cite=cite), **BARE)
    monkeypatch.setattr(pl, "_mm_align", _offering(a=fn("f", v("x"))))
    error = _refused_line(EXISTS.format(cite="2"), **BARE)
    assert (error.label, error.category) == ("3", pl.CATEGORY_RULE_MISMATCH)
    assert error.detail == (
        "Mutatis mutandis cannot repeat line 2 with a by f(x): line 2 cannot be rewritten, because "
        "a cannot be replaced by f(x): the variable x in it would be captured by the quantifier "
        "that binds x around a")


def test_a_starting_line_that_cannot_be_rewritten_is_refused_at_the_line(monkeypatch):
    monkeypatch.setattr(pl, "_mm_align", _offering(a=fn("f", v("x"))))
    error = _refused_line(EXISTS.format(cite="1 to 2"), **BARE)
    assert (error.label, error.category) == ("3", pl.CATEGORY_RULE_MISMATCH)
    assert error.detail == (
        "Mutatis mutandis cannot start from line 1 with a by f(x): it cannot be rewritten, because "
        "a cannot be replaced by f(x): the variable x in it would be free in the result, and a "
        "proof line has no free variable")


def test_a_line_that_the_argument_cites_is_checked_as_well(monkeypatch):
    # The statement of line 2 has no `a`, so it is rewritten as it is; line 1 says it of `a`.
    # With a replacement that has no variable the argument is refused for what it cites instead.
    monkeypatch.setattr(pl, "_mm_align", _offering(a=fn("f", c("b"))))
    error = _refused_line(SAME_STATEMENT, **BARE)
    assert (error.label, error.category) == ("3", pl.CATEGORY_BAD_REFERENCE)
    assert "no visible line says R(f(b), f(b)); R(b, b)" in error.detail

    monkeypatch.setattr(pl, "_mm_align", _offering(a=fn("f", v("y"))))
    error = _refused_line(SAME_STATEMENT, **BARE)
    assert (error.label, error.category) == ("3", pl.CATEGORY_RULE_MISMATCH)
    assert error.detail == (
        "Mutatis mutandis cannot repeat line 2 with a by f(y): line 2 cannot be rewritten, because "
        "a cannot be replaced by f(y): the variable y in it would be free in the result, and a "
        "proof line has no free variable")


def test_a_line_inside_the_argument_is_named_when_it_cannot_be_rewritten(monkeypatch):
    _accepted(ARBITRARY, **BARE)
    # c occurs only inside the argument, so the first line that says it is 2.1
    monkeypatch.setattr(pl, "_mm_align", _offering(c=fn("f", v("y"))))
    error = _refused_line(ARBITRARY, **BARE)
    assert (error.label, error.category) == ("3", pl.CATEGORY_RULE_MISMATCH)
    assert error.detail == (
        "Mutatis mutandis cannot repeat line 2 with c by f(y): line 2.1 cannot be rewritten, because "
        "c cannot be replaced by f(y): the variable y in it would be free in the result, and a "
        "proof line has no free variable")


# --------------------------------------------------------------------------
# WLOG and the citation of a theorem
# --------------------------------------------------------------------------

WLOG = """1. Let a be any object. (Declaration)
2. Let x be any object. (Declaration)
3. Let y be any object. (Declaration)
4. Let P be a predicate. (Declaration)
5. Let Q be a closed formula. (Declaration)
6. P(x). (Premise)
7. P(y). (Premise)
8. P(x) -> Q. (Premise)
9. P(y) -> Q. (Premise)
10. a = x or a = y. (Premise)
11. a = x. (WLOG from 10)
12. Q. (Modus Ponens from 6, 8)
"""


def test_the_replay_of_wlog_refuses_a_replacement_with_a_variable_at_the_line(monkeypatch):
    _accepted(WLOG)
    monkeypatch.setattr(pl, "_wlog_substitution", lambda chosen, alternative: {"x": fn("f", v("z"))})
    error = _refused_line(WLOG)
    assert (error.label, error.category) == ("12", pl.CATEGORY_RULE_MISMATCH)
    assert error.detail == (
        "WLOG replay cannot rewrite line 12, because x cannot be replaced by f(z): the variable z "
        "in it would be free in the result, and a proof line has no free variable")


def test_a_promoted_theorem_is_not_citable_where_its_premises_would_take_a_variable():
    # For any a: if everything is R-related to a, then P(a).
    theorem = pl.TheoremRule("Related", [fl.ForAll("y", atom("R", c("a"), v("y")))], atom("P", c("a")), ["a"])
    assert theorem.applies([fl.ForAll("y", atom("R", c("b"), v("y")))], atom("P", c("b")))
    assert theorem.applies([fl.ForAll("y", atom("R", fn("f", c("b")), v("y")))], atom("P", fn("f", c("b"))))
    # at a variable, the premise would be `forall y, R(y, y)`: the y of the instance captured
    assert not theorem.applies([fl.ForAll("y", atom("R", v("y"), v("y")))], atom("P", v("y")))
    # and at one that no quantifier of the premise binds, it would have a free variable
    assert not theorem.applies([fl.ForAll("y", atom("R", v("z"), v("y")))], atom("P", v("z")))
