# Refinement Type System for SyLoPy

**Status: design proposal only.** This document proposes an architecture; it does not authorize changes to the proof kernel. The first motivating application is the owner's requirement that divisibility be accepted only when both operands are known to be integers, with a type error otherwise.

## 1. Goals and constraints

The checker should reject a statement such as `a|b` when neither the declaration nor the active logical context establishes that `a` and `b` are integers. It should accept it after `a` and `b` have been declared as integers, or inside a scope whose assumptions establish their integer status. A local fact must not escape its subproof.

This should be infrastructure for future theories, not a special case for the divisibility parser. It should support:
- functions with argument and result types, such as `Times : Int × Int → Int`;
- predicates with typed arguments, when a theory needs them;
- overlapping refinements and inclusion relations, such as `Nat <: Int`;
- type facts established by declarations, premises, assumptions, and previously validated proof lines;
- source-located diagnostics that distinguish a type error from a failed inference rule.

SyLoPy should **not** be converted wholesale to disjoint many-sorted first-order logic. Its current mathematical vocabulary treats `Nat` and `Int` as overlapping predicates on one object domain, and set-theoretic objects can also be integers. The type layer should model refinements over the existing object domain. It should not assume types are mutually exclusive, nor invent coercions between unrelated refinements.

## 2. Separate three concepts currently easy to conflate

1. **Vocabulary declarations** say which constants, functions, and predicates exist. The existing `Declaration` remains responsible for that.
2. **Type signatures** state the typing contract of an operation: which refinements its arguments must satisfy, and (where guaranteed) the refinement of its result.
3. **Logical formulas** such as `Int(a)` remain ordinary formulas handled by the existing proof rules. A typing judgment is not itself a derived proof line.

In particular, `Declaration.type_name` must not become the type system by accident. It is currently descriptive metadata; interpreting arbitrary strings such as `"integer"` as types would make correctness depend on English parsing details. Typed declaration phrases should be resolved through registered type descriptors and recipes, not through ad hoc string inspection in the validator.

## 3. Proposed data model

Add a small, independent typing module (working name: `source/TypeSystem.py`) with immutable records along these lines:

- `TypeSpec`: a type name and its logical predicate symbol, plus any explicitly declared supertypes.
- `FunctionSignature`: a function symbol, the required type of each argument, and an optional result type.
- `PredicateSignature`: a predicate symbol and any argument-type requirements.
- `TypeSystem`: the registry of these declarations, including validated inclusion relationships and conflict checks when theory environments are combined.

The exact class names are provisional. The architectural requirement is that signatures be explicit, inspectable data rather than logic hidden in parser callbacks.

`TheoryEnvironment` should register/compose this metadata alongside rules, axioms, and vocabulary. `ElaboratedEntries` should carry the required typing metadata just as it currently carries required rules, axioms, and declarations. The validator must receive the same type system whether the caller uses the text API or constructs a `Proof` directly.

A signature with a result type must have one authoritative meaning. The type checker should not silently assume closure facts that contradict the theory's logical axioms. The implementation should either derive the relevant closure axiom from the signature or validate the signature against the theory's explicit closure axiom/schema. This is an important consistency check, not a documentation detail.

## 4. Typing judgment and context

Conceptually, the checker establishes judgments of the form

\[
\Gamma;\Sigma \vdash t : T
\]

where \(\Sigma\) is the registered signature/type system and \(\Gamma\) is the typing context at the exact point being checked. A term has type \(T\) when its registered function signature permits it and its arguments meet their required types, or when \(\Gamma\) establishes the relevant type predicate. Registered inclusion relationships propagate type facts; for example, evidence of `Nat(a)` can establish `Int(a)` when `Nat <: Int` is part of the composed type system.

This is a conservative checker, not an arbitrary first-order theorem prover. It should use type facts that are explicitly established by the supported mechanisms, rather than trying to prove any imaginable formula from every axiom in the theory.

The context must be updated in the same order and scope as proof validation:

- A typed object declaration establishes its declared type. It should also expose the corresponding ordinary type predicate (e.g. `Int(a)`) to mathematical proof reasoning, following the existing `Type.as_declaration_recipe()` pattern.
- A type-predicate formula contributes a type fact only after that line has passed normal validation.
- An open assumption contributes local type facts inside its subproof; those facts disappear when the subproof closes.
- Facts from a closed sibling subproof never leak.
- A failed or unvalidated line must never supply type facts to a later accepted line.
- A fact from an external premise is available only according to the existing proof-premise semantics; a raw formula that is ill-typed must not be made acceptable simply by being listed as a premise.

A conservative first version need not use a general theorem prover to discover that a formula implies a type. It should recognize direct type-predicate facts and a deliberately specified set of logical guard patterns. Additional propagation rules can be added with explicit tests.

## 5. Logical guards and quantified formulas

Because this is a refinement system over ordinary first-order logic, the type checker must understand the standard encodings used by the theory. In particular:

- In `if Int(a) then P(a)`, the consequent is checked with `Int(a)` available.
- In `forall a, (Int(a) -> P(a))`, `a` is known to be an integer while checking `P(a)`.
- In a guarded existential such as `exists m, (Int(m) and P(m))`, the occurrence of `m` in `P(m)` is checked under the integer guard.

The rules must be explicit and order-independent. In particular, a type fact may be promoted out of a disjunction only if every branch guarantees it; it is not safe to treat one disjunct's type fact as a fact about the whole disjunction. Negation and other connectives need equally precise rules. When the type checker cannot establish a required type under those rules, it rejects conservatively.

