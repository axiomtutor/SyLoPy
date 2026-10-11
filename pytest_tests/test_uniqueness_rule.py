"""Tests for `UniquenessRule`.

From `exists Y, B(Y)` and `B(c) -> c = d` it infers
`exists W, (B(W) and forall V, (B(V) -> V = W))`. The shape checks are tested
on formulas. What makes the rule sound -- the constant `c` must really be
arbitrary -- depends on the proof around the rule, which `RuleContext` carries:
the constants a plain declaration introduced, and everything the proof took
for granted. That part is tested twice: with hand-built contexts, and through
the validator, which is what builds them.
"""

import pytest

from .support import assert_invalid, assert_valid, pl, fl, tl, pp, mp, st, c, v


def formula(text):
    return pp.parse_formula(text, set())


EXISTENCE = "exists Y, Y = a"
STEP = "if X = a then X = Y"
CONCLUSION = "exists Y, (Y = a and forall X, (X = a -> X = Y))"


def context(given=(), assumptions=(), arbitrary=("X",)):
    """A rule context with `X` -- the constant the shape tests generalize --
    arbitrary unless a test says otherwise."""
    return pl.RuleContext([formula(t) for t in given], [formula(t) for t in assumptions], arbitrary)


def applies(existence=EXISTENCE, step=STEP, conclusion=CONCLUSION, ctx=None):
    rule = pl.UniquenessRule()
    candidates = [formula(existence), formula(step)]
    return rule.applies_in_context(candidates, formula(conclusion), ctx if ctx is not None else context())


# --------------------------------------------------------------------
# Shapes
# --------------------------------------------------------------------

def test_accepts_the_unique_existence_form():
    assert applies()


def test_the_cited_lines_may_come_in_either_order():
    rule = pl.UniquenessRule()
    candidates = [formula(STEP), formula(EXISTENCE)]
    assert rule.applies_in_context(candidates, formula(CONCLUSION), context())


def test_the_conclusion_may_name_its_bound_variables_anything():
    assert applies(conclusion="exists W, (W = a and forall V, (V = a -> V = W))")


def test_equalities_may_be_written_either_way_round():
    assert applies(conclusion="exists Y, (Y = a and forall X, (X = a -> Y = X))")
    assert applies(step="if X = a then Y = X")


def test_a_property_with_several_parts_is_matched_whole():
    existence = "exists Y, (In(a, Y) and In(b, Y))"
    step = "if In(a, X) and In(b, X) then X = Y"
    conclusion = "exists Y, (In(a, Y) and In(b, Y) and forall X, ((In(a, X) and In(b, X)) -> X = Y))"
    assert applies(existence, step, conclusion)


def test_a_parameter_of_the_property_may_be_any_other_constant():
    assert applies("exists Y, In(Y, W)", "if In(X, W) then X = Y",
                   "exists Y, (In(Y, W) and forall X, (In(X, W) -> X = Y))")


@pytest.mark.parametrize("conclusion", [
    # the uniqueness clause is missing
    "exists Y, Y = a",
    # nothing says Y itself has the property
    "exists Y, forall X, (X = a -> X = Y)",
    # the uniqueness clause is about a different property
    "exists Y, (Y = a and forall X, (X = b -> X = Y))",
    # and about a different witness
    "exists Y, (Y = a and forall X, (X = a -> X = a))",
    # the property is not the one the existence line states
    "exists Y, (Y = b and forall X, (X = b -> X = Y))",
    # both bound variables share a name: the inner one captures
    "exists Y, (Y = a and forall Y, (Y = a -> Y = Y))",
    # a universal where an existential belongs
    "forall Y, (Y = a and forall X, (X = a -> X = Y))",
])
def test_rejects_a_conclusion_that_is_not_the_unique_existence_form(conclusion):
    assert not applies(conclusion=conclusion)


@pytest.mark.parametrize("existence,step", [
    # the conditional is about a different property
    (EXISTENCE, "if X = b then X = Y"),
    # it does not conclude equality
    (EXISTENCE, "if X = a then In(X, Y)"),
    # it is not a conditional
    (EXISTENCE, "X = a"),
    # the existence line is not existential
    ("Y = a", STEP),
    # c and d must be different constants
    (EXISTENCE, "if X = a then X = X"),
    # and d must be a constant, not a compound term
    (EXISTENCE, "if X = a then X = f(a)"),
])
def test_rejects_cited_lines_of_the_wrong_shape(existence, step):
    assert not applies(existence, step)


