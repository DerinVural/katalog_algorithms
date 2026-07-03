"""Padgett & Kreutz-Delgado (1997) — Grid Algorithm (brief 08).

Bench'in İLK açı-ailesi DIŞI algoritması. Şimdiye kadar her algoritma (Liebe,
planar triangle, Quine, SLA, Pyramid, Samaan/NDSIA) **yıldızlar-arası açı**
eşler. Grid, **uzamsal bit-imza** eşler: referans yıldız etrafına, roll'a göre
normalize edilmiş bir g×g ızgara serer ve her hücrenin dolu/boş oluşunu bir bit
olarak kodlar. İmza karşılaştırması eşleşen-hücre sayımı (g² − Hamming).

Tasarım kararları (brief §12 uzlaştırma + repo kontratı):
  * **Projeksiyon = equidistant azimuthal** (radyal-lineer): komşunun açısal
    uzaklığı ρ doğrudan yarıçap olur -> hücre açısal boyutu TAM 2·r_p/g (T6
    temiz, brief default g=40, r_p=6° -> 0.30°/hücre). Gnomonik yerine bu
    seçildi çünkü açı-koruyucu (bit-flip modeli gürültüye lineer bağlanır).
  * **NN hizalama** azimutu NN yönüne çevirir -> roll (boresight etrafı dönme)
    imzadan düşer (T1). Buffer r_b yalnız NN SEÇİMİNİ etkiler; ızgaraya r_p
    içindeki TÜM komşular girer.
  * **FOV görünürlük maskesi** (repo'ya özgü, brief'e bildirilen sapma):
    gözlemcinin r_p diski FOV'dan (yarıçap 7.35°) taşar -> kenar yıldızlarında
    katalog imzası (tam disk) ile gözlem imzası (budanmış) uyuşmaz, gürültüsüzde
    bile self-id kırılırdı (Liebe kenar-kaybı ile aynı olgu). Çözüm: Hamming'i
    YALNIZ gözlemcinin görebileceği hücrelerde say. Maske body-frame'de
    hesaplanır (attitude gerektirmez): hücre yönünün boresight'a açısı FOV
    içindeyse hücre "görünür". Böylece merkez VE kenar yıldızı gürültüsüz
    sahnede tam eşleşir (score=g²), T4 %100 tutar.

Katkı ekseni (brief §1): hash tabanlı imza vs k-vector açı-araması; ve tek-NN
seçimine dayanan YAPISAL bir tekil-hata-noktası — açı ailesinde yoktur.

Attitude BURADA çözülmez: match() correspondence döndürür, bench'in QUEST
aşaması tüketir (SLA/Pyramid ile aynı kontrat). Native güvenlik tümüyle kabul
kapılarında (threshold + margin + consensus); Grid'in yerleşik spike-reddi yok
(Pyramid'in 4-yıldız onayı gibi) -> kapılar ZORUNLU (brief §5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ..core.interfaces import BodyVector, Catalog, CandidateMatch
from ..core.sensor import SENSOR, SensorProfile
from ..core.verify import ransac_confirm

_ARCSEC = np.pi / (180.0 * 3600.0)
_DEG = np.pi / 180.0
_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)


# ================================================================= konfigürasyon
@dataclass
class PadgettGridConfig:
    pattern_radius_deg: float = 6.0     # r_p: desen diski (FOV 14.7° içinde kalmalı)
    buffer_radius_deg: float = 0.30     # r_b: NN gürültü koruması (>> centroid hata)
    grid_size: int = 40                 # g: g²=1600 bit/yıldız; hücre ~2r_p/g=0.30°
    match_threshold: float = 1520.0     # τ: min eşleşen hücre skoru (g²−izinli uyumsuz)
    margin_threshold: float = 2.0       # Δ: (en iyi − ikinci) min skor farkı — near-tie =
    #   bozulmuş NN yöneliminin imzası -> belirsiz, reddet (brief §5.2, ana güvenlik kapısı)
    min_consensus: int = 3              # c: kare 'solved' için min geometrik-tutarlı ID
    consensus_tol_arcsec: float = 60.0  # geometrik tutarlılık açı toleransı
    # Faz 2+ ablation: native kapıları paylaşılan RANSAC doğrulayıcıyla değiştir
    use_shared_verify: bool = False
    verify_gate_arcsec: float = 60.0

    @property
    def r_p(self) -> float:
        return self.pattern_radius_deg * _DEG

    @property
    def r_b(self) -> float:
        return self.buffer_radius_deg * _DEG

    @property
    def n_bits(self) -> int:
        return self.grid_size * self.grid_size


@dataclass
class GridDB:
    sig_packed: np.ndarray   # (N, ceil(g²/8)) uint8 — katalog imza matrisi (paketli)
    hip_ids: np.ndarray      # (N,) int64
    valid: np.ndarray        # (N,) bool — NN yönü tanımlıysa (buffer dışı komşu var)
    catalog: Catalog
    g: int
    r_p: float               # rad
    n_bits: int
    n_records: int           # = N (raporlama uyumu)


@dataclass
class GridFeatures:
    observed: list                 # BodyVector listesi
    sig_packed: np.ndarray         # (f, nbytes) uint8 — gözlem imzaları
    mask_packed: np.ndarray        # (f, nbytes) uint8 — FOV görünürlük maskeleri
    valid: np.ndarray              # (f,) bool


# ================================================================= imza çekirdeği
def _tangent_basis(center: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """`center` yönüne dik deterministik ortonormal taban (e1, e2).

    Ham taban keyfidir (roll'a bağlı); NN hizalaması bu keyfiliği siler. Referans
    olarak +z; center ona paralelse +x kullanılır (kutup tekilliği koruması).
    """
    ref = np.array([0.0, 0.0, 1.0])
    if abs(center[2]) > 0.9:
        ref = np.array([1.0, 0.0, 0.0])
    e1 = np.cross(ref, center)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(center, e1)          # zaten birim (center⊥e1, ikisi de birim)
    return e1, e2


def _grid_cell_polar(g: int, r_p: float) -> tuple[np.ndarray, np.ndarray]:
    """Her hücre MERKEZİNİN kutupsal (ρ, α) koordinatı (equidistant projeksiyon).

    Hücre (row, col) -> kartezyen merkez [-r_p, r_p]² -> (ρ=hypot, α=atan2).
    row*g+col düzleştirme sırası imza bitleriyle aynı. FOV maskesi için kullanılır.
    """
    edges = np.linspace(-r_p, r_p, g + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])          # (g,)
    xc, yc = np.meshgrid(centers, centers)            # xc: sütun(x), yc: satır(y)
    rho = np.hypot(xc, yc).ravel()                    # (g²,) row-major (satır dış)
    alpha = np.arctan2(yc, xc).ravel()
    return rho, alpha


def _signature(center: np.ndarray, neigh: np.ndarray, ids: np.ndarray,
               cfg: PadgettGridConfig) -> tuple[np.ndarray | None, np.ndarray | None]:
    """`center` etrafındaki `neigh` (r_p içi) komşulardan g²-bit imza + hizalı taban.

    Döner (sig_bits (g²,) uint8 0/1, aligned_basis (2,3)) ya da NN yoksa (None,None).
    `ids`: komşu kimlikleri (deterministik NN tie-break için; katalog hip / gözlem obs_id).
    """
    g = cfg.grid_size
    if neigh.shape[0] == 0:
        return None, None
    cos_sep = np.clip(neigh @ center, -1.0, 1.0)
    sep = np.arccos(cos_sep)                           # (k,) açısal uzaklık (rad)
    e1, e2 = _tangent_basis(center)
    v_perp = neigh - cos_sep[:, None] * center         # teğet-düzlem izdüşümü
    comp1 = v_perp @ e1
    comp2 = v_perp @ e2
    az = np.arctan2(comp2, comp1)                      # ham azimut

    # NN seçimi: buffer DIŞI (sep > r_b) en yakın komşu; tie-break (sep, az, id)
    elig = sep > cfg.r_b
    if not np.any(elig):
        return None, None
    order = np.lexsort((ids, az, sep))                 # sep birincil anahtar
    nn = next(i for i in order if elig[i])
    phi = az[nn]                                       # NN azimutu -> hizalama açısı

    # hizalı taban: grid +x ekseni = NN yönü (roll bağımsızlığı buradan gelir)
    e1a = np.cos(phi) * e1 + np.sin(phi) * e2
    e2a = -np.sin(phi) * e1 + np.cos(phi) * e2

    az_rot = az - phi
    x = sep * np.cos(az_rot)                           # equidistant: yarıçap = sep
    y = sep * np.sin(az_rot)
    # [-r_p, r_p] -> [0, g); disk içi komşular sınır dışına taşmaz, yine de kırp
    col = np.clip(((x + cfg.r_p) / (2.0 * cfg.r_p) * g).astype(int), 0, g - 1)
    row = np.clip(((y + cfg.r_p) / (2.0 * cfg.r_p) * g).astype(int), 0, g - 1)
    sig = np.zeros(g * g, dtype=np.uint8)
    sig[row * g + col] = 1
    return sig, np.stack([e1a, e2a])


def _fov_mask(center: np.ndarray, basis: np.ndarray, rho: np.ndarray,
              alpha: np.ndarray, sensor: SensorProfile) -> np.ndarray:
    """Görünürlük maskesi: her hücrenin yönü boresight FOV'u içinde mi (g²,) uint8.

    Hücre yönü (equidistant, hizalı tabanda):
        d = cos(ρ)·center + sin(ρ)·(cos(α)·e1a + sin(α)·e2a)
    Maske = d_z >= cos(FOV_radius) (boresight = +z gövde ekseni). Attitude GEREKMEZ
    — gözlem body vektörleri zaten gövde çerçevesindedir.
    """
    e1a, e2a = basis[0], basis[1]
    tang_z = np.cos(alpha) * e1a[2] + np.sin(alpha) * e2a[2]   # (g²,)
    dz = np.cos(rho) * center[2] + np.sin(rho) * tang_z
    return (dz >= np.cos(sensor.fov_radius_rad)).astype(np.uint8)


# ===================================================================== algoritma
class PadgettGridAlgorithm:
    name = "padgett_grid"

    def __init__(self, config: PadgettGridConfig | None = None,
                 sensor: SensorProfile = SENSOR) -> None:
        self.cfg = config or PadgettGridConfig()
        self.sensor = sensor
        self._rho, self._alpha = _grid_cell_polar(self.cfg.grid_size, self.cfg.r_p)
        self.last_n_reference = 0        # teşhis: kaç gözlem imzası kuruldu
        self.last_consensus_size = 0     # teşhis: seçilen tutarlı kümenin boyutu

    # ------------------------------------------------------ DB: katalog imzaları
    def build_database(self, catalog: Catalog) -> GridDB:
        V = catalog.vectors
        hips = catalog.hip_ids
        cfg = self.cfg
        # r_p içi komşular (KD-tree ile), her katalog yıldızı için imza
        neigh_idx = catalog.kdtree.query_ball_point(
            V, 2.0 * np.sin(cfg.r_p / 2.0))
        sig_rows = np.zeros((len(V), cfg.n_bits), dtype=np.uint8)
        valid = np.zeros(len(V), dtype=bool)
        for i in range(len(V)):
            J = np.array([j for j in neigh_idx[i] if j != i], dtype=int)
            if J.size == 0:
                continue
            sig, _ = _signature(V[i], V[J], hips[J], cfg)
            if sig is not None:
                sig_rows[i] = sig
                valid[i] = True
        sig_packed = np.packbits(sig_rows, axis=1)     # (N, ceil(g²/8))
        return GridDB(sig_packed=sig_packed, hip_ids=hips.astype(np.int64),
                      valid=valid, catalog=catalog, g=cfg.grid_size,
                      r_p=cfg.r_p, n_bits=cfg.n_bits, n_records=len(V))

    # ------------------------------------------------ feature: gözlem imzaları
    def extract_features(self, observed: Sequence[BodyVector]) -> GridFeatures:
        obs = list(observed)
        cfg = self.cfg
        nbytes = (cfg.n_bits + 7) // 8
        f = len(obs)
        if f < 2:
            empty = np.zeros((f, nbytes), dtype=np.uint8)
            return GridFeatures(obs, empty, empty.copy(), np.zeros(f, dtype=bool))
        U = np.array([o.u_body for o in obs])          # (f,3)
        ids = np.array([o.obs_id for o in obs])
        cos_r = np.cos(cfg.r_p)
        sig_rows = np.zeros((f, cfg.n_bits), dtype=np.uint8)
        mask_rows = np.zeros((f, cfg.n_bits), dtype=np.uint8)
        valid = np.zeros(f, dtype=bool)
        for i in range(f):
            sep_cos = np.clip(U @ U[i], -1.0, 1.0)
            J = np.where((sep_cos >= cos_r) & (np.arange(f) != i))[0]
            if J.size == 0:
                continue
            sig, basis = _signature(U[i], U[J], ids[J], cfg)
            if sig is None:
                continue
            sig_rows[i] = sig
            mask_rows[i] = _fov_mask(U[i], basis, self._rho, self._alpha, self.sensor)
            valid[i] = True
        return GridFeatures(obs, np.packbits(sig_rows, axis=1),
                            np.packbits(mask_rows, axis=1), valid)

    # ------------------------------------------------------------------ match
    def match(self, features: GridFeatures, db: GridDB) -> list[CandidateMatch]:
        obs = features.observed
        cfg = self.cfg
        self.last_n_reference = int(features.valid.sum())
        self.last_consensus_size = 0
        cat_valid = db.valid
        if self.last_n_reference == 0 or not np.any(cat_valid):
            return []

        # brief §5 üç kapı: her geçerli gözlem yıldızı için en iyi katalog eşleşmesi,
        # sonra threshold (τ) + margin (Δ) + consensus. Grid yıldızları TEK TEK ID'ler.
        best_scores: list[tuple[int, int, float, float]] = []  # (obs_idx, hip, best, margin)
        for i in range(len(obs)):
            if not features.valid[i]:
                continue
            osig = features.sig_packed[i]
            omask = features.mask_packed[i]
            # maskeli Hamming: popcount((cat XOR obs) AND mask), tüm katalog vektörize
            xor = np.bitwise_and(np.bitwise_xor(db.sig_packed, osig), omask)
            hamming = _POPCOUNT[xor].sum(axis=1)       # (N,)
            hamming[~cat_valid] = db.n_bits + 1         # geçersiz katalog imzalarını ele
            score = db.n_bits - hamming                 # g² − Hamming (eşleşen hücre)
            b1 = int(np.argmax(score))
            best = float(score[b1])
            s2 = score.copy(); s2[b1] = -1.0
            best_scores.append((i, int(db.hip_ids[b1]), best, best - float(s2.max())))

        if cfg.use_shared_verify:
            return self._ablation(best_scores, obs, db)

        # kapı 1 (threshold) + kapı 2 (margin): near-tie = bozulmuş NN yöneliminin
        # imzasıdır -> belirsiz, ID verme (brief §5.2, en önemli güvenlik kapısı).
        accepted = [(i, hip) for (i, hip, best, margin) in best_scores
                    if best >= cfg.match_threshold and margin >= cfg.margin_threshold]
        if len(accepted) < cfg.min_consensus:
            return []
        # kapı 3 (consensus): en büyük geometrik-tutarlı alt küme (brief §5.3)
        keep = self._consensus_subset(accepted, obs, db.catalog)
        self.last_consensus_size = len(keep)
        if len(keep) < cfg.min_consensus:
            return []
        return [CandidateMatch(obs[i].obs_id, hip) for (i, hip) in keep]

    # ------------------------------------------------------------- ablation
    def _ablation(self, best_scores, obs, db) -> list[CandidateMatch]:
        """Native kapıları paylaşılan RANSAC ile değiştir (ham en-iyi/yıldız listesi).

        Sinyal kalitesini (imza -> ham argmax) doğrulama katmanından ayırır — Pyramid
        için istenen ayrıştırmanın aynısı (brief §6). Eşik/margin/consensus KOYULMAZ;
        her yıldızın ham en-iyi adayı RANSAC'a beslenir.
        """
        raw = [CandidateMatch(obs[i].obs_id, hip, confidence=best)
               for (i, hip, best, _margin) in best_scores]
        if len(raw) < 3:
            return []
        out = ransac_confirm(raw, obs, db.catalog,
                             gate_arcsec=self.cfg.verify_gate_arcsec)
        self.last_consensus_size = len(out)
        return out

    def _consensus_subset(self, accepted, obs, catalog) -> list[tuple[int, int]]:
        """En büyük ikili-geometrik-tutarlı obs->hip alt kümesi (brief §5.3 consensus).

        Tutarlılık: |ang(obs_a,obs_b) − ang(hipA,hipB)| <= tol. Korumalı NN yöneliminin
        yol açtığı yanlış ID'ler geometriyi bozar -> çekirdekten düşer. Küçük n (~<=15)
        için açgözlü tohum-büyütme yeterli (O(n³)).
        """
        n = len(accepted)
        if n == 0:
            return []
        tol = self.cfg.consensus_tol_arcsec * _ARCSEC
        ub = np.array([obs[i].u_body for (i, _h) in accepted])
        cv = np.array([catalog.by_id(h).u_inertial for (_i, h) in accepted])
        ang_obs = np.arccos(np.clip(ub @ ub.T, -1.0, 1.0))
        ang_cat = np.arccos(np.clip(cv @ cv.T, -1.0, 1.0))
        consistent = np.abs(ang_obs - ang_cat) <= tol      # (n,n) simetrik
        np.fill_diagonal(consistent, True)

        best_set: list[int] = []
        for seed in range(n):
            members = [seed]
            for cand in range(n):
                if cand == seed:
                    continue
                if all(consistent[cand, m] for m in members):
                    members.append(cand)
            if len(members) > len(best_set):
                best_set = members
        return [accepted[k] for k in best_set]
