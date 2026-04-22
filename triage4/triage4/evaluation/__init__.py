"""DARPA-aligned gate evaluators for triage4.

Each module scores a specific capability required by the DARPA Triage
Challenge Event 3:

- ``gate1_find_locate`` — detect and localise casualties;
- ``gate2_rapid_triage`` — assign the correct priority class;
- ``gate3_trauma``     — identify trauma hypotheses per casualty;
- ``gate4_vitals``     — estimate HR / RR within tolerance;
- ``hmt_lane``         — evaluate human-machine handoff quality.
"""

from .gate1_find_locate import Gate1Report, evaluate_gate1
from .gate2_rapid_triage import ClassMetrics, Gate2Report, evaluate_gate2
from .gate3_trauma import Gate3Report, LabelMetrics, evaluate_gate3
from .gate4_vitals import Gate4Report, VitalMetrics, evaluate_gate4
from .hmt_lane import HMTEvent, HMTReport, evaluate_hmt_lane
from .counterfactual import (
    CounterfactualCase,
    CounterfactualReport,
    evaluate_counterfactuals,
    score_counterfactuals,
)

__all__ = [
    "ClassMetrics",
    "CounterfactualCase",
    "CounterfactualReport",
    "Gate1Report",
    "Gate2Report",
    "Gate3Report",
    "Gate4Report",
    "HMTEvent",
    "HMTReport",
    "LabelMetrics",
    "VitalMetrics",
    "evaluate_counterfactuals",
    "evaluate_gate1",
    "evaluate_gate2",
    "evaluate_gate3",
    "evaluate_gate4",
    "evaluate_hmt_lane",
    "score_counterfactuals",
]
