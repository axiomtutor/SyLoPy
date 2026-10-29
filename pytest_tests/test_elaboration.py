


import pytest

from SyLoPy.source import ProofElaboration as pe
from SyLoPy.source import SetTheory as st
from .support import pp, pl, fl, tl


EMPTY_SUBSET_PROOF = """
# 1: The empty set subset theorem
## Proof that
### If X is any set
### then the empty set is a subset of X
1. Let X be any set. (Declaration)
2. The empty set is a subset of X. (Subset proof below)
 2.1. Let a in the empty set. (Assumption for subset proof)
 2.2. a is not in the empty set. (Set property)
 2.3. a is in X. (Explosion from 2.1 and 2.2)
"""


def test_surface_parser_preserves_natural_subset_construct_and_source_lines():
    surface = pp.parse_surface_proof(EMPTY_SUBSET_PROOF)
    assert isinstance(surface, pe.SurfaceProof)
    assert len(surface.entries) == 2

    subset_line = surface.entries[1]
    assert isinstance(subset_line, pe.SurfaceLine)
    assert subset_line.formula_text == "The empty set is a subset of X"
    assert subset_line.justification_text == "Subset proof below"
    assert subset_line.span.label == "2"
    assert subset_line.span.start_line == 7

    assert len(subset_line.subproofs) == 1
    subproof = subset_line.subproofs[0]
    assert subproof.implicit is True
    assert [entry.label for entry in subproof.entries] == ["2.1", "2.2", "2.3"]


def test_subset_proof_elaborates_to_ug_then_conditional_introduction():
    entries, _ = pp.parse_proof_text(EMPTY_SUBSET_PROOF)
    assert isinstance(entries, pe.ElaboratedEntries)

    subset = entries[1]
    assert subset[0] == "2"
    assert isinstance(subset[1], fl.ForAll)
    assert isinstance(subset[2][1], pl.UniversalGeneralizationRule)

    outer = subset[3]
    assert outer[0][0] == "2.__arbitrary"
    assert outer[0][2] == ("arbitrary",)
    assert outer[1][0] == "2.__conditional"
    assert isinstance(outer[1][1], fl.Implies)
    assert isinstance(outer[1][2][1], pl.ConditionalIntroductionRule)
    assert [line[0] for line in outer[1][3]] == ["2.1", "2.2", "2.3"]


def test_empty_subset_surface_proof_validates():
    entries, _ = pp.parse_proof_text(EMPTY_SUBSET_PROOF)
    ok, err = pl.Proof(entries).check_detailed()
    assert ok
    assert err is None


def test_subset_proof_accepts_explicit_begin_end_form_too():
    text = """
1. Let X be any set. (Declaration)
2. The empty set is a subset of X. (Subset proof below)
begin subproof
 2.1. Let a in the empty set. (Assumption for subset proof)
 2.2. a is not in the empty set. (Set property)
 2.3. a is in X. (Explosion from 2.1 and 2.2)
end subproof
"""
    entries, _ = pp.parse_proof_text(text)
    assert pl.Proof(entries).check()[0]


def test_bad_subset_opening_reports_the_surface_line():
    text = """
1. Let X, Y be any sets. (Declaration)
2. X is a subset of Y. (Subset proof below)
 2.1. Let a in Y. (Assumption for subset proof)
 2.2. a is in Y. (Reiteration from 2.1)
"""
    with pytest.raises(pe.ElaborationError) as exc_info:
        pp.parse_proof_text(text)
    assert "Line 2.1" in str(exc_info.value)
    assert "left-hand set" in str(exc_info.value)


def test_synthetic_freshness_failure_maps_back_to_subset_line():
    text = """
1. Let X be any set. (Declaration)
2. Let a be any object. (Declaration)
3. The empty set is a subset of X. (Subset proof below)
 3.1. Let a in the empty set. (Assumption for subset proof)
 3.2. a is not in the empty set. (Set property)
 3.3. a is in X. (Explosion from 3.1 and 3.2)
"""
    entries, _ = pp.parse_proof_text(text)
    ok, err = pl.Proof(entries).check_detailed()
    assert not ok
    assert err.label == "3"
    assert err.location == "Line 3"
    assert "Invalid subset proof" in err.detail
    assert "already declared" in err.detail


