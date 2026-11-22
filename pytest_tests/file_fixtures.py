"""Small proof files for the tests of files that use files (`Use NAME.`) and of
saved results: a theorem, a proof that cites it, a proof that is broken, and
the functions that write them to a directory and run the checker over them."""
from __future__ import annotations

from pathlib import Path
from typing import List

from .support import mp as vap


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


def record_checks(monkeypatch) -> List[str]:
    """Record the name of every file whose proofs the checker actually checks."""
    names: List[str] = []
    for attribute in ("_check_multi_proof_file", "_check_bare_proof_file"):
        real = getattr(vap, attribute)

        def recorder(path, *args, _real=real, **kwargs):
            names.append(path.name)
            return _real(path, *args, **kwargs)

        monkeypatch.setattr(vap, attribute, recorder)
    return names
