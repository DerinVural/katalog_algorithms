"""Kabul testleri — Quine (brief 04 §Kabul testleri)."""
from pathlib import Path

import numpy as np

from bench.algorithms.liebe import LiebeAlgorithm
from bench.algorithms.quine import QuineAlgorithm, QuineConfig
from bench.core.interfaces import Catalog
from bench.core.scene import NoiseConfig, simulate_scene
from bench.runner import run_monte_carlo, run_trial, write_csv
from bench.tests.conftest import find_attitude_in_range

RESULTS = Path(__file__).resolve().parent.parent / "results"


# 1) EŞDEĞERLİK (en önemli): Quine eşleşme kümesi == Liebe (tek fark hız)
def test_quine_equivalent_to_liebe(catalog, rich_attitude):
    L, Q = LiebeAlgorithm(), QuineAlgorithm()
    ldb, qdb = L.build_database(catalog), Q.build_database(catalog)
    for seed in range(6):
        for cfg in (NoiseConfig(), NoiseConfig(sigma_centroid_arcsec=8, n_spikes=3)):
            obs, _ = simulate_scene(catalog, rich_attitude, cfg, rng=np.random.default_rng(seed))
            lm = sorted((c.obs_id, c.hip_id) for c in L.match(L.extract_features(obs), ldb))
            qm = sorted((c.obs_id, c.hip_id) for c in Q.match(Q.extract_features(obs), qdb))
            assert lm == qm, f"seed={seed} eşdeğerlik bozuldu"


# 2) gürültüsüz id_rate >= 0.99, wrong_attitude = 0
def test_quine_noiseless(catalog, rich_attitude):
    recs = run_monte_carlo(QuineAlgorithm(), catalog, rich_attitude, n_trials=8, seed=1)
    assert np.mean([r["id_rate"] for r in recs]) >= 0.99
    assert not any(r["wrong_attitude"] for r in recs)


# 3) ölçekleme (Tablo 1): Liebe taranan kayıt ~O(n), Quine aday ~sabit
def test_quine_search_scaling(catalog):
    full = catalog
    rng0 = np.random.default_rng(0)
    tol_d = 15 * np.pi / (180 * 3600)
    ns = [1000, 2000, 4000, len(full.stars)]
    rows = []
    for n in ns:
        cat = (full if n >= len(full.stars)
               else Catalog([full.stars[i] for i in rng0.choice(len(full.stars), n, replace=False)]))
        L, Q = LiebeAlgorithm(), QuineAlgorithm()
        ldb, qdb = L.build_database(cat), Q.build_database(cat)
        q = find_attitude_in_range(cat, 8, 40, 1)
        scanned, cand = [], []
        rng = np.random.default_rng(2)
        for _ in range(20):
            obs, _ = simulate_scene(cat, q, NoiseConfig(sigma_centroid_arcsec=5), rng=rng)
            if len(obs) < 3:
                continue
            for (oc, on1, on2, d1, d2, theta) in L.extract_features(obs):
                lo = np.searchsorted(ldb.d1, d1 - tol_d, "left")
                hi = np.searchsorted(ldb.d1, d1 + tol_d, "right")
                scanned.append(hi - lo)
                qs = np.array([d1, d2, theta]) * qdb.scale
                cand.append(len(qdb.tree.query_ball_point(qs, r=1.0, p=np.inf)))
        rows.append({"n": n, "liebe_scanned_per_query": float(np.mean(scanned)),
                     "quine_candidates_per_query": float(np.mean(cand))})
    write_csv(rows, RESULTS / "quine_scaling.csv")

    liebe_ratio = rows[-1]["liebe_scanned_per_query"] / rows[0]["liebe_scanned_per_query"]
    quine_ratio = rows[-1]["quine_candidates_per_query"] / rows[0]["quine_candidates_per_query"]
    assert liebe_ratio >= 4.0          # ~O(n): n 5× artınca tarama ~5× büyür
    assert quine_ratio <= 2.0          # ~sabit: kutu sorgusu n'den bağımsız

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        x = [r["n"] for r in rows]
        fig, ax = plt.subplots()
        ax.plot(x, [r["liebe_scanned_per_query"] for r in rows], "o-", label="Liebe taranan (~O(n))")
        ax.plot(x, [r["quine_candidates_per_query"] for r in rows], "s-", label="Quine aday (~sabit)")
        ax.set(xlabel="katalog n", ylabel="sorgu başına kayıt",
               title="Arama ölçeklemesi: Liebe O(n) vs Quine O(lg n)")
        ax.legend(); ax.grid(alpha=.3)
        fig.savefig(RESULTS / "quine_scaling.png", dpi=120)
        plt.close(fig)
    except Exception:
        pass


# 4) native vs +ortak doğrulayıcı: verify spike yanlışlarını buder, wrong_attitude'u düşürür
def test_quine_native_vs_verify(catalog, moderate_attitude):
    cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=20)
    native = run_monte_carlo(QuineAlgorithm(QuineConfig(use_core_verify=False)),
                             catalog, moderate_attitude, cfg, n_trials=25, seed=4)
    verify = run_monte_carlo(QuineAlgorithm(QuineConfig(use_core_verify=True)),
                             catalog, moderate_attitude, cfg, n_trials=25, seed=4)
    nwrong_n = np.mean([r["n_wrong"] for r in native])
    nwrong_v = np.mean([r["n_wrong"] for r in verify])
    wrong_n = np.mean([r["wrong_attitude"] for r in native])
    wrong_v = np.mean([r["wrong_attitude"] for r in verify])
    assert nwrong_n > 0                # native: spike yanlış eşleşmeleri var
    assert nwrong_v < nwrong_n         # verify onları buder
    assert wrong_v <= wrong_n          # verify wrong_attitude'u artırmaz (düşürür)


# 5) determinizm
def test_quine_deterministic(catalog, rich_attitude):
    Q = QuineAlgorithm()
    db = Q.build_database(catalog)
    cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=3)

    def run():
        obs, _ = simulate_scene(catalog, rich_attitude, cfg, rng=np.random.default_rng(7))
        return sorted((c.obs_id, c.hip_id) for c in Q.match(Q.extract_features(obs), db))

    assert run() == run()
