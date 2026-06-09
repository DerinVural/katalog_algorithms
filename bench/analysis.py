"""Brief raporu analiz seti — yeniden kullanılabilir.

Herhangi bir `StarIDAlgorithm` alıp brief raporunun standart analizlerini üretir:
  1. DB dökümü (insan-birimli CSV)        -> dump_database
  2. Zamanlama (build / extract / match)  -> measure_timing
  3. Zamanlama grafiği (süre vs gözlem)   -> plot_timing
  4. Gürültü grace eğrisi (CSV + PNG)     -> grace_curve
  5. Sahne görseli                        -> scene_figure
  -> run_full_analysis hepsini koşar, artefaktları results/ altına yazar,
     rapora gömülecek özet sözlüğü döndürür.

Algoritmaya özel hiçbir varsayım yok: yalnız build_database / extract_features /
match protokolü ve DB'nin (dataclass ya da __dict__) eşit-uzunluklu numpy alanları
kullanılır. Mutlak süreler makine yüküne duyarlıdır — anlamlı olan algoritmalar
arası GÖRELİ kıyastır.
"""
from __future__ import annotations

import csv
import time
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .core.catalog import load_catalog
from .core.interfaces import Catalog
from .core.quest import random_quat, rotate
from .core.scene import NOISELESS, NoiseConfig, simulate_scene
from .core.sensor import SENSOR, SensorProfile
from .runner import build, run_trial, write_csv

RESULTS_DIR = Path(__file__).resolve().parent / "results"
_ARCSEC = 180.0 * 3600.0 / np.pi


# --------------------------------------------------------------------- yardımcı
def count_visible(catalog: Catalog, q: np.ndarray, sensor: SensorProfile = SENSOR) -> int:
    u = rotate(q, catalog.vectors)
    return int(np.sum((u[:, 2] > 0) & (u[:, 2] >= np.cos(sensor.fov_radius_rad))))


