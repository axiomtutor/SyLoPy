"""Core SyLoPy source package."""

# Keep the public parser facade available as ``source.ProofParser`` and expose
# its language-policy module explicitly.  Language-policy extensions are kept
# separate from the parser implementation.
from . import ProofParser as ProofParser
from . import ProofParserPolicy as ProofParserPolicy
