


import pytest

from .support import pl, fl, tl, atom, prop, c, v, fn, A, B, C, assert_valid, assert_invalid


def test_label_scope_parent_visibility_and_child_isolation():
    root = pl.LabelScope()
    root["1"] = A
    child = root.child()
    child["1.1"] = B

    assert child["1"] is A
    assert child["1.1"] is B
    assert "1.1" not in root
    with pytest.raises(KeyError):
        _ = root["missing"]


def test_subproof_outer_context_is_boundary_limited():
    outer = [A, B]
    sp = pl.SubproofRecord(C, [C], outer_context_ref=outer, boundary_index=1)
    outer.append(C)
    assert list(sp.get_outer_context()) == [A]
    assert list(sp.get_outer_context()) == [A]  # each call is a fresh iterator


@pytest.mark.parametrize(
    "entry,expected_block,expected_label,expected_phi",
    [
        (("subproof", []), True, None, None),
        (("2", "subproof", []), True, "2", None),
        ((A, ("premise",)), False, None, A),
        (("1", A, ("premise",)), False, "1", A),
        (("1", A, ("rule_below", pl.ConditionalIntroductionRule()), []), False, "1", A),
    ],
)
def test_classify_entry_shapes(entry, expected_block, expected_label, expected_phi):
    parsed = pl._classify_entry(entry)
    assert not isinstance(parsed, str)
    assert parsed.is_subproof_block is expected_block
    assert parsed.label == expected_label
    assert parsed.phi is expected_phi


@pytest.mark.parametrize("entry", [None, ("a", "b", "c", "d", "e")])
def test_classify_entry_rejects_invalid_shapes(entry):
    assert isinstance(pl._classify_entry(entry), str)


def test_simple_valid_proof():
    entries = [
        ("1", A, ("premise",)),
        ("2", fl.Implies(A, B), ("premise",)),
        ("3", B, ("rule", pl.ModusPonensRule(), ["1", "2"])),
    ]
    assert_valid(entries)


def test_premise_and_axiom_restrictions_are_structural():
    premise = atom("P", c("a"))
    axiom = fl.ForAll("x", atom("Q", v("x")))
    entries = [
        ("1", atom("P", c("a")), ("premise",)),
        ("2", fl.ForAll("x", atom("Q", v("x"))), ("axiom",)),
    ]
    assert_valid(entries, premises=[premise], axioms=[axiom])


@pytest.mark.parametrize("tag,kwargs", [("premise", {"premises": [B]}), ("axiom", {"axioms": [B]})])
def test_unregistered_premise_or_axiom(tag, kwargs):
    err = assert_invalid(
        [("7", A, (tag,))],
        pl.CATEGORY_UNREGISTERED_FORMULA,
        label="7",
        **kwargs,
    )
    assert "does not match" in err.detail


def test_empty_allowed_lists_mean_unrestricted_premises_and_axioms():
    assert_valid([("1", A, ("premise",)), ("2", B, ("axiom",))])


def test_not_closed_failure():
    assert_invalid(
        [("1", atom("P", v("x")), ("premise",))],
        pl.CATEGORY_NOT_CLOSED,
        label="1",
    )


@pytest.mark.parametrize(
    "entry,category",
    [
        ("not a tuple", pl.CATEGORY_MALFORMED_ENTRY),
        (("1", A, None), pl.CATEGORY_MALFORMED_JUSTIFICATION),
        (("1", A, ("mystery",)), pl.CATEGORY_UNKNOWN_TAG),
    ],
)
def test_malformed_entry_justification_and_unknown_tag(entry, category):
    assert_invalid([entry], category)


@pytest.mark.parametrize("tag", ["assume", "arbitrary"])
def test_assume_and_arbitrary_illegal_at_top_level(tag):
    assert_invalid(
        [("1", A, (tag,))],
        pl.CATEGORY_WRONG_POSITION,
        label="1",
    )


def test_empty_subproof_and_bad_opening():
    assert_invalid(
        [("2", "subproof", [])],
        pl.CATEGORY_EMPTY_SUBPROOF,
    )
    assert_invalid(
        [("2", "subproof", [("2.1", A, ("premise",))])],
        pl.CATEGORY_BAD_OPENING,
        label="2.1",
    )


def test_assumption_illegal_after_first_subproof_line():
    entries = [
        ("2", "subproof", [
            ("2.1", A, ("assume",)),
            ("2.2", B, ("assume",)),
        ]),
    ]
    assert_invalid(entries, pl.CATEGORY_WRONG_POSITION, label="2.2")


