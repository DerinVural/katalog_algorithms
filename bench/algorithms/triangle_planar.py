"""Planar Triangle baseline (brief 03 — Junkins 1981 soyu).

Feature: bir üçlünün 3 ara açısı, permütasyon-bağımsız sıralı anahtar
    (a_min, a_mid, a_max).
DB: FOV'da birlikte görülebilir tüm üçlüler -> O(n·f²) (KASITLI büyük; Liebe'nin
    O(n)'iyle kontrast için). a_min'e göre sıralı.
search: lineer (a_min penceresi + diğer iki açı filtresi) + oylama; opsiyonel
    4. yıldız (attitude) doğrulaması yanlış üçlüleri eler.

Bu, hız/bellek için değil, "neden modern yöntemler kazandı"yı sayısal göstermek
için var. Magnitude kullanılmaz.

NOT (PM'e): brief co-visibility için köşegen/FOV-çapı yarıçap öneriyor; bench'in
sahne modeli DAİRESEL FOV (yarıçap = FOV_H/2) olduğundan, her üçgenin bir
yıldızın FOV'una sığdığı A-merkezli co-visibility (yarıçap = fov_radius)
kullanıldı. Bu, sahnede gerçekten birlikte görülebilen üçgenleri kapsar ve
DB'yi 2×-yarıçapın ~25M'lik (inşası infeasible) hâline kıyasla ~1.7M'de tutar.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.quest import davenport_q_method, rotate
from ..core.sensor import SENSOR, SensorProfile

_ARCSEC = np.pi / (180.0 * 3600.0)


@dataclass
class TriangleConfig:
    tol_angle_arcsec: float = 15.0     # Liebe ile AYNI ölçek (adil kıyas)
    require_confirm: bool = True       # 4. yıldız / attitude doğrulaması
    tol_confirm_arcsec: float = 60.0   # doğrulama artık açısı kapısı
    min_votes: int = 2

    @property
    def tol_rad(self) -> float:
        return self.tol_angle_arcsec * _ARCSEC

    @property
    def tol_confirm_rad(self) -> float:
        return self.tol_confirm_arcsec * _ARCSEC


@dataclass
class TriangleDB:
    key: np.ndarray            # (M,3) sıralı (a_min,a_mid,a_max), a_min'e göre sıralı
    v_mm: np.ndarray           # (M,) min&mid kenarlarının ortak köşesi (hip)
    v_mx: np.ndarray           # (M,) min&max ortak köşe
    v_dx: np.ndarray           # (M,) mid&max ortak köşe
    hip_to_vec: dict           # doğrulama için hip -> u_inertial
    n_records: int


@dataclass
class TriFeatures:
    triples: list              # (a_min,a_mid,a_max, vmm,vmx,vdx) obs_id'lerle
    obs_vec: dict              # obs_id -> u_body


def _pairwise_angle(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.arccos(np.clip(np.sum(u * v, axis=-1), -1.0, 1.0))


def _triple_key_and_vertices(s_xy, s_xz, s_yz, x, y, z):
    """3 kenar + 3 köşe -> sıralı anahtar + sıralı-kenar-çiftlerinin ortak köşeleri.

    Kenar->köşe-çifti: kol0={x,y}, kol1={x,z}, kol2={y,z}.
    İki kolun ortak köşesi kol-indeks toplamıyla belirlenir: 1->x, 2->y, 3->z.
    """
    S = np.stack([s_xy, s_xz, s_yz], axis=-1)        # (...,3)
    order = np.argsort(S, axis=-1)                   # min,mid,max kol indeksleri
    key = np.take_along_axis(S, order, axis=-1)
    o0, o1, o2 = order[..., 0], order[..., 1], order[..., 2]

    def common(ca, cb):
        s = ca + cb
        return np.where(s == 1, x, np.where(s == 2, y, z))

    v_mm = common(o0, o1)
    v_mx = common(o0, o2)
    v_dx = common(o1, o2)
    return key, v_mm, v_mx, v_dx


class TrianglePlanarAlgorithm:
    name = "triangle_planar"

    def __init__(self, config: TriangleConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or TriangleConfig()
        self.sensor = sensor

    # ------------------------------------------------------------------ DB
    def build_database(self, catalog: Catalog) -> TriangleDB:
        V = catalog.vectors
        hips = catalog.hip_ids
        # A-merkezli co-visibility: bir yıldızın FOV'una (yarıçap fov_radius) sığan üçlüler
        chord = 2.0 * np.sin(self.sensor.fov_radius_rad / 2.0)
        neigh = catalog.kdtree.query_ball_point(V, chord)

        keys, vmm_l, vmx_l, vdx_l = [], [], [], []
        for a in range(len(V)):
            J = np.array([j for j in neigh[a] if j != a], dtype=int)
            if J.size < 2:
                continue
            NV = V[J]
            hA = int(hips[a]); hJ = hips[J]
            aA = np.arccos(np.clip(NV @ V[a], -1.0, 1.0))     # A-komşu kenarları
            pi, pj = np.triu_indices(J.size, 1)
            s_ABi = aA[pi]                                    # {A, Bi}
            s_ABj = aA[pj]                                    # {A, Bj}
            s_BiBj = _pairwise_angle(NV[pi], NV[pj])          # {Bi, Bj}
            key, v_mm, v_mx, v_dx = _triple_key_and_vertices(
                s_ABi, s_ABj, s_BiBj, hA, hJ[pi], hJ[pj]
            )
            keys.append(key); vmm_l.append(v_mm); vmx_l.append(v_mx); vdx_l.append(v_dx)

        key = np.concatenate(keys)                            # (M,3)
        v_mm = np.concatenate(vmm_l); v_mx = np.concatenate(vmx_l); v_dx = np.concatenate(vdx_l)

        # dedup: üçgen = {3 köşe}. Sıralı köşe üçlüsüne göre tekille.
        tri = np.sort(np.stack([v_mm, v_mx, v_dx], axis=1), axis=1)
        _, uniq = np.unique(tri, axis=0, return_index=True)
        key, v_mm, v_mx, v_dx = key[uniq], v_mm[uniq], v_mx[uniq], v_dx[uniq]

        order = np.argsort(key[:, 0])                         # a_min'e göre sırala
        hip_to_vec = {int(h): V[i] for i, h in enumerate(hips)}
        return TriangleDB(
            key=np.ascontiguousarray(key[order]),
            v_mm=v_mm[order], v_mx=v_mx[order], v_dx=v_dx[order],
            hip_to_vec=hip_to_vec, n_records=len(uniq),
        )

    # -------------------------------------------------------------- feature
    def extract_features(self, observed: Sequence[BodyVector]) -> TriFeatures:
        from itertools import combinations
        obs = list(observed)
        obs_vec = {o.obs_id: o.u_body for o in obs}
        n = len(obs)
        if n < 3:
            return TriFeatures(triples=[], obs_vec=obs_vec)
        U = np.array([o.u_body for o in obs])
        idarr = np.array([o.obs_id for o in obs])
        D = np.arccos(np.clip(U @ U.T, -1.0, 1.0))             # tüm ikili açılar (n,n)

        tri = np.array(list(combinations(range(n), 3)))         # (T,3) indeks
        ti, tj, tk = tri[:, 0], tri[:, 1], tri[:, 2]
        key, vmm, vmx, vdx = _triple_key_and_vertices(          # vektörize
            D[ti, tj], D[ti, tk], D[tj, tk], idarr[ti], idarr[tj], idarr[tk]
        )
        triples = list(zip(
            key[:, 0].tolist(), key[:, 1].tolist(), key[:, 2].tolist(),
            vmm.tolist(), vmx.tolist(), vdx.tolist(),
        ))
        return TriFeatures(triples=triples, obs_vec=obs_vec)

    # ---------------------------------------------------------------- match
    def match(self, features: TriFeatures, db: TriangleDB) -> list[CandidateMatch]:
        tol = self.cfg.tol_rad
        a_min = db.key[:, 0]
        votes: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))

        for (amin, amid, amax, vmm, vmx, vdx) in features.triples:
            lo = np.searchsorted(a_min, amin - tol, side="left")
            hi = np.searchsorted(a_min, amin + tol, side="right")
            if hi <= lo:
                continue
            dk = db.key[lo:hi]
            ok = (np.abs(dk[:, 1] - amid) < tol) & (np.abs(dk[:, 2] - amax) < tol)
            for k in np.nonzero(ok)[0]:
                j = lo + k
                votes[vmm][int(db.v_mm[j])] += 1.0
                votes[vmx][int(db.v_mx[j])] += 1.0
                votes[vdx][int(db.v_dx[j])] += 1.0

        matches = self._resolve(votes)
        if self.cfg.require_confirm:
            matches = self._confirm(matches, features, db)
        return matches

    def _resolve(self, votes) -> list[CandidateMatch]:
        mv = self.cfg.min_votes
        tentative = []
        for obs_id in sorted(votes):
            cand = votes[obs_id]
            best = max(cand, key=lambda h: cand[h])
            bv = cand[best]
            vals = sorted(cand.values(), reverse=True)
            unique = len(cand) == 1 or bv > vals[1]
            if unique and (bv >= mv or len(cand) == 1):
                tentative.append((obs_id, best, bv))
        best_for_hip = {}
        for obs_id, hip, v in tentative:
            if hip not in best_for_hip or v > best_for_hip[hip][1]:
                best_for_hip[hip] = (obs_id, v)
        keep = {(o, h) for h, (o, _) in best_for_hip.items()}
        return [CandidateMatch(o, h, float(v)) for (o, h, v) in tentative if (o, h) in keep]

    def _confirm(self, matches, features: TriFeatures, db: TriangleDB):
        """Dayanıklı (RANSAC-tarzı) 4. yıldız doğrulaması.

        Spike kaynaklı yanlış eşleşmeler tüm-eşleşmeli tek QUEST'i bozar; bunun
        yerine en yüksek-oylu eşleşme çiftlerinden attitude tohumlanır, her tohum
        için tüm eşleşmeler içindeki INLIER (artık açısı < gate) kümesi sayılır,
        en büyük tutarlı küme seçilir. Doğru yıldızlar ortak gerçek attitude'da
        anlaşır (büyük inlier kümesi); spike'lar tutarsız kalır (elenir).
        """
        gate = self.cfg.tol_confirm_rad
        ms = sorted(matches, key=lambda m: -m.confidence)
        if len(ms) < 3:
            return matches
        body = np.array([features.obs_vec[m.obs_id] for m in ms])
        inertial = np.array([db.hip_to_vec[m.hip_id] for m in ms])

        def inliers_of(q):
            pred = rotate(q, inertial)
            resid = np.arccos(np.clip(np.sum(pred * body, axis=1), -1.0, 1.0))
            return resid <= gate

        seeds = list(range(min(8, len(ms))))                  # en yüksek-oylu adaylar
        best_mask = None
        for a in range(len(seeds)):
            for b in range(a + 1, len(seeds)):
                try:
                    q = davenport_q_method(body[[a, b]], inertial[[a, b]])
                except Exception:
                    continue
                mask = inliers_of(q)
                if best_mask is None or mask.sum() > best_mask.sum():
                    best_mask = mask

        if best_mask is None or best_mask.sum() < 3:
            return []                                         # tutarlı küme yok -> çözümsüz (>yanlış)

        # rafine: inlier'lardan yeniden kestir, yeniden seç
        try:
            q = davenport_q_method(body[best_mask], inertial[best_mask])
            best_mask = inliers_of(q)
        except Exception:
            pass
        return [m for m, keep in zip(ms, best_mask) if keep]
