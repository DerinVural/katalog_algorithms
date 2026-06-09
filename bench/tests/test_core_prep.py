"""Kabul testleri — Faz 2 öncesi core hazırlığı (brief 03b)."""
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from bench.core import verify
from bench.core.interfaces import CandidateMatch, SceneTruth
from bench.core.metrics import evaluate
from bench.core.scene import NOISELESS, simulate_scene
from bench.core.verify import ransac_confirm


def _truth():
    q = Rotation.from_euler("xyz", [10, 20, 30], degrees=True).as_quat()
    return SceneTruth(q_true=q, true_matches={0: 100, 1: 200, 2: 300})


# 1) çözümsüzlük: q_est=None -> no_solution True, wrong_attitude/false_id False
def test_metric_no_solution():
    res = evaluate(None, [], _truth())
    assert res.no_solution is True
    assert res.wrong_attitude is False
    assert res.false_id_flag is False


# 2) yanlış attitude: çözüldü ama 90° sapık -> wrong_attitude True, false_id True
def test_metric_wrong_attitude():
    truth = _truth()
    bad = (Rotation.from_rotvec([0, 0, np.pi / 2]) * Rotation.from_quat(truth.q_true)).as_quat()
    res = evaluate(bad, [CandidateMatch(0, 100)], truth)
    assert res.no_solution is False
    assert res.wrong_attitude is True
    assert res.false_id_flag is True


# 3) iyi durum: doğru attitude -> üçü de False
def test_metric_good():
    truth = _truth()
    res = evaluate(truth.q_true, [CandidateMatch(0, 100), CandidateMatch(1, 200)], truth)
    assert res.no_solution is False
    assert res.wrong_attitude is False
    assert res.false_id_flag is False


# 4) doğrulayıcı aykırı değeri eler; <3 tutarlı kalırsa []
def test_verify_prunes_outlier(catalog, rich_attitude):
    observed, truth = simulate_scene(catalog, rich_attitude, NOISELESS,
                                     rng=np.random.default_rng(0))
    correct = [CandidateMatch(o, h) for o, h in list(truth.true_matches.items())[:6]]
    some_hip = correct[0].hip_id
    other_obs = correct[5].obs_id
    outlier = CandidateMatch(other_obs, some_hip + 12345)        # uydurma hip
    # 5 doğru + 1 aykırı -> aykırı elenir, doğrular kalır
    matches = correct[:5] + [outlier]
    out = ransac_confirm(matches, observed, catalog)
    out_pairs = {(m.obs_id, m.hip_id) for m in out}
    assert (outlier.obs_id, outlier.hip_id) not in out_pairs
    assert len(out) >= 3

    # 2 doğru + 1 antipodal (uzak, katalogda var) aykırı -> tutarlı küme <3 -> []
    ref = catalog.by_id(correct[0].hip_id).u_inertial
    far_hip = next(s.hip_id for s in catalog.stars if float(s.u_inertial @ ref) < -0.5)
    degenerate = correct[:2] + [CandidateMatch(correct[2].obs_id, far_hip)]
    assert ransac_confirm(degenerate, observed, catalog) == []


# 5) doğrulayıcı truth erişimi içermez (grep)
def test_verify_no_truth_access():
    src = Path(verify.__file__).read_text(encoding="utf-8")
    assert "true_matches" not in src
    assert "SceneTruth" not in src
    assert ".q_true" not in src
