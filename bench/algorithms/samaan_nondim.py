"""Samaan Non-Dimensional Star-ID (2003/2006) — Faz 3 açılışı (brief 07).

Yeni eksen: KALİBRASYON ROBUSTLUĞU. Ara açı, odak-uzaklığı hatasıyla doğrudan
ölçeklenir (Liebe tutorial Fig. 23); üçgenin İÇ açıları ise görüntü düzleminde
radyal ölçeklemeye birinci dereceden değişmezdir. Sıcaklıkla kayan kalibrasyon
SLA/Liebe'yi bozar, Samaan ayakta kalır.

Feature: θ_min + θ_mid + θ_max ≈ π (küresel fazlalık küçük FOV'da ihmal) →
yalnız 2 bağımsız öznitelik (θ_min, θ_max). Boyutlu üçgenin 3 bağımsız
özniteliğinden biri ölçek değişmezliğine harcandı — non-dim'in bilgi bedeli.
Bu yüzden Samaan bulgusu: EN AZ 5 yıldız tutarlı eşleşmeden çözüm üretme
(`min_match_stars=5`) — iki öznitelikli üçgen tek başına ayırt edici değildir.

KRİTİK: gözlem iç açıları PİKSEL koordinatlarından (centroid_px) düz
trigonometriyle hesaplanır — body vektörlerden DEĞİL. Body vektörler (yanlış)
nominal pinhole'dan geçer ve bozulmayı içeri taşır; düzlem iç açıları radyal
ölçeklemeden hiç etkilenmez. Değişmezlik tam burada yaşar.

DB: co-visible üçlü enumerasyonu Triangle'dan, k-vector SLA'dan import (kopya yok).
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
from .sla_kvector import build_kvector, kvector_range, propagate_full_frame
from .triangle_planar import covisible_triples


@dataclass
class SamaanConfig:
    tol_theta_deg: float = 0.5        # iç açı toleransı (ara açıdan farklı ölçek)
    min_match_stars: int = 5          # Samaan bulgusu: <5 tutarlı yıldız -> çözümsüz
    min_votes: int = 2
    max_candidates_per_triple: int = 200   # bundan kalabalık aday listesi = bilgisiz
    #   üçlü (ince/yaygın üçgen), atlanır; oylar ayrıca 1/n_aday ağırlıklı —
    #   2 öznitelikli anahtarın zayıf ayırt ediciliğine karşı koruma
    #   (aday patlaması: tipik sorgu ~2000+ aday veriyordu; rapor §teşhis).
    consistency_rounds: int = 2       # karşılıklı-tutarlılık turu (kaba eleme)
    shortlist_k: int = 6              # obs başına aday havuzu boyutu
    consensus_gate_arcsec: float = 300.0   # ≥5-yıldız GEOMETRİK konsensüs kapısı.
    #   Samaan'ın ≥5 ilkesinin uygulaması: oy-kısa-listesi havuzundan en büyük
    #   attitude-tutarlı alt küme (RANSAC). Kapı kalibrasyon-toleranslı seçilir:
    #   ±3000 ppm'in body-vektör bozulması ≤~80″ ≪ 300″ ≪ sahtekâr hatası
    #   (derece mertebesi) — değişmezlik korunur (rapor §teşhis/sapma).
    use_core_verify: bool = False     # Faz 2 ablation politikası devam
    verify_gate_arcsec: float = 60.0

    @property
    def tol_rad(self) -> float:
        return np.radians(self.tol_theta_deg)


@dataclass
class SamaanDB:
    th_min: np.ndarray       # (M,) sıralı en küçük iç açı (rad) — k-vector ekseni
    th_max: np.ndarray       # (M,) en büyük iç açı
    hip_min: np.ndarray      # iç açısına göre eşlenmiş köşe hip'leri
    hip_mid: np.ndarray
    hip_max: np.ndarray
    a: float                 # k-vector doğrusu
    b: float
    K: np.ndarray
    catalog: Catalog         # opsiyonel core doğrulayıcı için (SLA deseni)
    n_records: int


@dataclass
class SamaanFeatures:
    triples: list            # (th_min, th_max, obs_min, obs_mid, obs_max)
    observed: list           # opsiyonel core doğrulayıcı için


def _interior_angles_vec(C: np.ndarray, A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Köşe C'deki küresel iç açı, vektörize (liebe._interior_angle eşdeğeri).

    A ve B, C'nin teğet düzlemine izdüşürülür; aradaki açı döner. (M,) rad.
    """
    dotAC = np.sum(A * C, axis=1, keepdims=True)
    dotBC = np.sum(B * C, axis=1, keepdims=True)
    ta = A - dotAC * C
    tb = B - dotBC * C
    na = np.linalg.norm(ta, axis=1)
    nb = np.linalg.norm(tb, axis=1)
    safe = (na > 1e-12) & (nb > 1e-12)
    cos = np.zeros(len(C))
    cos[safe] = np.sum(ta[safe] * tb[safe], axis=1) / (na[safe] * nb[safe])
    out = np.arccos(np.clip(cos, -1.0, 1.0))
    out[~safe] = 0.0
    return out


