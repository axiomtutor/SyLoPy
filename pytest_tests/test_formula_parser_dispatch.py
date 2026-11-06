"""The top-level dispatch over `TheoryEnvironment.formula_parsers`.

A theory's `formula_parsers` are offered the whole text of an ordinary proof-line
expression (`_ElaborationContext.parse_surface_expression`) and of each component of
a premise bundle (`_parse_premise_part`), in registry order, before the generic
grammar sees it. The first one that answers wins. A premise lowers what it gets to a
core formula; a line keeps the `SurfaceExpression`, because a line elaborator may use
its extra structure. When no parser answers, the generic grammar parses the text with
the same environment and the same bound variables. With no environment at all, no
parser is consulted.

These tests state that behavior, not how it is written, so that it can be moved
between one helper and two loops (issue #144) without a test changing. Each one was
written to fail for a plausible mistake in either layout.
"""

import pytest

from .support import fl, pl, pp, st, tl

WHOLE = fl.AtomicFormula("Whole", [])


class Recorder:
    """A formula parser that records what it is offered and answers from a table."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []  # (text, contents of the set it was given, id of that set)

    def __call__(self, text, bound_vars):
        self.calls.append((text, frozenset(bound_vars), id(bound_vars)))
        return self.answers.get(text.strip())

    @property
    def texts(self):
        return [text for text, _bound, _identity in self.calls]


def whole_phrase():
    """A surface expression whose wording contains a connective: the generic grammar would cut it at `or`."""
    return pp.SurfaceExpression("core", WHOLE, "x is a or b")


def subset_surface():
    """A real non-core surface expression, with raw operands that only lowering turns into a formula."""
    expression = st.try_parse_set_expression("A subseteq B", set())
    assert expression is not None and expression.kind == "subset"
    return expression


def environment(*parsers, **registries):
    return pp.TheoryEnvironment(formula_parsers=list(parsers), **registries)


def context(*parsers, **registries):
    return pp._ElaborationContext(environment(*parsers, **registries))


# --- a premise: its bundle components, one at a time ------------------------

def test_a_premise_component_is_offered_whole_before_the_connective_grammar():
    parser = Recorder({"x is a or b": whole_phrase()})
    assert pp._parse_premise_part("x is a or b", environment(parser)) is WHOLE
    assert parser.texts == ["x is a or b"]


def test_every_bundle_component_is_offered_on_its_own_with_an_empty_set():
    parser = Recorder()
    formulas = pp._parse_formula_or_bundle("A -> B. B -> C.", environment(parser))
    assert len(formulas) == 2
    assert parser.texts == ["A -> B", "B -> C"]
    assert [bound for _text, bound, _identity in parser.calls] == [frozenset(), frozenset()]


def test_the_first_parser_that_answers_wins_and_later_ones_are_not_asked():
    first, second, third = Recorder(), Recorder({"P": pp.SurfaceExpression("core", WHOLE, "P")}), Recorder()
    assert pp._parse_premise_part("P", environment(first, second, third)) is WHOLE
    assert first.texts == ["P"] and second.texts == ["P"] and third.texts == []


def test_the_parsers_are_asked_in_registry_order():
    order = []

    def named(name):
        def parser(text, bound_vars):
            order.append(name)
            return None
        return parser

    pp._parse_premise_part("P", environment(named("first"), named("second"), named("third")))
    assert order == ["first", "second", "third"]


def test_a_surface_expression_that_is_not_core_is_lowered_for_a_premise():
    surface = subset_surface()
    result = pp._parse_premise_part("S", environment(Recorder({"S": surface})))
    left, right = surface.value
    assert pl._ast_eq(result, st.subset_formula(left, right))


def test_a_surface_kind_with_no_core_lowering_is_an_error_for_a_premise():
    parser = Recorder({"S": pp.SurfaceExpression("mystery", 1, "S")})
    with pytest.raises(ValueError, match="no core lowering registered"):
        pp._parse_premise_part("S", environment(parser))


def test_with_no_environment_no_parser_is_consulted_and_the_default_grammar_decides(monkeypatch):
    spy = Recorder()
    monkeypatch.setattr(pp, "_cached_default_environment", lambda: environment(spy))
    result = pp._parse_premise_part("A and B", None)
    assert spy.calls == []
    assert repr(result) == repr(pp.parse_formula("A and B"))


def test_a_premise_that_no_parser_takes_is_parsed_by_the_generic_grammar_with_the_same_environment():
    parser = Recorder()
    env = environment(parser)
    assert repr(pp._parse_premise_part("A -> B and C", env)) == repr(pp.parse_formula("A -> B and C", environment=env))
    assert parser.texts == ["A -> B and C"]


# --- a line: the whole expression ------------------------------------------

def test_a_line_is_offered_whole_and_a_non_core_surface_expression_is_kept_as_it_is():
    surface = subset_surface()
    parser = Recorder({"S": surface})
    assert context(parser).parse_surface_expression("S") is surface
    assert parser.texts == ["S"]


def test_parse_core_formula_lowers_what_parse_surface_expression_keeps():
    surface = subset_surface()
    left, right = surface.value
    result = context(Recorder({"S": surface})).parse_core_formula("S")
    assert pl._ast_eq(result, st.subset_formula(left, right))


def test_a_line_that_no_parser_takes_is_wrapped_as_core_with_its_own_text():
    ctx = context(Recorder())
    expression = ctx.parse_surface_expression("A -> B")
    assert (expression.kind, expression.text) == ("core", "A -> B")
    assert repr(expression.value) == repr(pp.parse_formula("A -> B"))


def test_a_whole_line_with_a_connective_in_its_wording_is_offered_whole():
    parser = Recorder({"x is a or b": whole_phrase()})
    assert context(parser).parse_surface_expression("x is a or b").value is WHOLE
    assert parser.texts == ["x is a or b"]


def test_the_callers_bound_variables_reach_the_parsers_unchanged_and_are_not_altered():
    parser = Recorder()
    bound = {"x"}
    context(parser).parse_surface_expression("P(x)", bound)
    assert bound == {"x"}
    assert [contents for _text, contents, _identity in parser.calls] == [frozenset({"x"})]
    assert [identity for _text, _contents, identity in parser.calls] == [id(bound)]


def test_the_generic_fallback_gets_the_same_bound_variables_as_the_parsers():
    ctx = context(Recorder())
    with_x = ctx.parse_surface_expression("P(x)", {"x"}).value
    without = ctx.parse_surface_expression("P(x)", set()).value
    assert isinstance(with_x.args[0], tl.VariableTerm)
    assert isinstance(without.args[0], tl.ConstantTerm)


def test_with_no_bound_variables_given_the_parsers_get_an_empty_set():
    parser = Recorder()
    context(parser).parse_surface_expression("P(x)")
    assert [contents for _text, contents, _identity in parser.calls] == [frozenset()]


# --- both entry points -----------------------------------------------------

def _registered_marker(text, bound_vars):
    return fl.AtomicFormula("Marked", []) if text.strip() == "Z" else None


@pytest.mark.parametrize("entry", ["premise", "line"])
def test_the_generic_fallback_uses_the_environment_it_was_given(entry):
    env = environment(Recorder(), nested_formula_parsers=[_registered_marker])
    if entry == "premise":
        formula = pp._parse_premise_part("Z and P", env)
    else:
        formula = pp._ElaborationContext(env).parse_surface_expression("Z and P").value
    assert "Marked" in repr(formula)


@pytest.mark.parametrize("text", ["A -> B", "A and B", "x is a or b", "S"])
def test_both_entry_points_offer_the_same_text_to_the_same_parsers_in_the_same_order(text):
    answers = {"S": subset_surface(), "x is a or b": whole_phrase()}
    premise_answering, premise_declining = Recorder(answers), Recorder()
    line_answering, line_declining = Recorder(answers), Recorder()
    pp._parse_premise_part(text, environment(premise_answering, premise_declining))
    context(line_answering, line_declining).parse_surface_expression(text)
    assert premise_answering.texts == line_answering.texts == [text]
    assert premise_declining.texts == line_declining.texts
