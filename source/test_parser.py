


import pytest

from .support import pp, pl, fl, tl


def test_split_top_level_respects_nesting():
    assert pp.split_top_level("A and (B and C) and D", " and ") == ["A", "(B and C)", "D"]
    assert pp.split_top_level("f(x, g(y, z)), w", ",") == ["f(x, g(y, z))", "w"]
    assert pp.split_top_level("", ",") == []


def test_split_top_level_rejects_unmatched_closing_parenthesis():
    with pytest.raises(ValueError, match="Unmatched closing"):
        pp.split_top_level("A) and B", " and ")


def test_split_top_level_rejects_unmatched_opening_parenthesis():
    with pytest.raises(ValueError, match="Unmatched opening"):
        pp.split_top_level("A and (B", " and ")


@pytest.mark.parametrize(
    "text,bound,kind,expected",
    [
        ("a", set(), tl.ConstantTerm, "a"),
        ("x", {"x"}, tl.VariableTerm, "x"),
        ("f()", set(), tl.FunctionTerm, "f()"),
        ("f(x, g(a, h(y)))", {"x", "y"}, tl.FunctionTerm, "f(x, g(a, h(y)))"),
    ],
)
def test_parse_term(text, bound, kind, expected):
    term = pp.parse_term(text, bound)
    assert isinstance(term, kind)
    assert repr(term) == expected


@pytest.mark.parametrize(
    "text,kind,expected",
    [
        ("A", fl.AtomicFormula, "A()"),
        ("P(a, f(b))", fl.AtomicFormula, "P(a, f(b))"),
        ("A and B and C", fl.And, "(A() ∧ B() ∧ C())"),
        ("A or B or C", fl.Or, "(A() ∨ B() ∨ C())"),
        ("not A", fl.Not, "¬A()"),
        ("¬ A", fl.Not, "¬A()"),
        ("A -> B", fl.Implies, "(A() → B())"),
        ("A implies B", fl.Implies, "(A() → B())"),
        ("if A then B", fl.Implies, "(A() → B())"),
        ("A <-> B", fl.Iff, "(A() ↔ B())"),
        ("A <=> B", fl.Iff, "(A() ↔ B())"),
        ("A iff B", fl.Iff, "(A() ↔ B())"),
        ("a = f(b)", fl.Equals, "a = f(b)"),
        ("forall x, P(x)", fl.ForAll, "(∀x. P(x))"),
        ("for all x P(x)", fl.ForAll, "(∀x. P(x))"),
        ("exists x, P(x)", fl.Exists, "(∃x. P(x))"),
        ("there exists x P(x)", fl.Exists, "(∃x. P(x))"),
        ("let c be arbitrary", fl.AtomicFormula, "c()"),
        ("let c be in the domain.", fl.AtomicFormula, "c()"),
    ],
)
def test_parse_formula_forms(text, kind, expected):
    formula = pp.parse_formula(text)
    assert isinstance(formula, kind)
    assert repr(formula) == expected


def test_quantifier_bound_names_become_variable_terms():
    formula = pp.parse_formula("forall x, R(x, a)")
    assert isinstance(formula.body.args[0], tl.VariableTerm)
    assert isinstance(formula.body.args[1], tl.ConstantTerm)


def test_parentheses_control_grouping():
    left = pp.parse_formula("(A and B) -> C")
    right = pp.parse_formula("A and (B -> C)")
    assert repr(left) == "((A() ∧ B()) → C())"
    assert repr(right) == "(A() ∧ (B() → C()))"


def test_documented_nonstandard_precedence_is_stable():
    assert repr(pp.parse_formula("A -> B and C")) == "((A() → B()) ∧ C())"
    assert repr(pp.parse_formula("A and B -> C")) == "(A() ∧ (B() → C()))"


def test_bare_if_and_only_if_parses_as_iff():
    assert isinstance(pp.parse_formula("A if and only if B"), fl.Iff)


def test_nested_quantifier_and_equality_parse():
    formula = pp.parse_formula("forall x, exists y, (P(x, y) and x = y)")
    assert repr(formula) == "(∀x. (∃y. (P(x, y) ∧ x = y)))"


