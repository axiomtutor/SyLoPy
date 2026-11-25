"""Textual rewriting of mathematical symbols into ordinary surface syntax."""

import re
from typing import Mapping


_BOUNDED_QUANTIFIER_MEMBERSHIP = re.compile(
    r"([∀∃]\s*[A-Za-z_][A-Za-z0-9_]*)\s*∈"
)


def rewrite_formula_symbols(text: str, notation_table: Mapping[str, str]) -> str:
    """Rewrite notation registered by the active theory environment.

    Bounded quantifiers are handled before ordinary membership: the form
    with a quantifier immediately followed by membership must become
    "forall x in A", not "forall x is in A". Other symbols are replaced
    with their word-form reading, padded by spaces so adjacent tokens such
    as "x∈A" and "¬P(x)∧Q(x)" remain lexically separate.
    """
    if not isinstance(text, str):
        raise TypeError("formula text must be a string")

    rewritten = _BOUNDED_QUANTIFIER_MEMBERSHIP.sub(r"\1 in ", text)
    for symbol in sorted(notation_table, key=len, reverse=True):
        reading = notation_table[symbol]
        if not symbol or not reading:
            raise ValueError("notation symbols and readings must be nonempty")
        rewritten = rewritten.replace(symbol, f" {reading} ")
    return rewritten.strip()
