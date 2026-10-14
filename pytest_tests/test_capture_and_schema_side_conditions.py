"""Regression tests: variable capture, and the side conditions of schema rules.

Each group below was a soundness hole. The checker accepted a proof of something
that is false in some model of the proof's premises -- or, for Separation, a proof
of an arbitrary formula from the set-theory axioms alone. All of them are the same
mistake: matching or building an instance of a quantified formula without checking
that no variable of the substituted term (or of the set being defined) ends up
captured by a binder.

Every rejection test also checks *where* and *why* the proof is refused -- the
line, the rule named, and the `rule_mismatch` category -- so a parse error or an
unrelated scope error cannot pass for the guard working. Each rejection is paired
with a positive control that differs only in the property under test.
"""

from .support import atom, c, fl, fn, pl, pp, st, v


def _rejected_by(text: str, label: str, rule_name: str) -> None:
    ok, err = pp.check_proof_text(text)
    assert not ok, "the proof was accepted"
    assert isinstance(err, pl.ValidationError), err
    assert err.label == label, err
    assert err.category == pl.CATEGORY_RULE_MISMATCH, err
    assert f"'{rule_name}' does not justify" in err.detail, err


def _accepted(text: str) -> None:
    ok, err = pp.check_proof_text(text)
    assert ok, err


def _R(left, right):
    return atom("R", left, right)


# ---------------------------------------------------------------------------
# The matchers behind Universal Instantiation, Existential Introduction,
# Universal Modus Ponens, and promoted-theorem citation.
# ---------------------------------------------------------------------------

def test_matcher_refuses_to_capture_a_variable_of_the_instantiating_term():
    pattern = fl.Exists("y", _R(v("x"), v("y")))
    assert not pl.FormulaMatcher("x").match_formula(pattern, fl.Exists("y", _R(v("y"), v("y"))))


def test_matcher_allows_a_variable_that_no_enclosing_quantifier_binds():
    pattern = fl.Exists("y", _R(v("x"), v("y")))
    matcher = pl.FormulaMatcher("x")
    assert matcher.match_formula(pattern, fl.Exists("y", _R(v("z"), v("y"))))
    assert pl._ast_eq(matcher.mapping["x"], v("z"))


def test_matcher_still_instantiates_a_constant_under_quantifiers():
    pattern = fl.Exists("y", _R(v("x"), v("y")))
    matcher = pl.FormulaMatcher("x")
    assert matcher.match_formula(pattern, fl.Exists("y", _R(c("a"), v("y"))))
    assert pl._ast_eq(matcher.mapping["x"], c("a"))


def test_matcher_checks_every_occurrence_not_just_the_first():
    # The first occurrence of x sits under no quantifier, so x := y is harmless
    # there; the second sits under `exists y` and would be captured.
    pattern = fl.And(atom("P", v("x")), fl.Exists("y", _R(v("x"), v("y"))))
    target = fl.And(atom("P", v("y")), fl.Exists("y", _R(v("y"), v("y"))))
    assert not pl.FormulaMatcher("x").match_formula(pattern, target)


def test_constant_generalizing_matcher_refuses_to_capture():
    pattern = fl.Exists("y", fl.Not(fl.Equals(v("y"), c("a"))))
    capturing = fl.Exists("y", fl.Not(fl.Equals(v("y"), v("y"))))
    assert not pl.ConstantGeneralizingMatcher({"a"}).match_formula(pattern, capturing)

    matcher = pl.ConstantGeneralizingMatcher({"a"})
    assert matcher.match_formula(pattern, fl.Exists("y", fl.Not(fl.Equals(v("y"), c("b")))))
    assert pl._ast_eq(matcher.mapping["a"], c("b"))


def test_promoted_theorem_is_not_citable_at_a_capturing_instance():
    # "For any a there is something different from it" must not become
    # "there is something different from itself".
    theorem = pl.TheoremRule("Different", [], fl.Exists("y", fl.Not(fl.Equals(v("y"), c("a")))), ["a"])
    assert theorem.applies([], fl.Exists("y", fl.Not(fl.Equals(v("y"), c("b")))))
    assert not theorem.applies([], fl.Exists("y", fl.Not(fl.Equals(v("y"), v("y")))))


# ---------------------------------------------------------------------------
# Through the whole pipeline: Universal Instantiation, Existential
# Introduction, Universal Modus Ponens.
# ---------------------------------------------------------------------------

