"""Faz 1 head-to-head: Liebe vs Planar Triangle (brief 03 §Karşılaştırma).

Aynı sahne setinde iki algoritmayı koşar; id_rate, false_id, ölçülen search
süresi ve DB boyutunu `results/phase1_compare.csv`'ye yazar. Bench core
değiştirilmez (ayrı dosya).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .algorithms.liebe import LiebeAlgorithm
from .algorithms.triangle_planar import TrianglePlanarAlgorithm
from .core import metrics
from .core.catalog import load_catalog
from .core.quest import quest, random_quat
from .core.scene import NoiseConfig, simulate_scene
from .runner import write_csv

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _eval_on_scene(algo, db, catalog, observed, truth) -> dict[str, Any]:
    if hasattr(algo, "set_truth"):
        algo.set_truth(truth)
    feats, t_ext = metrics.timed(algo.extract_features, observed)
    cands, t_mat = metrics.timed(algo.match, feats, db)
    q_est = quest(cands, catalog, observed)
    res = metrics.evaluate(q_est, cands, truth)
    return {
        "id_rate": res.id_rate, "false_id_flag": res.false_id_flag,
        "no_solution": res.no_solution, "wrong_attitude": res.wrong_attitude,
        "n_wrong": res.n_wrong, "attitude_error_arcsec": res.attitude_error_arcsec,
        "t_extract_s": t_ext, "t_match_s": t_mat,
    }


def compare(
    catalog=None,
    noise_cfg: NoiseConfig | None = None,
    n_trials: int = 100,
    seed: int = 0,
) -> dict[str, Any]:
    catalog = catalog if catalog is not None else load_catalog()
    if noise_cfg is None:
        noise_cfg = NoiseConfig(sigma_centroid_arcsec=5.0, n_spikes=3)

    algos = {"liebe": LiebeAlgorithm(), "triangle_planar": TrianglePlanarAlgorithm()}
    built = {}
    for name, algo in algos.items():
        db, t_build = metrics.timed(algo.build_database, catalog)
        built[name] = (db, metrics.db_size_bytes(db), t_build)

    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_trials):
        q = random_quat(rng)
        observed, truth = simulate_scene(catalog, q, noise_cfg, rng=rng)
        if len(observed) < 3:
            continue
        for name, algo in algos.items():
            db, db_bytes, t_build = built[name]
            m = _eval_on_scene(algo, db, catalog, observed, truth)
            rows.append({"trial": i, "algo": name, "n_observed": len(observed),
                         "db_bytes": db_bytes, "build_s": round(t_build, 3), **m})

    write_csv(rows, RESULTS_DIR / "phase1_compare.csv")
    return _summarize(rows, built)


def _summarize(rows, built) -> dict[str, Any]:
    summary = {}
    for name in built:
        r = [x for x in rows if x["algo"] == name]
        if not r:
            continue
        summary[name] = {
            "db_bytes": built[name][1],
            "build_s": built[name][2],
            "id_rate_mean": float(np.mean([x["id_rate"] for x in r])),
            "false_id_rate": float(np.mean([x["false_id_flag"] for x in r])),
            "wrong_attitude_rate": float(np.mean([x["wrong_attitude"] for x in r])),
            "no_solution_rate": float(np.mean([x["no_solution"] for x in r])),
            "t_match_ms_median": float(np.median([x["t_match_s"] for x in r]) * 1e3),
            "t_extract_ms_median": float(np.median([x["t_extract_s"] for x in r]) * 1e3),
        }
    return summary


def main() -> None:
    cat = load_catalog()
    s = compare(cat, n_trials=100, seed=0)
    print("=== Faz 1 karşılaştırma (Liebe vs Triangle) ===")
    for name, m in s.items():
        print(f"\n[{name}]")
        print(f"  DB boyutu    : {m['db_bytes']/1e6:.2f} MB")
        print(f"  build        : {m['build_s']:.2f} s")
        print(f"  id_rate ort  : {m['id_rate_mean']:.3f}")
        print(f"  wrong_attitude: {m['wrong_attitude_rate']:.3f}  (TEHLİKELİ)")
        print(f"  no_solution  : {m['no_solution_rate']:.3f}  (güvenli)")
        print(f"  match medyan : {m['t_match_ms_median']:.3f} ms")
        print(f"  extract medyan: {m['t_extract_ms_median']:.3f} ms")
    if "liebe" in s and "triangle_planar" in s:
        ratio = s["triangle_planar"]["db_bytes"] / s["liebe"]["db_bytes"]
        print(f"\nDB boyut oranı (triangle / liebe): {ratio:.0f}x  "
              f"(O(n·f²) vs O(n) ampirik kanıtı)")
    print(f"\nCSV: {RESULTS_DIR / 'phase1_compare.csv'}")


if __name__ == "__main__":
    main()
