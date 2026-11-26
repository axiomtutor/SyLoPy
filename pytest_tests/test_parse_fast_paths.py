"""The shortcuts that keep formula parsing fast give the answers of the full computation.

Three places skip work they would only repeat: `_with_base_line_elaborators`
returns an environment that already has the base syntax, `rewrite_formula_symbols`
returns text that holds none of the notation symbols, and `Proof.__init__` does
not compare a required rule with the rule list when that very object is in it.
Each test states the full computation (a copy of the code before the shortcut)
and checks that the shortcut returns an equal result, including the cases the
shortcut must not take.
"""
from dataclasses import replace

import pytest

from .support import c, importlib, pl

pp = importlib.import_module("SyLoPy.source.ProofParser")
no = importlib.import_module("SyLoPy.source.Notation")
pe = importlib.import_module("SyLoPy.source.ProofElaboration")
st = importlib.import_module("SyLoPy.source.SetTheory")


def _full_computation(environment):
    """`_with_base_line_elaborators` as it was before the shortcut."""
    base_elaborators = pp._base_line_elaborators()
    base_environment = pe.TheoryEnvironment(
        name="base logic",
        notation_table=pp._BASE_LOGICAL_NOTATION_TABLE,
    )
    notation_table = base_environment.extended(environment).notation_table
    return replace(
        environment,
        notation_table=notation_table,
        line_elaborators=[
            *base_elaborators,
            *(item for item in environment.line_elaborators
              if item not in base_elaborators),
        ],
        phrase_parsers=[
            pp._parse_base_equality_phrase,
            *(item for item in environment.phrase_parsers
              if item is not pp._parse_base_equality_phrase),
        ],
    )


def _environments():
    bare = pe.TheoryEnvironment(name="bare")
    with_set_theory = st.SET_THEORY_ENVIRONMENT
    wrapped = pp._with_base_line_elaborators(with_set_theory)
    base = pp._base_line_elaborators()
    repeated_elaborator = replace(
        wrapped, line_elaborators=[*wrapped.line_elaborators, base[0]]
    )
    repeated_phrase_parser = replace(
        wrapped,
        phrase_parsers=[*wrapped.phrase_parsers, pp._parse_base_equality_phrase],
    )
    base_second = replace(
        wrapped,
        phrase_parsers=[
            wrapped.phrase_parsers[1],
            wrapped.phrase_parsers[0],
            *wrapped.phrase_parsers[2:],
        ],
    )
    elaborators_reordered = replace(
        wrapped, line_elaborators=list(reversed(wrapped.line_elaborators))
    )
    base_count = len(base)
    other_elaborators = replace(
        wrapped, line_elaborators=[object() for _ in range(base_count + 1)]
    )
    no_base_phrase_parser = replace(
        wrapped,
        phrase_parsers=[item for item in wrapped.phrase_parsers
                        if item is not pp._parse_base_equality_phrase],
    )
    return {
        "other elaborators": other_elaborators,
        "no base phrase parser": no_base_phrase_parser,
        "bare": bare,
        "set theory": with_set_theory,
        "wrapped": wrapped,
        "default": pp._cached_default_environment(),
        "elaborator repeated": repeated_elaborator,
        "phrase parser repeated": repeated_phrase_parser,
        "base phrase parser second": base_second,
        "elaborators reordered": elaborators_reordered,
    }


@pytest.mark.parametrize("name", list(_environments()))
def test_base_syntax_shortcut_equals_the_full_computation(name):
    environment = _environments()[name]

    assert pp._with_base_line_elaborators(environment) == _full_computation(environment)


def test_an_environment_with_the_base_syntax_is_returned_as_it_is():
    wrapped = pp._with_base_line_elaborators(st.SET_THEORY_ENVIRONMENT)

    assert pp._with_base_line_elaborators(wrapped) is wrapped


@pytest.mark.parametrize("symbol", sorted(pp._BASE_LOGICAL_NOTATION_TABLE))
def test_a_changed_base_symbol_is_still_a_conflict(symbol):
    wrapped = pp._with_base_line_elaborators(st.SET_THEORY_ENVIRONMENT)
    changed = dict(wrapped.notation_table)
    changed[symbol] = "something else"
    environment = replace(wrapped, notation_table=changed)

    with pytest.raises(ValueError, match="conflicting notation"):
        pp._with_base_line_elaborators(environment)
    with pytest.raises(ValueError, match="conflicting notation"):
        _full_computation(environment)


