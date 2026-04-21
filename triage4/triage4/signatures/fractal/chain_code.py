"""Freeman chain code.

Adapted from svend4/meta2 — ``puzzle_reconstruction/algorithms/fractal/css.py``
(the ``freeman_chain_code`` function originally sits inside the CSS module).
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Used as a fast shape hash for wound-boundary / silhouette deduplication.
"""

from __future__ import annotations

import numpy as np


_DIR_TABLE: dict[tuple[int, int], int] = {
    (1, 0): 0,
    (1, -1): 1,
    (0, -1): 2,
    (-1, -1): 3,
    (-1, 0): 4,
    (-1, 1): 5,
    (0, 1): 6,
    (1, 1): 7,
}


def freeman_chain_code(contour: np.ndarray) -> str:
    """8-directional Freeman chain code.

    Directions: 0=E, 1=NE, 2=N, 3=NW, 4=W, 5=SW, 6=S, 7=SE.
    """
    if len(contour) < 2:
        return ""
    pts = np.round(np.asarray(contour)).astype(int)
    code: list[str] = []
    for i in range(len(pts) - 1):
        dx = int(pts[i + 1, 0] - pts[i, 0])
        dy = int(pts[i + 1, 1] - pts[i, 1])
        dx = max(-1, min(1, dx))
        dy = max(-1, min(1, dy))
        d = _DIR_TABLE.get((dx, dy))
        if d is not None:
            code.append(str(d))
    return "".join(code)
