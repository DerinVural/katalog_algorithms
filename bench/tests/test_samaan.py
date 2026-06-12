"""Kabul testleri — Samaan non-dimensional (brief 07), Faz 3 açılışı."""
from pathlib import Path

import numpy as np
import pytest

from bench.algorithms.liebe import LiebeAlgorithm
from bench.algorithms.samaan_nondim import SamaanAlgorithm, SamaanConfig
from bench.algorithms.sla_kvector import SLAAlgorithm
from bench.algorithms.triangle_planar import TrianglePlanarAlgorithm
from bench.core.metrics import db_size_bytes
from bench.core.scene import NoiseConfig, simulate_scene
from bench.runner import build, run_trial, write_csv
from bench.tests.conftest import find_attitude_in_range

RESULTS = Path(__file__).resolve().parent.parent / "results"


@pytest.fixture(scope="module")
def samaan_built(catalog):
    algo = SamaanAlgorithm()
    db, db_bytes = build(algo, catalog)
    return algo, db, db_bytes


# T1 — T-calib (tanımlayıcı test): Samaan ppm taramasında düz, Liebe/SLA bozulur
def test_t1_calibration_sweep(catalog, samaan_built):
    sam, sdb, _ = samaan_built
    q = find_attitude_in_range(catalog, 10, 16, 0)
    others = {"liebe": LiebeAlgorithm(), "sla_kvector": SLAAlgorithm()}
    dbs = {name: build(a, catalog)[0] for name, a in others.items()}

    rows = []
    curves = {"samaan_nondim": {}, "liebe": {}, "sla_kvector": {}}
    for ppm in [-3000, -2000, -1000, 0, 1000, 2000, 3000]:
        cfg = NoiseConfig(sigma_centroid_arcsec=5, focal_error_ppm=ppm)
        for name, algo, db in [("samaan_nondim", sam, sdb),
                               ("liebe", others["liebe"], dbs["liebe"]),
                               ("sla_kvector", others["sla_kvector"], dbs["sla_kvector"])]:
            rng = np.random.default_rng(1)
            recs = [run_trial(algo, db, catalog, q, cfg, rng) for _ in range(8)]
            idr = float(np.mean([r["id_rate"] for r in recs]))
            rows.append({"algo": name, "focal_error_ppm": ppm, "id_rate": idr,
                         "wrong_attitude_rate": float(np.mean([r["wrong_attitude"] for r in recs])),
                         "no_solution_rate": float(np.mean([r["no_solution"] for r in recs]))})
            curves[name][ppm] = idr
    write_csv(rows, RESULTS / "calib_sweep.csv")

    # Samaan DÜZ kalmalı: tüm ppm'lerde ppm=0 değerine yakın ve yüksek
    assert all(v >= 0.95 for v in curves["samaan_nondim"].values()), curves["samaan_nondim"]
    # Liebe ve SLA ±3000'de belirgin bozulmalı (kıyas eğrisi anlamlı)
    assert curves["liebe"][3000] < curves["liebe"][0] - 0.2
    assert curves["sla_kvector"][3000] < curves["sla_kvector"][0] - 0.2

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 5))
        ppms = sorted(curves["samaan_nondim"])
        for name, c in curves.items():
            ax.plot(ppms, [c[p] for p in ppms], "o-", label=name)
        ax.set(xlabel="focal_error_ppm", ylabel="id_rate (σ=5″)",
               title="Kalibrasyon robustluğu: Samaan non-dim vs Liebe vs SLA")
        ax.grid(alpha=.3); ax.legend()
        fig.savefig(RESULTS / "calib_sweep.png", dpi=130)
        plt.close(fig)
    except Exception:
        pass


# T2 — gürültüsüz: id_rate >= 0.99, wrong_attitude = 0 (eksen-ayrık kapı)
def test_t2_noiseless(catalog, samaan_built):
    algo, db, _ = samaan_built
    q = find_attitude_in_range(catalog, 10, 16, 0)
    rng = np.random.default_rng(1)
    recs = [run_trial(algo, db, catalog, q, rng=rng) for _ in range(8)]
    assert np.mean([r["id_rate"] for r in recs]) >= 0.99
    assert not any(r["wrong_attitude"] for r in recs)


# T3 — gürültü grace
def test_t3_noise_grace(catalog, samaan_built):
    algo, db, _ = samaan_built
    q = find_attitude_in_range(catalog, 10, 16, 0)
    curve = []
    for sig in [2, 5, 10]:
        rng = np.random.default_rng(1)
        recs = [run_trial(algo, db, catalog, q,
                          NoiseConfig(sigma_centroid_arcsec=sig), rng) for _ in range(10)]
        curve.append({"sigma_arcsec": sig,
                      "id_rate": float(np.mean([r["id_rate"] for r in recs]))})
    write_csv(curve, RESULTS / "samaan_nondim_grace.csv")
    assert curve[0]["id_rate"] >= 0.95
    assert curve[1]["id_rate"] >= 0.90


# T4 — min_match_stars ablation: 5 -> 3 düşürülünce wrong_attitude artmalı
def test_t4_min_match_ablation(catalog):
    q = find_attitude_in_range(catalog, 10, 16, 0)
    cfg_noise = NoiseConfig(sigma_centroid_arcsec=10, n_spikes=5)

    def wa_rate(min_stars):
        algo = SamaanAlgorithm(SamaanConfig(min_match_stars=min_stars))
        db, _ = build(algo, catalog)
        rng = np.random.default_rng(4)
        recs = [run_trial(algo, db, catalog, q, cfg_noise, rng) for _ in range(25)]
        return (float(np.mean([r["wrong_attitude"] for r in recs])),
                float(np.mean([r["no_solution"] for r in recs])))

    wa5, _ = wa_rate(5)
    wa3, _ = wa_rate(3)
    assert wa3 >= wa5            # ≥5 kuralı gevşeyince tehlike artar (veya eşit)
    assert wa5 <= 0.1            # ≥5 ile nadir


# T5 — determinizm + DB boyutu (Triangle mertebesi beklenir)
def test_t5_deterministic_and_db(catalog, samaan_built):
    algo, db, db_bytes = samaan_built
    tri_bytes = db_size_bytes(TrianglePlanarAlgorithm().build_database(catalog))
    # Triangle ile aynı mertebe (üçlü kataloğu sınıfı): 3x bandında
    assert db_bytes > tri_bytes / 3 and db_bytes < tri_bytes * 3
    assert db.n_records == 1024337          # paylaşılan covisible_triples

    q = find_attitude_in_range(catalog, 10, 16, 0)
    cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=3)

    def run():
        obs, _ = simulate_scene(catalog, q, cfg, rng=np.random.default_rng(7))
        return sorted((c.obs_id, c.hip_id) for c in algo.match(algo.extract_features(obs), db))

    assert run() == run()