def _planar_interior(P0: np.ndarray, P1: np.ndarray, P2: np.ndarray) -> np.ndarray:
    """P0 köşesindeki DÜZLEM iç açısı (piksel koordinatları, (T,2))."""
    u = P1 - P0
    w = P2 - P0
    nu = np.linalg.norm(u, axis=1)
    nw = np.linalg.norm(w, axis=1)
    safe = (nu > 1e-9) & (nw > 1e-9)
    cos = np.zeros(len(P0))
    cos[safe] = np.sum(u[safe] * w[safe], axis=1) / (nu[safe] * nw[safe])
    out = np.arccos(np.clip(cos, -1.0, 1.0))
    out[~safe] = 0.0
    return out


class SamaanAlgorithm:
    name = "samaan_nondim"

    def __init__(self, config: SamaanConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or SamaanConfig()
        self.sensor = sensor

    # ------------------------------------------ DB: üçlü kataloğu + k-vector
    def build_database(self, catalog: Catalog) -> SamaanDB:
        V = catalog.vectors
        hips = catalog.hip_ids
        tri = covisible_triples(catalog, self.sensor)          # paylaşılan enumerasyon
        A, B, C = V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]]
        TH = np.stack([
            _interior_angles_vec(A, B, C),                     # köşe A
            _interior_angles_vec(B, A, C),                     # köşe B
            _interior_angles_vec(C, A, B),                     # köşe C
        ], axis=1)                                             # (M,3)
        H = hips[tri]                                          # (M,3)
        order = np.argsort(TH, axis=1)                         # iç açıya göre köşe sırası
        THs = np.take_along_axis(TH, order, axis=1)
        Hs = np.take_along_axis(H, order, axis=1)

        srt = np.argsort(THs[:, 0])                            # th_min'e göre sırala
        th_min = np.ascontiguousarray(THs[srt, 0])
        a, b, K = build_kvector(th_min)                        # SLA'dan import
        return SamaanDB(
            th_min=th_min, th_max=THs[srt, 2],
            hip_min=Hs[srt, 0], hip_mid=Hs[srt, 1], hip_max=Hs[srt, 2],
            a=a, b=b, K=K, catalog=catalog, n_records=len(tri),
        )

    # ---------------------------- feature: DÜZLEMSEL iç açılar (centroid_px!)
    def extract_features(self, observed: Sequence[BodyVector]) -> SamaanFeatures:
        obs = list(observed)
        f = len(obs)
        if f < 3:
            return SamaanFeatures(triples=[], observed=obs)
        P = np.array([o.centroid_px for o in obs], dtype=float)  # (f,2) piksel
        ids = np.array([o.obs_id for o in obs])
        tri = np.array(list(combinations(range(f), 3)))        # (T,3)
        P0, P1, P2 = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
        TH = np.stack([
            _planar_interior(P0, P1, P2),
            _planar_interior(P1, P0, P2),
            _planar_interior(P2, P0, P1),
        ], axis=1)
        OI = ids[tri]                                          # (T,3)
        order = np.argsort(TH, axis=1)
        THs = np.take_along_axis(TH, order, axis=1)
        OIs = np.take_along_axis(OI, order, axis=1)
        triples = list(zip(THs[:, 0].tolist(), THs[:, 2].tolist(),
                           OIs[:, 0].tolist(), OIs[:, 1].tolist(), OIs[:, 2].tolist()))
        return SamaanFeatures(triples=triples, observed=obs)

    # ------------------------------------------------------------------ match
    def match(self, features: SamaanFeatures, db: SamaanDB) -> list[CandidateMatch]:
        if not features.triples:
            return []
        tol = self.cfg.tol_rad
        cap = self.cfg.max_candidates_per_triple

        # 1) aday kayıtları topla: (o_min,o_mid,o_max, h_min,h_mid,h_max, w)
        records: list[tuple] = []
        for (tmin, tmax, o_min, o_mid, o_max) in features.triples:
            lo, hi = kvector_range(db.th_min, db.a, db.b, db.K, tmin - tol, tmin + tol)
            if hi <= lo:
                continue
            idx = np.nonzero(np.abs(db.th_max[lo:hi] - tmax) < tol)[0]
            n_cand = idx.size
            if n_cand == 0 or n_cand > cap:        # bilgisiz üçlü -> atla
                continue
            w = 1.0 / n_cand                       # ayırt edicilik ağırlığı
            for k in idx:
                j = lo + k
                # sıra-eşlenmiş köşe ataması (min<->min, mid<->mid, max<->max)
                records.append((o_min, o_mid, o_max,
                                int(db.hip_min[j]), int(db.hip_mid[j]),
                                int(db.hip_max[j]), w))

        # 2) oylama + karşılıklı-tutarlılık turları
        def tally(recs):
            votes = defaultdict(lambda: defaultdict(float))
            counts = defaultdict(lambda: defaultdict(int))
            for (om, od, ox, hm, hd, hx, w) in recs:
                for o, h in ((om, hm), (od, hd), (ox, hx)):
                    votes[o][h] += w
                    counts[o][h] += 1
            return votes, counts

        votes, counts = tally(records)
        K_ = self.cfg.shortlist_k
        for _ in range(self.cfg.consistency_rounds):
            short = {o: set(sorted(c, key=lambda h: -c[h])[:K_])
                     for o, c in votes.items()}
            kept = [r for r in records
                    if r[3] in short.get(r[0], ()) and r[4] in short.get(r[1], ())
                    and r[5] in short.get(r[2], ())]
            if not kept:
                break
            records = kept
            votes, counts = tally(records)

        # 3) ≥5-yıldız GEOMETRİK konsensüs (Samaan ilkesinin uygulaması):
        # obs başına top-k aday havuzu -> en büyük attitude-tutarlı alt küme
        # (kalibrasyon-toleranslı geniş kapı) -> obs başına tekille -> birebir.
        pool: list[CandidateMatch] = []
        for o, cand in votes.items():
            for h in sorted(cand, key=lambda x: -cand[x])[:self.cfg.shortlist_k]:
                if counts[o][h] >= self.cfg.min_votes:
                    pool.append(CandidateMatch(o, h, confidence=float(cand[h])))
        consensus = ransac_confirm(pool, features.observed, db.catalog,
                                   gate_arcsec=self.cfg.consensus_gate_arcsec,
                                   max_seeds=12)
        best_obs: dict[int, CandidateMatch] = {}
        used_hip: set[int] = set()
        for m in sorted(consensus, key=lambda m: -m.confidence):
            if m.obs_id not in best_obs and m.hip_id not in used_hip:
                best_obs[m.obs_id] = m
                used_hip.add(m.hip_id)
        core = list(best_obs.values())
        if len(core) < 3:
            return []

        # 4) tam-kare yayılım (SLA/Pyramid ile paylaşılan; kalibrasyon-toleranslı
        # geniş kapı — ppm bozulması body vektörleri ≤~80″ kaydırır)
        q = quest(core, db.catalog, features.observed)
        if q is None:
            return []
        matches = propagate_full_frame(
            q, features.observed, db.catalog,
            np.radians(self.cfg.consensus_gate_arcsec / 3600.0), self.sensor,
        )

        if len(matches) < self.cfg.min_match_stars:            # Samaan: ≥5 yoksa çözümsüz
            return []
        if self.cfg.use_core_verify:
            matches = ransac_confirm(matches, features.observed, db.catalog,
                                     gate_arcsec=self.cfg.verify_gate_arcsec)
        return matches

    def _resolve(self, votes, counts) -> list[CandidateMatch]:
        """Liebe `_resolve` deseni: obs başına en yüksek AĞIRLIKLI oy + global
        birebir; min_votes eşiği ham destek sayısı (counts) üzerinden."""
        mv = self.cfg.min_votes
        tentative = []
        for obs_id in sorted(votes):
            cand = votes[obs_id]
            best = max(cand, key=lambda h: cand[h])
            bv = cand[best]
            vals = sorted(cand.values(), reverse=True)
            unique = len(cand) == 1 or bv > vals[1]
            if unique and (counts[obs_id][best] >= mv or len(cand) == 1):
                tentative.append((obs_id, best, bv))
        best_for_hip: dict[int, tuple[int, float]] = {}
        for o, h, v in tentative:
            if h not in best_for_hip or v > best_for_hip[h][1]:
                best_for_hip[h] = (o, v)
        keep = {(o, h) for h, (o, _) in best_for_hip.items()}
        return [CandidateMatch(o, h, float(v)) for (o, h, v) in tentative if (o, h) in keep]
