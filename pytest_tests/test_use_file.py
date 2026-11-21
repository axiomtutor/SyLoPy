"""A file that uses another file: `Use NAME.` in a multi-proof file.

The tests write small files to a temporary directory and run the whole
checker over them (`check_files`, `check_file`, `run`), so each claim is about
what the checker does with the files. The rules, from
`source/validate_all_proofs.py`:

* A proof may cite the theorems of a file that the file's `Use` lines name,
  by title, as it cites the theorems its own earlier proofs promoted.
* The checker never checks a file because another file cites it. A run keeps
  the files it checked, and a file may cite only files that the run checked
  before it and that passed.
* `Use` is not transitive, and a title that two cited theorems, or a cited
  theorem and a proof of the citing file, share is refused.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from .support import mp as vap, pp


# ---------------------------------------------------------------------------
# Small files
# ---------------------------------------------------------------------------

PAIR_TRANSPORT = """\
# 1: Pair transport
## Proof that
### then P(a) and Q(a).

1. Let a be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P(a). (Premise)
5. Q(a). (Premise)
6. P(a) and Q(a). (Conjunction Introduction from 4, 5)
"""

# A proof that is invalid on purpose: the last line is not a conjunction.
BROKEN = """\
# 2: Broken
## Proof that
### then P(a).

1. Let a be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. P(a). (Conjunction Introduction from 1)
"""

BOGUS = """\
# 2: Bogus
## Invalid proof.
### then P(a).

1. Let a be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. P(a). (Conjunction Introduction from 1)
"""


def citing(title: str, cited: str = "Pair transport", lines: str = "4, 5",
           thing: str = "b", number: int = 1) -> str:
    """A proof, titled `title`, that cites the theorem `cited` for `thing`."""
    return f"""\
# {number}: {title}
## Proof that
### then P({thing}) and Q({thing}).

