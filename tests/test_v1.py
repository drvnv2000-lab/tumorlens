import numpy as np
import pytest

from tumorlens import rano, v1


def ball(shape, center, r, spacing):
    grids = np.meshgrid(*[(np.arange(n) + 0.5) * s for n, s in zip(shape, spacing)], indexing="ij")
    return sum((g - c) ** 2 for g, c in zip(grids, center)) <= r**2


@pytest.mark.parametrize(
    "text, spd, n",
    [
        ("Target L.: 1, 24mm x 43mm", 24 * 43, 1),
        ("New target L.: 22mm x 40 mm", 22 * 40, 1),
        ("Two new target L.: 15mm x 29m and 16mm x 30mm", 15 * 29 + 16 * 30, 2),
        ("T2-Progr., target L. 36.5mm x 18.5mm", 36.5 * 18.5, 1),
        ("Target L.: 2, 33mm x 41mm, 30mm x 27mm, Non-Target L.: 2", 33 * 41 + 30 * 27, 2),
        ("Target L.: 14mm x 23mm (static), new 16mm x 26mm", 14 * 23 + 16 * 26, 2),
        ("no measurable lesion", 0.0, 0),
    ],
)
def test_parse_expert_spd(text, spd, n):
    assert v1.parse_expert_spd(text) == (pytest.approx(spd), n)


def test_measurement_axis_follows_acquisition():
    assert rano.measurement_axis((1.0, 1.0, 1.0)) == 2
    assert rano.measurement_axis((0.4, 0.4, 6.0)) == 2
    assert rano.measurement_axis((0.9, 6.0, 0.9)) == 1  # coronal stack
    assert rano.measurement_axis((5.0, 0.5, 0.5)) == 0  # sagittal stack


def test_largest_lesion_in_coronal_plane():
    spacing = (1.0, 5.0, 1.0)
    m = ball((80, 12, 80), (40, 30, 40), 15, spacing)
    les = rano.largest_lesion(m, spacing, axis=1)
    assert les.d1_mm == pytest.approx(30, abs=2)
    assert les.d2_mm == pytest.approx(30, abs=2)


def test_offset_3d_grows_and_shrinks_diameter():
    spacing = (1.0, 1.0, 1.0)
    m = ball((60, 60, 60), (30, 30, 30), 10, spacing)
    res = v1.measure_mask(m, spacing, offsets=(-2.0, 0.0, 2.0))
    d = {o: r["d1"] for o, r in res["by_offset"].items()}
    assert d[2.0] - d[0.0] == pytest.approx(4, abs=1)
    assert d[0.0] - d[-2.0] == pytest.approx(4, abs=1)
    assert res["by_offset"][0.0]["volume_mm3"] == pytest.approx(4 / 3 * np.pi * 1000, rel=0.05)


def test_measure_mask_empty():
    res = v1.measure_mask(np.zeros((10, 10, 10), bool), (1, 1, 1), offsets=(0.0, 1.0))
    assert res["by_offset"][1.0]["enhancing_voxels"] == 0


def test_spd_for_call_drops_non_measurable():
    assert v1.spd_for_call(12, 10) == 120
    assert v1.spd_for_call(30, 9.9) == 0


def test_calls_from_zero_nadir_and_cr_needs_no_enhancement():
    assert rano.call_series([0, 0, 120], [True, True, True]) == ["Baseline", "SD", "PD"]
    assert rano.call_series([400, 0], [True, False]) == ["Baseline", "CR"]
    assert rano.call_series([400, 0], [True, True]) == ["Baseline", "PR"]  # -100% of baseline


def test_build_series():
    rows = [((0, 1), "week-000-1", "Pre-Op"), ((0, 2), "week-000-2", "Post-Op"),
            ((10, 0), "week-010", "SD"), ((20, 0), "week-020", "PD"),
            ((22, 0), "week-022", "Post-Op"), ((30, 0), "week-030", "PD"),
            ((40, 0), "week-040", "Post-Op/PD"), ((50, 0), "week-050", "SD")]
    s = v1.build_series(rows)
    assert s == [[("week-000-2", "Post-Op"), ("week-010", "SD"), ("week-020", "PD")],
                 [("week-022", "Post-Op"), ("week-030", "PD")]]


def test_week_key_orders_same_week_scans():
    assert sorted(["week-044", "week-000-2", "week-000-1"], key=v1.week_key) == [
        "week-000-1", "week-000-2", "week-044"]


def test_direction_pairs():
    assert v1.direction_pairs_nadir([100, 80, 120], [50, 60, 70]) == [False, True]
    assert v1.direction_pairs_consecutive([100, 80, 120], [50, 40, 30]) == [True, False]
    assert v1.direction_pairs_consecutive([100, 100], [5, 5]) == [True]


def test_bootstrap_ci_is_reproducible_and_brackets_point():
    clusters = {f"p{i}": [float(i % 3)] * (1 + i % 2) for i in range(30)}
    a = v1.bootstrap_ci(clusters, lambda xs: float(np.mean(xs)), n=500)
    b = v1.bootstrap_ci(clusters, lambda xs: float(np.mean(xs)), n=500)
    assert a == b
    assert a[1] <= a[0] <= a[2]


def test_auroc_basic_and_ties():
    assert v1.auroc([(1, True), (0, False)]) == 1.0
    assert v1.auroc([(0, True), (1, False)]) == 0.0
    assert v1.auroc([(1, True), (1, False)]) == 0.5
    assert np.isnan(v1.auroc([(1, True), (2, True)]))


def test_bootstrap_counts_undefined_resamples():
    clusters = {"a": [(1.0, True)], "b": [(0.0, False)]}
    r = v1.bootstrap(clusters, lambda xs: v1.auroc(xs), n=200)
    assert r["estimate"] == 1.0
    assert 0 < r["undefined_resamples"] < 200  # resamples drawing one patient twice have one class


def test_bootstrap_keeps_duplicated_patients():
    # one patient with 9 zeros, one with a single 1: resampling the second twice must count twice
    clusters = {"a": [0.0] * 9, "b": [1.0]}
    r = v1.bootstrap(clusters, lambda xs: float(np.mean(xs)), n=2000)
    assert r["ci95"][1] == pytest.approx(1.0)  # both draws = patient b


@pytest.mark.parametrize("text, nt, nm", [
    ("Non-Target L.: 11mm x 22mm", True, False),
    ("T2-Progr., Target L. 12mm x 16mm, target L. to non-measurable, Non-Target L.: 3", False, True),
    ("T2-Progr., Target L.:  11mm x 17mm, Non-Target L., target lesion to non-measurable L.", False, True),
    ("Target L.: 15.5mm x 13mm, non-measurable L. to target L., 25% increase in SPD", False, False),
    ("Target L.: 20mm x 23mm, non-target L.: 1", False, False),
])
def test_expert_row_flags(text, nt, nm):
    assert v1.expert_row_flags(text) == {"non_target_only": nt, "target_became_non_measurable": nm}
