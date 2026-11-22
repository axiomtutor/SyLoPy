"""Saved results: a file that has been checked is not checked again while
nothing it depends on has changed.

What checking a file finds is a function of three things: the text of the
file, the theorems of the files it uses, and the checker itself (its code, the
Python it runs on, and the rules it starts from). `SavedChecks` saves what a
check that passed found, under a *key*, a digest of all three. The key of a
file that uses other files contains the keys of those files, so a change
anywhere below a file changes its key. A later run computes the key again.
A saved result with that key was made from exactly the same inputs, so it
takes the place of checking; with any other key there is none, and the file is
checked. Nothing is saved for a file that did not pass.

A saved result holds the results of the file's proofs, as they were reported,
and the theorems the file promoted, for the files that cite it. The checker's
own rules are not copied into a theorem: a theorem that needs one of the rules
the checker starts from holds a reference to it, which is why the key contains
a digest of the list of those rules.

Trust. A saved result is trusted as far as the checker's own files are: whoever
can write the directory can make a file look checked. So nothing is saved or
read unless the caller asks (the test suite and CI check everything from
scratch), a result that cannot be read in full is no result, a result may name
only classes of this package, and to be sure of a file, check it without saved
results.
"""
from __future__ import annotations

import functools
import hashlib
import io
import json
import os
import pickle
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

import SyLoPy.source.ProofLogic as pl

FORMAT = 1
_MAGIC = b"SyLoPy saved check, format %d\n" % FORMAT
_SUFFIX = ".check"

# A saved result may name the classes of this package, and the containers that
# Python itself pickles by name; it may not name anything else.
_PACKAGE_PREFIX = __name__.rpartition(".")[0] + "."
_ALLOWED_BUILTINS = frozenset({"set", "frozenset", "tuple", "list", "dict"})


def source_digest(source_dir: Path) -> str:
    """A digest of every `.py` file under `source_dir`, and of the package's
    `__init__.py` above it: the code that a check runs on."""
    root = source_dir.parent
    files = [path for path in source_dir.rglob("*.py") if "__pycache__" not in path.parts]
    package_init = root / "__init__.py"
    if package_init.is_file():
        files.append(package_init)
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda found: found.relative_to(root).as_posix()):
        data = path.read_bytes()
        digest.update(f"{path.relative_to(root).as_posix()}\0{len(data)}\0".encode())
        digest.update(data)
    return digest.hexdigest()


@functools.lru_cache(maxsize=None)
def _default_source_digest() -> str:
    return source_digest(Path(__file__).resolve().parent)


def rules_digest(rules: Iterable[Any]) -> str:
    """A digest of a list of rules, by position, class and name."""
    lines = (f"{type(rule).__module__}.{type(rule).__qualname__}\t{getattr(rule, 'name', '')}" for rule in rules)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SavedFile(NamedTuple):
    """What is saved of a file that passed: the result of each of its proofs,
    as `(proof id, expected valid, ok, message, implementation error)`, and
    the theorems it promoted."""
    results: Tuple[Tuple[str, bool, bool, Optional[str], bool], ...]
    theorems: Tuple[pl.TheoremRule, ...]


class _Pickler(pickle.Pickler):
    def __init__(self, file, rule_index: Dict[int, int]):
        super().__init__(file, protocol=pickle.HIGHEST_PROTOCOL)
        self._rule_index = rule_index

    def persistent_id(self, obj):
        index = self._rule_index.get(id(obj))
        return None if index is None else ("rule", index)


class _Unpickler(pickle.Unpickler):
    def __init__(self, file, rules: Sequence[Any]):
        super().__init__(file)
        self._rules = rules

    def persistent_load(self, pid):
        if (isinstance(pid, tuple) and len(pid) == 2 and pid[0] == "rule"
                and isinstance(pid[1], int) and 0 <= pid[1] < len(self._rules)):
            return self._rules[pid[1]]
        raise pickle.UnpicklingError(f"a saved result refers to {pid!r}, which is not a rule")

    def find_class(self, module, name):
        if module == "builtins" and name in _ALLOWED_BUILTINS:
            return super().find_class(module, name)
        if module.startswith(_PACKAGE_PREFIX):
            found = super().find_class(module, name)
            if isinstance(found, type):
                return found
        raise pickle.UnpicklingError(f"{module}.{name} may not be named in a saved result")


