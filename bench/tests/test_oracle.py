"""Kabul testi 5: oracle, runner üzerinden uçtan uca; id_rate=%100, false_id=0."""
import numpy as np

from bench.algorithms.oracle import OracleAlgorithm
from bench.core.scene import NoiseConfig
from bench.runner import run_monte_carlo


def test_oracle_end_to_end_noiseless(catalog, rich_attitude):
    algo = OracleAlgorithm()
    recs = run_monte_carlo(algo, catalog, rich_attitude, n_trials=30, seed=3)
    assert all(r["n_true"] > 0 for r in recs)
    assert all(r["id_rate"] == 1.0 for r in recs)
    assert all(r["false_id_flag"] is False for r in recs)
    assert all(r["n_wrong"] == 0 for r in recs)


def test_oracle_robust_to_noise(catalog, rich_attitude):
    # Oracle truth tabanlı: spike/eksik yıldız/centroid gürültüsünde de doğru.
    algo = OracleAlgorithm()
    cfg = NoiseConfig(sigma_centroid_arcsec=8.0, sigma_mag=0.1, n_spikes=4, p_missing=0.1)
    recs = run_monte_carlo(algo, catalog, rich_attitude, cfg, n_trials=30, seed=5)
    # spike'lar atılır, gerçek eşleşmeler doğru -> yanlış eşleşme yok, false-id yok
    assert all(r["n_wrong"] == 0 for r in recs)
    assert all(r["false_id_flag"] is False for r in recs)