def test_missing_rule_below_subproof():
    entries = [
        ("1", fl.Implies(A, A), ("rule_below", pl.ConditionalIntroductionRule())),
    ]
    assert_invalid(entries, pl.CATEGORY_MISSING_SUBPROOF, label="1")


def test_valid_conditional_introduction_with_inline_subproof():
    entries = [
        (
            "1",
            fl.Implies(A, A),
            ("rule_below", pl.ConditionalIntroductionRule()),
            [
                ("1.1", A, ("assume",)),
                ("1.2", A, ("rule", pl.ReiterationRule(), ["1.1"])),
            ],
        )
    ]
    assert_valid(entries)


def test_rule_below_validates_inner_lines_before_outer_rule():
    entries = [
        (
            "1",
            fl.Implies(A, B),
            ("rule_below", pl.ConditionalIntroductionRule()),
            [
                ("1.1", A, ("assume",)),
                ("1.2", B, ("rule", pl.ReiterationRule(), ["missing"])),
            ],
        )
    ]
    assert_invalid(entries, pl.CATEGORY_BAD_REFERENCE, label="1.2")


def test_bad_reference_and_rule_mismatch_are_distinct():
    bad_ref = [
        ("1", A, ("premise",)),
        ("2", A, ("rule", pl.ReiterationRule(), ["99"])),
    ]
    assert_invalid(bad_ref, pl.CATEGORY_BAD_REFERENCE, label="2")

    mismatch = [
        ("1", A, ("premise",)),
        ("2", B, ("rule", pl.ReiterationRule(), ["1"])),
    ]
    assert_invalid(mismatch, pl.CATEGORY_RULE_MISMATCH, label="2")


def test_rule_arity_mismatch():
    entries = [
        ("1", A, ("premise",)),
        ("2", B, ("rule", pl.ModusPonensRule(), ["1"])),
    ]
    assert_invalid(entries, pl.CATEGORY_ARITY_MISMATCH, label="2")


def test_unrecognized_rule_when_proof_uses_restricted_registry():
    entries = [
        ("1", A, ("premise",)),
        ("2", fl.Or(A, B), ("rule", pl.DisjunctionIntroductionRule(), ["1"])),
    ]
    assert_invalid(
        entries,
        pl.CATEGORY_UNRECOGNIZED_RULE,
        label="2",
        rules=[pl.ReiterationRule()],
    )


class ExplodingRule(pl.InferenceRule):
    name = "Exploding"
    premise_arity = 1

    def applies(self, candidates, phi):
        raise RuntimeError("boom")


def test_rule_exception_becomes_structured_failure():
    entries = [
        ("1", A, ("premise",)),
        ("2", B, ("rule", ExplodingRule(), ["1"])),
    ]
    err = assert_invalid(
        entries,
        pl.CATEGORY_RULE_RAISED,
        label="2",
        rules=[ExplodingRule()],
    )
    assert "boom" in err.detail


def test_inner_subproof_can_cite_outer_line():
    entries = [
        ("1", A, ("premise",)),
        (
            "2",
            fl.Implies(B, A),
            ("rule_below", pl.ConditionalIntroductionRule()),
            [
                ("2.1", B, ("assume",)),
                ("2.2", A, ("rule", pl.ReiterationRule(), ["1"])),
            ],
        ),
    ]
    assert_valid(entries)


def test_closed_subproof_labels_do_not_escape():
    entries = [
        (
            "1",
            fl.Implies(A, A),
            ("rule_below", pl.ConditionalIntroductionRule()),
            [
                ("1.1", A, ("assume",)),
                ("1.2", A, ("rule", pl.ReiterationRule(), ["1.1"])),
            ],
        ),
        ("2", A, ("rule", pl.ReiterationRule(), ["1.2"])),
    ]
    assert_invalid(entries, pl.CATEGORY_BAD_REFERENCE, label="2")


def test_standalone_subproof_can_be_cited_by_disjunction_elimination():
    entries = [
        ("1", fl.Or(A, B), ("premise",)),
        ("2", "subproof", [
            ("2.1", A, ("assume",)),
            ("2.2", C, ("premise",)),
        ]),
        ("3", "subproof", [
            ("3.1", B, ("assume",)),
            ("3.2", C, ("premise",)),
        ]),
        ("4", C, ("rule", pl.DisjunctionEliminationRule(), ["1", "2", "3"])),
    ]
    assert_valid(entries)


