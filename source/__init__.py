"""Core SyLoPy source package."""

# Keep the public parser facade available as ``source.ProofParser`` and expose
# its language-policy module explicitly.  Language-policy extensions are kept
# separate from the parser implementation.
from . import ProofParser as ProofParser
from . import ProofParserPolicy as ProofParserPolicy

# The proof validator is layered after ProofLogic has been loaded by
# ProofParser.  This makes ProofContext the authoritative lexical environment
# without introducing an import cycle into the kernel modules themselves.
from .ContextProofValidator import ProofValidator as ContextProofValidator
from . import ProofLogic as _ProofLogic

_ProofLogic.ProofValidator = ContextProofValidator
