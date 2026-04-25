"""portal — cross-sibling coordination layer.

The portal reads each participating sibling's native
``Report`` / ``Alert`` types via a per-sibling adapter and
exposes them through a common ``PortalEntry`` shape so
that cross-sibling analyses (co-occurrence, domain
neighbourhood, escalation ladders) become possible without
any sibling having to give up its native types.

Policy: "Не слияние — совместимость" — *not merger,
compatibility*. The portal NEVER modifies a sibling. It
only reads. See ``docs/DOMAIN_ADAPTATIONS.md §8``.
"""

__version__ = "0.1.0"
