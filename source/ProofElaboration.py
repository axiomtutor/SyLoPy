


"""Surface-proof and elaboration data structures.

The text accepted by SyLoPy is intentionally more natural than the small
entry language checked by :mod:`ProofLogic`.  This module supplies the
intermediate representation between those two layers:

    proof text -> SurfaceProof -> ElaboratedEntries -> ProofLogic.Proof

A ``SurfaceProof`` preserves what the user wrote, including source lines and
natural-language justifications.  An elaborator may replace one surface line
with several synthetic core steps.  ``ElaboratedEntries`` retains an origin
map so validator errors on synthetic steps can still be reported against the
surface line that produced them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Union

from SyLoPy.source.ProofContext import ProofContext


@dataclass(frozen=True)
class SourceSpan:
    """Location of one logical item in the user's proof text."""

    start_line: int
    end_line: int
    original_text: str
    label: Optional[str] = None

    @property
    def location(self) -> str:
        if self.label:
            return f"Line {self.label}"
        if self.start_line == self.end_line:
            return f"Source line {self.start_line}"
        return f"Source lines {self.start_line}-{self.end_line}"


@dataclass(frozen=True)
class SurfaceDeclaration:
    """One symbol declaration in the surface declaration language."""

    name: str
    kind: str
    descriptor: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    span: Optional[SourceSpan] = None


@dataclass(frozen=True)
class SurfaceDeclarationClause:
    """A coordinated declaration clause, possibly introducing several names."""

    declarations: List[SurfaceDeclaration]
    span: Optional[SourceSpan] = None
    membership_expression: Optional[str] = None


@dataclass(frozen=True)
class SurfacePremiseClause:
    """A coordinated premise clause retained as formula text until elaboration."""

    formula: str
    span: Optional[SourceSpan] = None


SurfaceDeclarationClauseItem = Union[SurfaceDeclarationClause, SurfacePremiseClause]


@dataclass(frozen=True)
class SurfaceDeclarationStatement:
    """The surface AST for a coordinated ``Let`` statement."""

    clauses: List[SurfaceDeclarationClauseItem]
    span: SourceSpan


@dataclass
class SurfaceLine:
    """A numbered line before formula/rule sugar has been elaborated."""

    label: Optional[str]
    formula_text: str
    justification_text: str
    span: SourceSpan
    subproofs: List["SurfaceSubproof"] = field(default_factory=list)
    declaration_statement: Optional[SurfaceDeclarationStatement] = None


@dataclass
class SurfaceSubproof:
    """A surface subproof, explicit or inferred from descendant labels."""

    entries: List["SurfaceEntry"]
    span: SourceSpan
    label: Optional[str] = None
    implicit: bool = False


SurfaceEntry = Union[SurfaceLine, SurfaceSubproof]


@dataclass
class SurfaceProof:
    """Parsed surface proof together with the original non-comment lines."""

    entries: List[SurfaceEntry]
    raw_lines: List[str]
    source_text: str


@dataclass(frozen=True)
class SurfaceExpression:
    """A formula-like surface expression.

    ``kind='core'`` stores a normal FormulaLogic formula in ``value``.
    Theory extensions may use another kind and retain structured data in
    ``value`` until an elaborator lowers it to core logic.
    """

    kind: str
    value: Any
    text: str


@dataclass(frozen=True)
class CoreOrigin:
    """Relationship between a core entry and the surface construct it came from."""

    span: SourceSpan
    construct: str = "proof line"
    synthetic: bool = False


class ElaboratedEntries(list):
    """A list of ProofLogic entries with elaboration metadata.

    It deliberately subclasses ``list`` so all existing callers that expect
    the old ``entries`` API continue to work unchanged.
    """

    def __init__(
        self,
        values: Iterable[Any] = (),
        *,
        origin_by_label: Optional[Dict[str, CoreOrigin]] = None,
        surface_proof: Optional[SurfaceProof] = None,
        required_rules: Optional[Sequence[Any]] = None,
        required_axioms: Optional[Sequence[Any]] = None,
        required_declarations: Optional[Sequence[Any]] = None,
    ):
        super().__init__(values)
        self.origin_by_label: Dict[str, CoreOrigin] = dict(origin_by_label or {})
        self.surface_proof = surface_proof
        self.required_rules = list(required_rules or [])
        self.required_axioms = list(required_axioms or [])
        self.required_declarations = list(required_declarations or [])


class ElaborationError(ValueError):
    """A source-located failure while translating surface syntax."""

    def __init__(self, detail: str, span: Optional[SourceSpan] = None):
        self.detail = detail
        self.span = span
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.span is None:
            return self.detail
        return f"{self.span.location}: {self.detail}"


FormulaParser = Callable[[str, set], Optional[SurfaceExpression]]
LineElaborator = Callable[[SurfaceLine, Any], Optional[Any]]
TermParser = Callable[[str, set], Optional[Any]]
NestedFormulaParser = Callable[[str, set], Optional[Any]]


@dataclass
class TheoryEnvironment:
    """Theory-specific syntax and core resources used during elaboration."""

    name: str = "base logic"
    formula_parsers: List[FormulaParser] = field(default_factory=list)
    line_elaborators: List[LineElaborator] = field(default_factory=list)
    rules: List[Any] = field(default_factory=list)
    axioms: List[Any] = field(default_factory=list)
    declarations: List[Any] = field(default_factory=list)
    term_parsers: List[TermParser] = field(default_factory=list)
    nested_formula_parsers: List[NestedFormulaParser] = field(default_factory=list)
    declaration_recipes: List[Any] = field(default_factory=list)

    def extended(self, *others: "TheoryEnvironment") -> "TheoryEnvironment":
        result = TheoryEnvironment(name=" + ".join([self.name, *[o.name for o in others]]))
        for environment in (self, *others):
            result.formula_parsers.extend(environment.formula_parsers)
            result.line_elaborators.extend(environment.line_elaborators)
            result.rules.extend(environment.rules)
            result.axioms.extend(environment.axioms)
            result.declarations.extend(environment.declarations)
            result.term_parsers.extend(environment.term_parsers)
            result.nested_formula_parsers.extend(environment.nested_formula_parsers)
            result.declaration_recipes.extend(environment.declaration_recipes)
        return result