@pytest.mark.parametrize("existence,step,conclusion,parameter", [
    # The simplest case: the constant generalized is the parameter `a`.
    (EXISTENCE, "if a = a then a = Y",
     "exists W, (W = a and forall V, (V = a -> V = W))", "a"),
    # The same with a property whose only parameter `W` is the constant: the
    # step `In(W, W) -> W = Y` is an instance of B at W, and everything else
    # about the lines is in order, so only the parameter check stands in the way.
    ("exists Y, In(Y, W)", "if In(W, W) then W = Y",
     "exists V, (In(V, W) and forall U, (In(U, W) -> U = V))", "W"),
])
def test_rejects_when_the_arbitrary_constant_is_a_parameter_of_the_property(existence, step, conclusion, parameter):
    # With nothing stopping it but the parameter check: the constant is
    # arbitrary as far as the context knows, and no hypothesis mentions it.
    ctx = context(arbitrary=[parameter])
    assert not applies(existence, step, conclusion, ctx)


def test_wrong_number_of_citations():
    rule = pl.UniquenessRule()
    assert not rule.applies_in_context([formula(EXISTENCE)], formula(CONCLUSION), context())
    assert not rule.applies_in_context([], formula(CONCLUSION), context())


def test_it_is_among_the_default_rules():
    assert any(isinstance(rule, pl.UniquenessRule) for rule in pl.default_rules())


# --------------------------------------------------------------------
# The context: which constants are arbitrary, and what mentions them
# --------------------------------------------------------------------

def test_asked_outside_a_proof_it_never_applies():
    # Nothing outside a proof can show that a constant is arbitrary, so the
    # rule says no -- even to lines that are exactly right otherwise.
    rule = pl.UniquenessRule()
    candidates = [formula(EXISTENCE), formula(STEP)]
    assert not rule.applies(candidates, formula(CONCLUSION))
    assert not rule.applies_in_context(candidates, formula(CONCLUSION), pl.RuleContext())


def test_the_constant_must_be_one_the_context_calls_arbitrary():
    assert applies(ctx=context(arbitrary=["X"]))
    # every other name in the lines is arbitrary, X is not
    assert not applies(ctx=context(arbitrary=["a", "Y", "Z"]))
    assert not applies(ctx=context(arbitrary=[]))


def test_a_compound_term_cannot_be_the_arbitrary_constant():
    # `f(a)` is an instance of B and the step concludes `f(a) = Y`, but only a
    # constant can be generalized. Every name in sight is declared arbitrary
    # here, so it is the shape of the term that refuses.
    ctx = context(arbitrary=["a", "f", "W", "X", "Y"])
    assert not applies("exists Y, In(Y, W)", "if In(f(a), W) then f(a) = Y",
                       "exists Y, (In(Y, W) and forall X, (In(X, W) -> X = Y))", ctx)


def test_a_given_statement_that_mentions_the_constant_blocks_it():
    assert not applies(ctx=context(given=["In(X, W)"]))


def test_an_assumption_that_mentions_the_constant_blocks_it():
    assert not applies(ctx=context(assumptions=["In(X, W)"]))


def test_statements_about_other_constants_do_not():
    assert applies(ctx=context(given=["In(a, W)", "Y = a"], assumptions=["In(b, W)"]))


def test_the_context_reports_what_it_was_given():
    given, assumed = [formula("P(a)")], [formula("Q(a)")]
    ctx = pl.RuleContext(given, assumed, ["X", "Y"])
    assert ctx.hypotheses == (given[0], assumed[0])
    assert ctx.arbitrary_constants == frozenset({"X", "Y"})
    assert pl.RuleContext().hypotheses == ()
    assert pl.RuleContext().arbitrary_constants == frozenset()


def test_every_other_rule_ignores_the_context_by_default():
    rule = pl.ModusPonensRule()
    ctx = pl.RuleContext([formula("P(X)")], [], [])
    candidates = [formula("P(a)"), formula("if P(a) then Q(a)")]
    assert rule.applies_in_context(candidates, formula("Q(a)"), ctx) == rule.applies(candidates, formula("Q(a)"))


# --------------------------------------------------------------------
# Through the validator: the context it builds
# --------------------------------------------------------------------

def run(text, axioms=(), declarations=None):
    results = mp.run_multi_proof_file(
        "# 1\n## Proof that\n### x\n" + text,
        axioms=list(st.SET_THEORY_ENVIRONMENT.axioms) + list(axioms),
        rules=pl.default_rules() + st.SET_THEORY_ENVIRONMENT.rules,
        declarations=declarations,
    )
    ((_number, _expected, ok, message, crashed),) = results
    assert not crashed, message
    return ok, message


def assert_rejected_at(text, line, **kwargs):
    """The proof is refused, and at the Uniqueness line: everything before it
    is in order (a refusal anywhere else would prove nothing)."""
    ok, message = run(text, **kwargs)
    assert not ok
    assert f"Line {line}:" in message and "'Uniqueness' does not justify" in message, message


_HEAD = """
1. Let a, W be any set. (Declaration)
2. a = a. (Reflexivity)
3. Exists Y, Y = a. (Existential Introduction from 2)
4. Let Y be such a set. (Existence from 3)
"""
_DECLARE_X = "5. Let X be any set. (Declaration)\n"


