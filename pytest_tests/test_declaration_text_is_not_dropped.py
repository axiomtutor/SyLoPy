"""Declaration-line parsing must preserve every name and reject extra sentences.

The regression cases here were previously accepted with text silently absorbed
into a descriptor or discarded. They must fail at the declaration line or
produce exactly the declarations and formulas the author wrote.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from SyLoPy.source.ProofElaboration import TheoryEnvironment

from .support import pp, pl


def _declaration_data(text):
    entries, _ = pp.parse_proof_text(text)
    assert len(entries) == 1
    _label, value, justification = entries[0]
    assert justification[0] in {"declare", "premise"}
    formulas = [] if value is None else (value if isinstance(value, list) else [value])
    return [declaration.name for declaration in justification[1]], [
        repr(formula) for formula in formulas
    ], entries


@pytest.mark.parametrize(
    "surface,names,formulas,valid_twin",
    [
        (
            "1. Let X be any set, a and b be in X. (Declaration)\n",
            ["X", "a", "b"],
            ["In(a, X)", "In(b, X)"],
            "1. Let X be any set, a, b be in X. (Declaration)\n",
        ),
        (
            "1. Let X be any set, a and b be objects. (Declaration)\n",
            ["X", "a", "b"],
            [],
            "1. Let X be any set, a, b be objects. (Declaration)\n",
        ),
        (
            "1. Let X be any set, an and b be in X. (Declaration)\n",
            ["X", "an", "b"],
            ["In(an, X)", "In(b, X)"],
            "1. Let X be any set, an, b be in X. (Declaration)\n",
        ),
    ],
    ids=["and-joined-membership-names", "and-joined-object-names", "article-like-name"],
)
def test_grouped_names_after_a_declaration_clause_are_not_dropped(
    surface, names, formulas, valid_twin
):
    actual_names, actual_formulas, entries = _declaration_data(surface)
    assert actual_names == names
    assert actual_formulas == formulas
    assert pl.Proof(entries).check()[0]

    twin_names, twin_formulas, twin_entries = _declaration_data(valid_twin)
    assert twin_names == names
    assert twin_formulas == formulas
    assert pl.Proof(twin_entries).check()[0]


@pytest.mark.parametrize(
    "surface",
    [
        "1. Let X be any set. Let a be in X. (Declaration)\n",
        "1. Let X be any set, a be in X, and a = a. Let R be a relation on X. (Declaration)\n",
    ],
    ids=["second-let-sentence-is-discarded", "second-let-sentence-is-absorbed-as-a-name"],
)
def test_a_declaration_line_rejects_a_second_let_sentence_at_its_source_line(surface):
    with pytest.raises(
        pp.ElaborationError,
        match="a declaration line is one sentence",
    ) as caught:
        pp.parse_proof_text(surface)

    assert caught.value.span is not None
    assert caught.value.span.start_line == 1


@pytest.mark.parametrize(
    "surface",
    [
        (
            "1. Let X be any set. (Declaration)\n"
            "2. Let a be in X. (Declaration)\n"
        ),
        (
            "1. Let X be any set, a be in X, and a = a. (Declaration)\n"
            "2. Let R be a relation on X. (Declaration)\n"
        ),
    ],
    ids=["separate-membership-declaration", "separate-relation-declaration"],
)
def test_splitting_each_let_statement_onto_its_own_line_is_accepted(surface):
    entries, _ = pp.parse_proof_text(surface)
    assert len(entries) == 2
    assert pl.Proof(entries).check()[0]


class _InvalidNameRecipe:
    name = "test invalid-name recipe"

    def try_match(self, clauses, index):
        if clauses[index].normalized_descriptor != "specially marked object":
            return None
        return (
            1,
            [pl.Declaration("a = a. Let R", pl.DeclarationKind.OBJECT)],
            [],
            [],
        )


def test_declaration_recipe_output_is_subject_to_the_identifier_guard():
    environment = pp.default_theory_environment().extended(
        TheoryEnvironment(declaration_recipes=[_InvalidNameRecipe()])
    )

    with pytest.raises(
        pp.ElaborationError,
        match="invalid declared symbol name",
    ):
        pp.parse_proof_text(
            "1. Let X be a specially marked object. (Declaration)\n",
            environment=environment,
        )



def test_oxford_comma_name_group_remains_one_declaration():
    entries, _ = pp.parse_proof_text(
        "1. Let X, Y and Z be sets. (Declaration)\n"
    )
    assert [declaration.name for declaration in entries[0][2][1]] == ["X", "Y", "Z"]
    assert entries[0][1] is None
    assert pl.Proof(entries).check()[0]


def test_j30_parser_mutations_are_detected(tmp_path):
    """Run the repository mutation checker against each new parser guard."""
    project_root = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "tools" / "mutation_check.py").is_file()
    )
    declaration_start = r"""_DECL_START_RE = re.compile(
    r'^(?:[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*|\s+and\s+))*'
    r'[A-Za-z_][A-Za-z0-9_]*\s+(?:be|are)\b',
    re.I,
)"""
    old_declaration_start = r"""_DECL_START_RE = re.compile(r'^(?:[A-Za-z_][A-Za-z0-9_]*\s*,\s*)*[A-Za-z_][A-Za-z0-9_]*\s+(?:be|are)\b', re.I)"""
    mutations = [
        {
            "id": "and-joined-name-list",
            "file": "source/ProofParser.py",
            "old": declaration_start,
            "new": old_declaration_start,
        },
        {
            "id": "and-joined-comma-lookahead",
            "file": "source/ProofParser.py",
            "old": r"""            if re.match(
                r'^[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*
        {
            "id": "single-sentence-guard",
            "file": "source/ProofParser.py",
            "old": r"if re.search(r'\.\s*let\b', source, re.I):",
            "new": "if False:",
        },
        {
            "id": "recipe-name-guard",
            "file": "source/ProofParser.py",
            "old": "if not isinstance(name, str) or not _IDENTIFIER_RE.fullmatch(name):",
            "new": "if False:",
        },
    ]
    spec = tmp_path / "j30-mutations.json"
    spec.write_text(json.dumps(mutations), encoding="utf-8")
    focused_tests = (
        "python3 -m pytest -q pytest_tests/test_declaration_text_is_not_dropped.py "
        "-k 'grouped_names_after_a_declaration_clause_are_not_dropped or "
        "a_declaration_line_rejects_a_second_let_sentence_at_its_source_line or ""test_oxford_comma_name_group_remains_one_declaration or "
        "declaration_recipe_output_is_subject_to_the_identifier_guard'"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "tools" / "mutation_check.py"),
            str(spec),
            "--tests",
            focused_tests,
            "--jobs",
            "3",
        ],
        cwd=project_root,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
        timeout=150,
    )
    assert completed.returncode == 0, (
        f"mutation checker failed\nstdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert "Summary: total=4 killed=4 survived=0 pattern=0 timeout=0 error=0" in completed.stdout
,
                current,
            ) and _text_after_is_declaration_start(rest):
                buf.append(ch)
                i += 1
                continue""",
            "new": r"""            if re.match(
                r'^[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*
        {
            "id": "single-sentence-guard",
            "file": "source/ProofParser.py",
            "old": r"if re.search(r'\.\s*let\b', source, re.I):",
            "new": "if False:",
        },
        {
            "id": "recipe-name-guard",
            "file": "source/ProofParser.py",
            "old": "if not isinstance(name, str) or not _IDENTIFIER_RE.fullmatch(name):",
            "new": "if False:",
        },
    ]
    spec = tmp_path / "j30-mutations.json"
    spec.write_text(json.dumps(mutations), encoding="utf-8")
    focused_tests = (
        "python3 -m pytest -q pytest_tests/test_declaration_text_is_not_dropped.py "
        "-k 'grouped_names_after_a_declaration_clause_are_not_dropped or "
        "a_declaration_line_rejects_a_second_let_sentence_at_its_source_line or ""test_oxford_comma_name_group_remains_one_declaration or "
        "declaration_recipe_output_is_subject_to_the_identifier_guard'"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "tools" / "mutation_check.py"),
            str(spec),
            "--tests",
            focused_tests,
            "--jobs",
            "3",
        ],
        cwd=project_root,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
        timeout=150,
    )
    assert completed.returncode == 0, (
        f"mutation checker failed\nstdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert "Summary: total=4 killed=4 survived=0 pattern=0 timeout=0 error=0" in completed.stdout
,
                current,
            ) and not _text_after_is_declaration_start(rest):
                buf.append(ch)
                i += 1
                continue""",
        },
        {
            "id": "single-sentence-guard",
            "file": "source/ProofParser.py",
            "old": r"if re.search(r'\.\s*let\b', source, re.I):",
            "new": "if False:",
        },
        {
            "id": "recipe-name-guard",
            "file": "source/ProofParser.py",
            "old": "if not isinstance(name, str) or not _IDENTIFIER_RE.fullmatch(name):",
            "new": "if False:",
        },
    ]
    spec = tmp_path / "j30-mutations.json"
    spec.write_text(json.dumps(mutations), encoding="utf-8")
    focused_tests = (
        "python3 -m pytest -q pytest_tests/test_declaration_text_is_not_dropped.py "
        "-k 'grouped_names_after_a_declaration_clause_are_not_dropped or "
        "a_declaration_line_rejects_a_second_let_sentence_at_its_source_line or ""test_oxford_comma_name_group_remains_one_declaration or "
        "declaration_recipe_output_is_subject_to_the_identifier_guard'"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "tools" / "mutation_check.py"),
            str(spec),
            "--tests",
            focused_tests,
            "--jobs",
            "3",
        ],
        cwd=project_root,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
        timeout=150,
    )
    assert completed.returncode == 0, (
        f"mutation checker failed\nstdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert "Summary: total=4 killed=4 survived=0 pattern=0 timeout=0 error=0" in completed.stdout
