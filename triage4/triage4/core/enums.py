from enum import Enum


class PlatformType(str, Enum):
    UAV = "uav"
    UGV = "ugv"
    QUADRUPED = "quadruped"


class TriagePriority(str, Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    MINIMAL = "minimal"
    EXPECTANT = "expectant"
    UNKNOWN = "unknown"


class CasualtyStatus(str, Enum):
    DETECTED = "detected"
    TRACKED = "tracked"
    ASSESSED = "assessed"
    HANDED_OFF = "handed_off"
    LOST = "lost"


class HypothesisType(str, Enum):
    HEMORRHAGE = "hemorrhage"
    RESPIRATORY_DISTRESS = "respiratory_distress"
    SHOCK_RISK = "shock_risk"
    AIRWAY_RISK = "airway_risk"
    UNRESPONSIVE = "unresponsive"
