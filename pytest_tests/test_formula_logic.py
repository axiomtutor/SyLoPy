


import pytest

from .support import fl, tl, c, v, fn, atom, A, B, C


def test_formula_representations():
    x = v("x")
    a = c("a")
    assert repr(atom("P", x, a)) == "P(x, a)"
    assert repr(fl.And(A, B, C)) == "(A() ∧ B() ∧ C())"
    assert repr(fl.Or(A, B)) == "(A() ∨ B())"
    assert repr(fl.Not(A)) == "¬A()"
    assert repr(fl.Implies(A, B)) == "(A() → B())"
    assert repr(fl.Iff(A, B)) == "(A() ↔ B())"
    assert repr(fl.Equals(x, a)) == "x = a"
    assert repr(fl.ForAll("x", atom("P", x))) == "(∀x. P(x))"
    assert repr(fl.Exists("x", atom("P", x))) == "(∃x. P(x))"


def test_formula_base_repr_is_abstract():
    with pytest.raises(NotImplementedError):
        repr(fl.Formula())


def test_atomic_evaluation_with_named_predicate_and_terms():
    formula = atom("Less", v("x"), c("ten", 10))
    schema = {"x": 3, "Less": lambda x, y: x < y}
    assert fl.evaluate_formula(formula, schema) is True


def test_atomic_evaluation_with_callable_predicate_and_literal_argument():
    formula = fl.AtomicFormula(lambda x, y: x == y, [c("a", 4), 4])
    assert fl.evaluate_formula(formula) is True


@pytest.mark.parametrize(
    "formula,expected",
    [
        (fl.And(), True),
        (fl.Or(), False),
        (fl.And(A, B), False),
        (fl.Or(A, B), True),
        (fl.Not(A), False),
        (fl.Implies(A, B), False),
        (fl.Implies(B, A), True),
        (fl.Iff(A, B), False),
        (fl.Iff(A, A), True),
    ],
)
def test_connective_evaluation(formula, expected):
    schema = {"A": lambda: True, "B": lambda: False}
    assert fl.evaluate_formula(formula, schema) is expected


def test_equality_evaluation_uses_term_values():
    assert fl.evaluate_formula(fl.Equals(c("a", 3), c("b", 3))) is True
    assert fl.evaluate_formula(fl.Equals(c("a", 3), c("b", 4))) is False


def test_quantifiers_use_variable_specific_domain():
    x = v("x")
    formula = fl.ForAll("x", atom("Positive", x))
    assert fl.evaluate_formula(formula, {"Positive": lambda n: n > 0}, {"x": [1, 2, 3]})
    assert not fl.evaluate_formula(formula, {"Positive": lambda n: n > 0}, {"x": [0, 1]})


def test_quantifiers_use_default_domain_and_schema_domain():
    x = v("x")
    exists_even = fl.Exists("x", atom("Even", x))
    assert fl.evaluate_formula(exists_even, {"Even": lambda n: n % 2 == 0}, {"_": [1, 2, 3]})
    assert fl.evaluate_formula(exists_even, {"Even": lambda n: n % 2 == 0, "__domain__": {"_": [2]}})


def test_empty_domain_vacuity():
    x = v("x")
    assert fl.evaluate_formula(fl.ForAll("x", atom("P", x)), {"P": lambda _: False}, {"_": []})
    assert not fl.evaluate_formula(fl.Exists("x", atom("P", x)), {"P": lambda _: True}, {"_": []})


@pytest.mark.parametrize("quantifier", [fl.ForAll, fl.Exists])
def test_quantifier_requires_domain(quantifier):
    with pytest.raises(Exception, match="No domain provided"):
        fl.evaluate_formula(quantifier("x", atom("P", v("x"))), {"P": lambda _: True})


def test_predicate_lookup_and_validation_errors():
    with pytest.raises(Exception, match="not found"):
        fl.evaluate_formula(atom("Missing"))
    with pytest.raises(Exception, match="callable or a string"):
        fl.evaluate_formula(fl.AtomicFormula(42, []))
    with pytest.raises(Exception, match="must be callable"):
        fl.evaluate_formula(atom("P"), {"P": 42})


class UnknownFormula(fl.Formula):
    def __repr__(self):
        return "?"


def test_unknown_formula_type_rejected():
    with pytest.raises(Exception, match="Unknown formula type"):
        fl.evaluate_formula(UnknownFormula())


def test_term_free_variables():
    term = fn("f", v("x"), c("a"), fn("g", v("y"), v("x")))
    assert fl.term_free_variables(term) == {"x", "y"}
    assert fl.term_free_variables(c("a")) == set()
    assert fl.term_free_variables(object()) == set()


def test_free_variables_all_formula_shapes():
    x, y, z = v("x"), v("y"), v("z")
    formula = fl.Iff(
        fl.ForAll("x", fl.And(atom("P", x, y), fl.Equals(x, z))),
        fl.Exists("y", fl.Or(atom("Q", y, z), fl.Not(atom("R", x)))),
    )
    assert fl.free_variables(formula) == {"x", "y", "z"}
    assert not fl.is_closed(formula)
    assert fl.is_closed(fl.ForAll("x", atom("P", v("x"))))


def test_substitute_in_term_recursive_and_non_mutating():
    original = fn("f", v("x"), fn("g", v("y")))
    replacement = c("a")
    result = fl.substitute_in_term(original, "x", replacement)
    assert repr(result) == "f(a, g(y))"
    assert repr(original) == "f(x, g(y))"
    assert result is not original


def test_substitute_in_formula_all_connectives():
    x, y = v("x"), v("y")
    original = fl.Iff(
        fl.And(atom("P", x), fl.Equals(x, y)),
        fl.Exists("z", fl.Implies(atom("Q", x, v("z")), fl.Not(atom("R", x)))),
    )
    result = fl.substitute_in_formula(original, "x", c("a"))
    assert repr(result) == "((P(a) ∧ a = y) ↔ (∃z. (Q(a, z) → ¬R(a))))"


def test_substitution_stops_under_same_binder():
    formula = fl.ForAll("x", atom("P", v("x"), v("y")))
    result = fl.substitute_in_formula(formula, "x", c("a"))
    assert result is formula


def test_substitution_does_not_rename_to_avoid_capture_current_contract():
    formula = fl.ForAll("y", atom("P", v("x"), v("y")))
    result = fl.substitute_in_formula(formula, "x", v("y"))
    assert repr(result) == "(∀y. P(y, y))"