def test_detailed_error_location_and_rendering():
    entries = [
        ("10", A, ("premise",)),
        ("11", B, ("rule", pl.ReiterationRule(), ["10"])),
    ]
    proof = pl.Proof(entries, declarations=pl.infer_declarations([A, B]))
    ok, err = proof.check_detailed()
    assert not ok
    assert err.location == "Line 11"
    assert err.label == "11"
    assert str(err).startswith("Line 11:")

    ok2, message = proof.check()
    assert not ok2
    assert message == str(err)


def test_named_rule_placeholder_resolves_registered_rule():
    zero = c("Zero")
    induction = pl.InductionRule("Nat", zero, "Succ")
    conclusion = fl.ForAll("x", fl.Implies(atom("Nat", v("x")), atom("P", v("x"))))
    base = atom("P", zero)
    step = fl.ForAll(
        "n",
        fl.Implies(
            fl.And(atom("Nat", v("n")), atom("P", v("n"))),
            atom("P", tl.FunctionTerm("Succ", [v("n")])),
        ),
    )
    entries = [
        ("1", base, ("premise",)),
        ("2", step, ("premise",)),
        ("3", conclusion, ("rule", pl.NamedRulePlaceholder("Induction"), ["1", "2"])),
    ]
    assert_valid(entries, rules=pl.default_rules() + [induction])


def test_named_rule_placeholder_fails_without_type_rule():
    entries = [
        ("1", A, ("premise",)),
        ("2", B, ("premise",)),
        ("3", C, ("rule", pl.NamedRulePlaceholder("Induction"), ["1", "2"])),
    ]
    assert_invalid(entries, pl.CATEGORY_UNRECOGNIZED_RULE, label="3")


def test_default_rules_returns_fresh_instances_and_all_expected_names():
    r1 = pl.default_rules()
    r2 = pl.default_rules()
    assert len(r1) == 23
    assert all(a is not b for a, b in zip(r1, r2))
    assert {r.name for r in r1} >= {
        "ModusPonens", "ProofByContradiction", "UniversalInstantiation",
        "ExistentialElimination", "Explosion", "Reflexivity", "Transitivity",
    }


def test_declaration_only_line_registers_vocabulary_without_creating_a_citable_formula():
    declarations = [
        pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA),
    ]
    entries = [
        ("1", None, ("declare", declarations)),
        ("2", A, ("premise",)),
        ("3", A, ("rule", pl.ReiterationRule(), ["2"])),
    ]
    assert_valid(entries)


def test_premise_declaration_prefix_declares_symbols_before_validating_formula():
    declarations = [
        pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA),
        pl.Declaration("B", pl.DeclarationKind.CLOSED_FORMULA),
    ]
    entries = [
        ("1", fl.Implies(A, B), ("premise", declarations)),
        ("2", A, ("premise",)),
    ]
    assert_valid(entries)


def test_undeclared_symbol_is_rejected():
    err = assert_invalid(
        [("1", atom("P", c("a")), ("premise",))],
        pl.CATEGORY_UNDECLARED_SYMBOL,
        label="1",
        auto_declare=False,
    )
    assert "a" in err.detail


def test_declaration_scope_does_not_leak_out_of_subproof():
    entries = [
        ("0", None, ("declare", [pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA)])),
        ("1", "subproof", [
            ("1.1", A, ("assume",)),
            ("1.2", None, ("declare", [pl.Declaration("b", pl.DeclarationKind.OBJECT)])),
            ("1.3", atom("P", c("b")), ("declare",)),
        ]),
        ("2", atom("P", c("b")), ("premise",)),
    ]
    err = assert_invalid(entries, pl.CATEGORY_UNDECLARED_SYMBOL, label="2", auto_declare=False)
    assert "b" in err.detail


def test_duplicate_declaration_is_rejected():
    entries = [
        ("1", None, ("declare", [pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA)])),
        ("2", None, ("declare", [pl.Declaration("A", pl.DeclarationKind.CLOSED_FORMULA)])),
    ]
    assert_invalid(entries, pl.CATEGORY_DECLARATION_CONFLICT, label="2")


def test_theory_declarations_supply_builtin_symbols():
    declarations = [
        pl.Declaration("Nat", pl.DeclarationKind.PREDICATE, arity=1),
        pl.Declaration("Zero", pl.DeclarationKind.OBJECT),
        pl.Declaration("Succ", pl.DeclarationKind.FUNCTION, arity=1),
    ]
    entries = [
        ("1", atom("Nat", c("Zero")), ("premise",)),
        ("2", fl.ForAll("x", fl.Implies(atom("Nat", v("x")), atom("Nat", fn("Succ", v("x"))))), ("axiom",)),
    ]
    assert_valid(entries, axioms=[entries[1][1]], declarations=declarations)




