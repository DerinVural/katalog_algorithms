"""Brief 07b FINAL §8 — Non-Dim × Pyramid deney matrisi.

5 çizgi: Pyramid, Samaan, NonDimPyramid (B), TwoStage (C), NDSIA (D).
- Adım 0 / baseline: Pyramid + Samaan (zaten ızgarada koşuluyor).
- Düzlem 1: ppm × spike (OA=0) — H1-H5 + H6'nın f-ayağı.
- Düzlem 2: OA × spike (ppm=0) — H7 figürü.
- Köşe hücresi, işkence, maliyet, f* doğruluk.

Çıktılar: results/exp07b_grid.{csv,png}, exp07b_torture.csv, exp07b_cost.csv,
exp07b_h7.png, exp07b_focal.csv.

Kullanım: python -m bench.experiments.exp_07b_hybrid [N_TRIALS]
Algoritmalar yavaş (Kol B/D spike'ta saniyeler); N parametrik, varsayılan 12.
Tam çalıştırma (≥40) için CLI argümanı; uzun sürer (arka planda).
"""
from __future__ import annotations

import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from bench.algorithms.ndsia import NDSIAAlgorithm
from bench.algorithms.nondim_pyramid import NonDimPyramidAlgorithm
from bench.algorithms.pyramid import PyramidAlgorithm
from bench.algorithms.samaan_nondim import SamaanAlgorithm
from bench.algorithms.twostage_ndsia import TwoStageNDSIAAlgorithm
from bench.core.catalog import load_catalog
from bench.core.scene import NoiseConfig
from bench.runner import build, run_trial, write_csv
from bench.tests.conftest import find_attitude_in_range

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _algos():
    return {"pyramid": PyramidAlgorithm(), "samaan": SamaanAlgorithm(),
            "nondim_pyramid": NonDimPyramidAlgorithm(),
            "twostage": TwoStageNDSIAAlgorithm(), "ndsia": NDSIAAlgorithm()}


def _cell(algo, db, catalog, q, cfg, n, seed):
    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()
    recs = [run_trial(algo, db, catalog, q, cfg, rng) for _ in range(n)]
    dt = (time.perf_counter() - t0) / n
    return {"id_rate": float(np.mean([r["id_rate"] for r in recs])),
            "wrong_attitude_rate": float(np.mean([r["wrong_attitude"] for r in recs])),
            "no_solution_rate": float(np.mean([r["no_solution"] for r in recs])),
            "n_wrong_total": int(sum(r["n_wrong"] for r in recs)),
            "match_ms": dt * 1000}


def run_grid(n=12, seed=11):
    catalog = load_catalog()
    q = find_attitude_in_range(catalog, 12, 18, 0)
    algos = _algos()
    print("DB'ler kuruluyor...")
    dbs = {name: build(a, catalog)[0] for name, a in algos.items()}

    rows = []
    # Düzlem 1: ppm × spike (OA=0)
    for ppm in [0, 1500, 3000]:
        for spike in [0, 10, 30, 63]:
            cfg = NoiseConfig(sigma_centroid_arcsec=5, focal_error_ppm=ppm, n_spikes=spike)
            for name, a in algos.items():
                m = _cell(a, dbs[name], catalog, q, cfg, n, seed)
                m.update(plane="ppm_spike", algo=name, ppm=ppm, oa=0.0, spike=spike)
                rows.append(m)
                print(f"  P1 {name:15s} ppm={ppm:4d} spk={spike:2d}: id={m['id_rate']:.2f} "
                      f"wa={m['wrong_attitude_rate']:.2f} nosol={m['no_solution_rate']:.2f} "
                      f"({m['match_ms']:.0f}ms)")
    # Düzlem 2: OA × spike (ppm=0)
    for oa in [0.0, 0.005, 0.02]:
        for spike in [0, 30]:
            cfg = NoiseConfig(sigma_centroid_arcsec=5, oa_offset_error_frac=oa, n_spikes=spike)
            for name, a in algos.items():
                m = _cell(a, dbs[name], catalog, q, cfg, n, seed)
                m.update(plane="oa_spike", algo=name, ppm=0, oa=oa, spike=spike)
                rows.append(m)
                print(f"  P2 {name:15s} oa={oa:.3f} spk={spike:2d}: id={m['id_rate']:.2f} "
                      f"wa={m['wrong_attitude_rate']:.2f} ({m['match_ms']:.0f}ms)")
    write_csv(rows, RESULTS / "exp07b_grid.csv")
    _plot_grid(rows)
    return rows


def _plot_grid(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    p1 = [r for r in rows if r["plane"] == "ppm_spike" and r["spike"] == 0]
    p2 = [r for r in rows if r["plane"] == "oa_spike" and r["spike"] == 0]
    algos = sorted({r["algo"] for r in rows})
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    for name in algos:
        a1 = sorted([r for r in p1 if r["algo"] == name], key=lambda r: r["ppm"])
        ax[0].plot([r["ppm"] for r in a1], [r["id_rate"] for r in a1], "o-", label=name)
        a2 = sorted([r for r in p2 if r["algo"] == name], key=lambda r: r["oa"])
        ax[1].plot([r["oa"] * 100 for r in a2], [r["id_rate"] for r in a2], "o-", label=name)
    ax[0].set(xlabel="focal_error_ppm", ylabel="id_rate (σ=5″, spike=0)",
              title="Düzlem 1: kalibrasyon (f) ekseni")
    ax[1].set(xlabel="OA ofseti (% yarı-imager)", ylabel="id_rate",
              title="Düzlem 2 / H7: OA ekseni")
    for a in ax:
        a.grid(alpha=.3); a.legend(fontsize=8); a.set_ylim(-0.02, 1.05)
    fig.tight_layout(); fig.savefig(RESULTS / "exp07b_h7.png", dpi=130); plt.close(fig)

    # manşet ısı haritası: id_rate, ppm×spike, 5 panel
    fig, axes = plt.subplots(1, 5, figsize=(18, 3.4))
    ppms = [0, 1500, 3000]; spikes = [0, 10, 30, 63]
    for ax_, name in zip(axes, algos):
        M = np.full((len(ppms), len(spikes)), np.nan)
        for r in rows:
            if r["plane"] == "ppm_spike" and r["algo"] == name:
                M[ppms.index(r["ppm"]), spikes.index(r["spike"])] = r["id_rate"]
        im = ax_.imshow(M, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax_.set(title=name, xticks=range(len(spikes)), xticklabels=spikes,
                yticks=range(len(ppms)), yticklabels=ppms,
                xlabel="spike", ylabel="ppm")
    fig.colorbar(im, ax=axes, fraction=0.012, label="id_rate")
    fig.suptitle("Manşet: id_rate ısı haritası (Düzlem 1: ppm × spike)")
    fig.savefig(RESULTS / "exp07b_grid.png", dpi=120); plt.close(fig)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    print(f"=== Brief 07b ızgara deneyi (N={n}/hücre) ===")
    run_grid(n=n)
    print("DONE")


if __name__ == "__main__":
    main()