def test_natural_set_formulas_lower_to_core_formula_ast():
    member = pp.parse_formula("a is in X")
    assert repr(member) == "In(a, X)"

    not_member = pp.parse_formula("a is not in the empty set")
    assert repr(not_member) == "¬In(a, EmptySet)"

    subset = pp.parse_formula("the empty set is a subset of X")
    assert isinstance(subset, fl.ForAll)
    assert repr(subset.body) == "(In(__subset_element, EmptySet) → In(__subset_element, X))"


def test_explosion_rule_accepts_a_contradictory_pair_in_either_order():
    p = fl.AtomicFormula("P", [])
    q = fl.AtomicFormula("Q", [])
    rule = pl.ExplosionRule()
    assert rule.applies([p, fl.Not(p)], q)
    assert rule.applies([fl.Not(p), p], q)
    assert not rule.applies([p, q], q)


def test_core_renderer_exposes_desugared_steps_without_reparsing_text():
    entries, _ = pp.parse_proof_text(EMPTY_SUBSET_PROOF)
    rendered = pp.format_core_proof(entries)
    assert "2.__arbitrary" in rendered
    assert "UniversalGeneralization from subproof below" in rendered
    assert "ConditionalIntroduction from subproof below" in rendered
    assert "Explosion from 2.1, 2.2" in rendered

# --------------------------------------------------------------------
# Elaboration uses ProofContext as its sole lexical scope for declarations.
# The kernel's DeclarationScope remains an independent validation boundary.
# These tests cover declaration registration, environment seeding, and
# duplicate-declaration errors.
# --------------------------------------------------------------------

def test_compound_declaration_registers_into_proof_context():
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof("1. Let X be any set. (Declaration)\n")
    context.elaborate_entry(surface.entries[0])

    declaration = context.context.lookup_declaration("X")
    assert declaration is not None
    assert declaration.kind == pl.DeclarationKind.OBJECT


def test_proof_context_seeding_tolerates_vocabulary_reachable_through_two_extension_paths():
    context = pp._ElaborationContext(pp.default_theory_environment())
    assert context.context.lookup_declaration("EmptySet") is not None
    assert context.context.lookup_declaration("In") is not None


def test_duplicate_compound_declaration_still_raises_elaboration_error():
    with pytest.raises(pe.ElaborationError, match="already declared"):
        pp.parse_proof_text(
            "1. Let X be any set. (Declaration)\n"
            "2. Let X be any set. (Declaration)\n"
        )


# --------------------------------------------------------------------
# Each subproof gets a child ProofContext, so labels remain local to their
# branch and sibling branches may reuse the same labels.
# --------------------------------------------------------------------

def test_sibling_subproofs_can_reuse_the_same_label():
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof(
        "1. Let P, Q, R be closed formulas such that: P or Q. if P then R. Q -> R. (Premise)\n"
        "2. R. (Proof by Cases from 1, subproofs below)\n"
        "begin subproof\n"
        " 2.1. P. (Case)\n"
        " 2.2. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
        "begin subproof\n"
        " 2.1. Q. (Case)\n"
        " 2.2. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
    )
    for entry in surface.entries:
        context.elaborate_entry(entry)  # must not raise DuplicateBindingError
    assert context.context.lookup_label("2.1") is None
    assert context.context.lookup_label("2.2") is None


def test_sibling_subproofs_can_reuse_the_same_compound_declaration_name():
    # Sibling branches have independent child contexts, so the same named
    # declaration may be introduced in both without leaking after closure.
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof(
        "1. Let P, Q, R be closed formulas such that: P or Q. if P then R. Q -> R. (Premise)\n"
        "2. R. (Proof by Cases from 1, subproofs below)\n"
        "begin subproof\n"
        " 2.1. P. (Case)\n"
        " 2.2. Let X be any set. (Declaration)\n"
        " 2.3. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
        "begin subproof\n"
        " 2.1. Q. (Case)\n"
        " 2.2. Let X be any set. (Declaration)\n"
        " 2.3. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
    )
    for entry in surface.entries:
        context.elaborate_entry(entry)  # must not raise DuplicateBindingError / KeyError
    assert context.context.lookup_declaration("X") is None


def test_declaration_inside_a_subproof_does_not_leak_into_the_enclosing_context():
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof(
        "1. A -> A. (Conditional Introduction from subproof below)\n"
        "begin subproof\n"
        " 1.1. A. (Assumption)\n"
        " 1.2. Let X be any set. (Declaration)\n"
        " 1.3. A. (Reiteration from 1.1)\n"
        "end subproof\n"
    )
    context.elaborate_entry(surface.entries[0])
    assert context.context.lookup_declaration("X") is None


