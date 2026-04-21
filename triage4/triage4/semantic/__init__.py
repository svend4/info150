"""K3-2.1 Evidence Semantics Layer.

Turns numeric signatures into named evidence tokens that downstream
reasoning can compose into hypotheses.
"""

from .evidence_tokens import EvidenceToken, build_evidence_tokens

__all__ = ["EvidenceToken", "build_evidence_tokens"]
