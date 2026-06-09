"""Liebe (1992) — merkez yıldız + 2 en yakın komşu pattern'i (brief 02).

Feature: (d1, d2, theta)
    d1, d2 = merkeze en yakın 2 yıldızın açısal uzaklığı (rad), d1 <= d2
    theta  = bu iki komşunun merkez yıldızdaki iç açısı (rad)
DB: yıldız başına bir kayıt -> O(n). search: lineer (d1'e göre sıralı dizide
pencere daraltma). Eşleşmeler oylanır; çoğunluk tutarlı kümeyi seçer.

Survey Tablo 1 hedefi: Feature O(f·lg b), DB O(n), search O(n).
Magnitude KULLANILMAZ (survey: "neglecting the stellar magnitudes").
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Sequence

import numpy as np

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.sensor import SENSOR, SensorProfile

_ARCSEC = np.pi / (180.0 * 3600.0)


@dataclass
class LiebeConfig:
    tol_d_arcsec: float = 15.0     # uzaklık toleransı (~birkaç × centroid hatası)
    tol_theta_deg: float = 0.5     # iç açı toleransı
    min_votes: int = 2             # belirsizlikte kabul için min oy
    neighbors_k: int = 3           # en yakın K komşunun ikili kombinasyonları
    # K>2: FOV-kenarı komşu kaybına karşı dayanıklılık. DB hâlâ O(n)
    # (yıldız başına C(K,2) sabit kayıt). Magnitude yine kullanılmaz.

    @property
    def tol_d_rad(self) -> float:
        return self.tol_d_arcsec * _ARCSEC

    @property
    def tol_theta_rad(self) -> float:
        return np.radians(self.tol_theta_deg)


@dataclass
class LiebeDB:
    d1: np.ndarray         # (m,) sıralı
    d2: np.ndarray
    theta: np.ndarray
    hip_center: np.ndarray
    hip_n1: np.ndarray
    hip_n2: np.ndarray
    n_records: int


def _angular_dist(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """u (3,) ile v (...,3) arasında açısal uzaklık (rad)."""
    return np.arccos(np.clip(v @ u, -1.0, 1.0))


def _interior_angle(c: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Merkez c'de, a ve b komşularına olan yönler arasındaki iç açı (rad).

    Yönler c'deki teğet düzleme izdüşürülür (büyük-çember bearing'i).
    """
    ta = a - (a @ c) * c
    tb = b - (b @ c) * c
    na, nb = np.linalg.norm(ta), np.linalg.norm(tb)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.arccos(np.clip((ta @ tb) / (na * nb), -1.0, 1.0)))


def _feature_from_neighbors(c, a, b):
    """(d1, d2, theta, swap) — a,b komşu vektörleri; en yakın önce sıralanır."""
    da = float(_angular_dist(c, a[None, :])[0])
    db = float(_angular_dist(c, b[None, :])[0])
    if da <= db:
        d1, d2, n1, n2 = da, db, a, b
        swapped = False
    else:
        d1, d2, n1, n2 = db, da, b, a
        swapped = True
    theta = _interior_angle(c, n1, n2)
    return d1, d2, theta, swapped


