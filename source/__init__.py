"""Core SyLoPy source package."""

# Import the parser once and install its language-policy extensions.  The
# policy module is deliberately separate from the parser implementation so
# the parser no longer depends on a legacy compatibility module.
from . import ProofParser as ProofParser
from . import ProofParserPolicy as ProofParserPolicy
