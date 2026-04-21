from triage4.signatures.fractal.box_counting import BoxCountingFD
from triage4.signatures.fractal.richardson import RichardsonDivider
from triage4.signatures.fractal_motion import FractalMotionAnalyzer


def _solid_square(n: int = 32) -> list[list[int]]:
    return [[1] * n for _ in range(n)]


def _diagonal(n: int = 32) -> list[list[int]]:
    mask = [[0] * n for _ in range(n)]
    for i in range(n):
        mask[i][i] = 1
    return mask


def test_box_counting_on_solid_square_is_near_2():
    fd = BoxCountingFD(box_sizes=(2, 4, 8, 16)).estimate(_solid_square(32))
    # A filled square tends to the topological dimension 2.0.
    assert 1.6 <= fd <= 2.0


def test_box_counting_on_diagonal_is_near_1():
    fd = BoxCountingFD(box_sizes=(2, 4, 8, 16)).estimate(_diagonal(32))
    # A straight line tends to dimension 1.0 (with discretization bias).
    assert 0.8 <= fd <= 1.3


def test_box_counting_on_empty_mask_is_zero():
    assert BoxCountingFD().estimate([]) == 0.0
    assert BoxCountingFD().estimate([[0, 0], [0, 0]]) == 0.0


def test_richardson_on_smooth_curve_near_1():
    # Linear ramp has low fractal dimension, close to 1.0.
    curve = [float(i) for i in range(64)]
    dim = RichardsonDivider().estimate_1d(curve)
    assert 1.0 <= dim <= 1.2


def test_richardson_on_flat_signal_is_one():
    # A horizontal line is mathematically 1-dimensional.
    dim = RichardsonDivider().estimate_1d([0.0] * 64)
    assert 1.0 <= dim <= 1.05


def test_richardson_on_short_signal_is_zero():
    assert RichardsonDivider().estimate_1d([0.0, 0.0]) == 0.0


def test_fractal_motion_normalizes_to_unit_interval():
    analyzer = FractalMotionAnalyzer()
    # Highly jagged signal.
    jagged = [0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9]
    v = analyzer.chest_motion_fd(jagged)
    assert 0.0 <= v <= 1.0