class LiebeAlgorithm:
    name = "liebe"

    def __init__(self, config: LiebeConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or LiebeConfig()
        self.sensor = sensor

    # ------------------------------------------------------------------ DB
    def build_database(self, catalog: Catalog) -> LiebeDB:
        vecs = catalog.vectors
        hips = catalog.hip_ids
        fov_r = self.sensor.fov_radius_rad
        K = self.cfg.neighbors_k

        # her yıldız için en yakın K (kendisi hariç); kombinasyonlardan pattern
        chord, idx = catalog.kdtree.query(vecs, k=K + 1)
        recs_d1, recs_d2, recs_th = [], [], []
        recs_c, recs_n1, recs_n2 = [], [], []

        for i in range(len(vecs)):
            cand = [j for j in idx[i] if j != i][:K]
            if len(cand) < 2:
                continue
            c = vecs[i]
            for ja, jb in combinations(cand, 2):
                d1, d2, theta, swapped = _feature_from_neighbors(c, vecs[ja], vecs[jb])
                # iki komşu da FOV yarıçapı içinde olmalı (birlikte görünür)
                if d2 > fov_r:
                    continue
                hn1, hn2 = (ja, jb) if not swapped else (jb, ja)
                recs_d1.append(d1); recs_d2.append(d2); recs_th.append(theta)
                recs_c.append(hips[i]); recs_n1.append(hips[hn1]); recs_n2.append(hips[hn2])

        d1 = np.array(recs_d1); order = np.argsort(d1)
        return LiebeDB(
            d1=d1[order],
            d2=np.array(recs_d2)[order],
            theta=np.array(recs_th)[order],
            hip_center=np.array(recs_c, dtype=np.int64)[order],
            hip_n1=np.array(recs_n1, dtype=np.int64)[order],
            hip_n2=np.array(recs_n2, dtype=np.int64)[order],
            n_records=len(recs_d1),
        )

    # -------------------------------------------------------------- feature
    def extract_features(self, observed: Sequence[BodyVector]) -> list[tuple]:
        obs = list(observed)
        n = len(obs)
        if n < 3:
            return []
        U = np.array([o.u_body for o in obs])
        ids = [o.obs_id for o in obs]
        K = self.cfg.neighbors_k
        feats = []
        for i in range(n):
            d = _angular_dist(U[i], U)        # (n,)
            d[i] = np.inf
            nn = np.argsort(d)[:K]
            nn = [j for j in nn if np.isfinite(d[j])]
            for ja, jb in combinations(nn, 2):
                d1, d2, theta, swapped = _feature_from_neighbors(U[i], U[ja], U[jb])
                o1, o2 = (ja, jb) if not swapped else (jb, ja)
                feats.append((ids[i], ids[o1], ids[o2], d1, d2, theta))
        return feats

    # ---------------------------------------------------------------- match
    def match(self, features: list[tuple], db: LiebeDB) -> list[CandidateMatch]:
        cfg = self.cfg
        tol_d, tol_t = cfg.tol_d_rad, cfg.tol_theta_rad
        votes: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))

        for (oc, on1, on2, d1, d2, theta) in features:
            # d1≈d2 belirsizliği: her iki sıralamayı da dene
            orders = [(d1, d2, on1, on2)]
            if abs(d1 - d2) < tol_d:
                orders.append((d2, d1, on2, on1))

            for (qd1, qd2, qn1, qn2) in orders:
                lo = np.searchsorted(db.d1, qd1 - tol_d, side="left")
                hi = np.searchsorted(db.d1, qd1 + tol_d, side="right")
                if hi <= lo:
                    continue
                sl = slice(lo, hi)
                ok = (
                    (np.abs(db.d2[sl] - qd2) < tol_d)
                    & (np.abs(db.theta[sl] - theta) < tol_t)
                )
                for k in np.nonzero(ok)[0]:
                    j = lo + k
                    # merkez + komşu eşleşmeleri için oy (çoğunluk oylaması)
                    votes[oc][int(db.hip_center[j])] += 1.0
                    votes[qn1][int(db.hip_n1[j])] += 1.0
                    votes[qn2][int(db.hip_n2[j])] += 1.0

        return self._resolve(votes)

    def _resolve(self, votes) -> list[CandidateMatch]:
        """Her obs için en çok oyu alan hip'i seç; min_votes ya da tek-aday
        koşulu; sonra hip başına tek obs (global birebir) zorla."""
        min_votes = self.cfg.min_votes
        tentative: list[tuple[int, int, float]] = []  # (obs, hip, votes)
        for obs_id in sorted(votes):
            cand = votes[obs_id]
            best_hip = max(cand, key=lambda h: cand[h])
            best_v = cand[best_hip]
            second = sorted(cand.values(), reverse=True)
            unique = len(cand) == 1 or best_v > second[1]
            if unique and (best_v >= min_votes or len(cand) == 1):
                tentative.append((obs_id, best_hip, best_v))

        # global birebir: bir hip birden çok obs tarafından seçildiyse en çok oylu kalır
        best_for_hip: dict[int, tuple[int, float]] = {}
        for obs_id, hip, v in tentative:
            if hip not in best_for_hip or v > best_for_hip[hip][1]:
                best_for_hip[hip] = (obs_id, v)
        keep = {(obs_id, hip) for hip, (obs_id, _) in best_for_hip.items()}

        return [
            CandidateMatch(obs_id=obs_id, hip_id=hip, confidence=float(v))
            for (obs_id, hip, v) in tentative
            if (obs_id, hip) in keep
        ]