def _step(n):
    """Line n: `If X = a then X = Y`, derived from the witness Y."""
    return (f"{n}. If X = a then X = Y. (Conditional Introduction from subproof below)\n"
            f" {n}.1. X = a. (Assumption for Conditional Introduction)\n"
            f" {n}.2. a = Y. (Symmetry from 4)\n"
            f" {n}.3. X = Y. (Transitivity from {n}.1, {n}.2)\n")


def _uniqueness(n, step_label):
    return f"{n}. Exists Y, (Y = a and forall X, (X = a -> X = Y)). (Uniqueness, 3, {step_label})\n"


def proof_with(extra_line=None):
    """The unique-existence proof, `X` declared on line 5, with one more line
    (numbered 6) between the declaration and the step if `extra_line` is
    given. Returns the text and the number of the Uniqueness line."""
    text = _HEAD + _DECLARE_X
    n = 6
    if extra_line is not None:
        text += extra_line + "\n"
        n = 7
    return text + _step(n) + _uniqueness(n + 1, n), n + 1


def test_control_the_unconstrained_proof_is_accepted():
    text, _line = proof_with()
    ok, message = run(text)
    assert ok, message


# One way each of constraining X, and a harmless twin that says the same kind of
# thing about `a` instead. The first must stop X being arbitrary, the second
# must not -- and for each the line that does it is a different one of the
# validator's recording points.
_X_IN_W = formula("In(X, W)")
_A_IN_W = formula("In(a, W)")
_CONSTRAINTS = {
    "a premise": ("6. In({0}, W). (Premise)", ()),
    "a cited axiom": ("6. In({0}, W). (Axiom)", None),
    "a declaration line that states a formula": ("6. In({0}, W). (Declaration)", ()),
    "a Define bundle": ("6. Define Z = a, and V = {0}. (Existence from 3)", ()),
}


def _constraint(kind, constant):
    template, axioms = _CONSTRAINTS[kind]
    extra_axioms = [formula(f"In({constant}, W)")] if axioms is None else list(axioms)
    return template.format(constant), extra_axioms


@pytest.mark.parametrize("kind", list(_CONSTRAINTS))
def test_a_statement_taken_for_granted_about_the_constant_is_refused(kind):
    line, axioms = _constraint(kind, "X")
    text, uniqueness_line = proof_with(line)
    assert_rejected_at(text, uniqueness_line, axioms=axioms)


@pytest.mark.parametrize("kind", list(_CONSTRAINTS))
def test_the_same_statement_about_another_constant_is_fine(kind):
    line, axioms = _constraint(kind, "a")
    text, _uniqueness_line = proof_with(line)
    ok, message = run(text, axioms=axioms)
    assert ok, message


_NESTED = _HEAD + _DECLARE_X + """
6. {assumed} -> Exists Y, (Y = a and forall X, (X = a -> X = Y)). (Conditional Introduction from subproof below)
 6.1. {assumed}. (Assumption for Conditional Introduction)
 6.2. If X = a then X = Y. (Conditional Introduction from subproof below)
  6.2.1. X = a. (Assumption for Conditional Introduction)
  6.2.2. a = Y. (Symmetry from 4)
  6.2.3. X = Y. (Transitivity from 6.2.1, 6.2.2)
 6.3. Exists Y, (Y = a and forall X, (X = a -> X = Y)). (Uniqueness, 3, 6.2)
"""


def test_an_open_assumption_about_the_constant_is_refused():
    assert_rejected_at(_NESTED.format(assumed="In(X, W)"), "6.3")


def test_an_open_assumption_about_other_constants_is_fine():
    ok, message = run(_NESTED.format(assumed="In(a, W)"))
    assert ok, message


def test_a_closed_subproofs_assumption_no_longer_counts():
    # The assumption `In(X, W)` is discharged by line 6; line 8 is back at the
    # top level, where nothing assumed mentions X.
    text = (_HEAD + _DECLARE_X
            + "6. In(X, W) -> X = X. (Conditional Introduction from subproof below)\n"
              " 6.1. In(X, W). (Assumption for Conditional Introduction)\n"
              " 6.2. X = X. (Reflexivity)\n"
            + _step(7) + _uniqueness(8, 7))
    ok, message = run(text)
    assert ok, message


def test_a_constant_the_proof_was_handed_is_not_arbitrary():
    # The same proof, with X declared up front instead of on line 5.
    text = _HEAD + _step(5) + _uniqueness(6, 5)
    handed = [pl.Declaration("X", pl.DeclarationKind.OBJECT, type_name="set")]
    assert_rejected_at(text, 6, declarations=handed)