class SavedChecks:
    """Saved results in the directory `directory`.

    `rules` is the list of rules the checker starts from: a theorem that needs
    one of them is saved with a reference to it. `code_digest` is the digest of
    the checker's code; it is computed from this package unless given.

    `replayed`, `stored` and `not_stored` are the names of the files whose saved
    results were used, whose results were saved, and that passed but could not
    be saved, since this object was made."""

    def __init__(self, directory, rules: Iterable[Any], *, code_digest: Optional[str] = None):
        self.directory = Path(directory)
        self._rules = tuple(rules)
        self._rule_index = {id(rule): index for index, rule in enumerate(self._rules)}
        self._environment = rules_digest(self._rules)
        self._code = code_digest if code_digest is not None else _default_source_digest()
        self.replayed: List[str] = []
        self.stored: List[str] = []
        self.not_stored: List[str] = []

    def key(self, file: Dict[str, Any]) -> str:
        """The key for a file described by `file` (JSON data: its text digest,
        the keys of the files it uses, ...) under this checker."""
        description = {
            "format": FORMAT,
            "code": self._code,
            "python": list(sys.version_info[:2]),
            "environment": self._environment,
            "file": file,
        }
        return hashlib.sha256(json.dumps(description, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def path(self, key: str) -> Path:
        return self.directory / f"{key}{_SUFFIX}"

    def load(self, key: str) -> Optional[SavedFile]:
        """The saved result for `key`, or None. A result that cannot be read
        in full, that was altered, or that names anything it may not, is no
        result: this never raises, and the file is checked instead."""
        try:
            data = self.path(key).read_bytes()
            if not data.startswith(_MAGIC):
                return None
            stated, newline, payload = data[len(_MAGIC):].partition(b"\n")
            if not newline or stated != hashlib.sha256(payload).hexdigest().encode():
                return None
            return self._read(key, payload)
        except Exception:
            return None

    def _read(self, key: str, payload: bytes) -> Optional[SavedFile]:
        record = _Unpickler(io.BytesIO(payload), self._rules).load()
        if not isinstance(record, dict) or record.get("key") != key:
            return None
        results = tuple(tuple(entry) for entry in record["results"])
        theorems = tuple(record["theorems"])
        if not all(
            len(entry) == 5 and isinstance(entry[0], str) and isinstance(entry[1], bool)
            and isinstance(entry[2], bool) and (entry[3] is None or isinstance(entry[3], str))
            and isinstance(entry[4], bool)
            for entry in results
        ):
            return None
        if not all(isinstance(theorem, pl.TheoremRule) for theorem in theorems):
            return None
        return SavedFile(results, theorems)

    def save(self, key: str, results: Iterable[Sequence[Any]], theorems: Iterable[pl.TheoremRule]) -> bool:
        """Save a result under `key`; False if it could not be saved, which
        never stops the check: the file is simply checked again next time."""
        try:
            buffer = io.BytesIO()
            _Pickler(buffer, self._rule_index).dump(
                {"key": key, "results": [tuple(entry) for entry in results], "theorems": list(theorems)}
            )
            payload = buffer.getvalue()
            # Save only what will be read back.
            if self._read(key, payload) is None:
                return False
            data = _MAGIC + hashlib.sha256(payload).hexdigest().encode() + b"\n" + payload
            self.directory.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=self.directory, prefix=".saving-", suffix=".tmp")
            try:
                with os.fdopen(handle, "wb") as out:
                    out.write(data)
                os.replace(temporary, self.path(key))
            except BaseException:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise
        except Exception:
            return False
        return True