def test_universal_instantiation_cannot_capture():
    # forall x exists y R(x,y) does not entail exists y R(y,y) (R is < on the naturals).
    _rejected_by("""\
1. Let R be a predicate such that: forall x, exists y, R(x, y). (Premise)
2. exists y, R(y, y). (Universal Instantiation from 1)
""", "2", "UniversalInstantiation")


def test_universal_instantiation_at_a_constant_is_still_accepted():
    _accepted("""\
1. Let a be an object and R be a predicate such that: forall x, exists y, R(x, y). (Premise)
2. exists y, R(a, y). (Universal Instantiation from 1)
""")


def test_existential_introduction_cannot_capture():
    # forall y R(y,y) does not entail exists x forall y R(x,y) (R is = on two elements).
    _rejected_by("""\
1. Let R be a predicate such that: forall y, R(y, y). (Premise)
2. exists x, forall y, R(x, y). (Existential Introduction from 1)
""", "2", "ExistentialIntroduction")


def test_existential_introduction_at_a_constant_is_still_accepted():
    _accepted("""\
1. Let a be an object and R be a predicate such that: forall y, R(a, y). (Premise)
2. exists x, forall y, R(x, y). (Existential Introduction from 1)
""")


def test_universal_modus_ponens_cannot_capture():
    # Both lines are closed, and x := y is captured in the cited minor premise
    # and in the conclusion alike.
    _rejected_by("""\
1. Let P, R be predicates such that: forall x, ((exists y, P(x, y)) -> (exists y, R(x, y))). (Premise)
2. exists y, P(y, y). (Premise)
3. exists y, R(y, y). (Universal Modus Ponens from 1, 2)
""", "3", "UniversalModusPonens")


def test_universal_modus_ponens_at_a_constant_is_still_accepted():
    _accepted("""\
1. Let a be an object and P, R be predicates such that: forall x, ((exists y, P(x, y)) -> (exists y, R(x, y))). (Premise)
2. exists y, P(a, y). (Premise)
3. exists y, R(a, y). (Universal Modus Ponens from 1, 2)
""")


def test_capture_no_longer_derives_a_contradiction_from_satisfiable_premises():
    # `not Q` and "every object differs from some object" are jointly satisfiable
    # (Q false, two objects), yet the capturing step used to give Q and not Q.
    _rejected_by("""\
1. Let Q be a closed formula such that: not Q. (Premise)
2. forall x, exists y, not (x = y). (Premise)
3. exists y, not (y = y). (Universal Instantiation from 2)
4. Let c be an object. (Declare)
5. Q. (Existential Elimination from 3, subproof below)
begin subproof
 5.1. not (c = c). (Assumption for Existential Elimination)
 5.2. c = c. (Reflexivity)
 5.3. Q. (Explosion from 5.1, 5.2)
end subproof
6. Q and not Q. (Conjunction Introduction from 5, 1)
""", "3", "UniversalInstantiation")


# ---------------------------------------------------------------------------
# Separation: the new set Y may not occur in B, nor in the bounding term X.
# ---------------------------------------------------------------------------

_SEPARATION = st.SeparationSchemaRule()


def _separation(B, X=None, y_name="Y", u_name="u"):
    """exists Y, forall u, (u in Y <-> (u in X and B))"""
    bounding = c("X") if X is None else X
    return fl.Exists(y_name, fl.ForAll(u_name, fl.Iff(
        st.membership_formula(v(u_name), v(y_name)),
        fl.And(st.membership_formula(v(u_name), bounding), B),
    )))


_ORDINARY_B = fl.Not(st.membership_formula(v("u"), st.EMPTY_SET))


def test_separation_accepts_an_ordinary_instance():
    assert _SEPARATION.applies([], _separation(_ORDINARY_B))


def test_separation_accepts_a_parameter_in_b():
    assert _SEPARATION.applies([], _separation(st.membership_formula(v("u"), c("p"))))


def test_separation_refuses_a_b_that_mentions_the_new_set():
    # With B := "u is not in Y" and any X that has an element, Y = {u in X : u not in Y}.
    assert not _SEPARATION.applies([], _separation(fl.Not(st.membership_formula(v("u"), v("Y")))))
    assert not _SEPARATION.applies([], _separation(fl.Or(_ORDINARY_B, st.membership_formula(v("p"), v("Y")))))