def test_an_axiom_about_a_constant_the_proof_never_declares_cannot_make_it_arbitrary():
    # The theory knows a constant k and an axiom says k is not b. The proof
    # then "derives" that anything equal to a or b is a -- from the axiom,
    # which mentions only k -- and generalizes over k. If k could pass for
    # arbitrary, this would conclude that exactly one thing equals a or b, for
    # any a and b.
    text = """
1. Let a, b be any set. (Declaration)
2. a = a. (Reflexivity)
3. a = a or a = b. (Disjunction Introduction from 2)
4. Exists Y, (Y = a or Y = b). (Existential Introduction from 3)
5. not (k = b). (Axiom)
6. If (k = a or k = b) then k = a. (Conditional Introduction from subproof below)
 6.1. k = a or k = b. (Assumption for Conditional Introduction)
 6.2. k = a. (Disjunctive Syllogism from 6.1, 5)
7. Exists Y, ((Y = a or Y = b) and forall X, ((X = a or X = b) -> X = Y)). (Uniqueness, 4, 6)
"""
    axiom = formula("not (k = b)")
    declared = [pl.Declaration("k", pl.DeclarationKind.OBJECT, type_name="constant")]
    assert_rejected_at(text, 7, axioms=[axiom], declarations=declared)


def test_a_constrained_witness_cannot_be_the_arbitrary_constant():
    # Two things satisfy B (a and b), so "exactly one" is false. Line 6 pins the
    # witness Y down to a; then "B(Y) -> Y = a" is provable, and if Y were
    # allowed to play the arbitrary constant, Uniqueness would conclude the
    # false statement on line 8. Y is named from an existential, not declared
    # plainly, so it is not arbitrary and the rule refuses.
    text = """
1. Let a, b be any set. (Declaration)
2. a = a. (Reflexivity)
3. a = a or a = b. (Disjunction Introduction from 2)
4. Exists Y, (Y = a or Y = b). (Existential Introduction from 3)
5. Let Y be such a set. (Existence from 4)
6. Y = a. (Premise)
7. If (Y = a or Y = b) then Y = a. (Conditional Introduction from subproof below)
 7.1. Y = a or Y = b. (Assumption for Conditional Introduction)
 7.2. Y = a. (Reiteration from 6)
8. Exists Y, ((Y = a or Y = b) and forall X, ((X = a or X = b) -> X = Y)). (Uniqueness, 4, 7)
"""
    assert_rejected_at(text, 8)


def test_a_witness_nobody_has_said_anything_about_is_still_not_arbitrary():
    # Line 5 names a witness of `exists Z, a = a`, whose body says nothing
    # about it: no hypothesis mentions X. It is still not arbitrary, because
    # a witness is not a plain declaration. (X was an arbitrary constant
    # inside the closed subproof before it, so this also checks that the
    # name stops being arbitrary when that subproof closes.)
    text = _HEAD + """
5. Exists Z, a = a. (Existential Introduction from 2)
begin subproof
 6.1. let X be arbitrary. (Fresh Variable)
 6.2. X = X. (Reflexivity)
end subproof
7. Let X be such a set. (Existence from 5)
""" + _step(8) + _uniqueness(9, 8)
    assert_rejected_at(text, 9)


def test_the_constant_of_a_fresh_variable_subproof_is_arbitrary():
    text = _HEAD + """
begin subproof
 5.1. let X be arbitrary. (Fresh Variable)
 5.2. If X = a then X = Y. (Conditional Introduction from subproof below)
  5.2.1. X = a. (Assumption for Conditional Introduction)
  5.2.2. a = Y. (Symmetry from 4)
  5.2.3. X = Y. (Transitivity from 5.2.1, 5.2.2)
 5.3. Exists Y, (Y = a and forall X, (X = a -> X = Y)). (Uniqueness, 3, 5.2)
end subproof
"""
    ok, message = run(text)
    assert ok, message


# --------------------------------------------------------------------
# Through the validator: declarations that are not plain
# --------------------------------------------------------------------

def _entries(introduce_x):
    """Hand-built entries: `introduce_x` is line 4, the line that brings X
    in; line 5 is `X = a -> X = a` and line 6 the Uniqueness step."""
    return [
        ("1", None, ("declare", [pl.Declaration("a", pl.DeclarationKind.OBJECT)])),
        ("2", formula("a = a"), ("rule", pl.ReflexivityRule(), [])),
        ("3", formula("exists Y, Y = a"), ("rule", pl.ExistentialIntroductionRule(), ["2"])),
        introduce_x,
        ("5", formula("X = a -> X = a"), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("5.1", formula("X = a"), ("assume",)),
            ("5.2", formula("X = a"), ("rule", pl.ReiterationRule(), ["5.1"])),
        ]),
        ("6", formula("exists W, (W = a and forall V, (V = a -> V = W))"),
         ("rule", pl.UniquenessRule(), ["3", "5"])),
    ]


_OBJECT = pl.DeclarationKind.OBJECT
_PLAIN_X = ("4", None, ("declare", [pl.Declaration("X", _OBJECT)]))


def test_control_a_plainly_declared_object_is_arbitrary():
    assert_valid(_entries(_PLAIN_X), auto_declare=False)