def find_rich_attitude(catalog: Catalog, min_stars: int = 8, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    for _ in range(5000):
        q = random_quat(rng)
        if count_visible(catalog, q) >= min_stars:
            return q
    raise RuntimeError(f"{min_stars} yıldızlı attitude bulunamadı.")


def _db_array_fields(db: Any) -> dict[str, np.ndarray]:
    """DB nesnesinden eşit-uzunluklu numpy alanlarını topla (dataclass/__dict__).

    1-D alanlar olduğu gibi; 2-D (M,k) alanlar k sütuna açılır (ör. key -> key0..)."""
    if is_dataclass(db):
        items = {f.name: getattr(db, f.name) for f in fields(db)}
    elif hasattr(db, "__dict__"):
        items = dict(vars(db))
    else:
        items = {}
    arrays = {k: np.asarray(v) for k, v in items.items()
              if isinstance(v, np.ndarray) and v.ndim in (1, 2)}
    if not arrays:
        return {}
    n = max(v.shape[0] for v in arrays.values())
    out: dict[str, np.ndarray] = {}
    for k, v in arrays.items():
        if v.shape[0] != n:
            continue
        if v.ndim == 1:
            out[k] = v
        else:
            for c in range(v.shape[1]):
                out[f"{k}{c}"] = v[:, c]
    return out


# --------------------------------------------------------------------- 1) DB
def dump_database(
    db: Any,
    path: Path,
    transforms: dict[str, Callable[[np.ndarray], np.ndarray]] | None = None,
) -> dict[str, Any]:
    """DB'nin numpy alanlarını CSV'ye dök. `transforms` ile birim çevir
    (ör. {'d1': lambda x: x*ARCSEC}). Özet döndürür."""
    cols = _db_array_fields(db)
    if not cols:
        return {"n_records": 0, "path": None, "columns": []}
    transforms = transforms or {}
    names = list(cols.values())[0]
    n = len(names)
    out_cols = {k: (transforms[k](v) if k in transforms else v) for k, v in cols.items()}

    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(out_cols.keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["idx"] + keys)
        for i in range(n):
            w.writerow([i] + [
                (round(float(out_cols[k][i]), 3)
                 if np.issubdtype(out_cols[k].dtype, np.floating)
                 else int(out_cols[k][i]))
                for k in keys
            ])
    return {"n_records": n, "path": str(path), "columns": keys,
            "size_kb": round(path.stat().st_size / 1024, 1)}


# --------------------------------------------------------------- 2) zamanlama
def _best(fn, *args, reps: int = 3) -> tuple[Any, float]:
    """En iyi (en küçük) süreyi döndür — geçici yük sıçramalarını filtreler."""
    best = np.inf
    out = None
    for _ in range(reps):
        t0 = time.perf_counter()
        out = fn(*args)
        dt = time.perf_counter() - t0
        best = min(best, dt)
    return out, best


def measure_timing(
    algo: Any,
    catalog: Catalog,
    noise_cfg: NoiseConfig | None = None,
    n_scenes: int = 150,
    reps: int = 3,
    warmup: int = 20,
    seed: int = 0,
) -> dict[str, Any]:
    if noise_cfg is None:
        noise_cfg = NoiseConfig(sigma_centroid_arcsec=5.0, n_spikes=3)

    # build_database (tek seferlik) — ayrı ölç
    _, t_build = _best(algo.build_database, catalog, reps=max(1, reps - 1))
    db = algo.build_database(catalog)

    rng = np.random.default_rng(seed)
    scenes = []
    while len(scenes) < n_scenes:
        q = random_quat(rng)
        obs, _ = simulate_scene(catalog, q, noise_cfg, rng=rng)
        if len(obs) >= 3:
            scenes.append(obs)

    for obs in scenes[:warmup]:                      # ısınma
        algo.match(algo.extract_features(obs), db)

    nobs, ext_ms, mat_ms = [], [], []
    for obs in scenes:
        _, te = _best(algo.extract_features, obs, reps=reps)
        feats = algo.extract_features(obs)
        _, tm = _best(algo.match, feats, db, reps=reps)
        nobs.append(len(obs)); ext_ms.append(te * 1e3); mat_ms.append(tm * 1e3)

    nobs = np.array(nobs); ext_ms = np.array(ext_ms)
    mat_ms = np.array(mat_ms); tot_ms = ext_ms + mat_ms

    def stat(x):
        return {"median": float(np.median(x)), "mean": float(np.mean(x)),
                "min": float(np.min(x)), "max": float(np.max(x))}

    return {
        "build_ms": t_build * 1e3,
        "n_scenes": len(scenes),
        "nobs": nobs, "extract_ms": ext_ms, "match_ms": mat_ms, "total_ms": tot_ms,
        "nobs_median": int(np.median(nobs)),
        "extract": stat(ext_ms), "match": stat(mat_ms), "total": stat(tot_ms),
    }


def plot_timing(timing: dict[str, Any], path: Path, name: str = "algo") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nobs = timing["nobs"]; tot = timing["total_ms"]
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.scatter(nobs, timing["extract_ms"], s=15, alpha=.35, c="tab:blue", label="extract_features")
    ax.scatter(nobs, timing["match_ms"], s=15, alpha=.35, c="tab:green", label="match (DB arama)")
    ax.scatter(nobs, tot, s=17, alpha=.5, c="tab:red", label="toplam")
    bins = np.arange(nobs.min(), nobs.max() + 2, 3); cx, cy = [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (nobs >= lo) & (nobs < hi)
        if m.sum() >= 3:
            cx.append((lo + hi) / 2); cy.append(np.median(tot[m]))
    if cx:
        ax.plot(cx, cy, "k-", lw=2, label="toplam medyan")
    ax.set(xlabel="sahnedeki gözlem sayısı", ylabel="süre [ms] (best-of-%d)" % 3,
           title=f"{name} eşleştirme süresi vs gözlem sayısı")
    ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130); plt.close(fig)


# ------------------------------------------------------------- 4) grace eğrisi
def grace_curve(
    algo: Any,
    catalog: Catalog,
    attitude: np.ndarray,
    sigmas: tuple[float, ...] = (2, 5, 10, 20),
    n_trials: int = 15,
    seed: int = 1,
    plot_path: Path | None = None,
    name: str = "algo",
) -> list[dict[str, float]]:
    db, _ = build(algo, catalog)
    curve = []
    for sig in sigmas:
        cfg = NoiseConfig(sigma_centroid_arcsec=sig)
        rng = np.random.default_rng(seed)
        recs = [run_trial(algo, db, catalog, attitude, cfg, rng) for _ in range(n_trials)]
        curve.append({
            "sigma_arcsec": float(sig),
            "id_rate": float(np.mean([r["id_rate"] for r in recs])),
            "false_id_rate": float(np.mean([r["false_id_flag"] for r in recs])),
        })
    if plot_path is not None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([c["sigma_arcsec"] for c in curve], [c["id_rate"] for c in curve], "o-")
        ax.set(xlabel="centroid σ [arcsec]", ylabel="id_rate",
               title=f"{name} gürültü grace eğrisi", ylim=(0, 1.02))
        ax.grid(alpha=.3)
        fig.savefig(plot_path, dpi=120); plt.close(fig)
    return curve


# ----------------------------------------------------------------- 5) sahne
def scene_figure(
    catalog: Catalog,
    attitude: np.ndarray,
    noise_cfg: NoiseConfig,
    path: Path,
    seed: int = 0,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .visualize import visualize_scene

    fig, _, _, _ = visualize_scene(catalog, attitude, noise_cfg, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130); plt.close(fig)


# --------------------------------------------------------------- orkestrasyon
def run_full_analysis(
    algo: Any,
    catalog: Catalog | None = None,
    name: str | None = None,
    out_dir: Path = RESULTS_DIR,
    attitude: np.ndarray | None = None,
    db_transforms: dict[str, Callable] | None = None,
    n_scenes: int = 150,
) -> dict[str, Any]:
    """Tüm analiz setini koş, artefaktları yaz, rapora gömülecek özeti döndür.

    n_scenes: timing örnekleme sahnesi sayısı (pahalı algoritmalarda düşür)."""
    catalog = catalog if catalog is not None else load_catalog()
    name = name or getattr(algo, "name", "algo")
    attitude = attitude if attitude is not None else find_rich_attitude(catalog)
    out_dir.mkdir(parents=True, exist_ok=True)

    db = algo.build_database(catalog)
    db_summary = dump_database(db, out_dir / f"{name}_db.csv", db_transforms)

    timing = measure_timing(algo, catalog, n_scenes=n_scenes)
    plot_timing(timing, out_dir / f"{name}_timing.png", name=name)

    grace = grace_curve(algo, catalog, attitude,
                        plot_path=out_dir / f"{name}_grace.png", name=name)
    write_csv(grace, out_dir / f"{name}_grace.csv")

    scene_figure(catalog, attitude, NoiseConfig(sigma_centroid_arcsec=5.0, n_spikes=3),
                 out_dir / f"{name}_scene.png")

    summary = {
        "name": name,
        "n_catalog": len(catalog),
        "db": db_summary,
        "timing": {"build_ms": timing["build_ms"], "nobs_median": timing["nobs_median"],
                   "extract": timing["extract"], "match": timing["match"],
                   "total": timing["total"]},
        "grace": grace,
        "artifacts": [str(out_dir / f"{name}_{s}") for s in
                      ("db.csv", "timing.png", "grace.csv", "grace.png", "scene.png")],
    }
    return summary


def _print_summary(s: dict[str, Any]) -> None:
    print(f"=== {s['name']} analiz özeti (katalog {s['n_catalog']}) ===")
    db = s["db"]
    print(f"DB: {db['n_records']} kayıt, {db.get('size_kb','?')} KB -> {db['path']}")
    t = s["timing"]
    print(f"build_database: {t['build_ms']:.0f} ms (tek seferlik)")
    print(f"gözlem medyan: {t['nobs_median']}")
    print(f"extract medyan: {t['extract']['median']:.2f} ms | "
          f"match medyan: {t['match']['median']:.2f} ms | "
          f"toplam medyan: {t['total']['median']:.2f} ms")
    print("grace (sigma[arcsec] -> id_rate):")
    for c in s["grace"]:
        print(f"  sigma={c['sigma_arcsec']:>4.0f}  id_rate={c['id_rate']:.3f}  "
              f"false_id={c['false_id_rate']:.3f}")
    print("artefaktlar:")
    for a in s["artifacts"]:
        print("  ", a)


def main() -> None:
    """Örnek: Liebe için tam analiz."""
    from .algorithms.liebe import LiebeAlgorithm
    cat = load_catalog()
    transforms = {"d1": lambda x: x * _ARCSEC, "d2": lambda x: x * _ARCSEC,
                  "theta": lambda x: np.degrees(x)}
    s = run_full_analysis(LiebeAlgorithm(), cat, name="liebe", db_transforms=transforms)
    _print_summary(s)


if __name__ == "__main__":
    main()
