# Phase 4 Audit: Lexical Bookkeeping Duplication

## Overview

This audit maps all lexical-environment tracking across the elaborator and kernel to identify what's redundant with ProofContext (Phase 2), what's genuinely kernel-only semantics, and what can be removed.

**Conclusion**: Two pieces of duplicated bookkeeping can be safely removed:

1. **`_ElaborationContext.declarations` (legacy `DeclarationScope`)** — Can be removed entirely from the elaborator
2. **`_ElaborationContext.formula_by_label`** — Can potentially be moved or simplified once confirmed labels aren't read during elaboration

Everything else serves distinct purposes or has architectural constraints that keep it necessary.

---

## Lexical Bookkeeping Map

### 1. DECLARATIONS

#### Layer: Elaborator (`_ElaborationContext`)
**What is tracked:**
- `self.declarations` — a `pl.DeclarationScope` (legacy kernel object)
- Seeded from `environment.declarations` at init
- Dual-written with `self.context` during `register_declaration()`
- Also has `declarations_here()` read at the end of elaboration for theory hooks

**What it's for:**
- Track declared symbols during elaboration
- Feed into `dm.relation_rule_set()` at the end (DiscreteMath needs declarations to build relation rules)
- Dual-write safety: keep both structures in lockstep during Phase 2 migration

**Layer: ProofContext (`self.context`)**
**What is tracked:**
- `_declarations` dict — identical semantic as `DeclarationScope`
- Seeded from `self.declarations.declarations_here()`
- Dual-written by `register_declaration()`
- Read during elaboration for all declaration lookups

**What it's for:**
- Authoritative lexical scope for declarations (Phase 2 goal)
- Support nested scopes with proper inheritance/isolation
- All elaboration queries now go through `self.context.lookup_declaration()`

#### Layer: Kernel (`ProofValidator`)
**What is tracked:**
- `DeclarationScope` created fresh for each validation, seeded with `initial_declarations`
- One per call to `validate()`
- Passed through `_validate_block()` and child'd for subproofs
- Used to check "has this symbol been declared?" during validation

**What it's for:**
- Kernel semantics: enforce declaration rules during proof checking
- NOT fed from elaboration's declarations — kernel gets declarations from elsewhere

**Redundancy Analysis:**
- ✅ `_ElaborationContext.declarations` is **redundant with `_ElaborationContext.context`** for normal lookups
  - All declaration references resolve through `self.context` now
  - Dual-write ensures both track the same state
  - Still needed: `declarations_here()` read for DiscreteMath hook at end of elaborate_proof
  - **Solution**: Keep the context, remove the dual-write, read `context.declarations_here()` or expose a method

- ✅ `ProofValidator.declarations` is **NOT redundant with `_ElaborationContext`**
  - It's the kernel's own independent copy, not connected to elaboration
  - It re-checks declarations during validation, independent of what elaboration saw
  - This is intentional: kernel proves it's sound without assuming elaboration was correct
  - **Keep it**: kernel owns its own lexical bookkeeping

---

### 2. LABELS

#### Layer: Elaborator (`_ElaborationContext`)
**What is tracked:**
- `self.origin_by_label` — maps label string → `CoreOrigin` (source location info)
- `self.formula_by_label` — maps label string → core formula/bundle result
- Both keyed by full dotted label string (e.g., "1", "2.1", "3.2.1")
- Populated during `elaborate_entry()`
- Read during elaboration by `try_elaborate_existence()` to resolve "Existence from L" citations

**What it's for:**
- Preserve source origins through elaboration so errors can be traced back
- Allow elaboration to look up what formula a label denotes
- Store the final elaborated form of each line for reference

**Layer: ProofContext (`self.context`)**
**What is tracked:**
- `_labels` dict — label → `LabelBinding` (value + metadata)
- `_assumption_labels` dict — for labeled assumptions specifically
- Both use scoped lookups, support nested scopes
- Dual-written by `elaborate_entry()` (every line registers via `bind_label` or `assume`)

