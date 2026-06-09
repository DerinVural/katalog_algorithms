"""Değerlendirme metrikleri (PROJECT_PLAN.md §5).

- evaluate: id-rate, false-id, attitude hatası (cross-boresight & roll ayrı).
- timed: süre ölçümü.
- db_size_bytes: DB bellek boyutu (derin).
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Callable

import numpy as np
from scipy.spatial.transform import Rotation

from .interfaces import CandidateMatch, SceneTruth

# Bu eşiğin üzerindeki toplam attitude hatası "yanlış attitude" (false-ID) sayılır.
FALSE_ID_THRESHOLD_ARCSEC = 60.0

_ARCSEC_PER_RAD = 180.0 * 3600.0 / np.pi


@dataclass
class TrialResult:
    id_rate: float
    false_id_flag: bool
    n_true: int
    n_correct: int
    n_wrong: int
    attitude_error_arcsec: float        # toplam
    cross_boresight_arcsec: float
    roll_arcsec: float


def attitude_error(q_est: np.ndarray | None, q_true: np.ndarray) -> tuple[float, float, float]:
    """(toplam, cross-boresight, roll) hatası arcsec.

    Hata rotasyonu gövde çerçevesinde: δR = R_est @ R_trueᵀ. Rotasyon
    vektörünün z (boresight) bileşeni = roll, dik bileşeni = cross-boresight.
    """
    if q_est is None or np.any(~np.isfinite(q_est)):
        return (np.inf, np.inf, np.inf)
    R_est = Rotation.from_quat(q_est).as_matrix()
    R_true = Rotation.from_quat(q_true).as_matrix()
    dR = R_est @ R_true.T
    rv = Rotation.from_matrix(dR).as_rotvec()      # radyan, gövde çerçevesi
    roll = abs(rv[2])
    cross = np.hypot(rv[0], rv[1])
    total = np.linalg.norm(rv)
    return (total * _ARCSEC_PER_RAD, cross * _ARCSEC_PER_RAD, roll * _ARCSEC_PER_RAD)


def evaluate(
    q_est: np.ndarray | None,
    cands: list[CandidateMatch],
    truth: SceneTruth,
    false_id_threshold_arcsec: float = FALSE_ID_THRESHOLD_ARCSEC,
) -> TrialResult:
    cand_map: dict[int, int] = {c.obs_id: c.hip_id for c in cands}
    true_matches = truth.true_matches
    n_true = len(true_matches)

    n_correct = sum(
        1 for obs_id, hip in true_matches.items() if cand_map.get(obs_id) == hip
    )
    # yanlış: gerçek yıldıza yanlış hip, ya da spike'a (truth'ta yok) atanan eşleşme
    n_wrong = 0
    for obs_id, hip in cand_map.items():
        if obs_id in true_matches:
            if true_matches[obs_id] != hip:
                n_wrong += 1
        else:
            n_wrong += 1  # spike eşleştirildi

    id_rate = n_correct / n_true if n_true > 0 else 0.0
    total_err, cross_err, roll_err = attitude_error(q_est, truth.q_true)
    false_id_flag = (not np.isfinite(total_err)) or (total_err > false_id_threshold_arcsec)

    return TrialResult(
        id_rate=id_rate,
        false_id_flag=bool(false_id_flag),
        n_true=n_true,
        n_correct=n_correct,
        n_wrong=n_wrong,
        attitude_error_arcsec=total_err,
        cross_boresight_arcsec=cross_err,
        roll_arcsec=roll_err,
    )


def timed(fn: Callable, *args, **kwargs) -> tuple[Any, float]:
    """(sonuç, süre[s]) — perf_counter ile."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - t0


def db_size_bytes(obj: Any, _seen: set[int] | None = None) -> int:
    """Bir nesnenin yaklaşık derin bellek boyutu (byte).

    numpy dizileri .nbytes ile; dict/list/tuple/set/dataclass özyinelemeli.
    """
    if _seen is None:
        _seen = set()
    oid = id(obj)
    if oid in _seen:
        return 0
    _seen.add(oid)

    if isinstance(obj, np.ndarray):
        return int(obj.nbytes)

    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        for k, v in obj.items():
            size += db_size_bytes(k, _seen) + db_size_bytes(v, _seen)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for item in obj:
            size += db_size_bytes(item, _seen)
    elif is_dataclass(obj) and not isinstance(obj, type):
        for f in fields(obj):
            size += db_size_bytes(getattr(obj, f.name), _seen)
    elif hasattr(obj, "__dict__"):
        size += db_size_bytes(vars(obj), _seen)
    return size
