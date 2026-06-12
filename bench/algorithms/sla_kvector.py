"""Mortari SLA / k-vector (1997) — Search-Less Algorithm (brief 05).

Faz 2'nin asıl sıçraması: pattern Liebe'den FARKLI (herhangi yıldız çifti + ara
açı) ve arama DB boyutundan TAMAMEN koparılır — sorgu maliyeti yalnız tolerans
içindeki aday sayısına (k) bağlı, m=DB boyutuna değil.

İki yeni parça:
  1. Çift kataloğu (O(n·f)): FOV içine sığabilen tüm yıldız çiftlerinin ara açıları.
  2. k-vector (Mortari 2000): sıralı dizide aralık sorgusunu O(1)-erişimle yapan
     önhesaplı tamsayı indeks.
Üstüne SLA'nın çoklu-çift cross-check'i + (tam id_rate için) attitude-tabanlı
tam-kare yayılım.

k-vector yardımcıları (build_kvector / kvector_range) BURADA kalır — Pyramid
(brief 06) bunları buradan import eder.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np
from scipy.spatial import cKDTree

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.quest import davenport_q_method, quest, rotate
from ..core.sensor import SENSOR, SensorProfile
from ..core.verify import ransac_confirm

_ARCSEC = np.pi / (180.0 * 3600.0)


# ============================================================ k-vector çekirdek
def build_kvector(y: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Sıralı (artan) `y` dizisi için k-vector indeksi (Mortari 2000).

    Uç noktalardan geçen doğru z(i)=a·i+b, i=1..m. ξ kaydırması (makine-epsilon)
    ile z(1)<y[0], z(m)>y[-1] garantilenir. K[i]=count(y ≤ z(i)); K boyutu m+1
    (K[0]=0 kullanılmaz, K[1..m]). Döner: (a, b, K).
    """
    y = np.ascontiguousarray(y, dtype=float)
    m = len(y)
    if m == 0:
        return 1.0, 0.0, np.array([0], dtype=np.int64)
    if m == 1:
        return 1.0, y[0] - 1.0, np.array([0, 1], dtype=np.int64)  # z(1)=y[0]
    span = float(y[-1] - y[0])
    xi = max(abs(span), 1.0) * 1e-12          # robustluk kaydırması
    ymin, ymax = y[0] - xi, y[-1] + xi
    a = (ymax - ymin) / (m - 1)
    b = ymin - a                              # z(i)=a·i+b -> z(1)=ymin, z(m)=ymax
    z = a * np.arange(1, m + 1) + b
    K = np.searchsorted(y, z, side="right").astype(np.int64)   # count(y <= z(i))
    return a, b, np.concatenate([[0], K])     # K[0]=0, K[1..m]


def kvector_range(y: np.ndarray, a: float, b: float, K: np.ndarray,
                  y_lo: float, y_hi: float) -> tuple[int, int]:
    """[y_lo, y_hi] aralığındaki elemanların [lo, hi) dilimini döndür.

    İkili arama/ağaç YOK: i_lo/i_hi iki aritmetik işlemle bulunur, K ile O(1)
    erişim, iki uçta birkaç eleman daraltılır (k-vector "en fazla birkaç taşar"
    garantisi). `searchsorted` ile birebir aynı küme (T1).
    """
    m = len(y)
    if m == 0:
        return 0, 0
    i_lo = int(np.floor((y_lo - b) / a))
    i_hi = int(np.ceil((y_hi - b) / a))
    i_lo = min(max(i_lo, 1), m)
    i_hi = min(max(i_hi, 1), m)
    lo, hi = int(K[i_lo]), int(K[i_hi])
    # k-vector tahmininden çift-yönlü daraltma -> kesin [lo,hi).
    # Tahmin iyiyken döngüler O(1) (k-vector taşma garantisi); aksi hâlde
    # kendini düzeltir. lo = ilk (y>=y_lo), hi = son (y<=y_hi)+1.
    while lo > 0 and y[lo - 1] >= y_lo:
        lo -= 1
    while lo < m and y[lo] < y_lo:
        lo += 1
    while hi < m and y[hi] <= y_hi:
        hi += 1
    while hi > 0 and y[hi - 1] > y_hi:
        hi -= 1
    return lo, hi