## 6. Why divisibility is a useful first case

The current surface syntax `a|b` is expanded immediately into

`exists m, (Int(m) and b = Times(a, m))`.

That expansion is ordinary first-order logic, which is desirable. But it erases the fact that the original expression was a typed divisibility construct: notably, `b` occurs on one side of an equality, and an untyped equality by itself does not establish that `b` was already known to be an integer. Checking only the `Times` function signature is therefore insufficient to enforce the owner's requirement for *both* operands.

**No typed surface construct may lose its typing obligations during desugaring.** The front end must preserve the obligations until the scoped checker has discharged them. There are two viable implementation techniques:
- retain a typed surface-formula node/annotation for each macro use, check it at the correct logical position, then lower it to the existing core formula; or
- carry equivalent source-mapped typing obligations through elaboration, including their positions inside connectives and quantifiers.

I recommend a small typed surface-formula representation if the existing parser APIs can be evolved without destabilizing them. It is cleaner than reconstructing a sugar construct from a formula's shape after it has been erased. This does not require a new kernel logic connective: the final proof kernel can continue to receive ordinary formulas.

For `a|b`, the obligation is that both operands satisfy `Int` at that occurrence. So:
- `Let a and b be integers` followed by `a|b`: accept.
- `Let a be any object` followed by `a|b`: type error for `a`.
- `a|b` when only `Int(a)` is in scope: type error for `b`.
- `forall a, (Int(a) -> a|b)`: the occurrence of `a` is well-typed in the consequent, but `b` must independently be known to be an integer.
- a type fact introduced in a subproof: use it there, but reject reliance on it after the subproof closes.

## 7. Where checking belongs

A parser-only check is not sufficient: parsing does not know which proof lines have been validated, and callers can construct core proof entries directly. A purely front-end check also risks reporting a later type error before the validator has reported an earlier invalid proof line.

The authoritative check should be integrated into the validator's top-to-bottom walk, using a dedicated type-checking component and a typing context whose scope is synchronized with validation. It should check each line's formula and preserved surface obligations before committing that line's formula/type facts. The parser/elaborator may perform early checks for better diagnostics, but early checks must be advisory or use the same context rules; they must not be the soundness boundary.

This follows the existing separation of responsibilities: `ProofContext` remains the elaboration-time lexical context, while the proof validator owns validation-time facts. Do not make the kernel depend on the mutable elaboration `ProofContext`.

Introduce a distinct validation category such as `CATEGORY_TYPE_ERROR`, with a diagnostic naming the offending term, the required type, and the missing fact. It should not be reported as an ordinary inference-rule mismatch.

## 8. Migration plan

1. **Specify and unit-test the type judgments** independently: type registry composition, conflicts, subtype closure, function argument checking, result-type propagation, and scope-sensitive facts.
2. **Add typing metadata without changing existing proof behavior.** Extend `TheoryEnvironment` and `ElaboratedEntries` with a default-empty type-system field; preserve compatibility for all existing theories until their signatures are registered.
3. **Integrate scoped checking into validation** and add tests for context lifetimes, guarded formulas, and direct-core API paths. Type failures must be attributed to the line using the expression.
4. **Register integer signatures** for `Plus`, `Times`, and `Neg`; encode the result-type/closure relationship only once. Add the integer declaration recipe so `Let a be an integer` is a real type declaration rather than descriptive metadata.
5. **Enforce divisibility's two operand obligations** before accepting the expanded core formula. Keep the existing existential definition and ordinary proof rules.
6. **Apply the same mechanism to other theory symbols incrementally.** Do not type every existing symbol merely to complete the redesign; each newly registered signature should be strict immediately, while unregistered legacy symbols retain existing behavior during migration.
7. Run the canonical suite and focused audits after every step. Do not soften oracle expectations or turn type errors into parser failures just to keep the corpus green.

## 9. Acceptance criteria

The initial implementation is complete only when tests demonstrate all of these:

- Integer operands are accepted; an unknown/non-integer operand is rejected with a type-specific error.
- `Nat` evidence is accepted as `Int` evidence through an explicit, validated subtype relationship.
- A theorem-derived `Int(a)` fact becomes available only after its proof validates.
- Assumptions and typed declarations work within scope; neither leaks from a closed subproof.
- Nested typed surface constructs and guarded quantified formulas are checked in their actual logical context.
- Divisibility checks both operands, not merely the argument to `Times`.
- The same invariant holds for hand-built core proofs wherever their core representation retains the relevant operation/signature obligations; there is no public entry point that bypasses checks for registered typed symbols.
- Existing untyped propositional and set-theoretic proofs retain their current behavior unless they use a newly registered typed symbol incorrectly.

## 10. Open decisions to resolve before implementation

1. Which exact logical patterns are recognized as type guards in version 1, especially conjunction and negation? The first version should define a sound conservative rule set instead of inferring types from arbitrary formulas.
2. How signatures and logical closure axioms share one source of truth, so the type checker cannot assume a result type the theory does not actually guarantee.
3. How a typed surface formula or its annotations travel through nested formula parsing without making every theory-specific parser invent its own side channel.

These questions should be resolved in design and tests before touching kernel validation code. The first implementation PR should be narrow and separately reviewable; the architecture should make it possible to add later types and signatures without adding more special cases to `ProofLogic.py`.