def test_a_missing_base_symbol_is_added_back():
    wrapped = pp._with_base_line_elaborators(st.SET_THEORY_ENVIRONMENT)
    table = dict(wrapped.notation_table)
    del table["∧"]
    environment = replace(wrapped, notation_table=table)

    result = pp._with_base_line_elaborators(environment)

    assert result.notation_table["∧"] == "and"
    assert result == _full_computation(environment)


TEXTS = [
    "",
    "   ",
    "P(x)",
    "  P(x) and Q(x)  ",
    "x is in A union B",
    "x ∈ A",
    "x∈A∪B",
    "¬P(x)∧Q(x)",
    "∀x ∈ A, P(x)",
    "∃ y, x ∈ y",
    "∀x, ∃y, (x ∈ y → y ⊆ A)",
    "A × B ∩ C",
]


TABLES = {
    "default": pp._BASE_LOGICAL_NOTATION_TABLE,
    "no quantifier symbols": {"∧": "and", "∨": "or"},
    "empty": {},
}


@pytest.mark.parametrize("table_name", list(TABLES))
@pytest.mark.parametrize("text", TEXTS)
def test_symbol_rewriting_shortcut_equals_the_full_computation(text, table_name):
    table = TABLES[table_name]
    try:
        expected = _rewrite_in_full(text, table)
    except ValueError as error:
        with pytest.raises(ValueError, match=str(error)):
            no.rewrite_formula_symbols(text, table)
    else:
        assert no.rewrite_formula_symbols(text, table) == expected


def _rewrite_in_full(text, notation_table):
    """`rewrite_formula_symbols` as it was before the shortcut."""
    import re

    for quantifier in re.finditer(r"[∀∃]", text):
        remainder = text[quantifier.end():]
        if re.match(r"\s*[A-Za-z_][A-Za-z0-9_]*", remainder) is None:
            raise ValueError(
                f"quantifier symbol {quantifier.group()!r} must be followed by a variable"
            )
    rewritten = no._BOUNDED_QUANTIFIER_MEMBERSHIP.sub(r"\1 in ", text)
    for symbol in sorted(notation_table, key=len, reverse=True):
        reading = notation_table[symbol]
        if not symbol or not reading:
            raise ValueError("notation symbols and readings must be nonempty")
        rewritten = rewritten.replace(symbol, f" {reading} ")
    return rewritten.strip()


def test_text_without_symbols_is_only_stripped():
    table = pp._cached_default_environment().notation_table

    assert no.rewrite_formula_symbols("  forall x, P(x)  ", table) == "forall x, P(x)"


@pytest.mark.parametrize("table_name", list(TABLES))
@pytest.mark.parametrize("text", ["∀ 1", "∃", "∀", "x and ∃ (y)"])
def test_a_quantifier_symbol_without_a_variable_is_still_refused(text, table_name):
    table = TABLES[table_name]

    with pytest.raises(ValueError, match="must be followed by a variable"):
        no.rewrite_formula_symbols(text, table)


@pytest.mark.parametrize(
    "table",
    [{"": "x"}, {"∧": ""}, {"∧": "and", "∨": ""}],
)
@pytest.mark.parametrize("text", ["P(x)", "P ∧ Q"])
def test_an_empty_symbol_or_reading_is_refused_for_any_text(table, text):
    with pytest.raises(ValueError, match="must be nonempty"):
        no.rewrite_formula_symbols(text, table)


def test_a_non_string_is_refused():
    with pytest.raises(TypeError):
        no.rewrite_formula_symbols(None, {})


# ---------------------------------------------------------------------------
# Required rules of a proof
# ---------------------------------------------------------------------------

def _proof_with_required(rules, required):
    entries = pe.ElaboratedEntries([], required_rules=list(required))
    return pl.Proof(entries, rules=list(rules))


def test_a_required_rule_that_is_already_registered_is_not_added_again():
    rules = pl.default_rules()
    proof = _proof_with_required(rules, [rules[0], rules[-1]])

    assert proof.rules == rules


def test_a_required_rule_equal_in_configuration_is_not_added_again():
    rules = pl.default_rules()
    twin = type(rules[0])()
    proof = _proof_with_required(rules, [twin])

    assert len(proof.rules) == len(rules)
    assert proof.rules[0] is rules[0]


def test_a_required_rule_of_another_configuration_is_added_once():
    rules = [pl.ModusPonensRule()]
    other = pl.InductionRule("Nat", c("0"), "S")
    proof = _proof_with_required(rules, [other, other])

    assert [type(rule) for rule in proof.rules] == [pl.ModusPonensRule, pl.InductionRule]
    assert proof.rules[1] is other
