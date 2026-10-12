"""The validator tells every rule which declarations are in scope at its line.

`RuleContext.declaration(name)` is how a rule learns what a symbol was
declared to be (the relation rules read a relation's carrier and properties
from it). Whatever the way a rule is cited -- from earlier lines, from a
subproof below, from lines plus subproofs below -- it must be handed the
scope of the line it justifies: the declarations of that line's own block and
of the blocks around it, including what the line itself declares, and never
what a subproof it consumed declared inside.

The probe rule here says yes exactly when `c` is declared at its line, so a
test can tell what the validator showed it.
"""

import pytest

from .support import assert_invalid, assert_valid, pl, prop

P = prop("P")
Q = prop("Q")
C = pl.Declaration("c", pl.DeclarationKind.OBJECT)


class SeesC(pl.InferenceRule):
    name = "SeesC"
    premise_arity = 1

    def applies(self, candidates, phi):
        return False

    def applies_in_context(self, candidates, phi, context):
        return context.declaration("c") is not None


class ExplainsC(SeesC):
    """Says yes only to `Q`, and explains a refusal from the scope it was shown."""
    name = "ExplainsC"

    def applies_in_context(self, candidates, phi, context):
        return context.declaration("c") is not None and phi == Q

    def explain_in_context(self, candidates, phi, context):
        return "c is declared here" if context.declaration("c") is not None else "c is not declared here"


def declare_c(label):
    return (label, None, ("declare", [C]))


# --------------------------------------------------------------------
# Cited from earlier lines.
# --------------------------------------------------------------------

def test_a_rule_cited_from_lines_sees_the_declarations_before_its_line():
    assert_valid([
        ("1", P, ("premise",)),
        declare_c("2"),
        ("3", Q, ("rule", SeesC(), ["1"])),
    ], rules=[SeesC()])


def test_a_rule_cited_from_lines_does_not_see_a_symbol_nobody_declared():
    assert_invalid([
        ("1", P, ("premise",)),
        ("2", Q, ("rule", SeesC(), ["1"])),
    ], pl.CATEGORY_RULE_MISMATCH, label="2", rules=[SeesC()])


def test_a_rule_line_sees_what_it_declares_itself():
    assert_valid([
        ("1", P, ("premise",)),
        ("2", Q, ("rule", SeesC(), ["1"], [C])),
    ], rules=[SeesC()])


def test_a_declaration_below_the_line_is_not_yet_in_scope():
    assert_invalid([
        ("1", P, ("premise",)),
        ("2", Q, ("rule", SeesC(), ["1"])),
        declare_c("3"),
    ], pl.CATEGORY_RULE_MISMATCH, label="2", rules=[SeesC()])


def test_a_subproof_sees_the_declarations_of_the_blocks_around_it():
    assert_valid([
        ("1", P, ("premise",)),
        declare_c("2"),
        ("3", "subproof", [
            ("3.1", Q, ("assume",)),
            ("3.2", Q, ("rule", SeesC(), ["3.1"])),
        ]),
    ], rules=[SeesC()])


def test_a_subproofs_declaration_is_seen_inside_it_and_not_after_it_closes():
    inside = [
        ("1", P, ("premise",)),
        ("2", "subproof", [
            ("2.1", Q, ("assume",)),
            declare_c("2.2"),
            ("2.3", Q, ("rule", SeesC(), ["2.1"])),
        ]),
    ]
    assert_valid(inside, rules=[SeesC()])

    after = inside + [("3", Q, ("rule", SeesC(), ["1"]))]
    assert_invalid(after, pl.CATEGORY_RULE_MISMATCH, label="3", rules=[SeesC()])


def test_a_sibling_subproofs_declaration_is_not_seen():
    entries = [
        ("1", P, ("premise",)),
        ("2", "subproof", [
            ("2.1", Q, ("assume",)),
            declare_c("2.2"),
        ]),
        ("3", "subproof", [
            ("3.1", Q, ("assume",)),
            ("3.2", Q, ("rule", SeesC(), ["3.1"])),
        ]),
    ]
    assert_invalid(entries, pl.CATEGORY_RULE_MISMATCH, label="3.2", rules=[SeesC()])