# --------------------------------------------------------------------
# Arbitrary-name bindings and assumptions are scoped to the subproof in
# which they are introduced. A common placeholder such as `c` may be
# reused in sibling branches without leaking across them.
# --------------------------------------------------------------------

def test_sibling_subproofs_can_reuse_the_same_arbitrary_name():
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof(
        "1. Let P, Q, R be closed formulas such that: P or Q. if P then R. Q -> R. (Premise)\n"
        "2. R. (Proof by Cases from 1, subproofs below)\n"
        "begin subproof\n"
        " 2.1. P. (Case)\n"
        " 2.2. let c be arbitrary. (Fresh Variable)\n"
        " 2.3. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
        "begin subproof\n"
        " 2.1. Q. (Case)\n"
        " 2.2. let c be arbitrary. (Fresh Variable)\n"
        " 2.3. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
    )
    for entry in surface.entries:
        context.elaborate_entry(entry)  # must not raise DuplicateBindingError
    assert context.context.lookup_arbitrary("c") is None  # neither leaked out


def test_arbitrary_binding_inside_a_subproof_does_not_leak_into_the_enclosing_context():
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof(
        "1. forall x, x = x. (Universal Generalization from subproof below)\n"
        "begin subproof\n"
        " 1.0. let c be arbitrary. (Fresh Variable)\n"
        " 1.1. c = c. (Reflexivity)\n"
        "end subproof\n"
    )
    context.elaborate_entry(surface.entries[0])
    assert context.context.lookup_arbitrary("c") is None
    assert context.context.is_arbitrary("c") is False


def test_declaration_from_an_enclosing_scope_is_visible_inside_a_nested_subproof():
    # A declaration in an enclosing scope must remain visible when a nested
    # relation declaration refers to that enclosing carrier.
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof(
        "1. Let X be any set. (Declaration)\n"
        "2. A -> A. (Conditional Introduction from subproof below)\n"
        "begin subproof\n"
        " 2.1. A. (Assumption)\n"
        " 2.2. Let R be a relation on X. (Declaration)\n"
        " 2.3. A. (Reiteration from 2.1)\n"
        "end subproof\n"
    )
    for entry in surface.entries:
        context.elaborate_entry(entry)  # must not raise -- "X" must be visible from inside
    # "R" was local to the (now closed) subproof and did not leak back out.
    assert context.context.lookup_declaration("R") is None
    # "X" is still visible at the root, exactly as before -- it was never
    # local to the subproof to begin with.
    assert context.context.lookup_declaration("X") is not None


# --------------------------------------------------------------------
# Elaboration resolves line-label references through ProofContext.
# "Existence from L" reads the content of an earlier line, so these tests
# check that ancestor labels are visible but closed sibling labels are not.
# The kernel's LabelScope independently enforces reference visibility.
# --------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "1. A. (Premise)\n1. B. (Premise)\n",
        "1. A. (Premise)\nbegin subproof\n 1. B. (Assumption)\nend subproof\n",
    ],
    ids=["duplicate-line-label", "duplicate-assumption-label"],
)
def test_duplicate_reference_labels_have_consistent_elaboration_errors(text):
    with pytest.raises(
        pe.ElaborationError,
        match="already used earlier in this proof or an enclosing scope",
    ):
        pp.parse_proof_text(text)


def test_label_from_an_enclosing_scope_is_visible_to_existence_inside_a_nested_subproof():
    # The label half of the same "parent visibility" property the
    # declaration test above covers: an existential established outside a
    # subproof must still be citable by "Existence from L" *inside* it.
    text = (
        "1. exists x, P(x). (Premise)\n"
        "2. A -> A. (Conditional Introduction from subproof below)\n"
        "begin subproof\n"
        " 2.1. A. (Assumption)\n"
        " 2.2. Define z = a. (Existence from 1)\n"
        " 2.3. A. (Reiteration from 2.1)\n"
        "end subproof\n"
    )
    entries, _ = pp.parse_proof_text(text)  # must not raise
    assert entries[1][0] == "2"


def test_existence_no_longer_leaks_a_sibling_subproofs_reused_label():
    # Regression test for sibling-scoped label lookup. Two branches may reuse
    # a label, so lookup must consult the currently visible context rather than
    # a flat label-to-formula dictionary that can leak a sibling's formula.
    text = (
        "1. P or Q. (Premise)\n"
        "2. R. (Proof by Cases from 1, subproofs below)\n"
        "begin subproof\n"
        " 2.1. P. (Case)\n"
        " 2.2. exists x, S(x). (Premise)\n"
        " 2.3. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
        "begin subproof\n"
        " 2.1. Q. (Case)\n"
        " 2.2. Define z = a. (Existence from 2.2)\n"
        " 2.3. R. (Modus Ponens from 1, 2.1)\n"
        "end subproof\n"
    )
    with pytest.raises(pe.ElaborationError, match="unknown label '2.2'"):
        pp.parse_proof_text(text)