**What it's for:**
- Authoritative lexical scope for label references during elaboration
- Support nested scopes (currently working correctly per Phase 2 notes)
- Prevent label shadowing

**Layer: Kernel (`ProofValidator`)
**What is tracked:**
- `LabelScope` created fresh for each validation
- Tracks label → formula only (stripped of origin info)
- Passed through `_validate_block()` and child'd for subproofs
- Labels registered as lines are validated

**What it's for:**
- Kernel semantics: answer "what does label L denote?" during rule checking
- Enforce label scoping and shadowing rules during validation
- NOT connected to elaboration's label tracking

**Redundancy Analysis:**
- ✅ `_ElaborationContext.formula_by_label` is **mostly redundant with `_ElaborationContext.context`**
  - Every label in `formula_by_label` is also in `self.context._labels` (or `_assumption_labels`)
  - Both are populated by the same `elaborate_entry()` calls
  - However: `formula_by_label` stores the *core formula*, `context` stores a `LabelBinding` wrapping it
  - Critical difference: `origin_by_label` is needed, and that lives alongside `formula_by_label`
  - **Solution**: Can refactor `LabelBinding` to always include the origin, but requires careful handling

- ✅ `_ElaborationContext.origin_by_label` is **NOT redundant** — it's essential
  - Carries source locations through to error reporting
  - Kernel's `LabelScope` never sees this info
  - Must be preserved

- ✅ `ProofValidator.labels` is **NOT redundant with elaboration**
  - It's kernel's own independent label tracking
  - Validates labels are used correctly during proof checking
  - Independent of elaboration's view
  - **Keep it**: kernel owns its own label bookkeeping

---

### 3. ASSUMPTIONS

#### Layer: Elaborator (`_ElaborationContext`)
**What is tracked:**
- Implicitly: formulas added by `assume` lines flow through `elaborate_entry()`
- No explicit elaborator-level assumption tracking
- Instead: written to `ProofContext` via `context.assume(formula, label=label)`
- Also written to `formula_by_label` for labeled assumptions

**Layer: ProofContext (`self.context`)**
**What is tracked:**
- `_assumptions` list — ordered list of all assumptions in this scope
- `_assumption_labels` dict — for label-based lookup of labeled assumptions
- Scoped with inheritance

**What it's for:**
- Track what assumptions are visible at each point in elaboration
- Allow "Existence from L" citations to work correctly (Phase 2 bug fix)
- Support `has_assumption()` checks

**Layer: Kernel (`ProofValidator`)**
**What is tracked:**
- Implicitly: assumptions are processed as part of `_validate_block()`
- Assumptions opening a subproof are checked for legality
- No explicit assumption dict (unlike labels)

**What it's for:**
- Kernel semantics: enforce that assumptions only open subproofs correctly
- Not used for later lookups

**Redundancy Analysis:**
- ✅ No redundancy: elaborator defers all assumption tracking to `ProofContext`
- Kernel doesn't need the full assumption history
- This is correct and clean

---

### 4. ARBITRARY/FRESH BINDINGS

#### Layer: Elaborator (`_ElaborationContext`)
**What is tracked:**
- Implicitly: `arbitrary` lines flow through `elaborate_entry()`
- No explicit elaborator-level arbitrary tracking
- Registered to `ProofContext` via `context.bind_arbitrary(name)`

**Layer: ProofContext (`self.context`)**
**What is tracked:**
- `_arbitrary` dict — fresh constant name → `ArbitraryBinding`
- Scoped with inheritance
- Used to prevent duplicate arbitrary declarations

**Layer: Kernel (`ProofValidator`)**
**What is tracked:**
- Implicitly: `arbitrary` entries are processed as part of `_validate_block()`
- No explicit arbitrary dict

**What it's for:**
- Track fresh constants during elaboration
- Prevent accidental re-use of a name

