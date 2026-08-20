from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "ProofLogic.py"
VALIDATOR = ROOT / "source" / "ProofValidator.py"
CONTEXT_VALIDATOR = ROOT / "source" / "ContextProofValidator.py"


def node_source(text: str, node: ast.AST) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1:node.end_lineno])


def extract_class(text: str, name: str) -> tuple[ast.ClassDef, str]:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node, node_source(text, node)
    raise RuntimeError(f"could not find class {name}")


def remove_classes(text: str, names: set[str]) -> str:
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    ranges = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in names:
            ranges.append((node.lineno - 1, node.end_lineno))
    for start, end in sorted(ranges, reverse=True):
        del lines[start:end]
    return "".join(lines)


def refactor_validator_class(source: str) -> str:
    source = source.replace("class ProofValidator:", "class ProofValidator:")

    # The validator now has one lexical environment.  Replace the paired
    # legacy parameters and the paired child-scope calls first, before
    # replacing individual operations.
    source = re.sub(
        r"labels: LabelScope,\s*declarations: DeclarationScope",
        "context: ProofContext",
        source,
    )
    source = re.sub(
        r"labels: LabelScope",
        "context: ProofContext",
        source,
    )
    source = re.sub(
        r"declarations: DeclarationScope",
        "context: ProofContext",
        source,
    )
    source = source.replace("labels.child(), declarations.child()", "context.child()")
    source = source.replace("labels.child(),\n                declarations.child()", "context.child()")
    source = source.replace("labels.child(),\n                            declarations.child()", "context.child()")

    # Paired scope arguments in validator-internal calls.
    source = re.sub(r"labels,\s*declarations,\s*outer_context", "context, outer_context", source)
    source = re.sub(r"labels,\s*declarations,\s*seen", "context, seen", source)
    source = re.sub(r"labels,\s*declarations,\s*seen,", "context, seen,", source)
    source = re.sub(r"labels,\s*declarations\)", "context)", source)
    source = re.sub(r"labels,\s*declarations,", "context,", source)

    # Rename remaining parameter/local references.  These replacements are
    # deliberately restricted to the semantic operations, rather than doing
    # a blind identifier replacement that could alter self.declarations.
    source = source.replace("i not in labels", "context.lookup_label(i) is None")
    source = source.replace("index not in labels", "context.lookup_label(index) is None")
    source = source.replace("labels[index]", "context.require_label(index).value")
    source = source.replace("labels[label] = phi", "context.bind_label(label, phi)")
    source = source.replace("labels[entry.label] = sp_rec", "context.bind_label(entry.label, sp_rec)")
    source = source.replace("declarations.lookup(", "context.lookup_declaration(")
    source = source.replace("declarations.declare(", "context.declare(")

    # Any remaining standalone scope names in method calls are now context.
    source = re.sub(r"\bdeclarations\b(?=,|\))", "context", source)
    source = re.sub(r"\blabels\b(?=,|\))", "context", source)

    # Replace the top-level initialization with a real ProofContext.
    old = '''        seen: list = []\n        labels = LabelScope()\n        declarations = DeclarationScope(initial=self.initial_declarations)\n        return self._validate_block(entries, None, seen, labels, declarations, outer_context=seen)'''
    new = '''        seen: list = []\n        context = ProofContext()\n        for declaration in self.initial_declarations:\n            try:\n                context.declare(declaration)\n            except DuplicateBindingError:\n                existing = context.lookup_declaration(declaration.name)\n                return False, _mk_error(\n                    None, None, 0, CATEGORY_DECLARATION_CONFLICT,\n                    f"symbol '{declaration.name}' is already declared as "\n                    f"{existing.kind if existing else 'another symbol kind'}",\n                ), None\n        return self._validate_block(entries, None, seen, context, outer_context=seen)'''
    if old not in source:
        raise RuntimeError("could not find legacy validator initialization")
    source = source.replace(old, new)

    # The source-level type names in docstrings are documentation only, but
    # keeping them accurate makes the extracted module self-contained.
    source = source.replace("`labels`", "`context`")
    source = source.replace("`declarations`", "`context`")
    source = source.replace("LabelScope", "ProofContext")
    source = source.replace("DeclarationScope", "ProofContext")

    return source


def main() -> None:
    text = SOURCE.read_text()
    validator_node, validator_source = extract_class(text, "ProofValidator")
    validator_source = refactor_validator_class(validator_source)

    validator_module = '''"""Proof validation over an explicit lexical ``ProofContext``.\n\nThe validator owns proof history (``seen``) while ``ProofContext`` owns\nlexical visibility of declarations, labels, assumptions, arbitrary bindings,\nand theorem bindings.  Inference rules remain pure and are imported from\n``ProofLogic``.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any, Dict, Iterable, Iterator, List, NamedTuple, Optional, Tuple, Union\nimport itertools\n\nimport SyLoPy.source.FormulaLogic as fl\nimport SyLoPy.source.TermLogic as tl\nfrom .ProofContext import ProofContext, DuplicateBindingError, UnknownBindingError\nfrom . import ProofLogic as _pl\n\n# ProofLogic contains the formula/rule machinery.  Import its namespace\n# wholesale so the extracted validator retains exactly the same semantic\n# dependencies without duplicating kernel helpers.  ProofLogic no longer\n# imports this module, so there is no import cycle.\nglobals().update({name: value for name, value in vars(_pl).items()\n                  if name not in {"ProofValidator", "Proof"}})\n\n'''
    validator_module += validator_source
    VALIDATOR.write_text(validator_module)

    # Remove the legacy validator and the two obsolete scope classes from the
    # semantic core.  Proof remains in ProofLogic, but imports its validator
    # lazily at the point of validation to avoid a module cycle.
    text = remove_classes(text, {"DeclarationScope", "LabelScope", "ProofValidator"})
    text = text.replace(
        """        validator = ProofValidator(\n            self.rules, self.premises, self.axioms,\n            declarations=self.declarations,\n        )""",
        """        from .ProofValidator import ProofValidator\n\n        validator = ProofValidator(\n            self.rules, self.premises, self.axioms,\n            declarations=self.declarations,\n        )""",
    )
    if "from .ProofValidator import ProofValidator" not in text:
        raise RuntimeError("failed to update Proof.check_detailed")
    SOURCE.write_text(text)

    if CONTEXT_VALIDATOR.exists():
        CONTEXT_VALIDATOR.unlink()


if __name__ == "__main__":
    main()
