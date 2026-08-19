


import pytest

from .support import pl, fl, tl, c, v, fn, atom, A, B


def test_formula_matcher_recovers_consistent_term():
    x = v("x")
    pattern = fl.And(atom("P", x), atom("R", fn("f", x), x))
    target = fl.And(atom("P", c("a")), atom("R", fn("f", c("a")), c("a")))
    matcher = pl.FormulaMatcher("x")
    assert matcher.match_formula(pattern, target)
    assert pl._ast_eq(matcher.mapping["x"], c("a"))


def test_formula_matcher_rejects_inconsistent_replacement():
    matcher = pl.FormulaMatcher("x")
    assert not matcher.match_formula(
        atom("R", v("x"), v("x")),
        atom("R", c("a"), c("b")),
    )


def test_formula_matcher_handles_equality_and_nested_quantifiers():
    pattern = fl.And(
        fl.Equals(v("x"), c("a")),
        fl.ForAll("y", atom("R", v("x"), v("y"))),
    )
    target = fl.And(
        fl.Equals(c("b"), c("a")),
        fl.ForAll("y", atom("R", c("b"), v("y"))),
    )
    matcher = pl.FormulaMatcher("x")
    assert matcher.match_formula(pattern, target)


def test_formula_matcher_respects_shadowing_and_other_variables():
    matcher = pl.FormulaMatcher("x")
    assert not matcher.match_formula(
        fl.ForAll("x", atom("P", v("x"))),
        fl.ForAll("x", atom("P", v("x"))),
    )
    term_matcher = pl.FormulaMatcher("x")
    assert not term_matcher.match_term(v("y"), v("z"))


def test_universal_instantiation():
    universal = fl.ForAll("x", fl.Implies(atom("P", v("x")), fl.Equals(fn("f", v("x")), c("a"))))
    instance = fl.Implies(atom("P", c("b")), fl.Equals(fn("f", c("b")), c("a")))
    rule = pl.UniversalInstantiationRule()
    assert rule.applies([universal], instance)
    assert not rule.applies([universal], fl.Implies(atom("P", c("b")), fl.Equals(fn("f", c("c")), c("a"))))
    assert not rule.applies([A], A)


def test_existential_introduction():
    conclusion = fl.Exists("x", fl.And(atom("P", v("x")), fl.Equals(v("x"), c("a"))))
    source = fl.And(atom("P", c("a")), fl.Equals(c("a"), c("a")))
    rule = pl.ExistentialIntroductionRule()
    assert rule.applies([source], conclusion)
    assert not rule.applies([atom("Q", c("a"))], conclusion)


def test_universal_generalization_requires_fresh_constant_flag():
    c0 = c("c")
    conclusion = fl.ForAll("x", atom("P", v("x")))
    sp = pl.SubproofRecord(atom("c"), [atom("c"), atom("P", c0)])
    rule = pl.UniversalGeneralizationRule()
    assert rule.applies([sp], conclusion)

    wrong_flag = pl.SubproofRecord(atom("d"), [atom("d"), atom("P", c0)])
    assert not rule.applies([wrong_flag], conclusion)

    variable_instance = pl.SubproofRecord(atom("c"), [atom("c"), atom("P", v("y"))])
    assert not rule.applies([variable_instance], conclusion)


def test_universal_generalization_rejects_constant_in_outer_context():
    c0 = c("c")
    outer = [atom("R", c0)]
    sp = pl.SubproofRecord(atom("c"), [atom("c"), atom("P", c0)], outer_context_ref=outer, boundary_index=1)
    assert not pl.UniversalGeneralizationRule().applies(
        [sp], fl.ForAll("x", atom("P", v("x")))
    )


def test_existential_elimination_happy_path():
    exists = fl.Exists("x", atom("P", v("x")))
    witness = c("c")
    conclusion = fl.Exists("z", atom("Q", v("z")))
    sp = pl.SubproofRecord(
        atom("P", witness),
        [atom("P", witness), atom("Q", c("a")), conclusion],
        outer_context_ref=[],
        boundary_index=0,
    )
    assert pl.ExistentialEliminationRule().applies([exists, sp], conclusion)
    assert pl.ExistentialEliminationRule().applies([sp, exists], conclusion)