**Redundancy Analysis:**
- ✅ No redundancy: elaborator correctly defers all arbitrary tracking to `ProofContext`
- This is clean

---

### 5. SCOPE NESTING

#### Layer: Elaborator (`_ElaborationContext`)
**Mechanism:**
- `elaborate_subproof_body()` creates `parent_context.child()` and `parent_declarations.child()`
- Both are restored after subproof processing
- Dual-write approach: both structures get the child scope

**Layer: Kernel (`ProofValidator`)**
**Mechanism:**
- `_validate_block()` recurses with `labels.child()` and `declarations.child()`
- Both create new scopes
- Isolation is automatic (each child has its own `_local` dict)

**Redundancy Analysis:**
- ✅ No redundancy: separate purposes
  - Elaborator structures exist during proof processing
  - Kernel structures exist during proof validation
  - They never exist at the same time

---

## Summary Table

| What | Where | Redundancy | Action |
|------|-------|-----------|--------|
| Declaration tracking | `Elaborator.declarations` + `ProofContext._declarations` | **Redundant for lookups** | Remove elaborator's `DeclarationScope`; expose `context.declarations_here()` method |
| Declaration checking | `Kernel.DeclarationScope` | **Not redundant** | Keep (kernel's own semantics) |
| Label→Formula mapping | `Elaborator.formula_by_label` | **Redundant** | Move to `ProofContext.LabelBinding.value` |
| Label source origins | `Elaborator.origin_by_label` | **Not redundant** | Keep (essential for errors) |
| Label checking | `Kernel.LabelScope` | **Not redundant** | Keep (kernel's own semantics) |
| Assumptions | `ProofContext._assumptions` | **Not redundant** | Keep (only place tracked) |
| Arbitrary bindings | `ProofContext._arbitrary` | **Not redundant** | Keep (only place tracked) |
| Scope nesting | Both structures child'd identically | **Not redundant** | Keep (each layer needs it for its own purposes) |

---

## Removal Roadmap for Phase 4

### Stage 1: Expose `declarations_here()` on ProofContext
- Add method `ProofContext.declarations_here()` that returns list of declarations (mirrors DeclarationScope API)
- Refactor elaborate_proof to read from `context.declarations_here()` instead of `self.declarations.declarations_here()`
- Update all other `self.declarations.declarations_here()` calls to use `context`

### Stage 2: Stop dual-writing `self.declarations`
- Remove dual-write from `register_declaration()`
- Remove `self.declarations = pl.DeclarationScope(...)` from `_ElaborationContext.__init__()`
- Confirm all lookups already go through `self.context`
- Confirm DiscreteMath hook works with just `context.declarations_here()`

### Stage 3: Refactor label and origin tracking
- Consider storing origin info in `LabelBinding` instead of separate `origin_by_label` dict
- Or: leave them separate if complexity isn't worth the cleanup
- Keep `formula_by_label` as-is for now (it's a small dict, not blocking anything)

### Stage 4: Document and regression test
- Add test confirming ProofContext alone is sufficient for declaration/label resolution
- Verify DiscreteMath.relation_rule_set works with new declarations_here() path
- Run full test suite

---

## Risk Assessment

**Low Risk:**
- Removing `self.declarations` from elaborator (Stage 2)
- All its readers are already using `self.context`
- Only write point (`register_declaration`) is internal

**Medium Risk:**
- Moving origins to LabelBinding (Stage 3, if attempted)
- Must preserve all origin info through elaboration
- Could break error reporting if not done carefully

**No Risk:**
- Everything in the kernel (`ProofValidator`, `LabelScope`, `DeclarationScope`)
- These are independent and not redundant
- Removing them would break validation

---

## Next Steps

1. Implement Stage 1 (expose `declarations_here()` on ProofContext)
2. Implement Stage 2 (stop dual-writing and remove legacy `DeclarationScope` from elaborator)
3. Run full test suite to confirm no regressions
4. Decide whether Stage 3 (refactor origin tracking) is worth the effort or leave it as-is
