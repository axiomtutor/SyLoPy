"""Adversarial scope/freshness probes for the proof validator.

The test-only Probe rule snapshots the context supplied by the validator. This
checks the validator's live scoping behavior directly, rather than inferring it
only from whether a particular inference rule happens to accept a proof.
"""

from SyLoPy.source import FormulaLogic as fl
from SyLoPy.source import ProofLogic as pl
from SyLoPy.source import TermLogic as tl
from .support import pp


def _atom(name):
    return fl.AtomicFormula(name, [])


def _eq_a():
    a = tl.ConstantTerm("a", "a")
    return fl.Equals(a, a)


def _declaration(name):
    return pl.Declaration(name, pl.DeclarationKind.OBJECT)


class _SeenContext:
    def __init__(self, hypotheses, arbitrary_constants):
        self.hypotheses = tuple(hypotheses)
        self.arbitrary_constants = frozenset(arbitrary_constants)


class _ContextProbe(pl.InferenceRule):
    """Accept a line and record exactly what context it receives."""

    name = "ScopeAuditProbe"
    premise_arity = 0

    def __init__(self):
        self.seen = []

    def applies(self, candidates, phi):
        raise AssertionError("the validator must supply RuleContext")

    def applies_in_context(self, candidates, phi, context):
        self.seen.append(_SeenContext(
            context.hypotheses, context.arbitrary_constants
        ))
        return True


def _check(entries, probe):
    proof = pl.Proof(
        entries,
        rules=pl.default_rules() + [probe],
        declarations=[
            pl.Declaration("P", pl.DeclarationKind.CLOSED_FORMULA),
            pl.Declaration("Q", pl.DeclarationKind.CLOSED_FORMULA),
            pl.Declaration("R", pl.DeclarationKind.CLOSED_FORMULA),
        ],
    )
    ok, error = proof.check_detailed()
    assert ok, str(error)
    return probe.seen


def _assert_hypotheses(context, *names):
    expected = [pp.parse_formula(name, set()) for name in names]
    assert len(context.hypotheses) == len(expected)
    assert all(
        pl._ast_eq(actual, wanted)
        for actual, wanted in zip(context.hypotheses, expected)
    )


def test_plain_declarations_flow_down_ancestor_scopes_and_leave_at_each_boundary():
    """A declaration is visible in descendants, but not after its scope closes."""
    probe = _ContextProbe()
    eq = _eq_a()
    entries = [
        ("1", None, ("declare", [_declaration("a")])),
        ("2", "subproof", [
            ("2.1", _atom("P"), ("assume",)),
            ("2.2", None, ("declare", [_declaration("X")])),
            ("2.3", "subproof", [
                ("2.3.1", _atom("Q"), ("assume",)),
                ("2.3.2", None, ("declare", [_declaration("Y")])),
                ("2.3.3", "subproof", [
                    ("2.3.3.1", _atom("R"), ("assume",)),
                    ("2.3.3.2", eq, ("rule", probe, [])),
                ]),
                ("2.3.4", eq, ("rule", probe, [])),
            ]),
            ("2.4", eq, ("rule", probe, [])),
        ]),
        ("3", eq, ("rule", probe, [])),
    ]

    seen = _check(entries, probe)
    assert [s.arbitrary_constants for s in seen] == [
        frozenset({"a", "X", "Y"}),
        frozenset({"a", "X", "Y"}),
        frozenset({"a", "X"}),
        frozenset({"a"}),
    ]
    _assert_hypotheses(seen[0], "P", "Q", "R")
    _assert_hypotheses(seen[1], "P", "Q")
    _assert_hypotheses(seen[2], "P")
    _assert_hypotheses(seen[3])


def test_fresh_variable_flag_flows_to_descendants_but_not_siblings_or_the_parent():
    probe = _ContextProbe()
    eq = _eq_a()
    entries = [
        ("1", None, ("declare", [_declaration("a")])),
        ("2", "subproof", [
            ("2.1", _atom("X"), ("arbitrary",)),
            ("2.2", "subproof", [
                ("2.2.1", _atom("P"), ("assume",)),
                ("2.2.2", eq, ("rule", probe, [])),
            ]),
            ("2.3", eq, ("rule", probe, [])),
        ]),
        ("3", "subproof", [
            ("3.1", _atom("Q"), ("assume",)),
            ("3.2", eq, ("rule", probe, [])),
        ]),
        ("4", eq, ("rule", probe, [])),
    ]

    seen = _check(entries, probe)
    assert [s.arbitrary_constants for s in seen] == [
        frozenset({"a", "X"}),
        frozenset({"a", "X"}),
        frozenset({"a"}),
        frozenset({"a"}),
    ]
    _assert_hypotheses(seen[0], "P")
    _assert_hypotheses(seen[1])
    _assert_hypotheses(seen[2], "Q")
    _assert_hypotheses(seen[3])


def _replace_justification(entries, label, justification):
    """Replace one parsed line's justification, including in nested entries."""
    for index, entry in enumerate(entries):
        if not isinstance(entry, tuple) or not entry:
            continue

        if (
            entry[0] == label
            and len(entry) >= 3
            and entry[1] != "subproof"
        ):
            entries[index] = (
                entry[0], entry[1], justification, *entry[3:]
            )
            return True

        nested = None
        if len(entry) >= 4 and isinstance(entry[3], list):
            nested = entry[3]
        elif (
            len(entry) >= 3
            and entry[1] == "subproof"
            and isinstance(entry[2], list)
        ):
            nested = entry[2]
        if nested is not None and _replace_justification(
            nested, label, justification
        ):
            return True
    return False


def test_existence_witness_is_never_arbitrary_and_is_scoped_to_its_subproof():
    """An Existence-from-line witness is declared, but not an arbitrary name."""
    text = """
1. Let a be any set. (Declaration)
2. a = a. (Reflexivity)
3. If a = a then a = a. (Conditional Introduction from subproof below)
 3.1. a = a. (Assumption for Conditional Introduction)
 3.2. Exists Z, a = a. (Existential Introduction from 2)
 3.3. Let Y be such a set. (Existence from 3.2)
 3.4. a = a. (Reflexivity)
4. a = a. (Reflexivity)
"""
    entries, _ = pp.parse_proof_text(text)
    probe = _ContextProbe()
    assert _replace_justification(entries, "3.4", ("rule", probe, []))
    assert _replace_justification(entries, "4", ("rule", probe, []))

    proof = pl.Proof(entries, rules=pl.default_rules() + [probe])
    ok, error = proof.check_detailed()
    assert ok, str(error)

    assert len(probe.seen) == 2
    assert all(s.arbitrary_constants == frozenset({"a"}) for s in probe.seen)
    # The assumption is open for the probe inside line 3, but discharged
    # before the top-level probe on line 4.
    _assert_hypotheses(probe.seen[0], "a = a")
    _assert_hypotheses(probe.seen[1])