def test_separation_allows_y_to_be_bound_inside_b():
    inner = fl.Exists("Y", st.membership_formula(v("u"), v("Y")))
    assert _SEPARATION.applies([], _separation(inner))


def test_separation_refuses_a_bounding_term_that_mentions_a_binder():
    # "In(u, f(u))" would let the bounding set depend on the element.
    for bounding in (fn("f", v("u")), v("Y"), fn("f", v("Y"))):
        assert not _SEPARATION.applies([], _separation(_ORDINARY_B, bounding)), bounding


def test_separation_refuses_equal_binders():
    assert not _SEPARATION.applies([], _separation(_ORDINARY_B, y_name="u", u_name="u"))


def test_separation_instance_is_accepted_through_the_pipeline():
    _accepted("""\
1. Let X be any set. (Declaration)
2. exists Y, forall u, (In(u, Y) iff (In(u, X) and not In(u, EmptySet))). (Separation)
""")


def test_separation_cannot_prove_an_arbitrary_formula_from_the_axioms():
    # Pairing gives a set X with an element a; Separation with B := "u not in Y"
    # then gives Y with `a in Y <-> a not in Y`, and Explosion proves anything.
    # No premises. The first refusal is at the Separation line.
    _rejected_by("""\
1. Let a be an object. (Declare)
2. Let Q be a closed formula. (Declare)
3. exists Y, forall u, (In(u, Y) iff (u = a or u = a)). (Axiom of pairing)
4. Let X be an object. (Declare)
5. Q. (Existential Elimination from 3, subproof below)
begin subproof
 5.1. forall u, (In(u, X) iff (u = a or u = a)). (Assumption for Existential Elimination)
 5.2. In(a, X) iff (a = a or a = a). (Universal Instantiation from 5.1)
 5.3. (a = a or a = a) -> In(a, X). (Biconditional Elimination from 5.2)
 5.4. a = a. (Reflexivity)
 5.5. a = a or a = a. (Disjunction Introduction from 5.4)
 5.6. In(a, X). (Modus Ponens from 5.3, 5.5)
 5.7. exists Y, forall u, (In(u, Y) iff (In(u, X) and not In(u, Y))). (Separation)
 5.8. Let W be an object. (Declare)
 5.9. Q. (Existential Elimination from 5.7, subproof below)
 begin subproof
  5.9.1. forall u, (In(u, W) iff (In(u, X) and not In(u, W))). (Assumption for Existential Elimination)
  5.9.2. In(a, W) iff (In(a, X) and not In(a, W)). (Universal Instantiation from 5.9.1)
  5.9.3. In(a, W) -> (In(a, X) and not In(a, W)). (Biconditional Elimination from 5.9.2)
  5.9.4. (In(a, X) and not In(a, W)) -> In(a, W). (Biconditional Elimination from 5.9.2)
  5.9.5. not In(a, W). (Proof by Contradiction from subproof below)
  begin subproof
   5.9.5.1. In(a, W). (Assumption for contradiction)
   5.9.5.2. In(a, X) and not In(a, W). (Modus Ponens from 5.9.3, 5.9.5.1)
   5.9.5.3. not In(a, W). (Conjunction Elimination from 5.9.5.2)
   5.9.5.4. In(a, W) and not In(a, W). (Conjunction Introduction from 5.9.5.1, 5.9.5.3)
  end subproof
  5.9.6. In(a, X) and not In(a, W). (Conjunction Introduction from 5.6, 5.9.5)
  5.9.7. In(a, W). (Modus Ponens from 5.9.4, 5.9.6)
  5.9.8. Q. (Explosion from 5.9.7, 5.9.5)
 end subproof
end subproof
""", "5.7", "Separation")


# ---------------------------------------------------------------------------
# Replacement: C (the image set) and z (the uniqueness clause's variable) may
# not occur in B, and A may not mention any binder it sits under.
# ---------------------------------------------------------------------------

_REPLACEMENT = st.ReplacementSchemaRule()


