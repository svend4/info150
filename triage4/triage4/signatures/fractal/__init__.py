"""Fractal descriptors (vendored-in from meta2, adapted for triage4).

The upstream `meta2` project implements a broader `FractalSignature` with
box-counting, Richardson divider, IFS, CSS and chain-code descriptors for
torn-document edges. For triage4 we need only the subset that makes sense
on casualty-oriented signals:

- `box_counting.BoxCountingFD` — fractal dimension of a binary mask / 2D
  pattern. Used for wound-boundary complexity and thermal-anomaly texture.
- `richardson.RichardsonDivider` — coastline-style dimension for a 1D
  time series (chest-motion curve, skin-color curve).

See `third_party/META2_ATTRIBUTION.md` for provenance.
"""

from .box_counting import BoxCountingFD
from .richardson import RichardsonDivider

__all__ = ["BoxCountingFD", "RichardsonDivider"]