1. Let {thing} be any object. (Declaration)
2. Let P be a predicate. (Declaration)
3. Let Q be a predicate. (Declaration)
4. P({thing}). (Premise)
5. Q({thing}). (Premise)
6. P({thing}) and Q({thing}). ({cited} from {lines})
"""


def uses(*names: str) -> str:
    return "".join(f"Use {name}.\n" for name in names) + "\n"


def write(directory: Path, name: str, *parts: str) -> Path:
    path = directory / f"{name}.txt"
    path.write_text("\n".join(parts))
    return path


def verdicts(results):
    """`(file, proof, passed)` for each result."""
    return [(result.file, result.proof_id, result.passed) for result in results]


def record_runs(monkeypatch) -> List[str]:
    """Record the text of every file the checker runs the proofs of."""
    texts: List[str] = []
    real = vap.run_multi_proof_file

    def recorder(text, *args, **kwargs):
        texts.append(text)
        return real(text, *args, **kwargs)

    monkeypatch.setattr(vap, "run_multi_proof_file", recorder)
    return texts


# ---------------------------------------------------------------------------
# What a file gets from the files it uses
# ---------------------------------------------------------------------------

def test_a_file_cites_the_theorems_of_a_file_checked_before_it(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    assert verdicts(vap.check_files([a, b])) == [("A.txt", "1", True), ("B.txt", "1", True)]


def test_the_citation_without_the_use_line_is_refused(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", citing("Use pair transport"))
    results = vap.check_files([a, b])
    assert verdicts(results) == [("A.txt", "1", True), ("B.txt", "1", False)]
    assert "Pair transport" in results[1].message


def test_every_proof_of_the_citing_file_may_cite_the_theorem_from_its_first_line(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("First", number=1), citing("Second", thing="c", number=2))
    assert verdicts(vap.check_files([a, b])) == [("A.txt", "1", True), ("B.txt", "1", True), ("B.txt", "2", True)]


def test_a_cited_theorem_keeps_its_premises(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Premises swapped", lines="5, 4"))
    results = vap.check_files([a, b])
    assert verdicts(results)[-1] == ("B.txt", "1", False)
    assert "'Pair transport' does not justify" in results[-1].message


def test_a_cited_theorem_is_cited_for_another_object_than_the_one_it_was_proved_for(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Another object", thing="c"))
    assert verdicts(vap.check_files([a, b]))[-1] == ("B.txt", "1", True)


def test_the_theorems_a_file_promotes_stay_citable_in_the_file_next_to_the_imported_ones(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport", number=1),
              citing("Again", cited="Use pair transport", thing="c", number=2))
    assert verdicts(vap.check_files([a, b]))[1:] == [("B.txt", "1", True), ("B.txt", "2", True)]


def test_a_file_names_the_same_file_twice_without_a_clash(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A", "A"), citing("Use pair transport"))
    assert verdicts(vap.check_files([a, b]))[-1] == ("B.txt", "1", True)


def test_use_is_not_transitive(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    c = write(tmp_path, "C", uses("B"), citing("Cites the theorem of A", cited="Pair transport"))
    d = write(tmp_path, "D", uses("B"), citing("Cites the theorem of B", cited="Use pair transport"))
    assert verdicts(vap.check_files([a, b, c]))[-1] == ("C.txt", "1", False)
    assert verdicts(vap.check_files([a, b, d]))[-1] == ("D.txt", "1", True)


def test_a_proof_marked_invalid_in_a_cited_file_is_not_a_theorem(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT, BOGUS)
    b = write(tmp_path, "B", uses("A"), citing("Cites the bogus one", cited="Bogus", lines="4"))
    results = vap.check_files([a, b])
    assert verdicts(results) == [("A.txt", "1", True), ("A.txt", "2", True), ("B.txt", "1", False)]
    assert "Bogus" in results[-1].message


def test_check_file_keeps_what_the_file_proved_for_the_files_after_it(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT, BOGUS)
    checked = {}
    vap.check_file(a, checked)
    record = checked[a.resolve()]
    assert record.passed
    assert [theorem.name for theorem in record.theorems] == ["Pair transport"]


def test_run_multi_proof_file_exports_what_it_promotes_and_imports_what_it_is_given():
    exported = []
    vap.run_multi_proof_file(PAIR_TRANSPORT, exported=exported)
    assert [theorem.name for theorem in exported] == ["Pair transport"]
    citing_text = citing("Use pair transport")
    assert [(number, ok) for number, _, ok, _, _ in vap.run_multi_proof_file(citing_text, imported=exported)] == [("1", True)]
    assert [ok for _, _, ok, _, _ in vap.run_multi_proof_file(citing_text)] == [False]


# ---------------------------------------------------------------------------
# A file is never checked because another file cites it
# ---------------------------------------------------------------------------

def test_a_file_is_never_checked_because_another_file_cites_it(tmp_path, monkeypatch):
    write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    texts = record_runs(monkeypatch)
    results = vap.check_files([b])
    assert verdicts(results) == [("B.txt", "?", False)]
    assert results[0].message == (
        "Use A.: A.txt has not been checked in this run. A file is never checked because another cites it, "
        "so check A.txt first")
    assert texts == []


def test_check_file_alone_refuses_a_use_line_that_names_a_file(tmp_path):
    write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    assert verdicts(vap.check_file(b)) == [("B.txt", "?", False)]


def test_a_file_cited_by_several_files_is_checked_once(tmp_path, monkeypatch):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("First"))
    c = write(tmp_path, "C", uses("A"), citing("Second"))
    texts = record_runs(monkeypatch)
    assert all(result.passed for result in vap.check_files([a, b, c]))
    assert [text.count("Pair transport") for text in texts] == [1, 1, 1] and len(texts) == 3
    assert texts[0] == a.read_text()


def test_a_file_that_cites_a_later_file_is_refused(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    results = vap.check_files([b, a])
    assert verdicts(results) == [("B.txt", "?", False), ("A.txt", "1", True)]
    assert "check A.txt first" in results[0].message


def test_a_cited_file_that_did_not_pass_cannot_be_cited(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT, BROKEN)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    results = vap.check_files([a, b])
    assert verdicts(results) == [("A.txt", "1", True), ("A.txt", "2", False), ("B.txt", "?", False)]
    assert results[-1].message == "Use A.: A.txt did not pass, so its theorems cannot be cited; fix A.txt first"


def test_a_file_that_uses_a_file_that_did_not_pass_does_not_pass_either(tmp_path):
    a = write(tmp_path, "A", BROKEN)
    b = write(tmp_path, "B", uses("A"), citing("Never checked"))
    c = write(tmp_path, "C", uses("B"), citing("Never checked either"))
    results = vap.check_files([a, b, c])
    assert verdicts(results) == [("A.txt", "2", False), ("B.txt", "?", False), ("C.txt", "?", False)]
    assert "B.txt did not pass" in results[-1].message


# ---------------------------------------------------------------------------
# What a `Use` line may name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["Missing", "../A", "sub/A", "A.txt", "Chapter1_Axioms"])
def test_a_name_that_is_no_theory_and_no_file_next_to_the_file_is_refused(tmp_path, name):
    write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses(name), citing("Use pair transport"))
    results = vap.check_files([b])
    assert verdicts(results) == [("B.txt", "?", False)]
    assert results[0].message == (
        f"Use {name}.: there is no theory of that name and no file {name}.txt next to this one")


@pytest.mark.parametrize("name", ["../A", "sub/A"])
def test_a_use_line_names_a_file_and_never_a_path(tmp_path, name):
    inner = tmp_path / "inner"
    (inner / "sub").mkdir(parents=True)
    above = write(tmp_path, "A", PAIR_TRANSPORT)
    below = write(inner / "sub", "A", PAIR_TRANSPORT)
    b = write(inner, "B", uses(name), citing("Use pair transport"))
    results = vap.check_files([above, below, b])
    assert verdicts(results) == [("A.txt", "1", True), ("A.txt", "1", True), ("B.txt", "?", False)]
    assert results[-1].message == (
        f"Use {name}.: there is no theory of that name and no file {name}.txt next to this one")


@pytest.mark.parametrize("name", [
    "discrete math", "Discrete Math", "discrete mathematics", "set theory", "SET   THEORY",
    "number theory", "order theory",
])
def test_naming_a_theory_changes_nothing(tmp_path, name):
    a = write(tmp_path, "A", f"Use {name}.\n\n", PAIR_TRANSPORT)
    assert verdicts(vap.check_files([a])) == [("A.txt", "1", True)]


def test_the_theory_names_cover_the_theories_the_checker_loads():
    loaded = set(pp.default_theory_environment().name.split(" + ")) - {"base logic"}
    assert loaded and loaded <= vap.THEORY_NAMES


def test_a_file_named_like_a_theory_is_refused(tmp_path):
    theory = write(tmp_path, "set theory", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("set theory"), citing("Use pair transport"))
    results = vap.check_files([theory, b])
    assert verdicts(results)[-1] == ("B.txt", "?", False)
    assert results[-1].message == (
        "Use set theory.: set theory is the name of a theory of the checker and of the file set theory.txt; "
        "rename the file")


def test_only_a_file_of_several_proofs_can_use_a_file(tmp_path):
    write(tmp_path, "A", PAIR_TRANSPORT)
    bare = write(tmp_path, "bare", "Use A.\n1. Let a be any object. (Declaration)\n")
    results = vap.check_file(bare)
    assert verdicts(results) == [("bare.txt", "1", False)]
    assert "unknown theory directive" in results[0].message


def test_a_use_line_inside_a_comment_is_not_a_use_line(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", "(*\nUse Missing.\n*)\n", uses("A"), citing("Use pair transport"))
    assert verdicts(vap.check_files([a, b]))[-1] == ("B.txt", "1", True)


def test_use_lines_are_read_from_before_the_first_header_only():
    text = "(*\nUse Hidden.\n*)\nUse A.\nuse B\n  USE  C d.  \nsome words\n# 1: T\nUse D.\n"
    assert vap.parse_uses(text) == ["A", "B", "C d"]
    assert vap.parse_uses("# 1\nUse A.\n") == []
    assert vap.parse_uses("") == []


# ---------------------------------------------------------------------------
# Titles that would make a citation ambiguous
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("title", [
    "Pair transport", "pair transport", "Pair-transport", "PAIR   TRANSPORT",
])
def test_two_cited_theorems_with_the_same_title_are_refused(tmp_path, title):
    a1 = write(tmp_path, "A1", PAIR_TRANSPORT)
    a2 = write(tmp_path, "A2", PAIR_TRANSPORT.replace("Pair transport", title))
    b = write(tmp_path, "B", uses("A1", "A2"), citing("Use it"))
    results = vap.check_files([a1, a2, b])
    assert verdicts(results)[-1] == ("B.txt", "?", False)
    assert results[-1].message == (
        f"Use A2.: the title {title!r} is also the title of a theorem of A1.txt, so citing it would be ambiguous")


def test_a_proof_without_a_title_does_not_disturb_the_files_titles(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    untitled = citing("unused").replace("# 1: unused", "# 1")
    b = write(tmp_path, "B", uses("A"), untitled, citing("Titled", thing="c", number=2))
    assert verdicts(vap.check_files([a, b]))[1:] == [("B.txt", "1", True), ("B.txt", "2", True)]


def test_a_header_inside_a_comment_is_not_a_title_of_the_file(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), "(*\n# 7: Pair transport\n*)\n", citing("Use pair transport"))
    assert verdicts(vap.check_files([a, b]))[-1] == ("B.txt", "1", True)


@pytest.mark.parametrize("own_title", ["Pair transport", "pair-transport"])
def test_a_proof_titled_like_a_cited_theorem_is_refused(tmp_path, own_title):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing(own_title, cited="Pair transport"))
    results = vap.check_files([a, b])
    assert verdicts(results)[-1] == ("B.txt", "?", False)
    assert results[-1].message == (
        "Use A.: this file has a proof titled like the theorem 'Pair transport' of A.txt, "
        "so citing it would be ambiguous")


def test_the_same_title_in_files_that_are_not_both_used_is_no_clash(tmp_path):
    a1 = write(tmp_path, "A1", PAIR_TRANSPORT)
    a2 = write(tmp_path, "A2", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A1"), citing("Use pair transport"))
    assert verdicts(vap.check_files([a1, a2, b]))[-1] == ("B.txt", "1", True)


# ---------------------------------------------------------------------------
# Runs over a directory
# ---------------------------------------------------------------------------

def test_a_run_checks_the_cited_files_first(tmp_path):
    write(tmp_path, "a_user", uses("z_base"), citing("Use pair transport"))
    write(tmp_path, "z_base", PAIR_TRANSPORT)
    assert verdicts(vap.run([str(tmp_path)])) == [("z_base.txt", "1", True), ("a_user.txt", "1", True)]


def test_a_run_orders_a_chain_whatever_the_names(tmp_path):
    write(tmp_path, "a_top", uses("m_middle"), citing("Top", cited="Middle", thing="d"))
    write(tmp_path, "m_middle", uses("z_base"), citing("Middle", thing="c"))
    write(tmp_path, "z_base", PAIR_TRANSPORT)
    results = vap.run([str(tmp_path)])
    assert [result.file for result in results] == ["z_base.txt", "m_middle.txt", "a_top.txt"]
    assert all(result.passed for result in results)


def test_files_that_use_nothing_stay_in_alphabetical_order(tmp_path):
    for name in ("c", "a", "b"):
        write(tmp_path, name, PAIR_TRANSPORT)
    assert [result.file for result in vap.run([str(tmp_path)])] == ["a.txt", "b.txt", "c.txt"]


def test_a_use_line_names_a_file_next_to_the_file_and_not_one_elsewhere(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    write(other, "A", PAIR_TRANSPORT)
    here = tmp_path / "here"
    here.mkdir()
    write(here, "B", uses("A"), citing("Use pair transport"))
    results = vap.run([str(other), str(here)])
    assert verdicts(results) == [("A.txt", "1", True), ("B.txt", "?", False)]
    assert results[-1].message == "Use A.: there is no theory of that name and no file A.txt next to this one"


def test_a_run_checks_a_file_that_several_files_use_once(tmp_path, monkeypatch):
    write(tmp_path, "A", PAIR_TRANSPORT)
    write(tmp_path, "B", uses("A"), citing("First"))
    write(tmp_path, "C", uses("A"), citing("Second"))
    texts = record_runs(monkeypatch)
    results = vap.run([str(tmp_path)])
    assert [result.file for result in results] == ["A.txt", "B.txt", "C.txt"]
    assert all(result.passed for result in results)
    assert len(texts) == 3


def test_a_bare_proof_file_does_not_reorder_a_run(tmp_path):
    write(tmp_path, "a_bare", "Use z_base.\n1. Let a be any object. (Declaration)\n")
    write(tmp_path, "z_base", PAIR_TRANSPORT)
    assert [result.file for result in vap.run([str(tmp_path)])] == ["a_bare.txt", "z_base.txt"]


def test_a_cycle_of_use_lines_is_reported_and_nothing_in_it_is_checked(tmp_path, monkeypatch):
    write(tmp_path, "A", uses("B"), PAIR_TRANSPORT)
    write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    texts = record_runs(monkeypatch)
    results = vap.run([str(tmp_path)])
    assert verdicts(results) == [("A.txt", "?", False), ("B.txt", "?", False)]
    assert [result.message for result in results] == ["Use cycle: A.txt -> B.txt -> A.txt"] * 2
    assert texts == []


def test_a_file_that_uses_a_file_in_a_cycle_does_not_pass(tmp_path):
    write(tmp_path, "A", uses("B"), PAIR_TRANSPORT)
    write(tmp_path, "B", uses("A"), PAIR_TRANSPORT)
    write(tmp_path, "C", uses("A"), citing("Use pair transport"))
    results = vap.run([str(tmp_path)])
    assert verdicts(results) == [("A.txt", "?", False), ("B.txt", "?", False), ("C.txt", "?", False)]
    assert results[-1].message == "Use A.: A.txt did not pass, so its theorems cannot be cited; fix A.txt first"


def test_a_file_cannot_use_itself(tmp_path):
    a = write(tmp_path, "A", uses("A"), PAIR_TRANSPORT)
    expected = [("A.txt", "?", False)]
    for results in (vap.check_files([a]), vap.run([str(tmp_path)])):
        assert verdicts(results) == expected
        assert results[0].message == "Use A.: a file cannot use itself"


# ---------------------------------------------------------------------------
# The fixtures of the suite
# ---------------------------------------------------------------------------

def test_the_set_theory_fixtures_that_use_a_file_behave_as_expected():
    results = [result for result in vap.run(["tests/testSetTheory"]) if result.file.startswith("use_file_")]
    assert [(result.file, result.proof_id, result.expected_valid, result.ok) for result in results] == [
        ("use_file_base.txt", "1", True, True),
        ("use_file_cites.txt", "1", True, True),
        ("use_file_cites.txt", "2", False, False),
    ]
    assert all(result.passed for result in results)
    assert "does not justify" in results[-1].message
