"""Saved results: a file that was checked is not checked again while nothing it
depends on has changed.

The tests write small files to a temporary directory and run the whole checker
over them with saved results (`check_files`, `run`, `main`), and over the
fixtures of the suites, so each claim is about what the checker does. The
rules, from `source/SavedChecks.py` and `source/validate_all_proofs.py`:

* A file that passed is saved under a key made of its text, the keys of the
  files it uses, and the checker. A later run that finds the same key takes
  the saved results, and the saved theorems for the files that cite it, and
  does not check the file.
* A change to the file, to a file it uses (however far down), or to the
  checker means another key, so the file is checked.
* Nothing is saved for a file that did not pass, nothing is saved or read
  unless asked, and a saved result that cannot be read in full is no result.
* A file is still never checked because another cites it: a cited file counts
  as checked when its saved result is for its present text.
"""
from __future__ import annotations

import collections
import copy
import hashlib
import io
import json
import os
import pickle
import re
import shlex
import subprocess
import sys
import types

import pytest

import SyLoPy.source.SavedChecks as sc

from .file_fixtures import BROKEN, PAIR_TRANSPORT, citing, record_checks, uses, verdicts, write
from .support import mp as vap

# A file of one proof, valid; and the same text under a name that says it is not.
BARE_VALID = "1. Let a be any object. (Declaration)\n2. Let P be a predicate. (Declaration)\n"

# Every directory of fixtures the runner checks.
CORPUS = vap.ENFORCED_DIRS + vap.INFORMATIONAL_DIRS


def saved_in(tmp_path):
    return vap.open_saved_results(tmp_path / "saved")


def later_run(saved):
    """Saved results as a later run opens them: the same directory, nothing remembered."""
    return vap.open_saved_results(saved.directory)


def record_of(saved, path):
    return saved.path(vap.saved_key(path, path.read_text(), saved))


