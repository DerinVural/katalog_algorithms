"""Kabul testi 4: QUEST gürültüsüz eşleşmeden attitude'u <1 arcsec geri kazanır."""
import numpy as np

from bench.algorithms.oracle import OracleAlgorithm
from bench.core.metrics import attitude_error
from bench.core.quest import quest
from bench.core.scene import NOISELESS, simulate_scene


def test_quest_recovers_attitude(catalog, rich_attitude):
    observed, truth = simulate_scene(catalog, rich_attitude, NOISELESS,
                                     rng=np.random.default_rng(0))
    algo = OracleAlgorithm()
    algo.set_truth(truth)
    cands = algo.match(observed, catalog)

    q_est = quest(cands, catalog, observed)
    assert q_est is not None
    total, _, _ = attitude_error(q_est, truth.q_true)
    assert total < 1.0, f"attitude hatası {total} arcsec"