# --------------------------------------------------------------------
# Cited from a subproof below.
# --------------------------------------------------------------------

def test_a_rule_cited_from_a_subproof_below_sees_the_scope_of_the_line_it_justifies():
    assert_valid([
        declare_c("1"),
        ("2", Q, ("rule_below", SeesC()), [
            ("2.1", P, ("assume",)),
        ]),
    ], rules=[SeesC()])


def test_a_rule_cited_from_a_subproof_below_does_not_see_what_that_subproof_declared():
    assert_invalid([
        ("1", Q, ("rule_below", SeesC()), [
            ("1.1", P, ("assume",)),
            declare_c("1.2"),
        ]),
    ], pl.CATEGORY_RULE_MISMATCH, label="1", rules=[SeesC()])


# --------------------------------------------------------------------
# Cited from lines plus subproofs below.
# --------------------------------------------------------------------

def test_a_rule_cited_from_attached_subproofs_sees_the_scope_of_the_line_it_justifies():
    assert_valid([
        declare_c("1"),
        ("2", Q, ("rule_hybrid", SeesC(), []), [
            [("2.1", P, ("assume",))],
        ]),
    ], rules=[SeesC()])


def test_a_rule_cited_from_attached_subproofs_does_not_see_what_they_declared():
    assert_invalid([
        ("1", Q, ("rule_hybrid", SeesC(), []), [
            [("1.1", P, ("assume",)), declare_c("1.2")],
        ]),
    ], pl.CATEGORY_RULE_MISMATCH, label="1", rules=[SeesC()])


# --------------------------------------------------------------------
# The explanation of a refusal is asked with the same scope.
# --------------------------------------------------------------------

@pytest.mark.parametrize(
    ("declared", "expected"),
    [(True, "c is declared here"), (False, "c is not declared here")],
)
def test_a_rules_explanation_of_a_refusal_sees_the_scope_of_the_line(declared, expected):
    # The conclusion is P, which ExplainsC always refuses, so the refusal
    # does not depend on `c`; only the wording of the reason does.
    entries = [("1", P, ("premise",))]
    if declared:
        entries.append(declare_c("2"))
    entries.append(("3", P, ("rule", ExplainsC(), ["1"])))
    err = assert_invalid(entries, pl.CATEGORY_RULE_MISMATCH, label="3", rules=[ExplainsC()])
    assert err.detail.endswith(f": {expected}"), err.detail


def test_the_explanation_for_a_rule_below_and_a_hybrid_rule_sees_their_scope_too():
    below = [
        declare_c("1"),
        ("2", P, ("rule_below", ExplainsC()), [("2.1", Q, ("assume",))]),
    ]
    err = assert_invalid(below, pl.CATEGORY_RULE_MISMATCH, label="2", rules=[ExplainsC()])
    assert err.detail.endswith(": c is declared here"), err.detail

    hybrid = [
        declare_c("1"),
        ("2", P, ("rule_hybrid", ExplainsC(), []), [[("2.1", Q, ("assume",))]]),
    ]
    err = assert_invalid(hybrid, pl.CATEGORY_RULE_MISMATCH, label="2", rules=[ExplainsC()])
    assert err.detail.endswith(": c is declared here"), err.detail


# --------------------------------------------------------------------
# The context itself.
# --------------------------------------------------------------------

def test_a_rule_context_made_without_a_scope_declares_nothing():
    assert pl.RuleContext().declaration("c") is None
    assert pl.RuleContext([P], [Q], ["c"], ["c"]).declaration("c") is None


def test_a_rule_context_made_with_a_scope_answers_from_it():
    scope = pl.DeclarationScope()
    scope.declare(C)
    context = pl.RuleContext(declarations=scope)
    assert context.declaration("c") is C
    assert context.declaration("d") is None


def test_a_rule_asked_directly_outside_a_proof_sees_nothing():
    assert not SeesC().applies_in_context([P], Q, pl.RuleContext())
