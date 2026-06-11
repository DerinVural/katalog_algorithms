"""Brief 06b İş 2 — geçmiş wrong_attitude sayılarının yeniden denetimi.

Faz 1-2'nin yayımlanmış wrong_attitude sayıları eski tek 60″ toplam-hata
kapısıyla üretildi. Bu script, phase1_compare ve phase2_spike_sweep koşularını
AYNI seed'lerle yeniden üretir ve her eski-kapı bayrağını yeni eksen-ayrık
kapıyla (cross 60″ / roll 600″, Liebe §V) yeniden sınıflandırır:

    hala_tehlikeli   : cross-ihlal veya aşırı-roll (yeni kapıda da bayraklı)
    saf_roll_aklanan : eski kapı bayraklamıştı; kimliği ilgilendirmeyen doğal
                       roll gürültüsü — yeni kapıda temiz

Çıktı: results/roll_audit.csv + konsol özeti. Tek seferlik denetim aracı.
Kullanım: python -m bench.audit_roll
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .algorithms.liebe import LiebeAlgorithm
from .algorithms.quine import QuineAlgorithm
from .algorithms.triangle_planar import TrianglePlanarAlgorithm
from .algorithms.sla_kvector import SLAAlgorithm
from .algorithms.pyramid import PyramidAlgorithm
from .compare import compare
from .core.catalog import load_catalog
from .core.metrics import FALSE_ID_CROSS_ARCSEC, FALSE_ID_ROLL_ARCSEC
from .core.scene import NoiseConfig
from .runner import run_monte_carlo, write_csv
from .tests.conftest import find_attitude_in_range

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OLD_GATE_ARCSEC = 60.0           # eski tek toplam-hata kapısı (denetim referansı)


def _classify(no_solution: bool, total: float, cross: float, roll: float) -> str:
    old_wa = (not no_solution) and total > OLD_GATE_ARCSEC
    new_wa = (not no_solution) and (
        cross > FALSE_ID_CROSS_ARCSEC or roll > FALSE_ID_ROLL_ARCSEC
    )
    if old_wa and new_wa:
        return "hala_tehlikeli"
    if old_wa and not new_wa:
        return "saf_roll_aklanan"
    if new_wa:
        return "yeni_yakalanan"      # teorik olarak boş (yeni ⊆ eski)
    return "temiz"


def main() -> None:
    catalog = load_catalog()
    audit_rows = []

    # --- Faz 1: phase1_compare (yayımlanan koşu: n_trials=100, seed=0) ---
    print("Faz 1 (phase1_compare) yeniden üretiliyor...")
    compare(catalog, n_trials=100, seed=0)       # csv'yi yeni metrikle de tazeler
    with (RESULTS_DIR / "phase1_compare.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cat_ = _classify(r["no_solution"] == "True",
                             float(r["attitude_error_arcsec"]),
                             float(r["cross_boresight_arcsec"]),
                             float(r["roll_arcsec"]))
            audit_rows.append({"context": "phase1", "algo": r["algo"],
                               "n_spikes": 3, "trial": r["trial"],
                               "total": round(float(r["attitude_error_arcsec"]), 1),
                               "cross": round(float(r["cross_boresight_arcsec"]), 1),
                               "roll": round(float(r["roll_arcsec"]), 1),
                               "category": cat_})

    # --- Faz 2: phase2_spike_sweep (T3 ile aynı kurgu: seed=11, 8 deneme) ---
    print("Faz 2 (phase2_spike_sweep kurgusu) yeniden üretiliyor...")
    q = find_attitude_in_range(catalog, 18, 26, 1)
    algos = {"liebe": LiebeAlgorithm(), "quine": QuineAlgorithm(),
             "triangle_planar": TrianglePlanarAlgorithm(),
             "sla_kvector": SLAAlgorithm(), "pyramid": PyramidAlgorithm()}
    for name, algo in algos.items():
        for ns in [0, 5, 20]:
            cfg = NoiseConfig(sigma_centroid_arcsec=5, n_spikes=ns)
            for rec in run_monte_carlo(algo, catalog, q, cfg, n_trials=8, seed=11):
                cat_ = _classify(rec["no_solution"], rec["attitude_error_arcsec"],
                                 rec["cross_boresight_arcsec"], rec["roll_arcsec"])
                audit_rows.append({"context": "phase2", "algo": name,
                                   "n_spikes": ns, "trial": rec["trial"],
                                   "total": round(rec["attitude_error_arcsec"], 1)
                                   if np.isfinite(rec["attitude_error_arcsec"]) else -1,
                                   "cross": round(rec["cross_boresight_arcsec"], 1)
                                   if np.isfinite(rec["cross_boresight_arcsec"]) else -1,
                                   "roll": round(rec["roll_arcsec"], 1)
                                   if np.isfinite(rec["roll_arcsec"]) else -1,
                                   "category": cat_})

    write_csv(audit_rows, RESULTS_DIR / "roll_audit.csv")

    # --- özet ---
    print("\n=== Roll denetimi özeti (eski 60\" toplam-kapi bayraklari) ===")
    for ctx in ("phase1", "phase2"):
        print(f"\n[{ctx}]")
        for algo in sorted({r["algo"] for r in audit_rows if r["context"] == ctx}):
            rows = [r for r in audit_rows if r["context"] == ctx and r["algo"] == algo]
            old_flagged = [r for r in rows if r["category"] in
                           ("hala_tehlikeli", "saf_roll_aklanan")]
            still = sum(1 for r in old_flagged if r["category"] == "hala_tehlikeli")
            acq = sum(1 for r in old_flagged if r["category"] == "saf_roll_aklanan")
            print(f"  {algo:16s}: eski-bayrak {len(old_flagged):3d}/{len(rows)} -> "
                  f"hala-tehlikeli {still}, saf-roll-aklanan {acq}")
    print(f"\nCSV: {RESULTS_DIR / 'roll_audit.csv'}")


if __name__ == "__main__":
    main()
