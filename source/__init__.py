"""Core SyLoPy source package.

Parser extension assembly is centralized here so importing the parser facade
always produces one fully configured surface-language parser.
"""

from . import ProofParser as ProofParser
from . import ProofParserPolicy as ProofParserPolicy

# Keep all parser mutations in one named, idempotent assembly step rather than
# letting ProofParserPolicy patch the parser as an import side effect.
ProofParserPolicy.install_parser_extensions(ProofParser)
