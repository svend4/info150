"""Panorama slicing helper — split frame into N vertical zones."""

from __future__ import annotations

import numpy as np
import pytest

from triage4_coast.perception import slice_panorama


class TestSlicePanorama:
    def test_single_zone_returns_input(self) -> None:
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        slices = slice_panorama(frame, 1)
        assert len(slices) == 1
        assert slices[0].shape == frame.shape

    def test_four_zones_equal_width(self) -> None:
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        slices = slice_panorama(frame, 4)
        assert len(slices) == 4
        for sl in slices:
            assert sl.shape == (48, 16, 3)

    def test_remainder_goes_to_last_slice(self) -> None:
        frame = np.zeros((48, 67, 3), dtype=np.uint8)
        slices = slice_panorama(frame, 4)
        assert slices[0].shape[1] == 16
        assert slices[1].shape[1] == 16
        assert slices[2].shape[1] == 16
        assert slices[3].shape[1] == 67 - 3 * 16

    def test_invalid_n_zones(self) -> None:
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="n_zones"):
            slice_panorama(frame, 0)
        with pytest.raises(ValueError, match="n_zones"):
            slice_panorama(frame, -1)

    def test_n_zones_larger_than_width_rejected(self) -> None:
        frame = np.zeros((10, 5, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="smaller than"):
            slice_panorama(frame, 8)

    def test_invalid_frame_shape(self) -> None:
        with pytest.raises(ValueError, match="\\(H, W, 3\\)"):
            slice_panorama(np.zeros((48, 64), dtype=np.uint8), 2)

    def test_non_array_rejected(self) -> None:
        with pytest.raises(TypeError, match="numpy"):
            slice_panorama([[1, 2, 3]], 2)  # type: ignore[arg-type]

    def test_slices_are_views(self) -> None:
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        slices = slice_panorama(frame, 4)
        slices[2][:] = 42
        assert frame[0, 32, 0] == 42