@pytest.mark.parametrize(
    "exists,sp,phi",
    [
        (
            fl.Exists("x", atom("P", v("x"))),
            pl.SubproofRecord(atom("P", fn("f", c("a"))), [atom("P", fn("f", c("a"))), A]),
            A,
        ),
        (
            fl.Exists("x", atom("P", v("x"))),
            pl.SubproofRecord(atom("P", c("c")), [atom("P", c("c")), atom("Q", c("c"))]),
            atom("Q", c("c")),
        ),
        (
            fl.Exists("x", atom("P", v("x"))),
            pl.SubproofRecord(
                atom("P", c("c")),
                [atom("P", c("c")), A],
                outer_context_ref=[atom("R", c("c"))],
                boundary_index=1,
            ),
            A,
        ),
        (
            fl.Exists("x", atom("P", v("x"))),
            pl.SubproofRecord(atom("R", c("c")), [atom("R", c("c")), A]),
            A,
        ),
    ],
)
def test_existential_elimination_freshness_and_shape_rejections(exists, sp, phi):
    assert not pl.ExistentialEliminationRule().applies([exists, sp], phi)


def test_term_occurrence_searches_every_formula_shape_and_subproof_record():
    needle = c("c")
    formula = fl.ForAll(
        "x",
        fl.Iff(
            fl.And(atom("P", fn("f", needle)), fl.Equals(v("x"), c("a"))),
            fl.Exists("y", fl.Or(atom("Q", v("y")), fl.Not(atom("R", needle)))),
        ),
    )
    assert pl._term_occurs_in_formula(needle, formula)
    assert not pl._term_occurs_in_formula(c("d"), formula)

    sp = pl.SubproofRecord(A, [A, formula])
    assert pl._term_occurs_in_formula(needle, sp)


def test_reflexivity_symmetry_and_transitivity():
    a, b, d = c("a"), c("b"), c("d")
    assert pl.ReflexivityRule().applies([], fl.Equals(a, c("a")))
    assert not pl.ReflexivityRule().applies([A], fl.Equals(a, a))
    assert not pl.ReflexivityRule().applies([], fl.Equals(a, b))

    eq_ab = fl.Equals(a, b)
    assert pl.SymmetryRule().applies([eq_ab], fl.Equals(b, a))
    assert not pl.SymmetryRule().applies([eq_ab], fl.Equals(a, b))

    eq_bd = fl.Equals(b, d)
    assert pl.TransitivityRule().applies([eq_ab, eq_bd], fl.Equals(a, d))
    assert pl.TransitivityRule().applies([eq_bd, eq_ab], fl.Equals(a, d))
    assert not pl.TransitivityRule().applies([eq_ab, fl.Equals(c("x"), d)], fl.Equals(a, d))


def test_leibniz_substitution_replaces_one_or_many_occurrences():
    a, b = c("a"), c("b")
    eq = fl.Equals(a, b)
    source = fl.And(atom("P", a), atom("R", fn("f", a), c("z")))
    target_one = fl.And(atom("P", b), atom("R", fn("f", a), c("z")))
    target_all = fl.And(atom("P", b), atom("R", fn("f", b), c("z")))
    rule = pl.LeibnizSubstitutionRule()
    assert rule.applies([eq, source], target_one)
    assert rule.applies([source, eq], target_all)
    assert not rule.applies([eq, source], source)
    assert not rule.applies([eq, source], fl.And(atom("P", c("q")), atom("R", fn("f", a), c("z"))))


def test_leibniz_requires_closed_equality_terms():
    eq = fl.Equals(v("x"), c("a"))
    assert not pl.LeibnizSubstitutionRule().applies(
        [eq, atom("P", v("x"))], atom("P", c("a"))
    )


def test_replacement_helpers_distinguish_noop_mismatch_and_change():
    a, b = c("a"), c("b")
    assert pl._term_obtainable_by_replacing(fn("f", a), a, b, fn("f", b)) is True
    assert pl._term_obtainable_by_replacing(fn("f", a), a, b, fn("f", a)) is False
    assert pl._term_obtainable_by_replacing(fn("f", a), a, b, fn("g", b)) is None

    assert pl._formula_obtainable_by_replacing(atom("P", a), a, b, atom("P", b)) is True
    assert pl._formula_obtainable_by_replacing(atom("P", a), a, b, atom("P", a)) is False
    assert pl._formula_obtainable_by_replacing(atom("P", a), a, b, atom("Q", b)) is None




