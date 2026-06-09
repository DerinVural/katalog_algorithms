"""Plugin arayüz kontratı (PROJECT_PLAN.md §3).

Tüm algoritmalar `StarIDAlgorithm` protokolünü doldurur. Veri tipleri
dataclass; `Catalog` ek olarak by_id / vektör matrisi / KD-tree yardımcıları
sağlar (core içinde, brief 01 KAT-01).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Protocol, Sequence

import numpy as np
from scipy.spatial import cKDTree


@dataclass
class CatalogStar:
    hip_id: int
    u_inertial: np.ndarray   # birim vektör (3,), J2000 / ICRS
    mag: float


@dataclass
class Catalog:
    stars: list[CatalogStar]
    _by_id: dict[int, CatalogStar] | None = field(
        default=None, repr=False, compare=False
    )

    def by_id(self, hip_id: int) -> CatalogStar:
        if self._by_id is None:
            self._by_id = {s.hip_id: s for s in self.stars}
        return self._by_id[hip_id]

    @cached_property
    def vectors(self) -> np.ndarray:
        """(N, 3) birim vektör matrisi (stars sırasıyla)."""
        return np.array([s.u_inertial for s in self.stars], dtype=float)

    @cached_property
    def hip_ids(self) -> np.ndarray:
        return np.array([s.hip_id for s in self.stars], dtype=np.int64)

    @cached_property
    def kdtree(self) -> cKDTree:
        """3B birim vektörler üzerinde KD-tree (hızlı komşu sorgusu)."""
        return cKDTree(self.vectors)

    def query_radius(self, u: np.ndarray, radius_rad: float) -> np.ndarray:
        """`u` yönünün açısal `radius_rad` içindeki yıldızların indeksleri.

        Birim küre üzerinde açısal yarıçap, kiriş (Euclidean) yarıçapına
        çevrilir: chord = 2 sin(theta/2).
        """
        chord = 2.0 * np.sin(radius_rad / 2.0)
        return np.array(self.kdtree.query_ball_point(u, chord), dtype=int)

    def __len__(self) -> int:
        return len(self.stars)


@dataclass
class BodyVector:
    obs_id: int              # bu gözlemin yerel indeksi
    u_body: np.ndarray       # birim vektör (3,), sensör gövde çerçevesi
    mag: float               # instrumental magnitude (gürültülü)
    centroid_px: np.ndarray  # (2,) görüntü merkezine göre, S-curve/timing için


@dataclass
class CandidateMatch:
    obs_id: int              # gözlenen yıldız
    hip_id: int              # eşleştiği katalog yıldızı
    confidence: float = 1.0


@dataclass
class SceneTruth:
    q_true: np.ndarray              # (4,) doğru attitude quaternion [x,y,z,w]
    true_matches: dict[int, int]    # obs_id -> hip_id (yalnız gerçek yıldızlar)


class StarIDAlgorithm(Protocol):
    name: str

    def build_database(self, catalog: Catalog) -> Any:
        """Algoritmaya özel DB/index üret (k-vector, binary tree, grid, ...).
        Bellek boyutu burada ölçülür."""
        ...

    def extract_features(self, observed: Sequence[BodyVector]) -> Any:
        """Gözlenen yıldızlardan algoritmanın feature'larını çıkar.
        Survey Tablo 1'deki 'feature extraction' süresi burada ölçülür."""
        ...

    def match(self, features: Any, db: Any) -> list[CandidateMatch]:
        """DB araması + error checking. Survey'deki 'database search' süresi
        burada ölçülür."""
        ...

    # Opsiyonel — sadece recursive modu olan algoritmalar
    def identify_recursive(
        self, observed: Sequence[BodyVector], db: Any, q_prior: np.ndarray
    ) -> list[CandidateMatch]:
        ...
