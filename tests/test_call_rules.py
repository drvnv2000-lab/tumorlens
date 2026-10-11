"""Transition table for the measurement-driven call rules (review item 1A)."""

import numpy as np
import pytest

from tumorlens import rano, v1

# (spd series, enhancing flags, expected calls)
CASES = [
    # zero baseline (no measurable disease after surgery)
    ([0, 0], [False, False], ["Baseline", "CR"]),
    ([0, 0], [True, True], ["Baseline", "SD"]),          # residual, non-measurable
    ([0, 100], [True, True], ["Baseline", "PD"]),        # zero nadir, measurable lesion
    ([0, 0, 100], [False, False, True], ["Baseline", "CR", "PD"]),
    # measurable baseline
    ([400, 500], [True, True], ["Baseline", "PD"]),      # exactly +25%
    ([400, 499.9], [True, True], ["Baseline", "SD"]),
    ([400, 200], [True, True], ["Baseline", "PR"]),      # exactly -50%
    ([400, 200.1], [True, True], ["Baseline", "SD"]),
    ([400, 0], [True, True], ["Baseline", "PR"]),        # non-measurable residual, -100%
    ([400, 0], [True, False], ["Baseline", "CR"]),
    # nadir is the minimum of all earlier scans, not the previous scan
    ([400, 100, 124], [True] * 3, ["Baseline", "PR", "PR"]),
    ([400, 100, 125], [True] * 3, ["Baseline", "PR", "PD"]),
    ([400, 100, 300, 360], [True] * 4, ["Baseline", "PR", "PD", "PD"]),
    # non-measurable follow-up sets the nadir to 0 (study convention)
    ([400, 0, 120], [True, True, True], ["Baseline", "PR", "PD"]),
    # PD takes precedence over PR when both thresholds could apply (nadir far below baseline)
    ([400, 50, 190], [True] * 3, ["Baseline", "PR", "PD"]),
]


@pytest.mark.parametrize("spd, enh, expected", CASES)
def test_call_transitions(spd, enh, expected):
    assert rano.call_series(spd, enh) == expected


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        rano.call_series([400, 300], [True])


def test_sub_10mm_lesion_is_non_measurable():
    assert v1.spd_for_call(9.99, 30) == 0.0
    assert v1.spd_for_call(10.0, 10.0) == 100.0


def ball(shape, center, r, spacing=(1.0, 1.0, 1.0)):
    g = np.meshgrid(*[(np.arange(n) + 0.5) * s for n, s in zip(shape, spacing)], indexing="ij")
    return sum((a - c) ** 2 for a, c in zip(g, center)) <= r**2


def test_fragility_reruns_the_whole_pipeline_per_offset():
    """Flip offset from masks: measurement, measurability, nadir and call recomputed per offset."""
    shape = (80, 80, 80)
    radii = [8.0, 8.0, 8.8]  # just under the +25% SPD line at offset 0
    masks = [ball(shape, (40, 40, 40), r) for r in radii]
    res = [v1.measure_mask(m, (1.0, 1.0, 1.0)) for m in masks]
    spd = {o: [v1.spd_for_call(r["by_offset"][o]["d1"], r["by_offset"][o]["d2"]) for r in res]
           for o in v1.OFFSETS_MM}
    enh = {o: [r["by_offset"][o]["enhancing_voxels"] > 0 for r in res] for o in v1.OFFSETS_MM}
    assert rano.call_series(spd[0.0], enh[0.0])[2] == "SD"
    # shrinking every edge raises the relative change, so the SD call becomes PD at some offset
    margin = rano.flip_margin(spd, 2, enh)
    assert margin == 2.5
    flipped = [o for o in v1.OFFSETS_MM if rano.call_series(spd[o], enh[o])[2] != "SD"]
    assert min(abs(o) for o in flipped) == margin and all(o < 0 for o in flipped)


def test_erosion_can_remove_a_small_lesion_entirely():
    m = ball((30, 30, 30), (15, 15, 15), 1.6)
    res = v1.measure_mask(m, (1.0, 1.0, 1.0), offsets=(0.0, -2.0))
    assert res["by_offset"][0.0]["enhancing_voxels"] > 0
    assert res["by_offset"][-2.0]["enhancing_voxels"] == 0
