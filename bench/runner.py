"""Bench koşucusu (PROJECT_PLAN.md §3 özeti).

Herkese aynı davranır:
    db = algo.build_database(catalog)            # 1 kez, bellek ölçülür
    for trial:
        scene, truth = simulate_scene(...)       # ORTAK
        feats = timed(algo.extract_features, ...) # algo-özel, süre
        cands = timed(algo.match, ...)           # algo-özel, süre
        q_est = quest(cands, catalog, scene)     # ORTAK
        record(evaluate(q_est, cands, truth))    # ORTAK

Programatik API testlerde, main() CSV+plot üretiminde kullanılır.
"""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .core import metrics
from .core.catalog import load_catalog
from .core.interfaces import Catalog
from .core.quest import quest, random_quat, rotate
from .core.scene import NOISELESS, NoiseConfig, simulate_scene
from .core.sensor import SENSOR, SensorProfile

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def build(algo: Any, catalog: Catalog) -> tuple[Any, int]:
    """DB'yi bir kez kur, bellek boyutunu ölç."""
    db = algo.build_database(catalog)
    return db, metrics.db_size_bytes(db)


def run_trial(
    algo: Any,
    db: Any,
    catalog: Catalog,
    q_true: np.ndarray,
    noise_cfg: NoiseConfig = NOISELESS,
    rng: np.random.Generator | None = None,
    sensor: SensorProfile = SENSOR,
) -> dict[str, Any]:
    """Tek sahne: simüle et -> feature -> match -> attitude -> değerlendir."""
    observed, truth = simulate_scene(catalog, q_true, noise_cfg, rng, sensor)

    # Oracle gibi truth'a ihtiyaç duyan (Protocol dışı) algoritmalar için kanal.
    if hasattr(algo, "set_truth"):
        algo.set_truth(truth)

    feats, t_extract = metrics.timed(algo.extract_features, observed)
    cands, t_match = metrics.timed(algo.match, feats, db)
    q_est = quest(cands, catalog, observed)
    result = metrics.evaluate(q_est, cands, truth)

    rec = asdict(result)
    rec.update(
        n_observed=len(observed),
        t_extract_s=t_extract,
        t_match_s=t_match,
        attitude_solved=q_est is not None,
    )
    return rec


def run_monte_carlo(
    algo: Any,
    catalog: Catalog,
    q_true: np.ndarray,
    noise_cfg: NoiseConfig = NOISELESS,
    n_trials: int = 100,
    seed: int = 0,
    sensor: SensorProfile = SENSOR,
) -> list[dict[str, Any]]:
    """Sabit attitude etrafında n_trials gürültü gerçeklemesi."""
    db, db_bytes = build(algo, catalog)
    rng = np.random.default_rng(seed)
    records = []
    for i in range(n_trials):
        rec = run_trial(algo, db, catalog, q_true, noise_cfg, rng, sensor)
        rec.update(trial=i, db_bytes=db_bytes)
        records.append(rec)
    return records


def run_full_sky(
    algo: Any,
    catalog: Catalog,
    noise_cfg: NoiseConfig = NOISELESS,
    n_points: int = 200,
    seed: int = 0,
    min_id_rate: float = 0.99,
    sensor: SensorProfile = SENSOR,
) -> dict[str, Any]:
    """Full-sky rastgele attitude grid -> sky coverage.

    Bir nokta 'kapsandı' sayılır: attitude çözüldü, false-id yok,
    id_rate >= min_id_rate.
    """
    db, db_bytes = build(algo, catalog)
    rng = np.random.default_rng(seed)
    records = []
    covered = 0
    for i in range(n_points):
        q = random_quat(rng)
        rec = run_trial(algo, db, catalog, q, noise_cfg, rng, sensor)
        ok = (
            rec["attitude_solved"]
            and not rec["false_id_flag"]
            and rec["id_rate"] >= min_id_rate
        )
        covered += int(ok)
        rec.update(point=i, covered=ok)
        records.append(rec)
    return {
        "coverage": covered / n_points,
        "n_points": n_points,
        "db_bytes": db_bytes,
        "records": records,
    }


def write_csv(records: list[dict[str, Any]], path: Path) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    """Oracle ile uçtan uca demo: Monte Carlo + full-sky, CSV + plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .algorithms.oracle import OracleAlgorithm

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Katalog yükleniyor (Hipparcos Mv<6)...")
    catalog = load_catalog()
    print(f"  {len(catalog)} yıldız.")

    algo = OracleAlgorithm()

    # 1) Sabit attitude, gürültülü Monte Carlo
    rng = np.random.default_rng(42)
    q0 = random_quat(rng)
    noise = NoiseConfig(sigma_centroid_arcsec=10.0, sigma_mag=0.1, n_spikes=3, p_missing=0.1)
    mc = run_monte_carlo(algo, catalog, q0, noise, n_trials=200, seed=1)
    write_csv(mc, RESULTS_DIR / "oracle_montecarlo.csv")
    id_rates = np.array([r["id_rate"] for r in mc])
    err = np.array([r["attitude_error_arcsec"] for r in mc])
    print(f"  MC: ort id_rate={id_rates.mean():.3f}, "
          f"false_id={sum(r['false_id_flag'] for r in mc)}/{len(mc)}")

    # 2) Full-sky coverage
    fs = run_full_sky(algo, catalog, NOISELESS, n_points=300, seed=7)
    write_csv(fs["records"], RESULTS_DIR / "oracle_fullsky.csv")
    print(f"  Full-sky coverage (oracle, gürültüsüz): {fs['coverage']*100:.1f}%")

    # plotlar
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].hist(id_rates, bins=20, color="steelblue")
    ax[0].set(title="Oracle id_rate (gürültülü MC)", xlabel="id_rate", ylabel="trials")
    finite = err[np.isfinite(err)]
    ax[1].hist(finite, bins=20, color="indianred")
    ax[1].set(title="Attitude hatası", xlabel="arcsec", ylabel="trials")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "oracle_summary.png", dpi=120)
    print(f"  Çıktılar: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
