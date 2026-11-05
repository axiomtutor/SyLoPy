# Architecture status

SyLoPy is organized as a small proof-language compiler with a proof-theoretic
kernel:

```text
proof text
    -> SurfaceProof
    -> elaboration
    -> ElaboratedEntries
    -> ProofLogic.Proof
```

`ProofParser` is the public parser facade. Parsing produces the surface
representation before elaboration converts it into the strict entry language
checked by `ProofLogic`. Source-origin metadata is retained through
elaboration so errors in generated core steps can still be reported against
the user's source.

Theory modules extend `TheoryEnvironment` with syntax and core resources.
Discrete mathematics exposes its relation declaration interpretation as a
`RelationDeclarationRecipe`, rather than requiring the generic elaborator to
construct the relation's semantic representation itself.


## Surface representation and elaboration

The front end keeps three representations:

- **Text:** the user's formulas, justifications, labels, and subproof boundaries.
- **Surface AST:** `SurfaceProof`, `SurfaceLine`, `SurfaceSubproof`, and `SourceSpan`, preserving original text and locations.
- **Core entries:** `ElaboratedEntries`, the tuple language consumed by `ProofLogic.ProofValidator`.

`ElaboratedEntries` also carries source-origin mappings and the theory resources required by the elaborated proof. `ProofLogic.Proof` merges those resources before validation. Each generated core label maps to a `CoreOrigin`, so a kernel error on a synthetic step is reported against the surface line that generated it.

For example, `Subset proof below` lowers to universal generalization over an arbitrary element and conditional introduction from the user's subproof. Synthetic labels are internal; they are not inserted into the proof file.

```text
2. forall x, (In(x, S) -> In(x, T)). (UniversalGeneralization from subproof below)
begin subproof
  2.__arbitrary. a. (arbitrary)
  2.__conditional. In(a, S) -> In(a, T). (ConditionalIntroduction from subproof below)
  begin subproof
    2.1. In(a, S). (assume)
    ...
    2.n. In(a, T). (...)
  end subproof
end subproof
```

## Theory parser dispatch

The parser extension points have different precedence and scope:

- `formula_parsers` receive a whole ordinary proof-line expression and each whole premise-bundle component before generic connective splitting. They return `SurfaceExpression`, which can retain theory-specific data such as raw subset operands. This dispatch is not recursive.
- `phrase_parsers` receive a whole recursive formula substring before connective splitting. Use them for phrases containing connective-looking words; they must decline unless the entire substring is their phrase.
- `phrase_spans` protect recognized theory phrases inside larger formulas before connective splitting.
- `nested_formula_parsers` and `term_parsers` recognize formulas and terms during recursive parsing. Nested formula parsers run after generic connective splits, preventing them from swallowing a larger expression.
- `line_elaborators` and `declaration_recipes` handle proof constructs and structured declarations; theory inference rules, axioms, and declarations supply core resources.

Prefer theory-local parsers, recipes, and line elaborators. Lower new proof forms to existing core rules when possible. A genuinely theory-specific inference can be supplied as a registered rule; do not describe it as desugared unless the implementation creates and validates that derivation.

To inspect lowering, call `ProofParser.format_core_proof(entries)` after `parse_proof_text`. The formatter is diagnostic only; validation uses the in-memory entries and does not parse the formatted text again.

### Registered examples and a line-elaborator pattern

Set theory registers whole-line membership/subset syntax and set-operation phrases through `formula_parsers`; recursive set formulas and terms through `nested_formula_parsers`, `phrase_parsers`, `phrase_spans`, and `term_parsers`; and `Subset proof below` through a line elaborator. Its enumeration and set-builder forms lower to ordinary membership formulas. The `EmptySetPropertyRule` and `SetEqualityRule` remain specialized inference rules, not merely parser sugar.

Number theory extends the natural-number and set-theory environments. It registers quotient notation such as `n/a` as term syntax, divisibility and integerhood through nested formula parsers, and quotient defining-property and uniqueness rules. Its declarations include `Int`, `Plus`, `Times`, `Neg`, and `Quotient`.

