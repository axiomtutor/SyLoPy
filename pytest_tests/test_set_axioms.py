"""Tests for the ZFC axioms added to SetTheory.py: Pairing, Union, Power
Set and Infinity as plain formulas in `st.SET_AXIOMS`, and Separation and
Replacement as the zero-premise schema rules `SeparationSchemaRule` /
`ReplacementSchemaRule`. Extensionality adds no new formula or rule -- it
is already covered by `SetEqualityRule` plus ordinary equality reasoning
(see the module docstring in SetTheory.py) -- so there is nothing of its
own to test here.
"""

from pathlib import Path

from .support import pl, fl, tl, pp, mp, st, c, v, atom


def _proof_text(name: str) -> str:
    project = Path(__file__).resolve().parents[1]
    return (project / "tests" / "setTheoryProofs" / name).read_text()


def test_set_axioms_are_wired_into_the_environment():
    assert len(st.SET_AXIOMS) == 4
    assert st.SET_AXIOMS == st.SET_THEORY_ENVIRONMENT.axioms
    rule_names = {rule.name for rule in st.SET_THEORY_ENVIRONMENT.rules}
    assert {"Separation", "Replacement"} <= rule_names


def test_zfc_remaining_axioms_fixture_all_pass():
    text = _proof_text("zfc_remaining_axioms.txt")
    results = mp.run_multi_proof_file(text)
    assert [(number, ok) for number, _expected, ok, _msg, _crashed in results] == [
        ("1", True), ("2", True), ("3", True), ("4", True), ("5", True), ("6", True),
    ]


# --------------------------------------------------------------------
# SeparationSchemaRule
# --------------------------------------------------------------------

def _separation_instance(B, X_name="X", Y_name="Y", u_name="u"):
    X = c(X_name)
    return fl.Exists(Y_name, fl.ForAll(u_name, fl.Iff(
        st.membership_formula(v(u_name), v(Y_name)),
        fl.And(st.membership_formula(v(u_name), X), B(v(u_name))),
    )))


def test_separation_accepts_an_arbitrary_property():
    rule = st.SeparationSchemaRule()
    trivial = _separation_instance(lambda u: fl.Not(st.membership_formula(u, c("X"))))
    assert rule.applies([], trivial)

    W = c("W")
    two_parameter = _separation_instance(lambda u: st.membership_formula(u, W))
    assert rule.applies([], two_parameter)


def test_separation_rejects_any_cited_premise():
    rule = st.SeparationSchemaRule()
    instance = _separation_instance(lambda u: st.membership_formula(u, c("W")))
    assert not rule.applies([atom("P")], instance)


def test_separation_rejects_swapped_membership_target():
    rule = st.SeparationSchemaRule()
    X, Y = c("X"), c("Y")
    u = v("u")
    # In(u, X) <-> (In(u, Y) and B(u)) -- X and Y swapped from what the
    # schema requires (the new set must be on the *left* of the <->).
    swapped = fl.Exists("Y", fl.ForAll("u", fl.Iff(
        st.membership_formula(u, X),
        fl.And(st.membership_formula(u, Y), fl.Not(st.membership_formula(u, X))),
    )))
    assert not rule.applies([], swapped)


def test_separation_rejects_a_bare_existential_without_the_separation_shape():
    rule = st.SeparationSchemaRule()
    assert not rule.applies([], fl.Exists("Y", atom("P", v("Y"))))


# --------------------------------------------------------------------
# ReplacementSchemaRule
# --------------------------------------------------------------------

