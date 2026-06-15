"""Kol C — LAM-stili iki-aşama (brief 07b v2): mod-anahtarlamalı mimari.

Aşama 1: non-dim bootstrap (SamaanAlgorithm.match, import — değiştirilmez).
Kalibrasyon kestirimi: eşleşmiş çiftlerin piksel geometrisinden 1-D en-küçük-
kareler ile f* (odak uzaklığı) kestirilir.
Aşama 2: gözlem body vektörleri f* ile pikselden YENİDEN türetilir; boyutlu
PyramidAlgorithm.match bu düzeltilmiş vektörlerle koşar (Pyramid değişmez).

Bilinen kırılganlık (gizlenmez, H5 ölçer): Aşama 1'in kimlik HATALARI f*
kestirimini zehirler -> Aşama 2 çöker.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

import numpy as np
from scipy.optimize import minimize_scalar

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.sensor import SENSOR, SensorProfile
from .pyramid import PyramidAlgorithm, PyramidConfig
from .samaan_nondim import SamaanAlgorithm, SamaanConfig


def _estimate_focal(matches: list[CandidateMatch],
                    observed: Sequence[BodyVector],
                    catalog: Catalog,
                    sensor: SensorProfile = SENSOR) -> float:
    """Eşleşmelerden odak uzaklığı kestirimi (piksel cinsinden f*).

    θ_obs(f): çift (i,j) için u_i(f)=norm([x_i,y_i,f]) vektörleri arasındaki
    açı; θ_cat katalogdan. f* = argmin Σ (θ_obs(f) − θ_cat)² — 1-D problem,
    sınırlı altın-oran araması (minimize_scalar). En az 2 eşleşme ister.
    """
    by_obs = {o.obs_id: o for o in observed}
    P, C = [], []
    for m in matches:
        o = by_obs.get(m.obs_id)
        if o is None:
            continue
        try:
            star = catalog.by_id(m.hip_id)
        except KeyError:
            continue
        P.append(o.centroid_px)
        C.append(star.u_inertial)
    if len(P) < 2:
        return sensor.focal_length_px
    P = np.array(P); C = np.array(C)
    pi, pj = np.triu_indices(len(P), 1)
    th_cat = np.arccos(np.clip(np.sum(C[pi] * C[pj], axis=1), -1, 1))

    def loss(fpx):
        V = np.column_stack([P, np.full(len(P), fpx)])
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        th_obs = np.arccos(np.clip(np.sum(V[pi] * V[pj], axis=1), -1, 1))
        d = th_obs - th_cat
        return float(d @ d)

    f0 = sensor.focal_length_px
    res = minimize_scalar(loss, bounds=(f0 * 0.99, f0 * 1.01), method="bounded",
                          options={"xatol": f0 * 1e-7})
    return float(res.x)


@dataclass
class TwoStageConfig:
    samaan: SamaanConfig = None        # None -> default
    pyramid: PyramidConfig = None


class TwoStageNDSIAAlgorithm:
    name = "twostage_ndsia"

    def __init__(self, config: TwoStageConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        cfg = config or TwoStageConfig()
        self.sensor = sensor
        self._samaan = SamaanAlgorithm(cfg.samaan, sensor)
        self._pyramid = PyramidAlgorithm(cfg.pyramid, sensor)
        self.last_focal_estimate_ppm: float = 0.0    # teşhis

    def build_database(self, catalog: Catalog):
        return {"samaan": self._samaan.build_database(catalog),
                "pyramid": self._pyramid.build_database(catalog)}

    def extract_features(self, observed: Sequence[BodyVector]):
        return list(observed)

    def match(self, observed: list, db) -> list[CandidateMatch]:
        obs = list(observed)
        if len(obs) < 3:
            return []
        # Aşama 1 — non-dim bootstrap
        feats1 = self._samaan.extract_features(obs)
        boot = self._samaan.match(feats1, db["samaan"])
        if not boot:
            return []                                  # çözümsüz > yanlış

        # Kalibrasyon kestirimi
        catalog = db["samaan"].catalog
        f_star = _estimate_focal(boot, obs, catalog, self.sensor)
        f_nom = self.sensor.focal_length_px
        self.last_focal_estimate_ppm = (f_star / f_nom - 1.0) * 1e6

        # Aşama 2 — body vektörleri f* ile pikselden yeniden kur, Pyramid koş
        corrected = []
        for o in obs:
            v = np.array([o.centroid_px[0], o.centroid_px[1], f_star])
            corrected.append(replace(o, u_body=v / np.linalg.norm(v)))
        feats2 = self._pyramid.extract_features(corrected)
        return self._pyramid.match(feats2, db["pyramid"])