A proof-form extension should validate the surface contract, lower to existing core entries where possible, and register source origins for any synthetic labels. For example:

```python
def elaborate_some_construct(line, context):
    if not matches(line):
        return None
    # Validate the surface contract.
    # Generate a core entry, possibly with nested core entries.
    # Register origins for synthetic labels.
    return core_entry
```

Register the elaborator in `TheoryEnvironment.line_elaborators`. Use a specialized inference rule only when ordinary core derivation is not the right implementation.


## Current theory boundary

A theory should provide, as appropriate:

- surface formula parsers;
- nested formula parsers;
- phrase parsers and phrase-span finders, for phrases that contain connective
  words ("x is a or b"), so the connective grammar cannot cut them apart;
- term parsers;
- line elaborators;
- declaration recipes;
- inference rules;
- axioms;
- built-in declarations.

Adding a structure should therefore normally mean adding a recipe and core
rules to a theory module rather than modifying generic elaboration logic.

## Surface sugar versus inference implementation

"Prefer sugar" is a design principle, not a claim that every mathematical
inference currently expands into primitive logical steps. Keep two questions
separate:

1. **Surface lowering:** what formula, term, declaration, or core proof entries
   does the user's notation become?
2. **Inference checking:** does the validator use ordinary logical rules and
   formulas, or a theory-specific `InferenceRule` / axiom implementation?

Examples from the current code:

| Feature | Surface/elaboration behavior | Inference implementation |
| --- | --- | --- |
| Divisibility, `a\|n` | Expands at parse time to `exists m, (Int(m) and n = a * m)`. | Ordinary existential introduction/elimination are used; there is no separate divisibility rule. |
| `Subset proof below` | Elaborates into universal generalization and conditional introduction, concluding `forall x, (In(x,S) -> In(x,T))`. | The generated core proof is validated using existing proof rules. |
| Relation declarations | `RelationDeclarationRecipe` creates predicate declarations carrying the relation's carrier and property metadata. | `DiscreteMathCore.py` provides specialized rules such as relation symmetry, transitivity, and reflexivity; they check the declared property and, where needed, the carrier. |
| Set equality | The conclusion is the ordinary formula `X = Y`. | `SetEqualityRule` directly checks for subset formulas in opposite directions; the current implementation does not expand this citation into a subproof of more primitive steps. |
| Uniqueness | The conclusion is ordinary first-order logic: `exists W, (B(W) and forall V, (B(V) -> V = W))`. | `UniquenessRule` is a specialized, context-sensitive rule because soundness depends on whether the candidate constant is genuinely arbitrary. It is not a new `ExistsUnique` connective. |
| Quotient notation, `n/a` | Parses as the term `Quotient(n, a)`. | Its mathematical behavior is governed by the theory's quotient defining-property and uniqueness axioms; the term itself is not expanded away into a formula. |

Thus, a feature can use surface sugar and still rely on a specialized theory
rule or axiom. Conversely, a specialized rule can conclude an ordinary core
formula without creating a new formula-AST connective.

When adding mathematical syntax or inference, document these points separately:
(a) its surface-to-core lowering, (b) the checking mechanism and side conditions,
and (c) whether its mathematical force is definitional, derived by existing
rules, or axiomatic. Prefer formula/proof-entry expansion when it remains clear
and efficient, but do not describe a specialized rule as "desugared to logic"
unless the implementation actually constructs and validates that derivation.

## Rules that look at the proof around them

