"""Proof validator implementation backed by :mod:`ProofContext`.

This module is a migration layer for the validator refactor.  It deliberately
reuses the existing rule implementation in ``ProofLogic`` while replacing its
separate label/declaration scopes with one lexical ``ProofContext``.

``seen`` remains separate: it is ordered proof history, not lexical scope.
"""

from __future__ import annotations

from typing import Optional, Tuple

from .ProofContext import DuplicateBindingError, ProofContext
from . import ProofLogic as pl


class _ContextAdapter:
    """Compatibility view of one ProofContext for the legacy validator helpers.

    The old rule helpers operate on small mapping/scope protocols.  Keeping
    those protocols here lets the semantic transition happen without copying
    the rule implementations into a second validator.
    """

    def __init__(self, context: ProofContext):
        self.context = context

    def child(self):
        return _ContextAdapter(self.context.child())

    def declare(self, declaration):
        self.context.declare(declaration)

    def lookup(self, name):
        return self.context.lookup_declaration(name)

    def __contains__(self, label):
        return self.context.lookup_label(label) is not None

    def __getitem__(self, label):
        return self.context.require_label(label).value

    def __setitem__(self, label, value):
        self.context.bind_label(label, value)

    def bind_label(self, label, value):
        return self.context.bind_label(label, value)


class ProofValidator(pl.ProofValidator):
    """Existing validator rules with one authoritative lexical context."""

    def validate(self, entries: list) -> Tuple[bool, Optional[pl.ValidationError], Optional[pl.SubproofRecord]]:
        seen = []
        context = ProofContext()
        adapter = _ContextAdapter(context)

        for declaration in self.initial_declarations:
            try:
                context.declare(declaration)
            except DuplicateBindingError:
                existing = context.lookup_declaration(declaration.name)
                return False, pl._mk_error(
                    None, None, 0, pl.CATEGORY_DECLARATION_CONFLICT,
                    f"symbol '{declaration.name}' is already declared as "
                    f"{existing.kind if existing else 'another symbol kind'}",
                ), None

        return self._validate_block_context(
            entries, None, seen, adapter, seen, is_subproof=False
        )

    def _validate_block_context(
        self,
        block_entries,
        block_label,
        seen,
        scope,
        outer_context,
        is_subproof=False,
    ):
        if not block_entries:
            detail = "subproof has no lines" if is_subproof else "proof has no lines"
            return False, pl._mk_error(
                None, block_label, None, pl.CATEGORY_EMPTY_SUBPROOF, detail
            ), None

        if is_subproof:
            opening_detail, opening_label = self._check_opens_with_assumption(block_entries[0])
            if opening_detail:
                return False, pl._mk_error(
                    opening_label, block_label, 0, pl.CATEGORY_BAD_OPENING, opening_detail
                ), None

        for sidx, raw_entry in enumerate(block_entries):
            entry = pl._classify_entry(raw_entry)
            if isinstance(entry, str):
                return False, pl._mk_error(
                    None, block_label, sidx, pl.CATEGORY_MALFORMED_ENTRY, entry
                ), None

            if entry.is_subproof_block:
                child = _ContextAdapter(scope.context.child())
                ok, err, sp_rec = self._validate_block_context(
                    entry.subproof_entries,
                    entry.label,
                    [],
                    child,
                    seen,
                    is_subproof=True,
                )
                if not ok:
                    return False, err, None
                seen.append(sp_rec)
                if entry.label:
                    scope.bind_label(entry.label, sp_rec)
                continue

            err = self._validate_line(
                entry, sidx, block_label, is_subproof, seen,
                scope, scope, outer_context
            )
            if err:
                return False, err, None

        if is_subproof:
            boundary = len(outer_context) if outer_context else 0
            return True, None, pl.SubproofRecord(
                seen[0], seen, outer_context_ref=outer_context,
                boundary_index=boundary,
            )

        return True, None, None

    def _validate_rule_below(
        self, phi, justification, nested_subproof, label, sidx,
        block_label, labels, declarations, seen,
    ):
        if nested_subproof is None:
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_MISSING_SUBPROOF,
                "justification requires an immediate subproof below, but none was found",
            )

        rule = justification[1]
        child = _ContextAdapter(labels.context.child())
        ok, err, sp_rec = self._validate_block_context(
            nested_subproof, label, [], child, seen, is_subproof=True
        )
        if not ok:
            return err

        if not self._rule_is_registered(rule):
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_UNRECOGNIZED_RULE,
                f"rule '{rule.name}' is not one of the rules this proof allows",
            )
        if not rule.applies([sp_rec], phi):
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_RULE_MISMATCH,
                f"'{rule.name}' does not justify {phi!r} from the subproof immediately below this line",
            )
        return None

    def _validate_rule_hybrid(
        self, phi, justification, nested_subproof, label, sidx,
        block_label, labels, declarations, seen,
    ):
        if len(justification) != 3:
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_MALFORMED_JUSTIFICATION,
                "malformed hybrid rule justification",
            )
        rule, indices = justification[1], justification[2]
        if nested_subproof is None or not isinstance(nested_subproof, list):
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_MISSING_SUBPROOF,
                "hybrid rule requires subproofs below the cited line",
            )

        if isinstance(rule, pl.NamedRulePlaceholder):
            resolved = next((r for r in self.rules if r.name == rule.name), None)
            if resolved is None:
                return pl._mk_error(
                    label, block_label, sidx, pl.CATEGORY_UNRECOGNIZED_RULE,
                    f"no rule named '{rule.name}' is registered for this proof (check that the relevant Type was combined in)",
                )
            rule = resolved

        if not self._rule_is_registered(rule):
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_UNRECOGNIZED_RULE,
                f"rule '{rule.name}' is not one of the rules this proof allows",
            )

        arity = getattr(rule, 'premise_arity', 0)
        expected_subproofs = arity - len(indices)
        if expected_subproofs <= 0 or len(nested_subproof) != expected_subproofs:
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_ARITY_MISMATCH,
                f"'{rule.name}' requires {expected_subproofs} subproof(s) after {len(indices)} explicit citation(s), "
                f"but {len(nested_subproof)} were provided",
            )

        missing = [i for i in indices if i not in labels]
        if missing:
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_BAD_REFERENCE,
                f"cites {missing}, which {'is' if len(missing) == 1 else 'are'} not defined or not in scope at this point in the proof",
            )

        available = []
        for index in indices:
            value = labels[index]
            if isinstance(value, list):
                available.extend(value)
            else:
                available.append(value)

        for subentries in nested_subproof:
            child = _ContextAdapter(labels.context.child())
            ok, err, sp_rec = self._validate_block_context(
                subentries, label, [], child, seen, is_subproof=True
            )
            if not ok:
                return err
            available.append(sp_rec)

        if len(available) < arity:
            return pl._mk_error(
                label, block_label, sidx, pl.CATEGORY_ARITY_MISMATCH,
                f"'{rule.name}' requires {arity} candidate premise(s), but the cited line(s) and subproofs provide only {len(available)}",
            )

        for candidate_indices in pl.itertools.combinations(range(len(available)), arity):
            candidates = [available[i] for i in candidate_indices]
            try:
                if rule.applies(candidates, phi):
                    return None
            except Exception as raised:
                return pl._mk_error(
                    label, block_label, sidx, pl.CATEGORY_RULE_RAISED,
                    f"'{rule.name}' raised an exception while checking this line: {raised}",
                )

        return pl._mk_error(
            label, block_label, sidx, pl.CATEGORY_RULE_MISMATCH,
            f"'{rule.name}' does not justify {phi!r} from the cited line(s) {indices} and attached subproofs",
        )
