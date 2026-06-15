"""Kabul testleri — Brief 07b FINAL (Non-Dim × Pyramid araştırması)."""
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from bench.algorithms.ndsia import NDSIAAlgorithm, dihedral_angles
from bench.algorithms.nondim_pyramid import NonDimPyramidAlgorithm
from bench.algorithms.oracle import OracleAlgorithm
from bench.algorithms.twostage_ndsia import _estimate_focal
from bench.core.interfaces import CandidateMatch
from bench.core.scene import NoiseConfig, simulate_scene
from bench.core.sensor import SENSOR
from bench.runner import build, run_monte_carlo, run_trial
from bench.tests.conftest import find_attitude_in_range

RESULTS = Path(__file__).resolve().parent.parent / "results"


# A1 — İş 0 regresyon: oa=0 bit-bit (enabled False); oracle her bozulmada 1.0
def test_a1_is0_regression(catalog):
    assert not NoiseConfig().enabled
    assert NoiseConfig(oa_offset_error_frac=0.02).enabled
    q = find_attitude_in_range(catalog, 10, 16, 0)
    for cfg in [NoiseConfig(oa_offset_error_frac=0.02),
                NoiseConfig(focal_error_ppm=3000, oa_offset_error_frac=0.02)]:
        recs = run_monte_carlo(OracleAlgorithm(), catalog, q, cfg, n_trials=5, seed=1)
        assert np.mean([r["id_rate"] for r in recs]) == 1.0


# A2 — _estimate_focal: tam-doğru kimliklerle <50 ppm (çok-seed ortalama)
def test_a2_estimate_focal(catalog):
    q = find_attitude_in_range(catalog, 12, 18, 0)
    f0 = SENSOR.focal_length_px
    for ppm in [-2000, 0, 2000]:
        errs = []
        for s in range(10):
            obs, truth = simulate_scene(catalog, q,
                NoiseConfig(sigma_centroid_arcsec=2, focal_error_ppm=ppm),
                rng=np.random.default_rng(s))
            good = [CandidateMatch(o.obs_id, truth.true_matches[o.obs_id])
                    for o in obs if o.obs_id in truth.true_matches]
            est = (_estimate_focal(good, obs, catalog) / f0 - 1) * 1e6
            errs.append(abs(est - ppm))
        assert np.mean(errs) < 50, f"ppm={ppm} ort hata {np.mean(errs):.0f}"


# A3 — NDSIA dihedral: bağımsız küresel kosinüs kuralıyla birebir
def test_a3_dihedral_vs_cosine_law():
    rng = np.random.default_rng(0)
    pts = []
    for _ in range(3):
        ang = rng.uniform(0, 0.25, 4000); az = rng.uniform(0, 2 * np.pi, 4000)
        pts.append(np.stack([np.sin(ang) * np.cos(az),
                             np.sin(ang) * np.sin(az), np.cos(ang)], 1))
    U1, U2, U3 = pts
    a = np.arccos(np.clip(np.sum(U2 * U3, 1), -1, 1))   # köşe1 karşısı
    b = np.arccos(np.clip(np.sum(U1 * U3, 1), -1, 1))   # köşe2 karşısı
    c = np.arccos(np.clip(np.sum(U1 * U2, 1), -1, 1))   # köşe3 karşısı

    def vertex(opp, s1, s2):                            # küresel kosinüs kuralı
        return np.arccos(np.clip(
            (np.cos(opp) - np.cos(s1) * np.cos(s2)) / (np.sin(s1) * np.sin(s2)), -1, 1))
    BF = np.stack([vertex(a, b, c), vertex(b, a, c), vertex(c, a, b)], 1)
    TH = dihedral_angles(U1, U2, U3)
    assert np.max(np.abs(TH - BF)) * 180 * 3600 / np.pi < 0.01   # < 0.01 arcsec


# A3b — NDSIA nominal koşulda "never completes unsuccessfully" (yanlış tanıma 0)
def test_a3_ndsia_no_wrong_id(catalog):
    q = find_attitude_in_range(catalog, 12, 18, 0)
    algo = NDSIAAlgorithm(); db, _ = build(algo, catalog)
    rng = np.random.default_rng(1)
    recs = [run_trial(algo, db, catalog, q,
                      NoiseConfig(sigma_centroid_arcsec=5), rng) for _ in range(10)]
    assert sum(r["n_wrong"] for r in recs) == 0       # makalenin imzası
    assert not any(r["wrong_attitude"] for r in recs)


# A4 — Kol B: gürültüsüz id≥0.99, wa=0, determinizm
def test_a4_nondim_pyramid(catalog):
    q = find_attitude_in_range(catalog, 10, 16, 0)
    algo = NonDimPyramidAlgorithm(); db, _ = build(algo, catalog)
    rng = np.random.default_rng(1)
    recs = [run_trial(algo, db, catalog, q, rng=rng) for _ in range(6)]
    assert np.mean([r["id_rate"] for r in recs]) >= 0.99
    assert not any(r["wrong_attitude"] for r in recs)

    cfg = NoiseConfig(sigma_centroid_arcsec=5)

    def run():
        obs, _ = simulate_scene(catalog, q, cfg, rng=np.random.default_rng(7))
        return sorted((c.obs_id, c.hip_id) for c in algo.match(algo.extract_features(obs), db))
    assert run() == run()


# A4b — Kol B kalibrasyon değişmezliği: ppm boyunca düz (H1)
def test_a4_calibration_flat(catalog):
    q = find_attitude_in_range(catalog, 10, 16, 0)
    algo = NonDimPyramidAlgorithm(); db, _ = build(algo, catalog)
    for ppm in [0, 3000, -3000]:
        rng = np.random.default_rng(1)
        recs = [run_trial(algo, db, catalog, q,
                NoiseConfig(sigma_centroid_arcsec=5, focal_error_ppm=ppm), rng)
                for _ in range(6)]
        assert np.mean([r["id_rate"] for r in recs]) >= 0.95     # düz
        assert sum(r["n_wrong"] for r in recs) == 0