@pytest.mark.parametrize(
    "text,tag,rule_type,indices",
    [
        ("Modus Ponens from 1, 2", "rule", pl.ModusPonensRule, ["1", "2"]),
        ("Modus Tollens from 1,2", "rule", pl.ModusTollensRule, ["1", "2"]),
        ("Hypothetical Syllogism from 1, 2", "rule", pl.HypotheticalSyllogismRule, ["1", "2"]),
        ("Disjunctive Syllogism from 1, 2", "rule", pl.DisjunctiveSyllogismRule, ["1", "2"]),
        ("Universal Instantiation from 2.1", "rule", pl.UniversalInstantiationRule, ["2.1"]),
        ("Universal Generalization from 2", "rule", pl.UniversalGeneralizationRule, ["2"]),
        ("Existential Introduction from 1", "rule", pl.ExistentialIntroductionRule, ["1"]),
        ("Existential Elimination from 1, 2", "rule", pl.ExistentialEliminationRule, ["1", "2"]),
        ("Conjunction Elimination from 1", "rule", pl.ConjunctionEliminationRule, ["1"]),
        ("Conjunction Introduction from 1, 2", "rule", pl.ConjunctionIntroductionRule, ["1", "2"]),
        ("Disjunction Introduction from 1", "rule", pl.DisjunctionIntroductionRule, ["1"]),
        ("Proof by Cases from 1, 2, 3", "rule", pl.DisjunctionEliminationRule, ["1", "2", "3"]),
        ("Biconditional Introduction from 1, 2", "rule", pl.BiconditionalIntroductionRule, ["1", "2"]),
        ("Biconditional Elimination from 1", "rule", pl.BiconditionalEliminationRule, ["1"]),
        ("Reiteration from 1", "rule", pl.ReiterationRule, ["1"]),
        ("Double Negation from 1", "rule", pl.PropositionalEquivalenceRule, ["1"]),
        ("Leibniz Substitution from 1, 2", "rule", pl.LeibnizSubstitutionRule, ["1", "2"]),
        ("Symmetry from 1", "rule", pl.SymmetryRule, ["1"]),
        ("Transitivity from 1, 2", "rule", pl.TransitivityRule, ["1", "2"]),
        ("Induction from 1, 2", "rule", pl.NamedRulePlaceholder, ["1", "2"]),
    ],
)
def test_parse_justification_rule_aliases(text, tag, rule_type, indices):
    parsed = pp.parse_justification(text)
    assert parsed[0] == tag
    assert isinstance(parsed[1], rule_type)
    assert parsed[2] == indices


@pytest.mark.parametrize(
    "text,tag,rule_type",
    [
        ("Conditional Introduction from subproof below", "rule_below", pl.ConditionalIntroductionRule),
        ("Proof by Contradiction from subproof below", "rule_below", pl.ProofByContradictionRule),
        ("Universal Generalization from subproof below", "rule_below", pl.UniversalGeneralizationRule),
    ],
)
def test_parse_rule_below(text, tag, rule_type):
    parsed = pp.parse_justification(text)
    assert parsed[0] == tag
    assert isinstance(parsed[1], rule_type)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Premise", ("premise",)),
        ("Axiom", ("axiom",)),
        ("Assumption for contradiction", ("assume",)),
        ("Fresh Variable", ("arbitrary",)),
    ],
)
def test_parse_bare_justifications(text, expected):
    assert pp.parse_justification(text) == expected


def test_reflexivity_has_zero_citations():
    parsed = pp.parse_justification("Reflexivity")
    assert parsed[0] == "rule"
    assert isinstance(parsed[1], pl.ReflexivityRule)
    assert parsed[2] == []


@pytest.mark.parametrize("text", ["", "Conditional Introduction from subproof above"])
def test_invalid_justification(text):
    with pytest.raises(ValueError):
        pp.parse_justification(text)


