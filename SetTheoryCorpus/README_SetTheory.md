This directory represents the set theory corpus, which acts like a reference for all proven set theory theorems.

The axioms and sequence of theorems and definitions come from Jech's Set Theory textbook.  The goal is to ultimately reproduce every theorem in that text.

Eventually we will extend beyond Jech's text to any other useful theorems.

# Structure

Each chapter of Jech's textbook corresponds to one file here, or to several when its parts have to come at different places in the dependency order (see Layout below).

I will first, in a comment, present the natural-language proof.  Below that I will produce the SyLoPy representation.

Any file which is checked for valid proofs, has its validity recorded at the end of this file.  Any file which is validated does not need to be checked any further, and its are promoted to the status of "proved theorems". Proved theorems can then be referenced in later proofs and chapters, and even outside the set theory corpus.

# Layout

The files are ordered by dependency.  A file may `Use` only the files before it, so reading them in this order never meets something that has not been defined yet.

1. `Chapter1_Axioms.txt`: the axioms of set theory.
2. `OrderTheory.txt`: partial and linear orderings, bounds and extrema, order-preserving maps.  These definitions open Chapter 2 of the text.  They are a file of their own because they need only the axioms, and the ordinals need them.
3. `Chapter2_Ordinals.txt`: the ordinals (so far only a stub).  Uses `OrderTheory.txt`.

A `Use` line names either a theory of the checker (`Use set theory.`) or an earlier file of this directory, by its file name without `.txt` (`Use OrderTheory.`).  The file `OrderTheory.txt` is the general theory of partial orders.  It is not the checker's `order theory` module, which is the order on the integers.

A new file goes where its dependencies put it, and the list above is kept in that order.

# Conventions

- A function is a set of ordered pairs, and a relation on a set P is a subset of the Cartesian product of P with itself, with `x < y` as the notation for "the pair (x, y) is in <".  There is no separate notion of function outside the theory.
- An operation such as the identity function on a set X is a definition, which shows that the thing exists, names it, and adds no axiom.  The existence proof is written in the corpus, not in Python code.
- A term that makes sense only under a condition, such as `f(x)` for an `x` in the domain of `f`, `sup(X)` for a set that has a supremum, or `max(X)` for a set that has a greatest element, always names something: the unique thing with the stated property when there is exactly one such thing, and the empty set otherwise.  A theorem about such a term states the condition, as on paper.  The "This is denoted" lines of `OrderTheory.txt` are read this way.

These are decisions recorded in `todos.txt` under "Owner decisions".

# Proved Theorems

One heading per file, in the order of the Layout.

## Chapter1_Axioms.txt

## OrderTheory.txt

## Chapter2_Ordinals.txt

## Chapter 3. 

## Chapter 4.