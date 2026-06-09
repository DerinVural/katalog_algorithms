"""Kabul testi 3: gürültüsüz sahnede gözlenen çift açıları katalogla eşleşir."""
import numpy as np

from bench.core.scene import NOISELESS, simulate_scene

ARCSEC = np.pi / (180.0 * 3600.0)


def test_scene_angles_match_catalog(catalog, rich_attitude):
    observed, truth = simulate_scene(catalog, rich_attitude, NOISELESS,
                                     rng=np.random.default_rng(0))
    # en az birkaç gerçek yıldız
    assert len(truth.true_matches) >= 5

    by_obs = {o.obs_id: o for o in observed}
    ids = list(truth.true_matches.keys())
    max_err = 0.0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            oi, oj = ids[i], ids[j]
            ang_obs = np.arccos(np.clip(by_obs[oi].u_body @ by_obs[oj].u_body, -1, 1))
            ci = catalog.by_id(truth.true_matches[oi]).u_inertial
            cj = catalog.by_id(truth.true_matches[oj]).u_inertial
            ang_cat = np.arccos(np.clip(ci @ cj, -1, 1))
            max_err = max(max_err, abs(ang_obs - ang_cat))
    assert max_err / ARCSEC < 1.0, f"maks açı hatası {max_err/ARCSEC} arcsec"


def test_scene_spikes_not_in_truth(catalog, rich_attitude):
    from bench.core.scene import NoiseConfig
    cfg = NoiseConfig(n_spikes=5)
    observed, truth = simulate_scene(catalog, rich_attitude, cfg,
                                     rng=np.random.default_rng(1))
    # spike'lar truth'ta yok: gözlem sayısı > truth eşleşme sayısı
    assert len(observed) == len(truth.true_matches) + 5