def _replacement(A, B_of, x="x", y="y", z="z", C="C"):
    """forall x, (x in A -> exists y, (B(x,y) and forall z, (B(x,z) -> z = y)))
         -> exists C, forall y, (y in C <-> exists x, (x in A and B(x,y)))"""
    B_xy, B_xz = B_of(y), B_of(z)
    in_a = lambda var: st.membership_formula(v(var), A)
    antecedent = fl.ForAll(x, fl.Implies(in_a(x), fl.Exists(y, fl.And(
        B_xy, fl.ForAll(z, fl.Implies(B_xz, fl.Equals(v(z), v(y)))),
    ))))
    consequent = fl.Exists(C, fl.ForAll(y, fl.Iff(
        st.membership_formula(v(y), v(C)),
        fl.Exists(x, fl.And(in_a(x), B_xy)),
    )))
    return fl.Implies(antecedent, consequent)


def _y_equals_x(y_name):
    return fl.Equals(v(y_name), v("x"))


def test_replacement_accepts_an_ordinary_instance():
    assert _REPLACEMENT.applies([], _replacement(c("A"), _y_equals_x))


def test_replacement_refuses_an_a_that_mentions_the_bound_x():
    # With f(x) = {x} this would assert that the universal set exists.
    assert not _REPLACEMENT.applies([], _replacement(fn("f", v("x")), _y_equals_x))


def test_replacement_refuses_an_a_that_mentions_another_binder():
    for binder in ("y", "z", "C"):
        assert not _REPLACEMENT.applies([], _replacement(fn("f", v(binder)), _y_equals_x)), binder


def test_replacement_refuses_a_b_that_mentions_the_image_set():
    not_in_c = lambda y_name: fl.And(_y_equals_x(y_name), fl.Not(st.membership_formula(v("x"), v("C"))))
    assert not _REPLACEMENT.applies([], _replacement(c("A"), not_in_c))


def test_replacement_refuses_a_b_that_mentions_the_uniqueness_variable():
    not_in_z = lambda y_name: fl.And(_y_equals_x(y_name), fl.Not(st.membership_formula(v("x"), v("z"))))
    assert not _REPLACEMENT.applies([], _replacement(c("A"), not_in_z))


def test_replacement_refuses_coinciding_binder_names():
    assert not _REPLACEMENT.applies([], _replacement(c("A"), _y_equals_x, C="x"))


# ---------------------------------------------------------------------------
# Induction: the step variable may not be captured by a quantifier inside P.
# ---------------------------------------------------------------------------

def test_induction_cannot_use_a_step_variable_that_p_binds():
    # P(x) := exists n, R(x, n); the "step" the rule would build for the variable n,
    #   forall n, ((Nat(n) and exists n, R(n, n)) -> exists n, R(Succ(n), n)),
    # no longer mentions the n being inducted on. On the naturals with
    # R(a, b) := (a = 0 and b = 1) the base and this step are true and the
    # conclusion is false (at x = 1).
    _rejected_by("""\
1. Let R be a predicate such that: exists n, R(Zero, n). (Premise)
2. forall n, ((Nat(n) and exists n, R(n, n)) -> exists n, R(Succ(n), n)). (Premise)
3. forall x, (Nat(x) -> exists n, R(x, n)). (Induction from 1, 2)
""", "3", "Induction")


def test_induction_with_a_step_variable_that_p_does_not_mention_is_accepted():
    _accepted("""\
1. Let R be a predicate such that: exists m, R(Zero, m). (Premise)
2. forall n, ((Nat(n) and exists m, R(n, m)) -> exists m, R(Succ(n), m)). (Premise)
3. forall x, (Nat(x) -> exists m, R(x, m)). (Induction from 1, 2)
""")


def test_induction_step_variable_equal_to_the_induction_variable_is_accepted():
    # Same variable as the conclusion's: nothing is captured, even though P binds n.
    _accepted("""\
1. Let R be a predicate such that: exists n, R(Zero, n). (Premise)
2. forall x, ((Nat(x) and exists n, R(x, n)) -> exists n, R(Succ(x), n)). (Premise)
3. forall x, (Nat(x) -> exists n, R(x, n)). (Induction from 1, 2)
""")


def test_induction_refuses_a_step_variable_that_is_a_free_parameter_of_p():
    rule = pl.InductionRule(type_predicate="Nat", zero_term=c("Zero"), succ_symbol="Succ")
    conclusion = fl.ForAll("x", fl.Implies(atom("Nat", v("x")), _R(v("x"), v("n"))))
    step = fl.ForAll("n", fl.Implies(
        fl.And(atom("Nat", v("n")), _R(v("n"), v("n"))),
        _R(fn("Succ", v("n")), v("n")),
    ))
    assert rule._expected(conclusion, [_R(c("Zero"), v("n")), step]) is None