def test_unrecognized_rule_name_defers_to_validation_not_parsing():
    # "Magic Rule from 1" used to raise here, at parse time -- but that
    # meant *no* theory module could ever add a new citable rule without
    # also editing this shared, core function, which defeats the entire
    # point of theories being modular (see ProofParser.parse_justification's
    # docstring on the generic NamedRulePlaceholder fallback). Parsing a
    # rule name it doesn't recognize now always succeeds, deferring to
    # validation -- where a genuinely made-up name still fails loudly, just
    # one stage later, with an equally specific message.
    result = pp.parse_justification("Magic Rule from 1")
    assert result[0] == 'rule'
    assert isinstance(result[1], pl.NamedRulePlaceholder)
    assert result[1].name == 'MagicRule'
    assert result[2] == ['1']


def test_split_trailing_parenthetical_uses_final_group():
    assert pp._split_trailing_parenthetical("(A and B) -> C. (Premise)") == (
        "(A and B) -> C", "Premise"
    )
    assert pp._split_trailing_parenthetical("A") == (None, None)


def test_parse_simple_proof_and_labels():
    entries, raw = pp.parse_proof_text(
        "1. A. (Premise)\n"
        "2. A -> B. (Premise)\n"
        "3. B. (Modus Ponens from 1, 2)\n"
    )
    assert [e[0] for e in entries] == ["1", "2", "3"]
    assert isinstance(entries[2][2][1], pl.ModusPonensRule)
    assert len(raw) == 3


def test_parse_rule_below_subproof_shape():
    entries, _ = pp.parse_proof_text(
        "1. A -> A. (Conditional Introduction from subproof below)\n"
        "begin subproof\n"
        " 1.1. A. (Assumption)\n"
        " 1.2. A. (Reiteration from 1.1)\n"
        "end subproof\n"
    )
    assert len(entries) == 1
    assert len(entries[0]) == 4
    assert entries[0][0] == "1"
    assert [e[0] for e in entries[0][3]] == ["1.1", "1.2"]


def test_parse_standalone_labeled_subproof_shape():
    entries, _ = pp.parse_proof_text(
        "1. A or B. (Premise)\n"
        "2. begin subproof\n"
        " 2.1. A. (Assumption)\n"
        " 2.2. C. (Premise)\n"
        "end subproof\n"
    )
    assert entries[1][0:2] == ("2", "subproof")
    assert len(entries[1][2]) == 2


def test_comments_headings_blank_lines_and_wrapped_lines_are_ignored_or_joined():
    entries, raw = pp.parse_proof_text(
        "(* multi-line\ncomment *)\n"
        "# 1\n## Proof that\n### then B.\n\n"
        "1. A ->\n"
        "   B. (Premise)\n"
        "2. A. (Premise)\n"
        "3. B. (Modus Ponens\n"
        "   from 1, 2)\n"
    )
    assert len(entries) == 3
    assert repr(entries[0][1]) == "(A() → B())"
    assert entries[2][2][2] == ["1", "2"]
    assert len(raw) == 5


@pytest.mark.parametrize(
    "text,message",
    [
        ("1. A.", "missing explicit justification"),
        ("1. A. (Conditional Introduction from subproof below)", "requires an immediate subproof"),
        ("begin subproof\n1.1. A. (Assumption)", "Unterminated subproof"),
    ],
)
def test_proof_text_parse_errors(text, message):
    with pytest.raises(ValueError, match=message):
        pp.parse_proof_text(text)


def test_closed_formula_declaration_prefix_attaches_to_premise():
    entries, _ = pp.parse_proof_text(
        "1. Let A, B be closed formulas such that: A -> B. (Premise)"
    )
    assert entries[0][2][0] == "premise"
    assert [(d.name, d.kind) for d in entries[0][2][1]] == [
        ("A", pl.DeclarationKind.CLOSED_FORMULA),
        ("B", pl.DeclarationKind.CLOSED_FORMULA),
    ]
    assert isinstance(entries[0][1], fl.Implies)


