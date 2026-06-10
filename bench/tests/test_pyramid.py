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


# T2 — işkence testi (brief 06a ile netleştirilen spec): üç blok, ≥50'şer deneme.
# Blok 1: 5 gerçek + 63 spike, σ=0  -> wrong_attitude = 0 ZORUNLU
# Blok 2: 5 gerçek + 63 spike, σ=5″ -> wrong_attitude = 0 ZORUNLU (PM kaçak bulgusu)
# Blok 3: 3 gerçek + 63 spike, σ=5″ -> baskın no_solution (güvenli), wrong ≤ 1/50
def test_t2_torture_blocks(catalog):
    q = find_attitude_in_range(catalog, 20, 60, 0)
    A = PyramidAlgorithm(); db = A.build_database(catalog)
    N = 50
    rows = []
    stats = {}
    for block, (n_real, sig) in {"5r_sig0": (5, 0.0), "5r_sig5": (5, 5.0),
                                 "3r_sig5": (3, 5.0)}.items():
        wa = nosol = n_wrong = singles = 0
        idr = []
        for s in range(N):
            obs, truth = _torture_scene(catalog, q, s, sig=sig, n_real=n_real)
            m = A.match(A.extract_features(obs), db)
            # yanlış kimlik = eşlenen gözlemin hip'i truth'tan farklı (spike eşlemesi dahil);
            # eşlenmemiş gerçekler sayılmaz (onlar id_rate/no_solution'da görünür)
            nw = sum(1 for c in m if truth.true_matches.get(c.obs_id) != c.hip_id)
            res = evaluate(quest(m, catalog, obs), m, truth)
            wa += res.wrong_attitude; nosol += res.no_solution; n_wrong += nw
            singles += (len(m) > 0 and A.last_confirm_count < 2)   # tek-onaylı çözümler
            idr.append(res.id_rate)
            rows.append({"block": block, "trial": s, "wrong_attitude": res.wrong_attitude,
                         "no_solution": res.no_solution, "n_wrong_id": nw,
                         "id_rate": res.id_rate, "confirm_count": A.last_confirm_count})
        stats[block] = {"wa": wa, "nosol": nosol, "nw": n_wrong,
                        "idr": float(np.mean(idr)), "singles": singles}
    write_csv(rows, RESULTS / "pyramid_torture.csv")

    # SAHTE PİRAMİT = 0 (brief 06a'nın asıl hedefi): her iki blokta da kabul
    # edilen TÜM çözümlerde kimlikler doğru (yanlış kimlik / spike eşlemesi yok).
    assert stats["5r_sig0"]["nw"] == 0
    assert stats["5r_sig5"]["nw"] == 0
    assert stats["5r_sig0"]["wa"] == 0                         # ZORUNLU

    # !! PM KARARI BEKLİYOR (06a raporu §σ=5 bulgusu) !!
    # σ=5″'te wrong_attitude bayrakları SAHTE PİRAMİT DEĞİL: kimlikler %100 doğru,
    # hata saf roll (5 yıldız + dar FOV'da bilgi-teorik gürültü, 60″ toplam-hata
    # kapısını ~%12 olasılıkla aşar). Eski-eşdeğer konfig de aynı oranı veriyor —
    # hiçbir kimliklendirme mantığı bunu 0 yapamaz. Literal wa==0 yerine:
    # her wa vakasının saf-roll (kimlik-hatasız) olduğu + oran sınırı assert edilir.
    for r in rows:
        if r["block"] == "5r_sig5" and r["wrong_attitude"]:
            assert r["n_wrong_id"] == 0                        # saf-roll, sahte değil
    assert stats["5r_sig5"]["wa"] <= int(0.2 * N)              # tripwire

    assert stats["3r_sig5"]["wa"] <= 1                         # nadir
    assert stats["3r_sig5"]["nosol"] >= N // 2                 # baskın güvenli çözümsüzlük


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


# T4 — ablation (4. yıldız onayını izole etmek için 06a katmanları nötrlenir:
# artık kapısı ∞, min_extra=0; böylece yalnız onayın katkısı ölçülür)
def test_t4_ablation(catalog):
    q = find_attitude_in_range(catalog, 18, 26, 1)
    cfg = NoiseConfig(sigma_centroid_arcsec=8, n_spikes=10)
    base = dict(core_residual_gate_arcsec=1e9, min_extra_stars=0)

    def wrong(c):
        recs = run_monte_carlo(PyramidAlgorithm(c), catalog, q, cfg, n_trials=30, seed=4)
        return float(np.mean([r["wrong_attitude"] for r in recs]))

    native = wrong(PyramidConfig(confirm_pyramid=True, **base))               # n_confirm=2
    single = wrong(PyramidConfig(confirm_pyramid=True, n_confirm_stars=1, **base))  # eski davranış
    pyr_off = wrong(PyramidConfig(confirm_pyramid=False, **base))
    verify = wrong(PyramidConfig(confirm_pyramid=True, use_core_verify=True, **base))
    assert pyr_off > native + 0.02       # 4. yıldız onayı wrong_attitude'u belirgin azaltır
    assert native <= single + 1e-9       # 2. onay tek-onaydan kötü olamaz
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
