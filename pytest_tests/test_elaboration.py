


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
# ProofContext integration (todos.txt "ProofContext integration", phase 2).
#
# `_ElaborationContext` is migrating its lexical bookkeeping onto
# `ProofContext`. The first step is a pure dual-write: every declaration
# registered through `register_declaration` is now also declared into a
# `ProofContext` instance, alongside the pre-existing `DeclarationScope`.
# Nothing yet *reads* from the new context, so these tests only pin down
# that the write itself happens and stays consistent -- not any change in
# validator-visible behavior (the full suite above already guards that).
# --------------------------------------------------------------------

def test_compound_declaration_registers_into_proof_context_alongside_declaration_scope():
    context = pp._ElaborationContext(pp.default_theory_environment())
    surface = pp.parse_surface_proof("1. Let X be any set. (Declaration)\n")
    context.elaborate_entry(surface.entries[0])

    declaration = context.context.lookup_declaration("X")
    assert declaration is not None
    assert declaration.kind == pl.DeclarationKind.OBJECT
    assert declaration == context.declarations.lookup("X")


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
# ProofContext integration, phase 2 continued: `elaborate_subproof_body`
# gives every subproof its own child `ProofContext`, and `elaborate_entry`
# now also dual-writes each label into it.
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


@pytest.mark.xfail(
    reason="self.declarations (DeclarationScope) is not yet subproof-scoped "
           "the way self.context (ProofContext) now is -- see todos.txt's "
           "'ProofContext integration' project, phase 2. A compound "
           "declaration name reused across sibling subproofs still "
           "collides via that pre-existing flat structure, independent "
           "of anything ProofContext-related. Tracked here so this test "
           "flips to an unexpected pass (visible, not silent) the day "
           "self.declarations gets the same scoping treatment.",
)
def test_sibling_subproofs_cannot_yet_reuse_a_compound_declaration_name():
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
        context.elaborate_entry(entry)


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