def test_an_object_declared_by_a_rule_is_not_arbitrary():
    # The fourth slot of a rule justification lets a rule declare what it
    # introduces (the direct Pairing witness does). Its line says something
    # about the object, and that line is derived, not assumed, so no
    # hypothesis mentions it -- the declaration must not count as plain.
    by_rule = ("4", formula("a = a"), ("rule", pl.ReflexivityRule(), [], [pl.Declaration("X", _OBJECT)]))
    assert_invalid(_entries(by_rule), pl.CATEGORY_RULE_MISMATCH, label="6", auto_declare=False)


def test_an_object_that_carries_structure_metadata_is_not_assumed_arbitrary():
    # The kernel cannot read metadata, so it cannot know the object is free.
    structured = ("4", None, ("declare", [pl.Declaration("X", _OBJECT, metadata=(("carrier", "a"),))]))
    assert_invalid(_entries(structured), pl.CATEGORY_RULE_MISMATCH, label="6", auto_declare=False)


# --------------------------------------------------------------------
# Through the validator: the context reaches every way of citing a rule
# --------------------------------------------------------------------

class _ContextProbe(pl.InferenceRule):
    """Test-only rule: accepts any line, and records what the context said
    at that moment (a context is only good for the call it is made for: it
    reads the validator's own lists). Asking the probe without a context is
    an error."""
    name = "Probe"

    def __init__(self, arity):
        self.premise_arity = arity
        self.seen = []

    def applies(self, candidates, phi):
        raise AssertionError("the validator must ask a rule through applies_in_context")

    def applies_in_context(self, candidates, phi, context):
        self.seen.append(Seen(context.hypotheses, context.arbitrary_constants))
        return True


class Seen:
    def __init__(self, hypotheses, arbitrary_constants):
        self.hypotheses = hypotheses
        self.arbitrary_constants = arbitrary_constants

    def hypotheses_are(self, *texts):
        return (len(self.hypotheses) == len(texts)
                and all(pl._ast_eq(h, formula(t)) for h, t in zip(self.hypotheses, texts)))


def _check_with(probe, entries):
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + [probe],
        declarations=[pl.Declaration("a", _OBJECT),
                      pl.Declaration("P", pl.DeclarationKind.PREDICATE, arity=1),
                      pl.Declaration("Q", pl.DeclarationKind.PREDICATE, arity=1)],
    )
    ok, err = proof.check_detailed()
    assert ok, str(err)
    return probe.seen


_PROBE_HEAD = [
    ("1", None, ("declare", [pl.Declaration("X", _OBJECT)])),
    ("2", formula("P(a)"), ("premise",)),
]


def test_the_context_reaches_a_rule_cited_by_lines():
    probe = _ContextProbe(0)
    (ctx,) = _check_with(probe, _PROBE_HEAD + [("3", formula("Q(a)"), ("rule", probe, []))])
    assert ctx.hypotheses_are("P(a)")
    assert ctx.arbitrary_constants == frozenset({"X"})


def test_the_context_reaches_a_rule_cited_with_a_subproof_below():
    probe = _ContextProbe(1)
    entries = _PROBE_HEAD + [
        ("3", formula("Q(a)"), ("rule_below", probe), [
            ("3.1", formula("P(a)"), ("assume",)),
            ("3.2", formula("P(a)"), ("rule", pl.ReiterationRule(), ["3.1"])),
        ]),
    ]
    (ctx,) = _check_with(probe, entries)
    assert ctx.hypotheses_are("P(a)")       # the subproof's assumption is closed again
    assert ctx.arbitrary_constants == frozenset({"X"})


def test_the_context_reaches_a_rule_cited_by_lines_and_subproofs():
    probe = _ContextProbe(2)
    entries = _PROBE_HEAD + [
        ("3", formula("Q(a)"), ("rule_hybrid", probe, ["2"]), [[
            ("3.1", formula("P(a)"), ("assume",)),
            ("3.2", formula("P(a)"), ("rule", pl.ReiterationRule(), ["3.1"])),
        ]]),
    ]
    (ctx,) = _check_with(probe, entries)
    assert ctx.hypotheses_are("P(a)")
    assert ctx.arbitrary_constants == frozenset({"X"})


def test_an_open_assumption_is_in_the_context_until_its_subproof_closes():
    probe = _ContextProbe(0)
    entries = _PROBE_HEAD + [
        ("3", formula("Q(a) -> Q(a)"), ("rule_below", pl.ConditionalIntroductionRule()), [
            ("3.1", formula("Q(a)"), ("assume",)),
            ("3.2", formula("Q(a)"), ("rule", probe, [])),
        ]),
        ("4", formula("P(a)"), ("rule", probe, [])),
    ]
    inside, after = _check_with(probe, entries)
    assert inside.hypotheses_are("P(a)", "Q(a)")
    assert after.hypotheses_are("P(a)")


# --------------------------------------------------------------------
# Through the validator: what the proof relies on without a line that says it
# --------------------------------------------------------------------
#
# Found by red-teaming, and not by looking at lines that mention the constant:
# a constant can be constrained by something the proof relies on although no
# premise, axiom or assumption names it. Each proof below, accepted, would
# derive a false "exactly one" statement, so the rule has to refuse it.

