


import pytest

from .support import tl, c, v, fn


@pytest.mark.parametrize(
    "factory,args,message",
    [
        (tl.ConstantTerm, (1, 1), "name must be a string"),
        (tl.ConstantTerm, ("", 1), "cannot be empty"),
        (tl.VariableTerm, (1,), "name must be a string"),
        (tl.VariableTerm, ("",), "cannot be empty"),
        (tl.FunctionTerm, (1, []), "symbol must be a string"),
        (tl.FunctionTerm, ("", []), "cannot be empty"),
        (tl.FunctionTerm, ("f", "x"), "list or tuple"),
        (tl.FunctionTerm, ("f", [object()]), "Term instances"),
    ],
)
def test_constructor_validation(factory, args, message):
    with pytest.raises(tl.TypecheckError, match=message):
        factory(*args)


def test_term_kind_predicates_and_arity():
    a = c("a", 3)
    x = v("x")
    f = fn("f", x, a)

    assert a.is_constant() and not a.is_variable() and not a.is_function()
    assert x.is_variable() and not x.is_constant() and not x.is_function()
    assert f.is_function() and not f.is_constant() and not f.is_variable()
    assert f.arity() == 2


def test_repr_str_and_nested_function_formatting():
    term = fn("f", v("x"), fn("g", c("a"), c("b")))
    assert repr(term) == "f(x, g(a, b))"
    assert str(term) == repr(term)


def test_equality_and_hash_are_repr_based():
    assert c("a", 1) == c("a", 999)
    assert c("a") == v("a")  # current Term contract is repr-based across subclasses
    assert c("a") != c("b")
    assert len({c("a", 1), c("a", 2), v("a")}) == 1
    assert c("a") != "a"


def test_base_term_repr_is_abstract():
    with pytest.raises(NotImplementedError):
        repr(tl.Term())


def test_evaluate_constant_ignores_schema():
    assert tl.evaluate_term(c("a", 7), {"a": 100}) == 7


def test_evaluate_variable_uses_schema_value_verbatim():
    replacement = object()
    assert tl.evaluate_term(v("x"), {"x": replacement}) is replacement


def test_evaluate_nested_function():
    term = fn("mul", fn("add", v("x"), c("two", 2)), c("three", 3))
    schema = {"x": 4, "add": lambda a, b: a + b, "mul": lambda a, b: a * b}
    assert tl.evaluate_term(term, schema) == 18


@pytest.mark.parametrize(
    "term,schema,message",
    [
        (v("x"), {}, "Variable 'x' not found"),
        (fn("f", c("a", 1)), {}, "Function symbol 'f' not found"),
        (fn("f", c("a", 1)), {"f": 4}, "must be callable"),
    ],
)
def test_evaluation_failures(term, schema, message):
    with pytest.raises(tl.TypecheckError, match=message):
        tl.evaluate_term(term, schema)


def test_evaluate_rejects_non_term():
    with pytest.raises(tl.TypecheckError, match="requires a Term"):
        tl.evaluate_term("x")


class UnknownTerm(tl.Term):
    def __repr__(self):
        return "unknown"


def test_evaluate_rejects_unknown_term_subtype():
    with pytest.raises(tl.TypecheckError, match="Unknown Term subtype"):
        tl.evaluate_term(UnknownTerm())




