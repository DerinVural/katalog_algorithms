"""Pyramid (Mortari, Samaan & Bruccoleri 2004) — Faz 2 finali (brief 06).

Arama problemi SLA ile çözüldü; Pyramid'in tüm katkısı **non-star (spike) reddi**:
  1. Akıllı üçlü permütasyonu — ardışık denemeler aynı yıldızda ısrar etmez
     (kalıcı bir spike denemeleri arka arkaya zehirleyemez).
  2. Üçgen eşleme: 3 çift açı için 3 k-vector sorgusu → tam 1 tutarlı (hI,hJ,hK)
     atama (0 veya ≥2 → reddet, sıradakine geç).
  3. Piramit doğrulaması: 4. yıldız r ile (i,r),(j,r),(k,r) aynı hipR'de tutarlı
     → kabul. Hiçbir r onaylamazsa üçlü reddedilir (içinde spike var).
Native doğrulama bu algoritmanın TANIMIDIR (Triangle'daki gibi sonradan ekli değil).

build_database + k-vector + yayılım SLA'dan İÇE AKTARILIR (kopya kod yok); DB
boyutu SLA ile birebir aynı (ek maliyet 0).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.quest import quest
from ..core.sensor import SENSOR, SensorProfile
from ..core.verify import ransac_confirm
from .sla_kvector import SLAAlgorithm, SLAConfig, SLADB, kvector_range

_ARCSEC = np.pi / (180.0 * 3600.0)
_EMPTY: frozenset = frozenset()


def pyramid_triad_order(f: int) -> list[tuple[int, int, int]]:
    """Mortari'nin akıllı üçlü deneme sırası (brief 06 İş 1).

    (i, i+dj, i+dk), dj=1..f-2, dk=dj+1..f-1, i=0..f-1-dk. Tüm C(f,3) üçlüyü tam
    bir kez üretir; küçük kaydırmalılar önce → ilk denemelerde hiçbir yıldız tüm
    üçlülerde ortak olmaz (tek spike'a ısrar yok). Deterministik.
    """
    order = []
    for dj in range(1, f - 1):
        for dk in range(dj + 1, f):
            for i in range(0, f - dk):
                order.append((i, i + dj, i + dk))
    return order


@dataclass
class PyramidConfig:
    tol_angle_arcsec: float = 15.0
    confirm_pyramid: bool = True       # native: 4. yıldız doğrulaması (ablation kapatır)
    use_core_verify: bool = False      # +ortak doğrulayıcı (ablation)
    match_gate_arcsec: float = 60.0
    verify_gate_arcsec: float = 60.0
    min_solution_stars: int = 4        # onaylı piramidin tam-karede açıklaması gereken min yıldız
    #   (sahte piramit reddi: yanlış attitude tam-kareyi açıklayamaz)

    @property
    def tol_rad(self) -> float:
        return self.tol_angle_arcsec * _ARCSEC


@dataclass
class PyramidFeatures:
    observed: list           # BodyVector listesi (pozisyon 0..f-1)
    D: np.ndarray            # (f,f) ikili ara açılar (rad)


class PyramidAlgorithm:
    name = "pyramid"

    def __init__(self, config: PyramidConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or PyramidConfig()
        self.sensor = sensor
        # DB inşası + yayılım SLA'dan paylaşılır
        self._sla = SLAAlgorithm(
            SLAConfig(tol_angle_arcsec=self.cfg.tol_angle_arcsec,
                      match_gate_arcsec=self.cfg.match_gate_arcsec),
            sensor,
        )
        self.last_triads_tried = 0     # teşhis: kaç üçlü denendi

    # build_database — SLA ile AYNI (ek maliyet 0)
    def build_database(self, catalog: Catalog) -> SLADB:
        return self._sla.build_database(catalog)

    # extract — tüm gözlem çiftlerinin ara açıları (en-parlak-4 kısıtı YOK)
    def extract_features(self, observed: Sequence[BodyVector]) -> PyramidFeatures:
        obs = list(observed)
        if len(obs) < 3:
            return PyramidFeatures(observed=obs, D=np.zeros((len(obs), len(obs))))
        U = np.array([o.u_body for o in obs])
        D = np.arccos(np.clip(U @ U.T, -1.0, 1.0))
        return PyramidFeatures(observed=obs, D=D)

    def match(self, features: PyramidFeatures, db: SLADB) -> list[CandidateMatch]:
        obs = features.observed
        f = len(obs)
        self.last_triads_tried = 0
        if f < 3:
            return []
        tol = self.cfg.tol_rad
        D = features.D

        # partner dict + anahtar kümesi LAZY (talep üzerine, cache'li) — zengin
        # alanda başarı ilk üçlüde olduğundan yalnız denenen çiftler hesaplanır.
        P: dict[tuple[int, int], dict[int, frozenset]] = {}
        keyset: dict[tuple[int, int], frozenset] = {}

        def _get(a, b):
            key = (a, b) if a < b else (b, a)
            pd = P.get(key)
            if pd is None:
                pd = self._partners(db, D[key[0], key[1]], tol)
                P[key] = pd
                keyset[key] = frozenset(pd.keys())
            return key

        def part(a, b, h) -> frozenset:
            return P[_get(a, b)].get(h, _EMPTY)

        def keys(a, b) -> frozenset:
            return keyset[_get(a, b)]

        for (i, j, k) in pyramid_triad_order(f):
            self.last_triads_tried += 1
            triple = self._unique_triple(i, j, k, P, part, keys)
            if triple is None:
                continue
            hI, hJ, hK = triple
            if self.cfg.confirm_pyramid:
                hR_r = self._confirm_pyramid(i, j, k, hI, hJ, hK, f, part)
                if hR_r is None:
                    continue                           # 4. yıldız onaylamadı -> spike içeriyor
                r, hR = hR_r
                core = {i: hI, j: hJ, k: hK, r: hR}
            else:
                core = {i: hI, j: hJ, k: hK}           # ablation: onaysız ilk tutarlı üçlü

            # çekirdekten attitude + tam-kare yayılım (SLA ile paylaşılan)
            core_cm = [CandidateMatch(obs[p].obs_id, h) for p, h in core.items()]
            q = quest(core_cm, db.catalog, obs)
            if q is None:
                continue
            full = self._sla._propagate(q, obs, db.catalog)
            # sahte piramit reddi: doğru attitude tam-kareyi açıklar; sahtesi açıklamaz
            if len(full) < self.cfg.min_solution_stars:
                continue
            if self.cfg.use_core_verify:
                full = ransac_confirm(full, obs, db.catalog,
                                      gate_arcsec=self.cfg.verify_gate_arcsec)
            return full

        return []                                      # tüm üçlüler tükendi -> çözümsüz > yanlış

    # --------------------------------------------------------------- yardımcı
    def _partners(self, db: SLADB, theta: float, tol: float) -> dict[int, frozenset]:
        lo, hi = kvector_range(db.pair_angles, db.a, db.b, db.K, theta - tol, theta + tol)
        acc: dict[int, set] = defaultdict(set)
        for hA, hB in zip(db.hipA[lo:hi].tolist(), db.hipB[lo:hi].tolist()):
            acc[hA].add(hB); acc[hB].add(hA)
        return {h: frozenset(s) for h, s in acc.items()}

    def _unique_triple(self, i, j, k, P, part, keys):
        """(i,j,k) için TAM 1 tutarlı (hI,hJ,hK) varsa döndür, yoksa None.

        hI yalnız (i,j) ve (i,k) aday kümelerinin kesişimi (pivot kısıtı) —
        spike üçlüleri için kesişim küçük/boş, hızlı reddedilir.
        """
        cand_hI = keys(i, j) & keys(i, k)             # keys() lazy _get tetikler
        pij = P[(i, j)]
        found = None
        for hI in cand_hI:
            ik = part(i, k, hI)
            for hJ in pij[hI]:
                for hK in (ik & part(j, k, hJ)):
                    if found is not None and found != (hI, hJ, hK):
                        return None                    # ≥2 belirsiz -> reddet
                    found = (hI, hJ, hK)
        return found

    def _confirm_pyramid(self, i, j, k, hI, hJ, hK, f, part):
        """Kalan gözlemlerden bir r, (i,r),(j,r),(k,r) aynı tek hipR'de tutarlıysa
        (r, hR) döndür; yoksa None."""
        for r in range(f):
            if r in (i, j, k):
                continue
            hRset = part(i, r, hI) & part(j, r, hJ) & part(k, r, hK)
            if len(hRset) == 1:
                return r, next(iter(hRset))
        return None