def check(text):
    ok, error = pp.check_proof_text(text)
    return ok, str(error)


def assert_rejected_by_uniqueness(text, line):
    ok, message = check(text)
    assert not ok
    assert f"Line {line}:" in message and "'Uniqueness' does not justify" in message, message


# `There is a set Y = {a, b}` names a witness AND states its defining property
# on one line, so the line is the existential-elimination assumption of the
# witness: a statement about Y, a and b that nothing derives. Line 5 uses it to
# get `In(a, Y)`, which refutes `not In(a, Y)`; so `not In(a, Y) -> a = b` is
# provable for this particular `a`. Generalizing it would say that Y has exactly
# one non-member, although line 6 only says it has one. The constant `a` is
# arbitrary as far as the premises go (line 6 does not mention it) -- only the
# witness line ties it down.
_DIRECT_WITNESS_EXPLOIT = """1. Let a, b be any set. (Declaration)
2. There is a set Y = {a, b}. (Axiom of pairing)
3. a = a. (Reflexivity)
4. a = a or a = b. (Disjunction Introduction from 3)
5. In(a, Y). (Set property from 2, 4)
6. Exists W, not In(W, Y). (Premise)
7. If not In(a, Y) then a = b. (Conditional Introduction from subproof below)
 7.1. not In(a, Y). (Assumption for Conditional Introduction)
 7.2. a = b. (Explosion from 5, 7.1)
8. Exists V, (not In(V, Y) and forall Z, (not In(Z, Y) -> Z = V)). (Uniqueness, 6, 7)
"""

# The same argument with the witness named in two steps: `Existence from`
# turns the existential into a premise bundle, which the validator always
# recorded as a hypothesis.
_NAMED_WITNESS_EXPLOIT = """1. Let a, b be any set. (Declaration)
2. Exists Z, forall u, (In(u, Z) iff (u = a or u = b)). (Axiom of pairing)
3. Let Y be such a set. (Existence from 2)
4. a = a. (Reflexivity)
5. a = a or a = b. (Disjunction Introduction from 4)
6. In(a, Y). (Set property from 3, 5)
7. Exists W, not In(W, Y). (Premise)
8. If not In(a, Y) then a = b. (Conditional Introduction from subproof below)
 8.1. not In(a, Y). (Assumption for Conditional Introduction)
 8.2. a = b. (Explosion from 6, 8.1)
9. Exists V, (not In(V, Y) and forall Z, (not In(Z, Y) -> Z = V)). (Uniqueness, 7, 8)
"""

# The same line of the witness proof about a constant it does not mention: the
# unique thing equal to `b` is `b`, generalized over a fresh `X`.
_DIRECT_WITNESS_CONTROL = """1. Let a, b be any set. (Declaration)
2. There is a set Y = {a, b}. (Axiom of pairing)
3. b = b. (Reflexivity)
4. Exists V, V = b. (Existential Introduction from 3)
5. Let X be any set. (Declaration)
6. If X = b then X = b. (Conditional Introduction from subproof below)
 6.1. X = b. (Assumption for Conditional Introduction)
 6.2. X = b. (Reiteration from 6.1)
7. Exists W, (W = b and forall U, (U = b -> U = W)). (Uniqueness, 4, 6)
"""


def test_a_witness_line_that_states_a_property_in_terms_of_the_constant_blocks_it():
    assert_rejected_by_uniqueness(_DIRECT_WITNESS_EXPLOIT, 8)


def test_a_named_witness_bundle_that_states_it_blocks_the_constant_too():
    assert_rejected_by_uniqueness(_NAMED_WITNESS_EXPLOIT, 9)


def test_a_witness_line_about_other_constants_does_not_block_a_fresh_one():
    ok, message = check(_DIRECT_WITNESS_CONTROL)
    assert ok, message


# `Let R be a reflexive relation on X` records the carrier X as metadata that
# the relation rules read (`Relation Reflexivity` only derives `R(a, a)` from
# `In(a, X)` for the declared carrier). So R says something about X that no
# line states. Below, the step `(In(a, X) and not R(a, a)) -> X = a` is
# provable by that hidden fact, for this X; generalizing it would say that
# exactly one set contains a, although line 3 only says one does.
_CARRIER_EXPLOIT = """Use discrete math.
1. Let X be any set, R be a reflexive relation on X. (Declaration)
2. Let a be any set. (Declaration)
3. Exists Y, (In(a, Y) and not R(a, a)). (Premise)
4. If (In(a, X) and not R(a, a)) then X = a. (Conditional Introduction from subproof below)
 4.1. In(a, X) and not R(a, a). (Assumption for Conditional Introduction)
 4.2. In(a, X). (Conjunction Elimination from 4.1)
 4.3. R(a, a). (Relation Reflexivity from 4.2)
 4.4. not R(a, a). (Conjunction Elimination from 4.1)
 4.5. X = a. (Explosion from 4.3, 4.4)
5. Exists W, ((In(a, W) and not R(a, a)) and forall V, ((In(a, V) and not R(a, a)) -> V = W)). (Uniqueness, 3, 4)
"""

