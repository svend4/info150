import numpy as np
import pytest

from triage4.signatures import ThermalSignatureExtractor


def test_thermal_empty_patch_returns_zeros():
    extractor = ThermalSignatureExtractor()
    result = extractor.extract([])
    assert result["thermal_asymmetry_score"] == 0.0
    assert result["gradient_magnitude"] == 0.0


def test_thermal_uniform_patch_has_no_hotspots():
    extractor = ThermalSignatureExtractor()
    patch = np.full((8, 8), 30.0)
    result = extractor.extract(patch)
    assert result["hotspot_fraction"] == 0.0
    assert result["gradient_magnitude"] == 0.0


def test_thermal_hotspot_detected():
    extractor = ThermalSignatureExtractor(hotspot_z=1.5)
    patch = np.full((10, 10), 20.0)
    patch[4:6, 4:6] = 40.0  # 4 hot pixels out of 100
    result = extractor.extract(patch)
    assert result["hotspot_fraction"] > 0.0
    assert result["gradient_magnitude"] > 0.0
    assert result["thermal_asymmetry_score"] > 0.0


def test_thermal_quality_scales_with_dynamic_range():
    extractor = ThermalSignatureExtractor()
    low_range = extractor.extract(np.random.default_rng(0).normal(0.0, 0.01, (6, 6)))
    high_range = extractor.extract(np.random.default_rng(0).normal(0.0, 0.3, (6, 6)))
    assert high_range["quality_score"] >= low_range["quality_score"]


def test_thermal_rejects_non_positive_z():
    with pytest.raises(ValueError):
        ThermalSignatureExtractor(hotspot_z=0.0)


def test_thermal_all_in_unit_range():
    extractor = ThermalSignatureExtractor()
    patch = np.random.default_rng(42).normal(25.0, 3.0, (12, 12))
    result = extractor.extract(patch)
    assert 0.0 <= result["thermal_asymmetry_score"] <= 1.0
    assert 0.0 <= result["hotspot_fraction"] <= 1.0
    assert 0.0 <= result["quality_score"] <= 1.0