def test_declaration_only_line_has_no_formula():
    entries, _ = pp.parse_proof_text(
        "1. Let A, B be closed formulas. (Declare)\n"
    )
    assert entries[0][1] is None
    assert entries[0][2][0] == "declare"
    assert [(d.name, d.kind) for d in entries[0][2][1]] == [
        ("A", pl.DeclarationKind.CLOSED_FORMULA),
        ("B", pl.DeclarationKind.CLOSED_FORMULA),
    ]


def test_object_predicate_and_function_declaration_prefixes():
    entries, _ = pp.parse_proof_text(
        "1. Let a, b be objects and P be a predicate and f be a function such that: P(f(a)). (Premise)"
    )
    declarations = entries[0][2][1]
    assert [(d.name, d.kind) for d in declarations] == [
        ("a", pl.DeclarationKind.OBJECT),
        ("b", pl.DeclarationKind.OBJECT),
        ("P", pl.DeclarationKind.PREDICATE),
        ("f", pl.DeclarationKind.FUNCTION),
    ]


def test_declaration_clause_parsing_recognizes_all_three_target_shapes():
    plain = pp.parse_declaration_clause("n be a natural number")
    assert plain.names == ["n"] and not plain.is_tuple and plain.domain is None

    tup = pp.parse_declaration_clause("(W, <) be a well-ordered poset")
    assert tup.names == ["W", "<"] and tup.is_tuple

    typed = pp.parse_declaration_clause("f: W -> W be an increasing function")
    assert typed.names == ["f"] and typed.domain == "W" and typed.codomain == "W"


def test_declaration_recipe_registry_dispatches_a_registered_structure_type_generically():
    # A minimal, throwaway structure type -- not order theory, not number
    # theory -- to confirm the dispatch mechanism itself is generic and
    # not secretly special-cased to the two real recipes that happen to
    # use it. This is the "would a *third*, unrelated theory module work
    # the same way" check.
    def expand_widget(clauses, start):
        dc = clauses[start]
        if not dc.is_tuple or dc.normalized_descriptor != "widget":
            return None
        carrier, marker = dc.names
        decls = [
            pl.Declaration(carrier, pl.DeclarationKind.OBJECT),
            pl.Declaration(marker, pl.DeclarationKind.PREDICATE, arity=1),
        ]
        formula = fl.AtomicFormula(marker, [tl.ConstantTerm(carrier, carrier)])
        return (1, decls, [formula], [])

    recipe = pl.DeclarationRecipe("Widget", expand_widget)
    fake_environment = pp.TheoryEnvironment(name="widget theory", declaration_recipes=[recipe])
    environment = pp.default_theory_environment().extended(fake_environment)

    entries, _ = pp.parse_proof_text("1. Let (X, Tagged) be a widget. (Declaration)\n", environment=environment)
    label, formula, justification = entries[0]
    assert repr(formula) == "Tagged(X)"
    tag, declarations = justification
    assert tag == "premise"
    assert [(d.name, d.kind) for d in declarations] == [("X", pl.DeclarationKind.OBJECT), ("Tagged", pl.DeclarationKind.PREDICATE)]


def test_implication_binds_looser_than_equality():
    # "A -> B = C" has to mean "A -> (B = C)": '='s operands must be
    # Terms, and only the left side of '->' stands alone as one. Checking
    # '=' before '->' used to split this on the '=' and try (and, after
    # the loud-failure fallback, correctly fail) to parse "Nat(x) -> x" as
    # a Term -- the wrong problem entirely, since it was never supposed to
    # be parsed as a term in the first place. Found via validate_all_
    # proofs.py surfacing tests/testProofsDeclared/declare_basic.txt,
    # previously reachable by nothing.
    formula = pp.parse_formula("Nat(x) -> x = x")
    assert isinstance(formula, fl.Implies)
    assert repr(formula.antecedent) == "Nat(x)"
    assert isinstance(formula.consequent, fl.Equals)

    quantified = pp.parse_formula("forall x, (Nat(x) -> x = x)")
    assert isinstance(quantified, fl.ForAll) and isinstance(quantified.body, fl.Implies)