def _replacement_instance(B_xy_factory, *, A_ante=None, A_cons=None,
                           cons_x="x", cons_y="y", unique_rhs="y"):
    """Build a Replacement instance. `B_xy_factory(x, y)` returns B(x,y);
    the uniqueness clause's B(x,z) is always the correctly-substituted
    (x, z) form, so the "good" shape is the default -- tests that want a
    broken instance tamper with the result afterwards.
    """
    x, y, z = v("x"), v("y"), v("z")
    A_ante = A_ante if A_ante is not None else c("A")
    A_cons = A_cons if A_cons is not None else c("A")
    B_xy = B_xy_factory(x, y)
    B_xz = B_xy_factory(x, z)
    antecedent = fl.ForAll("x", fl.Implies(
        st.membership_formula(x, A_ante),
        fl.Exists("y", fl.And(B_xy, fl.ForAll("z", fl.Implies(
            B_xz, fl.Equals(z, v(unique_rhs))
        )))),
    ))
    cons_x_t, cons_y_t = v(cons_x), v(cons_y)
    B_cons = B_xy_factory(cons_x_t, cons_y_t)
    consequent = fl.Exists("C", fl.ForAll(cons_y, fl.Iff(
        st.membership_formula(cons_y_t, v("C")),
        fl.Exists(cons_x, fl.And(st.membership_formula(cons_x_t, A_cons), B_cons)),
    )))
    return fl.Implies(antecedent, consequent)


def test_replacement_accepts_a_trivial_functional_relation():
    rule = st.ReplacementSchemaRule()
    instance = _replacement_instance(lambda x, y: fl.Equals(y, x))
    assert rule.applies([], instance)


def test_replacement_accepts_a_relation_with_an_extra_parameter():
    rule = st.ReplacementSchemaRule()
    W = c("W")
    instance = _replacement_instance(
        lambda x, y: fl.And(fl.Equals(y, x), st.membership_formula(x, W))
    )
    assert rule.applies([], instance)


def test_replacement_rejects_any_cited_premise():
    rule = st.ReplacementSchemaRule()
    instance = _replacement_instance(lambda x, y: fl.Equals(y, x))
    assert not rule.applies([atom("P")], instance)


def test_replacement_rejects_a_wrong_uniqueness_conclusion():
    # forall z, (B(x,z) -> z = w) -- w instead of y: z is required to equal
    # some unrelated term rather than the existential's own witness.
    rule = st.ReplacementSchemaRule()
    bad = _replacement_instance(lambda x, y: fl.Equals(y, x), unique_rhs="w")
    assert not rule.applies([], bad)


def test_replacement_rejects_a_uniqueness_clause_that_is_not_a_real_substitution():
    # B(x,z) is some unrelated formula, not B(x,y) with y replaced by z.
    rule = st.ReplacementSchemaRule()
    x, y, z = v("x"), v("y"), v("z")
    A = c("A")
    antecedent = fl.ForAll("x", fl.Implies(
        st.membership_formula(x, A),
        fl.Exists("y", fl.And(fl.Equals(y, x), fl.ForAll("z", fl.Implies(
            st.membership_formula(z, c("W")), fl.Equals(z, y),
        )))),
    ))
    consequent = fl.Exists("C", fl.ForAll("y", fl.Iff(
        st.membership_formula(y, v("C")),
        fl.Exists("x", fl.And(st.membership_formula(x, A), fl.Equals(y, x))),
    )))
    assert not rule.applies([], fl.Implies(antecedent, consequent))


def test_replacement_rejects_mismatched_set_between_antecedent_and_consequent():
    rule = st.ReplacementSchemaRule()
    bad = _replacement_instance(lambda x, y: fl.Equals(y, x), A_cons=c("B"))
    assert not rule.applies([], bad)


def test_replacement_rejects_renamed_variables_in_the_consequent():
    # The schema requires the *same* x, y spelling throughout one citation
    # (see ReplacementSchemaRule's docstring) -- a consequent written with
    # fresh names x2/y2 is not matched, even though it is logically the
    # same statement up to alpha-equivalence.
    rule = st.ReplacementSchemaRule()
    bad = _replacement_instance(lambda x, y: fl.Equals(y, x), cons_x="x2", cons_y="y2")
    assert not rule.applies([], bad)


def test_replacement_rejects_a_bare_implication_without_the_replacement_shape():
    rule = st.ReplacementSchemaRule()
    assert not rule.applies([], fl.Implies(atom("P"), atom("Q")))
