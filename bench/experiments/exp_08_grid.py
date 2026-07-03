"""Brief 08 — Padgett Grid adversarial deneyler (A1-A5) + rapor artefaktları.

Çalıştır:  python -m bench.experiments.exp_08_grid [N_TRIALS]

Üretir (results/ altına):
  A1/A5 spike süpürme  : exp08_spike.csv,  exp08_spike.png   (Grid native/ablation vs Pyramid)
  A2 centroid gürültü  : exp08_noise.csv,  exp08_noise.png
  A3 completeness       : exp08_completeness.csv, exp08_completeness.png
  timing vs gözlem      : exp08_timing.csv, exp08_timing.png
  DB dökümü (insan)     : exp08_db_dump.csv
  sahne görseli         : exp08_scene.png

Tasarım: mutlak süreler makine yüküne duyarlı; anlamlı olan GÖRELİ kıyas
(Grid vs Pyramid). Grid match ~açı-yöntemlerinden yavaş (maskeli Hamming tüm
katalog + O(n³) consensus) — deneme sayıları buna göre ölçülü.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

from ..algorithms.padgett_grid import PadgettGridAlgorithm, PadgettGridConfig
from ..algorithms.pyramid import PyramidAlgorithm
from ..core.catalog import load_catalog
from ..core.quest import quest, random_quat, rotate
from ..core.scene import NoiseConfig, simulate_scene
from ..core.sensor import SENSOR
from ..core.metrics import evaluate, db_size_bytes
from ..runner import build, write_csv

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _attitudes(catalog, n, lo=10, hi=18):
    """n farklı, [lo,hi] yıldızlı attitude (deterministik tohumlar)."""
    from ..tests.conftest import find_attitude_in_range
    return [find_attitude_in_range(catalog, lo, hi, s) for s in range(n)]


def _eval_batch(algo, db, catalog, attitudes, noise, ntr, seed0=1):
    """attitudes × ntr gerçekleme -> ortalama metrikler + medyan match süresi."""
    idr, wa, ns, tm = [], [], [], []
    for k, q in enumerate(attitudes):
        rng = np.random.default_rng(seed0 + k)
        for _ in range(ntr):
            obs, truth = simulate_scene(catalog, q, noise, rng)
            if len(obs) < 3:
                continue
            feats = algo.extract_features(obs)
            t0 = time.perf_counter()
            cands = algo.match(feats, db)
            tm.append(time.perf_counter() - t0)
            qe = quest(cands, catalog, obs)
            r = evaluate(qe, cands, truth)
            idr.append(r.id_rate); wa.append(r.wrong_attitude); ns.append(r.no_solution)
    return {
        "id_rate": float(np.mean(idr)) if idr else 0.0,
        "wrong_attitude": float(np.mean(wa)) if wa else 0.0,
        "no_solution": float(np.mean(ns)) if ns else 0.0,
        "match_ms": float(np.median(tm) * 1e3) if tm else 0.0,
    }


# ------------------------------------------------- A1 + A5: spike süpürme (manşet)
def a1_a5_spike_sweep(catalog, atts, ntr):
    print("[A1/A5] spike süpürme (Grid native/ablation vs Pyramid)...")
    grid = PadgettGridAlgorithm()
    grid_abl = PadgettGridAlgorithm(PadgettGridConfig(use_shared_verify=True))
    pyr = PyramidAlgorithm()
    gdb, gbytes = build(grid, catalog)
    pdb, pbytes = build(pyr, catalog)
    algos = [("grid_native", grid, gdb), ("grid_ablation", grid_abl, gdb),
             ("pyramid", pyr, pdb)]
    rows = []
    for sp in [0, 2, 4, 8, 12, 16, 20, 24]:
        noise = NoiseConfig(sigma_centroid_arcsec=2.0, n_spikes=sp)
        for name, algo, db in algos:
            m = _eval_batch(algo, db, catalog, atts, noise, ntr)
            rows.append({"spikes": sp, "algo": name, **m})
            print(f"   spikes={sp:2d} {name:14s} id={m['id_rate']:.3f} "
                  f"wa={m['wrong_attitude']:.3f} nosol={m['no_solution']:.3f} "
                  f"match={m['match_ms']:.1f}ms")
    write_csv(rows, RESULTS / "exp08_spike.csv")
    _plot_spike(rows)
    return rows, {"grid": gbytes, "pyramid": pbytes}


def _plot_spike(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    names = ["grid_native", "grid_ablation", "pyramid"]
    sps = sorted({r["spikes"] for r in rows})
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for metric, a, ttl in [("id_rate", ax[0], "id_rate"),
                           ("wrong_attitude", ax[1], "wrong_attitude (TEHLİKELİ)"),
                           ("no_solution", ax[2], "no_solution (güvenli)")]:
        for nm in names:
            ys = [next(r[metric] for r in rows if r["spikes"] == s and r["algo"] == nm)
                  for s in sps]
            a.plot(sps, ys, "o-", label=nm)
        a.set(xlabel="spike sayısı", ylabel=metric, title=ttl)
        a.grid(alpha=.3); a.legend(fontsize=8)
    fig.suptitle("A1/A5 — Grid vs Pyramid spike dayanımı (σ=2″)")
    fig.tight_layout()
    fig.savefig(RESULTS / "exp08_spike.png", dpi=125)
    plt.close(fig)


# ------------------------------------------------------- A2: centroid gürültü
def a2_noise_sweep(catalog, atts, ntr):
    print("[A2] centroid gürültü süpürme...")
    grid = PadgettGridAlgorithm()
    gdb, _ = build(grid, catalog)
    pyr = PyramidAlgorithm(); pdb, _ = build(pyr, catalog)
    rows = []
    # hücre yarısı ~0.15° = 540″; taban-çevrilme başlangıcını bulmak için
    for sig in [0, 2, 5, 10, 20, 60, 180, 360, 540]:
        noise = NoiseConfig(sigma_centroid_arcsec=sig)
        mg = _eval_batch(grid, gdb, catalog, atts, noise, ntr)
        mp = _eval_batch(pyr, pdb, catalog, atts, noise, ntr)
        rows.append({"sigma_arcsec": sig, "grid_id": mg["id_rate"],
                     "grid_wa": mg["wrong_attitude"], "pyramid_id": mp["id_rate"]})
        print(f"   sigma={sig:4d}\" grid_id={mg['id_rate']:.3f} "
              f"grid_wa={mg['wrong_attitude']:.3f} pyr_id={mp['id_rate']:.3f}")
    write_csv(rows, RESULTS / "exp08_noise.csv")
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        sigs = [r["sigma_arcsec"] for r in rows]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(sigs, [r["grid_id"] for r in rows], "o-", label="Grid id_rate")
        ax.plot(sigs, [r["pyramid_id"] for r in rows], "s--", label="Pyramid id_rate")
        ax.axvline(540, color="gray", ls=":", label="hücre/2 = 540″ (H8c)")
        ax.set(xlabel="sigma_centroid (arcsec)", ylabel="id_rate",
               title="A2 — centroid gürültü: taban-çevrilme başlangıcı", xscale="symlog")
        ax.grid(alpha=.3); ax.legend()
        fig.savefig(RESULTS / "exp08_noise.png", dpi=125); plt.close(fig)
    except Exception:
        pass
    return rows


# ------------------------------------------- A3: katalog-completeness uyumsuzluğu
def a3_completeness(catalog, atts, ntr):
    print("[A3] completeness uyumsuzluğu (eksik yıldız / fazla spike)...")
    grid = PadgettGridAlgorithm(); gdb, _ = build(grid, catalog)
    pyr = PyramidAlgorithm(); pdb, _ = build(pyr, catalog)
    rows = []
    # p_missing: katalogda var, sahnede yok (sınır-magnitude kaybı proxy'si)
    for pm in [0.0, 0.05, 0.10, 0.20, 0.30]:
        noise = NoiseConfig(sigma_centroid_arcsec=2.0, p_missing=pm)
        mg = _eval_batch(grid, gdb, catalog, atts, noise, ntr)
        mp = _eval_batch(pyr, pdb, catalog, atts, noise, ntr)
        rows.append({"p_missing": pm, "grid_id": mg["id_rate"], "grid_nosol": mg["no_solution"],
                     "pyramid_id": mp["id_rate"], "delta_grid": 0.0})
        print(f"   p_missing={pm:.2f} grid_id={mg['id_rate']:.3f} pyr_id={mp['id_rate']:.3f}")
    # göreli düşüş (H8d: Grid açı-yönteminden daha dik düşmeli)
    g0, p0 = rows[0]["grid_id"], rows[0]["pyramid_id"]
    for r in rows:
        r["grid_drop_frac"] = (g0 - r["grid_id"]) / g0 if g0 else 0.0
        r["pyramid_drop_frac"] = (p0 - r["pyramid_id"]) / p0 if p0 else 0.0
    write_csv(rows, RESULTS / "exp08_completeness.csv")
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        pms = [r["p_missing"] for r in rows]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(pms, [r["grid_drop_frac"] for r in rows], "o-", label="Grid göreli düşüş")
        ax.plot(pms, [r["pyramid_drop_frac"] for r in rows], "s--", label="Pyramid göreli düşüş")
        ax.set(xlabel="p_missing (completeness açığı)", ylabel="id_rate göreli düşüş",
               title="A3 — completeness duyarlılığı (H8d)")
        ax.grid(alpha=.3); ax.legend()
        fig.savefig(RESULTS / "exp08_completeness.png", dpi=125); plt.close(fig)
    except Exception:
        pass
    return rows


# ------------------------------------------------------- timing vs gözlem sayısı
def timing_vs_obs(catalog):
    print("[timing] build + match vs gözlem sayısı...")
    grid = PadgettGridAlgorithm()
    # build (best-of-3)
    tb = min(_timeit(lambda: grid.build_database(catalog)) for _ in range(3))
    db = grid.build_database(catalog)
    rows = [{"phase": "build_once_s", "value": round(tb, 3),
             "db_sig_MB": round(db.sig_packed.nbytes / 1e6, 3)}]
    from ..tests.conftest import find_attitude_in_range
    dump = []
    for lo, hi in [(4, 6), (8, 10), (12, 14), (16, 20)]:
        q = find_attitude_in_range(catalog, lo, hi, 0)
        obs, _ = simulate_scene(catalog, q, NoiseConfig(sigma_centroid_arcsec=2),
                                rng=np.random.default_rng(1))
        te = min(_timeit(lambda: grid.extract_features(obs)) for _ in range(3))
        feats = grid.extract_features(obs)
        tm = min(_timeit(lambda: grid.match(feats, db)) for _ in range(3))
        dump.append({"n_observed": len(obs), "extract_ms": round(te * 1e3, 2),
                     "match_ms": round(tm * 1e3, 2), "total_ms": round((te + tm) * 1e3, 2)})
        print(f"   n_obs={len(obs):2d} extract={te*1e3:.2f}ms match={tm*1e3:.2f}ms")
    write_csv(dump, RESULTS / "exp08_timing.csv")
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ns = [d["n_observed"] for d in dump]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(ns, [d["match_ms"] for d in dump], "o-", label="match")
        ax.plot(ns, [d["extract_ms"] for d in dump], "s--", label="extract")
        ax.set(xlabel="gözlem sayısı", ylabel="süre (ms)",
               title="Grid timing vs gözlem (build bir kez: %.2fs)" % tb)
        ax.grid(alpha=.3); ax.legend()
        fig.savefig(RESULTS / "exp08_timing.png", dpi=125); plt.close(fig)
    except Exception:
        pass
    return tb, dump


def _timeit(fn):
    t0 = time.perf_counter(); fn(); return time.perf_counter() - t0


# ------------------------------------------------------- DB dökümü (insan-birimli)
def db_dump(catalog):
    print("[DB] insan-birimli döküm...")
    grid = PadgettGridAlgorithm()
    db = grid.build_database(catalog)
    from ..algorithms.padgett_grid import _POPCOUNT
    n_bits = _POPCOUNT[db.sig_packed].sum(axis=1)     # her yıldızın dolu hücre sayısı
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(catalog))[:25]
    rows = []
    for i in sorted(idx):
        st = catalog.stars[i]
        rows.append({"hip": int(st.hip_id), "mag": round(float(st.mag), 2),
                     "n_set_bits": int(n_bits[i]), "valid_NN": bool(db.valid[i])})
    write_csv(rows, RESULTS / "exp08_db_dump.csv")
    stats = {"sig_matrix_MB": round(db.sig_packed.nbytes / 1e6, 3),
             "total_deep_MB": round(db_size_bytes(db) / 1e6, 3),
             "valid_frac": round(float(db.valid.mean()), 3),
             "mean_set_bits": round(float(n_bits.mean()), 2),
             "median_set_bits": int(np.median(n_bits)),
             "frac_le2_bits": round(float(np.mean(n_bits <= 2)), 3)}
    print("   ", stats)
    return stats


# ------------------------------------------------------------- sahne görseli
def scene_figure(catalog):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    from ..tests.conftest import find_attitude_in_range
    from ..core.pinhole import body_to_focal
    q = find_attitude_in_range(catalog, 12, 16, 0)
    obs, truth = simulate_scene(catalog, q, NoiseConfig(sigma_centroid_arcsec=2, n_spikes=4),
                                rng=np.random.default_rng(1))
    grid = PadgettGridAlgorithm(); db = grid.build_database(catalog)
    cands = grid.match(grid.extract_features(obs), db)
    idset = {c.obs_id for c in cands}
    fig, ax = plt.subplots(figsize=(7, 7))
    for o in obs:
        px = o.centroid_px
        spike = o.obs_id not in truth.true_matches
        ided = o.obs_id in idset
        color = "red" if spike else ("green" if ided else "gray")
        mark = "x" if spike else "o"
        ax.scatter(px[0], px[1], c=color, marker=mark, s=60,
                   edgecolors="k", linewidths=0.4)
    ax.set(title="Grid sahnesi: yeşil=ID'lendi, gri=gerçek/ID yok, kırmızı×=spike",
           xlabel="px", ylabel="px"); ax.set_aspect("equal"); ax.grid(alpha=.3)
    fig.savefig(RESULTS / "exp08_scene.png", dpi=120); plt.close(fig)
    print("[scene] exp08_scene.png yazıldı")


def main():
    ntr = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"Katalog yükleniyor... (N_TRIALS={ntr})")
    catalog = load_catalog()
    print(f"  {len(catalog)} yıldız.")
    atts = _attitudes(catalog, 6)

    dbstats = db_dump(catalog)
    tb, tdump = timing_vs_obs(catalog)
    spike_rows, sizes = a1_a5_spike_sweep(catalog, atts, ntr)
    noise_rows = a2_noise_sweep(catalog, atts, ntr)
    comp_rows = a3_completeness(catalog, atts, ntr)
    scene_figure(catalog)

    print("\n=== ÖZET ===")
    print("DB:", dbstats)
    print("Grid sig MB:", round(sizes["grid"] / 1e6, 3),
          "| Pyramid MB:", round(sizes["pyramid"] / 1e6, 3))
    g0 = next(r for r in spike_rows if r["spikes"] == 0 and r["algo"] == "grid_native")
    print(f"Grid noiseless id={g0['id_rate']:.3f} wa={g0['wrong_attitude']:.3f}")
    print(f"Artefaktlar: {RESULTS}")


if __name__ == "__main__":
    main()
