"""Pin each set-theory red-team rejection to the condition it exercises."""

from pathlib import Path

from .support import fl, pl, st, v, c
import SyLoPy.source.validate_all_proofs as mp


_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "testSetTheory"
_FIXTURES = (
    "red_team_separation.txt",
    "red_team_replacement.txt",
    "red_team_set_property.txt",
    "red_team_set_equality.txt",
    "red_team_empty_set_property.txt",
    "red_team_subset_proof.txt",
)


def _titles(text: str) -> dict[str, str]:
    titles = {}
    number = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            head = stripped[2:].split(":", 1)
            if len(head) == 2 and head[0].isdigit():
                number = head[0]
        elif number is not None and stripped.startswith("## ") and not stripped.startswith("### "):
            titles.setdefault(number, stripped[3:])
    return titles


def _results(filename: str):
    text = (_FIXTURE_DIR / filename).read_text(encoding="utf-8")
    results = mp.run_multi_proof_file(
        text,
        axioms=mp.BARE_PROOF_AXIOMS,
        rules=mp.BARE_PROOF_RULES,
        declarations=mp.BARE_PROOF_DECLARATIONS,
    )
    titles = _titles(text)
    assert [number for number, *_rest in results] == sorted(titles, key=int), (
        f"{filename}: lost a proof case; titles={sorted(titles, key=int)}"
    )
    return [(number, expected, ok, message, crashed, titles[number])
            for number, expected, ok, message, crashed in results]


def test_every_red_team_fixture_is_complete_and_decided_for_its_named_reason():
    for filename in _FIXTURES:
        results = _results(filename)
        assert results, f"{filename}: no cases found"
        for number, expected, ok, message, crashed, title in results:
            assert not crashed, f"{filename} case {number} raised a rule exception: {message}"
            if title.startswith("Proof that"):
                assert expected and ok, f"{filename} case {number} is a valid boundary example: {message}"
                continue

            assert title.startswith("Invalid: "), f"{filename} case {number} has no expected validity marker"
            condition = title.removeprefix("Invalid: ").split(" — ", 1)[0]
            assert not expected, f"{filename} case {number} was not marked invalid"
            assert not ok, f"{filename} case {number} was accepted: {condition}"
            assert message, f"{filename} case {number} was rejected without a diagnostic"
            assert condition.casefold() in message.casefold(), (
                f"{filename} case {number} should identify {condition!r}, got: {message}"
            )


def _replacement_instance(B_xy_factory, *, A_ante=None, A_cons=None, cons_x="x",
                          cons_y="y", unique_rhs="y"):
    """Build one AST-level Replacement schema instance.

    AST-level tests can express a genuinely free VariableTerm named C or z in
    B(x, y). In surface text, those unbound names are constants, not variables,
    so those capture guards need direct rule tests as well as proof fixtures.
    """
    x, y, z = v("x"), v("y"), v("z")
    A_ante = A_ante if A_ante is not None else c("A")
    A_cons = A_cons if A_cons is not None else c("A")
    B_xy = B_xy_factory(x, y)
    B_xz = B_xy_factory(x, z)
    antecedent = fl.ForAll("x", fl.Implies(
        st.membership_formula(x, A_ante),
        fl.Exists("y", fl.And(B_xy, fl.ForAll("z", fl.Implies(
            B_xz, fl.Equals(z, v(unique_rhs))
        )))),
    ))
    cons_x_t, cons_y_t = v(cons_x), v(cons_y)
    B_cons = B_xy_factory(cons_x_t, cons_y_t)
    consequent = fl.Exists("C", fl.ForAll(cons_y, fl.Iff(
        st.membership_formula(cons_y_t, v("C")),
        fl.Exists(cons_x, fl.And(st.membership_formula(cons_x_t, A_cons), B_cons)),
    )))
    return fl.Implies(antecedent, consequent)


def test_replacement_rejects_the_image_set_variable_free_in_B():
    rule = st.ReplacementSchemaRule()
    instance = _replacement_instance(
        lambda x, y: fl.And(fl.Equals(y, x), fl.AtomicFormula("R", [v("C")]))
    )
    assert not rule.applies([], instance)
    reason = rule.explain_in_context([], instance, pl.RuleContext())
    assert reason is not None
    assert "image-set variable C must not occur free" in reason


def test_replacement_rejects_the_uniqueness_variable_free_in_B():
    rule = st.ReplacementSchemaRule()
    instance = _replacement_instance(
        lambda x, y: fl.And(fl.Equals(y, x), fl.AtomicFormula("R", [v("z")]))
    )
    assert not rule.applies([], instance)
    reason = rule.explain_in_context([], instance, pl.RuleContext())
    assert reason is not None
    assert "uniqueness variable z must not occur free" in reason
