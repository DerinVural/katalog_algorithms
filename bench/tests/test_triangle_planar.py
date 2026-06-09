"""Kabul testleri — Planar Triangle baseline (brief 03 §Kabul testleri)."""
from pathlib import Path

import numpy as np
import pytest

from bench.algorithms.liebe import LiebeAlgorithm
from bench.algorithms.triangle_planar import TrianglePlanarAlgorithm, TriangleConfig
from bench.core.metrics import db_size_bytes
from bench.core.scene import NoiseConfig, simulate_scene
from bench.runner import build, run_trial, write_csv

RESULTS = Path(__file__).resolve().parent.parent / "results"


@pytest.fixture(scope="module")
def tri_built(catalog):
    """Üçgen DB'yi modül başına bir kez kur (pahalı)."""
    algo = TrianglePlanarAlgorithm()
    db, db_bytes = build(algo, catalog)
    return algo, db, db_bytes


# 1) Gürültüsüz, zengin sahne: id_rate>=0.99, false_id yok
def test_triangle_noiseless(catalog, moderate_attitude, tri_built):
    algo, db, _ = tri_built
    rng = np.random.default_rng(1)
    recs = [run_trial(algo, db, catalog, moderate_attitude, rng=rng) for _ in range(8)]
    assert np.mean([r["id_rate"] for r in recs]) >= 0.99
    assert not any(r["false_id_flag"] for r in recs)


# 2) DB boyut kontrastı: triangle >> liebe (O(n·f²) vs O(n) ampirik kanıtı)
def test_triangle_db_much_larger_than_liebe(catalog, tri_built):
    _, _, tri_bytes = tri_built
    liebe_bytes = db_size_bytes(LiebeAlgorithm().build_database(catalog))
    ratio = tri_bytes / liebe_bytes
    assert ratio > 10, f"triangle/liebe DB oranı yalnız {ratio:.1f}x"


# 3) Gürültü grace: eğri results/'a
def test_triangle_noise_grace(catalog, moderate_attitude, tri_built):
    algo, db, _ = tri_built
    sigmas = [2, 5, 10, 20]
    curve = []
    for sig in sigmas:
        cfg = NoiseConfig(sigma_centroid_arcsec=sig)
        rng = np.random.default_rng(1)
        idr = np.mean([run_trial(algo, db, catalog, moderate_attitude, cfg, rng)["id_rate"]
                       for _ in range(10)])
        curve.append({"sigma_arcsec": sig, "id_rate": float(idr)})
    write_csv(curve, RESULTS / "triangle_planar_grace.csv")
    vals = [c["id_rate"] for c in curve]
    assert vals[0] >= 0.95                                   # düşük gürültüde yüksek
    assert all(vals[i] <= vals[i - 1] + 0.05 for i in range(1, len(vals)))  # ~monoton


# 4) Doğrulama adımı işliyor: confirm kapalı -> false_id belirgin artar (spike senaryosu)
def test_triangle_confirmation_helps(catalog, moderate_attitude, tri_built):
    _, db, _ = tri_built
    cfg = NoiseConfig(sigma_centroid_arcsec=8.0, n_spikes=5)
    algo_on = TrianglePlanarAlgorithm(TriangleConfig(require_confirm=True))
    algo_off = TrianglePlanarAlgorithm(TriangleConfig(require_confirm=False))

    def false_rate(algo):
        rng = np.random.default_rng(4)
        return np.mean([run_trial(algo, db, catalog, moderate_attitude, cfg, rng)["false_id_flag"]
                        for _ in range(30)])

    fr_on = false_rate(algo_on)
    fr_off = false_rate(algo_off)
    assert fr_off > fr_on + 0.3      # 4. yıldız doğrulaması spike yanlışlarını belirgin azaltır
    assert fr_on <= 0.2              # açıkken false_id nadir


# 5) Determinizm
def test_triangle_deterministic(catalog, moderate_attitude, tri_built):
    algo, db, _ = tri_built
    cfg = NoiseConfig(sigma_centroid_arcsec=5.0, n_spikes=3)

    def run():
        obs, _ = simulate_scene(catalog, moderate_attitude, cfg, rng=np.random.default_rng(7))
        return sorted((c.obs_id, c.hip_id) for c in algo.match(algo.extract_features(obs), db))

    assert run() == run()
