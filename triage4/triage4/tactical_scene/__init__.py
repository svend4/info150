"""K3-3.1 Tactical Scene Layer.

Projects the casualty graph onto a tactical 2D scene: platforms, casualties,
hazard zones.
"""

from .map_projection import TacticalSceneBuilder

__all__ = ["TacticalSceneBuilder"]