def pair_and_citer(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    return a, b


# ---------------------------------------------------------------------------
# What a saved result does
# ---------------------------------------------------------------------------

def test_a_file_that_passed_is_not_checked_again_by_a_later_run(tmp_path, monkeypatch):
    a, b = pair_and_citer(tmp_path)
    first = saved_in(tmp_path)
    results = vap.check_files([a, b], first)
    assert all(result.passed for result in results)
    assert (first.stored, first.replayed) == (["A.txt", "B.txt"], [])
    names = record_checks(monkeypatch)
    later = later_run(first)
    assert vap.check_files([a, b], later) == results
    assert names == []
    assert (later.stored, later.replayed) == ([], ["A.txt", "B.txt"])


def test_a_file_saved_by_an_earlier_run_counts_as_checked_for_a_file_that_cites_it(tmp_path, monkeypatch):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    first = saved_in(tmp_path)
    vap.check_files([a], first)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    names = record_checks(monkeypatch)
    later = later_run(first)
    assert verdicts(vap.check_files([b], later)) == [("B.txt", "1", True)]
    assert names == ["B.txt"]
    assert later.replayed == [] and later.stored == ["B.txt"]


def test_in_a_run_a_file_taken_from_saved_results_is_there_for_the_files_that_cite_it(tmp_path, monkeypatch):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    first = saved_in(tmp_path)
    vap.run([str(tmp_path)], first)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    names = record_checks(monkeypatch)
    later = later_run(first)
    assert verdicts(vap.run([str(tmp_path)], later)) == [("A.txt", "1", True), ("B.txt", "1", True)]
    assert names == ["B.txt"] and later.replayed == ["A.txt"]


def test_theorems_that_need_the_rules_of_the_checker_are_saved_and_cited(tmp_path, monkeypatch):
    fixture = vap.ROOT / "tests" / "testSetTheory" / "set_operation_definitions.txt"
    write(tmp_path, "set_ops", fixture.read_text())
    first = saved_in(tmp_path)
    vap.check_files([tmp_path / "set_ops.txt"], first)
    assert first.stored == ["set_ops.txt"]
    b = write(tmp_path, "B", uses("set_ops"), "\n".join([
        "# 1: The first set is inside the union",
        "## Proof that",
        "### If C and D are sets then C is a subset of C union D.",
        "1. Let C, D be any set. (Declaration)",
        "2. C is a subset of C union D. (A union contains its first set)",
    ]))
    names = record_checks(monkeypatch)
    assert verdicts(vap.check_files([b], later_run(first))) == [("B.txt", "1", True)]
    assert names == ["B.txt"]


def test_a_saved_theorem_refers_to_the_rules_of_the_checker_and_does_not_copy_them(tmp_path):
    fixture = vap.ROOT / "tests" / "testSetTheory" / "set_operation_definitions.txt"
    exported = []
    vap.run_multi_proof_file(
        fixture.read_text(), vap.BARE_PROOF_AXIOMS, vap.BARE_PROOF_RULES, vap.BARE_PROOF_DECLARATIONS,
        exported=exported, warn_on_unpromoted=False, warn_unparseable_description=False,
    )
    original = next(theorem for theorem in exported if theorem.name == "A union contains its first set")
    saved = saved_in(tmp_path)
    assert saved.save("k", [], [original])
    (restored,) = saved.load("k").theorems
    live = {id(rule) for rule in vap.BARE_PROOF_RULES}
    from_the_checker = [rule for rule in original.required_rules if id(rule) in live]
    assert from_the_checker
    assert len([rule for rule in restored.required_rules if id(rule) in live]) == len(from_the_checker)


def test_nothing_is_saved_or_read_unless_asked(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("saved results were used without being asked for")

    monkeypatch.setattr(sc.SavedChecks, "save", refuse)
    monkeypatch.setattr(sc.SavedChecks, "load", refuse)
    a, b = pair_and_citer(tmp_path)
    assert all(result.passed for result in vap.check_files([a, b]))
    assert all(result.passed for result in vap.run(["tests/testSetTheory"]))


def test_the_command_line_flag_names_the_directory_and_the_default_is_ignored_by_git():
    assert vap._parse_args([]).saved_results is None
    assert vap._parse_args(["--saved-results"]).saved_results == str(vap.DEFAULT_SAVED_RESULTS)
    assert vap._parse_args(["--saved-results", "somewhere"]).saved_results == "somewhere"
    assert vap.DEFAULT_SAVED_RESULTS == vap.ROOT / ".saved_results"
    assert ".saved_results/" in (vap.ROOT / ".gitignore").read_text().splitlines()


_SAVED_LINE = re.compile(
    r"^saved results in (.*): (\d+) files not checked again, (\d+) checked and saved(?:, (\d+) passed but could not be saved)?$",
    re.MULTILINE,
)


def saved_line(output):
    """What the saved-results line of a run says: the directory, and how many
    files were not checked again, were saved, and could not be saved."""
    (directory, replayed, stored, not_stored), = _SAVED_LINE.findall(output)
    return directory, int(replayed), int(stored), int(not_stored or 0)


def without_the_saved_line(output):
    return [line for line in output.splitlines() if not line.startswith("saved results in ")]


@pytest.mark.parametrize("selection, directories", [
    (["--suite", "testSetTheory"], ["tests/testSetTheory"]),
    ([], CORPUS),
], ids=["one suite", "every suite"])
def test_the_command_line_reports_what_it_did_not_check_again(tmp_path, capsys, selection, directories):
    # What the files of these directories give when they are checked with saved
    # results through the Python API: the command line must save and replay the same.
    through_the_api = vap.open_saved_results(tmp_path / "api")
    vap.run(directories, through_the_api)
    assert through_the_api.stored
    arguments = [*selection, "--saved-results", str(tmp_path / "saved")]
    assert vap.main(arguments) == 0
    first = capsys.readouterr().out
    assert vap.main(arguments) == 0
    second = capsys.readouterr().out
    directory, replayed, stored, not_stored = saved_line(first)
    assert (directory, not_stored) == (str(tmp_path / "saved"), 0)
    assert (replayed, stored) == (len(through_the_api.replayed), len(through_the_api.stored))
    assert saved_line(second) == (directory, replayed + stored, 0, 0)
    assert without_the_saved_line(first) == without_the_saved_line(second)


def test_the_command_line_says_when_a_result_could_not_be_saved(tmp_path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the directory should be")
    assert vap.main(["--suite", "testSetTheory", "--saved-results", str(blocker / "saved")]) == 0
    _, replayed, stored, not_stored = saved_line(capsys.readouterr().out)
    assert (replayed, stored) == (0, 0) and not_stored > 0


def test_the_command_line_says_nothing_of_saved_results_unless_asked(capsys):
    assert vap.main(["--suite", "testSetTheory"]) == 0
    assert "saved results" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# A later process, with another hash seed
# ---------------------------------------------------------------------------

_SCRIPT = """
import json, sys
from pathlib import Path
import SyLoPy.source.validate_all_proofs as vap
saved = vap.open_saved_results(sys.argv[1])
results = vap.check_files([Path(name) for name in sys.argv[2:]], saved)
print(json.dumps({"results": [[r.file, r.proof_id, r.passed] for r in results],
                  "replayed": saved.replayed, "stored": saved.stored}))
"""


def in_another_process(seed, directory, *files):
    environment = dict(os.environ, PYTHONHASHSEED=str(seed),
                       PYTHONPATH=os.pathsep.join([str(vap.ROOT.parent), os.environ.get("PYTHONPATH", "")]))
    done = subprocess.run([sys.executable, "-c", _SCRIPT, str(directory), *map(str, files)],
                          env=environment, capture_output=True, text=True, check=True)
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_a_file_checked_by_one_process_is_not_checked_by_another_and_its_theorems_are_cited(tmp_path):
    a, b = pair_and_citer(tmp_path)
    store = tmp_path / "saved"
    first = in_another_process(1, store, a)
    assert first == {"results": [["A.txt", "1", True]], "replayed": [], "stored": ["A.txt"]}
    second = in_another_process(2, store, a, b)
    assert second == {"results": [["A.txt", "1", True], ["B.txt", "1", True]],
                      "replayed": ["A.txt"], "stored": ["B.txt"]}
    third = in_another_process(3, store, b)
    assert third == {"results": [["B.txt", "1", True]], "replayed": ["B.txt"], "stored": []}


def test_the_theorems_of_a_saved_file_are_cited_by_another_process(tmp_path):
    fixture = vap.ROOT / "tests" / "testSetTheory" / "set_operation_definitions.txt"
    set_ops = write(tmp_path, "set_ops", fixture.read_text())
    b = write(tmp_path, "B", uses("set_ops"), "\n".join([
        "# 1: The first set is inside the union",
        "## Proof that",
        "### If C and D are sets then C is a subset of C union D.",
        "1. Let C, D be any set. (Declaration)",
        "2. C is a subset of C union D. (A union contains its first set)",
    ]))
    store = tmp_path / "saved"
    assert in_another_process(11, store, set_ops)["stored"] == ["set_ops.txt"]
    cited = in_another_process(12, store, b)
    assert cited == {"results": [["B.txt", "1", True]], "replayed": [], "stored": ["B.txt"]}


# ---------------------------------------------------------------------------
# Everything of the fixtures
# ---------------------------------------------------------------------------

def test_a_later_run_gives_the_results_of_the_first_and_checks_no_file(tmp_path, monkeypatch):
    fresh = vap.run(CORPUS)
    saving = saved_in(tmp_path)
    assert vap.run(CORPUS, saving) == fresh
    assert saving.stored and not saving.replayed and not saving.not_stored
    names = record_checks(monkeypatch)
    later = later_run(saving)
    assert vap.run(CORPUS, later) == fresh
    assert names == []
    assert later.replayed == saving.stored and not later.stored


def proof_blocks(text):
    """The text of each proof of a multi-proof file, header included, in order."""
    lines = vap._COMMENT_RE.sub(" ", text).splitlines()
    starts = [index for index, line in enumerate(lines) if vap._PROOF_HEADER_RE.match(line.strip())]
    return ["\n".join(lines[start:end]) for start, end in zip(starts, starts[1:] + [len(lines)])]


def canon(value, live, path=()):
    """What `value` is made of, with the rules the checker starts from named
    by their place in its list: two values with the same canon are the same
    data, and refer to the same live rules."""
    if id(value) in live:
        return ("rule of the checker", live[id(value)])
    if id(value) in path:
        return ("cycle",)
    path = path + (id(value),)
    if isinstance(value, (list, tuple)):
        return [canon(item, live, path) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((canon(item, live, path) for item in value), key=repr)
    if isinstance(value, dict):
        return sorted(((canon(key, live, path), canon(item, live, path)) for key, item in value.items()), key=repr)
    if type(value).__repr__ is object.__repr__ and hasattr(value, "__dict__"):
        return (type(value).__qualname__, canon(vars(value), live, path))
    return repr(value)


def test_theorems_restored_from_saved_results_are_the_originals_in_every_file(tmp_path):
    saved = saved_in(tmp_path)
    live = {id(rule): index for index, rule in enumerate(vap.BARE_PROOF_RULES)}
    quiet = dict(warn_on_unpromoted=False, warn_unparseable_description=False, warn_duplicate_number=False)
    theorems = needing_a_rule = 0
    for directory in CORPUS:
        for path in sorted((vap.ROOT / directory).glob("*.txt")):
            text = path.read_text()
            if not vap._looks_like_multi_proof(text) or vap.parse_uses(text):
                continue
            exported: list = []
            vap.run_multi_proof_file(
                text, vap.BARE_PROOF_AXIOMS, vap.BARE_PROOF_RULES, vap.BARE_PROOF_DECLARATIONS,
                exported=exported, **quiet)
            key = saved.key({"file": str(path)})
            assert saved.save(key, [], exported), path
            restored = saved.load(key).theorems
            assert len(restored) == len(exported)
            for original, copy_ in zip(exported, restored):
                assert type(copy_) is type(original) and copy_ is not original
                assert canon(vars(copy_), live) == canon(vars(original), live), (path.name, original.name)
                theorems += 1
                needing_a_rule += any(id(rule) in live for rule in original.required_rules)
    assert theorems > 150 and needing_a_rule > 20


def test_theorems_restored_from_saved_results_behave_as_the_originals_in_every_proof(tmp_path):
    saved = saved_in(tmp_path)
    quiet = dict(warn_on_unpromoted=False, warn_unparseable_description=False, warn_duplicate_number=False)

    def alone(block, theorems):
        return vap.run_multi_proof_file(
            block, vap.BARE_PROOF_AXIOMS, vap.BARE_PROOF_RULES, vap.BARE_PROOF_DECLARATIONS,
            imported=list(theorems), **quiet)

    compared = cited = 0
    for directory in vap.ENFORCED_DIRS:
        for path in sorted((vap.ROOT / directory).glob("*.txt")):
            text = path.read_text()
            if not vap._looks_like_multi_proof(text) or vap.parse_uses(text):
                continue
            titles = vap.proof_titles(text)
            if len(titles) != len(set(titles)):
                continue
            exported: list = []
            expected = vap.run_multi_proof_file(
                text, vap.BARE_PROOF_AXIOMS, vap.BARE_PROOF_RULES, vap.BARE_PROOF_DECLARATIONS,
                exported=exported, **quiet)
            key = saved.key({"file": str(path)})
            assert saved.save(key, [], exported), path
            restored = list(saved.load(key).theorems)
            assert [theorem.name for theorem in restored] == [theorem.name for theorem in exported]
            blocks = proof_blocks(text)
            cases = vap.parse_multi_proof_file(text, warn_unparseable_description=False)
            assert len(blocks) == len(cases) == len(expected)
            # Each proof alone, once with the theorems that the proofs before it
            # promoted and once with the restored copies of them, comes out the same.
            originals_before: list = []
            restored_before: list = []
            for block, case, result in zip(blocks, cases, expected):
                with_originals = alone(block, originals_before)
                assert alone(block, restored_before) == with_originals, (path.name, case.number)
                compared += 1
                cited += any(theorem.name in block for theorem in originals_before)
                promoted = len(originals_before)
                if result[2] and promoted < len(exported) and exported[promoted].name == case.title:
                    originals_before.append(exported[promoted])
                    restored_before.append(restored[promoted])
    assert compared > 100 and cited > 5


def test_the_fixtures_that_use_a_file_give_the_same_results_when_that_file_comes_from_saved_results(tmp_path, monkeypatch):
    fresh = vap.run(CORPUS)
    saving = saved_in(tmp_path)
    assert vap.run(CORPUS, saving) == fresh
    users = [path for directory in CORPUS for path in sorted((vap.ROOT / directory).glob("*.txt"))
             if vap.parse_uses(path.read_text())]
    assert users
    for path in users:
        record_of(saving, path).unlink()
    names = record_checks(monkeypatch)
    later = later_run(saving)
    assert vap.run(CORPUS, later) == fresh
    assert sorted(names) == sorted(path.name for path in users)
    assert not {path.name for path in users} & set(later.replayed)


# ---------------------------------------------------------------------------
# What makes a saved result no longer the result
# ---------------------------------------------------------------------------

def test_a_change_to_a_file_means_it_is_checked_again_and_so_is_every_file_that_uses_it(tmp_path, monkeypatch):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    c = write(tmp_path, "C", uses("B"), citing("Cites the theorem of B", cited="Use pair transport", thing="c"))
    write(tmp_path, "D", PAIR_TRANSPORT, "(* a file that uses no other file *)")
    first = saved_in(tmp_path)
    assert all(result.passed for result in vap.run([str(tmp_path)], first))
    assert sorted(first.stored) == ["A.txt", "B.txt", "C.txt", "D.txt"] and first.replayed == []
    everything = {"A.txt", "B.txt", "C.txt", "D.txt"}
    # A is below B and C; B is below C; D is below none, and none is below D.
    for changed, rechecked in ((a, {"A.txt", "B.txt", "C.txt"}), (b, {"B.txt", "C.txt"}), (c, {"C.txt"})):
        changed.write_text(changed.read_text() + "\n(* a comment *)\n")
        names = record_checks(monkeypatch)
        later = later_run(first)
        assert all(result.passed for result in vap.run([str(tmp_path)], later))
        assert set(names) == rechecked and len(names) == len(rechecked)
        assert set(later.replayed) == everything - rechecked
        assert set(later.stored) == rechecked
        monkeypatch.undo()


def test_the_saved_result_of_a_file_is_read_once_for_all_the_files_that_cite_it(tmp_path, monkeypatch):
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    b1 = write(tmp_path, "B1", uses("A"), citing("Use pair transport"))
    b2 = write(tmp_path, "B2", uses("A"), citing("Use pair transport", thing="c"))
    first = saved_in(tmp_path)
    vap.check_files([a, b1, b2], first)
    key_of_a = record_of(first, a).stem
    for changed in (b1, b2):
        changed.write_text(changed.read_text() + "\n(* changed *)\n")
    loaded = []
    real = sc.SavedChecks.load

    def counting(self, key):
        loaded.append(key)
        return real(self, key)

    monkeypatch.setattr(sc.SavedChecks, "load", counting)
    assert all(result.passed for result in vap.check_files([b1, b2], later_run(first)))
    assert loaded.count(key_of_a) == 1


def test_a_change_of_whitespace_alone_is_a_change(tmp_path, monkeypatch):
    a, b = pair_and_citer(tmp_path)
    first = saved_in(tmp_path)
    vap.check_files([a, b], first)
    a.write_text(a.read_text() + "\n")
    names = record_checks(monkeypatch)
    vap.check_files([a, b], later_run(first))
    assert names == ["A.txt", "B.txt"]


def test_a_change_to_the_checker_means_every_file_is_checked_again(tmp_path, monkeypatch):
    a, b = pair_and_citer(tmp_path)
    first = saved_in(tmp_path)
    vap.check_files([a, b], first)
    names = record_checks(monkeypatch)
    other = sc.SavedChecks(first.directory, vap.BARE_PROOF_RULES, code_digest="another checker")
    vap.check_files([a, b], other)
    assert names == ["A.txt", "B.txt"] and other.stored == ["A.txt", "B.txt"]
    again = later_run(first)
    vap.check_files([a, b], again)
    assert names == ["A.txt", "B.txt"] and again.replayed == ["A.txt", "B.txt"]


def test_a_change_to_the_rules_the_checker_starts_from_means_every_file_is_checked_again(tmp_path, monkeypatch):
    a, b = pair_and_citer(tmp_path)
    first = saved_in(tmp_path)
    vap.check_files([a, b], first)
    names = record_checks(monkeypatch)
    reordered = sc.SavedChecks(first.directory, list(reversed(vap.BARE_PROOF_RULES)))
    vap.check_files([a, b], reordered)
    assert names == ["A.txt", "B.txt"]


def test_the_key_depends_on_everything_a_check_depends_on(tmp_path, monkeypatch):
    rules = list(vap.BARE_PROOF_RULES)
    base = sc.SavedChecks(tmp_path, rules, code_digest="code")
    file = {"text": "t", "uses": []}
    key = base.key(file)
    assert sc.SavedChecks(tmp_path, rules, code_digest="code").key({"uses": [], "text": "t"}) == key
    assert sc.SavedChecks(tmp_path, rules, code_digest="other").key(file) != key
    assert sc.SavedChecks(tmp_path, rules[::-1], code_digest="code").key(file) != key
    assert sc.SavedChecks(tmp_path, rules[:-1], code_digest="code").key(file) != key
    assert base.key({"text": "u", "uses": []}) != key
    assert base.key({"text": "t", "uses": [["A", "k"]]}) != key
    with monkeypatch.context() as patched:
        patched.setattr(sc, "sys", types.SimpleNamespace(version_info=(3, 99, 0, "final", 0)))
        assert base.key(file) != key
    with monkeypatch.context() as patched:
        patched.setattr(sc, "FORMAT", sc.FORMAT + 1)
        assert base.key(file) != key
    keys = set()
    for micro in (0, 7):  # the same Python, in another patch release
        with monkeypatch.context() as patched:
            patched.setattr(sc, "sys", types.SimpleNamespace(version_info=(3, 12, micro, "final", 0)))
            keys.add(base.key(file))
    assert len(keys) == 1


def test_the_digest_of_the_rules_follows_their_order_classes_and_names():
    def rule(name, module="m", kind="Rule"):
        return type(kind, (), {"__module__": module, "name": name})()

    base = [rule("a"), rule("b")]
    digest = sc.rules_digest(base)
    assert sc.rules_digest([rule("a"), rule("b")]) == digest
    assert sc.rules_digest(reversed(base)) != digest
    assert sc.rules_digest(base[:1]) != digest
    assert sc.rules_digest(base + [rule("c")]) != digest
    assert sc.rules_digest([rule("a"), rule("c")]) != digest
    assert sc.rules_digest([rule("a"), rule("b", kind="Other")]) != digest
    assert sc.rules_digest([rule("a"), rule("b", module="other")]) != digest
    assert sc.rules_digest([]) != digest


def test_the_source_digest_follows_every_python_file_of_the_package(tmp_path):
    package = tmp_path / "pkg"
    source = package / "source"
    (source / "sub").mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (source / "a.py").write_text("x = 1\n")
    (source / "sub" / "b.py").write_text("y = 2\n")
    base = sc.source_digest(source)
    assert sc.source_digest(source) == base
    (source / "notes.txt").write_text("not code")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"compiled")
    (source / "__pycache__" / "c.py").write_text("ignored")
    assert sc.source_digest(source) == base
    (source / "sub" / "b.py").write_text("y = 3\n")
    changed = sc.source_digest(source)
    assert changed != base
    (source / "sub" / "b.py").write_text("y = 2\n")
    assert sc.source_digest(source) == base
    (package / "__init__.py").write_text("# changed")
    assert sc.source_digest(source) != base
    (package / "__init__.py").write_text("")
    (source / "a.py").rename(source / "aa.py")  # the same place in the order, another name
    assert sc.source_digest(source) != base
    (source / "aa.py").rename(source / "a.py")
    assert sc.source_digest(source) == base
    (source / "new.py").write_text("")
    assert sc.source_digest(source) != base


def test_the_digest_of_the_checkers_own_code_is_the_one_a_saved_result_is_made_with(tmp_path):
    source = vap.ROOT / "source"
    first = saved_in(tmp_path)
    assert first.key({}) == sc.SavedChecks(tmp_path, vap.BARE_PROOF_RULES, code_digest=sc.source_digest(source)).key({})


def test_the_name_of_a_file_of_one_proof_is_part_of_its_key(tmp_path, monkeypatch):
    ok = write(tmp_path, "ok", BARE_VALID)
    invalid = write(tmp_path, "invalid_ok", BARE_VALID)
    first = saved_in(tmp_path)
    assert [result.passed for result in vap.check_files([ok], first)] == [True]
    names = record_checks(monkeypatch)
    later = later_run(first)
    assert [result.passed for result in vap.check_files([invalid], later)] == [False]
    assert names == ["invalid_ok.txt"] and later.stored == []


def test_two_files_with_the_same_text_and_uses_share_a_saved_result(tmp_path, monkeypatch):
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    first = saved_in(tmp_path)
    vap.check_files([write(one, "Same", PAIR_TRANSPORT)], first)
    names = record_checks(monkeypatch)
    later = later_run(first)
    assert vap.check_files([write(two, "Other", PAIR_TRANSPORT)], later)[0].file == "Other.txt"
    assert names == [] and later.replayed == ["Other.txt"]


# ---------------------------------------------------------------------------
# What is never saved, and what is never replayed
# ---------------------------------------------------------------------------

def test_a_file_that_did_not_pass_is_not_saved(tmp_path, monkeypatch):
    a = write(tmp_path, "A", PAIR_TRANSPORT, BROKEN)
    first = saved_in(tmp_path)
    assert [result.passed for result in vap.check_files([a], first)] == [True, False]
    assert first.stored == [] and not first.directory.exists()
    names = record_checks(monkeypatch)
    vap.check_files([a], later_run(first))
    assert names == ["A.txt"]


def test_a_file_that_cites_a_file_that_did_not_pass_is_refused_and_not_saved(tmp_path):
    a = write(tmp_path, "A", PAIR_TRANSPORT, BROKEN)
    b = write(tmp_path, "B", uses("A"), citing("Use pair transport"))
    first = saved_in(tmp_path)
    results = vap.check_files([a, b], first)
    assert results[-1].message == "Use A.: A.txt did not pass, so its theorems cannot be cited; fix A.txt first"
    assert first.stored == []
    later = later_run(first)
    assert vap.check_files([b], later)[0].message.startswith("Use A.: A.txt has not been checked in this run, and no saved result")


def test_a_file_is_never_checked_because_it_is_cited_even_with_saved_results(tmp_path, monkeypatch):
    a, b = pair_and_citer(tmp_path)
    names = record_checks(monkeypatch)
    results = vap.check_files([b], saved_in(tmp_path))
    assert verdicts(results) == [("B.txt", "?", False)]
    assert results[0].message == (
        "Use A.: A.txt has not been checked in this run, and no saved result is for its present text. "
        "A file is never checked because another cites it, so check A.txt first")
    assert names == ["B.txt"]  # B is checked, and refused; A is not checked


def test_a_file_that_cites_a_file_that_changed_since_it_was_saved_is_refused(tmp_path):
    a, b = pair_and_citer(tmp_path)
    first = saved_in(tmp_path)
    vap.check_files([a, b], first)
    a.write_text(PAIR_TRANSPORT + "\n(* edited, and not checked again *)\n")
    results = vap.check_files([b], later_run(first))
    assert verdicts(results) == [("B.txt", "?", False)]
    assert "no saved result is for its present text" in results[0].message


def test_use_lines_that_are_refused_are_refused_whatever_was_saved(tmp_path):
    write(tmp_path, "A", PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("set theory"), citing("Use pair transport", cited="Pair transport"))
    first = saved_in(tmp_path)
    assert verdicts(vap.check_files([b], first))[-1] == ("B.txt", "1", False)
    clean = write(tmp_path, "C", uses("set theory"), PAIR_TRANSPORT)
    assert vap.check_files([clean], first)[0].passed and first.stored == ["C.txt"]
    write(tmp_path, "set theory", PAIR_TRANSPORT)
    results = vap.check_files([clean], later_run(first))
    assert verdicts(results) == [("C.txt", "?", False)]
    assert results[0].message.endswith("rename the file")


def test_a_cycle_of_use_lines_has_no_saved_result(tmp_path):
    write(tmp_path, "A", uses("B"), PAIR_TRANSPORT)
    write(tmp_path, "B", uses("A"), PAIR_TRANSPORT)
    first = saved_in(tmp_path)
    results = vap.run([str(tmp_path)], first)
    assert [result.message for result in results] == ["Use cycle: A.txt -> B.txt -> A.txt"] * 2
    assert first.stored == [] and not first.directory.exists()


def test_files_that_use_each_other_have_no_key_and_are_refused_when_checked_in_order(tmp_path):
    a = write(tmp_path, "A", uses("B"), PAIR_TRANSPORT)
    b = write(tmp_path, "B", uses("A"), PAIR_TRANSPORT)
    first = saved_in(tmp_path)
    assert vap.saved_key(a, a.read_text(), first) is None and vap.saved_key(b, b.read_text(), first) is None
    results = vap.check_files([a, b], first)
    assert [result.passed for result in results] == [False, False]
    assert first.stored == [] and first.replayed == [] and not first.directory.exists()


def test_a_file_cannot_use_itself_whatever_was_saved(tmp_path):
    a = write(tmp_path, "A", uses("A"), PAIR_TRANSPORT)
    first = saved_in(tmp_path)
    assert vap.check_files([a], first)[0].message == "Use A.: a file cannot use itself"
    assert first.stored == [] and vap.saved_key(a, a.read_text(), first) is None


def test_a_file_that_passed_but_cannot_be_saved_is_still_checked_and_passes(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the directory should be")
    saved = vap.open_saved_results(blocker / "saved")
    a = write(tmp_path, "A", PAIR_TRANSPORT)
    assert [result.passed for result in vap.check_files([a], saved)] == [True]
    assert saved.stored == [] and saved.not_stored == ["A.txt"]


# ---------------------------------------------------------------------------
# A saved result that cannot be read in full is no result
# ---------------------------------------------------------------------------

def damaged_one(data):
    return data[: len(data) // 2]


def damaged_two(data):
    return data[:-5] + bytes([data[-5] ^ 1]) + data[-4:]


def damaged_three(data):
    return b""


def damaged_four(data):
    return b"x" + data[1:]


def damaged_five(data):
    return data + b"more"


def damaged_six(data):
    head, _, rest = data.partition(b"\n")
    digest, _, payload = rest.partition(b"\n")
    return head + b"\n" + (b"0" if digest[:1] != b"0" else b"1") + digest[1:] + b"\n" + payload


@pytest.mark.parametrize("damage", [damaged_one, damaged_two, damaged_three, damaged_four, damaged_five, damaged_six])
@pytest.mark.parametrize("damaged, intact", [("A.txt", "B.txt"), ("B.txt", "A.txt")])
def test_a_damaged_saved_result_is_checked_again_and_saved_again(tmp_path, monkeypatch, damage, damaged, intact):
    a, b = pair_and_citer(tmp_path)
    first = saved_in(tmp_path)
    vap.check_files([a, b], first)
    record = record_of(first, tmp_path / damaged)
    record.write_bytes(damage(record.read_bytes()))
    names = record_checks(monkeypatch)
    later = later_run(first)
    assert all(result.passed for result in vap.check_files([a, b], later))
    # Only the file whose saved result is damaged is checked, and the file that
    # cites it still gets its theorems.
    assert names == [damaged] and later.stored == [damaged] and later.replayed == [intact]
    again = later_run(first)
    vap.check_files([a, b], again)
    assert again.replayed == ["A.txt", "B.txt"] and again.stored == []


def forged(saved, key, payload):
    """Write `payload` as the saved result for `key`, with the magic line and the
    digest that make it look like one."""
    data = sc._MAGIC + hashlib.sha256(payload).hexdigest().encode() + b"\n" + payload
    saved.directory.mkdir(parents=True, exist_ok=True)
    saved.path(key).write_bytes(data)


class _Reference:
    """Stands for a rule of the checker in a record that is forged."""


def referring_to(reference):
    """A pickler that writes every `_Reference` as the reference `reference`."""
    class Pickler(sc._Pickler):
        def persistent_id(self, obj):
            return reference if isinstance(obj, _Reference) else None

    return Pickler


def dumps(record, pickler=sc._Pickler):
    buffer = io.BytesIO()
    pickler(buffer, {}).dump(record)
    return buffer.getvalue()


GOOD = ("1", True, True, None, False)  # the result of a proof, as saved


def record(results=(GOOD,), theorems=(), key="k"):
    return {"key": key, "results": list(results), "theorems": list(theorems)}


def a_theorem_requiring(rule):
    theorem = copy.copy(a_theorem())
    theorem.required_rules = [rule]
    return theorem


def a_theorem_with(**attributes):
    theorem = copy.copy(a_theorem())
    for name, value in attributes.items():
        setattr(theorem, name, value)
    return theorem


def test_a_record_that_is_right_is_read(tmp_path):
    """The forged records below are refused for what is wrong with them: the
    same record without it is read."""
    saved = saved_in(tmp_path)
    forged(saved, "k", dumps(record(theorems=[a_theorem()])))
    read = saved.load("k")
    assert read.results == (GOOD,) and [theorem.name for theorem in read.theorems] == ["Pair transport"]


@pytest.mark.parametrize("wrong", [
    pytest.param(lambda: record(results=[GOOD, ("2", 1, True, None, False)]), id="a bad result after a good one"),
    pytest.param(lambda: record(results=[("1", True, True, None)]), id="a result of four fields"),
    pytest.param(lambda: record(results=[("1", True, True, None, False, 0)]), id="a result of six fields"),
    pytest.param(lambda: record(results=[(1, True, True, None, False)]), id="a proof number that is no text"),
    pytest.param(lambda: record(results=[("1", 1, True, None, False)]), id="expected valid that is no truth value"),
    pytest.param(lambda: record(results=[("1", True, 1, None, False)]), id="ok that is no truth value"),
    pytest.param(lambda: record(results=[("1", True, True, 7, False)]), id="a message that is no text"),
    pytest.param(lambda: record(results=[("1", True, True, None, 0)]), id="an implementation error that is no truth value"),
    pytest.param(lambda: record(theorems=[a_theorem(), "not a theorem"]), id="something that is no theorem, after a theorem"),
    pytest.param(lambda: record(theorems=[collections.OrderedDict()]), id="a class outside the package"),
    pytest.param(lambda: record(theorems=[a_theorem_with(extra=collections.OrderedDict())]),
                 id="a class outside the package inside a theorem"),
    pytest.param(lambda: record(key="another"), id="made for another key"),
    pytest.param(lambda: ["not", "a", "record"], id="not a record"),
])
def test_a_saved_result_of_the_wrong_kind_is_no_result(tmp_path, wrong):
    saved = saved_in(tmp_path)
    forged(saved, "k", dumps(wrong()))
    assert saved.load("k") is None


@pytest.mark.parametrize("index", [0, len(vap.BARE_PROOF_RULES) - 1])
def test_a_saved_theorem_gets_the_rule_of_the_checker_it_refers_to(tmp_path, index):
    saved = saved_in(tmp_path)
    forged(saved, "k", dumps(record(theorems=[a_theorem_requiring(_Reference())]), referring_to(("rule", index))))
    (theorem,) = saved.load("k").theorems
    assert theorem.required_rules[0] is vap.BARE_PROOF_RULES[index]


@pytest.mark.parametrize("reference", [
    ("rule", len(vap.BARE_PROOF_RULES)), ("rule", 10 ** 9), ("rule", -1), ("rule", "0"), ("rule", 0.0),
    ("other", 0), ("rule",), ("rule", 0, 0), "rule", 0,
], ids=repr)
def test_a_saved_theorem_that_refers_to_what_is_no_rule_of_the_checker_is_no_result(tmp_path, reference):
    saved = saved_in(tmp_path)
    forged(saved, "k", dumps(record(theorems=[a_theorem_requiring(_Reference())]), referring_to(reference)))
    assert saved.load("k") is None


class _CallsAFunction:
    def __init__(self, function, argument):
        self.function, self.argument = function, argument

    def __reduce__(self):
        return self.function, (self.argument,)


def test_a_saved_result_that_names_a_command_is_no_result_and_runs_nothing(tmp_path):
    marker = tmp_path / "ran"
    saved = saved_in(tmp_path)
    forged(saved, "k", dumps(record(theorems=[_CallsAFunction(os.system, f"touch {shlex.quote(str(marker))}")])))
    assert saved.load("k") is None
    assert not marker.exists()


def test_a_saved_result_that_names_a_function_of_python_is_no_result_and_runs_nothing(tmp_path):
    marker = tmp_path / "ran"
    saved = saved_in(tmp_path)
    source = f"open({str(marker)!r}, 'w').write('ran')"
    forged(saved, "k", dumps(record(theorems=[_CallsAFunction(eval, source)])))
    assert saved.load("k") is None
    assert not marker.exists()


def _short(text):
    data = text.encode()
    return b"\x8c" + bytes([len(data)]) + data


def test_a_saved_result_cannot_reach_a_function_through_a_module_of_the_package(tmp_path):
    # `SyLoPy.source.SavedChecks` imports `os`: a pickle can name `os.system` as
    # an attribute of that module, which is a function and not a class.
    marker = tmp_path / "ran"
    saved = saved_in(tmp_path)
    payload = (b"\x80\x04" + _short(sc.__name__) + _short("os.system") + b"\x93"
               + _short(f"touch {shlex.quote(str(marker))}") + b"\x85R.")
    assert pickle.loads(payload) == 0 and marker.exists()  # what the payload does, if it is loaded
    marker.unlink()
    forged(saved, "k", payload)
    assert saved.load("k") is None
    assert not marker.exists()


def test_a_missing_saved_result_is_no_result(tmp_path):
    assert saved_in(tmp_path).load("0" * 64) is None


# ---------------------------------------------------------------------------
# Saving and reading back
# ---------------------------------------------------------------------------

def a_theorem():
    exported: list = []
    vap.run_multi_proof_file(PAIR_TRANSPORT, exported=exported)
    return exported[0]


def test_a_saved_result_reads_back_as_it_was_saved(tmp_path):
    saved = saved_in(tmp_path)
    theorem = a_theorem()
    results = [("1", True, True, None, False), ("2", False, False, "refused: because", False)]
    assert saved.save("k", results, [theorem])
    read = saved.load("k")
    assert read.results == tuple(results)
    (restored,) = read.theorems
    assert restored is not theorem
    for field in ("name", "premises", "conclusion", "generalized_names", "required_axioms", "relation_requirements"):
        assert repr(getattr(restored, field)) == repr(getattr(theorem, field))
    assert sorted(p.name for p in saved.directory.iterdir()) == [f"k{sc._SUFFIX}"]
    assert saved.save("k", results[:1], [theorem])
    assert saved.load("k").results == tuple(results[:1])
    assert sorted(p.name for p in saved.directory.iterdir()) == [f"k{sc._SUFFIX}"]


def test_saving_makes_the_directories_it_needs(tmp_path):
    saved = vap.open_saved_results(tmp_path / "one" / "two" / "saved")
    assert saved.save("k", [GOOD], [])
    assert saved.load("k").results == (GOOD,)


def test_a_theorem_that_cannot_be_pickled_is_not_saved(tmp_path):
    saved = saved_in(tmp_path)
    theorem = copy.copy(a_theorem())
    theorem.extra = lambda: None
    assert saved.save("k", [], [theorem]) is False
    assert not saved.directory.exists()
    assert saved.load("k") is None


def test_a_theorem_that_could_not_be_read_back_is_not_saved(tmp_path):
    saved = saved_in(tmp_path)
    theorem = copy.copy(a_theorem())
    theorem.extra = collections.OrderedDict()  # pickles, but a saved result may not name it
    assert saved.save("k", [], [theorem]) is False
    assert not saved.directory.exists()


def test_saving_leaves_no_partial_file_when_it_fails(tmp_path, monkeypatch):
    saved = saved_in(tmp_path)

    def fail(source, destination):
        raise OSError("the disk is full")

    monkeypatch.setattr(os, "replace", fail)
    assert saved.save("k", [], [a_theorem()]) is False
    assert list(saved.directory.iterdir()) == []
    assert saved.load("k") is None
