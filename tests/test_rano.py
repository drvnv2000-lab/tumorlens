import numpy as np
import pytest

from tumorlens import rano


def ellipse(shape, center, a, b, theta=0.0, spacing=1.0):
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    x = (xx + 0.5) * spacing - center[0]
    y = (yy + 0.5) * spacing - center[1]
    c, s = np.cos(theta), np.sin(theta)
    u, v = c * x + s * y, -s * x + c * y
    return (u / a) ** 2 + (v / b) ** 2 <= 1.0


@pytest.mark.parametrize("theta", [0.0, 0.5, 1.2])
def test_ellipse_diameters_recovered(theta):
    m = ellipse((120, 120), (60, 60), 15, 10, theta)  # 30 x 20 mm
    d1, d2 = rano.bidimensional(m, (1.0, 1.0))
    assert d1 == pytest.approx(30, abs=2.0)  # pixel-corner hull: bias at most one voxel
    assert d2 == pytest.approx(20, abs=2.0)


def test_anisotropic_spacing():
    m = ellipse((200, 100), (25, 50), 15, 10, spacing=0.5)
    d1, d2 = rano.bidimensional(m, (0.5, 0.5))
    assert d1 == pytest.approx(30, abs=1.0)
    assert d2 == pytest.approx(20, abs=1.0)


def test_empty_mask():
    assert rano.bidimensional(np.zeros((10, 10), bool), (1, 1)) == (0.0, 0.0)


def test_measurable_rule():
    assert rano.Lesion(12, 10, 0).measurable
    assert not rano.Lesion(30, 9.9, 0).measurable


def test_largest_lesion_picks_biggest_slice():
    vol = np.zeros((60, 60, 9), bool)
    vol[:, :, 4] = ellipse((60, 60), (30, 30), 12, 8).T
    vol[:, :, 2] = ellipse((60, 60), (30, 30), 5, 4).T
    les = rano.largest_lesion(vol, (1, 1, 1))
    assert les.slice_index == 4
    assert les.d1_mm == pytest.approx(24, abs=1.5)


def test_offset_changes_size_by_offset():
    m = ellipse((120, 120), (60, 60), 15, 10)
    d1, _ = rano.bidimensional(m, (1, 1))
    g1, _ = rano.bidimensional(rano.offset_mask(m, (1, 1), 2.0), (1, 1))
    s1, _ = rano.bidimensional(rano.offset_mask(m, (1, 1), -2.0), (1, 1))
    assert g1 == pytest.approx(d1 + 4, abs=1.0)
    assert s1 == pytest.approx(d1 - 4, abs=1.0)


def test_calls_use_nadir_not_baseline_or_previous():
    # baseline 400, nadir 250: 309 is +23.6% (SD), 313 is +25.2% (PD) although both are far below baseline
    assert rano.call_series([400, 350, 250, 309, 313]) == ["Baseline", "SD", "SD", "SD", "PD"]


def test_partial_response_threshold():
    assert rano.call_series([400, 200])[1] == "PR"
    assert rano.call_series([400, 201])[1] == "SD"


def test_complete_response():
    assert rano.call_series([400, 0])[1] == "CR"


def test_flip_margin():
    series = {-1.0: [350, 250, 190], 0.0: [400, 300, 240], 1.0: [450, 350, 295]}
    # at offset 0 the last call is SD (240 < 1.25*300? nadir=300 -> 375), check no flips first
    assert rano.flip_margin(series, 2) is None
    series[1.0] = [450, 300, 400]  # grows the last scan so it crosses +25% of the nadir
    assert rano.flip_margin(series, 2) == 1.0


def test_centre_convention_is_smaller_than_corner():
    m = ellipse((120, 120), (60, 60), 15, 10)  # 30 x 20 mm
    c1, c2 = rano.bidimensional(m, (1.0, 1.0), "corner")
    k1, k2 = rano.bidimensional(m, (1.0, 1.0), "centre")
    assert k1 < c1 and k2 < c2
    assert k1 == pytest.approx(30, abs=1.0) and k2 == pytest.approx(20, abs=1.0)
    assert c1 - k1 == pytest.approx(1.0, abs=0.5)