A rule normally sees only the lines it cites. A rule that is sound only
relative to the rest of the proof can implement
`InferenceRule.applies_in_context(candidates, phi, context)` instead. The
validator passes a `RuleContext`: `hypotheses` (what the proof takes for
granted: premises, `(Axiom)` lines, declarations that state a formula,
witness lines such as `Existence from L` and the direct Pairing witness, and
the open assumptions) and `arbitrary_constants` (constants introduced by a
plain declaration or as the flag of a Fresh Variable subproof, minus any name
that a declaration's metadata refers to, such as a relation's carrier). Rules
that do not opt in are unchanged. A rule that refuses can also implement
`explain_in_context`, and the validator appends its reason to the message.
`Uniqueness`, `UniversalGeneralization` and `ExistentialElimination` use the
hypotheses to check that the constant they treat as arbitrary occurs in none of
them -- including a premise stated inside the subproof they consume, which no
earlier check could see -- and that no declaration's structure names it; the
relation rules read `declaration(name)`. `Uniqueness` never applies without a
context; the other two keep their context-free checks when asked directly.
Theorem promotion takes its premises from the same record the validator keeps
(`ProofValidator.own_givens`). What a theorem cannot carry as a premise -- the
theory's axioms the proof cited and the non-standard rules it used
(`used_axioms`, `used_rules`) -- becomes the theorem's `required_axioms` and
`required_rules`, which `TheoremRule` checks at the citation through
`RuleContext.lists_axiom` and `RuleContext.allows_rule`. A rule counts as
allowed there, and for every citation the validator checks, when it is the same
rule, configuration included, as one the proof was configured with
(`InferenceRule.same_configuration`, asked of the registered rule): induction
over `Int` is not induction over `Nat`, and an unregistered subclass is not its
parent. `Proof` and promotion merge rule lists by the same test.

An `(Axiom)` line may state only what the proof's axiom list holds, once the
proof has a list; a proof given no axioms takes any formula as an axiom (a bare
proof). That is wrong for a theory that cites its axioms by name and so lists
none, so a theory can close its list: `TheoryEnvironment.axioms_closed` reaches
`ElaboratedEntries`, `Proof` and `ProofValidator`, and `ProofValidator.axioms_closed`
is the one place the question is answered (the axiom check, the record of which
axioms a proof used, the WLOG replay validators). A list that is not empty closes
itself and needs no flag. Set theory closes an empty list, which is what retired
generic `(Axiom)` for its four axioms. A refused `(Axiom)` line is answered with
the rules of the proof that justify the formula outright (`citation` of a rule is
the phrase a proof writes, when it is not the rule's `name`).

The invariant for such a rule: whatever the proof relies on that says
something about a constant must reach the context, as a recorded formula or as
declaration metadata. A fact a rule reads from somewhere else (a new kind of
declaration with hidden structure, a recipe that registers a rule about a
declared constant) must be made visible the same way, or the rule is unsound
for that constant. The two holes found so far -- the direct witness line and
the relation carrier -- are in `tests/testProofs/uniqueness_red_team.txt`.

## Remaining consolidation work

Declaration-justification `Let` statements now have one recipe-dispatch
path: `parse_surface_declaration_statement` builds the surface AST, and
`elaborate_compound_declaration` offers each contiguous run of declaration
clauses to registered recipes, including recipes that consume multiple clauses.
The redundant `elaborate_typed_declaration` dispatcher has been removed.
`parse_declaration_prefix` remains for the distinct generic premise/fallback
path, notably declaration-like premises that use `such that`; it is not a
second route for ordinary `(Declaration)` `Let` statements.

Further consolidation should target demonstrated duplication rather than move
theory-specific syntax indiscriminately. New theory-specific syntax should
continue to use `TheoryEnvironment` and declaration recipes where appropriate.

`ProofContext` is the lexical scope for declarations, assumptions, labels and
arbitrary bindings during elaboration; the elaborator no longer keeps a
parallel declaration scope.

The kernel's `LabelScope` and `DeclarationScope` in `ProofLogic.py` deliberately
remain separate validation-time scope structures. This preserves the compiler
boundary between elaboration and kernel validation: `ProofContext` manages
source-level bindings, while the kernel scopes operate only on elaborated
entries. Their overlapping lexical semantics are maintained by regression
tests.

The `Use discrete math.` directive is currently validated and accepted, while
the default environment remains backward-compatible and loads the available
theory modules. A future language-version change can make directives select
theory environments strictly after the existing proof corpus has been
updated.

The repository has `.gitignore` hygiene and GitHub Actions that run the same
complete test command used locally. Test counts are intentionally not
hard-coded into architecture documentation.
