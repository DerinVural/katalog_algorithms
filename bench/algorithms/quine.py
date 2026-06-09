"""Quine (1996) — Liebe pattern'i + ikili-ağaç/KD-tree araması (brief 04).

Tek yenilik **arama**: Liebe'nin feature'ı ve O(n) kayıt seti aynen kullanılır
(liebe.py'den içe aktarılır), lineer tarama yerine `(d1, d2, theta)` öznitelik
uzayında ölçekli bir cKDTree üzerinde **kutu sorgusu** (Chebyshev, p=inf) yapılır
→ search O(n)'den O(lg n)'e iner. Sonuç Liebe ile **birebir aynı** olmalı.

Survey Tablo 1: Feature O(f·lg b), DB O(n) (Liebe ile aynı), search O(lg n).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.spatial import cKDTree

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.sensor import SENSOR, SensorProfile
from ..core.verify import ransac_confirm
from .liebe import LiebeAlgorithm, LiebeConfig, LiebeDB


@dataclass
class QuineConfig:
    tol_d_arcsec: float = 15.0
    tol_theta_deg: float = 0.5
    min_votes: int = 2
    neighbors_k: int = 3
    use_core_verify: bool = False        # Faz 2 ablation: +ortak doğrulayıcı
    verify_gate_arcsec: float = 60.0

    def liebe_config(self) -> LiebeConfig:
        return LiebeConfig(self.tol_d_arcsec, self.tol_theta_deg,
                           self.min_votes, self.neighbors_k)


@dataclass
class QuineDB:
    ldb: LiebeDB              # Liebe ile AYNI kayıtlar (d1,d2,theta,hip*)
    tree: cKDTree            # (d1,d2,theta) ölçekli öznitelik uzayı indeksi
    scale: np.ndarray        # (3,) eksen ölçekleri = 1/tol (kutu -> birim küp)
    catalog: Catalog         # opsiyonel core doğrulayıcı için


@dataclass
class QuineFeatures:
    liebe: list              # LiebeAlgorithm.extract_features çıktısı (aynen)
    observed: list           # BodyVector listesi (opsiyonel verify için)


class QuineAlgorithm:
    name = "quine"

    def __init__(self, config: QuineConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or QuineConfig()
        self.sensor = sensor
        # feature + kayıt + oylama mantığı Liebe'den miras (kopyalanmaz)
        self._liebe = LiebeAlgorithm(self.cfg.liebe_config(), sensor)

    @property
    def _scale(self) -> np.ndarray:
        td = self.cfg.tol_d_arcsec * np.pi / (180 * 3600)
        tt = np.radians(self.cfg.tol_theta_deg)
        return np.array([1.0 / td, 1.0 / td, 1.0 / tt])

    # --------------------------------------------------------------- DB O(n)
    def build_database(self, catalog: Catalog) -> QuineDB:
        ldb = self._liebe.build_database(catalog)            # AYNI kayıtlar
        scale = self._scale
        pts = np.column_stack([ldb.d1, ldb.d2, ldb.theta]) * scale
        return QuineDB(ldb=ldb, tree=cKDTree(pts), scale=scale, catalog=catalog)

    # --------------------------------------------------------- feature (miras)
    def extract_features(self, observed: Sequence[BodyVector]) -> QuineFeatures:
        obs = list(observed)
        return QuineFeatures(liebe=self._liebe.extract_features(obs), observed=obs)

    # --------------------------------------------------------- match O(lg n)
    def match(self, features: QuineFeatures, db: QuineDB) -> list[CandidateMatch]:
        cfg = self.cfg
        tol_d = cfg.tol_d_arcsec * np.pi / (180 * 3600)
        ldb, tree, scale = db.ldb, db.tree, db.scale
        votes: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))

        for (oc, on1, on2, d1, d2, theta) in features.liebe:
            orders = [(d1, d2, on1, on2)]
            if abs(d1 - d2) < tol_d:                          # Liebe ile aynı belirsizlik
                orders.append((d2, d1, on2, on1))
            for (qd1, qd2, qn1, qn2) in orders:
                qs = np.array([qd1, qd2, theta]) * scale
                # kutu sorgusu: Chebyshev (p=inf) yarıçap 1 = |Δ|<=tol her eksende
                idxs = tree.query_ball_point(qs, r=1.0, p=np.inf)
                for j in idxs:
                    votes[oc][int(ldb.hip_center[j])] += 1.0
                    votes[qn1][int(ldb.hip_n1[j])] += 1.0
                    votes[qn2][int(ldb.hip_n2[j])] += 1.0

        matches = self._liebe._resolve(votes)                 # Liebe ile AYNI oylama
        if cfg.use_core_verify:
            matches = ransac_confirm(matches, features.observed, db.catalog,
                                     gate_arcsec=cfg.verify_gate_arcsec)
        return matches