# ================================================================= SLA algoritma
@dataclass
class SLAConfig:
    n_pattern_stars: int = 4          # SLA: görüntüden b=4 yıldız
    tol_angle_arcsec: float = 15.0    # Liebe/Quine ile aynı ölçek (adil kıyas)
    min_core: int = 3                 # tutarlı çekirdek için min yıldız
    match_gate_arcsec: float = 60.0   # yayılım (full-frame) eşleşme kapısı
    use_core_verify: bool = False     # Faz 2 ablation: +ortak doğrulayıcı
    verify_gate_arcsec: float = 60.0

    @property
    def tol_rad(self) -> float:
        return self.tol_angle_arcsec * _ARCSEC

    @property
    def gate_rad(self) -> float:
        return self.match_gate_arcsec * _ARCSEC


@dataclass
class SLADB:
    pair_angles: np.ndarray   # (m,) sıralı ara açılar (rad)
    hipA: np.ndarray          # (m,)
    hipB: np.ndarray          # (m,)
    a: float                  # k-vector doğrusu
    b: float
    K: np.ndarray             # (m+1,) k-vector
    catalog: Catalog
    n_records: int


@dataclass
class SLAFeatures:
    pairs: list               # (oi, oj, angle) — b=en parlak yıldız çiftleri
    observed: list            # BodyVector listesi (yayılım + verify için)


