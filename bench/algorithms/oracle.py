"""Oracle — sahte 'mükemmel' algoritma (bench self-test).

Gerçek bir Star-ID algoritması DEĞİLDİR. Görevi, gerçek algoritmalardan
ÖNCE harness'ı uçtan uca doğrulamak: truth'a bakarak doğru CandidateMatch
listesini döndürür (spike'ları atar).

NOT (PM'e — arayüz boşluğu): `match(features, db)` imzasında truth kanalı
yok. Oracle bunu standart-dışı `set_truth()` ile alır; runner bu metodu
yalnız oracle'da (hasattr) çağırır. StarIDAlgorithm Protocol'ü
değiştirilmedi — yalnız ek bir metod var. brief 01 §Yapma'ya sadık kalmak
için kontrat değiştirilmedi; bu sapma raporlanmıştır.
"""
from __future__ import annotations

from typing import Any, Sequence

from ..core.interfaces import BodyVector, Catalog, CandidateMatch, SceneTruth


class OracleAlgorithm:
    name = "oracle"

    def __init__(self) -> None:
        self._truth: SceneTruth | None = None

    # --- standart kontrat ---
    def build_database(self, catalog: Catalog) -> Catalog:
        """Katalogu olduğu gibi sar (DB = katalog)."""
        return catalog

    def extract_features(self, observed: Sequence[BodyVector]) -> Sequence[BodyVector]:
        """Gözlemleri aynen döndür."""
        return observed

    def match(self, features: Sequence[BodyVector], db: Catalog) -> list[CandidateMatch]:
        """Truth'a bakarak doğru eşleşmeleri döndür; spike'ları at."""
        if self._truth is None:
            raise RuntimeError("Oracle.match çağrılmadan önce set_truth() gerekir.")
        tm = self._truth.true_matches
        return [
            CandidateMatch(obs_id=o.obs_id, hip_id=tm[o.obs_id], confidence=1.0)
            for o in features
            if o.obs_id in tm  # spike değil
        ]

    # --- oracle'a özel (Protocol dışı) ---
    def set_truth(self, truth: SceneTruth) -> None:
        self._truth = truth
