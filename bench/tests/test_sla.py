"""Kabul testleri — Mortari SLA / k-vector (brief 05 §Kabul testleri)."""
from pathlib import Path

import numpy as np

from bench.algorithms.sla_kvector import (SLAAlgorithm, SLAConfig,
                                          build_kvector, kvector_range)
from bench.algorithms.quine import QuineAlgorithm
from bench.core.interfaces import Catalog, CatalogStar
from bench.core.scene import NoiseConfig, simulate_scene
from bench.runner import run_monte_carlo, run_trial, write_csv

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _synth_catalog(n, seed):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    mags = rng.uniform(1.0, 6.0, n)
    return Catalog([CatalogStar(i, v[i], float(mags[i])) for i in range(n)])


# T1 — k-vector birim doğruluğu (EN KRİTİK): searchsorted ile birebir
def test_t1_kvector_exact():
    rng = np.random.default_rng(0)
    fails = 0
    for _ in range(40):
        m = int(rng.integers(2, 3000))
        y = np.sort(rng.uniform(-5, 5, m))
        a, b, K = build_kvector(y)
        for _ in range(300):
            ylo, yhi = np.sort(rng.uniform(-7, 7, 2))
            got = kvector_range(y, a, b, K, ylo, yhi)
            exp = (int(np.searchsorted(y, ylo, "left")), int(np.searchsorted(y, yhi, "right")))
            fails += (got != exp)
    # uç vakalar: dışı, tüm dizi, tek eleman, tekrarlı
    for y in [np.sort(rng.uniform(0, 1, 50)), np.array([3.0]),
              np.array([1.0, 1.0, 2.0, 2.0, 2.0])]:
        a, b, K = build_kvector(y)
        for ylo, yhi in [(-9, -5), (5, 9), (y[0], y[0]), (y[-1], y[-1]), (-1, 2), (2, 2)]:
            got = kvector_range(y, a, b, K, ylo, yhi)
            exp = (int(np.searchsorted(y, ylo, "left")), int(np.searchsorted(y, yhi, "right")))
            fails += (got != exp)
    assert fails == 0, f"{fails} uyuşmazlık"


# T2 — search DB-boyutundan bağımsız: k-vector taşması ~sabit, n'den bağımsız
def test_t2_search_db_independent():
    tol = 15 * np.pi / (180 * 3600)
    rng = np.random.default_rng(1)
    rows = []
    for n in [2000, 5000, 10000, 20000]:
        cat = _synth_catalog(n, seed=n)
        sla = SLAAlgorithm(); quine = QuineAlgorithm()
        db = sla.build_database(cat)
        qdb = quine.build_database(cat)
        y, a, b, K = db.pair_angles, db.a, db.b, db.K
        overflow, k_cand = [], []
        qcand = []
        for _ in range(150):
            theta = float(rng.choice(y))
            ylo, yhi = theta - tol, theta + tol
            lo, hi = kvector_range(y, a, b, K, ylo, yhi)
            i_lo = min(max(int(np.floor((ylo - b) / a)), 1), len(y))
            i_hi = min(max(int(np.ceil((yhi - b) / a)), 1), len(y))
            bracket = int(K[i_hi]) - int(K[i_lo])
            overflow.append(bracket - (hi - lo))
            k_cand.append(hi - lo)
            # Quine: aynı sorgu feature uzayında kaç aday (kıyas)
            qs = np.array([theta, theta, 0.0]) * qdb.scale  # d1=d2=theta gibi tek-eksen kıyas
            qcand.append(len(qdb.tree.query_ball_point(qs, r=1.0, p=np.inf)))
        rows.append({"n": n, "m_pairs": db.n_records,
                     "kvector_overflow_mean": float(np.mean(overflow)),
                     "candidates_mean": float(np.mean(k_cand)),
                     "quine_candidates_mean": float(np.mean(qcand))})
    write_csv(rows, RESULTS / "sla_scaling.csv")
    # k-vector taşması (gerçek arama maliyeti) n 10× artsa da ~sabit ve küçük kalır
    overflows = [r["kvector_overflow_mean"] for r in rows]
    assert max(overflows) <= 10.0, f"taşma büyüdü: {overflows}"
    assert max(overflows) - min(overflows) <= 5.0   # n'den bağımsız ~sabit


# T3 — uçtan uca
def test_t3_end_to_end(catalog, rich_attitude):
    sla = SLAAlgorithm()
    rec0 = run_monte_carlo(sla, catalog, rich_attitude, n_trials=8, seed=1)
    assert np.mean([r["id_rate"] for r in rec0]) >= 0.99
    assert not any(r["wrong_attitude"] for r in rec0)
    rec5 = run_monte_carlo(sla, catalog, rich_attitude,
                           NoiseConfig(sigma_centroid_arcsec=5), n_trials=10, seed=2)
    assert np.mean([r["id_rate"] for r in rec5]) >= 0.90


# T4 — tek-spike dayanımı: çözüm ya doğru ya çözümsüz, wrong_attitude nadir
def test_t4_single_spike(catalog, rich_attitude):
    cfg = NoiseConfig(sigma_centroid_arcsec=3, n_spikes=1, spike_mag_range=(1.0, 3.0))
    recs = run_monte_carlo(SLAAlgorithm(), catalog, rich_attitude, cfg, n_trials=40, seed=3)
    assert np.mean([r["wrong_attitude"] for r in recs]) <= 0.1     # nadir, katastrofik değil
    assert np.mean([r["id_rate"] for r in recs]) >= 0.6           # tek spike çökertmiyor


# T5 — native vs +verify: verify wrong_attitude'u düşürür veya eşit tutar
def test_t5_native_vs_verify(catalog, moderate_attitude):
    cfg = NoiseConfig(sigma_centroid_arcsec=8, n_spikes=5)
    native = run_monte_carlo(SLAAlgorithm(SLAConfig(use_core_verify=False)),
                             catalog, moderate_attitude, cfg, n_trials=25, seed=4)
    verify = run_monte_carlo(SLAAlgorithm(SLAConfig(use_core_verify=True)),
                             catalog, moderate_attitude, cfg, n_trials=25, seed=4)
    wrong_n = np.mean([r["wrong_attitude"] for r in native])
    wrong_v = np.mean([r["wrong_attitude"] for r in verify])
    assert wrong_v <= wrong_n + 1e-9          # verify asla kötüleştirmez


# T6 — determinizm
def test_t6_deterministic(catalog, rich_attitude):
    sla = SLAAlgorithm()
    db = sla.build_database(catalog)
    cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=3)

    def run():
        obs, _ = simulate_scene(catalog, rich_attitude, cfg, rng=np.random.default_rng(7))
        return sorted((c.obs_id, c.hip_id) for c in sla.match(sla.extract_features(obs), db))

    assert run() == run()