class SLAAlgorithm:
    name = "sla_kvector"

    def __init__(self, config: SLAConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or SLAConfig()
        self.sensor = sensor

    # --------------------------------------------- DB: çift kataloğu + k-vector
    def build_database(self, catalog: Catalog) -> SLADB:
        V = catalog.vectors
        hips = catalog.hip_ids
        # co-visible çiftler: ayrım <= FOV çapı (2*fov_radius)
        chord = 2.0 * np.sin(self.sensor.fov_radius_rad)   # = 2 sin((2r)/2)
        neigh = catalog.kdtree.query_ball_point(V, chord)
        ang_l, ha_l, hb_l = [], [], []
        for i in range(len(V)):
            J = np.array([j for j in neigh[i] if j > i], dtype=int)   # index ile dedup
            if J.size == 0:
                continue
            ang = np.arccos(np.clip(V[J] @ V[i], -1.0, 1.0))
            ang_l.append(ang)
            ha_l.append(np.full(J.size, hips[i], dtype=np.int64))
            hb_l.append(hips[J])
        angles = np.concatenate(ang_l)
        hipA = np.concatenate(ha_l); hipB = np.concatenate(hb_l)
        order = np.argsort(angles)
        angles = np.ascontiguousarray(angles[order])
        hipA = hipA[order]; hipB = hipB[order]
        a, b, K = build_kvector(angles)
        return SLADB(angles, hipA, hipB, a, b, K, catalog, len(angles))

    # --------------------------------------------- feature: en parlak b yıldız
    def extract_features(self, observed: Sequence[BodyVector]) -> SLAFeatures:
        obs = list(observed)
        if len(obs) < 3:
            return SLAFeatures(pairs=[], observed=obs)
        b = min(self.cfg.n_pattern_stars, len(obs))
        chosen = sorted(obs, key=lambda o: o.mag)[:b]      # en parlak b
        pairs = []
        for oi, oj in combinations(chosen, 2):
            ang = float(np.arccos(np.clip(oi.u_body @ oj.u_body, -1.0, 1.0)))
            pairs.append((oi.obs_id, oj.obs_id, ang))
        return SLAFeatures(pairs=pairs, observed=obs)

    # ------------------------------------------------------------------ match
    def match(self, features: SLAFeatures, db: SLADB) -> list[CandidateMatch]:
        if not features.pairs:
            return []
        tol = self.cfg.tol_rad
        # 1) her gözlem çifti için k-vector aday katalog çiftleri -> partner dict
        partner: dict[frozenset, dict[int, set]] = {}
        for (oi, oj, ang) in features.pairs:
            lo, hi = kvector_range(db.pair_angles, db.a, db.b, db.K, ang - tol, ang + tol)
            pd: dict[int, set] = defaultdict(set)
            hA = db.hipA[lo:hi]; hB = db.hipB[lo:hi]
            for x, y in zip(hA.tolist(), hB.tolist()):
                pd[x].add(y); pd[y].add(x)
            partner[frozenset((oi, oj))] = pd

        # 2) cross-check: en büyük tutarlı atama (tek-spike dayanımı için tüm tohumlar)
        core = self._cross_check(features, partner)
        if len(core) < self.cfg.min_core:
            return []

        # 3) çekirdekten attitude
        core_cm = [CandidateMatch(o, h) for o, h in core.items()]
        q = quest(core_cm, db.catalog, features.observed)
        if q is None:
            return []

        # 4) attitude-tabanlı tam-kare yayılım (id_rate için)
        full = self._propagate(q, features.observed, db.catalog)

        # 5) opsiyonel ortak doğrulayıcı (Faz 2 ablation)
        if self.cfg.use_core_verify:
            full = ransac_confirm(full, features.observed, db.catalog,
                                  gate_arcsec=self.cfg.verify_gate_arcsec)
        return full

    def _cross_check(self, features, partner) -> dict[int, int]:
        """Aday çift listeleri arasında en büyük geometrik-tutarlı obs->hip atama.

        Her temel çiftten (her iki sıralama) tohumla; kalan yıldızları, atanmışlarla
        ortak-komşu kısıtının kesişimi tek hip verdiğinde ata. Tüm tohumlar denenir
        ki 4 yıldızdan biri spike olsa bile gerçek alt-küme bulunsun.
        """
        star_set = []
        for (oi, oj, _) in features.pairs:
            if oi not in star_set:
                star_set.append(oi)
            if oj not in star_set:
                star_set.append(oj)

        def partners(ok, os, h):
            pd = partner.get(frozenset((ok, os)))
            return pd.get(h, set()) if pd else set()

        best: dict[int, int] = {}
        for (oa, ob, _) in features.pairs:
            pd = partner[frozenset((oa, ob))]
            for ha, partners_ha in pd.items():
                for hb in partners_ha:
                    # tohum: oa=ha, ob=hb
                    assign = {oa: ha, ob: hb}
                    used = {ha, hb}
                    for ok in star_set:
                        if ok in assign:
                            continue
                        cand = None
                        for os, h in assign.items():
                            ps = partners(ok, os, h)
                            cand = set(ps) if cand is None else (cand & ps)
                            if not cand:
                                break
                        if cand:
                            cand -= used
                            if len(cand) == 1:
                                h_ok = next(iter(cand))
                                assign[ok] = h_ok; used.add(h_ok)
                    if len(assign) > len(best):
                        best = dict(assign)
        return best

    def _propagate(self, q, observed, catalog) -> list[CandidateMatch]:
        """Attitude ile tüm gözlemleri katalogla eşle (full-frame direct match)."""
        return propagate_full_frame(q, observed, catalog,
                                    self.cfg.gate_rad, self.sensor)


def propagate_full_frame(q, observed, catalog, gate_rad: float,
                         sensor: SensorProfile = SENSOR) -> list[CandidateMatch]:
    """Attitude-tabanlı tam-kare direct match (SLA/Pyramid/Samaan paylaşır).

    Katalog gövde çerçevesine döndürülür; her gözlem, FOV içindeki en yakın
    katalog yıldızına `gate_rad` içindeyse eşlenir (hip başına bir kez).
    """
    cat_body = rotate(q, catalog.vectors)
    vis = cat_body[:, 2] >= np.cos(sensor.fov_radius_rad)
    vidx = np.where(vis)[0]
    if vidx.size == 0:
        return []
    tree = cKDTree(cat_body[vidx])
    chord = 2.0 * np.sin(gate_rad / 2.0)
    used: set[int] = set()
    out = []
    for o in observed:
        d, j = tree.query(o.u_body)
        if d <= chord:
            hip = int(catalog.hip_ids[vidx[j]])
            if hip not in used:
                used.add(hip)
                out.append(CandidateMatch(o.obs_id, hip))
    return out
