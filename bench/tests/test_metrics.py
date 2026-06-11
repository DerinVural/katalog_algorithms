"""Kabul testi 6: elle kurulmuş vakada id_rate / false_id doğru hesaplanır."""
import numpy as np
from scipy.spatial.transform import Rotation

from bench.core.interfaces import CandidateMatch, SceneTruth
from bench.core.metrics import attitude_error, db_size_bytes, evaluate, timed


def _truth():
    q = Rotation.from_euler("xyz", [10, 20, 30], degrees=True).as_quat()
    return SceneTruth(q_true=q, true_matches={0: 100, 1: 200, 2: 300})


def test_evaluate_handbuilt():
    truth = _truth()
    # obs 0,1 doğru; obs 2 yanlış hip; obs 5 spike (truth'ta yok) eşleştirildi
    cands = [
        CandidateMatch(0, 100),
        CandidateMatch(1, 200),
        CandidateMatch(2, 999),  # yanlış
        CandidateMatch(5, 400),  # spike
    ]
    res = evaluate(truth.q_true, cands, truth)  # q_est = q_true -> hata ~0
    assert res.n_true == 3
    assert res.n_correct == 2
    assert res.id_rate == 2 / 3
    assert res.n_wrong == 2          # yanlış hip + spike
    assert res.false_id_flag is False  # attitude doğru


def test_attitude_error_zero():
    truth = _truth()
    total, cross, roll = attitude_error(truth.q_true, truth.q_true)
    assert total < 1e-6


def test_attitude_error_known_roll():
    # boresight (z) etrafında 100 arcsec roll
    roll_arcsec = 100.0
    q_true = np.array([0, 0, 0, 1.0])
    ang = np.radians(roll_arcsec / 3600.0)
    q_est = Rotation.from_rotvec([0, 0, ang]).as_quat()
    total, cross, roll = attitude_error(q_est, q_true)
    assert abs(roll - roll_arcsec) < 1e-3
    assert cross < 1e-6


def test_false_id_flag_on_bad_attitude():
    truth = _truth()
    bad = Rotation.from_euler("xyz", [10, 20, 35], degrees=True).as_quat()  # 5° sapma
    res = evaluate(bad, [CandidateMatch(0, 100)], truth)   # 5°=18000″ roll >> 600″
    assert res.false_id_flag is True


# --- brief 06b: eksen-ayrık kapı kabul testleri (Liebe §V) ---

def _est_with_error(q_true, cross_arcsec, roll_arcsec):
    """q_true'dan gövde çerçevesinde (cross, roll) hatalı kestirim üret."""
    rad = np.pi / (180.0 * 3600.0)
    dR = Rotation.from_rotvec([cross_arcsec * rad, 0.0, roll_arcsec * rad])
    return (dR * Rotation.from_quat(q_true)).as_quat()


def test_06b_pure_roll_acquitted():
    # saf-roll (cross=5″, roll=90″): ESKİ tek 60″ toplam-kapıda True olurdu;
    # eksen-ayrık kapıda (60″/600″) artık tehlikeli DEĞİL — 06a karşı-bulgusunun çözümü.
    truth = _truth()
    res = evaluate(_est_with_error(truth.q_true, 5.0, 90.0), [CandidateMatch(0, 100)], truth)
    assert res.wrong_attitude is False
    assert res.attitude_error_arcsec > 60.0          # eski kapı bayraklardı (belge)


def test_06b_cross_violation_flagged():
    truth = _truth()
    res = evaluate(_est_with_error(truth.q_true, 70.0, 10.0), [CandidateMatch(0, 100)], truth)
    assert res.wrong_attitude is True                # cross > 60″


def test_06b_extreme_roll_flagged():
    truth = _truth()
    res = evaluate(_est_with_error(truth.q_true, 5.0, 700.0), [CandidateMatch(0, 100)], truth)
    assert res.wrong_attitude is True                # roll > 600″


def test_timed_and_dbsize():
    out, dt = timed(lambda x: x * 2, 21)
    assert out == 42 and dt >= 0
    assert db_size_bytes({"a": np.zeros(100)}) >= 800
