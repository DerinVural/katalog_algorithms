"""Kabul testleri — Liebe (brief 02 §Kabul testleri)."""
import math
from pathlib import Path

import numpy as np
import pytest

from bench.algorithms.liebe import LiebeAlgorithm, LiebeConfig
from bench.core.interfaces import Catalog, CatalogStar
from bench.core.scene import NoiseConfig, simulate_scene
from bench.core.sensor import SENSOR
from bench.runner import build, run_monte_carlo, run_trial, write_csv

RESULTS = Path(__file__).resolve().parent.parent / "results"


# 1) Gürültüsüz, zengin sahne: id_rate>=0.99, false_id yok, attitude < birkaç arcsec
def test_liebe_noiseless(catalog, rich_attitude):
    algo = LiebeAlgorithm()
    recs = run_monte_carlo(algo, catalog, rich_attitude, n_trials=10, seed=1)
    idr = np.mean([r["id_rate"] for r in recs])
    assert idr >= 0.99, f"id_rate {idr}"
    assert not any(r["false_id_flag"] for r in recs)
    assert np.mean([r["attitude_error_arcsec"] for r in recs]) < 5.0


# 2) DB boyutu O(n): merkez başına C(K,2) kayıt, tekil merkez ~ katalog
def test_liebe_db_on_order(catalog):
    from bench.core.metrics import db_size_bytes
    algo = LiebeAlgorithm()
    db = algo.build_database(catalog)
    k = algo.cfg.neighbors_k
    max_per_star = math.comb(k, 2)
    n_centers = len(set(db.hip_center.tolist()))
    assert 0 < db.n_records <= max_per_star * len(catalog)   # O(n)
    assert n_centers > 0.9 * len(catalog)                    # çoğu yıldız >=2 komşu
    assert db_size_bytes(db) > 0


# 3) d1≈d2 vakası: iki en yakın komşu neredeyse eşit uzaklıkta -> doğru eşleşir
def test_liebe_d1_approx_d2():
    # boresight çevresinde küçük açılarla sentetik alan
    def dir_xy(ax, ay):  # küçük açı -> birim vektör (z~1)
        v = np.array([math.sin(ax), math.sin(ay), 1.0]); return v / np.linalg.norm(v)
    r = math.radians(2.0)
    stars = [
        CatalogStar(1, np.array([0.0, 0.0, 1.0]), 3.0),       # merkez
        CatalogStar(2, dir_xy(r, 0.0), 3.0),                  # komşu d1
        CatalogStar(3, dir_xy(0.0, r * 1.02), 3.0),           # komşu d2 ≈ d1
        CatalogStar(4, dir_xy(-2 * r, r), 4.0),               # distraktör
        CatalogStar(5, dir_xy(r, -3 * r), 4.0),               # distraktör
    ]
    cat = Catalog(stars=stars)
    algo = LiebeAlgorithm()
    db = algo.build_database(cat)
    obs, truth = simulate_scene(cat, np.array([0, 0, 0, 1.0]), rng=np.random.default_rng(0))
    cands = {c.obs_id: c.hip_id for c in algo.match(algo.extract_features(obs), db)}
    # merkez yıldız (hip=1) doğru tanınmalı
    center_obs = [o for o, h in truth.true_matches.items() if h == 1][0]
    assert cands.get(center_obs) == 1


# 4) Gürültü grace: id_rate monotonca düşer ama σ=5″'te >=%90 (eğri results/'a)
def test_liebe_noise_grace(catalog, rich_attitude):
    algo = LiebeAlgorithm()
    db, _ = build(algo, catalog)
    sigmas = [2, 5, 10, 20]
    curve = []
    for sig in sigmas:
        cfg = NoiseConfig(sigma_centroid_arcsec=sig)
        rng = np.random.default_rng(1)
        idr = np.mean([
            run_trial(algo, db, catalog, rich_attitude, cfg, rng)["id_rate"]
            for _ in range(15)
        ])
        curve.append({"sigma_arcsec": sig, "id_rate": float(idr)})

    idr = {c["sigma_arcsec"]: c["id_rate"] for c in curve}
    # σ=5'te >=%90
    assert idr[5] >= 0.90, f"σ=5 id_rate {idr[5]}"
    # monotonca artmayan (küçük gürültü payı)
    vals = [idr[s] for s in sigmas]
    assert all(vals[i] <= vals[i - 1] + 0.03 for i in range(1, len(vals)))

    write_csv(curve, RESULTS / "liebe_grace.csv")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(sigmas, vals, "o-")
        ax.set(xlabel="centroid σ [arcsec]", ylabel="id_rate",
               title="Liebe gürültü grace eğrisi", ylim=(0, 1.02))
        ax.grid(True, alpha=0.3)
        fig.savefig(RESULTS / "liebe_grace.png", dpi=120)
        plt.close(fig)
    except Exception:
        pass


# 5) Spike toleransı: 3 spike -> false_id nadir, katastrofik yanlış-attitude yok
def test_liebe_spike_tolerance(catalog, rich_attitude):
    algo = LiebeAlgorithm()
    cfg = NoiseConfig(sigma_centroid_arcsec=5.0, n_spikes=3)
    recs = run_monte_carlo(algo, catalog, rich_attitude, cfg, n_trials=30, seed=2)
    false_rate = np.mean([r["false_id_flag"] for r in recs])
    assert false_rate <= 0.2, f"false_id oranı {false_rate}"   # nadir, katastrofik değil


# 6) Determinizm: sabit seed -> aynı sonuç
def test_liebe_deterministic(catalog, rich_attitude):
    algo = LiebeAlgorithm()
    db, _ = build(algo, catalog)
    cfg = NoiseConfig(sigma_centroid_arcsec=5.0, n_spikes=3)

    def run():
        obs, _ = simulate_scene(catalog, rich_attitude, cfg, rng=np.random.default_rng(7))
        cands = algo.match(algo.extract_features(obs), db)
        return sorted((c.obs_id, c.hip_id) for c in cands)

    assert run() == run()
