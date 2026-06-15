"""NDSIA — Non-Dimensional Star-ID Algorithm (Leake, Arnas & Mortari 2020).

Sadık implementasyon (brief 07b v3 Kol D; Sensors 20(9):2697, arXiv:2003.13736).
NDSIA'nın kendisi bir füzyondur: Pyramid iskeleti (pattern-shifting kernel
generator, unique-triangle, referans-yıldız onayı) + non-dim öznitelik.

Öznitelik: üçgenin KÜRESEL DİHEDRAL açıları (denk. 5-6) — 3 bağımsız öznitelik
(toplam ∈ (180°,540°), kısıt yok), body-vektör yolundan f-hatasına birinci-
derece duyarsız ama OA ofsetine belirgin duyarlı (Adım 0: 186″ @ %2 OA).

İzinli sapmalar (raporda gerekçeli):
- Arama: sadık yol n-D k-vector (NDKV); burada ilk açıda 1-D `kvector_range`
  + kalan iki açıda filtre + L2 kontrolü (denk. 1) — bizim ölçekte yeterli;
  NDKV hız gerekirse yükseltme.
- Dal seçimi: en küçük ara açının KARŞISINDAKİ köşe kosinüs kuralıyla (denk. 5,
  en iyi koşullama), kalan ikisi sinüs kuralıyla (denk. 6) — arcsin ≤90° dalı;
  π/2 üstü açılar 180°-x'e katlanır. DB ve gözlem AYNI prosedürü kullandığından
  belirsizlik iki tarafta tutarlıdır (makale tanjant kuralının sonuç
  değiştirmediğini raporlar).
- Yayılım YOK: kalan yıldızlar makalenin r-protokolüyle tanınır; final kontrol
  tüm tanınan çiftlerin ara açıları < FOV.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.sensor import SENSOR, SensorProfile
from .pyramid import pyramid_triad_order
from .sla_kvector import build_kvector, kvector_range
from .triangle_planar import covisible_triples

_ARCSEC = np.pi / (180.0 * 3600.0)


def dihedral_angles(U1: np.ndarray, U2: np.ndarray, U3: np.ndarray):
    """Üçlünün küresel dihedral açıları (LAM denk. 4-6), vektörize.

    Girdi: (M,3) birim vektörler. Çıktı: (M,3) açılar [köşe1, köşe2, köşe3].
    En küçük ara açının karşısındaki köşe kosinüs kuralıyla (denk. 5), kalan
    ikisi sinüs kuralıyla (denk. 6, arcsin ≤90° dalı).
    """
    U1 = np.atleast_2d(U1); U2 = np.atleast_2d(U2); U3 = np.atleast_2d(U3)
    t12 = np.arccos(np.clip(np.sum(U1 * U2, axis=1), -1, 1))   # köşe3'ün karşısı
    t13 = np.arccos(np.clip(np.sum(U1 * U3, axis=1), -1, 1))   # köşe2'nin karşısı
    t23 = np.arccos(np.clip(np.sum(U2 * U3, axis=1), -1, 1))   # köşe1'in karşısı
    sides = np.stack([t23, t13, t12], axis=1)    # sides[:,v] = köşe v'nin karşısı
    M = len(t12)

    def cosrule(opp, a, b):
        denom = np.sin(a) * np.sin(b)
        denom = np.where(denom < 1e-15, 1e-15, denom)
        return np.arccos(np.clip(
            (np.cos(opp) - np.cos(a) * np.cos(b)) / denom, -1, 1))

    # her köşe için kosinüs-kuralı değeri (karşı kenar; komşu kenarlar)
    A_cos = np.stack([cosrule(t23, t12, t13),
                      cosrule(t13, t12, t23),
                      cosrule(t12, t13, t23)], axis=1)         # (M,3)

    # dal seçimi (denk. 5): pivot = EN BÜYÜK ara açının karşısındaki köşe.
    # Küçük-FOV üçgeni near-planar -> en fazla BİR dihedral >90° olabilir ve o,
    # en büyük kenarın karşısındakidir; kosinüs kuralı genişi güvenle taşır,
    # kalan iki açı garantili dar -> arcsin (denk. 6) dal-katlamasız çalışır.
    # (İlk denemedeki argmin seçimi geniş açıyı arcsin'e bırakıp katlıyor ve
    # DB-gözlem anahtarlarını tutarsızlaştırıyordu — birim testle yakalandı.)
    pivot = np.argmax(sides, axis=1)                            # (M,)
    out = np.empty((M, 3))
    rows = np.arange(M)
    piv_ang = A_cos[rows, pivot]
    out[rows, pivot] = piv_ang
    # kalan iki köşe sinüs kuralıyla: sin(V)/sin(karşı_V) sabit (denk. 6)
    sin_piv_side = np.sin(sides[rows, pivot])
    sin_piv_side = np.where(sin_piv_side < 1e-15, 1e-15, sin_piv_side)
    ratio = np.sin(piv_ang) / sin_piv_side
    for v in range(3):
        m = pivot != v
        out[m, v] = np.arcsin(np.clip(ratio[m] * np.sin(sides[m, v]), -1, 1))
    return out


@dataclass
class NDSIAConfig:
    epsilon_arcsec: float = 250.0     # ε = 3σ_dihedral (denk. 1 eşiği).
    #   Türetim (rapor §ε): σ_centroid=5″ truth-hizalı Monte Carlo'da dihedral
    #   sapması P50=57″ -> robust σ≈85″ -> 3σ≈255″ (ağır kuyruk ince üçgenlerden;
    #   onlar unique-match'te zaten elenir). ppm=3000 sistematiği P50=0.9″ (ihmal).
    #   L2 kontrolü de aynı ε ile.
    min_kernel_confirm: bool = True   # r + r2 iki-referans yapısı (makale)


@dataclass
class NDSIADB:
    A: np.ndarray            # (M,) sıralı en küçük dihedral (k-vector ekseni)
    B: np.ndarray            # (M,) orta
    C: np.ndarray            # (M,) en büyük
    hipA: np.ndarray         # köşe-eşli hip'ler (A<->hipA, ...)
    hipB: np.ndarray
    hipC: np.ndarray
    kv_a: float
    kv_b: float
    K: np.ndarray
    catalog: Catalog         # final FOV kontrolü için
    n_records: int


@dataclass
class NDSIAFeatures:
    observed: list
    U: np.ndarray            # (f,3) body vektörler (nominal pinhole — "yaklaşık" yol)


class NDSIAAlgorithm:
    name = "ndsia"

    def __init__(self, config: NDSIAConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or NDSIAConfig()
        self.sensor = sensor
        self.last_triads_tried = 0

    # ------------------------------------------------------------------ DB
    def build_database(self, catalog: Catalog) -> NDSIADB:
        V = catalog.vectors
        hips = catalog.hip_ids
        tri = covisible_triples(catalog, self.sensor)
        TH = dihedral_angles(V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]])  # (M,3)
        H = hips[tri]
        order = np.argsort(TH, axis=1)                # artan (A,B,C) + köşe-eşli hip
        THs = np.take_along_axis(TH, order, axis=1)
        Hs = np.take_along_axis(H, order, axis=1)
        srt = np.argsort(THs[:, 0])
        A = np.ascontiguousarray(THs[srt, 0])
        kv_a, kv_b, K = build_kvector(A)
        return NDSIADB(A=A, B=THs[srt, 1], C=THs[srt, 2],
                       hipA=Hs[srt, 0], hipB=Hs[srt, 1], hipC=Hs[srt, 2],
                       kv_a=kv_a, kv_b=kv_b, K=K, catalog=catalog,
                       n_records=len(tri))

    # ------------------------------------------------------------- feature
    def extract_features(self, observed: Sequence[BodyVector]) -> NDSIAFeatures:
        obs = list(observed)
        U = np.array([o.u_body for o in obs]) if obs else np.zeros((0, 3))
        return NDSIAFeatures(observed=obs, U=U)

    # -------------------------------------------------------------- yardımcı
    def _query_candidates(self, db: NDSIADB, i, j, k, U):
        """Gözlem üçlüsünün dihedral anahtarıyla DB adayları (atama listesi).

        Her aday: {pozisyon: hip}. Pencere: per-açı ε + L2 < ε (denk. 1)."""
        eps = self.cfg.epsilon_arcsec * _ARCSEC
        TH = dihedral_angles(U[i][None, :], U[j][None, :], U[k][None, :])[0]
        pos = np.array([i, j, k])
        order = np.argsort(TH)
        THs = TH[order]; pos_s = pos[order]
        lo, hi = kvector_range(db.A, db.kv_a, db.kv_b, db.K,
                               THs[0] - eps, THs[0] + eps)
        if hi <= lo:
            return []
        dB = db.B[lo:hi] - THs[1]
        dC = db.C[lo:hi] - THs[2]
        dA = db.A[lo:hi] - THs[0]
        ok = (np.abs(dB) < eps) & (np.abs(dC) < eps) & \
             (dA * dA + dB * dB + dC * dC < eps * eps)        # L2 (denk. 1)
        return [{int(pos_s[0]): int(db.hipA[lo + x]),
                 int(pos_s[1]): int(db.hipB[lo + x]),
                 int(pos_s[2]): int(db.hipC[lo + x])}
                for x in np.nonzero(ok)[0]]

    def _query_unique(self, db: NDSIADB, i, j, k, U):
        """TAM-1 aday varsa atamayı döndür (kernel temel üçlüsü için)."""
        cands = self._query_candidates(db, i, j, k, U)
        return cands[0] if len(cands) == 1 else None

    # ---------------------------------------------------------------- match
    def match(self, features: NDSIAFeatures, db: NDSIADB) -> list[CandidateMatch]:
        obs = features.observed
        U = features.U
        f = len(obs)
        self.last_triads_tried = 0
        if f < 3:
            return []

        for (i, j, k) in pyramid_triad_order(f):       # kernel generator (aynı aile)
            self.last_triads_tried += 1
            base = self._query_unique(db, i, j, k, U)
            if base is None or len(set(base.values())) != 3:
                continue
            hI, hJ, hK = base[i], base[j], base[k]

            # --- r onayı: {r,i,j},{r,i,k},{r,j,k} üçü de unique + tutarlı hR
            r_found = None
            for r in range(f):
                if r in (i, j, k):
                    continue
                hR = self._confirm_ref(db, U, r, i, j, k, hI, hJ, hK)
                if hR is not None:
                    r_found = (r, hR)
                    break
            if r_found is None:
                continue
            r, hR = r_found

            # --- r2 onayı: 6 üçgen hepsi unique + tutarlı (makalenin iki-referansı)
            assign = {i: hI, j: hJ, k: hK, r: hR}
            r2_ok = False
            for r2 in range(f):
                if r2 in assign:
                    continue
                h2 = self._confirm_ref(db, U, r2, i, j, k, hI, hJ, hK)
                if h2 is None:
                    continue
                # r ile de tutarlılık: {i,r,r2},{j,r,r2},{k,r,r2}
                h2b = self._confirm_ref(db, U, r2, i, j, r, hI, hJ, hR)
                if h2b == h2:
                    assign[r2] = h2
                    r2_ok = True
                    break
            if self.cfg.min_kernel_confirm and not r2_ok:
                continue

            # --- kalan yıldızlar r-protokolüyle (atanmış kümeden birkaç baz üçlü
            # denenir; ilk koşullu-unique sonuç kabul)
            for s in range(f):
                if s in assign:
                    continue
                hS = None
                known = list(assign.items())
                for bi in range(min(4, len(known) - 2)):
                    (a, ha), (b, hb), (c, hc) = known[bi], known[bi + 1], known[bi + 2]
                    hS = self._confirm_ref(db, U, s, a, b, c, ha, hb, hc)
                    if hS is not None:
                        break
                if hS is not None and hS not in assign.values():
                    assign[s] = hS

            # --- final kontrol: tanınan çiftlerin KATALOG ara açıları < FOV çapı
            hv = np.array([db.catalog.by_id(h).u_inertial for h in assign.values()])
            G = hv @ hv.T
            if np.min(G) < np.cos(2.0 * self.sensor.fov_radius_rad):
                continue                               # tutarsız küme -> bu üçlüyü at

            return [CandidateMatch(obs[p].obs_id, h) for p, h in assign.items()]

        return []

    def _confirm_ref(self, db, U, s, i, j, k, hI, hJ, hK):
        """s gözlemini, bilinen (i,j,k)->(hI,hJ,hK) ile 3 üçgen üzerinden tanı.

        Her {s,a,b} sorgusunda 'unique' = bilinen köşelerle (a->ha, b->hb)
        TUTARLI adaylar arasında hS'in tek olması (global tek-aday değil —
        bizim yoğunlukta global-unique r-üçgeni neredeyse hiç yok; rapor
        §sapma: makalenin niyetine sadık, koşullu-unique okuma). Üç üçgen de
        aynı hS'i vermeli."""
        cands = []
        for (a, b, ha, hb) in ((i, j, hI, hJ), (i, k, hI, hK), (j, k, hJ, hK)):
            consistent = {m[s] for m in self._query_candidates(db, s, a, b, U)
                          if m.get(a) == ha and m.get(b) == hb}
            if len(consistent) != 1:                  # 0 ya da ≥2 -> onaysız
                return None
            cands.append(next(iter(consistent)))
        return cands[0] if cands[0] == cands[1] == cands[2] else None
