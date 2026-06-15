"""Kol B — NonDimPyramid füzyonu (brief 07b FINAL §5; tasarım bizim).

Öznitelik: piksel-düzlemi PLANAR iç açıları (Samaan'dan import) — 2 bağımsız
öznitelik, f-ölçeklemesine VE OA-ötelemesine TAM değişmez (Adım-0/07 ölçümü:
0.000″ her bozulmada). Karar makinesi: Pyramid iskeleti.

match akışı (brief §5):
  1. `pyramid_triad_order(f)` (en-parlak kısıtı yok).
  2. Üçlü başına non-dim sorgu: kvector(θ_min±tol) + θ_max filtresi + köşe
     ataması; `max_candidates_per_triple` tavanı Samaan'dan. Samaan'ın oy
     havuzu YOK — merkezi tasarım kararı: oylama küme-kopyalarında tutarlı-
     yanlış kazanan üretebiliyor (07 teşhisi); aday + piramit onayı bunu
     yapısal engeller. TAM-1 kuralı (Pyramid'den) ONAYDAN SONRA uygulanır:
     r-onayını geçen aday sayısı != 1 ise üçlü reddedilir. (Sorgu-düzeyi
     tam-1 okuma 2-öznitelik uzayında [~46 aday/pencere] hiçbir üçlüyü
     geçirmiyor — H1/kabul-4 ile çelişir; rapor §yorum.)
  3. Non-dim piramit onayı: 4. gözlem r ile C(4,3)=4 üçgenin DÖRDÜ tutarlı
     (taban + 3 r-üçgeni, koşullu-tek hR); `n_confirm_stars=2` -> ≥2 farklı r.
  4. Çekirdek artık kapısı 300″ (±3000 ppm body-bozulması ≤~80″ ≪ 300″ ≪
     derece-mertebesi sahtekâr; 06a'nın 20″'si ppm altında gerçek çözümleri
     öldürürdü — bilinçli fark).
  5. `min_extra_stars≥1` + `propagate_full_frame` (geniş kapı).

DB: SamaanDB AYNEN (ek maliyet 0). Ebeveyn dosyaları değiştirilmez.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.quest import quest, rotate
from ..core.sensor import SENSOR, SensorProfile
from .pyramid import pyramid_triad_order
from .samaan_nondim import SamaanAlgorithm, SamaanDB, _planar_interior
from .sla_kvector import kvector_range, propagate_full_frame

_ARCSEC = np.pi / (180.0 * 3600.0)


@dataclass
class NonDimPyramidConfig:
    tol_theta_arcsec: float = 250.0       # = 3σ iç-açı eşiği (Samaan/NDSIA ε
    #   türetimi: σ_centroid=5″ -> robust σ≈85″; rapor §ε)
    max_candidates_per_triple: int = 200  # Samaan tavanı (bilgisiz üçlü atla)
    n_confirm_stars: int = 2              # ≥2 farklı doğrulayıcı r
    consensus_gate_arcsec: float = 300.0  # çekirdek artık kapısı + yayılım kapısı
    min_extra_stars: int = 1
    min_match_stars: int = 5              # Samaan kuralı (<5 -> çözümsüz)


@dataclass
class NonDimPyramidFeatures:
    observed: list
    P: np.ndarray            # (f,2) piksel koordinatları


class NonDimPyramidAlgorithm:
    name = "nondim_pyramid"

    def __init__(self, config: NonDimPyramidConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or NonDimPyramidConfig()
        self.sensor = sensor
        self._samaan = SamaanAlgorithm(sensor=sensor)
        self.last_triads_tried = 0

    # DB — Samaan ile AYNEN (ek maliyet 0)
    def build_database(self, catalog: Catalog) -> SamaanDB:
        return self._samaan.build_database(catalog)

    def extract_features(self, observed: Sequence[BodyVector]) -> NonDimPyramidFeatures:
        obs = list(observed)
        P = (np.array([o.centroid_px for o in obs], dtype=float)
             if obs else np.zeros((0, 2)))
        return NonDimPyramidFeatures(observed=obs, P=P)

    # ------------------------------------------------------------- yardımcı
    @staticmethod
    def _azimuth_matrix(P: np.ndarray) -> np.ndarray:
        """AZ[i,j] = atan2(P_j−P_i) — iç açı O(1)'e iner (hız: spike'lı
        sahnede per-üçlü array kurulumu 100×+ pahalıydı)."""
        d = P[None, :, :] - P[:, None, :]
        return np.arctan2(d[..., 1], d[..., 0])

    def _precompute(self, db: SamaanDB, AZ: np.ndarray, f: int):
        """TÜM C(f,3) gözlem üçlüsü için aday atamalarını bir kez hesapla.

        Döner: dict[(a<b<c)] -> list[dict{obs:hip}] (0/None = aday yok ya da
        tavan aşımı). match ve onay artık saf lookup — per-üçlü tekrar k-vector
        yok (spike'lı sahnede 87 s -> saniyeler)."""
        tol = self.cfg.tol_theta_arcsec * _ARCSEC
        cap = self.cfg.max_candidates_per_triple
        tris = np.array(list(combinations(range(f), 3)))
        i, j, k = tris[:, 0], tris[:, 1], tris[:, 2]
        TH = np.stack([self._interior_vec(AZ, i, j, k),
                       self._interior_vec(AZ, j, i, k),
                       self._interior_vec(AZ, k, i, j)], axis=1)   # (T,3)
        order = np.argsort(TH, axis=1)
        THs = np.take_along_axis(TH, order, axis=1)
        POSs = np.take_along_axis(tris, order, axis=1)             # iç-açı-sıralı obs

        out: dict[tuple, list] = {}
        for t in range(len(tris)):
            lo, hi = kvector_range(db.th_min, db.a, db.b, db.K,
                                   THs[t, 0] - tol, THs[t, 0] + tol)
            if hi <= lo or (hi - lo) > 80 * cap:                  # erken eleme
                continue
            sl = np.nonzero(np.abs(db.th_max[lo:hi] - THs[t, 2]) < tol)[0]
            if sl.size == 0 or sl.size > cap:
                continue
            p0, p1, p2 = int(POSs[t, 0]), int(POSs[t, 1]), int(POSs[t, 2])
            out[(int(tris[t, 0]), int(tris[t, 1]), int(tris[t, 2]))] = [
                {p0: int(db.hip_min[lo + x]), p1: int(db.hip_mid[lo + x]),
                 p2: int(db.hip_max[lo + x])} for x in sl]
        return out

    @staticmethod
    def _interior_vec(AZ, v, a, b):
        x = np.abs(AZ[v, a] - AZ[v, b]) % (2 * np.pi)
        return np.where(x > np.pi, 2 * np.pi - x, x)

    def _confirm_r(self, tcands, r, base):
        """r ile 3 r-üçgeni (önhesaplı tablodan): her biri base'in bilinen iki
        köşesiyle koşullu-tek aynı hR'yi vermeli."""
        items = list(base.items())             # [(pos,hip),...] 3 köşe
        hRs = []
        for a in range(3):
            for b in range(a + 1, 3):
                (x, hx), (y, hy) = items[a], items[b]
                key = tuple(sorted((r, x, y)))
                cands = tcands.get(key)
                if cands is None:
                    return None
                consistent = {m[r] for m in cands if m.get(x) == hx and m.get(y) == hy}
                if len(consistent) != 1:
                    return None
                hRs.append(next(iter(consistent)))
        return hRs[0] if hRs[0] == hRs[1] == hRs[2] else None

    # ---------------------------------------------------------------- match
    def match(self, features: NonDimPyramidFeatures, db: SamaanDB) -> list[CandidateMatch]:
        obs = features.observed
        P = features.P
        f = len(obs)
        self.last_triads_tried = 0
        if f < 3:
            return []
        gate = self.cfg.consensus_gate_arcsec * _ARCSEC
        AZ = self._azimuth_matrix(P)
        required = min(self.cfg.n_confirm_stars, max(f - 3, 0))
        tcands = self._precompute(db, AZ, f)       # tüm üçlü adayları (bir kez)

        for (i, j, k) in pyramid_triad_order(f):
            self.last_triads_tried += 1
            cands = tcands.get((i, j, k))
            if cands is None:
                continue

            # TAM-1 kuralı ONAYDAN SONRA: r-onayını geçen aday sayısı != 1 -> reddet
            survivor = None
            ambiguous = False
            for base in cands:
                if len(set(base.values())) != 3:
                    continue
                confirms = []
                used_hR = set(base.values())
                for r in range(f):
                    if r in (i, j, k):
                        continue
                    hR = self._confirm_r(tcands, r, base)
                    if hR is not None and hR not in used_hR:
                        confirms.append((r, hR))
                        used_hR.add(hR)
                        if len(confirms) >= self.cfg.n_confirm_stars:
                            break
                if len(confirms) >= max(required, 1) or (f <= 3 and not confirms):
                    if survivor is not None:
                        ambiguous = True               # ≥2 onaylı aday -> belirsiz
                        break
                    survivor = (dict(base), confirms)
            if survivor is None or ambiguous:
                continue
            core, confirms = survivor
            if confirms:
                r0, hR0 = confirms[0]
                core[r0] = hR0

            core_cm = [CandidateMatch(obs[p].obs_id, h) for p, h in core.items()]
            q = quest(core_cm, db.catalog, obs)
            if q is None:
                continue
            # çekirdek artık kapısı (300″ — kalibrasyon-toleranslı)
            body = np.array([obs[p].u_body for p in core])
            inertial = np.array([db.catalog.by_id(h).u_inertial for h in core.values()])
            resid = np.arccos(np.clip(np.sum(rotate(q, inertial) * body, axis=1), -1, 1))
            if np.any(resid > gate):
                continue

            full = propagate_full_frame(q, obs, db.catalog, gate, self.sensor)
            core_obs = {obs[p].obs_id for p in core}
            extra = sum(1 for m in full if m.obs_id not in core_obs)
            if f > len(core) and extra < self.cfg.min_extra_stars:
                continue
            if len(full) < self.cfg.min_match_stars:
                continue
            return full

        return []                                      # çözümsüz > yanlış