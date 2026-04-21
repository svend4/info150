from triage4.signatures.breathing_signature import BreathingSignatureExtractor
from triage4.signatures.bleeding_signature import BleedingSignatureExtractor
from triage4.signatures.perfusion_signature import PerfusionSignatureExtractor
from triage4.signatures.fractal_motion import FractalMotionAnalyzer


def test_breathing_extractor_stable_for_flat_signal():
    ext = BreathingSignatureExtractor()
    result = ext.extract([0.1, 0.1, 0.1, 0.1])
    assert result["chest_motion_fd"] == 0.0
    assert result["respiration_proxy"] == 0.0


def test_breathing_extractor_handles_short_signal():
    ext = BreathingSignatureExtractor()
    result = ext.extract([0.1])
    assert result["breathing_curve"] == [0.1]
    assert result["chest_motion_fd"] == 0.0


def test_bleeding_extractor_clamps_inputs():
    ext = BleedingSignatureExtractor()
    result = ext.extract(2.0, -1.0, 0.5)
    assert 0.0 <= result["bleeding_visual_score"] <= 1.0
    assert 0.35 <= result["confidence"] <= 1.0


def test_perfusion_extractor_detects_drop():
    ext = PerfusionSignatureExtractor()
    result = ext.extract([0.9, 0.6, 0.4, 0.2])
    assert result["perfusion_drop_score"] > 0.0


def test_fractal_motion_empty():
    ana = FractalMotionAnalyzer()
    assert ana.chest_motion_fd([]) == 0.0
    assert ana.chest_motion_fd([0.1]) == 0.0