# --------------------------------------------------------------------
# Context bookkeeping must preserve source origins and the core entry shape.
# This regression exercises declarations, an arbitrary binding, and a nested
# rule-below subproof in one proof.
# --------------------------------------------------------------------

def test_proof_context_tracking_preserves_origins_and_core_entry_shape():
    text = (
        "1. Let A be a closed formula. (Declare)\n"
        "2. forall x, x = x. (Universal Generalization from subproof below)\n"
        "begin subproof\n"
        " 2.1. let c be arbitrary. (Fresh Variable)\n"
        " 2.2. c = c. (Reflexivity)\n"
        "end subproof\n"
    )
    entries, _ = pp.parse_proof_text(text)

    assert [e[0] for e in entries] == ["1", "2"]
    assert entries[0][1] is None
    assert entries[0][2][0] == "declare"
    assert [d.name for d in entries[0][2][1]] == ["A"]
    assert entries[1][0] == "2"
    assert isinstance(entries[1][2][1], pl.UniversalGeneralizationRule)
    inner = entries[1][3]
    assert [line[0] for line in inner] == ["2.1", "2.2"]
    assert inner[0][2] == ("arbitrary",)
    assert isinstance(inner[1][2][1], pl.ReflexivityRule)

    assert set(entries.origin_by_label) == {"1", "2", "2.1", "2.2"}
    assert all(not origin.synthetic for origin in entries.origin_by_label.values())
    assert entries.origin_by_label["2.1"].span.original_text.strip() == "2.1. let c be arbitrary. (Fresh Variable)"

    ok, err = pl.Proof(entries).check_detailed()
    assert ok, err


def test_typed_declarations_register_into_proof_context():
    """Verify that typed declarations (e.g., 'Let x be a natural number')
    are registered in `ProofContext`, the same as ones made through
    `elaborate_compound_declaration` -- both paths agree on where a
    declaration ends up.
    """
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof("1. Let x be a natural number. (Declaration)\n")
    context.elaborate_entry(surface.entries[0])

    declaration = context.context.lookup_declaration("x")
    assert declaration is not None
    assert declaration.kind == pl.DeclarationKind.OBJECT
    assert declaration.type_name == "a natural number"



@pytest.mark.parametrize("membership", ["a is in X", "a is not in X"])
def test_compound_declaration_keeps_following_membership_formula_as_a_premise(membership):
    """A membership formula must not become part of the preceding type descriptor."""
    entries, _ = pp.parse_proof_text(
        f"1. Let X be any set, {membership}. (Declaration)\n"
    )

    (_label, formula, (tag, declarations)), = entries
    assert tag == "premise"
    assert [declaration.name for declaration in declarations] == ["X"]
    assert declarations[0].type_name == "any set"
    assert pl._ast_eq(formula, pp.parse_formula(membership))


def test_compound_declaration_keeps_membership_declaration_separate_from_descriptor():
    entries, _ = pp.parse_proof_text(
        "1. Let X be any set, a in X. (Declaration)\n"
    )

    (_label, formula, (tag, declarations)), = entries
    assert tag == "premise"
    by_name = {declaration.name: declaration for declaration in declarations}
    assert set(by_name) == {"X", "a"}
    assert by_name["X"].type_name == "any set"
    assert pl._ast_eq(formula, pp.parse_formula("a is in X"))


def test_compound_relation_descriptor_keeps_its_properties_before_membership_premise():
    text = (
        "1. Let X be any set, R be a reflexive, symmetric relation on X, "
        "a in X. (Declaration)\n"
    )
    entries, _ = pp.parse_proof_text(text)

    (_label, formula, (tag, declarations)), = entries
    assert tag == "premise"
    by_name = {declaration.name: declaration for declaration in declarations}
    assert set(by_name) == {"X", "R", "a"}
    assert by_name["X"].type_name == "any set"
    assert "a in X" not in by_name["R"].type_name
    assert pl._ast_eq(formula, pp.parse_formula("a is in X"))
    metadata = dict(by_name["R"].metadata)
    assert metadata["carrier"] == "X"
    assert set(metadata["properties"]) == {"reflexive", "symmetric"}