# The unobjectionable version of the same shape: nothing hidden constrains X
# (no relation), and the step is a plain instance of B.
_CARRIER_FREE = """Use discrete math.
1. Let X be any set. (Declaration)
2. Let a be any set. (Declaration)
3. a = a. (Reflexivity)
4. Exists Y, Y = a. (Existential Introduction from 3)
5. If X = a then X = a. (Conditional Introduction from subproof below)
 5.1. X = a. (Assumption for Conditional Introduction)
 5.2. X = a. (Reiteration from 5.1)
6. Exists W, (W = a and forall V, (V = a -> V = W)). (Uniqueness, 4, 5)
"""

# The same harmless proof, with a relation declared on X: it is the carrier,
# and the kernel cannot read what that says about it, so it is not arbitrary.
_CARRIER_NAMED_BY_A_RELATION = _CARRIER_FREE.replace(
    "1. Let X be any set. (Declaration)",
    "1. Let X be any set, R be a reflexive relation on X. (Declaration)")

# The relation may also be declared after the carrier, on a later line.
_CARRIER_NAMED_LATER = _CARRIER_FREE.replace(
    "3. a = a. (Reflexivity)",
    "3. a = a. (Reflexivity)").replace(
    "2. Let a be any set. (Declaration)",
    "2. Let a be any set, R be a reflexive relation on X. (Declaration)")


def test_a_carrier_a_relation_is_declared_on_does_not_count_as_arbitrary():
    assert_rejected_by_uniqueness(_CARRIER_EXPLOIT, 5)


def test_control_a_set_no_relation_is_declared_on_is_arbitrary():
    ok, message = check(_CARRIER_FREE)
    assert ok, message


def test_the_carrier_is_refused_even_when_the_proof_does_not_use_the_relation():
    # Fail closed: the rule does not try to work out whether the hidden
    # structure was used.
    assert_rejected_by_uniqueness(_CARRIER_NAMED_BY_A_RELATION, 6)


def test_the_carrier_is_refused_when_the_relation_comes_on_a_later_line():
    assert_rejected_by_uniqueness(_CARRIER_NAMED_LATER, 6)


# --------------------------------------------------------------------
# Saying why: the reason in the refusal
# --------------------------------------------------------------------

def explained(existence=EXISTENCE, step=STEP, conclusion=CONCLUSION, ctx=None):
    rule = pl.UniquenessRule()
    candidates = [formula(existence), formula(step)]
    return rule.explain_in_context(candidates, formula(conclusion), ctx if ctx is not None else context())


def test_there_is_nothing_to_explain_when_the_rule_applies():
    assert explained() is None


@pytest.mark.parametrize("kwargs,condition", [
    (dict(step="if X = a then X = X"), 1),
    (dict(step="if X = a then X = f(a)"), 1),
    (dict(existence="exists Y, In(Y, X)", step="if In(X, X) then X = Y",
          conclusion="exists V, (In(V, X) and forall U, (In(U, X) -> U = V))"), 2),
    (dict(ctx=context(arbitrary=[])), 3),
    (dict(ctx=context(given=["In(X, W)"])), 4),
    (dict(ctx=context(assumptions=["In(X, W)"])), 4),
])
def test_it_names_the_condition_that_failed(kwargs, condition):
    reason = explained(**kwargs)
    assert reason is not None and f"condition {condition}:" in reason, reason


def test_it_names_every_condition_that_failed():
    reason = explained(ctx=context(arbitrary=[], given=["In(X, W)"]))
    assert "condition 3:" in reason and "condition 4:" in reason
    assert "condition 1:" not in reason and "condition 2:" not in reason


def test_it_points_at_the_hypothesis_and_the_constant():
    reason = explained(ctx=context(given=["In(a, W)", "In(X, W)"]))
    assert "X occurs in a hypothesis in force, In(X, W)" in reason


@pytest.mark.parametrize("kwargs", [
    dict(conclusion="exists Y, Y = a"),
    dict(step="if X = b then X = Y"),
    dict(existence="Y = a"),
    dict(step="X = a"),
])
def test_when_the_lines_have_the_wrong_form_it_says_so_and_names_no_condition(kwargs):
    reason = explained(**kwargs)
    assert "unique-existence shape" in reason and "condition" not in reason.replace("conclusion", "")


def test_the_reason_is_found_whichever_way_round_the_lines_are_cited():
    rule = pl.UniquenessRule()
    candidates = [formula(STEP), formula(EXISTENCE)]
    reason = rule.explain_in_context(candidates, formula(CONCLUSION), context(arbitrary=[]))
    assert "condition 3:" in reason


