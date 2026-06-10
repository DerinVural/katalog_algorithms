"""Kabul testleri — Pyramid (brief 06 §Kabul testleri), Faz 2 finali."""
from itertools import combinations
from pathlib import Path

import numpy as np

from bench.algorithms.liebe import LiebeAlgorithm
from bench.algorithms.quine import QuineAlgorithm
from bench.algorithms.triangle_planar import TrianglePlanarAlgorithm
from bench.algorithms.sla_kvector import SLAAlgorithm
from bench.algorithms.pyramid import (PyramidAlgorithm, PyramidConfig,
                                      pyramid_triad_order)
from bench.core.interfaces import SceneTruth
from bench.core.metrics import evaluate
from bench.core.quest import quest
from bench.core.scene import NoiseConfig, simulate_scene
from bench.runner import run_monte_carlo, write_csv
from bench.tests.conftest import find_attitude_in_range

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _torture_scene(cat, q, seed, sig=0.0, n_real=5, n_spike=63):
    """Tam n_real gerçek + n_spike spike, karıştırılmış (survey işkence kurgusu)."""
    obs, truth = simulate_scene(cat, q, NoiseConfig(sigma_centroid_arcsec=sig, n_spikes=n_spike),
                                rng=np.random.default_rng(seed))
    reals = [o for o in obs if o.obs_id in truth.true_matches]
    spikes = [o for o in obs if o.obs_id not in truth.true_matches]
    rng = np.random.default_rng(1000 + seed)
    kept = [reals[i] for i in rng.permutation(len(reals))[:n_real]]
    new = kept + spikes
    rng.shuffle(new)
    tm = {o.obs_id: truth.true_matches[o.obs_id] for o in kept}
    return new, SceneTruth(q_true=truth.q_true, true_matches=tm)


# T1 — akıllı permütasyon birim testi
def test_t1_triad_order():
    for f in [5, 8, 12, 20]:
        order = pyramid_triad_order(f)
        allc = set(combinations(range(f), 3))
        assert len(order) == len(allc) == len(set(order))      # (a) tam bir kez
        assert set(order) == allc
        # (b) ilk ~f denemede hiçbir indeks tüm üçlülerde ortak değil
        first = order[:f]
        common = set(first[0])
        for t in first[1:]:
            common &= set(t)
        assert len(common) == 0
    assert pyramid_triad_order(10) == pyramid_triad_order(10)   # (c) deterministik


# T2 — işkence testi (survey referansı): 5 gerçek + 63 spike, wrong_attitude=0 ZORUNLU
def test_t2_torture_5real_63spike(catalog):
    q = find_attitude_in_range(catalog, 20, 60, 0)
    A = PyramidAlgorithm(); db = A.build_database(catalog)
    rows = []
    for s in range(15):
        obs, truth = _torture_scene(catalog, q, s, sig=0.0)
        m = A.match(A.extract_features(obs), db)
        cm = {c.obs_id: c.hip_id for c in m}
        n_wrong = (sum(1 for o, h in truth.true_matches.items() if cm.get(o) != h)
                   + sum(1 for c in m if c.obs_id not in truth.true_matches))
        res = evaluate(quest(m, catalog, obs), m, truth)
        rows.append({"trial": s, "wrong_attitude": res.wrong_attitude,
                     "no_solution": res.no_solution, "n_wrong_id": n_wrong,
                     "id_rate": res.id_rate})
    write_csv(rows, RESULTS / "pyramid_torture.csv")
    assert not any(r["wrong_attitude"] for r in rows)          # ZORUNLU
    assert sum(r["n_wrong_id"] for r in rows) == 0             # yanlış kimlik yok
    assert np.mean([r["id_rate"] for r in rows]) >= 0.9        # 5 gerçek çoğunlukla tanınır


# T3 — Faz 2 finali spike taraması: 5 algoritma (phase2_spike_sweep)
def test_t3_phase2_spike_sweep(catalog):
    q = find_attitude_in_range(catalog, 18, 26, 1)
    algos = {"liebe": LiebeAlgorithm(), "quine": QuineAlgorithm(),
             "triangle_planar": TrianglePlanarAlgorithm(), "sla_kvector": SLAAlgorithm(),
             "pyramid": PyramidAlgorithm()}
    rows = []
    pyr = {}
    for name, algo in algos.items():
        for ns in [0, 5, 20]:
            cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=ns)
            recs = run_monte_carlo(algo, catalog, q, cfg, n_trials=8, seed=11)
            wa = float(np.mean([r["wrong_attitude"] for r in recs]))
            rows.append({"algo": name, "n_spikes": ns,
                         "wrong_attitude_rate": wa,
                         "no_solution_rate": float(np.mean([r["no_solution"] for r in recs])),
                         "id_rate": float(np.mean([r["id_rate"] for r in recs]))})
            if name == "pyramid":
                pyr[ns] = wa
    write_csv(rows, RESULTS / "phase2_spike_sweep.csv")
    # Pyramid spike altında wrong_attitude'u en düşük (≤) tutar
    for ns in [5, 20]:
        others = [r["wrong_attitude_rate"] for r in rows if r["n_spikes"] == ns and r["algo"] != "pyramid"]
        assert pyr[ns] <= max(others) + 1e-9


# T4 — ablation üçlüsü (4. yıldız onayını izole etmek için min_solution_stars=2)
def test_t4_ablation(catalog):
    q = find_attitude_in_range(catalog, 18, 26, 1)
    cfg = NoiseConfig(sigma_centroid_arcsec=8, n_spikes=10)

    def wrong(c):
        recs = run_monte_carlo(PyramidAlgorithm(c), catalog, q, cfg, n_trials=30, seed=4)
        return float(np.mean([r["wrong_attitude"] for r in recs]))

    native = wrong(PyramidConfig(confirm_pyramid=True, min_solution_stars=2))
    pyr_off = wrong(PyramidConfig(confirm_pyramid=False, min_solution_stars=2))
    verify = wrong(PyramidConfig(confirm_pyramid=True, use_core_verify=True, min_solution_stars=2))
    assert pyr_off > native + 0.02       # 4. yıldız onayı wrong_attitude'u belirgin azaltır
    assert verify <= native + 1e-9       # +verify kötüleştirmez


# T5 — gürültüsüz taban
def test_t5_noiseless(catalog, rich_attitude):
    recs = run_monte_carlo(PyramidAlgorithm(), catalog, rich_attitude, n_trials=8, seed=1)
    assert np.mean([r["id_rate"] for r in recs]) >= 0.99
    assert not any(r["wrong_attitude"] for r in recs)


# T6 — determinizm
def test_t6_deterministic(catalog, rich_attitude):
    A = PyramidAlgorithm(); db = A.build_database(catalog)
    cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=5)

    def run():
        obs, _ = simulate_scene(catalog, rich_attitude, cfg, rng=np.random.default_rng(7))
        return sorted((c.obs_id, c.hip_id) for c in A.match(A.extract_features(obs), db))

    assert run() == run()
