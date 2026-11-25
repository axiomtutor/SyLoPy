import pytest

from .support import pp, pl


def _declarations(entries):
    found = []
    for _label, _formula, justification in entries:
        if justification and len(justification) > 1 and justification[0] in {"declare", "premise"}:
            found.extend(justification[1])
    return found


def _parse(text):
    entries, _ = pp.parse_proof_text(text)
    return entries


def _check(text):
    entries = _parse(text)
    ok, error = pl.Proof(entries).check_detailed()
    assert ok, error
    return entries


def _declaration(entries, name):
    matches = [item for item in _declarations(entries) if item.name == name]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize(
    ("names", "descriptor"),
    [
        ("P", "a proposition"),
        ("P, Q", "propositions"),
        ("P", "a statement"),
        ("P, Q", "statements"),
        ("P", "a propositional variable"),
        ("P, Q", "propositional variables"),
    ],
)
def test_proposition_declaration_phrases_make_zero_ary_predicates(names, descriptor):
    first = names.split(",")[0].strip()
    entries = _check(
        f"1. Let {names} be {descriptor}. (Declaration)\n"
        f"2. {first} or not {first}. (Premise)\n"
    )
    for name in [part.strip() for part in names.split(",")]:
        declaration = _declaration(entries, name)
        assert declaration.kind == pl.DeclarationKind.PREDICATE
        assert declaration.arity == 0


def test_proposition_declarations_support_proof_by_cases():
    entries = _check("""1. Let P, Q, R be propositions. (Declaration)
2. P or Q. (Premise)
3. If P then R. (Premise)
4. Q -> R. (Premise)
5. R. (Proof by Cases from 2, subproofs below)
begin subproof
 5.1.case1. P. (Case)
 5.2.case1. R. (Modus Ponens from 3, 5.1.case1)
end subproof
begin subproof
 5.1.case2. Q. (Case)
 5.2.case2. R. (Modus Ponens from 4, 5.1.case2)
end subproof
""")
    assert _declaration(entries, "P").arity == 0
    assert _declaration(entries, "Q").arity == 0
    assert _declaration(entries, "R").arity == 0


def _relation_signature(text):
    entries = _parse(text)
    relation = _declaration(entries, "R")
    return (
        relation.kind,
        relation.arity,
        dict(relation.metadata),
        [repr(formula) for formula in entries[0][1]],
    )


def test_strict_order_is_the_existing_strict_partial_order_recipe():
    prefix = "1. Let X be any set, R be a "
    suffix = " on X, a, b be in X. (Declaration)\n2. R(a, b). (Premise)\n"
    strict_order = prefix + "strict order" + suffix
    strict_partial_order = prefix + "strict partial order" + suffix

    strict_entries = _check(strict_order)
    partial_entries = _check(strict_partial_order)
    strict = _declaration(strict_entries, "R")

    assert strict.kind == pl.DeclarationKind.PREDICATE
    assert strict.arity == 2
    assert dict(strict.metadata) == {
        "carrier": "X",
        "properties": ("irreflexive", "transitive"),
    }
    assert _relation_signature(strict_order) == _relation_signature(strict_partial_order)


def _bijection_signature(text):
    entries = _parse(text)
    function = _declaration(entries, "f")
    return (
        function.kind,
        function.arity,
        function.type_name,
        dict(function.metadata),
        [repr(formula) for formula in entries[0][1]],
    )


def test_bijection_from_phrase_is_the_existing_typed_bijection_recipe():
    prefix = "1. Let A, B be any set, f "
    suffix = " a bijection from A to B, a be in A. (Declaration)\n"
    natural_entries = _check(prefix + "be" + suffix + "2. f(a) = f(a). (Reflexivity)\n")
    typed_entries = _check(
        "1. Let A, B be any set, f: A -> B be a bijection, a be in A. (Declaration)\n"
        "2. f(a) = f(a). (Reflexivity)\n"
    )

    function = _declaration(natural_entries, "f")
    assert function.kind == pl.DeclarationKind.FUNCTION
    assert function.arity == 1
    assert dict(function.metadata) == {
        "domain": "A",
        "codomain": "B",
        "bijection": True,
    }
    assert _bijection_signature(prefix + "be" + suffix) == _bijection_signature(
        "1. Let A, B be any set, f: A -> B be a bijection, a be in A. (Declaration)\n"
    )


def test_integer_declaration_remains_an_object():
    entries = _check(
        "1. Let a be an integer. (Declaration)\n"
        "2. a = a. (Reflexivity)\n"
    )
    declaration = _declaration(entries, "a")
    assert declaration.kind == pl.DeclarationKind.OBJECT


def test_proposition_used_as_predicate_is_refused_for_arity_not_declaration():
    entries = _parse("""1. Let P be a proposition. (Declaration)
2. P(a). (Premise)
""")
    ok, error = pl.Proof(entries).check_detailed()

    assert not ok
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_DECLARATION_ARITY_MISMATCH
    assert error.detail == "predicate 'P' expects arity 0, but is used with 1 argument(s)"


def test_relation_used_as_term_is_refused_for_its_declared_kind():
    entries = _parse("""1. Let X be any set, R be a strict order on X. (Declaration)
2. R = R. (Premise)
""")
    ok, error = pl.Proof(entries).check_detailed()

    assert not ok
    assert error is not None
    assert error.label == "2"
    assert error.category == pl.CATEGORY_DECLARATION_KIND_MISMATCH
    assert error.detail == "symbol 'R' is declared as predicate, but is used as an object constant"