def test_other_rules_have_nothing_to_add():
    rule = pl.ModusPonensRule()
    assert rule.explain_in_context([formula("P(a)"), formula("if P(a) then Q(a)")], formula("R(a)"),
                                   pl.RuleContext()) is None


def test_the_validator_puts_the_reason_after_its_own_message():
    text, uniqueness_line = proof_with("6. In(X, W). (Premise)")
    ok, message = run(text)
    assert not ok
    assert "'Uniqueness' does not justify" in message
    assert message.rstrip().endswith("so the conditional may depend on it"), message
    assert ": condition 4: X occurs in a hypothesis in force, In(X, W)" in message


# What the validator does with a rule's explanation, shown with test-only rules.

class _Refuser(pl.InferenceRule):
    """Test-only rule that refuses everything, with a canned explanation."""
    name = "Refuser"
    premise_arity = 0

    def __init__(self, explanation):
        self.explanation = explanation

    def applies(self, candidates, phi):
        return False

    def explain_in_context(self, candidates, phi, context):
        if isinstance(self.explanation, Exception):
            raise self.explanation
        return self.explanation


def _refusal(rule):
    entries = [("1", None, ("declare", [pl.Declaration("a", _OBJECT)])),
               ("2", formula("a = a"), ("rule", rule, []))]
    ok, err = pl.Proof(entries, rules=pl.default_rules() + [rule]).check_detailed()
    assert not ok
    return err


def test_a_rules_explanation_is_appended_to_the_refusal():
    err = _refusal(_Refuser("because of this"))
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert str(err).endswith("'Refuser' does not justify a = a from the cited line(s) []: because of this")


def test_a_rule_that_explains_nothing_leaves_the_refusal_as_it_was():
    err = _refusal(_Refuser(None))
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert str(err).endswith("from the cited line(s) []")


def test_an_explanation_that_raises_cannot_turn_a_refusal_into_a_crash():
    err = _refusal(_Refuser(RuntimeError("boom")))
    assert err.category == pl.CATEGORY_RULE_MISMATCH
    assert "boom" not in str(err)


# --------------------------------------------------------------------
# Names that declaration metadata refers to
# --------------------------------------------------------------------

_PRED = pl.DeclarationKind.PREDICATE


def _relation_on(carrier, name="R"):
    return pl.Declaration(name, _PRED, arity=2,
                          metadata=(("carrier", carrier), ("properties", ("reflexive", "symmetric"))))


def test_metadata_names_are_the_strings_in_the_values():
    names = pl._metadata_names([_relation_on("X")])
    assert names == {"X", "reflexive", "symmetric"}


def test_metadata_keys_are_not_names():
    assert "carrier" not in pl._metadata_names([_relation_on("X")])


def test_metadata_names_are_found_in_nested_values():
    declaration = pl.Declaration("S", _OBJECT, metadata=(("between", ("X", ("Y", ["Z"]))),))
    assert pl._metadata_names([declaration]) == {"X", "Y", "Z"}


def test_metadata_names_are_found_in_dict_values():
    declaration = pl.Declaration("S", _OBJECT, metadata=(("by", {"k": "W", "j": ("V",)}),))
    assert pl._metadata_names([declaration]) == {"W", "V"}


def test_an_entry_that_is_not_a_pair_is_read_whole():
    declaration = pl.Declaration("S", _OBJECT, metadata=("X", ("Y", "Z", "W")))
    assert pl._metadata_names([declaration]) == {"X", "Y", "Z", "W"}


def test_declarations_without_metadata_name_nothing():
    assert pl._metadata_names([pl.Declaration("X", _OBJECT), pl.Declaration("P", _PRED, arity=1)]) == set()
    assert pl._metadata_names([]) == set()


_PLAIN_X_FOR_CARRIER = ("4", None, ("declare", [pl.Declaration("X", _OBJECT)]))


def test_a_carrier_named_by_a_declaration_the_proof_was_handed_is_not_arbitrary():
    # Same proof as the plain control, but the proof was handed a relation on
    # X: nothing in its lines mentions the relation, yet X is its carrier.
    proof = pl.Proof(_entries(_PLAIN_X_FOR_CARRIER), declarations=[_relation_on("X")])
    ok, err = proof.check_detailed()
    assert not ok and err.category == pl.CATEGORY_RULE_MISMATCH and err.label == "6", str(err)


def test_control_without_that_relation_the_same_proof_is_accepted():
    ok, err = pl.Proof(_entries(_PLAIN_X_FOR_CARRIER)).check_detailed()
    assert ok, str(err)


def test_the_names_one_run_found_are_not_remembered_by_the_next():
    validator = pl.ProofValidator(pl.default_rules(), None, None, declarations=[_relation_on("X")])
    assert not validator.validate(_entries(_PLAIN_X_FOR_CARRIER))[0]
    # The same validator, now handed no relation: X is arbitrary again.
    validator.initial_declarations = []
    ok, err, _ = validator.validate(_entries(_PLAIN_X_FOR_CARRIER))
    assert ok, str(err)
